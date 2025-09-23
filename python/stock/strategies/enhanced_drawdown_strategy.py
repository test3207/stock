"""
增强版跌幅逆向选股策略 - 生产友好版本
从主文件中提取的策略类，遵循项目架构设计
"""

from __future__ import annotations
from datetime import date, timedelta
from typing import Dict, List, Tuple
import pandas as pd
import numpy as np


class ProductionSTFilter:
    """
    生产环境ST过滤器
    设计目标：在实盘交易中可靠地过滤ST股票
    """
    
    def __init__(self, use_conservative_mode=True):
        self.conservative_mode = use_conservative_mode
        self.st_patterns = ['ST', '*ST', 'S*ST', 'SST']
        
    def is_st_by_symbol(self, symbol: str) -> bool:
        """基于股票代码的快速ST判断 - 实盘可用"""
        if not symbol:
            return True
        
        symbol_upper = symbol.upper()
        return any(pattern in symbol_upper for pattern in self.st_patterns)
    
    def is_st_by_name(self, stock_name: str) -> bool:
        """基于股票名称的ST判断 - 需要实时数据"""
        if not stock_name:
            return False
        
        return any(pattern in stock_name for pattern in self.st_patterns + ['退市'])
    
    def create_production_filter(self, basic_df: pd.DataFrame, backup_mode='symbol_only') -> pd.DataFrame:
        """
        创建生产环境的ST过滤器
        backup_mode: 当数据不完整时的处理方式
        - 'symbol_only': 仅基于代码判断
        - 'conservative': 疑似的一律排除
        - 'permissive': 疑似的允许通过
        """
        
        print(f"🔍 生产环境ST过滤 (模式: {backup_mode})...")
        
        # 创建过滤后的DataFrame
        filtered_df = basic_df.copy()
        
        # 基础过滤：确保必要字段存在
        primary_filter = (
            filtered_df['symbol'].notna() & 
            (filtered_df['symbol'] != '')
        )
        
        # 检查是否有is_st列（数据中已包含ST信息）
        if 'is_st' in filtered_df.columns:
            # 直接使用数据中的is_st标识
            st_filter = ~filtered_df['is_st']
            print(f"   使用数据中的is_st字段进行过滤")
        else:
            # 代码层面过滤（快速且可靠）
            st_filter = ~filtered_df['symbol'].apply(self.is_st_by_symbol)
            print(f"   使用代码模式识别进行ST过滤")
        
        # 检查是否有name列
        if 'name' in filtered_df.columns:
            # 名称层面过滤（更准确但需要数据）
            name_filter = ~filtered_df['name'].apply(self.is_st_by_name)
            
            # 根据模式组合过滤条件
            if backup_mode == 'symbol_only':
                final_filter = primary_filter & st_filter
            elif backup_mode == 'conservative':
                final_filter = primary_filter & st_filter & name_filter
            else:  # permissive
                final_filter = primary_filter | st_filter
        else:
            # 没有name列时，只使用基础过滤和ST过滤
            final_filter = primary_filter & st_filter
            print(f"   数据中无name列，仅使用symbol和is_st字段过滤")
        
        filtered_result = filtered_df[final_filter]
        
        print(f"✓ ST过滤完成: {len(filtered_result)}/{len(filtered_df)}只股票可交易 ({len(filtered_result)/len(filtered_df):.1%})")
        
        return filtered_result


