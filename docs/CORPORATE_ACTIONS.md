# 企业行动与复权处理方案

> 目标：建立统一的企业行动数据模型与复权计算框架，确保历史价格可比性、回测结果真实性，为后续风险模型与归因分析提供基础。

## 1. 企业行动类型定义

### 1.1 核心企业行动分类

| 行动类型 | 代码 | 对价格影响 | 对股本影响 | 复权处理 | 优先级 |
|---------|-----|----------|----------|---------|--------|
| 现金分红 | `DIV` | 除权日价格调整 | 无 | 后复权加回 | 高 |
| 送股/股票股利 | `STOCK_DIV` | 按比例调整 | 股本增加 | 后复权系数调整 | 高 |
| 配股 | `RIGHTS` | 按比例+配股价调整 | 股本增加 | 后复权系数调整 | 高 |
| 拆股/并股 | `SPLIT` | 按比例调整 | 股本变动 | 后复权系数调整 | 高 |
| 特别分红 | `SPECIAL_DIV` | 大额除权调整 | 无 | 后复权加回 | 中 |
| ST标记变化 | `ST_CHANGE` | 无直接影响 | 无 | 仅标记更新 | 低 |
| 停牌/复牌 | `SUSPEND/RESUME` | 交易限制 | 无 | 前收价维持 | 中 |

### 1.2 复权计算公式

**后复权价格计算（推荐）：**

```
P_adj[t] = P_raw[t] * Π(adj_factor[t+1:end])

其中 adj_factor[t] = (P_close[t-1] + cash_div) / (P_close[t-1] * (1 + stock_ratio) + rights_price * rights_ratio)
```

**前复权价格（备选）：**

```
P_adj[t] = P_raw[t] / Π(adj_factor[start:t])
```

## 2. 数据模型设计

### 2.1 企业行动事件表（`data/raw/corporate_actions.parquet`）

| 列名 | 类型 | 说明 | 示例 |
|-----|-----|-----|-----|
| `symbol` | string | 股票代码 | `000001.SZ` |
| `action_date` | date | 除权除息日 | `2024-06-15` |
| `record_date` | date | 股权登记日 | `2024-06-14` |
| `announce_date` | date | 公告日期 | `2024-04-20` |
| `action_type` | string | 行动类型代码 | `DIV`, `STOCK_DIV`, `RIGHTS` |
| `cash_dividend` | float | 每股现金分红（元） | `0.50` |
| `stock_dividend_ratio` | float | 送股比例（每10股送X股） | `3.0` |
| `rights_ratio` | float | 配股比例（每10股配X股） | `2.0` |
| `rights_price` | float | 配股价格（元） | `8.50` |
| `split_ratio` | float | 拆股比例（1拆X） | `2.0` |
| `adj_factor` | float | 复权因子 | `0.95238` |
| `source` | string | 数据来源 | `akshare`, `manual` |
| `status` | string | 状态 | `confirmed`, `pending` |

### 2.2 停牌状态表（`data/raw/trading_status.parquet`）

| 列名 | 类型 | 说明 |
|-----|-----|-----|
| `symbol` | string | 股票代码 |
| `date` | date | 日期 |
| `is_trading` | int8 | 是否可交易（1=正常，0=停牌） |
| `suspend_reason` | string | 停牌原因 |
| `suspend_start` | date | 停牌开始日 |
| `expected_resume` | date | 预期复牌日 |

## 3. 复权处理实现策略

### 3.1 后复权价格计算（优先采用）

**优势：**

- 最新价格不调整，便于实时交易
- 历史价格向下调整，保持价格连续性
- 适合因子计算与回测

**实现步骤：**

1. 获取企业行动事件序列（按时间排序）
2. 计算累积复权因子：`cum_adj_factor[t] = Π(adj_factor[t:end])`
3. 应用到历史价格：`P_hfq[t] = P_raw[t] * cum_adj_factor[t]`

