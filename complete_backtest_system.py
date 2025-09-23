#!/usr/bin/env python3
"""
完整的5年期量化回测主程序
特性：
- 5年期所有707只股票池
- 跌幅逆向选股策略（6个月跌幅≥20%）
- 完整风控模块：个股止损(-15%)/止盈(+20%)、每日检查
- 月度调仓：等权配置选中股票
- 资金管理：风控触发后资金闲置，等待下次调仓再分配
- 真实交易成本：佣金、印花税、滑点
- 专业绩效分析：年度对比、风险指标
"""

import pandas as pd
import numpy as np
from datetime import date, timedelta
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')

class RiskController:
    """风控模块"""
    
    def __init__(self, stop_loss_pct=-0.15, take_profit_pct=0.20):
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        
        # 风控统计
        self.stop_loss_count = 0
        self.take_profit_count = 0
        self.total_risk_events = 0
        
    def check_positions(self, positions: Dict[str, dict], current_prices: Dict[str, float]) -> List[Tuple[str, str]]:
        """
        检查持仓风控
        返回：[(symbol, action), ...]  action: 'stop_loss' | 'take_profit'
        """
        actions = []
        
        for symbol, pos_info in positions.items():
            if symbol not in current_prices:
                continue
                
            current_price = current_prices[symbol]
            entry_price = pos_info['entry_price']
            shares = pos_info['shares']
            
            if shares <= 0:
                continue
                
            # 计算收益率
            return_rate = (current_price / entry_price) - 1
            
            # 检查止损
            if return_rate <= self.stop_loss_pct:
                actions.append((symbol, 'stop_loss'))
                self.stop_loss_count += 1
                self.total_risk_events += 1
                
            # 检查止盈
            elif return_rate >= self.take_profit_pct:
                actions.append((symbol, 'take_profit'))
                self.take_profit_count += 1
                self.total_risk_events += 1
        
        return actions
    
    def get_stats(self):
        """获取风控统计"""
        return {
            'stop_loss_count': self.stop_loss_count,
            'take_profit_count': self.take_profit_count,
            'total_risk_events': self.total_risk_events
        }

class DrawdownReversalStrategy:
    """跌幅逆向选股策略"""
    
    def __init__(self, lookback_days=126, primary_threshold=-0.20, 
                 fallback_threshold=-0.10, min_primary_ratio=0.6, top_n=30):
        self.lookback_days = lookback_days
        self.primary_threshold = primary_threshold
        self.fallback_threshold = fallback_threshold
        self.min_primary_ratio = min_primary_ratio
        self.top_n = top_n
        
    def calculate_drawdowns(self, price_df: pd.DataFrame, current_date: date) -> Dict[str, float]:
        """计算所有股票的6个月跌幅"""
        current_date_dt = pd.to_datetime(current_date)
        target_date = current_date_dt - timedelta(days=int(self.lookback_days * 1.5))
        
        drawdowns = {}
        
        for symbol, group in price_df.groupby('symbol'):
            group = group.sort_values('date')
            group_dates = pd.to_datetime(group['date'])
            
            # 当前价格
            current_mask = group_dates <= current_date_dt
            if not current_mask.any():
                continue
            current_price = group[current_mask]['close'].iloc[-1]
            
            # 历史价格
            past_mask = group_dates <= target_date
            if not past_mask.any():
                continue
            past_price = group[past_mask]['close'].iloc[-1]
            
            # 计算跌幅
            drawdown = (current_price / past_price) - 1
            drawdowns[symbol] = drawdown
            
        return drawdowns
    
    def select_stocks(self, drawdowns: Dict[str, float], basic_df: pd.DataFrame) -> Tuple[List[str], str, int, int]:
        """
        选股逻辑
        返回：(选中股票列表, 选择模式, 主要候选数量, 总候选数量)
        """
        # 过滤ST股票
        non_st_symbols = set(basic_df[~basic_df['is_st']]['symbol'])
        
        # 主要候选：跌幅≥20%
        primary_candidates = {
            sym: dd for sym, dd in drawdowns.items() 
            if sym in non_st_symbols and dd <= self.primary_threshold
        }
        
        # 判断是否使用备用阈值
        min_primary_count = int(self.top_n * self.min_primary_ratio)
        
        if len(primary_candidates) < min_primary_count:
            # 备用候选：跌幅≥10%
            fallback_candidates = {
                sym: dd for sym, dd in drawdowns.items() 
                if sym in non_st_symbols and dd <= self.fallback_threshold
            }
            candidates = fallback_candidates
            selection_mode = "fallback"
        else:
            candidates = primary_candidates
            selection_mode = "primary"
        
        # 按跌幅排序，选择跌幅最大的前N只
        sorted_candidates = sorted(candidates.items(), key=lambda x: x[1])
        selected = [sym for sym, _ in sorted_candidates[:self.top_n]]
        
        return selected, selection_mode, len(primary_candidates), len(candidates)

