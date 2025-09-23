#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
风控引擎
负责监控投资组合风险，执行止损止盈逻辑
"""

import sys
import logging
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

# 添加项目根路径
sys.path.append(str(Path(__file__).parent.parent.parent))

from python.stock.data.akshare_provider import AkShareProvider
from simulation.core.cache_manager import CacheManager

class RiskEngine:
    """风控引擎"""
    
    def __init__(self, config: Dict, cache_manager: CacheManager):
        self.config = config
        self.cache_manager = cache_manager
        self.logger = logging.getLogger(__name__)
        
        # 初始化数据提供者
        self.data_provider = AkShareProvider()
        
        # 风控参数
        risk_config = config.get("risk_control", {})
        self.stop_loss_threshold = risk_config.get("stop_loss_threshold", -0.15)  # -15%
        self.take_profit_threshold = risk_config.get("take_profit_threshold", 0.20)  # +20%
        self.max_position_pct = risk_config.get("max_position_pct", 0.05)  # 最大单股5%
        self.check_interval_minutes = risk_config.get("check_interval_minutes", 5)  # 5分钟检查
    
    def check_portfolio_risk(self, portfolio_state: Dict, risk_control_state: Dict) -> List[Dict]:
        """
        检查投资组合风险
        
        Args:
            portfolio_state: 投资组合状态
            risk_control_state: 风控状态
            
        Returns:
            List[Dict]: 风控触发列表
        """
        try:
            positions = portfolio_state.get("positions", {})
            if not positions:
                return []
            
            self.logger.info(f"开始风控检查，持仓数量: {len(positions)}")
            
            # 获取已触发的股票列表
            triggered_stocks = set(risk_control_state.get("triggered_stocks", []))
            
            # 获取当前价格
            stock_codes = list(positions.keys())
            current_prices = self._get_current_prices(stock_codes)
            
            if current_prices.empty:
                self.logger.warning("无法获取当前价格，跳过风控检查")
                return []
            
            risk_triggers = []
            
            # 检查每个持仓
            for stock_code, position in positions.items():
                if stock_code in triggered_stocks:
                    continue  # 已触发过的股票跳过
                
                if stock_code not in current_prices.index:
                    self.logger.warning(f"无法获取 {stock_code} 的价格数据")
                    continue
                
                # 计算收益率
                cost_price = position["cost"]
                current_price = current_prices.loc[stock_code, 'close']
                return_rate = (current_price - cost_price) / cost_price
                
                # 检查止损
                if return_rate <= self.stop_loss_threshold:
                    risk_triggers.append({
                        "stock_code": stock_code,
                        "type": "stop_loss",
                        "current_price": current_price,
                        "cost_price": cost_price,
                        "return_rate": return_rate,
                        "threshold": self.stop_loss_threshold,
                        "reason": f"触发止损: {return_rate:.2%} <= {self.stop_loss_threshold:.2%}",
                        "trigger_time": datetime.now().isoformat()
                    })
                
                # 检查止盈
                elif return_rate >= self.take_profit_threshold:
                    risk_triggers.append({
                        "stock_code": stock_code,
                        "type": "take_profit", 
                        "current_price": current_price,
                        "cost_price": cost_price,
                        "return_rate": return_rate,
                        "threshold": self.take_profit_threshold,
                        "reason": f"触发止盈: {return_rate:.2%} >= {self.take_profit_threshold:.2%}",
                        "trigger_time": datetime.now().isoformat()
                    })
            
            if risk_triggers:
                self.logger.info(f"检测到 {len(risk_triggers)} 个风控触发")
                for trigger in risk_triggers:
                    self.logger.info(f"  {trigger['stock_code']}: {trigger['reason']}")
            
            return risk_triggers
            
        except Exception as e:
            self.logger.error(f"风控检查失败: {e}")
            return []
    
    def check_position_concentration(self, portfolio_state: Dict) -> List[Dict]:
        """
        检查持仓集中度风险
        
        Args:
            portfolio_state: 投资组合状态
            
        Returns:
            List[Dict]: 集中度风险警告
        """
        try:
            positions = portfolio_state.get("positions", {})
            total_value = portfolio_state.get("total_value", 0.0)
            
            if not positions or total_value <= 0:
                return []
            
            # 获取当前价格
            stock_codes = list(positions.keys())
            current_prices = self._get_current_prices(stock_codes)
            
            concentration_warnings = []
            
            for stock_code, position in positions.items():
                if stock_code in current_prices.index:
                    current_price = current_prices.loc[stock_code, 'close']
                    position_value = position["shares"] * current_price
                    position_pct = position_value / total_value
                    
                    if position_pct > self.max_position_pct:
                        concentration_warnings.append({
                            "stock_code": stock_code,
                            "type": "concentration_risk",
                            "position_pct": position_pct,
                            "max_allowed_pct": self.max_position_pct,
                            "position_value": position_value,
                            "warning": f"持仓占比过高: {position_pct:.2%} > {self.max_position_pct:.2%}"
                        })
            
            return concentration_warnings
            
        except Exception as e:
            self.logger.error(f"集中度检查失败: {e}")
            return []
    
    def check_market_limits(self, stock_codes: List[str]) -> Dict[str, Dict]:
        """
        检查涨跌停和停牌状态
        
        Args:
            stock_codes: 股票代码列表
            
        Returns:
            Dict: 市场限制状态
        """
        try:
            if not stock_codes:
                return {}
            
            # 获取当前价格和前收盘价
            current_data = self._get_current_prices(stock_codes)
            if current_data.empty:
                return {}
            
            market_limits = {}
            
            for stock_code in stock_codes:
                if stock_code in current_data.index:
                    row = current_data.loc[stock_code]
                    
                    open_price = row.get('open', 0)
                    high_price = row.get('high', 0)
                    low_price = row.get('low', 0)
                    close_price = row.get('close', 0)
                    pre_close = row.get('pre_close', 0)
                    volume = row.get('vol', 0)
                    
                    limits = {
                        "suspended": False,
                        "limit_up": False,
                        "limit_down": False,
                        "can_buy": True,
                        "can_sell": True
                    }
                    
                    # 检查停牌
                    if volume == 0 or all(p == 0 for p in [open_price, high_price, low_price, close_price]):
                        limits.update({
                            "suspended": True,
                            "can_buy": False,
                            "can_sell": False,
                            "reason": "停牌"
                        })
                    
                    # 检查涨跌停
                    elif pre_close > 0:
                        change_rate = (close_price - pre_close) / pre_close
                        
                        # 一字涨停检查
                        if (open_price == high_price == low_price == close_price and 
                            change_rate >= 0.098):
                            limits.update({
                                "limit_up": True,
                                "can_buy": False,
                                "reason": "一字涨停"
                            })
                        
                        # 一字跌停检查
                        elif (open_price == high_price == low_price == close_price and 
                              change_rate <= -0.098):
                            limits.update({
                                "limit_down": True,
                                "can_sell": False,
                                "reason": "一字跌停"
                            })
                    
                    market_limits[stock_code] = limits
            
            return market_limits
            
        except Exception as e:
            self.logger.error(f"市场限制检查失败: {e}")
            return {}
    
    def validate_trading_time(self) -> bool:
        """
        验证是否在交易时间内
        
        Returns:
            bool: 是否在交易时间
        """
        try:
            now = datetime.now()
            weekday = now.weekday()
            
            # 周末不交易
            if weekday >= 5:  # 5=Saturday, 6=Sunday
                return False
            
            # 交易时间：9:30-11:30, 13:00-15:00
            current_time = now.time()
            morning_start = datetime.strptime("09:30", "%H:%M").time()
            morning_end = datetime.strptime("11:30", "%H:%M").time()
            afternoon_start = datetime.strptime("13:00", "%H:%M").time()
            afternoon_end = datetime.strptime("15:00", "%H:%M").time()
            
            is_trading_time = (
                (morning_start <= current_time <= morning_end) or
                (afternoon_start <= current_time <= afternoon_end)
            )
            
            return is_trading_time
            
        except Exception as e:
            self.logger.error(f"交易时间验证失败: {e}")
            return False
    
    def calculate_portfolio_metrics(self, portfolio_state: Dict) -> Dict:
        """
        计算投资组合风险指标
        
        Args:
            portfolio_state: 投资组合状态
            
        Returns:
            Dict: 风险指标
        """
        try:
            positions = portfolio_state.get("positions", {})
            total_value = portfolio_state.get("total_value", 0.0)
            cash = portfolio_state.get("cash", 0.0)
            
            if not positions or total_value <= 0:
                return {"error": "无有效持仓"}
            
            # 获取当前价格
            stock_codes = list(positions.keys())
            current_prices = self._get_current_prices(stock_codes)
            
            metrics = {
                "total_positions": len(positions),
                "cash_ratio": cash / total_value,
                "position_values": {},
                "position_weights": {},
                "unrealized_pnl": {},
                "concentration_risk": False
            }
            
            total_unrealized_pnl = 0.0
            max_position_weight = 0.0
            
            for stock_code, position in positions.items():
                if stock_code in current_prices.index:
                    current_price = current_prices.loc[stock_code, 'close']
                    cost_price = position["cost"]
                    shares = position["shares"]
                    
                    position_value = shares * current_price
                    position_weight = position_value / total_value
                    unrealized_pnl = (current_price - cost_price) * shares
                    
                    metrics["position_values"][stock_code] = position_value
                    metrics["position_weights"][stock_code] = position_weight
                    metrics["unrealized_pnl"][stock_code] = unrealized_pnl
                    
                    total_unrealized_pnl += unrealized_pnl
                    max_position_weight = max(max_position_weight, position_weight)
            
            metrics.update({
                "total_unrealized_pnl": total_unrealized_pnl,
                "max_position_weight": max_position_weight,
                "concentration_risk": max_position_weight > self.max_position_pct
            })
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"计算投资组合指标失败: {e}")
            return {"error": str(e)}
    
    def generate_risk_report(self, portfolio_state: Dict, risk_control_state: Dict) -> str:
        """
        生成风控报告
        
        Args:
            portfolio_state: 投资组合状态
            risk_control_state: 风控状态
            
        Returns:
            str: 风控报告
        """
        try:
            # 执行各项风控检查
            risk_triggers = self.check_portfolio_risk(portfolio_state, risk_control_state)
            concentration_warnings = self.check_position_concentration(portfolio_state)
            portfolio_metrics = self.calculate_portfolio_metrics(portfolio_state)
            
            # 生成报告
            report = f"""
