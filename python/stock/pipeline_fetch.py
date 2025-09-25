from __future__ import annotations
"""抓取最近5年 HS300+CSI500 成分与日线行情，生成 price_history / basic_info parquet"""
from datetime import date, timedelta
import pandas as pd
import os
import json
from stock.data.akshare_provider import AkShareProvider, HS300_INDEX, CSI500_INDEX
from stock.utils.trading_calendar import generate_trading_days

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
OUT_CLEAN = os.path.join(DATA_DIR, 'clean')
OUT_RAW = os.path.join(DATA_DIR, 'raw')
os.makedirs(OUT_CLEAN, exist_ok=True)
os.makedirs(OUT_RAW, exist_ok=True)

def run():
    provider = AkShareProvider()
    end = date.today()
    start = end - timedelta(days=365*5 + 30)  # 5年 + 30天缓冲
    trading_days = generate_trading_days(start, end)
    
    print(f"=== 数据抓取流水线开始执行 ===")
    print(f"执行时间: {pd.Timestamp.now()}")
    print(f"时间范围: {start} 至 {end}")
    print(f"交易日数: {len(trading_days)}天")
    print(f"当前工作目录: {os.getcwd()}")
    print(f"数据输出目录: {OUT_CLEAN}")
    
    # 扩展股票池：HS300 + CSI500
    print(f"\n📊 获取股票宇宙...")
    try:
        print("   正在获取HS300成分股...")
        hs300_universe = provider.get_index_members(HS300_INDEX, end)
        print(f"   ✅ HS300成分: {len(hs300_universe)}只")
        
        print("   正在获取CSI500成分股...")
        csi500_universe = provider.get_index_members(CSI500_INDEX, end)
        print(f"   ✅ CSI500成分: {len(csi500_universe)}只")
        
        # 合并去重
        universe = list(set(hs300_universe + csi500_universe))
        print(f"   🔗 合并去重后总数: {len(universe)}只股票")
        expected_stock_count = len(universe)
        
        # 打印前几只股票作为示例
        if len(universe) > 0:
            print(f"   📋 股票样本 (前10只): {universe[:10]}")
        
    except Exception as e:
        print(f"   ❌ 获取股票宇宙失败: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 检查是否为增量抓取
    existing_data_file = os.path.join(OUT_CLEAN, 'price_history.parquet')
    failed_symbols_file = os.path.join(OUT_RAW, 'failed_symbols.json')
    
    print(f"\n🔍 检查现有数据...")
    print(f"   已有数据文件: {existing_data_file}")
    print(f"   失败记录文件: {failed_symbols_file}")
    
    if os.path.exists(existing_data_file):
        print(f"   🔄 检测到已有数据，启用增量抓取模式...")
        try:
            existing_data = pd.read_parquet(existing_data_file)
            existing_symbols = set(existing_data['symbol'].unique())
            missing_symbols = set(universe) - existing_symbols
            
            print(f"   📈 已有数据股票数: {len(existing_symbols)}")
            print(f"   🆕 需要新增股票数: {len(missing_symbols)}")
            
            if os.path.exists(failed_symbols_file):
                with open(failed_symbols_file, 'r', encoding='utf-8') as f:
                    failed_data = json.load(f)
                failed_symbols = set(failed_data.get('symbols', []))
                print(f"   🔄 检测到失败记录: {len(failed_symbols)}只股票")
                # 优先重试失败的股票
                retry_symbols = failed_symbols.intersection(set(universe))
                missing_symbols = missing_symbols.union(retry_symbols)
                print(f"   🔄 需要重试股票数: {len(retry_symbols)}")
                
        except Exception as e:
            print(f"   ⚠️ 读取已有数据失败: {type(e).__name__}: {e}")
            print(f"   将执行全量抓取...")
            missing_symbols = set(universe)
            existing_data = pd.DataFrame()
        
        if missing_symbols:
            print(f"   📝 需要抓取的股票: {len(missing_symbols)}只")
            print(f"   ✅ 已有数据股票: {len(existing_symbols)}只")
        else:
            print(f"   ✅ 所有股票数据已完整，无需增量抓取")
            universe = []
    else:
        print(f"\n🆕 首次抓取，将获取全部{len(universe)}只股票数据")
        missing_symbols = set(universe)
        existing_data = pd.DataFrame()
    
    # 行情数据抓取
    if universe and missing_symbols:
        print(f"\n📈 开始抓取历史行情数据...")
        print(f"   目标股票数: {len(missing_symbols)}")
        print(f"   时间范围: {trading_days[0]} 至 {trading_days[-1]}")
        
        try:
            bars = provider.get_daily_bars(type('tmp', (), {
                'symbols': list(missing_symbols), 
                'start': trading_days[0], 
                'end': trading_days[-1], 
                'fields': None
            })())
            
            print(f"   ✅ 抓取到 {len(bars)} 条行情记录")
            
            # 合并新老数据
            if not existing_data.empty and not bars.empty:
                print(f"   🔗 合并新旧数据...")
                print(f"      原有数据: {len(existing_data)} 条")
                print(f"      新增数据: {len(bars)} 条")
                bars = pd.concat([existing_data, bars], ignore_index=True)
                # 去重
                bars = bars.drop_duplicates(subset=['symbol', 'date']).sort_values(['symbol', 'date'])
                print(f"      合并后总数: {len(bars)} 条")
            
        except Exception as e:
            print(f"   ❌ 抓取行情数据失败: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            bars = existing_data if not existing_data.empty else pd.DataFrame()
    else:
        bars = existing_data if not missing_symbols else pd.DataFrame()
    
    # 数据完整性校验
    actual_stock_count = bars['symbol'].nunique() if not bars.empty else 0
    success_rate = (actual_stock_count / expected_stock_count * 100) if expected_stock_count > 0 else 0
    
    print(f"\n📊 数据抓取完整性报告:")
    print(f"   预期股票数: {expected_stock_count}只")
    print(f"   实际抓取: {actual_stock_count}只")
    print(f"   成功率: {success_rate:.1f}%")
    
    if success_rate < 80:
        print(f"   ⚠️ 警告: 成功率过低 ({success_rate:.1f}%)，可能存在网络问题")
        missing_symbols = set(universe) - set(bars['symbol'].unique() if not bars.empty else [])
        print(f"   📋 缺失股票数: {len(missing_symbols)}只")
        if len(missing_symbols) <= 20:  # 只显示前20个
            print(f"   📋 缺失股票示例: {list(missing_symbols)[:20]}")
    
    if bars.empty:
        print("❌ 未获取到任何数据，请检查网络连接后重试")
        return
    
    # 基础信息获取
    print(f"\n📋 获取基础信息...")
    try:
        basic = provider.get_basic_info()
        basic = basic[basic['symbol'].isin(universe)]
        print(f"   ✅ 获取到 {len(basic)} 只股票的基础信息")
    except Exception as e:
        print(f"   ❌ 获取基础信息失败: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        basic = pd.DataFrame()
    
    # 保存数据
    print(f"\n💾 保存数据到 {OUT_CLEAN}...")
    try:
        price_file = os.path.join(OUT_CLEAN, 'price_history.parquet')
        basic_file = os.path.join(OUT_CLEAN, 'basic_info.parquet')
        
        bars.to_parquet(price_file, index=False)
        print(f"   ✅ 行情数据保存至: {price_file}")
        
        basic.to_parquet(basic_file, index=False)
        print(f"   ✅ 基础信息保存至: {basic_file}")
        
    except Exception as e:
        print(f"   ❌ 保存数据失败: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print(f"\n=== 数据抓取任务完成 ===")
    print(f"✅ 行情数据: {len(bars):,}条记录")
    print(f"✅ 基础信息: {len(basic)}只股票")
    if not bars.empty:
        print(f"✅ 时间覆盖: {bars['date'].min()} 至 {bars['date'].max()}")
        print(f"✅ 股票覆盖: {actual_stock_count}只 (成功率: {success_rate:.1f}%)")
    
    # 数据质量建议
    if success_rate < 90:
        print(f"\n💡 数据质量改进建议:")
        print(f"   - 当前成功率 {success_rate:.1f}% 偏低，建议:")
        print(f"   - ✓ 检查网络连接稳定性")
        print(f"   - ✓ 可考虑分批次抓取数据")
        print(f"   - ✓ 重新运行脚本进行增量补充")
    else:
        print(f"\n✅ 数据质量良好，成功率达到 {success_rate:.1f}%")
    
    print(f"=" * 50)

if __name__ == '__main__':
    run()
