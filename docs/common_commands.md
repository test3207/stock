# 股票交易系统常用命令文档

## ⚡ 快速命令（现成脚本）

**最简单的方式 - 使用现成的PowerShell脚本：**

```powershell
# � 快速监控（一键获取系统状态和实时价值）
.\scripts\quick_monitor.ps1

# 📊 系统管理（查看定时任务、手动执行等）
.\scripts\manage_trading.ps1 status     # 查看状态
.\scripts\manage_trading.ps1 monitor    # 立即监控
.\scripts\manage_trading.ps1 rebalance  # 立即调仓

# ⚙️ 一键配置所有定时任务
.\scripts\setup_cronjob.ps1

# 🎯 智能调仓（带时间检查）
.\scripts\smart_rebalance.ps1
```

**详细使用说明请参考：`scripts/README.md`**

---

## 📁 实例说明### 推荐实例配置

- **`test`**：测试专用实例，用于开发调试和快速验证
- **`default`**：主模拟实例，用于正式模拟交易
- **`backtest`**：回测专用实例

### 测试实例优势

- 独立的数据目录，不影响主模拟数据
- 可以快速清理重来
- 便于测试不同配置参数考

## �🚀 系统运行命令（测试实例）

### 启动实时模拟交易（强制调仓） - 测试实例

```bash
C:/dev/stock/.venv/Scripts/python.exe simulation/main.py --mode cronjob --instance test --task daily_rebalance --force-rebalance
```

### 启动实时模拟交易（正常模式） - 测试实例

```bash
C:/dev/stock/.venv/Scripts/python.exe simulation/main.py --mode cronjob --instance test --task daily_rebalance
```

### 启动风控监控 - 测试实例

```bash
C:/dev/stock/.venv/Scripts/python.exe simulation/main.py --mode cronjob --instance test --task risk_monitoring
```

## 📊 数据分析命令（测试实例）

### 查看交易结果分析 - 测试实例

```python
C:/dev/stock/.venv/Scripts/python.exe -c "
import json
from pathlib import Path

# 读取最新状态 - 测试实例
state_file = Path('data/simulation/instances/test/state/2025-09-23.json')
with open(state_file, 'r', encoding='utf-8') as f:
    state = json.load(f)

# 读取交易记录 - 测试实例
trades_file = Path('data/simulation/instances/test/trades/2025-09-23_trades.json')
with open(trades_file, 'r', encoding='utf-8') as f:
    trades_data = json.load(f)

trades = trades_data['trades']
total_value = state['portfolio']['total_value']
cash = state['portfolio']['cash']
market_value = state['portfolio']['market_value']

print('📊 交易结果分析 (测试实例):')
print(f'   交易笔数: {len(trades)}')
print(f'   总资产: {total_value:,.2f} 元')
print(f'   现金: {cash:,.2f} 元')
print(f'   市值: {market_value:,.2f} 元')
print(f'   持仓股票数: {len(state[\"portfolio\"][\"positions\"])}')

# 成本分析
initial_capital = 1000000.00
loss = initial_capital - total_value
all_commission = sum(t['commission'] for t in trades)

print(f'\\n💸 成本分析:')
print(f'   初始资金: {initial_capital:,.2f} 元')
print(f'   实际损失: {loss:.2f} 元')
print(f'   总佣金: {all_commission:.2f} 元')
print(f'   损失率: {loss/initial_capital*100:.4f}%')
"
```

### 验证交易成本构成 - 测试实例

```python
C:/dev/stock/.venv/Scripts/python.exe -c "
import json
from pathlib import Path

trades_file = Path('data/simulation/instances/test/trades/2025-09-23_trades.json')
with open(trades_file, 'r', encoding='utf-8') as f:
    trades_data = json.load(f)

trades = trades_data['trades']

# 检查成本构成
all_amount = sum(t['amount'] for t in trades)
all_commission = sum(t['commission'] for t in trades)  
all_total_cost = sum(t['total_cost'] for t in trades)

print('💰 交易成本验证 (测试实例):')
print(f'投资金额: {all_amount:,.2f}元')
print(f'佣金: {all_commission:.2f}元')
print(f'总成本: {all_total_cost:.2f}元')
print(f'差异: {abs(all_total_cost - all_amount - all_commission):.6f}元')
print(f'✅ 成本=投资+佣金: {abs(all_total_cost - all_amount - all_commission) < 0.01}')
"
```

