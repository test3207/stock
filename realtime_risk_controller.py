#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实时风控监控模块
负责实时监控持仓风险，触发止损止盈交易

核心功能：
1. 实时价格监控
2. 止损止盈检查
3. 自动交易执行
4. 风控状态记录
"""

import json
import logging
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import time
import sys

# 添加项目路径
sys.path.append(str(Path(__file__).parent / "python"))
from stock.data.akshare_provider import AkshareDataProvider

class RealTimeRiskController:
    """实时风控监控器"""
    
    def __init__(self, simulation_system):
        """
        初始化风控模块
        
        Args:
            simulation_system: 实时模拟系统实例
        """
        self.system = simulation_system
        self.data_provider = simulation_system.data_provider
        self.logger = simulation_system.logger
        
        # 风控配置
        self.risk_config = simulation_system.system_config.get("risk_control", {})
        self.stop_loss_threshold = self.risk_config.get("stop_loss_threshold", -0.15)
        self.take_profit_threshold = self.risk_config.get("take_profit_threshold", 0.20)
        self.check_interval = self.risk_config.get("check_interval_minutes", 5)
        
        # 交易成本配置
        self.trading_costs = simulation_system.system_config.get("trading_costs", {})
        
        self.logger.info("实时风控监控器初始化完成")
    
    def get_real_time_prices(self, stock_codes: List[str]) -> Dict[str, float]:
        """
        获取实时股价
        
        Args:
            stock_codes: 股票代码列表
            
        Returns:
            Dict: 股票代码 -> 当前价格
        """
        prices = {}
        
        try:
            for code in stock_codes:
                try:
                    # 获取实时价格
                    real_time_data = self.data_provider.get_real_time_price(code)
                    if real_time_data is not None and len(real_time_data) > 0:
                        current_price = float(real_time_data.iloc[-1]['close'])
                        prices[code] = current_price
                    else:
                        self.logger.warning(f"无法获取 {code} 的实时价格")
                except Exception as e:
                    self.logger.error(f"获取 {code} 实时价格失败: {e}")
                    continue
                    
            self.logger.info(f"成功获取 {len(prices)} 只股票的实时价格")
            return prices
            
        except Exception as e:
            self.logger.error(f"获取实时价格失败: {e}")
            return {}
    
    def check_risk_control_triggers(self) -> List[Dict]:
        """
        检查风控触发条件
        
        Returns:
            List[Dict]: 触发的风控操作列表
        """
        triggers = []
        positions = self.system.portfolio_state.get("positions", {})
        
        if not positions:
            return triggers
        
        # 获取实时价格
        stock_codes = list(positions.keys())
        current_prices = self.get_real_time_prices(stock_codes)
        
        for stock_code, position in positions.items():
            if stock_code not in current_prices:
                continue
                
            current_price = current_prices[stock_code]
            cost_price = position.get("cost", 0)
            shares = position.get("shares", 0)
            
            if cost_price <= 0 or shares <= 0:
                continue
            
            # 计算收益率
            return_rate = (current_price - cost_price) / cost_price
            
            # 检查止损
            if return_rate <= self.stop_loss_threshold:
                trigger = {
                    "type": "stop_loss",
                    "stock_code": stock_code,
                    "current_price": current_price,
                    "cost_price": cost_price,
                    "shares": shares,
                    "return_rate": return_rate,
                    "trigger_threshold": self.stop_loss_threshold,
                    "trigger_time": datetime.now().isoformat(),
                    "action": "sell_all"
                }
                triggers.append(trigger)
                self.logger.warning(f"触发止损: {stock_code}, 收益率: {return_rate:.2%}")
            
            # 检查止盈
            elif return_rate >= self.take_profit_threshold:
                trigger = {
                    "type": "take_profit",
                    "stock_code": stock_code,
                    "current_price": current_price,
                    "cost_price": cost_price,
                    "shares": shares,
                    "return_rate": return_rate,
                    "trigger_threshold": self.take_profit_threshold,
                    "trigger_time": datetime.now().isoformat(),
                    "action": "sell_all"
                }
                triggers.append(trigger)
                self.logger.info(f"触发止盈: {stock_code}, 收益率: {return_rate:.2%}")
        
        return triggers
    
    def calculate_trading_costs(self, stock_code: str, price: float, shares: int, action: str) -> Dict[str, float]:
        """
        计算交易成本
        
        Args:
            stock_code: 股票代码
            price: 交易价格
            shares: 交易股数
            action: 交易动作 ('buy' 或 'sell')
            
        Returns:
            Dict: 交易成本明细
        """
        trade_amount = price * shares
        
        # 佣金（买卖都有）
        commission_rate = self.trading_costs.get("commission_rate", 0.0001)
        commission = max(trade_amount * commission_rate, 5.0)  # 最低5元
        
        # 印花税（仅卖出）
        stamp_tax = 0.0
        if action == "sell":
            stamp_tax_rate = self.trading_costs.get("stamp_tax_rate", 0.001)
            stamp_tax = trade_amount * stamp_tax_rate
        
        # 过户费（沪市）
        transfer_fee = 0.0
        if stock_code.endswith('.SH'):
            transfer_fee = max(trade_amount * 0.00002, 1.0)  # 最低1元
        
        # 滑点
        slippage_bps = self.trading_costs.get("slippage_bps", 8)
        slippage = trade_amount * slippage_bps / 10000
        
        total_cost = commission + stamp_tax + transfer_fee + slippage
        
        return {
            "commission": commission,
            "stamp_tax": stamp_tax,
            "transfer_fee": transfer_fee,
            "slippage": slippage,
            "total_cost": total_cost,
            "cost_rate": total_cost / trade_amount if trade_amount > 0 else 0
        }
    
    def execute_risk_control_trade(self, trigger: Dict) -> Dict:
        """
        执行风控交易
        
        Args:
            trigger: 风控触发信息
            
        Returns:
            Dict: 交易执行结果
        """
        try:
            stock_code = trigger["stock_code"]
            current_price = trigger["current_price"]
            shares = trigger["shares"]
            action = trigger["action"]
            
            # 计算交易成本
            costs = self.calculate_trading_costs(stock_code, current_price, shares, "sell")
            
            # 计算净收入
            gross_amount = current_price * shares
            net_amount = gross_amount - costs["total_cost"]
            
            # 更新持仓
            positions = self.system.portfolio_state["positions"]
            if stock_code in positions:
                original_cost = positions[stock_code]["cost"] * shares
                
                # 移除持仓
                del positions[stock_code]
                
                # 更新现金
                self.system.portfolio_state["cash"] += net_amount
                
                # 如果是风控触发，资金进入闲置状态
                if trigger["type"] in ["stop_loss", "take_profit"]:
                    self.system.portfolio_state["idle_cash"] += net_amount
                    
                    # 更新风控状态
                    if trigger["type"] == "stop_loss":
                        self.system.risk_control_state["stop_loss_count"] += 1
                    else:
                        self.system.risk_control_state["take_profit_count"] += 1
                    
                    # 添加到触发列表
                    triggered_stocks = self.system.risk_control_state.get("triggered_stocks", [])
                    if stock_code not in triggered_stocks:
                        triggered_stocks.append(stock_code)
                        self.system.risk_control_state["triggered_stocks"] = triggered_stocks
                
                # 创建交易记录
                trade_record = {
                    "stock_code": stock_code,
                    "action": "sell",
                    "shares": shares,
                    "price": current_price,
                    "gross_amount": gross_amount,
                    "costs": costs,
                    "net_amount": net_amount,
                    "trigger_type": trigger["type"],
                    "return_rate": trigger["return_rate"],
                    "original_cost": original_cost,
                    "profit_loss": net_amount - original_cost,
                    "timestamp": datetime.now().isoformat(),
                    "execution_type": "risk_control_auto"
                }
                
                self.logger.info(f"风控交易执行成功: {trigger['type']} {stock_code}, "
                               f"收益率: {trigger['return_rate']:.2%}, "
                               f"盈亏: {trade_record['profit_loss']:,.2f}")
                
                return {
                    "success": True,
                    "trade_record": trade_record,
                    "message": f"风控交易执行成功: {trigger['type']}"
                }
            
            else:
                return {
                    "success": False,
                    "trade_record": None,
                    "message": f"持仓中未找到股票: {stock_code}"
                }
                
        except Exception as e:
            self.logger.error(f"执行风控交易失败: {e}")
            return {
                "success": False,
                "trade_record": None,
                "message": f"交易执行失败: {str(e)}"
            }
    
    def update_market_values(self):
        """更新持仓市值"""
        try:
            positions = self.system.portfolio_state.get("positions", {})
            if not positions:
                self.system.portfolio_state["market_value"] = 0.0
                self.system.portfolio_state["total_value"] = self.system.portfolio_state.get("cash", 0)
                return
            
            # 获取实时价格
            stock_codes = list(positions.keys())
            current_prices = self.get_real_time_prices(stock_codes)
            
            total_market_value = 0.0
            for stock_code, position in positions.items():
                if stock_code in current_prices:
                    shares = position.get("shares", 0)
                    current_price = current_prices[stock_code]
                    market_value = shares * current_price
                    total_market_value += market_value
                    
                    # 更新持仓市值
                    position["current_price"] = current_price
                    position["market_value"] = market_value
            
            # 更新总市值和总资产
            self.system.portfolio_state["market_value"] = total_market_value
            self.system.portfolio_state["total_value"] = (
                self.system.portfolio_state.get("cash", 0) + total_market_value
            )
            
        except Exception as e:
            self.logger.error(f"更新市值失败: {e}")
    
    def run_risk_monitoring_cycle(self) -> List[Dict]:
        """
        运行一次风控监控周期
        
        Returns:
            List[Dict]: 执行的交易记录
        """
        executed_trades = []
        
        try:
            self.logger.info("开始风控监控周期...")
            
            # 更新市值
            self.update_market_values()
            
            # 检查风控触发
            triggers = self.check_risk_control_triggers()
            
            if not triggers:
                self.logger.info("无风控触发")
                return executed_trades
            
            # 执行风控交易
            for trigger in triggers:
                result = self.execute_risk_control_trade(trigger)
                if result["success"]:
                    executed_trades.append(result["trade_record"])
                    
                    # 立即保存交易记录
                    current_date = datetime.now().strftime('%Y-%m-%d')
                    self.system.save_trading_record(current_date + "_risk_control", [result["trade_record"]])
            
            # 更新风控检查时间
            self.system.risk_control_state["last_risk_check"] = datetime.now().isoformat()
            
            # 保存更新后的状态
            current_date = datetime.now().strftime('%Y-%m-%d')
            self.system.save_portfolio_state(current_date)
            
            if executed_trades:
                self.logger.info(f"风控监控周期完成，执行交易 {len(executed_trades)} 笔")
            
            return executed_trades
            
        except Exception as e:
            self.logger.error(f"风控监控周期执行失败: {e}")
            return executed_trades


if __name__ == "__main__":
    # 测试代码
    print("风控监控模块测试...")
    
    # 这里需要实际的simulation_system实例
    # system = RealtimeSimulationSystem()
    # risk_controller = RealTimeRiskController(system)
    
    print("风控监控模块测试完成！")