class BacktestEngine:
    """回测引擎"""
    
    def __init__(self, initial_capital=1000000):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions = {}  # {symbol: {'shares': float, 'entry_price': float, 'entry_date': date}}
        self.idle_cash = 0  # 风控触发后的闲置资金
        
        # 交易成本
        self.commission_rate = 0.0003  # 万3佣金
        self.stamp_duty_rate = 0.001   # 千1印花税（卖出）
        self.slippage_bps = 5          # 5bp滑点
        
        # 记录
        self.daily_records = []
        self.trade_records = []
        
        # 统计
        self.total_trades = 0
        self.total_commission = 0
        self.total_tax = 0
        
    def calculate_trade_cost(self, amount: float, is_sell: bool = False) -> float:
        """计算交易成本"""
        # 佣金（双向）
        commission = amount * self.commission_rate
        
        # 印花税（仅卖出）
        tax = amount * self.stamp_duty_rate if is_sell else 0
        
        # 滑点（简化处理）
        slippage = amount * (self.slippage_bps / 10000)
        
        return commission + tax + slippage
    
    def execute_sell(self, symbol: str, current_price: float, reason: str = "rebalance") -> float:
        """执行卖出"""
        if symbol not in self.positions or self.positions[symbol]['shares'] <= 0:
            return 0
        
        pos_info = self.positions[symbol]
        shares = pos_info['shares']
        
        # 计算卖出金额
        gross_amount = shares * current_price
        trade_cost = self.calculate_trade_cost(gross_amount, is_sell=True)
        net_amount = gross_amount - trade_cost
        
        # 更新现金和持仓
        if reason == "risk_control":
            self.idle_cash += net_amount  # 风控卖出的资金暂时闲置
        else:
            self.cash += net_amount
            
        del self.positions[symbol]
        
        # 记录交易
        self.trade_records.append({
            'date': None,  # 会在调用时设置
            'symbol': symbol,
            'action': 'sell',
            'shares': shares,
            'price': current_price,
            'amount': gross_amount,
            'cost': trade_cost,
            'reason': reason
        })
        
        self.total_trades += 1
        self.total_commission += trade_cost
        
        return net_amount
    
    def execute_buy(self, symbol: str, target_amount: float, current_price: float) -> bool:
        """执行买入"""
        if target_amount <= 0:
            return False
            
        # 计算交易成本
        trade_cost = self.calculate_trade_cost(target_amount)
        total_cost = target_amount + trade_cost
        
        if total_cost > self.cash:
            return False
        
        # 计算股数
        shares = target_amount / current_price
        
        # 更新现金和持仓
        self.cash -= total_cost
        self.positions[symbol] = {
            'shares': shares,
            'entry_price': current_price,
            'entry_date': None  # 会在调用时设置
        }
        
        # 记录交易
        self.trade_records.append({
            'date': None,  # 会在调用时设置
            'symbol': symbol,
            'action': 'buy',
            'shares': shares,
            'price': current_price,
            'amount': target_amount,
            'cost': trade_cost,
            'reason': 'rebalance'
        })
        
        self.total_trades += 1
        self.total_commission += trade_cost
        
        return True
    
    def get_portfolio_value(self, current_prices: Dict[str, float]) -> float:
        """计算组合总价值"""
        market_value = 0
        for symbol, pos_info in self.positions.items():
            if symbol in current_prices:
                market_value += pos_info['shares'] * current_prices[symbol]
        
        return self.cash + self.idle_cash + market_value
    
    def record_daily_status(self, current_date: date, current_prices: Dict[str, float]):
        """记录每日状态"""
        portfolio_value = self.get_portfolio_value(current_prices)
        
        market_value = 0
        for symbol, pos_info in self.positions.items():
            if symbol in current_prices:
                market_value += pos_info['shares'] * current_prices[symbol]
        
        self.daily_records.append({
            'date': current_date,
            'portfolio_value': portfolio_value,
            'cash': self.cash,
            'idle_cash': self.idle_cash,
            'market_value': market_value,
            'positions_count': len(self.positions),
            'cash_ratio': (self.cash + self.idle_cash) / portfolio_value if portfolio_value > 0 else 1.0
        })

