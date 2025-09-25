"""
优化的数据采集脚本 - 解决网络连接和编码问题
"""
import os
import sys
import time
import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict

# 添加路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'python'))

from stock.data import IntegratedDataProvider, DataUploader
from stock.data.akshare_provider import AkShareProvider
from stock.config import get_github_token

# 修复Windows控制台编码问题
import io
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if hasattr(sys.stderr, 'buffer'):  
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 配置日志
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/stable_data_fetch.log', encoding='utf-8'),
        logging.StreamHandler()
    ],
    force=True
)
logger = logging.getLogger(__name__)

class StableDataCollector:
    """
    稳定的数据采集器 - 优化网络连接和错误处理
    
    数据流转图:
    1. AkShareProvider.get_basic_info() -> 基础信息DataFrame
       格式: {symbol, name, exchange, is_st, market, list_date}
    
    2. AkShareProvider.get_daily_price() -> 日K线DataFrame  
       格式: {ts_code, trade_date, open, high, low, close, vol, amount}
       
    3. DataUploader.upload_basic_info() -> GitHub:basic_info.json
       格式: {last_updated, record_count, records[]}
       
    4. DataUploader.upload_daily_data() -> GitHub:daily_data/{实际交易日期}/{symbol}.json
       格式: [{ts_code, trade_date, open, high, low, close, vol, amount}, ...]
       说明: 按数据中的trade_date字段实际交易日期存储，不按采集批次存储
    
    所有数据结构已验证 2025-09-25
    """
    
    def __init__(self, max_retries: int = 3, retry_delay: int = 5):
        self.token = get_github_token()
        if not self.token:
            raise ValueError("GitHub Token未配置")
        
        self.provider = IntegratedDataProvider(auto_upload=True)
        self.akshare = AkShareProvider()
        self.uploader = DataUploader()
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # 统计信息
        self.stats = {
            'total_batches': 0,
            'successful_batches': 0,
            'failed_batches': 0,
            'total_records': 0,
            'start_time': datetime.now(),
            'errors': []
        }
    
    def collect_with_retry(self, operation_func, *args, **kwargs):
        """带重试机制的操作执行"""
        for attempt in range(self.max_retries):
            try:
                return operation_func(*args, **kwargs)
            except Exception as e:
                logger.warning(f"尝试 {attempt + 1}/{self.max_retries} 失败: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))  # 指数退避
                else:
                    logger.error(f"操作最终失败: {e}")
                    raise
    
    def collect_basic_info(self) -> bool:
        """采集并上传基础信息"""
        try:
            logger.info("🔍 开始采集股票基础信息...")
            
            def _get_basic_info():
                return self.akshare.get_basic_info()
            
            basic_info = self.collect_with_retry(_get_basic_info)
            
            if basic_info is not None and len(basic_info) > 0:
                logger.info(f"✅ 基础信息采集完成: {len(basic_info)}只股票")
                
                # 上传基础信息
                def _upload_basic_info():
                    return self.uploader.upload_basic_info(basic_info)
                
                success = self.collect_with_retry(_upload_basic_info)
                if success:
                    logger.info("✅ 基础信息上传成功")
                    return True
                else:
                    logger.error("❌ 基础信息上传失败")
                    return False
            else:
                logger.error("❌ 基础信息采集失败")
                return False
                
        except Exception as e:
            logger.error(f"❌ 基础信息处理异常: {e}")
            return False
    
    def collect_historical_data_small_batches(self, target_stocks: int = 100, 
                                            years: int = 3, universe: str = 'FULLA') -> bool:
        """
        采集历史数据 - 小批次模式
        
        Args:
            target_stocks: 目标股票数量
            years: 历史数据年数
            universe: 股票池 ('HS300'|'CSI800'|'FULLA')
        """
        try:
            logger.info(f"📈 开始采集历史数据（小批次模式）- 股票池:{universe}")
            
            # 根据股票池获取股票列表
            if universe == 'CSI800':
                def _get_stock_list():
                    # 设置环境变量并获取CSI800成份股
                    import os
                    os.environ['UNIVERSE_MODE'] = 'CSI800'
                    return self.akshare.get_universe(datetime.now().date())
            elif universe == 'HS300':
                def _get_stock_list():
                    # 设置环境变量并获取HS300成份股
                    import os
                    os.environ['UNIVERSE_MODE'] = 'HS300'
                    return self.akshare.get_universe(datetime.now().date())
            else:
                def _get_stock_list():
                    # 获取全A股基础信息
                    basic_info = self.akshare.get_basic_info()
                    return [stock['symbol'] for stock in basic_info]
            
            stock_info = self.collect_with_retry(_get_stock_list)
            if stock_info is None or len(stock_info) == 0:
                logger.error("无法获取股票列表")
                return False
            
            # 获取股票代码列表
            if universe in ['CSI800', 'HS300']:
                # universe方法直接返回股票代码列表
                valid_stocks = stock_info
                logger.info(f"📋 {universe}股票池: {len(valid_stocks)}只股票")
            else:
                # 基础信息需要过滤ST股票（stock_info是股票代码列表）
                valid_stocks = stock_info
                logger.info(f"📋 全A股票池: {len(valid_stocks)}只股票（ST过滤将在交易时进行）")
            
            # 限制股票数量
            if target_stocks > 0 and target_stocks < len(valid_stocks):
                selected_stocks = valid_stocks[:target_stocks]
                logger.info(f"📋 选择股票: {len(selected_stocks)}只 (从{len(valid_stocks)}只中选择)")
            else:
                selected_stocks = valid_stocks
                logger.info(f"📋 选择全部股票: {len(selected_stocks)}只")
            
            # 计算日期范围
            end_date = datetime.now()
            start_date = end_date - timedelta(days=years * 365)
            
            logger.info(f"📅 数据范围: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
            
            # 按月分批处理
            current_date = start_date
            batch_num = 0
            
            while current_date < end_date:
                batch_num += 1
                batch_end = min(current_date + timedelta(days=30), end_date)
                
                start_str = current_date.strftime('%Y-%m-%d')
                end_str = batch_end.strftime('%Y-%m-%d')
                
                logger.info(f"🔄 批次 {batch_num}: {start_str} ~ {end_str}")
                
                success = self._process_small_batch(selected_stocks, start_str, end_str)
                
                self.stats['total_batches'] += 1
                if success:
                    self.stats['successful_batches'] += 1
                    logger.info(f"✅ 批次 {batch_num} 处理成功")
                else:
                    self.stats['failed_batches'] += 1
                    logger.warning(f"⚠️ 批次 {batch_num} 处理失败")
                
                current_date = batch_end + timedelta(days=1)
                
                # 批次间休息
                if current_date < end_date:
                    logger.info("💤 批次间休息5秒...")
                    time.sleep(5)
            
            self._print_statistics()
            return True
            
        except Exception as e:
            logger.error(f"❌ 历史数据采集异常: {e}")
            return False
    
    def _process_small_batch(self, stocks: List[str], start_date: str, end_date: str) -> bool:
        """处理小批次数据"""
        try:
            # 进一步细分 - 每次处理10只股票
            stock_batches = [stocks[i:i+10] for i in range(0, len(stocks), 10)]
            
            all_batch_data = []
            successful_mini_batches = 0
            
            for mini_batch_idx, stock_batch in enumerate(stock_batches):
                logger.info(f"   📦 子批次 {mini_batch_idx + 1}/{len(stock_batches)}: {len(stock_batch)}只股票")
                
                def _get_mini_batch_data():
                    return self.akshare.get_daily_price(stock_batch, start_date, end_date)
                
                try:
                    mini_data = self.collect_with_retry(_get_mini_batch_data)
                    
                    if mini_data is not None and len(mini_data) > 0:
                        all_batch_data.append(mini_data)
                        successful_mini_batches += 1
                        logger.info(f"   ✅ 子批次数据: {len(mini_data)}条记录")
                    else:
                        logger.warning(f"   ⚠️ 子批次无数据")
                    
                    # 子批次间短暂休息
                    time.sleep(2)
                    
                except Exception as e:
                    logger.warning(f"   ❌ 子批次失败: {e}")
                    continue
            
            # 合并并上传数据
            if all_batch_data:
                combined_data = pd.concat(all_batch_data, ignore_index=True)
                logger.info(f"   📊 合并数据: {len(combined_data)}条记录")
                
                # 上传数据（默认跳过已存在文件）
                def _upload_batch_data():
                    return self.uploader.upload_daily_data(combined_data, start_date, skip_existing=True)
                
                upload_success = self.collect_with_retry(_upload_batch_data)
                
                if upload_success:
                    self.stats['total_records'] += len(combined_data)
                    logger.info(f"   ✅ 批次数据上传成功")
                    return True
                else:
                    logger.warning(f"   ❌ 批次数据上传失败")
                    return False
            else:
                logger.warning(f"   ⚠️ 批次无有效数据")
                return False
                
        except Exception as e:
            logger.error(f"❌ 批次处理异常: {e}")
            return False
    
    def _print_statistics(self):
        """打印统计信息"""
        duration = datetime.now() - self.stats['start_time']
        
        logger.info("📊 ==========采集统计==========")
        logger.info(f"⏱️  耗时: {duration}")
        logger.info(f"📦 总批次: {self.stats['total_batches']}")
        logger.info(f"✅ 成功批次: {self.stats['successful_batches']}")
        logger.info(f"❌ 失败批次: {self.stats['failed_batches']}")
        logger.info(f"📈 总记录数: {self.stats['total_records']}")
        
        if self.stats['total_batches'] > 0:
            success_rate = self.stats['successful_batches'] / self.stats['total_batches'] * 100
            logger.info(f"🎯 成功率: {success_rate:.1f}%")

def main():
    """主执行函数"""
    try:
        logger.info("🚀 启动稳定数据采集系统")
        
        collector = StableDataCollector(max_retries=3, retry_delay=5)
        
        # 1. 采集基础信息
        logger.info("=" * 50)
        if not collector.collect_basic_info():
            logger.error("❌ 基础信息采集失败，停止执行")
            return False
        
        # 2. 采集历史数据（CSI800成份股10年数据）
        logger.info("=" * 50)
        success = collector.collect_historical_data_small_batches(
            target_stocks=-1,  # -1表示采集所有CSI800成份股（约800只）
            years=10,  # 10年历史数据
            universe='CSI800'  # 指定CSI800指数成份股
        )
        
        if success:
            logger.info("🎉 数据采集完成！")
        else:
            logger.error("❌ 数据采集失败")
            
        return success
        
    except KeyboardInterrupt:
        logger.info("⚠️ 用户中断操作")
        return False
    except Exception as e:
        logger.error(f"❌ 系统异常: {e}")
        return False

if __name__ == "__main__":
    main()