## 🔍 实时数据验证命令

### 实时资产价值计算（新功能）

```python
# 简化版 - 查看测试实例实时总资产
C:/dev/stock/.venv/Scripts/python.exe -c "
import sys
from pathlib import Path
sys.path.append(str(Path('.').absolute()))
sys.path.append('python/stock/tools')
from realtime_asset_calculator import RealTimeAssetCalculator

calc = RealTimeAssetCalculator()
calc.print_realtime_report('test')
"

# 详细版 - 查看每只股票的盈亏情况
C:/dev/stock/.venv/Scripts/python.exe python/stock/tools/realtime_asset_calculator.py --instance test --detailed

# 生产实例监控
C:/dev/stock/.venv/Scripts/python.exe python/stock/tools/realtime_asset_calculator.py --instance default

# 对比两个实例的表现
C:/dev/stock/.venv/Scripts/python.exe -c "
import sys
from pathlib import Path
sys.path.append(str(Path('.').absolute()))
from realtime_asset_calculator import RealTimeAssetCalculator

calc = RealTimeAssetCalculator()
print('🔥 测试实例:')
calc.print_realtime_report('test')
print('\\n' + '='*50 + '\\n')
print('📊 生产实例:')
calc.print_realtime_report('default')
"
```

### 测试实时价格获取

```python
C:/dev/stock/.venv/Scripts/python.exe -c "
import akshare as ak
from datetime import datetime

now = datetime.now()
current_time = now.strftime('%Y-%m-%d %H:%M:%S')
print(f'当前时间: {current_time}')
print('A股交易时间: 9:30-11:30, 13:00-15:00')

# 测试多只股票的实时价格
codes = ['000001', '000002', '600000', '000858', '002415']
today = now.strftime('%Y%m%d')

print('\\n盘中实时价格(以收盘价字段返回):')
for code in codes:
    try:
        df = ak.stock_zh_a_hist(symbol=code, period='daily', start_date=today, end_date=today, adjust='qfq')
        if not df.empty:
            latest = df.iloc[-1]
            price = latest.iloc[2]
            volume = latest.iloc[5]
            print(f'{code}: {price:.2f}元 (成交量: {volume})')
        else:
            print(f'{code}: 无数据')
    except Exception as e:
        print(f'{code}: 获取失败')
"
```

### 测试单只股票实时价格

```python
C:/dev/stock/.venv/Scripts/python.exe -c "
import akshare as ak
from datetime import datetime

code = '000001'  # 可修改为其他股票代码
today = datetime.now().strftime('%Y%m%d')
print(f'测试获取股票 {code} 的实时数据...')

try:
    df = ak.stock_zh_a_hist(symbol=code, period='daily', start_date=today, end_date=today, adjust='qfq')
    if not df.empty:
        latest = df.iloc[-1]
        trade_date = latest.iloc[0]
        close_price = latest.iloc[2]
        volume = latest.iloc[5]
        print(f'获取成功:')
        print(f'  日期: {trade_date}')
        print(f'  实时价格: {close_price}')
        print(f'  成交量: {volume}')
    else:
        print('未获取到数据')
except Exception as e:
    print(f'获取失败: {e}')
"
```

## 🗂️ 文件管理命令（测试实例）

### 清理测试实例（完全重新开始）

```bash
# 删除测试实例的所有数据
rm -r data/simulation/instances/test
```

### 清理当天测试数据（重新开始今天）

```bash
rm data/simulation/instances/test/state/2025-09-23.json
rm data/simulation/instances/test/trades/2025-09-23_trades.json
```

### 查看测试实例目录结构

```bash
tree data/simulation/instances/test
```

### 查看测试实例最新日志

```bash
tail -n 50 data/simulation/instances/test/logs/daily_rebalance.log
```

### 创建测试实例（如果不存在）

```python
C:/dev/stock/.venv/Scripts/python.exe -c "
import sys
from pathlib import Path
sys.path.append(str(Path('.').absolute()))

from simulation.core.instance_manager import InstanceManager

manager = InstanceManager()

# 创建测试实例配置
test_config = {
    'instance_name': 'test',
    'initial_capital': 1000000.0,
    'strategy': {
        'lookback_days': 126,
        'decline_threshold': 0.20,
        'top_n': 35,
        'min_listing_years': 5,
        'rebalance_frequency': 'monthly'
    },
    'risk_control': {
        'stop_loss': -0.15,
        'take_profit': 0.20,
        'max_position_ratio': 0.05,
        'check_frequency': 'daily',
        'concentration_limit': 0.10
    },
    'trading': {
        'commission_rate': 0.0001,
        'stamp_tax_rate': 0.001,
        'slippage_bps': 0,
        'min_shares': 100,
        'trading_hours': {
            'start': '09:30',
            'end': '15:00'
        }
    }
}

result = manager.create_instance('test', test_config)
if result:
    print('✅ 测试实例创建成功')
else:
    print('❌ 测试实例创建失败或已存在')
"
```

