#!/usr/bin/env python3
"""
数据仓库测试脚本
测试GitHub数据仓库和集成数据提供者功能
"""

import sys
import os
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "python"))

from stock.data import GitHubDataRepo, IntegratedDataProvider

def test_github_repo():
    """测试GitHub数据仓库"""
    print("=" * 50)
    print("测试 GitHub 数据仓库")
    print("=" * 50)
    
    repo = GitHubDataRepo()
    
    # 检查仓库存在性
    print("\n1. 检查仓库存在性")
    exists = repo.check_repo_exists()
    print(f"仓库是否存在: {exists}")
    
    if exists:
        # 获取可用日期
        print("\n2. 获取可用日期")
        dates = repo.get_available_dates()
        print(f"可用日期数量: {len(dates)}")
        if dates:
            print(f"最新日期: {max(dates)}")
            print(f"最早日期: {min(dates)}")
            
            # 尝试下载最新日期的数据
            latest_date = max(dates)
            print(f"\n3. 下载最新日期数据: {latest_date}")
            df = repo.download_daily_data(latest_date)
            if df is not None:
                print(f"数据条数: {len(df)}")
                print(f"股票数量: {df['symbol'].nunique()}")
                print("前5条记录:")
                print(df.head())
            else:
                print("下载失败")
    
    print("\n4. 下载基础信息")
    basic_df = repo.download_basic_info()
    if basic_df is not None:
        print(f"基础信息条数: {len(basic_df)}")
        print("基础信息列名:", list(basic_df.columns))
    else:
        print("基础信息下载失败")

def test_integrated_provider():
    """测试集成数据提供者"""
    print("\n" + "=" * 50)
    print("测试 集成数据提供者")
    print("=" * 50)
    
    provider = IntegratedDataProvider(use_github_first=True)
    
    # 检查数据源可用性
    print("\n1. 检查数据源可用性")
    availability = provider.check_data_availability()
    print(f"GitHub可用: {availability['github_available']}")
    print(f"akshare可用: {availability['akshare_available']}")
    print(f"GitHub日期数: {len(availability['github_dates'])}")
    
    # 获取数据总览
    print("\n2. 数据源总览")
    summary = provider.get_data_summary()
    for key, value in summary.items():
        print(f"{key}: {value}")
    
    # 获取基础信息
    print("\n3. 获取基础信息")
    basic_info = provider.get_stock_basic()
    if basic_info is not None:
        print(f"基础信息条数: {len(basic_info)}")
        if 'symbol' in basic_info.columns:
            print(f"股票数量: {basic_info['symbol'].nunique()}")
        print("列名:", list(basic_info.columns)[:10])  # 只显示前10个列名
    else:
        print("基础信息获取失败")
    
    # 测试单只股票数据获取
    print("\n4. 测试单只股票数据获取")
    if basic_info is not None and 'symbol' in basic_info.columns:
        test_symbol = basic_info['symbol'].iloc[0]
        print(f"测试股票: {test_symbol}")
        
        stock_data = provider.get_stock_daily(
            test_symbol, 
            "2024-12-01", 
            "2024-12-31"
        )
        
        if stock_data is not None:
            print(f"股票数据条数: {len(stock_data)}")
            print("股票数据列名:", list(stock_data.columns))
        else:
            print("股票数据获取失败")

def main():
    """主测试函数"""
    print("数据仓库功能测试开始")
    
    try:
        test_github_repo()
        test_integrated_provider()
        
        print("\n" + "=" * 50)
        print("测试完成")
        print("=" * 50)
        
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()