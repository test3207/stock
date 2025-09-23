from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Any, Optional
import pandas as pd

from stock.interfaces.data_provider import DataProvider, Strategy
from stock.engine.risk_control import RiskControl, RiskControlConfig

@dataclass
class BacktestConfig:
    """回测配置参数"""
    initial_capital: float = 500000.0
    commission_rate: float = 0.0003
    stamp_duty: float = 0.0005
    transfer_fee: float = 0.00002
    slippage_bps: float = 2.0
    enable_t_plus_one: bool = True
    enable_limit_trading_check: bool = True
    max_position_weight: Optional[float] = None  # 单只股票最大权重限制
    min_trade_amount: float = 100.0  # 最小交易金额（元）
    
    # 风控配置
    enable_risk_control: bool = False  # 是否启用风控
    risk_control_config: Optional[RiskControlConfig] = None  # 风控配置

    def __post_init__(self):
        """初始化后处理"""
        if self.enable_risk_control and self.risk_control_config is None:
            # 使用默认风控配置
            self.risk_control_config = RiskControlConfig()

@dataclass
class ExecutionParams:
    commission_rate: float = 0.0003  # 双边佣金（买卖都收）
    stamp_duty: float = 0.0005       # 卖出单边
    transfer_fee: float = 0.00002    # 沪市过户费（双边）
    slippage_bps: float = 2          # 双边滑点（bps）
    t_plus_one: bool = True

    @classmethod
    def from_config(cls, config: BacktestConfig) -> 'ExecutionParams':
        """从BacktestConfig创建ExecutionParams"""
        return cls(
            commission_rate=config.commission_rate,
            stamp_duty=config.stamp_duty,
            transfer_fee=config.transfer_fee,
            slippage_bps=config.slippage_bps,
            t_plus_one=config.enable_t_plus_one
        )

@dataclass
class PortfolioState:
    cash: float
    positions: Dict[str, int] = field(default_factory=dict)

    def market_value(self, price_map: Dict[str, float]) -> float:
        mv = 0.0
        for sym, qty in self.positions.items():
            mv += qty * price_map.get(sym, 0.0)
        return mv

    def total_equity(self, price_map: Dict[str, float]) -> float:
        return self.cash + self.market_value(price_map)

