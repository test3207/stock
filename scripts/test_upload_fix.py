"""
测试数据上传修复
"""
import os
import sys
import pandas as pd
from datetime import datetime

# 添加路径
sys.path.append(os.path.join('.', 'python'))

from stock.data import DataUploader
from stock.data.akshare_provider import AkShareProvider
from stock.config import get_github_token

def test_upload_fix():
    """测试上传修复"""
    print("🔧 测试数据上传修复...")
    
    # 验证token
    token = get_github_token()
    if not token:
        print("❌ GitHub Token未配置")
        return False
    
    # 初始化组件
    provider = AkShareProvider()
    uploader = DataUploader()
    
    # 获取少量测试数据
    print("📦 获取测试数据...")
    test_data = provider.get_daily_price(['000001.SZ', '000002.SZ'], '2025-09-23', '2025-09-25')
    
    if test_data is None or len(test_data) == 0:
        print("❌ 测试数据获取失败")
        return False
    
    print(f"✅ 测试数据: {len(test_data)}条记录")
    print(f"📊 数据列: {list(test_data.columns)}")
    
    # 测试上传
    print("🚀 测试上传...")
    success = uploader.upload_daily_data(test_data, "2025-09-23")
    
    if success:
        print("✅ 上传测试成功!")
        return True
    else:
        print("❌ 上传测试失败")
        return False

if __name__ == "__main__":
    test_upload_fix()