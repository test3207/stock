from __future__ import annotations
"""抓取最近5年 HS300+CSI500 成分与日线行情，生成 price_history / basic_info parquet"""
from datetime import date, timedelta
import pandas as pd
import os
from stock.data.akshare_provider import AkShareProvider, HS300_INDEX, CSI500_INDEX
from stock.utils.trading_calendar import generate_trading_days

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
OUT_CLEAN = os.path.join(DATA_DIR, 'clean')
os.makedirs(OUT_CLEAN, exist_ok=True)

def run():
    provider = AkShareProvider()
    end = date.today()
    start = end - timedelta(days=365*5 + 30)  # 5年 + 30天缓冲
    trading_days = generate_trading_days(start, end)
    
    print(f"=== 数据抓取流水线 ===")
    print(f"时间范围: {start} 至 {end}")
    print(f"交易日数: {len(trading_days)}天")
    
    # 扩展股票池：HS300 + CSI500
    print(f"\n获取股票宇宙...")
    hs300_universe = provider.get_index_members(HS300_INDEX, end)
    csi500_universe = provider.get_index_members(CSI500_INDEX, end)
    
    # 合并去重
    universe = list(set(hs300_universe + csi500_universe))
    print(f"HS300成分: {len(hs300_universe)}只")
    print(f"CSI500成分: {len(csi500_universe)}只")
    print(f"合并总数: {len(universe)}只")
    
    # 行情数据
    print(f"\n抓取历史行情...")
    bars = provider.get_daily_bars(type('tmp', (), {
        'symbols': universe, 
        'start': trading_days[0], 
        'end': trading_days[-1], 
        'fields': None
    })())
    
    # 基础信息
    print(f"\n获取基础信息...")
    basic = provider.get_basic_info()
    basic = basic[basic['symbol'].isin(universe)]
    
    # 保存数据
    print(f"\n保存数据到 {OUT_CLEAN}...")
    bars.to_parquet(os.path.join(OUT_CLEAN, 'price_history.parquet'), index=False)
    basic.to_parquet(os.path.join(OUT_CLEAN, 'basic_info.parquet'), index=False)
    
    print(f"\n=== 数据抓取完成 ===")
    print(f"行情数据: {len(bars)}条记录")
    print(f"基础信息: {len(basic)}只股票")
    print(f"时间覆盖: {bars['date'].min()} 至 {bars['date'].max()}")
    print(f"股票覆盖: {bars['symbol'].nunique()}只")

if __name__ == '__main__':
    run()