class EnhancedDrawdownStrategy:
    """增强版跌幅逆向选股策略 - 生产友好"""
    
    def __init__(self, lookback_days=90, primary_threshold=-0.30, 
                 fallback_threshold=-0.15, min_primary_ratio=0.6, top_n=35,
                 exclude_northeast=True):
        self.lookback_days = lookback_days
        self.primary_threshold = primary_threshold
        self.fallback_threshold = fallback_threshold
        self.min_primary_ratio = min_primary_ratio
        self.top_n = top_n
        self.exclude_northeast = exclude_northeast
        self.st_filter = ProductionSTFilter(use_conservative_mode=True)
        
        # 东北地区股票代码（简化版，主要代表性公司）
        self.northeast_codes = {
            # 辽宁省代表性公司
            '000410', '000709', '000723', '000726', '000758', '000767', '000778',
            '000798', '000802', '000806', '000850', '000851', '000852', '000878',
            '000898', '000930', '000962', '000969', '600507', '600517', '600525',
            '600546', '600558', '600581', '600585', '600587', '600592', '600594',
            '600606', '600616', '600623', '600631', '600647', '600679', '600683',
            '600688', '600726', '600739', '600747', '600753', '600759', '600773',
            
            # 吉林省代表性公司  
            '000547', '000557', '000623', '000661', '000687', '000698', '000700',
            '000718', '000780', '000797', '000812', '000885', '000903', '000949',
            '600095', '600128', '600252', '600291', '600295', '600303', '600352',
            '600365', '600375', '600403', '600455', '600499', '600500', '600520',
            
            # 黑龙江省代表性公司
            '000090', '000408', '000531', '000554', '000610', '000620', '000626',
            '000627', '000635', '000650', '000652', '000682', '000703', '000712',
            '000717', '000737', '000758', '000816', '000833', '000875', '000902',
            '600108', '600119', '600123', '600127', '600135', '600153', '600157',
            '600165', '600189', '600201', '600217', '600226', '600240', '600248'
        }
    
    def is_northeast_company(self, symbol: str) -> bool:
        """判断是否为东北地区公司"""
        if not symbol or len(symbol) < 6:
            return False
        
        # 提取6位代码
        code = symbol[:6]
        return code in self.northeast_codes
        
    def calculate_enhanced_scores(self, price_df: pd.DataFrame, current_date: date) -> Dict[str, dict]:
        """计算增强选股评分"""
        current_date_dt = pd.to_datetime(current_date)
        target_date = current_date_dt - timedelta(days=int(self.lookback_days * 1.5))
        
        scores = {}
        
        for symbol, group in price_df.groupby('symbol'):
            group = group.sort_values('date')
            group_dates = pd.to_datetime(group['date'])
            
            # 当前数据
            current_mask = group_dates <= current_date_dt
            if not current_mask.any():
                continue
            current_data = group[current_mask].iloc[-1]
            current_price = current_data['close']
            
            # 历史数据
            past_mask = group_dates <= target_date
            if not past_mask.any():
                continue
            past_price = group[past_mask]['close'].iloc[-1]
            
            # 基础跌幅
            drawdown = (current_price / past_price) - 1
            
            # 近期成交量平均 (流动性筛选)
            recent_data = group[group_dates >= (current_date_dt - timedelta(days=20))]
            if len(recent_data) < 5:
                continue
            avg_volume = recent_data['volume'].mean()
            
            # 市值估算
            market_proxy = current_price * avg_volume
            
            scores[symbol] = {
                'drawdown': drawdown,
                'avg_volume': avg_volume,
                'market_proxy': market_proxy,
                'current_price': current_price
            }
            
        return scores
    
    def select_enhanced_stocks(self, scores: Dict[str, dict], basic_df: pd.DataFrame) -> Tuple[List[str], str, int, int]:
        """
        增强选股逻辑 - 使用生产级ST过滤
        """
        # 使用生产级ST过滤器
        filtered_basic_df = self.st_filter.create_production_filter(basic_df, backup_mode='conservative')
        non_st_symbols = set(filtered_basic_df['symbol'])
        
        print(f"   ST过滤后可用股票池: {len(non_st_symbols)}只")
        
        # 过滤低流动性和异常股票
        volume_threshold = np.percentile([s['avg_volume'] for s in scores.values()], 20)
        market_threshold = np.percentile([s['market_proxy'] for s in scores.values()], 10)
        price_threshold = np.percentile([s['current_price'] for s in scores.values()], 90)
        
        # 应用多重过滤条件
        valid_stocks = {}
        northeast_excluded = 0
        
        for sym, data in scores.items():
            # ST过滤
            if sym not in non_st_symbols:
                continue
                
            # 流动性过滤
            if (data['avg_volume'] < volume_threshold or
                data['market_proxy'] < market_threshold or 
                data['current_price'] > price_threshold):
                continue
                
            # 东北地区过滤
            if self.exclude_northeast and self.is_northeast_company(sym):
                northeast_excluded += 1
                continue
                
            valid_stocks[sym] = data
        
        if northeast_excluded > 0:
            print(f"   排除东北地区公司: {northeast_excluded}只")
        print(f"   流动性等过滤后: {len(valid_stocks)}只股票")
        
        # 主要候选：跌幅达标
        primary_candidates = {
            sym: data for sym, data in valid_stocks.items()
            if data['drawdown'] <= self.primary_threshold
        }
        
        # 判断是否使用备用阈值
        min_primary_count = int(self.top_n * self.min_primary_ratio)
        
        if len(primary_candidates) < min_primary_count:
            fallback_candidates = {
                sym: data for sym, data in valid_stocks.items()
                if data['drawdown'] <= self.fallback_threshold
            }
            candidates = fallback_candidates
            selection_mode = "fallback"
        else:
            candidates = primary_candidates
            selection_mode = "primary"
        
        # 按综合评分排序
        def score_function(item):
            sym, data = item
            drawdown_score = data['drawdown']
            liquidity_bonus = min(0.02, data['avg_volume'] / 1e8)
            return drawdown_score + liquidity_bonus
        
        sorted_candidates = sorted(candidates.items(), key=score_function)
        selected = [sym for sym, _ in sorted_candidates[:self.top_n]]
        
        print(f"   最终选中: {len(selected)}只股票")
        
        return selected, selection_mode, len(primary_candidates), len(candidates)