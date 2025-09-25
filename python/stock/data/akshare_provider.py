from __future__ import annotations
from datetime import date
from typing import List, Iterable, Optional
import os
import json
import time
import pandas as pd
import akshare as ak
from concurrent.futures import ThreadPoolExecutor, as_completed
from stock.interfaces.data_provider import DataProvider, BarRequest

HS300_INDEX = "000300.SH"
CSI500_INDEX = "000905.SH"

CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'raw')
INDEX_CACHE_HS300 = os.path.join(CACHE_DIR, 'index_members_000300.json')
INDEX_CACHE_CSI500 = os.path.join(CACHE_DIR, 'index_members_000905.json')
HIST_DIR = os.path.join(CACHE_DIR, 'hist')
os.makedirs(HIST_DIR, exist_ok=True)
BASIC_INFO_CACHE = os.path.join(CACHE_DIR, 'basic_info.parquet')

class AkShareProvider(DataProvider):
    def _load_index_cache(self, cache_path: str) -> Optional[List[str]]:
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    payload = json.load(f)
                if (time.time() - payload.get('ts', 0)) < 86400:  # 1 天缓存
                    return payload.get('symbols', [])
            except Exception:
                return None
        return None

    def _save_index_cache(self, cache_path: str, symbols: List[str]):
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump({'ts': time.time(), 'symbols': symbols}, f, ensure_ascii=False)
        except Exception:
            pass

    def _fetch_index_members(self, symbol_code: str) -> List[str]:
        df = ak.index_stock_cons(symbol=symbol_code)
        code_col = '品种代码'
        if code_col not in df.columns:
            raise RuntimeError("index_stock_cons columns changed; got: %s" % df.columns.tolist())
        codes = df[code_col].astype(str).str.zfill(6)
        def _suffix(c: str):
            return c + ('.SH' if c.startswith('6') else '.SZ')
        return [ _suffix(c) for c in codes.unique().tolist() ]

    def get_index_members(self, index_code: str, as_of: date) -> List[str]:
        """获取指定指数成分（近似实时）。支持 HS300 / CSI500。"""
        if index_code == HS300_INDEX:
            cache = self._load_index_cache(INDEX_CACHE_HS300)
            if cache:
                return cache
            symbols = self._fetch_index_members("000300")
            self._save_index_cache(INDEX_CACHE_HS300, symbols)
            return symbols
        elif index_code == CSI500_INDEX:
            cache = self._load_index_cache(INDEX_CACHE_CSI500)
            if cache:
                return cache
            symbols = self._fetch_index_members("000905")
            self._save_index_cache(INDEX_CACHE_CSI500, symbols)
            return symbols
        else:
            raise NotImplementedError("Unsupported index code: %s" % index_code)

    def get_universe(self, as_of: date) -> List[str]:
        """根据环境变量 UNIVERSE_MODE 返回股票列表。
        UNIVERSE_MODE=HS300 (默认) | CSI800 (HS300 + CSI500 去重) | FULLA (全A: stock_info_a_code_name)
        """
        mode = os.environ.get('UNIVERSE_MODE', 'HS300').upper()
        if mode == 'HS300':
            return self.get_index_members(HS300_INDEX, as_of)
        if mode == 'CSI800':
            hs = set(self.get_index_members(HS300_INDEX, as_of))
            csi500 = set(self.get_index_members(CSI500_INDEX, as_of))
            merged = sorted(hs.union(csi500))
            print(f"[INFO] UNIVERSE_MODE=CSI800 组合成分数量={len(merged)}")
            return merged
        if mode == 'FULLA':
            df = ak.stock_info_a_code_name()
            symbols = df['code'].astype(str).str.zfill(6).map(lambda c: c + ('.SH' if c.startswith('6') else '.SZ'))
            symbols = sorted(symbols.unique().tolist())
            print(f"[INFO] UNIVERSE_MODE=FULLA 全A股票数量={len(symbols)}")
            return symbols
        print(f"[WARN] 未识别的 UNIVERSE_MODE={mode}，回退到 HS300")
        return self.get_index_members(HS300_INDEX, as_of)

    def _load_symbol_hist_cached(self, symbol: str) -> Optional[pd.DataFrame]:
        fp = os.path.join(HIST_DIR, f"{symbol.replace('.', '_')}.parquet")
        if os.path.exists(fp):
            try:
                return pd.read_parquet(fp)
            except Exception:
                return None
        return None

    def _save_symbol_hist(self, symbol: str, df: pd.DataFrame):
        fp = os.path.join(HIST_DIR, f"{symbol.replace('.', '_')}.parquet")
        try:
            df.to_parquet(fp)
        except Exception:
            pass

    def _fetch_one(self, sym: str, start: date, end: date) -> pd.DataFrame:
        code = sym[:6]
        # 目前只处理 A 股主板/创业板，后续可扩展
        try:
            df = ak.stock_zh_a_hist(symbol=code, period="daily", start_date=start.strftime('%Y%m%d'), end_date=end.strftime('%Y%m%d'), adjust="hfq")
        except Exception as e:
            print(f"[WARN] fetch failed {sym}: {e}")
            return pd.DataFrame()
        rename_map = {'日期':'date','开盘':'open','收盘':'close','最高':'high','最低':'low','成交量':'volume','成交额':'amount'}
        for k,v in rename_map.items():
            if k in df.columns:
                df.rename(columns={k:v}, inplace=True)
        if 'date' not in df.columns:
            return pd.DataFrame()
        df['symbol'] = sym
        df['date'] = pd.to_datetime(df['date']).dt.date
        df['preclose'] = df['close'].shift(1)
        df['adj_factor'] = 1.0
        out = df[['date','symbol','open','high','low','close','preclose','volume','amount','adj_factor']].copy()
        self._save_symbol_hist(sym, out)
        return out

    def get_daily_bars(self, req: BarRequest) -> pd.DataFrame:
        symbols = list(req.symbols)
        # quick 模式（测试用）
        quick = int(os.environ.get('QUICK_MODE', '0')) == 1
        if quick and len(symbols) > 50:
            symbols = symbols[:50]
            print(f"[INFO] QUICK_MODE=1 仅抓取前 50 支股票用于快速测试")
        frames = []
        to_fetch = []
        cache_hits = 0
        for sym in symbols:
            cached = self._load_symbol_hist_cached(sym)
            if cached is not None:
                # 过滤时间区间
                cached_slice = cached[(cached['date'] >= req.start) & (cached['date'] <= req.end)]
                frames.append(cached_slice)
                cache_hits += 1
            else:
                to_fetch.append(sym)
        if to_fetch:
            start_time = time.time()
            print(f"[INFO] 开始抓取 {len(to_fetch)} 支股票（日线后复权）...")
            with ThreadPoolExecutor(max_workers=min(8, len(to_fetch))) as ex:
                futures = {ex.submit(self._fetch_one, s, req.start, req.end): s for s in to_fetch}
                done = 0
                for fut in as_completed(futures):
                    sym = futures[fut]
                    df = fut.result()
                    if not df.empty:
                        frames.append(df)
                    done += 1
                    if done % 10 == 0 or done == len(to_fetch):
                        elapsed = time.time() - start_time
                        speed = done/elapsed if elapsed>0 else 0
                        eta = (len(to_fetch)-done)/speed if speed>0 else -1
                        print(f"[PROG] {done}/{len(to_fetch)} 完成, 用时 {elapsed:.1f}s, 预计剩余 {eta:.1f}s")
            print(f"[INFO] 抓取完成: cache_hits={cache_hits} miss={len(to_fetch)} 命中率={cache_hits/ max(1,len(symbols)):.2%}")
        else:
            print(f"[INFO] 全部 {len(symbols)} 支股票命中缓存，直接使用。")
        if not frames:
            return pd.DataFrame(columns=['date','symbol','open','high','low','close','preclose','volume','amount','adj_factor'])
        out = pd.concat(frames, ignore_index=True)
        # 统一按 symbol,date 排序去重
        out = out.sort_values(['symbol','date']).drop_duplicates(['symbol','date'])
        mask = (out['date'] >= req.start) & (out['date'] <= req.end)
        out = out[mask]
        
        # 添加交易状态检测（停牌与涨跌停标记）
        out = self._add_trading_status(out)
        return out

    def get_basic_info(self) -> pd.DataFrame:
        """
        获取A股基础信息
        
        返回数据结构 (已验证 2025-09-25):
        DataFrame 包含以下列:
        - symbol: str, 股票代码 (如 '000001.SZ', '600000.SH') 
        - name: str, 股票名称 (如 '平安银行', '浦发银行')
        - exchange: str, 交易所 ('SH' | 'SZ')
        - is_st: bool, 是否ST股票
        - market: str, 市场类型 (固定为'A')
        - list_date: str, 上市日期 (YYYY-MM-DD格式, 可能为None)
        
        数据来源: akshare.stock_info_a_code_name()
        原始数据转换:
        - code -> symbol (补齐6位数字 + '.SH'或'.SZ')  
        - name -> name (保持不变)
        - 根据首位数字判断交易所(6开头=SH, 其他=SZ)
        
        缓存策略: 本地parquet文件, 1天过期
        """
        # 若缓存存在且未过期(1天)则直接读取
        if os.path.exists(BASIC_INFO_CACHE):
            try:
                mtime = os.path.getmtime(BASIC_INFO_CACHE)
                if (time.time() - mtime) < 86400:
                    cached = pd.read_parquet(BASIC_INFO_CACHE)
                    if not cached.empty:
                        return cached
            except Exception:
                pass
        base = ak.stock_info_a_code_name()
        base.rename(columns={'code':'symbol','name':'name'}, inplace=True)
        base['symbol'] = base['symbol'].astype(str).str.zfill(6)
        base['exchange'] = base['symbol'].str[0].map(lambda x: 'SH' if x == '6' else 'SZ')
        base['symbol'] = base['symbol'] + '.' + base['exchange']
        # is_st: 名称包含 ST / *ST / ST* 均视为 ST
        base['is_st'] = base['name'].str.upper().str.contains('ST')
        base['market'] = 'A'
        # 获取上市日期: 优先使用 ak.stock_info_a_code_name 返回的 '上市日期'(若存在)
        list_date_col_candidates = ['上市日期','list_date','LIST_DATE']
        list_dates = None
        for c in list_date_col_candidates:
            if c in base.columns:
                list_dates = pd.to_datetime(base[c], errors='coerce')
                break
        if list_dates is None:
            list_dates = pd.NaT
        base['list_date'] = list_dates
        # 对缺失上市日期的股票尝试单只补抓 (数量可能较多, 设限)
        missing = base[base['list_date'].isna()].copy()
        # 限制最大补抓数量, 避免首次运行太慢
        limit = int(os.environ.get('LISTDATE_FETCH_LIMIT', '200'))
        to_fetch = missing.head(limit)
        fetched_map = {}
        if not to_fetch.empty:
            print(f"[INFO] 尝试补抓上市日期: {len(to_fetch)}/{len(missing)} (limit={limit})")
            for sym in to_fetch['symbol']:
                code = sym[:6]
                try:
                    # akshare 接口: stock_individual_info_em 返回包含上市日期的信息
                    # 使用6位代码（不带.SH/.SZ后缀）
                    info_df = ak.stock_individual_info_em(symbol=code)
                    
                    # 该接口返回两列: item, value; 寻找 '上市时间' 或 '上市日期'
                    if 'item' in info_df.columns and 'value' in info_df.columns:
                        # 尝试查找上市时间或上市日期
                        row = info_df[info_df['item'].str.contains('上市时间|上市日期', na=False)]
                        if not row.empty:
                            date_value = row['value'].iloc[0]
                            # 处理不同的日期格式
                            if isinstance(date_value, (int, float)):
                                # 数字格式：YYYYMMDD，如 19910403
                                date_str = str(int(date_value))
                                if len(date_str) == 8:
                                    try:
                                        ld = pd.to_datetime(date_str, format='%Y%m%d', errors='coerce')
                                    except:
                                        ld = pd.to_datetime(date_str, errors='coerce')
                                else:
                                    ld = pd.to_datetime(date_str, errors='coerce')
                            else:
                                # 字符串格式
                                ld = pd.to_datetime(date_value, errors='coerce')
                            
                            if pd.notna(ld):
                                fetched_map[sym] = ld
                except Exception as e:
                    print(f"[WARN] 单只上市日期获取失败 {sym}: {e}")
                time.sleep(0.2)  # 轻节流防止被限流
        if fetched_map:
            base.loc[base['symbol'].isin(fetched_map.keys()), 'list_date'] = base['symbol'].map(fetched_map)
        # 排序并缓存
        out = base[['symbol','name','list_date','is_st','market','exchange']].copy()
        try:
            out.to_parquet(BASIC_INFO_CACHE, index=False)
        except Exception as e:
            print(f"[WARN] basic_info 缓存失败: {e}")
        return out

    def _add_trading_status(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        为价格数据添加交易状态标记
        新增列：is_trading, limit_up_oneword, limit_down_oneword
        """
        if df.empty:
            return df
            
        df = df.copy()
        
        # 初始化交易状态：默认可交易
        df['is_trading'] = 1
        df['limit_up_oneword'] = 0
        df['limit_down_oneword'] = 0
        
        # 停牌检测：成交量为0/缺失，或价格数据缺失
        suspend_mask = (
            (df['volume'] == 0) | 
            (df['volume'].isna()) |
            (df['open'].isna()) |
            (df['close'].isna()) |
            (df['high'].isna()) |
            (df['low'].isna())
        )
        df.loc[suspend_mask, 'is_trading'] = 0
        
        # 一字涨跌停检测（仅在有交易时检测）
        trading_mask = df['is_trading'] == 1
        if trading_mask.any():
            trading_df = df.loc[trading_mask].copy()
            
            # 一字板：开盘=最高=最低=收盘
            oneword_mask = (
                (trading_df['open'] == trading_df['high']) & 
                (trading_df['high'] == trading_df['low']) & 
                (trading_df['low'] == trading_df['close'])
            )
            
            if oneword_mask.any() and 'preclose' in trading_df.columns:
                # 计算涨跌幅
                preclose_valid = trading_df['preclose'].notna() & (trading_df['preclose'] > 0)
                valid_mask = oneword_mask & preclose_valid
                
                if valid_mask.any():
                    pct_change = (trading_df.loc[valid_mask, 'close'] / trading_df.loc[valid_mask, 'preclose']) - 1
                    
                    # 涨停：涨幅 >= 9.8%
                    limit_up_mask = valid_mask & (pct_change >= 0.098)
                    df.loc[trading_df.index[limit_up_mask], 'limit_up_oneword'] = 1
                    
                    # 跌停：跌幅 <= -9.8%
                    limit_down_mask = valid_mask & (pct_change <= -0.098)
                    df.loc[trading_df.index[limit_down_mask], 'limit_down_oneword'] = 1
        
        return df

    def get_corporate_actions(self, symbols: Iterable[str]) -> pd.DataFrame:
        # Placeholder: could use ak.stock_history_dividend
        return pd.DataFrame(columns=['symbol','action_date','type','value'])

    def get_index_data_cached(self, index_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取指数历史数据（带缓存）
        
        Args:
            index_code: 指数代码，如 "000300"(沪深300), "000905"(中证500), "000001"(上证指数)
            start_date: 开始日期，格式 "20200101"
            end_date: 结束日期，格式 "20250831"
            
        Returns:
            pd.DataFrame: 包含日期、收盘价等字段的指数数据
        """
        # 生成缓存文件路径
        cache_file = os.path.join(CACHE_DIR, f'index_{index_code}_{start_date}_{end_date}.parquet')
        
        # 尝试加载缓存
        if os.path.exists(cache_file):
            try:
                mtime = os.path.getmtime(cache_file)
                # 如果缓存不到1天，直接使用
                if (time.time() - mtime) < 86400:
                    cached_df = pd.read_parquet(cache_file)
                    if not cached_df.empty:
                        return cached_df
            except Exception as e:
                print(f"[WARN] 读取指数缓存失败 {index_code}: {e}")
        
        # 从akshare获取指数数据
        try:
            df = ak.stock_zh_index_daily(symbol=f"sh{index_code}")
            if df.empty:
                print(f"[WARN] 未获取到指数数据: {index_code}")
                return pd.DataFrame()
            
            # 标准化列名
            rename_map = {
                'date': '日期',
                'open': '开盘',
                'high': '最高',
                'low': '最低',
                'close': '收盘',
                'volume': '成交量'
            }
            for k, v in rename_map.items():
                if k in df.columns:
                    df.rename(columns={k: v}, inplace=True)
            
            # 确保有必要的列
            if '日期' not in df.columns or '收盘' not in df.columns:
                print(f"[ERROR] 指数数据缺少必要字段: {df.columns.tolist()}")
                return pd.DataFrame()
            
            # 转换日期格式
            df['日期'] = pd.to_datetime(df['日期'])
            
            # 过滤日期范围
            start_dt = pd.to_datetime(start_date, format='%Y%m%d')
            end_dt = pd.to_datetime(end_date, format='%Y%m%d')
            df = df[(df['日期'] >= start_dt) & (df['日期'] <= end_dt)].copy()
            
            # 排序
            df = df.sort_values('日期').reset_index(drop=True)
            
            # 保存缓存
            try:
                df.to_parquet(cache_file, index=False)
            except Exception as e:
                print(f"[WARN] 保存指数缓存失败 {index_code}: {e}")
            
            return df
            
        except Exception as e:
            print(f"[ERROR] 获取指数数据失败 {index_code}: {e}")
            return pd.DataFrame()
    
    def get_trading_calendar(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取交易日历
        
        Args:
            start_date: 开始日期，格式 "20200101"  
            end_date: 结束日期，格式 "20251231"
            
        Returns:
            pd.DataFrame: 包含交易日期的DataFrame，列为 ['cal_date', 'is_open']
        """
        try:
            # 使用akshare获取交易日历
            df = ak.tool_trade_date_hist_sina()
            
            if df.empty:
                print("[WARN] 未获取到交易日历数据")
                return pd.DataFrame(columns=['cal_date', 'is_open'])
            
            # trade_date 是 datetime.date 对象，直接转换为字符串
            df['cal_date'] = df['trade_date'].astype(str)
            df['is_open'] = 1  # 交易日历中的日期都是交易日
            
            # 过滤日期范围 - 转换日期格式进行比较
            start_dt = pd.to_datetime(start_date, format='%Y%m%d').date()
            end_dt = pd.to_datetime(end_date, format='%Y%m%d').date()
            
            # 直接用 date 对象进行过滤
            df = df[
                (df['trade_date'] >= start_dt) & 
                (df['trade_date'] <= end_dt)
            ].copy()
            
            # 返回所需格式
            return df[['cal_date', 'is_open']].reset_index(drop=True)
            
        except Exception as e:
            print(f"[ERROR] 获取交易日历失败: {e}")
            # 返回空DataFrame但包含正确的列结构
            return pd.DataFrame(columns=['cal_date', 'is_open'])

    def get_daily_price(self, stock_codes: List[str], start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取指定日期范围的日线数据
        
        Args:
            stock_codes: 股票代码列表，格式如 ['000001.SZ', '600000.SH']
            start_date: 开始日期 'YYYY-MM-DD'
            end_date: 结束日期 'YYYY-MM-DD'
            
        Returns:
            pd.DataFrame: 日K线数据
            
        返回数据结构 (已验证 2025-09-25):
        DataFrame 包含以下列:
        - ts_code: str, 股票代码 (如 '000001.SZ', '600000.SH')
        - trade_date: str, 交易日期 (YYYYMMDD格式, 如 '20250925') 
        - open: float, 开盘价
        - high: float, 最高价  
        - low: float, 最低价
        - close: float, 收盘价
        - vol: float, 成交量 (手)
        - amount: float, 成交额 (元)
        
        数据来源: akshare.stock_zh_a_hist() 
        注意: 
        1. trade_date为YYYYMMDD格式，不是YYYY-MM-DD
        2. 成交量单位为手，成交额单位为元
        3. 可能包含停牌日数据(成交量为0)
        4. 按股票代码和日期排序
        """
        try:
            import pandas as pd
            from datetime import datetime
            
            # 转换日期格式
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            
            results = []
            
            for code in stock_codes:
                try:
                    # 提取股票代码（去掉后缀）
                    stock_code = code.split('.')[0]
                    
                    # 调用akshare获取股票日线数据
                    df = ak.stock_zh_a_hist(
                        symbol=stock_code, 
                        period="daily", 
                        start_date=start_dt.strftime('%Y%m%d'), 
                        end_date=end_dt.strftime('%Y%m%d'), 
                        adjust="qfq"  # 前复权
                    )
                    
                    if df.empty:
                        continue
                    
                    # 标准化列名
                    rename_map = {
                        '日期': 'trade_date',
                        '开盘': 'open', 
                        '收盘': 'close',
                        '最高': 'high',
                        '最低': 'low',
                        '成交量': 'vol',
                        '成交额': 'amount'
                    }
                    
                    df = df.rename(columns=rename_map)
                    
                    # 添加股票代码
                    df['ts_code'] = code
                    
                    # 转换日期格式
                    df['trade_date'] = pd.to_datetime(df['trade_date']).dt.strftime('%Y%m%d')
                    
                    # 选择需要的列
                    df = df[['ts_code', 'trade_date', 'open', 'high', 'low', 'close', 'vol', 'amount']]
                    
                    results.append(df)
                    
                except Exception as e:
                    print(f"获取 {code} 价格数据失败: {e}")
                    continue
            
            if results:
                final_df = pd.concat(results, ignore_index=True)
                return final_df
            else:
                return pd.DataFrame(columns=['ts_code', 'trade_date', 'open', 'high', 'low', 'close', 'vol', 'amount'])
                
        except Exception as e:
            print(f"获取股票价格数据失败: {e}")
            return pd.DataFrame(columns=['ts_code', 'trade_date', 'open', 'high', 'low', 'close', 'vol', 'amount'])
