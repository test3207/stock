#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交易引擎
负责执行买卖交易，计算交易成本和更新投资组合
"""

import sys
import logging
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

# 添加项目根路径
sys.path.append(str(Path(__file__).parent.parent.parent))

from python.stock.data.akshare_provider import AkShareProvider
from simulation.core.cache_manager import CacheManager

class TradingEngine:
    """交易引擎"""
    
    def __init__(self, config: Dict, cache_manager: CacheManager):
        self.config = config
        self.cache_manager = cache_manager
        self.logger = logging.getLogger(__name__)
        
        # 初始化数据提供者
        self.data_provider = AkShareProvider()
        
        # 交易成本配置 - 兼容新旧配置格式
        trading_costs = config.get("trading_costs", {})
        trading_config = config.get("trading", {})
        
        # 优先使用新格式(trading)，然后fallback到旧格式(trading_costs)
        self.commission_rate = trading_config.get("commission_rate", 
                                                 trading_costs.get("commission_rate", 0.0001))
        self.stamp_tax_rate = trading_config.get("stamp_tax_rate", 
                                                trading_costs.get("stamp_tax_rate", 0.001))
        self.slippage_bps = trading_config.get("slippage_bps", 
                                              trading_costs.get("slippage_bps", 8))
    
    def calculate_rebalance_trades(self, portfolio_state: Dict, 
                                 selected_stocks: List[str], target_date: str) -> Dict:
        """
        计算调仓需要的交易
        
        Args:
            portfolio_state: 当前投资组合状态
            selected_stocks: 策略选出的股票列表
            target_date: 目标日期
            
        Returns:
            Dict: 交易计划
        """
        try:
            self.logger.info(f"开始计算调仓交易，目标股票数: {len(selected_stocks)}")
            
            # 获取当前持仓
            current_positions = portfolio_state.get("positions", {})
            current_cash = portfolio_state.get("cash", 0.0)
            idle_cash = portfolio_state.get("idle_cash", 0.0)
            total_value = portfolio_state.get("total_value", 0.0)
            
            available_cash = current_cash + idle_cash
            
            # 获取最新价格
            price_data = self._get_latest_prices(list(set(list(current_positions.keys()) + selected_stocks)), target_date)
            if price_data.empty:
                raise Exception("无法获取股票价格数据")
            
            # 计算卖出交易
            sell_trades = self._calculate_sell_trades(current_positions, selected_stocks, price_data)
            
            # 计算卖出后的现金
            sell_proceeds = sum(trade["proceeds"] for trade in sell_trades)
            total_available_cash = available_cash + sell_proceeds
            
            # 计算买入交易
            buy_trades = self._calculate_buy_trades(selected_stocks, total_available_cash, price_data)
            
            # 汇总交易计划
            all_trades = sell_trades + buy_trades
            
            trade_plan = {
                "target_date": target_date,
                "trades": all_trades,
                "summary": {
                    "sell_count": len(sell_trades),
                    "buy_count": len(buy_trades),
                    "total_trades": len(all_trades),
                    "sell_proceeds": sell_proceeds,
                    "buy_amount": sum(trade["amount"] for trade in buy_trades),
                    "estimated_cash_after": total_available_cash - sum(trade["amount"] for trade in buy_trades)
                }
            }
            
            self.logger.info(f"交易计算完成: 卖出 {len(sell_trades)} 只, 买入 {len(buy_trades)} 只")
            return trade_plan
            
        except Exception as e:
            self.logger.error(f"计算调仓交易失败: {e}")
            return {}
    
    def execute_trade_plan(self, portfolio_state: Dict, trade_plan: Dict, target_date: str) -> Dict:
        """
        执行交易计划
        
        Args:
            portfolio_state: 当前投资组合状态
            trade_plan: 交易计划
            target_date: 目标日期
            
        Returns:
            Dict: 执行结果
        """
        try:
            self.logger.info("开始执行交易计划")
            
            # 复制当前状态
            new_portfolio_state = portfolio_state.copy()
            new_positions = new_portfolio_state.get("positions", {}).copy()
            current_cash = new_portfolio_state.get("cash", 0.0)
            idle_cash = new_portfolio_state.get("idle_cash", 0.0)
            
            trading_records = []
            total_commission = 0.0
            total_stamp_tax = 0.0
            
            # 执行所有交易
            for trade in trade_plan.get("trades", []):
                try:
                    # 执行单笔交易
                    trade_result = self._execute_single_trade(trade, new_positions, current_cash, idle_cash)
                    
                    if trade_result["success"]:
                        # 更新持仓和现金
                        if trade["action"] == "sell":
                            if trade["stock_code"] in new_positions:
                                del new_positions[trade["stock_code"]]
                            current_cash += trade_result["net_proceeds"]
                        else:  # buy
                            new_positions[trade["stock_code"]] = {
                                "shares": trade["shares"],
                                "cost": trade["price"]
                            }
                            current_cash -= trade_result["total_cost"]
                        
                        # 记录交易
                        trading_records.append({
                            "date": target_date,
                            "stock_code": trade["stock_code"],
                            "action": trade["action"],
                            "shares": trade["shares"],
                            "price": trade["price"],
                            "amount": trade["amount"],
                            "commission": trade_result.get("commission", 0.0),
                            "stamp_tax": trade_result.get("stamp_tax", 0.0),
                            "total_cost": trade_result.get("total_cost", trade["amount"]),
                            "net_proceeds": trade_result.get("net_proceeds", 0.0)
                        })
                        
                        total_commission += trade_result.get("commission", 0.0)
                        total_stamp_tax += trade_result.get("stamp_tax", 0.0)
                    
                except Exception as e:
                    self.logger.warning(f"执行交易失败: {trade['stock_code']} {trade['action']}, {e}")
                    continue
            
            # 计算新的市值
            price_data = self._get_latest_prices(list(new_positions.keys()), target_date)
            market_value = 0.0
            
            for stock_code, position in new_positions.items():
                if stock_code in price_data.index:
                    current_price = price_data.loc[stock_code, 'close']
                    market_value += position["shares"] * current_price
            
            # 更新投资组合状态
            new_portfolio_state.update({
                "cash": current_cash,
                "idle_cash": 0.0,  # 调仓后重置闲置资金
                "positions": new_positions,
                "market_value": market_value,
                "total_value": current_cash + market_value
            })
            
            execution_results = {
                "success": True,
                "new_portfolio_state": new_portfolio_state,
                "trading_records": trading_records,
                "summary": {
                    "executed_trades": len(trading_records),
                    "total_commission": total_commission,
                    "total_stamp_tax": total_stamp_tax,
                    "total_costs": total_commission + total_stamp_tax,
                    "final_cash": current_cash,
                    "final_market_value": market_value,
                    "final_total_value": current_cash + market_value
                }
            }
            
            self.logger.info(f"交易执行完成: {len(trading_records)} 笔交易, 总成本: {total_commission + total_stamp_tax:.2f}")
            return execution_results
            
        except Exception as e:
            self.logger.error(f"执行交易计划失败: {e}")
            return {"success": False, "error": str(e)}
    
    def execute_risk_control_trades(self, portfolio_state: Dict, risk_triggers: List[Dict]) -> Dict:
        """
        执行风控交易（止损止盈）
        
        Args:
            portfolio_state: 当前投资组合状态
            risk_triggers: 风控触发列表
            
        Returns:
            Dict: 执行结果
        """
        try:
            self.logger.info(f"开始执行风控交易，触发数量: {len(risk_triggers)}")
            
            # 生成风控交易计划
            risk_trade_plan = self._create_risk_trade_plan(portfolio_state, risk_triggers)
            
            if not risk_trade_plan.get("trades"):
                return {"success": False, "message": "没有需要执行的风控交易"}
            
            # 执行风控交易
            return self.execute_trade_plan(portfolio_state, risk_trade_plan, 
                                         datetime.now().strftime('%Y-%m-%d'))
            
        except Exception as e:
            self.logger.error(f"执行风控交易失败: {e}")
            return {"success": False, "error": str(e)}
    
    def _calculate_sell_trades(self, current_positions: Dict, selected_stocks: List[str], 
                              price_data: pd.DataFrame) -> List[Dict]:
        """计算卖出交易"""
        sell_trades = []
        
        for stock_code, position in current_positions.items():
            if stock_code not in selected_stocks:
                # 不在新选股中，需要卖出
                if stock_code in price_data.index:
                    current_price = price_data.loc[stock_code, 'close']
                    shares = position["shares"]
                    amount = shares * current_price
                    
                    # 计算交易成本
                    commission = amount * self.commission_rate  # 免5元最低佣金
                    stamp_tax = amount * self.stamp_tax_rate  # 仅卖出收印花税
                    slippage = amount * (self.slippage_bps / 10000)
                    
                    net_proceeds = amount - commission - stamp_tax - slippage
                    
                    sell_trades.append({
                        "action": "sell",
                        "stock_code": stock_code,
                        "shares": shares,
                        "price": current_price,
                        "amount": amount,
                        "commission": commission,
                        "stamp_tax": stamp_tax,
                        "slippage": slippage,
                        "proceeds": net_proceeds
                    })
        
        return sell_trades
    
    def _calculate_buy_trades(self, selected_stocks: List[str], available_cash: float, 
                             price_data: pd.DataFrame) -> List[Dict]:
        """计算买入交易"""
        buy_trades = []
        
        if not selected_stocks or available_cash <= 0:
            return buy_trades
        
        # 等权重分配资金
        target_amount_per_stock = available_cash / len(selected_stocks)
        
        for stock_code in selected_stocks:
            if stock_code in price_data.index:
                current_price = price_data.loc[stock_code, 'close']
                
                # 计算可买入的股数（必须是100的倍数）
                max_shares = int(target_amount_per_stock / current_price / 100) * 100
                
                if max_shares >= 100:  # 至少一手
                    amount = max_shares * current_price
                    
                    # 计算交易成本
                    commission = amount * self.commission_rate  # 免5元最低佣金
                    slippage = amount * (self.slippage_bps / 10000)
                    total_cost = amount + commission + slippage
                    
                    buy_trades.append({
                        "action": "buy",
                        "stock_code": stock_code,
                        "shares": max_shares,
                        "price": current_price,
                        "amount": amount,
                        "commission": commission,
                        "stamp_tax": 0.0,  # 买入无印花税
                        "slippage": slippage,
                        "total_cost": total_cost
                    })
        
        return buy_trades
    
    def _execute_single_trade(self, trade: Dict, positions: Dict, cash: float, idle_cash: float) -> Dict:
        """执行单笔交易"""
        try:
            if trade["action"] == "sell":
                # 卖出交易
                return {
                    "success": True,
                    "net_proceeds": trade["proceeds"],
                    "commission": trade["commission"],
                    "stamp_tax": trade["stamp_tax"]
                }
            else:  # buy
                # 买入交易
                if cash + idle_cash >= trade["total_cost"]:
                    return {
                        "success": True,
                        "total_cost": trade["total_cost"],
                        "commission": trade["commission"],
                        "stamp_tax": trade["stamp_tax"]
                    }
                else:
                    return {
                        "success": False,
                        "error": "资金不足"
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _create_risk_trade_plan(self, portfolio_state: Dict, risk_triggers: List[Dict]) -> Dict:
        """创建风控交易计划"""
        trades = []
        current_positions = portfolio_state.get("positions", {})
        
        # 获取需要风控的股票价格
        risk_stocks = [trigger["stock_code"] for trigger in risk_triggers]
        price_data = self._get_latest_prices(risk_stocks, datetime.now().strftime('%Y-%m-%d'))
        
        for trigger in risk_triggers:
            stock_code = trigger["stock_code"]
            if stock_code in current_positions and stock_code in price_data.index:
                position = current_positions[stock_code]
                current_price = price_data.loc[stock_code, 'close']
                shares = position["shares"]
                amount = shares * current_price
                
                # 计算卖出成本
                commission = amount * self.commission_rate  # 免5元最低佣金
                stamp_tax = amount * self.stamp_tax_rate
                slippage = amount * (self.slippage_bps / 10000)
                net_proceeds = amount - commission - stamp_tax - slippage
                
                trades.append({
                    "action": "sell",
                    "stock_code": stock_code,
                    "shares": shares,
                    "price": current_price,
                    "amount": amount,
                    "commission": commission,
                    "stamp_tax": stamp_tax,
                    "slippage": slippage,
                    "proceeds": net_proceeds,
                    "trigger_type": trigger["type"],
                    "trigger_reason": trigger.get("reason", "")
                })
        
        return {
            "target_date": datetime.now().strftime('%Y-%m-%d'),
            "trades": trades,
            "type": "risk_control"
        }
    
    def _get_latest_prices(self, stock_codes: List[str], target_date: str) -> pd.DataFrame:
        """获取最新价格"""
        try:
            if not stock_codes:
                return pd.DataFrame()
            
            # 尝试从缓存获取
            cache_key = f"latest_prices_{target_date}_{len(stock_codes)}"
            cached_data = self.cache_manager.get_market_data(cache_key)
            
            if cached_data is not None:
                # 过滤出需要的股票
                available_stocks = [code for code in stock_codes if code in cached_data.index]
                if len(available_stocks) == len(stock_codes):
                    return cached_data.loc[available_stocks]
            
            # 缓存未命中，从数据源获取
            price_data = self.data_provider.get_daily_price(stock_codes, target_date, target_date)
            
            if price_data is not None and not price_data.empty:
                # 转换为以股票代码为索引的格式
                price_data = price_data.set_index('ts_code')
                
                # 缓存数据
                self.cache_manager.cache_market_data(cache_key, price_data, ttl_hours=1)
                
                return price_data
            else:
                self.logger.warning(f"无法获取价格数据: {target_date}")
                return pd.DataFrame()
                
        except Exception as e:
            self.logger.error(f"获取最新价格失败: {e}")
            return pd.DataFrame()