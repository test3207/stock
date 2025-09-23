from __future__ import annotations
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from datetime import date

# 输入：回测结果 DataFrame: date, equity
# 输出：指标 dict

def performance_metrics(equity_df: pd.DataFrame, trades: pd.DataFrame | None = None, benchmark_df: pd.DataFrame | None = None) -> Dict[str, Any]:
    """
    计算全面的绩效与风险指标
    
    Args:
        equity_df: 包含 date, equity, 以及可选的 turnover, pos_count 等列
        trades: 交易记录 DataFrame
        benchmark_df: 基准净值数据，包含 date, benchmark_value 列
    """
    df = equity_df.sort_values('date').copy()
    if 'equity' not in df.columns or len(df) < 2:
        return {}
    
    df['ret'] = df['equity'].pct_change().fillna(0)
    
    # 基础收益指标
    total_return = df['equity'].iloc[-1] / df['equity'].iloc[0] - 1
    ann_factor = 252
    trading_days = len(df) - 1
    ann_ret = (1 + total_return) ** (ann_factor / max(1, trading_days)) - 1
    ann_vol = df['ret'].std() * (ann_factor ** 0.5)
    sharpe = ann_ret / ann_vol if ann_vol != 0 else 0
    
    # 回撤分析
    cum_max = df['equity'].cummax()
    dd = df['equity'] / cum_max - 1
    max_dd = dd.min()
    calmar = ann_ret / abs(max_dd) if max_dd < 0 else 0
    
    # 计算最大回撤恢复期
    max_dd_recovery_days = _calculate_drawdown_recovery(df['equity'])
    
    # 胜率统计
    winning_days = (df['ret'] > 0).sum()
    losing_days = (df['ret'] < 0).sum()
    winning_ratio = winning_days / max(1, trading_days)
    
    # 换手率分析
    avg_turnover = df['turnover'].mean() if 'turnover' in df.columns else None
    avg_turnover_buy = df['turnover_buy'].mean() if 'turnover_buy' in df.columns else None
    avg_turnover_sell = df['turnover_sell'].mean() if 'turnover_sell' in df.columns else None
    annualized_turnover = avg_turnover * ann_factor if avg_turnover is not None else None
    annualized_turnover_buy = avg_turnover_buy * ann_factor if avg_turnover_buy is not None else None
    annualized_turnover_sell = avg_turnover_sell * ann_factor if avg_turnover_sell is not None else None
    
    # 持仓统计
    position_stats = _calculate_position_stats(df)
    
    # 交易统计
    trade_stats = _calculate_trade_stats(trades)
    
    # 基准比较（如果提供）
    benchmark_stats = _calculate_benchmark_stats(df, benchmark_df) if benchmark_df is not None else {}
    
    # 分年度统计
    yearly_stats = _calculate_yearly_stats(df)
    
    # 风险指标
    risk_stats = _calculate_risk_stats(df)
    
    # 合并所有指标
    metrics = {
        # 基础收益指标
        'total_return': total_return,
        'annual_return': ann_ret,
        'annual_vol': ann_vol,
        'sharpe': sharpe,
        'max_drawdown': max_dd,
        'calmar': calmar,
        'max_drawdown_recovery_days': max_dd_recovery_days,
        
        # 胜率指标
        'winning_day_ratio': winning_ratio,
        'winning_days': int(winning_days),
        'losing_days': int(losing_days),
        
        # 换手率指标
        'avg_daily_turnover': avg_turnover,
        'avg_daily_turnover_buy': avg_turnover_buy,
        'avg_daily_turnover_sell': avg_turnover_sell,
        'annualized_turnover': annualized_turnover,
        'annualized_turnover_buy': annualized_turnover_buy,
        'annualized_turnover_sell': annualized_turnover_sell,
    }
    
    # 添加其他统计
    metrics.update(position_stats)
    metrics.update(trade_stats)
    metrics.update(benchmark_stats)
    metrics.update(risk_stats)
    metrics['yearly_breakdown'] = yearly_stats
    
    return metrics


def _calculate_drawdown_recovery(equity_series: pd.Series) -> int:
    """计算最大回撤恢复期（交易日数）"""
    cum_max = equity_series.cummax()
    dd = equity_series / cum_max - 1
    
    if dd.min() >= 0:
        return 0
    
    max_dd_idx = dd.idxmin()
    max_dd_start_idx = None
    
    # 找到最大回撤开始的位置
    for i in range(max_dd_idx, -1, -1):
        if dd.iloc[i] == 0:
            max_dd_start_idx = i
            break
    
    if max_dd_start_idx is None:
        return -1  # 无法确定开始位置
    
    # 找到恢复点（重新创新高）
    recovery_idx = None
    max_equity_at_start = equity_series.iloc[max_dd_start_idx]
    
    for i in range(max_dd_idx, len(equity_series)):
        if equity_series.iloc[i] >= max_equity_at_start:
            recovery_idx = i
            break
    
    if recovery_idx is None:
        return -1  # 尚未恢复
    
    return recovery_idx - max_dd_start_idx