# 投资组合风控报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 基本信息
- 总资产: {portfolio_state.get('total_value', 0):,.2f}
- 现金: {portfolio_state.get('cash', 0):,.2f}
- 持仓数量: {len(portfolio_state.get('positions', {}))}
- 现金占比: {portfolio_metrics.get('cash_ratio', 0):.2%}

## 风控状态
- 已触发股票数: {len(risk_control_state.get('triggered_stocks', []))}
- 止损次数: {risk_control_state.get('stop_loss_count', 0)}
- 止盈次数: {risk_control_state.get('take_profit_count', 0)}

## 当前风险检查
- 风控触发: {len(risk_triggers)} 个
- 集中度警告: {len(concentration_warnings)} 个
- 最大持仓占比: {portfolio_metrics.get('max_position_weight', 0):.2%}
- 集中度风险: {'是' if portfolio_metrics.get('concentration_risk', False) else '否'}

## 详细触发信息
"""
            
            if risk_triggers:
                report += "\n### 风控触发\n"
                for trigger in risk_triggers:
                    report += f"- {trigger['stock_code']}: {trigger['reason']}\n"
            
            if concentration_warnings:
                report += "\n### 集中度警告\n"
                for warning in concentration_warnings:
                    report += f"- {warning['stock_code']}: {warning['warning']}\n"
            
            return report
            
        except Exception as e:
            self.logger.error(f"生成风控报告失败: {e}")
            return f"报告生成失败: {str(e)}"
    
    def _get_current_prices(self, stock_codes: List[str]) -> pd.DataFrame:
        """获取当前价格"""
        try:
            if not stock_codes:
                return pd.DataFrame()
            
            today = datetime.now().strftime('%Y-%m-%d')
            
            # 尝试从缓存获取
            cache_key = f"current_prices_{today}_{len(stock_codes)}"
            cached_data = self.cache_manager.get_market_data(cache_key)
            
            if cached_data is not None:
                available_stocks = [code for code in stock_codes if code in cached_data.index]
                if len(available_stocks) == len(stock_codes):
                    return cached_data.loc[available_stocks]
            
            # 从数据源获取
            price_data = self.data_provider.get_daily_price(stock_codes, today, today)
            
            if price_data is not None and not price_data.empty:
                # 转换格式
                price_data = price_data.set_index('ts_code')
                
                # 缓存数据（短TTL，因为是实时价格）
                self.cache_manager.cache_market_data(cache_key, price_data, ttl_hours=0.5)
                
                return price_data
            else:
                self.logger.warning("无法获取当前价格数据")
                return pd.DataFrame()
                
        except Exception as e:
            self.logger.error(f"获取当前价格失败: {e}")
            return pd.DataFrame()