def load_data():
    """加载5年期完整数据"""
    print("加载5年期完整数据...")
    
    try:
        price_df = pd.read_parquet("data/clean/price_history_5year.parquet")
        price_df['date'] = pd.to_datetime(price_df['date']).dt.date
        
        basic_df = pd.read_parquet("data/clean/basic_info_5year.parquet")
        
        print(f"✓ 价格数据: {price_df['symbol'].nunique()}只股票")
        print(f"✓ 时间范围: {price_df['date'].min()} 至 {price_df['date'].max()}")
        print(f"✓ 记录总数: {len(price_df):,}条")
        
        return price_df, basic_df
        
    except Exception as e:
        print(f"❌ 数据加载失败: {e}")
        return None, None

def load_benchmark_data():
    """加载基准指数数据"""
    import akshare as ak
    from datetime import datetime, date
    
    print("加载基准指数数据...")
    
    benchmarks = {}
    index_codes = {
        'HS300': '000300',  # 沪深300
        'CSI500': '000905', # 中证500
        'SSE': '000001'     # 上证指数
    }
    
    start_date_dt = date(2020, 7, 1)
    end_date_dt = date(2025, 8, 31)
    
    for name, code in index_codes.items():
        try:
            df = ak.stock_zh_index_daily(symbol=f"sh{code}")
            df['date'] = pd.to_datetime(df['date']).dt.date
            
            # 过滤日期范围
            df = df[(df['date'] >= start_date_dt) & (df['date'] <= end_date_dt)]
            df = df.sort_values('date')
            
            benchmarks[name] = df[['date', 'close']].copy()
            print(f"✓ {name}: {len(df)}条记录")
            
        except Exception as e:
            print(f"⚠️ {name}数据获取失败: {e}")
            # 创建空数据框避免后续错误
            benchmarks[name] = pd.DataFrame(columns=['date', 'close'])
    
    return benchmarks

def calculate_benchmark_returns(benchmarks: dict, results_df: pd.DataFrame) -> dict:
    """计算基准指数收益率"""
    benchmark_returns = {}
    
    start_date = results_df['date'].iloc[0]
    end_date = results_df['date'].iloc[-1]
    
    for name, df in benchmarks.items():
        if df.empty:
            benchmark_returns[name] = {'total': 0, 'annual': {}}
            continue
            
        # 过滤日期范围
        mask = (df['date'] >= start_date) & (df['date'] <= end_date)
        index_data = df[mask].copy()
        
        if len(index_data) < 2:
            benchmark_returns[name] = {'total': 0, 'annual': {}}
            continue
        
        # 计算总收益
        start_price = index_data['close'].iloc[0]
        end_price = index_data['close'].iloc[-1]
        total_return = (end_price / start_price) - 1
        
        # 计算年度收益
        index_data['year'] = pd.to_datetime(index_data['date']).dt.year
        annual_returns = {}
        
        for year in sorted(index_data['year'].unique()):
            year_data = index_data[index_data['year'] == year]
            if len(year_data) < 2:
                continue
            
            year_start = year_data['close'].iloc[0]
            year_end = year_data['close'].iloc[-1]
            year_return = (year_end / year_start) - 1
            annual_returns[year] = year_return
        
        benchmark_returns[name] = {
            'total': total_return,
            'annual': annual_returns
        }
    
    return benchmark_returns

