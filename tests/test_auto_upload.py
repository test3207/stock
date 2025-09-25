#!/usr/bin/env python3
"""
测试自动上传功能
演示akshare数据自动上传到GitHub仓库的完整流程
"""

import sys
import os
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "python"))

from stock.data import IntegratedDataProvider

def test_auto_upload():
    """测试自动上传功能"""
    print("=" * 60)
    print("测试 akshare → GitHub 自动上传功能")
    print("=" * 60)
    
    # 创建启用自动上传的集成提供者
    # 注意：需要设置 GITHUB_TOKEN 环境变量才能上传
    provider = IntegratedDataProvider(
        use_github_first=True,
        auto_upload=True  # 启用自动上传
    )
    
    print("\n1. 检查上传功能状态")
    if provider.data_uploader and provider.data_uploader.github_token:
        print("✅ GitHub Token已配置，可以上传数据")
    else:
        print("⚠️ 未配置GitHub Token，只能演示流程（不会实际上传）")
    
    print("\n2. 测试获取股票数据（自动上传模式）")
    # 这个调用会：
    # 1. 先尝试GitHub仓库（失败）
    # 2. 使用akshare获取数据（如果成功）
    # 3. 自动上传akshare数据到GitHub仓库
    
    test_symbol = "000001.SZ"
    start_date = "2024-12-20"
    end_date = "2024-12-24"  # 较短范围以便测试
    
    print(f"获取 {test_symbol} 从 {start_date} 到 {end_date} 的数据...")
    
    data = provider.get_stock_daily(test_symbol, start_date, end_date)
    
    if data is not None:
        print(f"✅ 数据获取成功: {len(data)} 条记录")
        print("📤 如果akshare数据获取成功，已自动尝试上传到GitHub仓库")
        print("数据预览:")
        print(data.head())
    else:
        print("❌ 数据获取失败")
    
    print("\n3. 测试手动上传功能")
    success = provider.manual_upload_data("000002.SZ", "2024-12-23", "2024-12-24")
    if success:
        print("✅ 手动上传成功")
    else:
        print("❌ 手动上传失败")

def test_without_auto_upload():
    """测试不启用自动上传的情况"""
    print("\n" + "=" * 60)
    print("测试 不启用自动上传的模式")
    print("=" * 60)
    
    # 创建不启用自动上传的集成提供者
    provider = IntegratedDataProvider(
        use_github_first=True,
        auto_upload=False  # 不启用自动上传
    )
    
    print("获取数据（不会自动上传）...")
    data = provider.get_stock_daily("000001.SZ", "2024-12-20", "2024-12-21")
    
    if data is not None:
        print(f"✅ 数据获取成功: {len(data)} 条记录")
        print("📝 数据未自动上传（按配置）")
    else:
        print("❌ 数据获取失败")

def main():
    """主测试函数"""
    print("自动上传功能测试开始")
    
    try:
        test_auto_upload()
        test_without_auto_upload()
        
        print("\n" + "=" * 60)
        print("测试完成 - 现在的完整流程：")
        print("1. GitHub仓库无数据 → 尝试akshare")
        print("2. akshare获取成功 → 自动上传到GitHub仓库")
        print("3. 下次访问同样数据 → 直接从GitHub仓库获取")
        print("4. 实现了真正的'akshare → GitHub → 用户'流程！")
        print("=" * 60)
        
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()