### 创建prod生产实例（正式模拟交易）

```python
C:/dev/stock/.venv/Scripts/python.exe -c "
import sys
from pathlib import Path
sys.path.append(str(Path('.').absolute()))

from simulation.core.instance_manager import InstanceManager

manager = InstanceManager()

# 创建生产实例配置 - 使用优化后的交易成本
prod_config = {
    'instance_name': 'prod',
    'initial_capital': 1000000.0,
    'strategy': {
        'lookback_days': 126,
        'decline_threshold': 0.20,
        'top_n': 35,
        'min_listing_years': 5,
        'rebalance_frequency': 'monthly'
    },
    'risk_control': {
        'stop_loss': -0.15,
        'take_profit': 0.20,
        'max_position_ratio': 0.05,
        'check_frequency': 'daily',
        'concentration_limit': 0.10
    },
    'trading': {
        'commission_rate': 0.0001,  # 万1佣金，免5元
        'stamp_tax_rate': 0.001,    # 千1印花税（仅卖出）
        'slippage_bps': 0,          # 0bp滑点
        'min_shares': 100,
        'trading_hours': {
            'start': '09:30',
            'end': '15:00'
        }
    }
}

result = manager.create_instance('prod', prod_config)
if result:
    print('✅ prod生产实例创建成功')
    print('配置摘要:')
    print(f'  初始资金: {prod_config[\"initial_capital\"]:,.0f}元')
    print(f'  佣金费率: {prod_config[\"trading\"][\"commission_rate\"]*10000:.1f}万')
    print(f'  印花税: {prod_config[\"trading\"][\"stamp_tax_rate\"]*1000:.1f}千')
    print(f'  滑点: {prod_config[\"trading\"][\"slippage_bps\"]}bp')
    print(f'  选股数量: {prod_config[\"strategy\"][\"top_n\"]}只')
else:
    print('❌ prod实例创建失败或已存在')
"
```

## 🏭 prod实例专用命令（正式模拟交易）

### 🚀 启动prod实例流程（一键开始）

#### 1. 创建prod实例

```python
C:/dev/stock/.venv/Scripts/python.exe -c "
import sys
from pathlib import Path
sys.path.append(str(Path('.').absolute()))

from simulation.core.instance_manager import InstanceManager

manager = InstanceManager()

# 创建生产实例配置 - 使用优化后的交易成本
prod_config = {
    'instance_name': 'prod',
    'initial_capital': 1000000.0,
    'strategy': {
        'lookback_days': 126,
        'decline_threshold': 0.20,
        'top_n': 35,
        'min_listing_years': 5,
        'rebalance_frequency': 'monthly'
    },
    'risk_control': {
        'stop_loss': -0.15,
        'take_profit': 0.20,
        'max_position_ratio': 0.05,
        'check_frequency': 'daily',
        'concentration_limit': 0.10
    },
    'trading': {
        'commission_rate': 0.0001,  # 万1佣金，免5元
        'stamp_tax_rate': 0.001,    # 千1印花税（仅卖出）
        'slippage_bps': 0,          # 0bp滑点
        'min_shares': 100,
        'trading_hours': {
            'start': '09:30',
            'end': '15:00'
        }
    }
}

result = manager.create_instance('prod', prod_config)
if result:
    print('✅ prod生产实例创建成功')
    print('配置摘要:')
    print(f'  初始资金: {prod_config[\"initial_capital\"]:,.0f}元')
    print(f'  佣金费率: {prod_config[\"trading\"][\"commission_rate\"]*10000:.1f}万')
    print(f'  印花税: {prod_config[\"trading\"][\"stamp_tax_rate\"]*1000:.1f}千')
    print(f'  滑点: {prod_config[\"trading\"][\"slippage_bps\"]}bp')
    print(f'  选股数量: {prod_config[\"strategy\"][\"top_n\"]}只')
else:
    print('❌ prod实例创建失败或已存在')
"
```

