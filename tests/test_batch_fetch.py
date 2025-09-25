#!/usr/bin/env python3
"""
测试分批抓取功能
只抓取少量股票进行验证
"""

import sys
import os

# 添加python目录到路径
python_path = os.path.join(os.path.dirname(__file__), 'python')
if python_path not in sys.path:
    sys.path.insert(0, python_path)

from datetime import date, timedelta
from stock.data.akshare_provider import AkShareProvider
from stock.utils.trading_calendar import generate_trading_days

def test_batch_fetch():
    print("=== 测试分批抓取功能 ===")
    
    provider = AkShareProvider()
    end = date.today()
    start = end - timedelta(days=30)  # 只测试最近30天
    trading_days = generate_trading_days(start, end)
    
    # 测试用的少量股票
    test_symbols = ['000001', '000002', '600000', '600036', '000858']
    print(f"测试股票: {test_symbols}")
    print(f"测试期间: {start} 至 {end}")
    
    # 创建请求对象
    req = type('TestReq', (), {
        'symbols': test_symbols,
        'start': trading_days[0] if trading_days else start,
        'end': trading_days[-1] if trading_days else end,
        'fields': None
    })()
    
    # 测试分批抓取
    result = provider.get_daily_bars(req)
    
    if not result.empty:
        print(f"\n✅ 测试成功!")
        print(f"股票数: {result['symbol'].nunique()}")
        print(f"记录数: {len(result)}")
        print(f"日期范围: {result['date'].min()} - {result['date'].max()}")
    else:
        print("\n❌ 测试失败: 未获取到数据")

if __name__ == '__main__':
    test_batch_fetch()