#!/usr/bin/env python3
"""
生产级全量历史数据采集脚本
采集最近10年的A股数据并上传到GitHub仓库

功能特点:
- 基础信息统一存储（basic_info.json）
- 日线数据按日期分割（daily_data/YYYY-MM-DD.json）
- 智能错误处理和重试机制
- 进度跟踪和详细报告
- API限制友好的批处理策略
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import time
import logging

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "python"))

from stock.data import IntegratedDataProvider, DataUploader
from stock.data.akshare_provider import AkShareProvider
from stock.config import get_github_token

# 配置日志 - 修复编码问题
import io
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if hasattr(sys.stderr, 'buffer'):  
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/full_data_fetch.log', encoding='utf-8'),
        logging.StreamHandler()
    ],
    force=True
)
logger = logging.getLogger(__name__)

class FullDataCollector:
    """全量数据采集器"""
    
    def __init__(self):
        self.token = get_github_token()
        if not self.token:
            raise ValueError("GitHub Token未配置")
        
        self.provider = IntegratedDataProvider(auto_upload=True)
        self.akshare = AkShareProvider()
        self.uploader = DataUploader()
        
        # 统计信息
        self.stats = {
            'total_stocks': 0,
            'processed_stocks': 0,
            'successful_stocks': 0,
            'failed_stocks': 0,
            'total_records': 0,
            'start_time': datetime.now(),
            'errors': []
        }
    
    def collect_basic_info(self) -> bool:
        """采集基础信息"""
        logger.info("开始采集股票基础信息...")
        
        try:
            basic_data = self.provider.get_stock_basic()
            if basic_data is None or len(basic_data) == 0:
                logger.error("无法获取基础信息")
                return False
            
            self.stats['total_stocks'] = len(basic_data)
            logger.info(f"基础信息采集完成: {len(basic_data)}只股票")
            return True
            
        except Exception as e:
            logger.error(f"基础信息采集失败: {e}")
            self.stats['errors'].append(f"基础信息采集: {e}")
            return False
    
    def get_stock_list(self) -> list:
        """获取股票代码列表"""
        try:
            basic_data = self.provider.get_stock_basic()
            if basic_data is None:
                return []
            
            # 优先使用symbol列，fallback到ts_code
            if 'symbol' in basic_data.columns:
                stock_list = basic_data['symbol'].tolist()
            elif 'ts_code' in basic_data.columns:
                stock_list = basic_data['ts_code'].tolist()
            else:
                logger.error("无法找到股票代码列")
                return []
            
            # 过滤掉无效代码
            valid_stocks = [s for s in stock_list if s and str(s).strip()]
            logger.info(f"获取到有效股票代码: {len(valid_stocks)}只")
            
            return valid_stocks
            
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            return []
    
    def collect_historical_data(self, years: int = 10, batch_size: int = 50):
        """分批采集历史数据"""
        logger.info(f"开始采集最近{years}年历史数据...")
        
        # 获取股票列表
        stock_list = self.get_stock_list()
        if not stock_list:
            logger.error("无法获取股票列表")
            return False
        
        # 取前300只股票进行演示（避免API限制）
        selected_stocks = stock_list[:300]
        logger.info(f"选择采集股票数量: {len(selected_stocks)}")
        
        # 计算日期范围
        end_date = datetime.now()
        start_date = end_date - timedelta(days=years*365)
        
        logger.info(f"数据范围: {start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}")
        
        # 按月分批处理
        current_date = start_date
        batch_count = 0
        
        while current_date < end_date:
            batch_count += 1
            batch_end = min(current_date + timedelta(days=30), end_date)
            
            logger.info(f"批次 {batch_count}: {current_date.strftime('%Y-%m-%d')} ~ {batch_end.strftime('%Y-%m-%d')}")
            
            success = self._process_date_batch(
                selected_stocks[:batch_size],  # 每批处理50只股票
                current_date.strftime('%Y-%m-%d'),  # 修改为YYYY-MM-DD格式
                batch_end.strftime('%Y-%m-%d'),     # 修改为YYYY-MM-DD格式
                batch_end.strftime('%Y-%m-%d')
            )
            
            if success:
                logger.info(f"批次 {batch_count} 处理成功")
            else:
                logger.warning(f"批次 {batch_count} 处理失败")
            
            current_date = batch_end + timedelta(days=1)
            
            # 批次间休息
            if current_date < end_date:
                logger.info("批次间休息10秒...")
                time.sleep(10)
        
        return True
    
    def _process_date_batch(self, stocks: list, start_date: str, end_date: str, target_date: str) -> bool:
        """处理单个日期批次"""
        try:
            batch_data = []
            success_count = 0
            fail_count = 0
            
            for i, stock in enumerate(stocks):
                if i > 0 and i % 10 == 0:
                    logger.info(f"   进度: {i}/{len(stocks)} ({i/len(stocks)*100:.1f}%)")
                
                try:
                    # 获取单只股票数据
                    daily_data = self.akshare.get_daily_price([stock], start_date, end_date)
                    
                    if daily_data is not None and len(daily_data) > 0:
                        batch_data.append(daily_data)
                        success_count += 1
                        self.stats['total_records'] += len(daily_data)
                    else:
                        fail_count += 1
                    
                    # 每10只股票短暂休息
                    if i % 10 == 0:
                        time.sleep(1)
                        
                except Exception as e:
                    logger.warning(f"   股票 {stock} 处理失败: {e}")
                    fail_count += 1
                    continue
            
            # 合并批次数据并上传
            if batch_data:
                combined_data = pd.concat(batch_data, ignore_index=True)
                logger.info(f"   📊 批次数据: {len(combined_data)}条记录")
                
                # 上传数据
                upload_success = self.uploader.upload_daily_data(combined_data, target_date)
                
                if upload_success:
                    logger.info(f"   数据上传成功")
                    self.stats['successful_stocks'] += success_count
                    return True
                else:
                    logger.error(f"   数据上传失败")
                    return False
            else:
                logger.warning(f"   批次无有效数据")
                return False
                
        except Exception as e:
            logger.error(f"批次处理失败: {e}")
            self.stats['errors'].append(f"批次处理: {e}")
            return False
    
    def generate_report(self):
        """生成采集报告"""
        duration = datetime.now() - self.stats['start_time']
        
        report = f"""