#### 2. 首次调仓（强制）

```bash
C:/dev/stock/.venv/Scripts/python.exe simulation/main.py --mode cronjob --instance prod --task daily_rebalance --force-rebalance
```

#### 3. 查看交易结果

```python
C:/dev/stock/.venv/Scripts/python.exe -c "
import json
from pathlib import Path

# 读取最新状态 - prod实例
state_file = Path('data/simulation/instances/prod/state/2025-09-23.json')
with open(state_file, 'r', encoding='utf-8') as f:
    state = json.load(f)

# 读取交易记录 - prod实例
trades_file = Path('data/simulation/instances/prod/trades/2025-09-23_trades.json')
with open(trades_file, 'r', encoding='utf-8') as f:
    trades_data = json.load(f)

trades = trades_data['trades']
total_value = state['portfolio']['total_value']
cash = state['portfolio']['cash']
market_value = state['portfolio']['market_value']

print('🏭 prod实例交易结果:')
print(f'   交易笔数: {len(trades)}')
print(f'   总资产: {total_value:,.2f} 元')
print(f'   现金: {cash:,.2f} 元')
print(f'   市值: {market_value:,.2f} 元')
print(f'   持仓股票数: {len(state[\"portfolio\"][\"positions\"])}')

# 成本分析
initial_capital = 1000000.00
gain_loss = total_value - initial_capital
all_commission = sum(t['commission'] for t in trades)

print(f'\\n💰 收益分析:')
print(f'   初始资金: {initial_capital:,.2f} 元')
print(f'   盈亏: {gain_loss:+.2f} 元')
print(f'   总佣金: {all_commission:.2f} 元')
print(f'   收益率: {gain_loss/initial_capital*100:+.4f}%')
"
```

#### 4. 实时价值监控

```python
C:/dev/stock/.venv/Scripts/python.exe -c "
import sys
from pathlib import Path
sys.path.append(str(Path('.').absolute()))
from realtime_asset_calculator import RealTimeAssetCalculator

calc = RealTimeAssetCalculator()
print('🏭 prod实例实时监控:')
calc.print_realtime_report('prod')
"
```

### 📊 prod实例日常监控

#### 每日风控检查

```bash
C:/dev/stock/.venv/Scripts/python.exe simulation/main.py --mode cronjob --instance prod --task risk_monitoring
```

#### 查看持仓详情

```python
C:/dev/stock/.venv/Scripts/python.exe -c "
import json
from pathlib import Path

state_file = Path('data/simulation/instances/prod/state/2025-09-23.json')
with open(state_file, 'r', encoding='utf-8') as f:
    state = json.load(f)

positions = state['portfolio']['positions']
print('🏭 prod实例当前持仓:')
for code, pos in positions.items():
    shares = pos['shares']
    cost = pos['cost']
    market_value = shares * cost
    print(f'  {code}: {shares}股 @{cost:.2f}元 = {market_value:,.2f}元')

print(f'\\n现金余额: {state[\"portfolio\"][\"cash\"]:,.2f}元')
print(f'闲置资金: {state[\"portfolio\"][\"idle_cash\"]:,.2f}元')
"
```

#### 成本效率验证

```python
C:/dev/stock/.venv/Scripts/python.exe -c "
import json
from pathlib import Path

trades_file = Path('data/simulation/instances/prod/trades/2025-09-23_trades.json')
with open(trades_file, 'r', encoding='utf-8') as f:
    trades_data = json.load(f)

trades = trades_data['trades']

all_amount = sum(t['amount'] for t in trades)
all_commission = sum(t['commission'] for t in trades)  
all_total_cost = sum(t['total_cost'] for t in trades)

print('🏭 prod实例交易成本分析:')
print(f'投资金额: {all_amount:,.2f}元')
print(f'佣金成本: {all_commission:.2f}元')
print(f'总成本: {all_total_cost:.2f}元')
print(f'成本率: {all_commission/all_amount*10000:.2f}万')
print(f'✅ 成本结构验证: {abs(all_total_cost - all_amount - all_commission) < 0.01}')
"
```

### 🔧 prod实例维护

#### 检查实例状态

