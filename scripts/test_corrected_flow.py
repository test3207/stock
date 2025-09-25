"""
测试修正后的数据采集和存储流程
"""
import os
import sys

# 添加路径
sys.path.append(os.path.join('.', 'python'))
sys.path.append('.')

from stable_data_collector import StableDataCollector

def test_corrected_flow():
    """测试修正后的数据流程"""
    print("🔧 测试修正后的数据采集流程...")
    
    try:
        collector = StableDataCollector(max_retries=2, retry_delay=3)
        
        # 测试小规模数据采集：5只股票，30天数据
        success = collector.collect_historical_data_small_batches(
            target_stocks=5,  # 只采集5只股票
            years=0.1  # 只采集最近30天左右数据
        )
        
        if success:
            print("✅ 修正后的数据采集流程测试成功！")
        else:
            print("❌ 数据采集流程测试失败")
            
        return success
        
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        return False

if __name__ == "__main__":
    test_corrected_flow()