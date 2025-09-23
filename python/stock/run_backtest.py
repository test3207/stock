from __future__ import annotations
from datetime import date, timedelta
import pandas as pd
import os
from stock.data.akshare_provider import AkShareProvider, HS300_INDEX
from stock.engine.backtest import Backtester, ExecutionParams
from stock.engine.metrics import performance_metrics
from stock.strategies.drawdown_reversal import DrawdownReversalStrategy
from stock.utils.trading_calendar import generate_trading_days, month_rebalance_days

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'clean')

def load_or_fetch():
    price_path = os.path.join(DATA_DIR, 'price_history.parquet')
    basic_path = os.path.join(DATA_DIR, 'basic_info.parquet')
    if not (os.path.exists(price_path) and os.path.exists(basic_path)):
        from stock.pipeline_fetch import run as fetch_run
        fetch_run()
    prices = pd.read_parquet(price_path)
    basic = pd.read_parquet(basic_path)
    return prices, basic

def main():
    provider = AkShareProvider()
    prices, basic = load_or_fetch()
    # 交易日集合
    trading_days = sorted(prices['date'].unique())
    trading_days = [d for d in trading_days if isinstance(d, (str,)) or True]
    trading_days = [pd.to_datetime(d).date() for d in trading_days]
    # 去掉前 lookback 期，避免窗口不足
    lookback = 126
    if len(trading_days) > lookback:
        trading_days = trading_days[lookback:]
    # 月度调仓日期（在截断之后生成）
    rebal_dates = month_rebalance_days(trading_days)
    # Universe（支持扩展: HS300 / CSI800 / FULLA 由环境变量 UNIVERSE_MODE 控制）
    universe = provider.get_universe(date.today()) if hasattr(provider, 'get_universe') else provider.get_index_members(HS300_INDEX, date.today())
    print(f"[INFO] Universe 大小={len(universe)} (UNIVERSE_MODE={os.environ.get('UNIVERSE_MODE','HS300')})")
    strategy = DrawdownReversalStrategy(top_n=30)
    # 为策略准备 6 个月窗口价格 (这里简单在回测中每个日期提取时传递) —— 为简化，先一次性传
    price_history = prices[['date','symbol','close']]

    class WrapperStrategy(DrawdownReversalStrategy):
        def generate_target_weights(self, trade_date, universe, data_ctx):
            # 提供 price_history / basic
            ctx = {
                'price_history': price_history[price_history['date'] <= trade_date],
                'basic_info': basic
            }
            return super().generate_target_weights(trade_date, universe, ctx)

    wrapped = WrapperStrategy(top_n=30)
    bt = Backtester(provider, wrapped, initial_capital=500000, exec_params=ExecutionParams())
    result = bt.run(trading_days, universe, rebal_dates)
    trades = bt.get_trades()
    metrics = performance_metrics(result, trades)
    print("==== 回测结果摘要 ====")
    print(f"行数:{len(result)}  交易笔数:{len(trades)}  总收益:{metrics.get('total_return'):.2%}  年化:{metrics.get('annual_return'):.2%}  夏普:{metrics.get('sharpe'):.2f}")
    print(f"最大回撤:{metrics.get('max_drawdown'):.2%}  胜率:{metrics.get('winning_day_ratio'):.2%}  年化换手:{(metrics.get('annualized_turnover') or 0):.2f}")
    # 保存结果
    out_dir = os.path.join(DATA_DIR, '..', 'backtest')
    os.makedirs(out_dir, exist_ok=True)
    result.to_parquet(os.path.join(out_dir, 'equity_curve.parquet'))
    trades.to_parquet(os.path.join(out_dir, 'trades.parquet'))
    import json
    with open(os.path.join(out_dir, 'metrics.json'), 'w', encoding='utf-8') as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)
    print(f"结果已保存到: {out_dir}")
    if len(trades) > 0:
        print("示例交易前5行:")
        print(trades.head())
    quick = 'QUICK_MODE' in os.environ and os.environ['QUICK_MODE'] == '1'
    if quick:
        print("[提示] 当前为 QUICK_MODE，仅抓部分股票用于快速验证。移除 QUICK_MODE 后可获得完整结果。")

if __name__ == '__main__':
    main()