```python
C:/dev/stock/.venv/Scripts/python.exe -c "
import sys
from pathlib import Path
sys.path.append(str(Path('.').absolute()))

from simulation.core.instance_manager import InstanceManager

manager = InstanceManager()
instances = manager.list_instances()
print('📋 所有实例:', instances)

if 'prod' in instances:
    config = manager.get_instance_config('prod')
    print('✅ prod实例状态正常')
    print(f'初始资金: {config[\"initial_capital\"]:,.0f}元')
    print(f'策略参数: {config[\"strategy\"][\"top_n\"]}只股票, {config[\"strategy\"][\"decline_threshold\"]*100}%跌幅')
else:
    print('❌ prod实例不存在，需要先创建')
"
```

#### 查看运行日志

```bash
tail -n 50 data/simulation/instances/prod/logs/daily_rebalance.log
```

#### 备份prod实例数据

```bash
# 创建备份目录
mkdir -p backup/prod_$(date +%Y%m%d)

# 备份配置和状态
cp data/simulation/instances/prod/config.json backup/prod_$(date +%Y%m%d)/
cp -r data/simulation/instances/prod/state backup/prod_$(date +%Y%m%d)/
cp -r data/simulation/instances/prod/trades backup/prod_$(date +%Y%m%d)/

echo "✅ prod实例备份完成: backup/prod_$(date +%Y%m%d)/"
```

### 📈 prod实例性能评估

#### 获取详细P&L报告

```python
C:/dev/stock/.venv/Scripts/python.exe python/stock/tools/realtime_asset_calculator.py --instance prod --detailed
```

#### 与历史回测对比

```python
C:/dev/stock/.venv/Scripts/python.exe -c "
# 获取prod实例实时表现
import sys
from pathlib import Path
sys.path.append(str(Path('.').absolute()))
from realtime_asset_calculator import RealTimeAssetCalculator
import json

calc = RealTimeAssetCalculator()
state_file = Path('data/simulation/instances/prod/state/2025-09-23.json')
with open(state_file, 'r', encoding='utf-8') as f:
    state = json.load(f)

initial_capital = 1000000.0
current_value = state['portfolio']['total_value']
current_return = (current_value - initial_capital) / initial_capital * 100

print('📊 prod实例 vs 历史回测对比:')
print(f'实时模拟收益率: {current_return:+.4f}%')
print(f'历史5年年化收益: +11.7%')
print(f'历史最大回撤: -31.0%')
print(f'历史夏普比率: 0.52')
print(f'\\n✨ 当前表现评估:')
if current_return > 0:
    print(f'✅ 正收益，符合策略预期')
else:
    print(f'⚠️  负收益，需要观察更长时间')
"
```

## ⚡ prod实例快速启动（推荐流程）

### 一键完整启动流程

```bash
# 1. 创建prod实例（如果不存在）
C:/dev/stock/.venv/Scripts/python.exe -c "exec(open('docs/common_commands.md').read().split('#### 1. 创建prod实例')[1].split('```')[1])"

# 2. 首次强制调仓
C:/dev/stock/.venv/Scripts/python.exe simulation/main.py --mode cronjob --instance prod --task daily_rebalance --force-rebalance

# 3. 查看交易结果
C:/dev/stock/.venv/Scripts/python.exe -c "exec(open('docs/common_commands.md').read().split('#### 3. 查看交易结果')[1].split('```')[1])"

# 4. 启动实时监控
C:/dev/stock/.venv/Scripts/python.exe -c "exec(open('docs/common_commands.md').read().split('#### 4. 实时价值监控')[1].split('```')[1])"
```

### 日常运维命令（复制粘贴版）

```bash
# 🔥 推荐：使用现成脚本（一键命令）
.\scripts\quick_monitor.ps1              # 快速监控
.\scripts\manage_trading.ps1 monitor     # 完整监控
.\scripts\manage_trading.ps1 risk        # 风控检查

# 传统命令方式
# 每日风控检查
C:/dev/stock/.venv/Scripts/python.exe simulation/main.py --mode cronjob --instance prod --task risk_monitoring

# 实时价值监控
C:/dev/stock/.venv/Scripts/python.exe python/stock/tools/realtime_asset_calculator.py --instance prod

# 查看详细P&L
C:/dev/stock/.venv/Scripts/python.exe python/stock/tools/realtime_asset_calculator.py --instance prod --detailed

# 查看运行日志
tail -n 20 data/simulation/instances/prod/logs/daily_rebalance.log
```

## ⚙️ 配置修改命令

### 检查测试实例配置

```python
C:/dev/stock/.venv/Scripts/python.exe -c "
import json
from pathlib import Path