╔══════════════════════════════════════╗
║         全量数据采集完成报告            ║
╚══════════════════════════════════════╝

📊 采集统计:
   - 总股票数: {self.stats['total_stocks']}
   - 处理股票数: {self.stats['processed_stocks']}
   - 成功股票数: {self.stats['successful_stocks']}
   - 失败股票数: {self.stats['failed_stocks']}
   - 总记录数: {self.stats['total_records']}

⏱️  时间统计:
   - 开始时间: {self.stats['start_time'].strftime('%Y-%m-%d %H:%M:%S')}
   - 结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
   - 总耗时: {duration}

📈 成功率: {(self.stats['successful_stocks'] / max(1, self.stats['total_stocks']) * 100):.1f}%

🎯 数据存储:
   - GitHub仓库: test3207/stock-data
   - 基础信息: basic_info.json
   - 日线数据: daily_data/YYYY-MM-DD.json

"""
        
        if self.stats['errors']:
            report += f"\n❌ 错误记录 ({len(self.stats['errors'])}条):\n"
            for i, error in enumerate(self.stats['errors'][:10], 1):
                report += f"   {i}. {error}\n"
            if len(self.stats['errors']) > 10:
                report += f"   ... 和其他 {len(self.stats['errors']) - 10} 个错误\n"
        
        logger.info(report)
        return report

def main():
    """主函数"""
    print("🚀 生产级全量历史数据采集")
    print("=" * 60)
    
    try:
        collector = FullDataCollector()
        
        # 步骤1: 采集基础信息
        if not collector.collect_basic_info():
            logger.error("基础信息采集失败，退出")
            return
        
        # 步骤2: 采集历史数据
        collector.collect_historical_data(years=10, batch_size=50)
        
        # 步骤3: 生成报告
        collector.generate_report()
        
        logger.info("🎉 全量数据采集流程完成！")
        
    except Exception as e:
        logger.error(f"采集流程出现异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()