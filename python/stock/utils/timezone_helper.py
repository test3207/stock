#!/usr/bin/env python3
"""
时区感知的时间工具模块
解决系统中的时区处理问题
"""

from datetime import datetime, timezone, timedelta
import pytz
from typing import Optional

# 中国标准时间时区
CST = pytz.timezone('Asia/Shanghai')

def get_cst_now() -> datetime:
    """获取当前中国标准时间"""
    return datetime.now(CST)

def get_utc_now() -> datetime:
    """获取当前UTC时间"""
    return datetime.now(timezone.utc)

def get_trading_date(dt: Optional[datetime] = None) -> str:
    """
    获取交易日期字符串 (YYYY-MM-DD)
    
    Args:
        dt: 指定时间，如果为None则使用当前中国时间
        
    Returns:
        交易日期字符串
    """
    if dt is None:
        dt = get_cst_now()
    elif dt.tzinfo is None:
        # 如果没有时区信息，假设是UTC时间，转换为CST
        dt = dt.replace(tzinfo=timezone.utc).astimezone(CST)
    elif dt.tzinfo != CST:
        # 如果有其他时区信息，转换为CST
        dt = dt.astimezone(CST)
    
    return dt.strftime('%Y-%m-%d')

def get_trading_timestamp(dt: Optional[datetime] = None) -> str:
    """
    获取交易时间戳字符串 (YYYY-MM-DD HH:MM:SS)
    
    Args:
        dt: 指定时间，如果为None则使用当前中国时间
        
    Returns:
        时间戳字符串
    """
    if dt is None:
        dt = get_cst_now()
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc).astimezone(CST)
    elif dt.tzinfo != CST:
        dt = dt.astimezone(CST)
    
    return dt.strftime('%Y-%m-%d %H:%M:%S')

def get_iso_timestamp(dt: Optional[datetime] = None) -> str:
    """
    获取ISO格式时间戳（带时区信息）
    
    Args:
        dt: 指定时间，如果为None则使用当前中国时间
        
    Returns:
        ISO时间戳字符串
    """
    if dt is None:
        dt = get_cst_now()
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc).astimezone(CST)
    elif dt.tzinfo != CST:
        dt = dt.astimezone(CST)
    
    return dt.isoformat()

def is_trading_hours(dt: Optional[datetime] = None) -> bool:
    """
    判断是否在交易时间内
    A股交易时间: 9:30-11:30, 13:00-15:00 (工作日)
    
    Args:
        dt: 指定时间，如果为None则使用当前中国时间
        
    Returns:
        是否在交易时间内
    """
    if dt is None:
        dt = get_cst_now()
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc).astimezone(CST)
    elif dt.tzinfo != CST:
        dt = dt.astimezone(CST)
    
    # 检查是否为工作日 (周一到周五)
    if dt.weekday() >= 5:  # 周六、周日
        return False
    
    time_now = dt.time()
    
    # 上午交易时间: 9:30-11:30
    morning_start = datetime.strptime('09:30', '%H:%M').time()
    morning_end = datetime.strptime('11:30', '%H:%M').time()
    
    # 下午交易时间: 13:00-15:00  
    afternoon_start = datetime.strptime('13:00', '%H:%M').time()
    afternoon_end = datetime.strptime('15:00', '%H:%M').time()
    
    return (morning_start <= time_now <= morning_end) or \
           (afternoon_start <= time_now <= afternoon_end)

def convert_github_actions_time(utc_timestamp: str) -> str:
    """
    将GitHub Actions的UTC时间戳转换为中国时间
    
    Args:
        utc_timestamp: UTC时间戳字符串
        
    Returns:
        中国时间字符串
    """
    try:
        # 解析UTC时间戳
        if 'T' in utc_timestamp:
            if utc_timestamp.endswith('Z'):
                dt = datetime.fromisoformat(utc_timestamp[:-1]).replace(tzinfo=timezone.utc)
            else:
                dt = datetime.fromisoformat(utc_timestamp).replace(tzinfo=timezone.utc)
        else:
            dt = datetime.strptime(utc_timestamp, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
        
        # 转换为中国时间
        cst_dt = dt.astimezone(CST)
        return cst_dt.strftime('%Y-%m-%d %H:%M:%S CST')
    except Exception as e:
        return f"时间转换失败: {e}"

# 向后兼容的函数别名
def now_cst() -> datetime:
    """向后兼容：获取当前中国时间"""
    return get_cst_now()

def today_cst() -> str:
    """向后兼容：获取今日中国时间日期字符串"""
    return get_trading_date()

if __name__ == "__main__":
    # 测试时区处理
    print("=== 时区处理测试 ===")
    print(f"当前UTC时间: {get_utc_now()}")
    print(f"当前中国时间: {get_cst_now()}")
    print(f"交易日期: {get_trading_date()}")
    print(f"交易时间戳: {get_trading_timestamp()}")
    print(f"ISO时间戳: {get_iso_timestamp()}")
    print(f"是否交易时间: {is_trading_hours()}")
    
    # 测试GitHub Actions时间转换
    test_utc = "2025-09-25T03:15:19Z"
    print(f"GitHub时间转换: {test_utc} -> {convert_github_actions_time(test_utc)}")