config_file = Path('data/simulation/instances/test/config.json')
with open(config_file, 'r', encoding='utf-8') as f:
    config = json.load(f)

print('📋 测试实例配置:')
print(f'初始资金: {config[\"initial_capital\"]:,.0f}元')
print(f'佣金费率: {config[\"trading\"][\"commission_rate\"]*10000}万')
print(f'滑点: {config[\"trading\"][\"slippage_bps\"]}bp')
print(f'印花税: {config[\"trading\"][\"stamp_tax_rate\"]*1000}千')
print(f'选股数量: {config[\"strategy\"][\"top_n\"]}只')
print(f'跌幅阈值: {config[\"strategy\"][\"decline_threshold\"]*100}%')
"
```

## 📈 历史回测命令

### 运行完整历史回测

```bash
C:/dev/stock/.venv/Scripts/python.exe complete_backtest_system.py
```

### 运行主量化系统回测

```bash
C:/dev/stock/.venv/Scripts/python.exe main_quantitative_system.py
```

## 🚨 故障排查命令

### 检查系统组件状态

```python
C:/dev/stock/.venv/Scripts/python.exe -c "
import sys
from pathlib import Path
sys.path.append(str(Path('.').absolute()))

from simulation.core.instance_manager import InstanceManager

manager = InstanceManager()
instances = manager.list_instances()
print('📋 实例列表:', instances)

if 'default' in instances:
    config = manager.get_instance_config('default')
    print('✅ default实例配置正常')
else:
    print('❌ 未找到default实例')
"
```

### 检查测试实例数据文件完整性

```bash
ls -la data/simulation/instances/test/state/
ls -la data/simulation/instances/test/trades/
ls -la data/simulation/instances/test/config.json
```

## ⏰ Cronjob自动化配置

### 🤖 Windows任务计划程序配置

#### 创建每日风控检查任务

```powershell
# 创建每日上午9点风控检查任务
schtasks /create /tn "StockTradingRiskCheck" /tr "C:\dev\stock\.venv\Scripts\python.exe C:\dev\stock\simulation\main.py --mode cronjob --instance prod --task risk_monitoring" /sc daily /st 09:00 /f

# 验证任务创建
schtasks /query /tn "StockTradingRiskCheck"
```

#### 创建月末调仓任务

```powershell
# 创建每月最后一个工作日调仓任务（月末15:30执行）
schtasks /create /tn "StockTradingRebalance" /tr "C:\dev\stock\.venv\Scripts\python.exe C:\dev\stock\simulation\main.py --mode cronjob --instance prod --task daily_rebalance" /sc monthly /mo lastday /st 15:30 /f

# 验证任务创建
schtasks /query /tn "StockTradingRebalance"
```

#### 创建实时监控任务（可选）

```powershell
# 创建每小时实时价值监控任务
schtasks /create /tn "StockTradingMonitor" /tr "C:\dev\stock\.venv\Scripts\python.exe C:\dev\stock\python\stock\tools\realtime_asset_calculator.py --instance prod" /sc hourly /st 09:30 /et 15:00 /f

# 验证任务创建
schtasks /query /tn "StockTradingMonitor"
```

### 📋 任务管理命令

#### 查看所有交易相关任务

```powershell
schtasks /query | findstr "StockTrading"
```

#### 手动运行任务（测试用）

```powershell
# 手动触发风控检查
schtasks /run /tn "StockTradingRiskCheck"

# 手动触发调仓
schtasks /run /tn "StockTradingRebalance"

# 手动触发监控
schtasks /run /tn "StockTradingMonitor"
```

#### 删除任务（如需要）

```powershell
# 删除风控检查任务
schtasks /delete /tn "StockTradingRiskCheck" /f

# 删除调仓任务
schtasks /delete /tn "StockTradingRebalance" /f

# 删除监控任务
schtasks /delete /tn "StockTradingMonitor" /f
```

### 🐧 Linux Crontab配置（参考）

#### 编辑crontab

```bash
crontab -e
```

#### 添加定时任务

```bash
# 每日上午9点风控检查
0 9 * * 1-5 cd /path/to/stock && /path/to/.venv/bin/python simulation/main.py --mode cronjob --instance prod --task risk_monitoring

# 每月最后一个工作日15:30调仓
30 15 28-31 * 1-5 [ $(date -d tomorrow +\%d) -eq 1 ] && cd /path/to/stock && /path/to/.venv/bin/python simulation/main.py --mode cronjob --instance prod --task daily_rebalance

