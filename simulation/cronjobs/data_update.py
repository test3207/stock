#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据更新 cronjob 任务
负责更新市场数据、参考数据等
"""

import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List

# 添加项目根路径
sys.path.append(str(Path(__file__).parent.parent.parent))

from simulation.core.cache_manager import CacheManager
from python.stock.data.akshare_provider import AkshareDataProvider

def run_data_update():
    """执行数据更新任务"""
    logger = logging.getLogger("data_update")
    
    try:
        logger.info("开始执行数据更新任务")
        
        # 初始化组件
        cache_manager = CacheManager()
        data_provider = AkshareDataProvider()
        
        # 更新股票基本信息
        success_basic = _update_stock_basic_info(data_provider, cache_manager, logger)
        
        # 更新ST股票列表
        success_st = _update_st_stock_list(data_provider, cache_manager, logger)
        
        # 更新最新价格数据
        success_price = _update_latest_prices(data_provider, cache_manager, logger)
        
        # 清理过期缓存
        cleanup_stats = cache_manager.cleanup_expired_cache()
        logger.info(f"清理过期缓存: {cleanup_stats}")
        
        # 汇总结果
        total_success = success_basic and success_st and success_price
        
        if total_success:
            logger.info("数据更新任务完成")
        else:
            logger.warning("数据更新任务部分失败")
        
        return total_success
        
    except Exception as e:
        logger.error(f"数据更新任务失败: {e}", exc_info=True)
        return False

def _update_stock_basic_info(data_provider: AkshareDataProvider, 
                           cache_manager: CacheManager, logger) -> bool:
    """更新股票基本信息"""
    try:
        logger.info("更新股票基本信息...")
        
        # 获取股票基本信息
        basic_info = data_provider.get_stock_basic_info()
        
        if basic_info is not None and not basic_info.empty:
            # 缓存数据
            cache_key = f"stock_basic_info_{datetime.now().strftime('%Y%m%d')}"
            cache_manager.cache_reference_data(cache_key, basic_info, ttl_hours=24)
            
            logger.info(f"股票基本信息更新完成，共 {len(basic_info)} 条记录")
            return True
        else:
            logger.warning("获取股票基本信息失败")
            return False
            
    except Exception as e:
        logger.error(f"更新股票基本信息失败: {e}")
        return False

def _update_st_stock_list(data_provider: AkshareDataProvider, 
                         cache_manager: CacheManager, logger) -> bool:
    """更新ST股票列表"""
    try:
        logger.info("更新ST股票列表...")
        
        # 获取ST股票列表
        st_stocks = data_provider.get_st_stocks()
        
        if st_stocks is not None:
            # 缓存数据
            cache_key = f"st_stocks_{datetime.now().strftime('%Y%m%d')}"
            cache_manager.cache_reference_data(cache_key, st_stocks, ttl_hours=24)
            
            logger.info(f"ST股票列表更新完成，共 {len(st_stocks)} 只股票")
            return True
        else:
            logger.warning("获取ST股票列表失败")
            return False
            
    except Exception as e:
        logger.error(f"更新ST股票列表失败: {e}")
        return False

def _update_latest_prices(data_provider: AkshareDataProvider, 
                         cache_manager: CacheManager, logger) -> bool:
    """更新最新价格数据"""
    try:
        logger.info("更新最新价格数据...")
        
        # 获取当前日期
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 首先尝试从缓存获取股票列表
        cache_key = f"stock_basic_info_{datetime.now().strftime('%Y%m%d')}"
        basic_info = cache_manager.get_reference_data(cache_key)
        
        if basic_info is None:
            # 如果缓存中没有，直接获取
            basic_info = data_provider.get_stock_basic_info()
            if basic_info is None or basic_info.empty:
                logger.error("无法获取股票列表")
                return False
        
        # 获取所有股票代码
        stock_codes = basic_info['ts_code'].tolist()
        
        # 分批获取价格数据（避免API限制）
        batch_size = 100
        updated_count = 0
        
        for i in range(0, len(stock_codes), batch_size):
            batch_codes = stock_codes[i:i+batch_size]
            
            try:
                # 获取批次价格数据
                price_data = data_provider.get_daily_price(batch_codes, today, today)
                
                if price_data is not None and not price_data.empty:
                    # 缓存批次数据
                    batch_cache_key = f"daily_price_{today}_batch_{i//batch_size}"
                    cache_manager.cache_market_data(batch_cache_key, price_data, ttl_hours=12)
                    updated_count += len(price_data)
                
                # 避免请求过频
                import time
                time.sleep(0.1)
                
            except Exception as e:
                logger.warning(f"获取批次 {i//batch_size} 价格数据失败: {e}")
                continue
        
        logger.info(f"价格数据更新完成，共更新 {updated_count} 条记录")
        return updated_count > 0
        
    except Exception as e:
        logger.error(f"更新价格数据失败: {e}")
        return False

def run_cache_maintenance():
    """执行缓存维护任务"""
    logger = logging.getLogger("cache_maintenance")
    
    try:
        logger.info("开始缓存维护任务")
        
        cache_manager = CacheManager()
        
        # 获取缓存统计
        stats_before = cache_manager.get_cache_stats()
        logger.info(f"维护前缓存统计: {stats_before}")
        
        # 清理过期缓存
        cleanup_stats = cache_manager.cleanup_expired_cache()
        logger.info(f"清理统计: {cleanup_stats}")
        
        # 获取维护后统计
        stats_after = cache_manager.get_cache_stats()
        logger.info(f"维护后缓存统计: {stats_after}")
        
        return True
        
    except Exception as e:
        logger.error(f"缓存维护失败: {e}")
        return False

def run_data_integrity_check() -> Dict:
    """执行数据完整性检查"""
    logger = logging.getLogger("data_integrity")
    
    try:
        logger.info("开始数据完整性检查")
        
        cache_manager = CacheManager()
        check_result = {
            "timestamp": datetime.now().isoformat(),
            "status": "ok",
            "checks": {},
            "issues": []
        }
        
        # 检查基本信息数据
        today_key = f"stock_basic_info_{datetime.now().strftime('%Y%m%d')}"
        basic_info = cache_manager.get_reference_data(today_key)
        
        if basic_info is None:
            check_result["checks"]["basic_info"] = "missing"
            check_result["issues"].append("股票基本信息缺失")
        else:
            check_result["checks"]["basic_info"] = f"ok ({len(basic_info)} records)"
        
        # 检查ST股票数据
        st_key = f"st_stocks_{datetime.now().strftime('%Y%m%d')}"
        st_stocks = cache_manager.get_reference_data(st_key)
        
        if st_stocks is None:
            check_result["checks"]["st_stocks"] = "missing"
            check_result["issues"].append("ST股票列表缺失")
        else:
            check_result["checks"]["st_stocks"] = f"ok ({len(st_stocks)} stocks)"
        
        # 检查价格数据
        today = datetime.now().strftime('%Y-%m-%d')
        price_key = f"daily_price_{today}_batch_0"
        price_data = cache_manager.get_market_data(price_key)
        
        if price_data is None:
            check_result["checks"]["price_data"] = "missing"
            check_result["issues"].append("今日价格数据缺失")
        else:
            check_result["checks"]["price_data"] = f"ok ({len(price_data)} records)"
        
        # 综合评估
        if check_result["issues"]:
            check_result["status"] = "warning"
        
        logger.info(f"数据完整性检查完成: {check_result['status']}")
        return check_result
        
    except Exception as e:
        logger.error(f"数据完整性检查失败: {e}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    # 支持命令行调用
    import argparse
    
    parser = argparse.ArgumentParser(description='执行数据更新任务')
    parser.add_argument('--task', choices=['update', 'maintenance', 'integrity'], 
                       default='update', help='任务类型')
    
    args = parser.parse_args()
    
    # 设置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    if args.task == 'update':
        success = run_data_update()
        sys.exit(0 if success else 1)
    elif args.task == 'maintenance':
        success = run_cache_maintenance()
        sys.exit(0 if success else 1)
    elif args.task == 'integrity':
        result = run_data_integrity_check()
        print(f"完整性检查结果: {result}")
        sys.exit(0)