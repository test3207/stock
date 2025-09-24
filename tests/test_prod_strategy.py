#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试新prod实例的增强策略引擎
"""

import sys
sys.path.append('.')

from simulation.engines.strategy_engine import StrategyEngine
import json

def test_prod_strategy():
    """测试prod实例的增强策略"""
    # 加载新的prod配置
    with open('data/simulation/instances/prod/config.json', 'r') as f:
        config = json.load(f)
    
    print('测试新prod实例的增强策略引擎...')
    print(f'配置中的策略类型: {config["strategy"].get("strategy_type", "未指定")}')
    print(f'跌幅阈值: {config["strategy"]["decline_threshold"]*100}%')
    print(f'东北过滤: {config["strategy"]["exclude_northeast"]}')
    
    try:
        strategy_engine = StrategyEngine(config)
        selected_stocks = strategy_engine.select_stocks('2025-09-20')
        
        print('✅ 增强策略引擎工作正常')
        print(f'选出股票数量: {len(selected_stocks)}')
        if selected_stocks:
            print(f'前5只股票: {selected_stocks[:5]}')
            
    except Exception as e:
        print(f'❌ 增强策略引擎失败: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_prod_strategy()