# 每小时实时监控（交易时间内）
30 9-15 * * 1-5 cd /path/to/stock && /path/to/.venv/bin/python python/stock/tools/realtime_asset_calculator.py --instance prod
```

### 🔧 Cronjob模式优化

#### 测试cronjob模式（推荐先测试）

```bash
# 使用test实例测试cronjob模式
C:/dev/stock/.venv/Scripts/python.exe simulation/main.py --mode cronjob --instance test --task daily_rebalance --force-rebalance

# 检查cronjob日志
tail -n 20 data/simulation/instances/test/logs/daily_rebalance.log
```

#### prod实例cronjob命令

```bash
# 每日风控检查
C:/dev/stock/.venv/Scripts/python.exe simulation/main.py --mode cronjob --instance prod --task risk_monitoring

# 调仓（正常模式，会检查时间）
C:/dev/stock/.venv/Scripts/python.exe simulation/main.py --mode cronjob --instance prod --task daily_rebalance

# 强制调仓（忽略时间检查）
C:/dev/stock/.venv/Scripts/python.exe simulation/main.py --mode cronjob --instance prod --task daily_rebalance --force-rebalance
```

### 📊 自动化监控脚本（推荐使用现成脚本）

#### 现有脚本总览

项目已提供多个现成的PowerShell脚本，位于 `scripts/` 目录：

```powershell
# 📁 scripts/ 目录包含：
# ├── setup_cronjob.ps1     # 一键配置Windows定时任务
# ├── manage_trading.ps1    # 系统管理工具（启停任务、执行监控等）
# ├── smart_rebalance.ps1   # 智能调仓脚本（带时间和条件检查）
# ├── quick_monitor.ps1     # 快速监控脚本
# └── README.md             # 详细使用说明
```

#### 🚀 推荐使用方式（一键命令）

```powershell
# 1. 快速监控（推荐）
.\scripts\quick_monitor.ps1

# 2. 系统管理工具
.\scripts\manage_trading.ps1 status     # 查看定时任务状态
.\scripts\manage_trading.ps1 monitor    # 立即执行监控
.\scripts\manage_trading.ps1 rebalance  # 立即执行调仓
.\scripts\manage_trading.ps1 risk       # 立即执行风控检查

# 3. 一键配置所有定时任务
.\scripts\setup_cronjob.ps1

# 4. 智能调仓（带时间检查）
.\scripts\smart_rebalance.ps1
```

#### 手动创建监控脚本（如需自定义）

```powershell
# 创建自定义monitor_prod.ps1脚本
@"
# 股票交易系统监控脚本
Set-Location "C:\dev\stock"

Write-Host "=== $(Get-Date) 开始监控 ===" -ForegroundColor Green

# 1. 检查实例状态
Write-Host "1. 检查prod实例状态..." -ForegroundColor Yellow
& C:\dev\stock\.venv\Scripts\python.exe -c "
import sys
from pathlib import Path
sys.path.append(str(Path('.').absolute()))
from simulation.core.instance_manager import InstanceManager
manager = InstanceManager()
instances = manager.list_instances()
print('实例列表:', instances)
if 'prod' in instances:
    print('✅ prod实例正常')
else:
    print('❌ prod实例异常')
"

# 2. 执行风控检查
Write-Host "2. 执行风控检查..." -ForegroundColor Yellow
& C:\dev\stock\.venv\Scripts\python.exe simulation\main.py --mode cronjob --instance prod --task risk_monitoring

# 3. 获取实时价值
Write-Host "3. 获取实时价值..." -ForegroundColor Yellow
& C:\dev\stock\.venv\Scripts\python.exe python\stock\tools\realtime_asset_calculator.py --instance prod

Write-Host "=== 监控完成 ===" -ForegroundColor Green
"@ | Out-File -FilePath "monitor_prod.ps1" -Encoding UTF8

Write-Host "✅ 监控脚本已创建: monitor_prod.ps1"
```

### ⚙️ 高级Cronjob配置

#### 创建智能调仓脚本（检查市场开盘状态）

```powershell
# 创建smart_rebalance.ps1
@"
# 智能调仓脚本 - 检查交易日和交易时间
Set-Location "C:\dev\stock"

# 检查是否为交易日（简单版本，可以根据需要完善）
$today = Get-Date
$dayOfWeek = $today.DayOfWeek
$hour = $today.Hour

