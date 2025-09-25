#!/usr/bin/env python3
"""
解析并显示回测结果关键指标
"""

import json
import os
import glob
import sys

def display_key_metrics(output_dir):
    """解析并显示关键指标"""
    
    print("🔍 解析并显示关键指标...")
    
    # 查找结果文件
    result_files = []
    patterns = [
        f'{output_dir}/*.json',
        'data/backtest/*.json', 
        'data/backtest/*/*.json'
    ]
    
    for pattern in patterns:
        result_files.extend(glob.glob(pattern))

    if not result_files:
        print('❌ 未找到结果文件')
        return False

    print(f'📁 找到 {len(result_files)} 个结果文件')

    for file_path in result_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            print(f'\n📊 文件: {os.path.basename(file_path)}')
            
            # 提取关键指标
            if 'performance_metrics' in data:
                metrics = data['performance_metrics']
                print('🎯 核心指标:')
                if 'annual_return' in metrics:
                    print(f'  📈 年化收益率: {metrics["annual_return"]*100:.2f}%')
                if 'total_return' in metrics:
                    print(f'  💰 总收益率: {metrics["total_return"]*100:.2f}%')
                if 'max_drawdown' in metrics:
                    print(f'  📉 最大回撤: {metrics["max_drawdown"]*100:.2f}%')
                if 'sharpe_ratio' in metrics:
                    print(f'  ⚖️  夏普比率: {metrics["sharpe_ratio"]:.3f}')
                    
            # 显示策略信息
            if 'strategy_name' in data:
                print(f'📋 策略: {data["strategy_name"]}')
            if 'backtest_period' in data:
                print(f'📅 回测期间: {data["backtest_period"]}')
                
        except Exception as e:
            print(f'⚠️  解析文件 {file_path} 失败: {e}')
    
    return True

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python display_key_metrics.py <output_dir>")
        sys.exit(1)
        
    output_dir = sys.argv[1]
    success = display_key_metrics(output_dir)
    sys.exit(0 if success else 1)