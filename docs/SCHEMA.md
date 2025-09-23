# 数据分层与字段规范（Schema）

> 目标：建立可迭代、可验证、可服务化扩展的数据层级；保证回测/策略/可视化之间字段语义一致、减少耦合。所有列名统一 `snake_case`，股票代码统一 6 位 + `.SH`/`.SZ`。日期列使用 `date` 类型（Parquet 中为 `DATE` 或 `int32` annotated）。

## 分层总览

| 层级 | 目录示例 | 产出方式 | 主要用途 | 更新频率 | 保留周期 |
|------|----------|----------|----------|----------|----------|
| raw | `data/raw/` | 直接抓取缓存 | 原始接口落地，最小清洗 | 每日/按需 | 可滚动 (近2-3年) |
| clean | `data/clean/` | 清洗/标准化 | 基础行情 & 基础信息统一格式 | 每日 | 3~5 年 |
| features | `data/features/` | 因子计算脚本 | 特征/因子矩阵 (日频) | 调用时 | 2~3 年 |
| portfolio | `data/portfolio/` | 组合构建/持仓导出 | 目标权重、持仓切片 | 调仓日 | 全量 |
| backtest | `data/backtest/` | 回测运行 | 日度记录、交易、指标 | 运行时 | 永久(可压缩) |

## 1. raw 层

### 1.1 行情单股票 Parquet (`data/raw/hist/XXXXXX_SH.parquet`)

列 | 类型 | 说明
---|-----|----
`date` | date | 交易日期
`symbol` | string | 代码 (6位+后缀)
`open` | float | 开盘价 (后复权)
`high` | float | 最高价 (后复权)
`low` | float | 最低价 (后复权)
`close` | float | 收盘价 (后复权)
`preclose` | float | 前一交易日收盘价 (后复权)；首日为空
`volume` | float | 成交量（股）
`amount` | float | 成交额（元）
`adj_factor` | float | 复权因子（当前接口暂设 1.0 占位）

特点：

- 不做缺失前向填充；只保留接口直接可得。
- 同 symbol/date 去重后只保留一行。

### 1.2 指数成分缓存 (`data/raw/index_members_000300.json` 等)

字段 | 说明
------|-----
`ts` | 缓存生成时间戳 (epoch seconds)
`symbols` | 成分股代码数组

### 1.3 基础信息缓存 (`data/raw/basic_info.parquet`)