Write-Host "当前时间: $today" -ForegroundColor Cyan

# 检查是否为工作日
if ($dayOfWeek -eq [System.DayOfWeek]::Saturday -or $dayOfWeek -eq [System.DayOfWeek]::Sunday) {
    Write-Host "今天是周末，跳过调仓" -ForegroundColor Yellow
    exit 0
}

# 检查是否在交易时间内（9:30-15:00）
if ($hour -lt 9 -or $hour -gt 15) {
    Write-Host "非交易时间，跳过调仓" -ForegroundColor Yellow
    exit 0
}

Write-Host "执行智能调仓..." -ForegroundColor Green
& C:\dev\stock\.venv\Scripts\python.exe simulation\main.py --mode cronjob --instance prod --task daily_rebalance

Write-Host "调仓完成，查看结果..." -ForegroundColor Green
& C:\dev\stock\.venv\Scripts\python.exe python\stock\tools\realtime_asset_calculator.py --instance prod
"@ | Out-File -FilePath "smart_rebalance.ps1" -Encoding UTF8

Write-Host "✅ 智能调仓脚本已创建: smart_rebalance.ps1"
```

### 🎯 推荐自动化配置（一键设置）

#### 🔥 使用现成脚本（推荐）

```powershell
# 一键配置所有定时任务（推荐方式）
.\scripts\setup_cronjob.ps1

# 查看配置结果
.\scripts\manage_trading.ps1 status

# 测试手动执行
.\scripts\manage_trading.ps1 monitor
```

#### 手动配置（如需自定义）

```powershell
# 1. 创建每日风控检查（工作日上午9点）
schtasks /create /tn "StockTradingRiskCheck" /tr "C:\dev\stock\.venv\Scripts\python.exe C:\dev\stock\simulation\main.py --mode cronjob --instance prod --task risk_monitoring" /sc weekly /d MON,TUE,WED,THU,FRI /st 09:00 /f

# 2. 创建月末调仓（每月最后一个工作日下午3:30）
schtasks /create /tn "StockTradingRebalance" /tr "C:\dev\stock\smart_rebalance.ps1" /sc monthly /mo lastday /st 15:30 /f

# 3. 创建实时监控（工作日每2小时）
schtasks /create /tn "StockTradingMonitor" /tr "C:\dev\stock\.venv\Scripts\python.exe C:\dev\stock\python\stock\tools\realtime_asset_calculator.py --instance prod" /sc weekly /d MON,TUE,WED,THU,FRI /ri 120 /st 09:30 /et 15:00 /f

Write-Host "✅ 所有自动化任务已配置完成！"
Write-Host "可以使用以下命令查看："
Write-Host "schtasks /query | findstr StockTrading"
```

## 💡 使用说明

1. **推荐工作流程**：所有测试都使用`test`实例，生产使用`default`实例
2. **复制粘贴使用**：直接复制需要的命令到PowerShell中执行
3. **修改日期**：将命令中的`2025-09-23`替换为需要的日期
4. **修改股票代码**：将`000001`等替换为要查询的股票代码
5. **路径说明**：所有命令都假设在`c:\dev\stock`目录下执行

## 📅 日常运维流程

### 测试开发流程（推荐）

1. 创建测试实例：`test`
2. 强制调仓测试：使用`--instance test --force-rebalance`
3. 检查测试结果：查看测试实例数据
4. 快速清理重来：删除`test`实例数据
5. 验证无误后：使用`default`实例进行生产

### 每日交易流程

1. 强制调仓（首次运行或需要重新配置）
2. 检查交易结果
3. 验证成本构成
4. 查看实时价格变化

### 问题排查流程

1. 检查系统组件状态
2. 查看最新日志
3. 验证配置文件
4. 测试数据源连接

---

**💾 快速开始：**

```bash
# 1. 创建测试实例
C:/dev/stock/.venv/Scripts/python.exe -c "exec(open('docs/common_commands.md').read().split('### 创建测试实例')[1].split('```')[1])"

# 2. 运行测试交易
C:/dev/stock/.venv/Scripts/python.exe simulation/main.py --mode cronjob --instance test --task daily_rebalance --force-rebalance

# 3. 查看结果
tree data/simulation/instances/test

# 4. 清理重来（如需要）
rm -r data/simulation/instances/test
```

**💾 保存说明：此文档保存在 `docs/common_commands.md`，随时可以查阅和更新。**
