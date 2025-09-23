from __future__ import annotations
from datetime import date, timedelta
from typing import List
import pandas as pd

# 简化：用 AkShare 交易日历接口或本地生成；这里临时用工作日近似（后续替换为真实交易日）

def generate_trading_days(start: date, end: date) -> List[date]:
    days = []
    cur = start
    while cur <= end:
        if cur.weekday() < 5:  # Monday-Friday
            days.append(cur)
        cur += timedelta(days=1)
    return days

def month_rebalance_days(trading_days: List[date]) -> List[date]:
    df = pd.DataFrame({'date': trading_days})
    df['year_month'] = df['date'].apply(lambda d: d.strftime('%Y-%m'))
    firsts = df.groupby('year_month')['date'].min().tolist()
    return firsts