### 3.2 复权因子缓存策略

```python
# 复权因子计算与缓存示例
def calculate_adj_factors(symbol: str, actions: pd.DataFrame) -> pd.Series:
    """
    计算单股票复权因子序列
    返回：date -> adj_factor 映射
    """
    factors = {}
    cum_factor = 1.0
    
    for _, action in actions.sort_values('action_date', ascending=False).iterrows():
        if action.action_type == 'DIV':
            # 现金分红：factor = (price + div) / price
            factor = (action.close_before + action.cash_dividend) / action.close_before
        elif action.action_type == 'STOCK_DIV':
            # 送股：factor = 1 / (1 + ratio/10)
            factor = 1.0 / (1.0 + action.stock_dividend_ratio / 10.0)
        # ... 其他类型
        
        cum_factor *= factor
        factors[action.action_date] = cum_factor
    
    return pd.Series(factors)
```

## 4. 停牌与涨跌停处理

### 4.1 停牌检测规则

```python
def detect_trading_status(bars: pd.DataFrame) -> pd.DataFrame:
    """
    基于行情数据检测交易状态
    """
    bars['is_trading'] = 1
    
    # 停牌条件：成交量为0或缺失价格数据
    suspend_mask = (
        (bars['volume'] == 0) | 
        (bars['volume'].isna()) |
        (bars['open'].isna()) |
        (bars['close'].isna())
    )
    bars.loc[suspend_mask, 'is_trading'] = 0
    
    # 一字涨跌停检测（影响可交易性）
    oneword_limit = (
        (bars['open'] == bars['high']) & 
        (bars['high'] == bars['low']) & 
        (bars['low'] == bars['close'])
    )
    
    # 涨跌停幅度计算
    pct_change = (bars['close'] / bars['preclose'] - 1).fillna(0)
    
    bars['limit_up_oneword'] = oneword_limit & (pct_change >= 0.098)
    bars['limit_down_oneword'] = oneword_limit & (pct_change <= -0.098)
    
    return bars
```

### 4.2 停牌期间价格处理

- **原则：** 停牌期间维持前收盘价，不进行人工插值
- **成交量：** 停牌日成交量记为 0
- **复权：** 停牌期间企业行动正常计算复权因子
- **回测影响：** 停牌股票无法买入/卖出，影响组合权重分配

## 5. 在回测引擎中的集成

### 5.1 价格数据预处理

```python
class AdjustedPriceProvider:
    def __init__(self, raw_provider: DataProvider):
        self.raw_provider = raw_provider
        self.adj_cache = {}  # symbol -> adj_factors
    
    def get_adjusted_bars(self, req: BarRequest) -> pd.DataFrame:
        """
        返回复权后的价格数据
        """
        raw_bars = self.raw_provider.get_daily_bars(req)
        actions = self.get_corporate_actions(req.symbols, req.start, req.end)
        
        adjusted_bars = []
        for symbol in req.symbols:
            symbol_bars = raw_bars[raw_bars['symbol'] == symbol].copy()
            symbol_actions = actions[actions['symbol'] == symbol]
            
            # 应用复权
            adj_factors = self.calculate_adj_factors(symbol, symbol_actions)
            symbol_bars = self.apply_adjustment(symbol_bars, adj_factors)
            
            # 应用交易状态
            symbol_bars = detect_trading_status(symbol_bars)
            
            adjusted_bars.append(symbol_bars)
        
        return pd.concat(adjusted_bars, ignore_index=True)
```

### 5.2 回测执行增强

在 `backtest.py` 中集成：

```python
def _allow_trade(self, symbol: str, diff: int, bar: Any) -> bool:
    """
    扩展可交易性检查：停牌 + 涨跌停 + 企业行动日
    """
    # 现有逻辑：停牌/一字板检查
    if not self._check_suspend_and_limits(symbol, diff, bar):
        return False
    
    # 新增：企业行动日交易限制
    if self._is_action_date(symbol, self.current_date):
        # 除权日当天可能影响交易，根据具体规则处理
        self.action_blocked_day += 1
        return False
    
    return True
```

