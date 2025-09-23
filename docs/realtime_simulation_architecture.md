# 实时数据模拟系统架构设计

## 1. 系统设计目标

- **可中断恢复**：cronjob可在任意时点中断，重启后自动恢复
- **多实例支持**：支持同时运行多套不同参数的模拟
- **完整状态保存**：每日交易过程、结果、状态完整记录
- **跨机器迁移**：通过文件系统实现完整状态迁移
- **数据缓存优化**：智能缓存机制减少API调用

## 2. 目录结构设计

```text
data/simulation/
├── instances/                          # 多实例管理
│   ├── default/                        # 默认实例
│   │   ├── config.json                 # 实例配置
│   │   ├── state/                      # 状态文件
│   │   │   ├── 2025-09-23.json        # 每日状态
│   │   │   ├── 2025-09-24.json
│   │   │   └── ...
│   │   ├── trades/                     # 交易记录
│   │   │   ├── 2025-09-23_rebalance.json    # 调仓交易
│   │   │   ├── 2025-09-23_risk_control.json # 风控交易
│   │   │   └── ...
│   │   ├── logs/                       # 日志文件
│   │   │   ├── 2025-09-23.log
│   │   │   └── ...
│   │   └── performance/                # 绩效分析
│   │       ├── daily_summary.json     # 每日汇总
│   │       └── monthly_report.json    # 月度报告
│   ├── conservative/                   # 保守策略实例
│   ├── aggressive/                     # 激进策略实例
│   └── ...
├── cache/                              # 数据缓存
│   ├── market_data/                    # 市场数据缓存
│   │   ├── daily/                      # 日频数据
│   │   │   ├── 2025-09-23/
│   │   │   │   ├── stock_prices.json  # 股价数据
│   │   │   │   ├── st_status.json     # ST状态
│   │   │   │   └── trading_status.json # 交易状态
│   │   │   └── ...
│   │   └── realtime/                   # 实时数据缓存
│   │       ├── current_prices.json    # 当前价格
│   │       └── last_update.json       # 更新时间戳
│   ├── reference_data/                 # 参考数据
│   │   ├── stock_list.json            # 股票列表
│   │   ├── trading_calendar.json      # 交易日历
│   │   └── index_components.json      # 指数成分股
│   └── metadata/                       # 元数据
│       ├── cache_status.json          # 缓存状态
│       └── data_quality.json          # 数据质量报告
├── templates/                          # 配置模板
│   ├── instance_config_template.json  # 实例配置模板
│   └── strategy_templates/             # 策略模板
└── global_config.json                 # 全局配置
```

## 3. 核心组件设计

### 3.1 实例管理器 (InstanceManager)

- 管理多个模拟实例
- 实例创建、删除、暂停、恢复
- 实例间资源隔离

### 3.2 状态管理器 (StateManager)

- 每日状态保存/加载
- 断点恢复机制
- 状态一致性检查

### 3.3 缓存管理器 (CacheManager)

- 多层级缓存策略
- 数据有效性检查
- 智能更新机制

### 3.4 调度器 (Scheduler)

- cronjob任务调度
- 执行时间管理
- 错误重试机制

### 3.5 监控器 (Monitor)

- 系统健康检查
- 性能监控
- 异常告警

## 4. 数据流设计

```text
[市场数据源] → [缓存管理器] → [策略引擎] → [交易执行器] → [状态管理器]
      ↓              ↓              ↓              ↓              ↓
   [原始数据]    [清洗数据]    [交易信号]    [交易记录]    [组合状态]
```

## 5. 配置文件格式

### 5.1 实例配置 (instance/config.json)

```json
{
  "instance_id": "default",
  "instance_name": "默认策略实例",
  "created_date": "2025-09-23",
  "strategy": {
    "type": "drawdown_reversal",
    "parameters": {
      "stock_count": 35,
      "lookback_months": 6,
      "drawdown_threshold": -0.20,
      "rebalance_frequency": "monthly"
    }
  },
  "capital": {
    "initial_amount": 1000000.0,
    "currency": "CNY"
  },
  "risk_control": {
    "stop_loss": -0.15,
    "take_profit": 0.20,
    "max_position_weight": 0.05,
    "check_frequency": "5min"
  },
  "trading_costs": {
    "commission_rate": 0.0001,
    "stamp_tax_rate": 0.001,
    "slippage_bps": 8
  },
  "schedule": {
    "rebalance_time": "15:30",
    "risk_check_interval": "*/5 * * * *",
    "market_data_update": "*/1 * * * *"
  },
  "status": "active"
}
```

