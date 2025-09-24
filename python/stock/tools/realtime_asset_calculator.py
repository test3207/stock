#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实时资产价值计算工具
根据持仓信息获取实时股价，计算当前总资产价值
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

# 添加项目根路径
sys.path.append(str(Path(__file__).parent.parent))

from python.stock.data.akshare_provider import AkShareProvider

class RealTimeAssetCalculator:
    """实时资产价值计算器"""
    
    def __init__(self):
        self.data_provider = AkShareProvider()
        self.logger = logging.getLogger(__name__)
        
    def calculate_realtime_value(self, instance_name: str = "default", 
                               target_date: str = None) -> Dict:
        """
        计算指定实例的实时资产价值
        
        Args:
            instance_name: 实例名称
            target_date: 目标日期，默认为今天
            
        Returns:
            Dict: 包含实时资产价值信息
        """
        try:
            if target_date is None:
                target_date = datetime.now().strftime('%Y-%m-%d')
            
            # 读取状态文件
            state_file = Path(f'data/simulation/instances/{instance_name}/state/{target_date}.json')
            if not state_file.exists():
                return {
                    "success": False,
                    "error": f"未找到 {instance_name} 实例在 {target_date} 的状态文件"
                }
            
            with open(state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
            
            portfolio = state.get('portfolio', {})
            positions = portfolio.get('positions', {})
            cash = portfolio.get('cash', 0.0)
            idle_cash = portfolio.get('idle_cash', 0.0)
            
            if not positions:
                return {
                    "success": True,
                    "instance": instance_name,
                    "date": target_date,
                    "query_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "cash": cash,
                    "idle_cash": idle_cash,
                    "total_cash": cash + idle_cash,
                    "positions": [],
                    "market_value": 0.0,
                    "total_value": cash + idle_cash,
                    "original_total_value": portfolio.get('total_value', 0.0),
                    "value_change": (cash + idle_cash) - portfolio.get('total_value', 0.0),
                    "change_percentage": 0.0
                }
            
            # 获取实时价格
            stock_codes = list(positions.keys())
            price_data = self.data_provider.get_daily_price(stock_codes, target_date, target_date)
            
            if price_data is None or price_data.empty:
                return {
                    "success": False,
                    "error": f"无法获取 {target_date} 的实时价格数据"
                }
            
            # 转换为以股票代码为索引的格式
            price_data = price_data.set_index('ts_code')
            
            # 计算每只股票的实时价值
            position_details = []
            total_market_value = 0.0
            
            for stock_code, position in positions.items():
                shares = position.get('shares', 0)
                cost_price = position.get('cost', 0.0)
                
                if stock_code in price_data.index:
                    current_price = price_data.loc[stock_code, 'close']
                    current_value = shares * current_price
                    cost_value = shares * cost_price
                    profit_loss = current_value - cost_value
                    profit_loss_pct = (profit_loss / cost_value * 100) if cost_value > 0 else 0.0
                    
                    position_detail = {
                        "stock_code": stock_code,
                        "shares": shares,
                        "cost_price": cost_price,
                        "current_price": current_price,
                        "cost_value": cost_value,
                        "current_value": current_value,
                        "profit_loss": profit_loss,
                        "profit_loss_percentage": profit_loss_pct
                    }
                    position_details.append(position_detail)
                    total_market_value += current_value
                else:
                    self.logger.warning(f"未找到 {stock_code} 的实时价格数据")
            
            # 计算总资产
            total_cash = cash + idle_cash
            total_value = total_cash + total_market_value
            original_total_value = portfolio.get('total_value', 0.0)
            value_change = total_value - original_total_value
            change_percentage = (value_change / original_total_value * 100) if original_total_value > 0 else 0.0
            
            return {
                "success": True,
                "instance": instance_name,
                "date": target_date,
                "query_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "cash": cash,
                "idle_cash": idle_cash,
                "total_cash": total_cash,
                "positions": position_details,
                "market_value": total_market_value,
                "total_value": total_value,
                "original_total_value": original_total_value,
                "value_change": value_change,
                "change_percentage": change_percentage,
                "position_count": len(position_details)
            }
            
        except Exception as e:
            self.logger.error(f"计算实时资产价值失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def print_realtime_report(self, instance_name: str = "default", 
                            target_date: str = None, detailed: bool = False):
        """
        打印实时资产报告
        
        Args:
            instance_name: 实例名称
            target_date: 目标日期
            detailed: 是否显示详细持仓信息
        """
        result = self.calculate_realtime_value(instance_name, target_date)
        
        if not result["success"]:
            print(f"❌ 计算失败: {result['error']}")
            return
        
        print(f"📊 实时资产价值报告 - {result['instance']} 实例")
        print(f"   日期: {result['date']}")
        print(f"   查询时间: {result['query_time']}")
        print(f"   持仓数量: {result['position_count']} 只")
        print()
        
        print(f"💰 资产概览:")
        print(f"   现金: {result['total_cash']:,.2f} 元")
        print(f"   市值: {result['market_value']:,.2f} 元")
        print(f"   总资产: {result['total_value']:,.2f} 元")
        print()
        
        print(f"📈 价值变化:")
        print(f"   原始总资产: {result['original_total_value']:,.2f} 元")
        print(f"   价值变化: {result['value_change']:+,.2f} 元")
        print(f"   变化幅度: {result['change_percentage']:+.2f}%")
        
        if detailed and result['positions']:
            print(f"\n📋 详细持仓信息:")
            for pos in result['positions']:
                print(f"   {pos['stock_code']}:")
                print(f"     持仓: {pos['shares']} 股")
                print(f"     成本价: {pos['cost_price']:.2f} 元")
                print(f"     现价: {pos['current_price']:.2f} 元")
                print(f"     成本: {pos['cost_value']:,.2f} 元")
                print(f"     市值: {pos['current_value']:,.2f} 元")
                print(f"     盈亏: {pos['profit_loss']:+,.2f} 元 ({pos['profit_loss_percentage']:+.2f}%)")
                print()

def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='实时资产价值计算工具')
    parser.add_argument('--instance', default='default', help='实例名称')
    parser.add_argument('--date', help='目标日期 (YYYY-MM-DD)')
    parser.add_argument('--detailed', action='store_true', help='显示详细持仓信息')
    
    args = parser.parse_args()
    
    calculator = RealTimeAssetCalculator()
    calculator.print_realtime_report(args.instance, args.date, args.detailed)

if __name__ == "__main__":
    main()