## 6. 数据获取与更新

### 6.1 AkShare 企业行动接口

```python
def fetch_corporate_actions(symbol: str, start_date: date, end_date: date) -> pd.DataFrame:
    """
    从 AkShare 获取企业行动数据
    """
    try:
        # 分红送股数据
        dividend_data = ak.stock_history_dividend(symbol=symbol[:6])
        
        # 配股数据  
        rights_data = ak.stock_history_rights(symbol=symbol[:6])
        
        # 拆股数据
        split_data = ak.stock_history_split(symbol=symbol[:6])
        
        # 统一格式并合并
        actions = combine_action_data(dividend_data, rights_data, split_data)
        
        return actions[(actions['action_date'] >= start_date) & 
                      (actions['action_date'] <= end_date)]
    
    except Exception as e:
        print(f"获取企业行动数据失败 {symbol}: {e}")
        return pd.DataFrame()
```

### 6.2 缓存与增量更新

- **全量缓存：** 每只股票的历史企业行动存储为单独文件
- **增量更新：** 每日检查最近 30 天的新公告
- **数据验证：** 对比复权因子与市场数据验证计算正确性

## 7. 质量控制与验证

### 7.1 复权结果验证

```python
def validate_adjustment(symbol: str, adjusted_bars: pd.DataFrame) -> Dict[str, bool]:
    """
    验证复权结果的合理性
    """
    checks = {}
    
    # 检查价格连续性：复权前后涨跌幅应基本一致
    raw_returns = adjusted_bars['close'].pct_change()
    checks['return_continuity'] = (raw_returns.abs() < 0.15).all()  # 单日涨跌幅<15%
    
    # 检查复权因子范围：应在合理区间内
    checks['factor_range'] = adjusted_bars['adj_factor'].between(0.1, 10.0).all()
    
    # 检查缺失值
    checks['no_missing_prices'] = not adjusted_bars[['open','high','low','close']].isna().any().any()
    
    return checks
```

### 7.2 回测一致性检查

- **基准对比：** 与第三方数据源（如 Wind、Choice）的复权价格对比
- **收益率检验：** 确保复权前后收益率计算一致
- **企业行动完整性：** 检查重要除权日是否遗漏

## 8. 实现优先级

| 阶段 | 功能 | 时间估计 | 依赖 |
|-----|-----|---------|------|
| 1 | 基础停牌检测与标记 | 1-2天 | 当前 akshare_provider |
| 2 | 企业行动数据获取与存储 | 2-3天 | AkShare 接口调研 |
| 3 | 后复权价格计算实现 | 2-3天 | 企业行动数据 |
| 4 | 回测引擎集成与测试 | 1-2天 | 复权价格 + 现有回测 |
| 5 | 质量验证与基准对比 | 1-2天 | 外部数据源 |

## 9. 未来扩展占位

- **实时企业行动：** 监控交易所公告，自动更新企业行动日历
- **复杂企业行动：** 分拆、合并、吸收合并等特殊情况处理
- **税收影响：** 考虑股息税对实际收益的影响
- **境外标的：** 支持港股、美股企业行动（如有需求）

---

## 10. 集成检查清单

在完成实现后，确保以下集成点正常工作：

- [ ] `akshare_provider.get_daily_bars()` 返回复权价格
- [ ] `basic_info.parquet` 包含 `is_trading` 列
- [ ] `backtest.py._allow_trade()` 检查停牌状态
- [ ] `daily_records` 新增 `action_blocked` 计数
- [ ] `metrics.py` 能处理停牌期间的收益率计算
- [ ] 复权价格与原始价格对比验证通过

---
（本方案为企业行动处理草案，优先实现停牌检测，复权计算可分阶段完成。）
