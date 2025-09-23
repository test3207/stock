from __future__ import annotations
from datetime import date
from typing import List, Dict, Any
import pandas as pd

from stock.interfaces.data_provider import Strategy

class DrawdownReversalStrategy:
    """
    规则：
      - Universe 已限定为 HS300
      - 过滤：上市 >=5年；非ST；最近6个月(约126交易日)跌幅 >=20%
      - 排除：东北地区公司（辽宁、吉林、黑龙江）
      - 等权持仓（目标持仓数量 N，可配置，默认30）
    计算：过去6个月收盘价跌幅 = (当前收盘 / 6个月前收盘 - 1) <= -0.20
    等权：选出满足条件全部，若多于N只，取跌幅最大的前N（跌幅数值更负）
    """
    def __init__(self, lookback_days: int = 126, top_n: int = 30,
                 primary_drawdown: float = -0.20,
                 fallback_drawdown: float = -0.10,
                 min_primary_ratio: float = 0.5,
                 buy_all: bool = True,
                 enforce_st_filter: bool = True,
                 exclude_northeast: bool = True):
        """
        primary_drawdown: 主阈值 (<= -20%)
        fallback_drawdown: 候选不足时放宽阈值 (<= -10%)
        min_primary_ratio: 若主阈值满足数量 < top_n * 该比例，则启用 fallback
        exclude_northeast: 是否排除东北地区公司
        """
        self.lookback_days = lookback_days
        self.top_n = top_n
        self.primary_drawdown = primary_drawdown
        self.fallback_drawdown = fallback_drawdown
        self.min_primary_ratio = min_primary_ratio
        self.buy_all = buy_all
        self.enforce_st_filter = enforce_st_filter
        self.exclude_northeast = exclude_northeast
        
        # 东北地区股票代码前缀（基于交易所上市地区规律）
        self.northeast_prefixes = {
            # 辽宁省主要股票代码
            '000410', '000709', '000723', '000726', '000758', '000767', '000778',
            '000798', '000802', '000806', '000850', '000851', '000852', '000878',
            '000898', '000930', '000962', '000969', '002103', '002153', '002215',
            '002303', '002325', '002340', '002392', '002424', '002477', '002477',
            '600507', '600509', '600517', '600519', '600525', '600546', '600558',
            '600581', '600585', '600587', '600592', '600594', '600606', '600616',
            '600623', '600631', '600647', '600679', '600683', '600688', '600726',
            '600739', '600747', '600753', '600759', '600773', '600782', '600792',
            '600810', '600836', '600856', '600894', '600986',
            
            # 吉林省主要股票代码  
            '000547', '000557', '000623', '000661', '000687', '000698', '000700',
            '000718', '000780', '000797', '000812', '000885', '000903', '000949',
            '002019', '002102', '002148', '002164', '002178', '002226', '002245',
            '002278', '002323', '002390', '002468', '002506', '002565', '002626',
            '600095', '600128', '600252', '600291', '600295', '600303', '600352',
            '600365', '600375', '600403', '600455', '600499', '600500', '600520',
            '600563', '600578', '600590', '600593', '600595', '600604', '600618',
            '600663', '600677', '600691', '600694', '600701', '600714', '600723',
            '600756', '600769', '600775', '600803', '600817', '600821', '600853',
            '600860', '600863', '600876', '600900', '600917', '600965',
            
            # 黑龙江省主要股票代码
            '000090', '000408', '000531', '000554', '000610', '000620', '000626',
            '000627', '000635', '000650', '000652', '000682', '000703', '000712',
            '000717', '000737', '000758', '000816', '000833', '000875', '000902',
            '000912', '000915', '000950', '002009', '002041', '002092', '002129',
            '002159', '002184', '002202', '002234', '002263', '002287', '002328',
            '002353', '002374', '002395', '002421', '002430', '002455', '002463',
            '002482', '002498', '002508', '002529', '002535', '002560', '002569',
            '600095', '600098', '600108', '600119', '600123', '600127', '600135',
            '600153', '600157', '600165', '600189', '600201', '600217', '600226',
            '600240', '600248', '600261', '600267', '600271', '600275', '600285',
            '600298', '600309', '600315', '600321', '600326', '600338', '600348',
            '600354', '600362', '600371', '600378', '600381', '600391', '600397',
            '600408', '600419', '600425', '600428', '600435', '600443', '600449',
            '600456', '600462', '600467', '600475', '600485', '600490', '600502',
            '600511', '600515', '600521', '600528', '600535', '600542', '600548',
            '600556', '600565', '600573', '600582', '600589', '600597', '600602',
            '600610', '600619', '600625', '600632', '600639', '600645', '600652',
            '600659', '600666', '600673', '600681', '600687', '600693', '600700',
            '600707', '600713', '600720', '600727', '600734', '600741', '600748',
            '600755', '600762', '600768', '600776', '600783', '600789', '600796',
            '600802', '600809', '600815', '600822', '600829', '600835', '600842',
            '600848', '600855', '600861', '600868', '600874', '600881', '600887',
            '600893', '600899', '600905', '600912', '600918', '600925', '600931',
            '600938', '600944', '600951', '600957', '600964', '600970', '600977',
            '600983', '600989', '600995'
        }

    def is_northeast_company(self, symbol: str) -> bool:
        """判断是否为东北地区公司"""
        if not symbol or len(symbol) < 6:
            return False
        
        # 提取6位代码
        code = symbol[:6]
        return code in self.northeast_prefixes

    def generate_target_weights(self, trade_date: date, universe: List[str], data_ctx: Dict[str, Any]) -> Dict[str, float]:
        price_panel: pd.DataFrame = data_ctx.get('price_history')  # expected columns: date,symbol,close
        basic: pd.DataFrame = data_ctx.get('basic_info')  # symbol,list_date,is_st
        if price_panel is None or basic is None:
            return {}
        sub = price_panel.sort_values('date')
        dates_sorted = sorted(sub['date'].unique())
        if trade_date not in dates_sorted:
            return {}
        idx = dates_sorted.index(trade_date)
        # 窗口不足直接返回空（回测前期）
        if idx < self.lookback_days:
            return {}
        hist_start_date = dates_sorted[idx - self.lookback_days]
        latest = sub[sub['date'] == trade_date]
        hist_start = sub[sub['date'] == hist_start_date][['symbol','close']].rename(columns={'close':'past_close'})
        if latest.empty or hist_start.empty:
            return {}
        merged = latest.merge(hist_start, on='symbol', how='inner')
        merged['ret_6m'] = merged['close']/merged['past_close'] - 1
        # Join basic info
        merged = merged.merge(basic[['symbol','list_date','is_st']], on='symbol', how='left')
        # Listing age
        try:
            merged['list_date'] = pd.to_datetime(merged['list_date'], errors='coerce')
            merged['age_years'] = (pd.to_datetime(trade_date) - merged['list_date']).dt.days / 365
            # 对缺失上市日期的（NaT）填充一个大值，避免被年龄过滤全部剔除
            merged['age_years'] = merged['age_years'].fillna(10)
        except Exception:
            merged['age_years'] = 10  # fallback assume listed long enough
        
        # 应用过滤条件
        st_mask = ~merged['is_st'] if self.enforce_st_filter else (merged['is_st'] == merged['is_st'])  # 全 True
        
        # 东北地区过滤
        if self.exclude_northeast:
            northeast_mask = ~merged['symbol'].apply(self.is_northeast_company)
            excluded_count = (~northeast_mask).sum()
            if excluded_count > 0:
                print(f"[STRAT] {trade_date} 排除东北地区公司: {excluded_count}只")
        else:
            northeast_mask = pd.Series([True] * len(merged))
        
        base_filter = (merged['age_years'] >=5) & st_mask & northeast_mask
        primary_cond = base_filter & (merged['ret_6m'] <= self.primary_drawdown)
        primary = merged[primary_cond].copy()
        use_fallback = False
        need_min = int(self.top_n * self.min_primary_ratio)
        if len(primary) < need_min:
            fallback_cond = base_filter & (merged['ret_6m'] <= self.fallback_drawdown)
            fallback = merged[fallback_cond].copy()
            if not fallback.empty:
                use_fallback = True
                pool = fallback
            else:
                pool = primary  # 可能全空
        else:
            pool = primary
        if pool.empty:
            # 统计并强制选择最差标的（即便不满足阈值）防止完全空仓
            stats_source = merged[base_filter].copy()
            if not stats_source.empty:
                q = stats_source['ret_6m'].quantile
                min_ret = stats_source['ret_6m'].min()
                p10 = q(0.1)
                p25 = q(0.25)
                median = q(0.5)
                print(f"[STRAT] {trade_date} 阈值无候选 primary={len(primary)} fallback_used={use_fallback} ret6m[min={min_ret:.2%} p10={p10:.2%} p25={p25:.2%} med={median:.2%}] 强制选择最差 {self.top_n}")
                force = stats_source.sort_values('ret_6m').head(self.top_n)
                pool = force
            else:
                print(f"[STRAT] {trade_date} 无任何可用标的 (base_filter 为空)")
                return {}
        pool = pool.sort_values('ret_6m')  # more negative first
        if self.buy_all:
            select = pool  # 全部持有
        else:
            select = pool.head(self.top_n)
        if use_fallback:
            print(f"[STRAT] {trade_date} 主阈值不足({len(primary)}) 启用放宽阈值({self.fallback_drawdown}) 候选={len(pool)}")
        else:
            print(f"[STRAT] {trade_date} 主阈值候选={len(primary)} 使用主集合")
        n = len(select)
        weight = 1.0 / n if n>0 else 0
        return {sym: weight for sym in select['symbol']}