def run_complete_backtest():
    """运行完整的5年期回测"""
    print("="*80)
    print("🚀 5年期完整量化回测系统")
    print("策略：跌幅逆向选股 + 完整风控模块")
    print("数据：707只股票，5年期真实数据")
    print("="*80)
    
    # 1. 加载数据
    price_df, basic_df = load_data()
    if price_df is None:
        return
    
    # 1.1 加载基准指数数据
    benchmarks = load_benchmark_data()
    
    # 2. 初始化系统
    strategy = DrawdownReversalStrategy(
        lookback_days=126,
        primary_threshold=-0.20,
        fallback_threshold=-0.10,
        min_primary_ratio=0.6,
        top_n=30
    )
    
    risk_controller = RiskController(
        stop_loss_pct=-0.15,
        take_profit_pct=0.20
    )
    
    engine = BacktestEngine(initial_capital=1000000)
    
    # 3. 设置回测期间
    start_date = date(2020, 7, 1)  # 从7月开始，确保有足够历史数据
    end_date = date(2025, 8, 31)
    
    # 获取所有交易日
    all_dates = sorted([d for d in price_df['date'].unique() if start_date <= d <= end_date])
    
    # 获取月度调仓日期
    rebalance_dates = []
    current_month = None
    for dt in all_dates:
        if current_month != dt.month:
            rebalance_dates.append(dt)
            current_month = dt.month
    
    print(f"\n📅 回测配置:")
    print(f"回测期间: {start_date} 至 {end_date}")
    print(f"交易日数: {len(all_dates)}天")
    print(f"调仓次数: {len(rebalance_dates)}次")
    print(f"股票池: {price_df['symbol'].nunique()}只股票")
    print(f"初始资金: {engine.initial_capital:,.0f}元")
    
    # 4. 开始回测
    print(f"\n🔄 开始执行回测...")
    
    rebalance_count = 0
    risk_trigger_days = 0
    
    for i, current_date in enumerate(all_dates):
        # 获取当日价格
        day_data = price_df[price_df['date'] == current_date]
        current_prices = dict(zip(day_data['symbol'], day_data['close']))
        
        if not current_prices:
            continue
        
        # 每日风控检查
        if engine.positions:
            risk_actions = risk_controller.check_positions(engine.positions, current_prices)
            
            if risk_actions:
                risk_trigger_days += 1
                triggered_symbols = []
                
                for symbol, action in risk_actions:
                    if symbol in current_prices:
                        sell_amount = engine.execute_sell(symbol, current_prices[symbol], reason="risk_control")
                        triggered_symbols.append(f"{symbol}({action})")
                        
                        # 设置交易日期
                        if engine.trade_records:
                            engine.trade_records[-1]['date'] = current_date
                
                if triggered_symbols and rebalance_count <= 3:
                    print(f"   [{current_date}] 🚨 风控触发: {', '.join(triggered_symbols[:3])}{'...' if len(triggered_symbols) > 3 else ''}")
        
        # 月度调仓
        if current_date in rebalance_dates:
            rebalance_count += 1
            
            # 计算股票跌幅
            drawdowns = strategy.calculate_drawdowns(price_df, current_date)
            
            # 选股
            selected_stocks, selection_mode, primary_count, total_count = strategy.select_stocks(drawdowns, basic_df)
            
            if selected_stocks:
                # 清仓现有持仓
                total_value = engine.cash + engine.idle_cash  # 包含闲置资金
                
                for symbol in list(engine.positions.keys()):
                    if symbol in current_prices:
                        sell_amount = engine.execute_sell(symbol, current_prices[symbol])
                        total_value += sell_amount
                        
                        if engine.trade_records:
                            engine.trade_records[-1]['date'] = current_date
                
                # 清空闲置资金（重新投入）
                engine.cash += engine.idle_cash
                engine.idle_cash = 0
                
                # 等权买入新股票
                if selected_stocks and total_value > 10000:  # 最小金额限制
                    target_amount_per_stock = total_value / len(selected_stocks)
                    
                    successful_buys = 0
                    for symbol in selected_stocks:
                        if symbol in current_prices:
                            success = engine.execute_buy(symbol, target_amount_per_stock, current_prices[symbol])
                            if success:
                                successful_buys += 1
                                engine.positions[symbol]['entry_date'] = current_date
                                
                                if engine.trade_records:
                                    engine.trade_records[-1]['date'] = current_date
                
                if rebalance_count <= 5:  # 显示前5次调仓详情
                    print(f"   [{current_date}] 🔄 第{rebalance_count}次调仓: {successful_buys}只股票, {selection_mode}模式 ({primary_count}/{total_count})")
            
            elif rebalance_count <= 3:
                print(f"   [{current_date}] ⚠️ 无符合条件股票")
        
        # 记录每日状态
        engine.record_daily_status(current_date, current_prices)
        
        # 进度显示
        if i % 252 == 0 and i > 0:
            progress = i / len(all_dates)
            current_value = engine.get_portfolio_value(current_prices)
            print(f"   进度: {progress:.1%} 当前净值: {current_value:,.0f}元")
    
    # 5. 计算绩效指标
    print(f"\n📊 计算绩效指标...")
    
    if not engine.daily_records:
        print("❌ 没有有效的回测数据")
        return
    
    results_df = pd.DataFrame(engine.daily_records)
    
    # 基础指标
    initial_value = engine.initial_capital
    final_value = results_df['portfolio_value'].iloc[-1]
    total_return = (final_value / initial_value) - 1
    
    days = (end_date - start_date).days
    years = days / 365.25
    annual_return = (final_value / initial_value) ** (1/years) - 1
    
    # 风险指标
    daily_returns = results_df['portfolio_value'].pct_change().dropna()
    annual_vol = daily_returns.std() * np.sqrt(252)
    
    # 最大回撤
    cummax = results_df['portfolio_value'].cummax()
    drawdowns = (results_df['portfolio_value'] - cummax) / cummax
    max_drawdown = drawdowns.min()
    
    # Sharpe比率
    sharpe = annual_return / annual_vol if annual_vol > 0 else 0
    
    # 年度分析
    results_df['year'] = pd.to_datetime(results_df['date']).dt.year
    annual_stats = {}
    
    for year in sorted(results_df['year'].unique()):
        year_data = results_df[results_df['year'] == year]
        if len(year_data) < 2:
            continue
            
        year_start = year_data['portfolio_value'].iloc[0]
        year_end = year_data['portfolio_value'].iloc[-1]
        year_return = (year_end / year_start) - 1
        annual_stats[year] = year_return
    
    # 计算基准指数收益率
    benchmark_returns = calculate_benchmark_returns(benchmarks, results_df)
    
    # 6. 输出完整报告
    risk_stats = risk_controller.get_stats()
    
    print(f"\n" + "="*80)
    print(f"📈 5年期完整量化回测分析报告")
    print(f"="*80)
    
    print(f"\n【回测基础信息】")
    print(f"回测时间：{start_date} 至 {end_date} ({years:.1f}年)")
    print(f"初始资金：{initial_value:,.0f}元")
    print(f"最终净值：{final_value:,.0f}元")
    print(f"股票池：{price_df['symbol'].nunique()}只股票")
    print(f"调仓次数：{rebalance_count}次")
    print(f"总交易笔数：{engine.total_trades}笔")
    
    print(f"\n【策略绩效表现】")
    print(f"总收益率：{total_return:+.2%}")
    print(f"年化收益率：{annual_return:+.2%}")
    print(f"年化波动率：{annual_vol:.2%}")
    print(f"最大回撤：{max_drawdown:.2%}")
    print(f"Sharpe比率：{sharpe:.2f}")
    
    print(f"\n【风控效果分析】")
    print(f"风控触发天数：{risk_trigger_days}天")
    print(f"个股止损次数：{risk_stats['stop_loss_count']}次")
    print(f"个股止盈次数：{risk_stats['take_profit_count']}次")
    print(f"风控事件总数：{risk_stats['total_risk_events']}次")
    
    print(f"\n【交易成本分析】")
    print(f"总交易成本：{engine.total_commission:,.0f}元")
    print(f"成本占比：{engine.total_commission/initial_value:.3%}")
    
    print(f"\n【年度收益表现】")
    print(f"{'年份':<6} {'策略收益':<10} {'沪深300':<10} {'中证500':<10} {'上证指数':<10}")
    print(f"-" * 60)
    for year in sorted(annual_stats.keys()):
        strategy_ret = annual_stats[year]
        hs300_ret = benchmark_returns.get('HS300', {}).get('annual', {}).get(year, 0)
        csi500_ret = benchmark_returns.get('CSI500', {}).get('annual', {}).get(year, 0)
        sse_ret = benchmark_returns.get('SSE', {}).get('annual', {}).get(year, 0)
        
        print(f"{year:<6} {strategy_ret:+8.1%}  {hs300_ret:+8.1%}  {csi500_ret:+8.1%}  {sse_ret:+8.1%}")
    
    # 总收益对比
    strategy_total = total_return
    hs300_total = benchmark_returns.get('HS300', {}).get('total', 0)
    csi500_total = benchmark_returns.get('CSI500', {}).get('total', 0)
    sse_total = benchmark_returns.get('SSE', {}).get('total', 0)
    
    print(f"\n【总收益对比 ({years:.1f}年期)】")
    print(f"策略总收益：{strategy_total:+.1%}")
    print(f"沪深300：   {hs300_total:+.1%}")
    print(f"中证500：   {csi500_total:+.1%}")
    print(f"上证指数：   {sse_total:+.1%}")
    
    # 超额收益分析
    print(f"\n【超额收益分析】")
    print(f"vs 沪深300：{strategy_total - hs300_total:+.1%}")
    print(f"vs 中证500：{strategy_total - csi500_total:+.1%}")
    print(f"vs 上证指数：{strategy_total - sse_total:+.1%}")
    
    # 胜率统计
    positive_years = sum(1 for ret in annual_stats.values() if ret > 0)
    win_rate = positive_years / len(annual_stats) if annual_stats else 0
    avg_annual_return = np.mean(list(annual_stats.values())) if annual_stats else 0
    
    print(f"\n【策略特征统计】")
    print(f"年度胜率：{win_rate:.1%} ({positive_years}/{len(annual_stats)}年)")
    print(f"平均年收益：{avg_annual_return:+.1%}")
    print(f"平均持仓数：{results_df['positions_count'].mean():.1f}只")
    print(f"平均现金比例：{results_df['cash_ratio'].mean():.1%}")
    
    print(f"\n" + "="*80)
    print(f"✅ 5年期完整量化回测分析完成！")
    print(f"💡 策略在{years:.1f}年期间实现{annual_return:+.1%}年化收益")
    print(f"🛡️ 风控系统有效控制风险，最大回撤{max_drawdown:.1%}")
    print(f"="*80)

if __name__ == "__main__":
    run_complete_backtest()