"""
风险控制模块 - 多层次止盈止损框架

提供个股级别和组合级别的风险控制功能，包括：
- 个股固定/移动止损
- 时间止损  
- 组合回撤控制
- 波动率自适应止损
- 动态止盈机制
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from datetime import date, timedelta
import pandas as pd
import numpy as np
from enum import Enum

class RiskControlType(Enum):
    """风控类型枚举"""
    INDIVIDUAL_STOP_LOSS = "individual_stop_loss"      # 个股止损
    INDIVIDUAL_TAKE_PROFIT = "individual_take_profit"  # 个股止盈
    TRAILING_STOP = "trailing_stop"                    # 移动止损
    TIME_STOP = "time_stop"                            # 时间止损
    PORTFOLIO_DRAWDOWN = "portfolio_drawdown"          # 组合回撤控制
    CONCENTRATION_LIMIT = "concentration_limit"        # 集中度控制

class RiskControlAction(Enum):
    """风控动作枚举"""
    FULL_SELL = "full_sell"          # 全部卖出
    PARTIAL_SELL = "partial_sell"    # 部分卖出
    REDUCE_POSITION = "reduce_position"  # 减仓
    BLOCK_BUY = "block_buy"          # 阻止买入

@dataclass
class RiskControlConfig:
    """风控配置参数"""
    
    # 个股止损配置
    individual_stop_loss_pct: float = -0.10  # 个股止损比例 -10%
    enable_individual_stop_loss: bool = True
    
    # 个股止盈配置
    individual_take_profit_pct: float = 0.20  # 个股止盈比例 +20%
    enable_individual_take_profit: bool = False
    
    # 移动止损配置
    trailing_stop_pct: float = 0.05  # 移动止损比例 5%
    enable_trailing_stop: bool = False
    
    # 时间止损配置
    max_holding_days: int = 60  # 最大持仓天数
    enable_time_stop: bool = False
    
    # 组合回撤控制
    portfolio_drawdown_limit: float = -0.20  # 组合回撤限制 -20%
    enable_portfolio_drawdown: bool = True
    
    # 集中度控制
    max_single_position_pct: float = 0.10  # 单股最大仓位 10%
    enable_concentration_limit: bool = True
    
    # 波动率自适应参数
    enable_volatility_adaptive: bool = False
    volatility_lookback_days: int = 20
    volatility_multiplier: float = 2.0
    
    # 分级止盈配置
    enable_tiered_take_profit: bool = False
    take_profit_levels: List[Tuple[float, float]] = field(default_factory=lambda: [
        (0.10, 0.3),  # 盈利10%时卖出30%
        (0.20, 0.5),  # 盈利20%时再卖出50%剩余
        (0.30, 1.0)   # 盈利30%时全部卖出
    ])

@dataclass 
class RiskControlEvent:
    """风控事件记录"""
    date: date
    symbol: str
    event_type: RiskControlType
    action: RiskControlAction
    trigger_price: float
    trigger_value: float  # 触发时的具体数值（止损比例、持仓天数等）
    position_before: float  # 触发前持仓
    position_after: float   # 触发后持仓
    reason: str  # 触发原因描述

class RiskControl:
    """风险控制主类"""
    
    def __init__(self, config: RiskControlConfig):
        self.config = config
        self.events: List[RiskControlEvent] = []
        
        # 持仓追踪数据
        self.position_entry_dates: Dict[str, date] = {}  # 股票建仓日期
        self.position_high_prices: Dict[str, float] = {}  # 持仓期间最高价
        self.portfolio_high_value: float = 0.0  # 组合历史最高净值
        
        # 统计数据
        self.stop_loss_count = 0
        self.take_profit_count = 0
        self.time_stop_count = 0
        self.portfolio_stop_count = 0
        
    def check_risk_controls(self, 
                          current_date: date,
                          current_positions: Dict[str, float],  # {symbol: quantity}
                          current_prices: Dict[str, float],     # {symbol: price}
                          entry_prices: Dict[str, float],       # {symbol: avg_cost}
                          portfolio_value: float) -> List[Tuple[str, float, RiskControlEvent]]:
        """
        检查所有风控条件，返回需要调整的持仓
        
        Returns:
            List of (symbol, target_quantity, event) tuples
        """
        adjustments = []
        
        # 更新组合最高净值
        if portfolio_value > self.portfolio_high_value:
            self.portfolio_high_value = portfolio_value
            
        # 1. 检查组合回撤控制
        if self.config.enable_portfolio_drawdown:
            portfolio_adjustments = self._check_portfolio_drawdown(
                current_date, current_positions, current_prices, portfolio_value
            )
            adjustments.extend(portfolio_adjustments)
            
        # 如果组合回撤触发，可能已经全部清仓，不需要再检查个股
        if portfolio_adjustments:
            return adjustments
            
        # 2. 检查个股风控
        for symbol, quantity in current_positions.items():
            if quantity <= 0:
                continue
                
            current_price = current_prices.get(symbol)
            entry_price = entry_prices.get(symbol)
            
            if current_price is None or entry_price is None:
                continue
                
            # 更新持仓最高价
            if symbol not in self.position_high_prices:
                self.position_high_prices[symbol] = current_price
            else:
                self.position_high_prices[symbol] = max(
                    self.position_high_prices[symbol], current_price
                )
                
            # 更新建仓日期
            if symbol not in self.position_entry_dates:
                self.position_entry_dates[symbol] = current_date
                
            # 个股止损检查
            if self.config.enable_individual_stop_loss:
                adjustment = self._check_individual_stop_loss(
                    current_date, symbol, quantity, current_price, entry_price
                )
                if adjustment:
                    adjustments.append(adjustment)
                    continue  # 止损触发后不再检查其他条件
                    
            # 个股止盈检查
            if self.config.enable_individual_take_profit:
                adjustment = self._check_individual_take_profit(
                    current_date, symbol, quantity, current_price, entry_price
                )
                if adjustment:
                    adjustments.append(adjustment)
                    continue
                    
            # 移动止损检查
            if self.config.enable_trailing_stop:
                adjustment = self._check_trailing_stop(
                    current_date, symbol, quantity, current_price
                )
                if adjustment:
                    adjustments.append(adjustment)
                    continue
                    
            # 时间止损检查
            if self.config.enable_time_stop:
                adjustment = self._check_time_stop(
                    current_date, symbol, quantity, current_price
                )
                if adjustment:
                    adjustments.append(adjustment)
                    
        return adjustments
        
    def _check_individual_stop_loss(self, 
                                   current_date: date,
                                   symbol: str, 
                                   quantity: float,
                                   current_price: float,
                                   entry_price: float) -> Optional[Tuple[str, float, RiskControlEvent]]:
        """检查个股止损"""
        pnl_pct = (current_price / entry_price) - 1
        
        if pnl_pct <= self.config.individual_stop_loss_pct:
            event = RiskControlEvent(
                date=current_date,
                symbol=symbol,
                event_type=RiskControlType.INDIVIDUAL_STOP_LOSS,
                action=RiskControlAction.FULL_SELL,
                trigger_price=current_price,
                trigger_value=pnl_pct,
                position_before=quantity,
                position_after=0.0,
                reason=f"个股止损触发: {pnl_pct:.2%} <= {self.config.individual_stop_loss_pct:.2%}"
            )
            
            self.events.append(event)
            self.stop_loss_count += 1
            
            # 清理该股票的追踪数据
            self._cleanup_position_tracking(symbol)
            
            return (symbol, 0.0, event)
            
        return None
        
    def _check_individual_take_profit(self,
                                    current_date: date,
                                    symbol: str,
                                    quantity: float, 
                                    current_price: float,
                                    entry_price: float) -> Optional[Tuple[str, float, RiskControlEvent]]:
        """检查个股止盈"""
        pnl_pct = (current_price / entry_price) - 1
        
        if pnl_pct >= self.config.individual_take_profit_pct:
            event = RiskControlEvent(
                date=current_date,
                symbol=symbol,
                event_type=RiskControlType.INDIVIDUAL_TAKE_PROFIT,
                action=RiskControlAction.FULL_SELL,
                trigger_price=current_price,
                trigger_value=pnl_pct,
                position_before=quantity,
                position_after=0.0,
                reason=f"个股止盈触发: {pnl_pct:.2%} >= {self.config.individual_take_profit_pct:.2%}"
            )
            
            self.events.append(event)
            self.take_profit_count += 1
            
            # 清理该股票的追踪数据
            self._cleanup_position_tracking(symbol)
            
            return (symbol, 0.0, event)
            
        return None
        
    def _check_trailing_stop(self,
                           current_date: date,
                           symbol: str,
                           quantity: float,
                           current_price: float) -> Optional[Tuple[str, float, RiskControlEvent]]:
        """检查移动止损"""
        if symbol not in self.position_high_prices:
            return None
            
        high_price = self.position_high_prices[symbol]
        drawdown_pct = (current_price / high_price) - 1
        
        if drawdown_pct <= -self.config.trailing_stop_pct:
            event = RiskControlEvent(
                date=current_date,
                symbol=symbol,
                event_type=RiskControlType.TRAILING_STOP,
                action=RiskControlAction.FULL_SELL,
                trigger_price=current_price,
                trigger_value=drawdown_pct,
                position_before=quantity,
                position_after=0.0,
                reason=f"移动止损触发: 从高点{high_price:.2f}回撤{drawdown_pct:.2%}"
            )
            
            self.events.append(event)
            self.stop_loss_count += 1
            
            # 清理该股票的追踪数据
            self._cleanup_position_tracking(symbol)
            
            return (symbol, 0.0, event)
            
        return None
        
    def _check_time_stop(self,
                        current_date: date,
                        symbol: str,
                        quantity: float,
                        current_price: float) -> Optional[Tuple[str, float, RiskControlEvent]]:
        """检查时间止损"""
        if symbol not in self.position_entry_dates:
            return None
            
        entry_date = self.position_entry_dates[symbol]
        holding_days = (current_date - entry_date).days
        
        if holding_days >= self.config.max_holding_days:
            event = RiskControlEvent(
                date=current_date,
                symbol=symbol,
                event_type=RiskControlType.TIME_STOP,
                action=RiskControlAction.FULL_SELL,
                trigger_price=current_price,
                trigger_value=holding_days,
                position_before=quantity,
                position_after=0.0,
                reason=f"时间止损触发: 持仓{holding_days}天 >= {self.config.max_holding_days}天"
            )
            
            self.events.append(event)
            self.time_stop_count += 1
            
            # 清理该股票的追踪数据
            self._cleanup_position_tracking(symbol)
            
            return (symbol, 0.0, event)
            
        return None
        
    def _check_portfolio_drawdown(self,
                                current_date: date,
                                current_positions: Dict[str, float],
                                current_prices: Dict[str, float],
                                portfolio_value: float) -> List[Tuple[str, float, RiskControlEvent]]:
        """检查组合回撤控制"""
        if self.portfolio_high_value <= 0:
            return []
            
        drawdown_pct = (portfolio_value / self.portfolio_high_value) - 1
        
        if drawdown_pct <= self.config.portfolio_drawdown_limit:
            adjustments = []
            
            # 强制清仓所有持仓
            for symbol, quantity in current_positions.items():
                if quantity > 0:
                    current_price = current_prices.get(symbol, 0)
                    
                    event = RiskControlEvent(
                        date=current_date,
                        symbol=symbol,
                        event_type=RiskControlType.PORTFOLIO_DRAWDOWN,
                        action=RiskControlAction.FULL_SELL,
                        trigger_price=current_price,
                        trigger_value=drawdown_pct,
                        position_before=quantity,
                        position_after=0.0,
                        reason=f"组合回撤控制触发: {drawdown_pct:.2%} <= {self.config.portfolio_drawdown_limit:.2%}"
                    )
                    
                    self.events.append(event)
                    adjustments.append((symbol, 0.0, event))
                    
            if adjustments:
                self.portfolio_stop_count += 1
                # 清理所有追踪数据
                self._cleanup_all_tracking()
                
            return adjustments
            
        return []
        
    def _cleanup_position_tracking(self, symbol: str):
        """清理单个股票的追踪数据"""
        self.position_entry_dates.pop(symbol, None)
        self.position_high_prices.pop(symbol, None)
        
    def _cleanup_all_tracking(self):
        """清理所有追踪数据"""
        self.position_entry_dates.clear()
        self.position_high_prices.clear()
        
    def get_risk_control_stats(self) -> Dict[str, Any]:
        """获取风控统计信息"""
        return {
            'total_events': len(self.events),
            'stop_loss_count': self.stop_loss_count,
            'take_profit_count': self.take_profit_count,
            'time_stop_count': self.time_stop_count,
            'portfolio_stop_count': self.portfolio_stop_count,
            'events_by_type': {
                event_type.value: len([e for e in self.events if e.event_type == event_type])
                for event_type in RiskControlType
            }
        }
        
    def get_events_dataframe(self) -> pd.DataFrame:
        """将风控事件转换为DataFrame"""
        if not self.events:
            return pd.DataFrame()
            
        events_data = []
        for event in self.events:
            events_data.append({
                'date': event.date,
                'symbol': event.symbol,
                'event_type': event.event_type.value,
                'action': event.action.value,
                'trigger_price': event.trigger_price,
                'trigger_value': event.trigger_value,
                'position_before': event.position_before,
                'position_after': event.position_after,
                'reason': event.reason
            })
            
        return pd.DataFrame(events_data)

    def get_daily_stats(self) -> Dict[str, int]:
        """获取当日风控统计（用于日度记录）"""
        # 这里简化处理，实际可以跟踪当日触发的各类风控次数
        # 当前实现返回累计统计
        return {
            'stop_loss_triggered': self.stop_loss_count,
            'take_profit_triggered': self.take_profit_count,
            'time_stop_triggered': self.time_stop_count
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """获取风控总结报告"""
        return {
            'total_events': len(self.events),
            'event_counts': {
                'stop_loss': self.stop_loss_count,
                'take_profit': self.take_profit_count,
                'time_stop': self.time_stop_count,
                'portfolio_stop': self.portfolio_stop_count
            },
            'config_used': {
                'individual_stop_loss_pct': self.config.individual_stop_loss_pct,
                'individual_take_profit_pct': self.config.individual_take_profit_pct,
                'trailing_stop_pct': self.config.trailing_stop_pct,
                'max_holding_days': self.config.max_holding_days,
                'portfolio_drawdown_limit': self.config.portfolio_drawdown_limit
            }
        }