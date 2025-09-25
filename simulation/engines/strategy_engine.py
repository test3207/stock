#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略引擎 - T-1选股，T日执行模式
负责执行量化策略，进行股票选择

设计理念：
1. T-1日晚上：基于历史数据进行策略计算和选股
2. T日早上：获取实时价格，直接执行交易
3. 避免开盘时间的复杂计算，提高执行效率
"""

import sys
import logging
import pandas as pd
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

# 导入时区感知工具
try:
    sys.path.append(str(Path(__file__).parent.parent.parent))
    from python.stock.utils.timezone_helper import get_trading_timestamp, get_trading_date, get_cst_now
except ImportError:
    # 回退实现
    def get_trading_timestamp():
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    def get_trading_date():
        return datetime.now().strftime('%Y-%m-%d')
    def get_cst_now():
        return datetime.now()

# 添加项目根路径
sys.path.append(str(Path(__file__).parent.parent.parent))

from python.stock.data.akshare_provider import AkShareProvider
from python.stock.strategies.enhanced_drawdown_strategy import EnhancedDrawdownStrategy
from simulation.core.cache_manager import CacheManager

class StrategyEngine:
    """策略引擎 - T-1选股，T日执行"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # 初始化组件
        self.data_provider = AkShareProvider()
        self.cache_manager = CacheManager()  # 移除config参数
        
        # 初始化策略
        strategy_config = config.get('strategy', {})
        self.strategy = EnhancedDrawdownStrategy(
            lookback_days=strategy_config.get('lookback_days', 90),
            primary_threshold=strategy_config.get('primary_threshold', -0.15),
            fallback_threshold=strategy_config.get('fallback_threshold', -0.08),
            min_primary_ratio=strategy_config.get('min_primary_ratio', 0.6),
            top_n=strategy_config.get('max_positions', 35),
            exclude_northeast=strategy_config.get('exclude_northeast', True)
        )
        
        self.logger.info("策略引擎初始化完成 - T-1选股，T日执行模式")
    
    def prepare_tomorrow_trades(self, analysis_date: str) -> Dict:
        """
        T-1日晚上执行：准备明日交易计划
        
        Args:
            analysis_date: 分析基准日期 (T-1)
            
        Returns:
            Dict: 明日交易计划
        """
        self.logger.info(f"🌙 T-1日策略分析开始: {analysis_date}")
        
        try:
            # 1. 获取股票池（使用缓存的历史数据）
            stock_universe = self._get_cached_stock_universe()
            self.logger.info(f"   股票池: {len(stock_universe)}只股票")
            
            # 2. 获取历史价格数据（使用本地缓存）
            price_history = self._get_cached_price_history(analysis_date)
            self.logger.info(f"   价格历史: {len(price_history)}条记录")
            
            # 3. 执行策略选股
            selected_stocks = self._execute_strategy_selection(
                price_history, stock_universe, analysis_date
            )
            
            # 4. 生成交易计划
            trade_plan = {
                'analysis_date': analysis_date,
                'execution_date': self._get_next_trading_date(analysis_date),
                'selected_stocks': selected_stocks,
                'strategy_info': {
                    'strategy_name': 'enhanced_drawdown',
                    'selection_mode': getattr(self, '_last_selection_mode', 'unknown'),
                    'total_candidates': len(selected_stocks)
                },
                'prepared_at': get_trading_timestamp()
            }
            
            # 5. 保存交易计划
            self._save_trade_plan(trade_plan)
            
            self.logger.info(f"✅ T-1日策略分析完成，选出 {len(selected_stocks)} 只股票")
            return trade_plan
            
        except Exception as e:
            self.logger.error(f"❌ T-1日策略分析失败: {e}")
            raise
    
    def execute_morning_trades(self, execution_date: str) -> Dict:
        """
        T日早上执行：根据交易计划获取实时价格并执行
        
        Args:
            execution_date: 执行日期 (T)
            
        Returns:
            Dict: 执行结果
        """
        self.logger.info(f"🌅 T日交易执行开始: {execution_date}")
        
        try:
            # 1. 加载交易计划
            trade_plan = self._load_trade_plan(execution_date)
            if not trade_plan:
                raise ValueError(f"未找到 {execution_date} 的交易计划")
            
            selected_stocks = trade_plan['selected_stocks']
            self.logger.info(f"   加载交易计划: {len(selected_stocks)} 只股票")
            
            # 2. 获取实时价格（只需要选中股票的价格）
            current_prices = self._get_realtime_prices(selected_stocks, execution_date)
            self.logger.info(f"   获取实时价格: {len(current_prices)} 只股票")
            
            # 3. 构建执行结果
            execution_result = {
                'execution_date': execution_date,
                'selected_stocks': selected_stocks,
                'current_prices': current_prices,
                'strategy_info': trade_plan.get('strategy_info', {}),
                'executed_at': get_trading_timestamp()
            }
            
            self.logger.info(f"✅ T日交易执行完成，{len(selected_stocks)} 只股票待交易")
            return execution_result
            
        except Exception as e:
            self.logger.error(f"❌ T日交易执行失败: {e}")
            raise
        self.data_provider = AkShareProvider()
        self.cache_manager = CacheManager()
        
        # 初始化策略
        strategy_config = config.get("strategy", {})
        strategy_type = strategy_config.get("strategy_type", "enhanced")  # 默认使用增强策略
        
        if strategy_type == "enhanced":
            # 使用生产级增强策略
            self.strategy = EnhancedDrawdownStrategy(
                lookback_days=strategy_config.get("lookback_days", 90),
                primary_threshold=-abs(strategy_config.get("primary_threshold", 0.15)),
                fallback_threshold=-abs(strategy_config.get("fallback_threshold", 0.08)),
                min_primary_ratio=strategy_config.get("min_primary_ratio", 0.6),
                top_n=strategy_config.get("top_n", 35),
                exclude_northeast=strategy_config.get("exclude_northeast", True)
            )
            self.logger.info("已初始化增强策略引擎（生产级）")
        else:
            # 使用原始策略
            self.strategy = DrawdownReversalStrategy(
                lookback_days=strategy_config.get("lookback_days", 126),
                top_n=strategy_config.get("top_n", 35),
                primary_drawdown=-abs(strategy_config.get("decline_threshold", 0.20))
            )
            self.logger.info("已初始化原始策略引擎")
    
    def select_stocks(self, target_date: str) -> List[str]:
        """
        兼容性方法：执行T-1选股并返回股票列表
        
        Args:
            target_date: 目标日期 YYYY-MM-DD
            
        Returns:
            List[str]: 选出的股票代码列表
        """
        try:
            self.logger.info(f"🔄 兼容模式：T-1选股，目标日期: {target_date}")
            
            # 执行T-1选股
            trade_plan = self.prepare_tomorrow_trades(target_date)
            selected_stocks = trade_plan.get('selected_stocks', [])
            
            self.logger.info(f"兼容模式选股完成，选出 {len(selected_stocks)} 只股票")
            return selected_stocks
            
        except Exception as e:
            self.logger.error(f"兼容模式选股失败: {e}")
            return []
            return selected_stocks
            
        except Exception as e:
            self.logger.error(f"策略选股失败: {e}", exc_info=True)
            return []
    
    def _get_stock_universe(self, target_date: str) -> pd.DataFrame:
        """获取股票池"""
        try:
            # 尝试从缓存获取
            cache_key = f"stock_basic_info_{datetime.strptime(target_date, '%Y-%m-%d').strftime('%Y%m%d')}"
            basic_info = self.cache_manager.get_reference_data(cache_key)
            
            if basic_info is None:
                # 缓存未命中，从数据源获取
                self.logger.info("从数据源获取股票基本信息")
                basic_info = self.data_provider.get_basic_info()
                
                if basic_info is not None and not basic_info.empty:
                    # 缓存数据
                    self.cache_manager.cache_reference_data(cache_key, basic_info, ttl_hours=24)
            
            if basic_info is None or basic_info.empty:
                return pd.DataFrame()
            
            # 过滤股票池
            filtered_stocks = self._filter_stock_universe(basic_info, target_date)
            return filtered_stocks
            
        except Exception as e:
            self.logger.error(f"获取股票池失败: {e}")
            return pd.DataFrame()
    
    def _filter_stock_universe(self, basic_info: pd.DataFrame, target_date: str) -> pd.DataFrame:
        """过滤股票池"""
        try:
            original_count = len(basic_info)
            
            # 1. 过滤A股（基本信息中market字段为'A'）
            before_market_filter = len(basic_info)
            basic_info = basic_info[basic_info['market'] == 'A']
            self.logger.info(f"A股过滤: {before_market_filter} -> {len(basic_info)}")
            
            # 2. 暂时跳过上市时间过滤以便测试
            self.logger.info(f"跳过上市时间过滤（测试模式）")
            
            # 3. 过滤ST股票（基本信息中已包含is_st字段）
            if 'is_st' in basic_info.columns:
                before_st_filter = len(basic_info)
                basic_info = basic_info[~basic_info['is_st']]
                self.logger.info(f"ST过滤: {before_st_filter} -> {len(basic_info)}")
            else:
                self.logger.warning("基本信息中缺少is_st字段，跳过ST过滤")
            
            self.logger.info(f"股票池过滤完成: {len(basic_info)}/{original_count}")
            return basic_info
            
        except Exception as e:
            self.logger.error(f"过滤股票池失败: {e}")
            return basic_info
    
    def _get_st_stocks(self, target_date: str) -> List[str]:
        """获取ST股票列表"""
        try:
            # 尝试从缓存获取
            cache_key = f"st_stocks_{datetime.strptime(target_date, '%Y-%m-%d').strftime('%Y%m%d')}"
            st_stocks = self.cache_manager.get_reference_data(cache_key)
            
            if st_stocks is None:
                # 缓存未命中，从数据源获取
                self.logger.info("从数据源获取ST股票列表")
                st_stocks = self.data_provider.get_st_stocks()
                
                if st_stocks is not None:
                    # 缓存数据
                    self.cache_manager.cache_reference_data(cache_key, st_stocks, ttl_hours=24)
            
            return st_stocks if st_stocks is not None else []
            
        except Exception as e:
            self.logger.error(f"获取ST股票列表失败: {e}")
            return []
    
    def _get_price_history(self, stock_universe: pd.DataFrame, target_date: str) -> pd.DataFrame:
        """获取价格历史数据"""
        try:
            # 计算需要的历史数据范围
            target_dt = datetime.strptime(target_date, '%Y-%m-%d')
            lookback_months = self.config.get("strategy", {}).get("lookback_months", 6)
            start_date = target_dt - timedelta(days=lookback_months * 30 + 30)  # 多取一些数据
            start_date_str = start_date.strftime('%Y-%m-%d')
            
            # 获取股票代码列表
            # 使用symbol字段而不是ts_code（根据我们的数据结构）
            if 'symbol' in stock_universe.columns:
                stock_codes = stock_universe['symbol'].tolist()
            elif 'ts_code' in stock_universe.columns:
                stock_codes = stock_universe['ts_code'].tolist()
            else:
                self.logger.error("股票池数据中缺少股票代码字段")
                return pd.DataFrame()
            
            # 尝试从缓存获取
            cache_key = f"price_history_{start_date_str}_{target_date}"
            price_history = self.cache_manager.get_market_data(cache_key)
            
            if price_history is None:
                # 缓存未命中，从数据源获取
                self.logger.info(f"从数据源获取价格历史数据: {start_date_str} 到 {target_date}")
                
                # 分批获取数据（避免API限制）
                batch_size = 50
                all_price_data = []
                
                for i in range(0, len(stock_codes), batch_size):
                    batch_codes = stock_codes[i:i+batch_size]
                    
                    try:
                        batch_data = self.data_provider.get_daily_price(
                            batch_codes, start_date_str, target_date
                        )
                        
                        if batch_data is not None and not batch_data.empty:
                            all_price_data.append(batch_data)
                        
                        # 避免请求过频
                        import time
                        time.sleep(0.1)
                        
                    except Exception as e:
                        self.logger.warning(f"获取批次 {i//batch_size} 价格数据失败: {e}")
                        continue
                
                if all_price_data:
                    price_history = pd.concat(all_price_data, ignore_index=True)
                    
                    # 缓存数据
                    self.cache_manager.cache_market_data(cache_key, price_history, ttl_hours=6)
                else:
                    price_history = pd.DataFrame()
            
            if price_history.empty:
                self.logger.error("获取价格历史数据失败")
                return pd.DataFrame()
            
            self.logger.info(f"价格历史数据获取完成: {len(price_history)} 条记录")
            return price_history
            
        except Exception as e:
            self.logger.error(f"获取价格历史数据失败: {e}")
            return pd.DataFrame()
    
    def validate_strategy_result(self, selected_stocks: List[str], target_date: str) -> bool:
        """验证策略结果"""
        try:
            if not selected_stocks:
                return False
            
            # 检查股票数量
            target_count = self.config.get("stock_count", 35)
            if len(selected_stocks) > target_count * 1.5:  # 允许一定的超额
                self.logger.warning(f"选股数量过多: {len(selected_stocks)} > {target_count}")
                return False
            
            # 检查股票代码格式
            for stock_code in selected_stocks:
                if not isinstance(stock_code, str) or len(stock_code) < 8:
                    self.logger.warning(f"股票代码格式异常: {stock_code}")
                    return False
            
            # ST检查已在选股阶段完成，此处不再重复检查
            
            return True
            
        except Exception as e:
            self.logger.error(f"验证策略结果失败: {e}")
            return False
    
    def _execute_strategy(self, price_data: pd.DataFrame, basic_info: pd.DataFrame, target_date: str) -> List[str]:
        """执行策略选股"""
        try:
            from datetime import date
            target_date_obj = datetime.strptime(target_date, '%Y-%m-%d').date()
            strategy_config = self.config.get("strategy", {})
            strategy_type = strategy_config.get("strategy_type", "enhanced")
            
            if strategy_type == "enhanced":
                # 使用增强策略
                self.logger.info("执行增强策略选股")
                
                # 计算选股评分
                scores = self.strategy.calculate_enhanced_scores(price_data, target_date_obj)
                if not scores:
                    self.logger.warning("增强策略计算评分为空")
                    return []
                
                # 执行选股逻辑
                selected_stocks, selection_mode, primary_count, total_count = self.strategy.select_enhanced_stocks(scores, basic_info)
                
                self.logger.info(f"增强策略完成: 模式={selection_mode}, 主要候选={primary_count}, 总候选={total_count}")
                return selected_stocks
                
            else:
                # 使用原始策略
                self.logger.info("执行原始策略选股")
                
                # 原始策略的选股逻辑
                selected_stocks = self.strategy.select(
                    price_data=price_data,
                    basic_info=basic_info,
                    current_date=target_date_obj
                )
                
                return selected_stocks if selected_stocks else []
                
        except Exception as e:
            self.logger.error(f"执行策略失败: {e}", exc_info=True)
            return []
    
    # T-1选股，T日执行的支持方法
    
    def _get_cached_stock_universe(self) -> pd.DataFrame:
        """获取缓存的股票池（CSI800等）"""
        try:
            # 使用本地缓存的basic_info数据
            basic_file = Path("data/clean/basic_info_5year.parquet")
            if basic_file.exists():
                basic_df = pd.read_parquet(basic_file)
                self.logger.info(f"从缓存加载股票池: {len(basic_df)} 只股票")
                return basic_df
            else:
                self.logger.warning("缓存文件不存在，使用空股票池")
                return pd.DataFrame()
        except Exception as e:
            self.logger.error(f"获取缓存股票池失败: {e}")
            return pd.DataFrame()
    
    def _get_cached_price_history(self, analysis_date: str) -> pd.DataFrame:
        """获取缓存的价格历史数据"""
        try:
            # 使用本地缓存的price_history数据
            price_file = Path("data/clean/price_history_5year.parquet")
            if price_file.exists():
                price_df = pd.read_parquet(price_file)
                
                # 过滤到分析日期
                price_df['date'] = pd.to_datetime(price_df['date'])
                analysis_dt = pd.to_datetime(analysis_date)
                price_df = price_df[price_df['date'] <= analysis_dt]
                
                self.logger.info(f"从缓存加载价格历史: {len(price_df)} 条记录")
                return price_df
            else:
                self.logger.warning("价格历史缓存文件不存在")
                return pd.DataFrame()
        except Exception as e:
            self.logger.error(f"获取缓存价格历史失败: {e}")
            return pd.DataFrame()
    
    def _execute_strategy_selection(self, price_history: pd.DataFrame, 
                                   stock_universe: pd.DataFrame, 
                                   analysis_date: str) -> List[str]:
        """执行策略选股计算"""
        try:
            from datetime import datetime
            analysis_dt = datetime.strptime(analysis_date, '%Y-%m-%d').date()
            
            # 计算评分
            scores = self.strategy.calculate_enhanced_scores(price_history, analysis_dt)
            
            # 执行选股
            selected_stocks, selection_mode, primary_count, total_count = \
                self.strategy.select_enhanced_stocks(scores, stock_universe)
            
            # 保存选股模式信息
            self._last_selection_mode = selection_mode
            
            self.logger.info(f"策略选股: {selection_mode}模式, {len(selected_stocks)}只股票")
            return selected_stocks
            
        except Exception as e:
            self.logger.error(f"策略选股计算失败: {e}")
            return []
    
    def _get_next_trading_date(self, current_date: str) -> str:
        """获取下一个交易日（简化实现）"""
        from datetime import datetime, timedelta
        dt = datetime.strptime(current_date, '%Y-%m-%d')
        next_dt = dt + timedelta(days=1)
        
        # 简单跳过周末
        while next_dt.weekday() > 4:  # 5=周六, 6=周日
            next_dt += timedelta(days=1)
        
        return next_dt.strftime('%Y-%m-%d')
    
    def _save_trade_plan(self, trade_plan: Dict):
        """保存交易计划"""
        try:
            plan_dir = Path("data/simulation/instances/default/trade_plans")
            plan_dir.mkdir(parents=True, exist_ok=True)
            
            execution_date = trade_plan['execution_date']
            plan_file = plan_dir / f"{execution_date}_plan.json"
            
            with open(plan_file, 'w', encoding='utf-8') as f:
                json.dump(trade_plan, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"交易计划已保存: {plan_file}")
            
        except Exception as e:
            self.logger.error(f"保存交易计划失败: {e}")
    
    def _load_trade_plan(self, execution_date: str) -> Optional[Dict]:
        """加载交易计划"""
        try:
            plan_file = Path(f"data/simulation/instances/default/trade_plans/{execution_date}_plan.json")
            
            if plan_file.exists():
                with open(plan_file, 'r', encoding='utf-8') as f:
                    trade_plan = json.load(f)
                self.logger.info(f"交易计划已加载: {plan_file}")
                return trade_plan
            else:
                self.logger.warning(f"交易计划文件不存在: {plan_file}")
                return None
                
        except Exception as e:
            self.logger.error(f"加载交易计划失败: {e}")
            return None
    
    def _get_realtime_prices(self, symbols: List[str], execution_date: str) -> Dict[str, float]:
        """获取实时价格（简化实现）"""
        try:
            # 简化实现：使用最新收盘价作为实时价格
            price_file = Path("data/clean/price_history_5year.parquet")
            if not price_file.exists():
                return {}
            
            price_df = pd.read_parquet(price_file)
            price_df['date'] = pd.to_datetime(price_df['date'])
            
            # 获取最新价格
            latest_prices = {}
            for symbol in symbols:
                symbol_data = price_df[price_df['symbol'] == symbol]
                if not symbol_data.empty:
                    latest_price = symbol_data.iloc[-1]['close']
                    latest_prices[symbol] = float(latest_price)
            
            self.logger.info(f"获取实时价格: {len(latest_prices)} 只股票")
            return latest_prices
            
        except Exception as e:
            self.logger.error(f"获取实时价格失败: {e}")
            return {}