def _calculate_position_stats(df: pd.DataFrame) -> Dict[str, Any]:
    """计算持仓相关统计"""
    stats = {}
    
    if 'pos_count' in df.columns:
        stats.update({
            'avg_position_count': df['pos_count'].mean(),
            'max_position_count': df['pos_count'].max(),
            'min_position_count': df['pos_count'].min(),
        })
    
    if 'market_value' in df.columns and 'cash' in df.columns:
        total_equity = df['market_value'] + df['cash']
        position_ratio = df['market_value'] / total_equity
        stats.update({
            'avg_position_ratio': position_ratio.mean(),
            'max_position_ratio': position_ratio.max(),
            'min_position_ratio': position_ratio.min(),
        })
    
    return stats


def _calculate_trade_stats(trades: pd.DataFrame | None) -> Dict[str, Any]:
    """计算交易相关统计"""
    if trades is None or trades.empty:
        return {
            'trade_count': 0,
            'buy_trades': 0,
            'sell_trades': 0,
            'avg_trade_size': 0,
            'total_fees': 0,
        }
    
    trade_count = len(trades)
    buy_count = (trades['side'] == 'BUY').sum()
    sell_count = (trades['side'] == 'SELL').sum()
    avg_trade_size = trades['trade_value'].mean()
    total_fees = trades['cost_total'].sum() if 'cost_total' in trades.columns else 0
    
    return {
        'trade_count': trade_count,
        'buy_trades': int(buy_count),
        'sell_trades': int(sell_count),
        'avg_trade_size': avg_trade_size,
        'total_fees': total_fees,
        'fee_ratio': total_fees / trades['trade_value'].sum() if trades['trade_value'].sum() > 0 else 0,
    }


def _calculate_benchmark_stats(df: pd.DataFrame, benchmark_df: pd.DataFrame) -> Dict[str, Any]:
    """计算相对基准的统计指标"""
    # 合并数据，确保日期对齐
    merged = pd.merge(df[['date', 'ret']], benchmark_df[['date', 'benchmark_value']], on='date', how='inner')
    
    if merged.empty:
        return {}
    
    merged['bench_ret'] = merged['benchmark_value'].pct_change().fillna(0)
    merged['excess_ret'] = merged['ret'] - merged['bench_ret']
    
    # 计算信息比率
    excess_mean = merged['excess_ret'].mean()
    excess_std = merged['excess_ret'].std()
    info_ratio = excess_mean / excess_std * (252 ** 0.5) if excess_std > 0 else 0
    
    # 计算 Beta
    if merged['bench_ret'].std() > 0:
        beta = merged[['ret', 'bench_ret']].cov().iloc[0, 1] / merged['bench_ret'].var()
    else:
        beta = 0
    
    # 基准总收益
    benchmark_total_return = merged['benchmark_value'].iloc[-1] / merged['benchmark_value'].iloc[0] - 1
    
    return {
        'information_ratio': info_ratio,
        'beta': beta,
        'excess_return': merged['excess_ret'].sum(),
        'benchmark_total_return': benchmark_total_return,
        'tracking_error': excess_std * (252 ** 0.5),
    }


def _calculate_yearly_stats(df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    """计算分年度统计"""
    df = df.copy()
    df['year'] = pd.to_datetime(df['date']).dt.year
    
    yearly_stats = {}
    
    for year in sorted(df['year'].unique()):
        year_data = df[df['year'] == year].copy()
        if len(year_data) < 2:
            continue
            
        year_data['ret'] = year_data['equity'].pct_change().fillna(0)
        
        # 年度收益
        start_equity = year_data['equity'].iloc[0]
        end_equity = year_data['equity'].iloc[-1]
        year_return = end_equity / start_equity - 1
        
        # 年度波动
        year_vol = year_data['ret'].std() * (252 ** 0.5)
        
        # 年度最大回撤
        cum_max = year_data['equity'].cummax()
        dd = year_data['equity'] / cum_max - 1
        year_max_dd = dd.min()
        
        # 年度胜率
        year_winning_ratio = (year_data['ret'] > 0).sum() / max(1, len(year_data) - 1)
        
        yearly_stats[str(year)] = {
            'return': year_return,
            'volatility': year_vol,
            'max_drawdown': year_max_dd,
            'sharpe': year_return / year_vol if year_vol > 0 else 0,
            'winning_ratio': year_winning_ratio,
            'trading_days': len(year_data) - 1,
        }
    
    return yearly_stats


def _calculate_risk_stats(df: pd.DataFrame) -> Dict[str, Any]:
    """计算风险相关指标"""
    returns = df['ret'].dropna()
    
    if len(returns) < 2:
        return {}
    
    # VaR 和 CVaR (95% 置信度)
    var_95 = returns.quantile(0.05)
    cvar_95 = returns[returns <= var_95].mean()
    
    # 偏度和峰度
    skewness = returns.skew()
    kurtosis = returns.kurtosis()
    
    # 下行风险 (相对于0的下行波动)
    downside_returns = returns[returns < 0]
    downside_vol = downside_returns.std() * (252 ** 0.5) if len(downside_returns) > 1 else 0
    
    # Sortino 比率
    annual_return = (df['equity'].iloc[-1] / df['equity'].iloc[0]) ** (252 / max(1, len(df) - 1)) - 1
    sortino = annual_return / downside_vol if downside_vol > 0 else 0
    
    return {
        'var_95': var_95,
        'cvar_95': cvar_95,
        'skewness': skewness,
        'kurtosis': kurtosis,
        'downside_volatility': downside_vol,
        'sortino_ratio': sortino,
    }