列 | 类型 | 说明
---|-----|----
`symbol` | string | 代码
`name` | string | 名称
`list_date` | date | 上市日期 (接口或补抓)
`is_st` | bool | 名称含 ST/*ST 标记
`market` | string | 市场标识（A）
`exchange` | string | 交易所 SH/SZ

## 2. clean 层

当前与 raw 行情语义几乎一致，后续纳入：

- 统一停牌标记：新增 `is_trading` (1/0)。
- 价格前向补齐策略（可选）。
- /calc 预聚合（如 rolling 窗口的预先计算）。

建议新增列：

列 | 类型 | 说明
---|-----|----
`is_trading` | int8 | 1=有成交量且非停牌；0=停牌
`limit_up_oneword` | int8 | 一字涨停标记
`limit_down_oneword` | int8 | 一字跌停标记

## 3. features 层

示例：`data/features/drawdown_6m.parquet`

列 | 类型 | 说明
---|-----|----
`date` | date | 交易日
`symbol` | string | 股票
`ret_6m` | float | 6 个月 (126日) 回撤/跌幅（现策略使用 close 对比）

未来扩展占位：

- `mom_1m`, `vol_20d`, `turn_20d`, `size`, `pb`, `pe_ttm`, `industry_code`。

## 4. portfolio 层

示例：`data/portfolio/weights_2024-12-31.parquet`

列 | 类型 | 说明
---|-----|----
`date` | date | 信号生成日
`symbol` | string | 股票
`target_weight` | float | 目标权重 (归一)
`source` | string | 策略标识/版本号
`note` | string | 备注/阈值说明

## 5. backtest 层

### 5.1 日度记录（`data/backtest/daily_equity.parquet`）

列 | 类型 | 说明
---|-----|----
`date` | date | 交易日
`equity` | float | 组合总权益
`cash` | float | 现金余额
`positions_json` | string | 当日收盘持仓字典 JSON (symbol->shares)
`turnover` | float | 当日总换手 = (买+卖成交额)/昨日权益
`turnover_buy` | float | 买入换手
`turnover_sell` | float | 卖出换手
`tplus1_blocked` | int | 当日执行中 T+1 卖出被阻次数（累计或日度，现实现为累计）
`limit_blocked_buy` | int | 一字涨停导致买入阻断（当日）
`limit_blocked_sell` | int | 一字跌停导致卖出阻断（当日）
`suspend_blocked` | int | 停牌/无量阻断（当日）

未来计划新增：

列 | 类型 | 说明
---|-----|----
`pos_count` | int | 当日持仓标的数
`industry_exposure_json` | string | 行业暴露 (行业->权重)
`factor_exposure_json` | string | 风格/因子暴露向量
`max_drawdown_to_date` | float | 截至当日最大回撤
`recovery_days` | int | 回撤恢复用时 (滚动计算)

### 5.2 交易记录（`data/backtest/trades.parquet`）

列 | 类型 | 说明
---|-----|----
`date` | date | 交易日
`symbol` | string | 标的
`side` | string | BUY/SELL
`qty` | int | 成交股数
`price` | float | 成交价格（含滑点后）
`trade_value` | float | 成交额（= price * qty）
`commission` | float | 佣金
`transfer` | float | 过户费
`stamp` | float | 印花税（卖出）
`cost_total` | float | 总费用（不含滑点价差）

### 5.3 指标汇总（示例文件 `data/backtest/metrics.json`）

字段 | 说明
---|----
`total_return` | 总收益率 (最后权益/初始 -1)
`annual_return` | 年化收益
`annual_vol` | 年化波动
`sharpe` | Sharpe (rf=0)
`max_drawdown` | 最大回撤
`calmar` | Calmar 比率
`win_day_ratio` | 日收益为正比例
`avg_daily_turnover` | 平均日换手
`annualized_turnover` | 年化换手
`avg_daily_turnover_buy` | 平均买入换手
`avg_daily_turnover_sell` | 平均卖出换手
`trade_count` | 总交易笔数
`buy_count` | 买单数
`sell_count` | 卖单数
（未来）`info_ratio` | 信息比率 (需基准序列)

## 6. 命名 / 类型规范

项 | 规范
---|----
股票代码 | 6位 + `.SH`/`.SZ`
日期列名 | `date`
时间列（若扩展分钟） | `ts` (UTC 或本地需注明)
布尔 | `bool`，若需与 Arrow 兼容可转 int8 (1/0)
JSON 列 | 尽量保持最小嵌套，使用 UTF-8，无排序要求
浮点精度 | 默认 `float64`，若需压缩可在 clean 后使用类型降级策略

## 7. 质量校验建议

类别 | 规则 | 处理
-----|-----|----
缺失价格 | open/high/low/close 任一缺失 → 行删除或标记停牌 | 标记 `is_trading=0`
负价格/成交量 | 视为错误 | 过滤
重复 (symbol,date) | 保留最新行 | 统一排序再 `drop_duplicates`
权重和 | |abs(Σw-1)| < 1e-6 | 若不满足 → 归一

## 8. 生成与依赖顺序

1. raw: 行情 & 基础信息抓取
2. clean: 衍生停牌与涨跌停标记
3. features: 使用 clean 计算滚动因子
4. portfolio: 策略权重（依赖 features + clean）
5. backtest: 撮合与绩效结果（依赖 raw/clean/portfolio）

## 9. 最小流水线（文本流程图）

```
[index constituents] → raw/basic_info
                   ↘
        raw/hist  → clean (add flags) → features (ret_6m, etc) → strategy weights → backtest(run) → metrics
```

## 10. 后续扩展占位

方向 | 摘要
----|----
企业行动 | 增加 `dividend`, `split`, `rights_issue` 事件表（raw）→ 调整复权与收益归因
行业与风格 | 加入 `industry_code`, `style_size`, `style_value` 列并进入 features / 持仓暴露
多因子 | 统一因子元数据注册表（名称/窗口/方向）
基准 | 引入指数净值序列 → 计算超额 & 信息比率
风险模型 | 生成因子协方差矩阵（滚动）→ 组合波动分解

---
（本文件为 Schema 草案，随着实现可迭代更新；新增列需回溯注明版本变更。）