### 5.2 日度状态 (state/YYYY-MM-DD.json)

```json
{
  "date": "2025-09-23",
  "instance_id": "default",
  "portfolio": {
    "cash": 850000.0,
    "idle_cash": 150000.0,
    "positions": {
      "000001.SZ": {
        "shares": 1000,
        "cost_price": 12.50,
        "current_price": 13.25,
        "market_value": 13250.0,
        "weight": 0.028,
        "entry_date": "2025-08-31",
        "unrealized_pnl": 750.0,
        "unrealized_pnl_pct": 0.06
      }
    },
    "market_value": 475000.0,
    "total_value": 1325000.0,
    "total_return": 0.325,
    "daily_return": 0.002
  },
  "risk_control": {
    "triggered_stocks": ["000002.SZ"],
    "stop_loss_count": 2,
    "take_profit_count": 1,
    "last_check": "2025-09-23T14:55:00",
    "next_rebalance": "2025-10-31"
  },
  "system_metrics": {
    "data_freshness": "2025-09-23T14:57:00",
    "cache_hit_rate": 0.95,
    "execution_time_ms": 1250,
    "api_calls_today": 45
  },
  "checksum": "sha256:abc123...",
  "timestamp": "2025-09-23T15:00:00"
}
```

### 5.3 交易记录 (trades/YYYY-MM-DD_type.json)

```json
{
  "date": "2025-09-23",
  "instance_id": "default",
  "trade_type": "rebalance",
  "trades": [
    {
      "trade_id": "T20250923001",
      "stock_code": "000001.SZ",
      "action": "buy",
      "shares": 1000,
      "price": 12.50,
      "amount": 12500.0,
      "costs": {
        "commission": 1.25,
        "stamp_tax": 0.0,
        "transfer_fee": 0.25,
        "slippage": 10.0,
        "total": 11.50
      },
      "net_amount": 12511.50,
      "timestamp": "2025-09-23T09:31:00",
      "execution_type": "rebalance",
      "order_id": "ORD20250923001"
    }
  ],
  "summary": {
    "total_trades": 5,
    "total_buy_amount": 125000.0,
    "total_sell_amount": 98000.0,
    "total_costs": 234.50,
    "net_flow": -27234.50
  }
}
```

## 6. 执行流程设计

### 6.1 日度执行流程

1. **系统启动检查**
   - 验证交易日
   - 检查系统状态
   - 加载实例配置

2. **数据更新**
   - 更新市场数据缓存
   - 验证数据完整性
   - 更新ST状态

3. **策略执行**
   - 加载昨日状态
   - 执行策略逻辑
   - 生成交易信号

4. **交易执行**
   - 模拟订单执行
   - 计算交易成本
   - 更新持仓状态

5. **状态保存**
   - 保存今日状态
   - 记录交易明细
   - 更新绩效指标

### 6.2 风控监控流程 (每5分钟)

1. **持仓检查**
   - 获取实时价格
   - 计算浮动盈亏
   - 检查风控条件

2. **风控执行**
   - 触发止损/止盈
   - 执行风控交易
   - 更新风控状态

3. **状态同步**
   - 实时更新状态
   - 记录风控交易
   - 发送监控信息

## 7. 容错与恢复机制

### 7.1 断点恢复

- 每次执行前检查上次执行状态
- 自动识别中断点
- 从中断点继续执行

### 7.2 数据一致性

- 状态文件checksum验证
- 交易记录完整性检查
- 异常数据自动修复

### 7.3 异常处理

- 网络异常重试机制
- 数据异常降级策略
- 系统异常告警通知

## 8. 多实例管理

### 8.1 实例隔离

- 独立的配置文件
- 独立的状态目录
- 独立的缓存空间

### 8.2 资源共享

- 共享市场数据缓存
- 共享交易日历
- 共享基础配置

### 8.3 并发控制

- 文件锁机制
- 资源访问排队
- 冲突检测与解决

## 9. 监控与维护

### 9.1 健康检查

- 系统状态监控
- 数据质量检查
- 性能指标追踪

### 9.2 自动维护

- 日志文件清理
- 过期缓存清理
- 数据完整性修复

### 9.3 告警机制

- 异常情况告警
- 性能异常提醒
- 系统维护通知