class Backtester:
    def __init__(self, provider: DataProvider, strategy: Strategy, initial_capital: float, exec_params: ExecutionParams):
        self.provider = provider
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.exec_params = exec_params
        self.state = PortfolioState(cash=initial_capital)
        self.daily_records: List[Dict[str, Any]] = []
        self.trades: List[Dict[str, Any]] = []
        self.buy_day: Dict[str, date] = {}  # 记录最近买入日期用于 T+1 限制
        self.tplus1_blocked: int = 0
        self._pending_rebalance: Dict[str, float] | None = None
        self._pending_date: date | None = None
        # 每日（非累计）阻断计数器：停牌 / 涨停买入阻断 / 跌停卖出阻断
        self.limit_blocked_buy_day: int = 0
        self.limit_blocked_sell_day: int = 0
        self.suspend_blocked_day: int = 0
        
        # 风控模块
        self.risk_control: Optional[RiskControl] = None
        self.entry_prices: Dict[str, float] = {}  # 记录建仓成本价
    
    @classmethod
    def from_config(cls, provider: DataProvider, strategy: Strategy, config: BacktestConfig) -> 'Backtester':
        """从配置创建Backtester实例"""
        exec_params = ExecutionParams.from_config(config)
        backtester = cls(provider, strategy, config.initial_capital, exec_params)
        
        # 初始化风控模块
        if config.enable_risk_control and config.risk_control_config is not None:
            backtester.risk_control = RiskControl(config.risk_control_config)
            
        return backtester

    def run(self, trading_days: List[date], universe: List[str], rebalance_dates: List[date]):
        # Preload bars for efficiency
        print(f"[BT] 预加载 {len(universe)} 支股票价格数据，时间范围：{trading_days[0]} ~ {trading_days[-1]}")
        bars_df = self.provider.get_daily_bars(
            req = type('tmp', (), {'symbols': universe, 'start': trading_days[0], 'end': trading_days[-1], 'fields': None})()
        )
        bars_df = bars_df.sort_values(['symbol','date'])
        
        # 构建快速查找字典：(symbol, date) -> bar_record
        price_matrix = {}
        for row in bars_df.itertuples():
            key = (row.symbol, row.date)
            price_matrix[key] = row
        
        print(f"[BT] 价格矩阵构建完成：{len(price_matrix)} 条记录")
        
        # 添加回测执行统计
        self.execution_stats = {
            'total_rebalance_signals': 0,
            'executed_rebalances': 0,
            'empty_signals': 0,
            'avg_universe_coverage': 0.0
        }
        
        last_equity = None
        daily_traded_value_buy: float = 0.0
        daily_traded_value_sell: float = 0.0
        for i, d in enumerate(trading_days):
            # 使用预构建的价格矩阵获取当日数据
            day_bars = []
            for symbol in universe:
                bar = price_matrix.get((symbol, d))
                if bar is not None:
                    day_bars.append(bar)
            
            # 构建价格映射和行情映射
            price_map_close = {bar.symbol: bar.close for bar in day_bars}
            open_price_map = {bar.symbol: bar.open for bar in day_bars}
            bar_map = {bar.symbol: bar for bar in day_bars}
            day_turnover_total = 0.0
            day_turnover_buy = 0.0
            day_turnover_sell = 0.0
            # 重置当日阻断计数（与 tplus1_blocked 累计不同，这里按日）
            self.limit_blocked_buy_day = 0
            self.limit_blocked_sell_day = 0
            self.suspend_blocked_day = 0
            if last_equity is None:
                last_equity = self.state.total_equity(price_map_close)
            if self._pending_rebalance is not None and self._pending_date == d:
                print(f"[BT] {d} 执行前一日信号 调仓标的={len(self._pending_rebalance)}")
                total_v, buy_v, sell_v = self._rebalance_at(open_price_map, self._pending_rebalance, trade_date=d, bar_map=bar_map)
                daily_traded_value_buy += buy_v
                daily_traded_value_sell += sell_v
                self._pending_rebalance = None
                self._pending_date = None
            
            # 风控检查：每日收盘后对现有持仓进行风控评估
            if self.risk_control and price_map_close:
                risk_actions = self.risk_control.check_risk_controls(
                    positions=self.state.positions,
                    current_prices=price_map_close,
                    portfolio_equity=self.state.total_equity(price_map_close),
                    current_date=d
                )
                
                # 如果有风控触发，在下一交易日执行
                if risk_actions and i < len(trading_days)-1:
                    next_day = trading_days[i+1]
                    if not self._pending_rebalance:  # 没有其他调仓计划
                        print(f"[RISK] {d} 风控触发 {len(risk_actions)} 项，计划在 {next_day} 开盘执行")
                        self._pending_rebalance = self._convert_risk_actions_to_weights(risk_actions, price_map_close)
                        self._pending_date = next_day
                    else:
                        # 如果已有调仓计划，将风控动作合并进去
                        risk_weights = self._convert_risk_actions_to_weights(risk_actions, price_map_close)
                        for sym, weight in risk_weights.items():
                            if weight == 0:  # 风控要求清仓，覆盖原计划
                                self._pending_rebalance[sym] = 0
            if d in rebalance_dates and i < len(trading_days)-1:
                self.execution_stats['total_rebalance_signals'] += 1
                target_weights = self.strategy.generate_target_weights(d, universe, data_ctx={'price': price_map_close})
                if target_weights:
                    exec_day = trading_days[i+1]
                    print(f"[BT] {d} 生成权重 {len(target_weights)} 条, 计划在 {exec_day} 开盘执行")
                    self._pending_rebalance = target_weights
                    self._pending_date = exec_day
                    self.execution_stats['executed_rebalances'] += 1
                    
                    # 计算宇宙覆盖率
                    available_symbols = len([s for s in target_weights.keys() if s in price_map_close])
                    coverage = available_symbols / len(universe) if universe else 0
                    self.execution_stats['avg_universe_coverage'] += coverage
                else:
                    print(f"[BT] {d} 无调仓信号")
                    self.execution_stats['empty_signals'] += 1
            equity_after = self.state.total_equity(price_map_close)
            total_traded_value = daily_traded_value_buy + daily_traded_value_sell
            if total_traded_value > 0 and last_equity and last_equity > 0:
                day_turnover_total = total_traded_value / last_equity
                day_turnover_buy = daily_traded_value_buy / last_equity
                day_turnover_sell = daily_traded_value_sell / last_equity
            last_equity = equity_after
            daily_traded_value_buy = 0.0
            daily_traded_value_sell = 0.0
            import json as _json
            
            # 计算持仓统计
            pos_count = len([qty for qty in self.state.positions.values() if qty > 0])
            market_value = self.state.market_value(price_map_close)
            
            # 获取风控统计
            risk_stats = self.risk_control.get_daily_stats() if self.risk_control else {}
            
            self.daily_records.append({
                'date': d,
                'equity': equity_after,
                'cash': self.state.cash,
                'market_value': market_value,
                'positions_json': _json.dumps(self.state.positions, ensure_ascii=False),
                'pos_count': pos_count,
                'turnover': day_turnover_total,
                'turnover_buy': day_turnover_buy,
                'turnover_sell': day_turnover_sell,
                'tplus1_blocked': self.tplus1_blocked,
                'limit_blocked_buy': self.limit_blocked_buy_day,
                'limit_blocked_sell': self.limit_blocked_sell_day,
                'suspend_blocked': self.suspend_blocked_day,
                'risk_stop_loss_triggered': risk_stats.get('stop_loss_triggered', 0),
                'risk_take_profit_triggered': risk_stats.get('take_profit_triggered', 0),
                'risk_time_stop_triggered': risk_stats.get('time_stop_triggered', 0)
            })
        
        # 完成执行统计
        if self.execution_stats['executed_rebalances'] > 0:
            self.execution_stats['avg_universe_coverage'] /= self.execution_stats['executed_rebalances']
        
        print(f"[BT] 回测执行完成:")
        print(f"  - 调仓信号总数: {self.execution_stats['total_rebalance_signals']}")
        print(f"  - 成功执行调仓: {self.execution_stats['executed_rebalances']}")
        print(f"  - 空信号次数: {self.execution_stats['empty_signals']}")
        print(f"  - 平均宇宙覆盖率: {self.execution_stats['avg_universe_coverage']:.2%}")
        print(f"  - T+1阻断累计: {self.tplus1_blocked}")
        
        return pd.DataFrame(self.daily_records)
    
    def get_execution_report(self) -> Dict[str, Any]:
        """
        获取回测执行详细报告
        """
        report = {
            'execution_stats': self.execution_stats.copy() if hasattr(self, 'execution_stats') else {},
            'trading_blocks': {
                'tplus1_blocked_total': self.tplus1_blocked,
                'limit_blocked_buy_total': sum(1 for r in self.daily_records if r.get('limit_blocked_buy', 0) > 0),
                'limit_blocked_sell_total': sum(1 for r in self.daily_records if r.get('limit_blocked_sell', 0) > 0),
                'suspend_blocked_total': sum(1 for r in self.daily_records if r.get('suspend_blocked', 0) > 0),
            },
            'risk_control_stats': {
                'stop_loss_triggered_total': sum(r.get('risk_stop_loss_triggered', 0) for r in self.daily_records),
                'take_profit_triggered_total': sum(r.get('risk_take_profit_triggered', 0) for r in self.daily_records),
                'time_stop_triggered_total': sum(r.get('risk_time_stop_triggered', 0) for r in self.daily_records),
                'risk_control_summary': self.risk_control.get_summary() if self.risk_control else {},
            },
            'portfolio_stats': {
                'final_equity': self.state.total_equity({}),
                'final_cash': self.state.cash,
                'final_positions_count': len([qty for qty in self.state.positions.values() if qty > 0]),
                'total_trades': len(self.trades)
            }
        }
        return report

    def _convert_risk_actions_to_weights(self, risk_actions: List, current_prices: Dict[str, float]) -> Dict[str, float]:
        """
        将风控动作转换为权重字典，用于执行风控触发的调仓
        """
        from ..engine.risk_control import RiskControlAction
        
        weights = {}
        for action in risk_actions:
            if action.action_type == RiskControlAction.STOP_LOSS:
                # 止损：将权重设为0（清仓）
                weights[action.symbol] = 0.0
            elif action.action_type == RiskControlAction.TAKE_PROFIT:
                # 止盈：将权重设为0（清仓）
                weights[action.symbol] = 0.0
            elif action.action_type == RiskControlAction.REDUCE_POSITION:
                # 减仓：权重设为当前权重的一半（简化处理）
                current_equity = self.state.total_equity(current_prices)
                if current_equity > 0:
                    current_qty = self.state.positions.get(action.symbol, 0)
                    current_price = current_prices.get(action.symbol, 0)
                    if current_price > 0:
                        current_weight = (current_qty * current_price) / current_equity
                        weights[action.symbol] = current_weight * 0.5  # 减仓50%
        
        return weights

    def _rebalance_at(self, open_price_map: Dict[str, float], target_weights: Dict[str, float], trade_date: date, bar_map: Dict[str, Any]) -> tuple[float,float,float]:
        current_equity = self.state.total_equity(open_price_map)
        desired_shares: Dict[str, int] = {}
        for sym, w in target_weights.items():
            price = open_price_map.get(sym)
            if price and price > 0 and w > 0:
                desired_value = current_equity * w
                desired_shares[sym] = int(desired_value / price)
        all_syms = set(desired_shares) | set(self.state.positions)
        traded_value_total = 0.0
        buy_value = 0.0
        sell_value = 0.0
        for sym in all_syms:
            current_qty = self.state.positions.get(sym, 0)
            target_qty = desired_shares.get(sym, 0)
            diff = target_qty - current_qty
            if diff == 0:
                continue
            price = open_price_map.get(sym)
            if not price or price <= 0:
                continue
            # 可交易性检查（停牌 / 一字涨跌停）
            bar = bar_map.get(sym)
            if not self._allow_trade(sym, diff, bar):
                continue
            # T+1 卖出限制：如果是卖出且买入日与 trade_date 同日则跳过
            if diff < 0 and self.exec_params.t_plus_one:
                last_buy = self.buy_day.get(sym)
                if last_buy is not None and last_buy == trade_date:
                    self.tplus1_blocked += 1
                    continue
            trade_value = self._execute(sym, diff, price, trade_date)
            traded_value_total += abs(trade_value)
            if diff > 0:
                buy_value += abs(trade_value)
            else:
                sell_value += abs(trade_value)
            if target_qty == 0 and sym in self.state.positions:
                self.state.positions.pop(sym, None)
            else:
                self.state.positions[sym] = target_qty
        return traded_value_total, buy_value, sell_value

    def _allow_trade(self, symbol: str, diff: int, bar: Any) -> bool:
        """检查单只股票在当日开盘是否允许执行该方向订单。
        规则：
        1. 停牌：is_trading=0 → 买卖都阻断（suspend_blocked）。
        2. 一字涨停：limit_up_oneword=1 → 阻断买单（limit_blocked_buy）。
        3. 一字跌停：limit_down_oneword=1 → 阻断卖单（limit_blocked_sell）。
        返回 True 表示允许继续，False 表示阻断。
        """
        if bar is None:
            self.suspend_blocked_day += 1
            return False
        try:
            # 使用预计算的交易状态标记
            is_trading = getattr(bar, 'is_trading', None)
            if is_trading is None or is_trading == 0:
                self.suspend_blocked_day += 1
                return False
            
            # 检查一字涨跌停限制
            limit_up = getattr(bar, 'limit_up_oneword', 0)
            limit_down = getattr(bar, 'limit_down_oneword', 0)
            
            # 一字涨停阻断买单
            if limit_up == 1 and diff > 0:
                self.limit_blocked_buy_day += 1
                return False
            
            # 一字跌停阻断卖单
            if limit_down == 1 and diff < 0:
                self.limit_blocked_sell_day += 1
                return False
                
        except Exception:
            # 任何异常保守阻断
            self.suspend_blocked_day += 1
            return False
        return True

    def _execute(self, symbol: str, qty_diff: int, price: float, trade_date: date) -> float:
        slip_price = price * (1 + self.exec_params.slippage_bps/10000 * (1 if qty_diff>0 else -1))
        trade_value = slip_price * abs(qty_diff)
        commission = trade_value * self.exec_params.commission_rate
        transfer = trade_value * self.exec_params.transfer_fee
        stamp = trade_value * self.exec_params.stamp_duty if qty_diff < 0 else 0.0
        cost = commission + transfer + stamp
        
        if qty_diff > 0:
            total_cost = trade_value + cost
            if self.state.cash >= total_cost:
                self.state.cash -= total_cost
                self.buy_day[symbol] = trade_date
                
                # 更新成本价（用于风控）
                if self.risk_control:
                    current_qty = self.state.positions.get(symbol, 0)
                    if current_qty == 0:  # 新建仓位
                        self.entry_prices[symbol] = slip_price
                    else:  # 加仓，更新平均成本
                        current_cost = self.entry_prices.get(symbol, slip_price)
                        total_value = current_cost * current_qty + slip_price * abs(qty_diff)
                        self.entry_prices[symbol] = total_value / (current_qty + abs(qty_diff))
            else:
                return 0.0
        else:
            self.state.cash += trade_value - cost
            # 减仓/清仓时，如果完全清仓则删除成本价记录
            if self.risk_control:
                remaining_qty = self.state.positions.get(symbol, 0) + qty_diff  # qty_diff是负数
                if remaining_qty <= 0:
                    self.entry_prices.pop(symbol, None)
        
        self.trades.append({
            'date': trade_date,
            'symbol': symbol,
            'side': 'BUY' if qty_diff>0 else 'SELL',
            'qty': abs(qty_diff),
            'price': slip_price,
            'trade_value': trade_value,
            'commission': commission,
            'transfer': transfer,
            'stamp': stamp,
            'cost_total': cost
        })
        return trade_value

    def get_trades(self) -> pd.DataFrame:
        if not self.trades:
            return pd.DataFrame(columns=['date','symbol','side','qty','price','trade_value','commission','transfer','stamp','cost_total'])
        return pd.DataFrame(self.trades)
