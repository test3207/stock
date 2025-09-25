#!/usr/bin/env python3
"""
测试akshare数据格式
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "python"))

from stock.data import AkShareProvider

def test_akshare_format():
    """测试akshare返回的数据格式"""
    print("测试akshare数据格式...")
    
    provider = AkShareProvider()
    
    try:
        # 测试获取数据
        data = provider.get_daily_price(['000001.SZ'], '2024-12-20', '2024-12-24')
        
        if data is not None and not data.empty:
            print(f"✅ 获取数据成功: {len(data)} 条记录")
            print(f"📊 列名: {list(data.columns)}")
            print(f"📅 数据类型:")
            for col in data.columns:
                print(f"  {col}: {data[col].dtype}")
            
            print("\n前3条记录:")
            print(data.head(3))
            
            # 检查是否有我们需要的列
            required_cols = ['ts_code', 'trade_date']
            missing_cols = [col for col in required_cols if col not in data.columns]
            
            if missing_cols:
                print(f"❌ 缺少必要列: {missing_cols}")
            else:
                print(f"✅ 包含必要列: {required_cols}")
                
        else:
            print("❌ 获取数据失败")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_akshare_format()