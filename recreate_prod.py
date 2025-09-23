#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重新创建增强版prod实例
"""

import sys
from pathlib import Path
sys.path.append(str(Path('.').absolute()))

from simulation.core.instance_manager import InstanceManager

def recreate_prod_instance():
    """重新创建增强版prod实例"""
    manager = InstanceManager()
    
    # 创建增强版prod实例配置
    prod_config = {
        'instance_name': 'prod',
        'initial_capital': 1000000.0,
        'strategy': {
            'lookback_days': 90,
            'decline_threshold': 0.15,
            'top_n': 35,
            'min_listing_years': 5,
            'rebalance_frequency': 'monthly',
            'exclude_northeast': True,
            'strategy_type': 'enhanced_drawdown'
        },
        'risk_control': {
            'stop_loss': -0.15,
            'take_profit': 0.20,
            'max_position_ratio': 0.05,
            'check_frequency': 'daily',
            'concentration_limit': 0.10
        },
        'trading': {
            'commission_rate': 0.0001,
            'stamp_tax_rate': 0.001,
            'slippage_bps': 0,
            'min_shares': 100,
            'trading_hours': {
                'start': '09:30',
                'end': '15:00'
            }
        }
    }
    
    result = manager.create_instance('prod', prod_config)
    if result:
        print('✅ 增强版prod生产实例创建成功')
        print('配置摘要:')
        print(f'  初始资金: {prod_config["initial_capital"]:,.0f}元')
        print(f'  策略类型: {prod_config["strategy"]["strategy_type"]}')
        print(f'  回看天数: {prod_config["strategy"]["lookback_days"]}天')
        print(f'  跌幅阈值: {prod_config["strategy"]["decline_threshold"]*100}%')
        print(f'  东北过滤: {prod_config["strategy"]["exclude_northeast"]}')
        print(f'  选股数量: {prod_config["strategy"]["top_n"]}只')
        print(f'  佣金费率: {prod_config["trading"]["commission_rate"]*10000:.1f}万')
    else:
        print('❌ prod实例创建失败或已存在')
    
    return result

if __name__ == "__main__":
    recreate_prod_instance()