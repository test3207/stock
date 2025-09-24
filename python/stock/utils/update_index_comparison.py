#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取主要指数的年度表现数据，用于与策略对比
"""

import sys
import json
import pandas as pd
from pathlib import Path
from datetime import datetime

# 添加项目根路径
sys.path.append(str(Path(__file__).parent))

from python.stock.data.akshare_provider import AkShareProvider

def get_index_annual_returns():
    """获取主要指数的年度收益率"""
    data_provider = AkShareProvider()
    
    # 主要指数代码
    indices = {
        'hs300': '000300',    # 沪深300
        'csi500': '000905',   # 中证500
        'shanghai': '000001'   # 上证指数
    }
    
    results = {}
    
    for index_name, index_code in indices.items():
        print(f"正在获取{index_name}指数数据...")
        try:
            # 获取2020-2025年的指数数据
            df = data_provider.get_daily_price([f"{index_code}.SH"], '2020-01-01', '2025-09-23')
            if df is not None and not df.empty:
                df['trade_date'] = pd.to_datetime(df['trade_date'])
                df = df.set_index('trade_date')
                
                # 计算年度收益率
                annual_returns = {}
                years = [2020, 2021, 2022, 2023, 2024, 2025]
                
                for year in years:
                    year_data = df[df.index.year == year]
                    if not year_data.empty:
                        if year == 2020:
                            # 2020年从7月1日开始计算（与策略一致）
                            start_date = f"{year}-07-01"
                            year_data = year_data[year_data.index >= start_date]
                        
                        if year == 2025:
                            # 2025年到8月31日结束（与策略一致）
                            end_date = f"{year}-08-31"
                            year_data = year_data[year_data.index <= end_date]
                        
                        if len(year_data) >= 2:
                            start_price = year_data.iloc[0]['close']
                            end_price = year_data.iloc[-1]['close']
                            annual_return = (end_price - start_price) / start_price * 100
                            annual_returns[year] = round(annual_return, 2)
                
                results[index_name] = annual_returns
                print(f"✅ {index_name}指数数据获取成功")
            else:
                print(f"❌ 无法获取{index_name}指数数据")
                
        except Exception as e:
            print(f"❌ 获取{index_name}指数数据失败: {e}")
    
    return results

def update_backtest_json_with_index_data():
    """更新回测JSON文件，添加精确的指数对比数据"""
    
    # 获取指数数据
    index_returns = get_index_annual_returns()
    
    # 读取现有的回测JSON文件
    json_file = Path('data/backtest/enhanced_drawdown_strategy_backtest_2020-2025_20250923.json')
    
    if json_file.exists():
        with open(json_file, 'r', encoding='utf-8') as f:
            backtest_data = json.load(f)
        
        # 更新年度表现数据
        if 'annual_performance' in backtest_data:
            for year_str, year_data in backtest_data['annual_performance'].items():
                year = int(year_str)
                
                # 更新指数收益率数据
                if 'hs300' in index_returns and year in index_returns['hs300']:
                    year_data['hs300_return'] = f"{index_returns['hs300'][year]:+.2f}%"
                
                if 'csi500' in index_returns and year in index_returns['csi500']:
                    year_data['csi500_return'] = f"{index_returns['csi500'][year]:+.2f}%"
                
                if 'shanghai' in index_returns and year in index_returns['shanghai']:
                    year_data['shanghai_return'] = f"{index_returns['shanghai'][year]:+.2f}%"
        
        # 更新基准对比数据
        if 'benchmark_comparison' in backtest_data and index_returns:
            # 计算5年期年化收益率
            total_years = 5.2
            
            for index_name in ['hs300', 'csi500', 'shanghai']:
                if index_name in index_returns:
                    # 计算总收益率（复合增长）
                    total_return = 1.0
                    for year, annual_return in index_returns[index_name].items():
                        if year == 2020:
                            # 2020年只有下半年
                            total_return *= (1 + annual_return/100)
                        elif year == 2025:
                            # 2025年只有前8个月，按比例计算
                            monthly_return = (1 + annual_return/100) ** (1/8) - 1
                            total_return *= (1 + monthly_return) ** 8
                        else:
                            total_return *= (1 + annual_return/100)
                    
                    # 转换为年化收益率
                    annualized_return = (total_return ** (1/total_years) - 1) * 100
                    
                    # 更新基准对比数据
                    benchmark_key = f'vs_{index_name}'
                    if benchmark_key in backtest_data['benchmark_comparison']:
                        backtest_data['benchmark_comparison'][benchmark_key]['benchmark_annualized'] = f"{annualized_return:+.2f}%"
                        outperformance = 13.24 - annualized_return
                        backtest_data['benchmark_comparison'][benchmark_key]['outperformance'] = f"{outperformance:+.2f}%"
        
        # 添加数据更新时间戳
        backtest_data['index_data_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 保存更新后的数据
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(backtest_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 回测JSON文件已更新: {json_file}")
        
        # 显示更新后的指数对比
        print("\n📊 指数年度收益率对比:")
        for index_name, returns in index_returns.items():
            print(f"\n{index_name.upper()}指数:")
            for year, return_rate in returns.items():
                print(f"  {year}年: {return_rate:+.2f}%")
    
    else:
        print(f"❌ 未找到回测JSON文件: {json_file}")

if __name__ == "__main__":
    print("🔍 开始获取主要指数年度表现数据...")
    update_backtest_json_with_index_data()
    print("✅ 指数数据更新完成！")