#!/usr/bin/env python3
"""
测试跳过已存在数据的功能
"""

import pandas as pd
import sys
import os

# 添加python包路径
sys.path.append('python')

from stock.data.data_uploader import DataUploader

def test_skip_existing():
    """测试跳过已存在文件的功能"""
    
    # 创建测试数据
    test_data = pd.DataFrame({
        'symbol': ['000001.SZ'] * 3,
        'trade_date': ['20151228', '20151229', '20151230'],
        'open': [11.0, 11.1, 11.2],
        'high': [11.5, 11.6, 11.7],
        'low': [10.8, 10.9, 11.0],
        'close': [11.2, 11.3, 11.4],
        'vol': [1000, 1100, 1200],
        'amount': [110000, 121000, 132000]
    })
    
    print("🧪 测试跳过已存在数据功能")
    print(f"测试数据: {len(test_data)}条记录")
    
    # 初始化上传器
    uploader = DataUploader()
    
    # 第一次上传 - 应该创建新文件
    print("\n1️⃣ 第一次上传 (应该创建新文件):")
    result1 = uploader.upload_daily_data(test_data, "2015-12-28", skip_existing=False)
    print(f"第一次上传结果: {result1}")
    
    # 第二次上传 - 应该跳过已存在文件
    print("\n2️⃣ 第二次上传 (应该跳过已存在文件):")
    result2 = uploader.upload_daily_data(test_data, "2015-12-28", skip_existing=True)
    print(f"第二次上传结果: {result2}")
    
    print("\n✅ 测试完成！查看输出日志中的'跳过'和'新增'统计信息")

if __name__ == "__main__":
    test_skip_existing()