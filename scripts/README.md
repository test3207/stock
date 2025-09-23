# 股票交易系统工具脚本

本目录包含股票交易系统的各种管理和自动化脚本。

## 📁 目录结构

### PowerShell 脚本 (Windows)

- **`setup_cronjob.ps1`** - 一键配置Windows定时任务
- **`manage_trading.ps1`** - 系统管理工具（启停任务、执行监控等）
- **`smart_rebalance.ps1`** - 智能调仓脚本（带时间和条件检查）
- **`quick_monitor.ps1`** - 快速监控脚本（检查系统状态和实时价值）

### Shell 脚本 (Linux/Unix)

- **`daily_rebalance.sh`** - 每日调仓脚本
- **`risk_monitoring.sh`** - 风控监控脚本
- **`data_update.sh`** - 数据更新脚本

### 配置文件

- **`crontab_example.txt`** - Linux crontab配置示例

## 🚀 快速开始

### Windows 用户

```powershell
# 1. 配置自动化任务
.\scripts\setup_cronjob.ps1

# 2. 查看任务状态
.\scripts\manage_trading.ps1 status

# 3. 手动监控
.\scripts\quick_monitor.ps1
```

### Linux 用户

```bash
# 1. 设置执行权限
chmod +x scripts/*.sh

# 2. 编辑crontab
crontab -e
# 然后添加 scripts/crontab_example.txt 中的内容

# 3. 手动执行
./scripts/daily_rebalance.sh
```

## 📋 脚本说明

### setup_cronjob.ps1

**功能**: 自动配置Windows定时任务  
**包含**:

- 高频风控检查（每30分钟）
- 实时监控（每日12:00）
- 月末调仓（每月28日15:30）

**使用**: `.\scripts\setup_cronjob.ps1`

### manage_trading.ps1

**功能**: 系统管理工具  
**命令**:

- `status` - 查看定时任务状态
- `monitor` - 立即执行监控
- `rebalance` - 立即执行调仓
- `risk` - 立即执行风控检查
- `start` - 启用所有定时任务
- `stop` - 停用所有定时任务
- `remove` - 删除所有定时任务

**使用**: `.\scripts\manage_trading.ps1 <command>`

### smart_rebalance.ps1

**功能**: 智能调仓（带条件检查）  
**检查**:

- 是否为工作日
- 是否在交易时间内
- 是否为月末调仓期

**使用**: `.\scripts\smart_rebalance.ps1`

### quick_monitor.ps1

**功能**: 快速系统监控  
**内容**:

- 检查实例状态
- 获取实时价值
- 显示收益情况

**使用**: `.\scripts\quick_monitor.ps1`

## 📅 定时任务时间表

### 高频风控检查

- 09:45, 10:15, 10:45, 11:15 (上午)
- 13:15, 13:45, 14:15, 14:45 (下午)
- **频率**: 每30分钟
- **目的**: 及时执行止损止盈

### 实时监控

- **时间**: 每日12:00
- **目的**: 跟踪组合价值变化

### 月末调仓

- **时间**: 每月28日15:30
- **目的**: 执行策略调仓

## 🔧 维护

### 查看日志

```powershell
# Windows
tail -n 20 data/simulation/instances/prod/logs/daily_rebalance.log

# Linux
tail -20 data/simulation/instances/prod/logs/daily_rebalance.log
```

### 备份数据

```powershell
# Windows
mkdir backup/prod_$(Get-Date -Format "yyyyMMdd")
Copy-Item -Recurse data/simulation/instances/prod/* backup/prod_$(Get-Date -Format "yyyyMMdd")/

# Linux
mkdir -p backup/prod_$(date +%Y%m%d)
cp -r data/simulation/instances/prod/* backup/prod_$(date +%Y%m%d)/
```

## 📝 注意事项

1. **权限**: 确保脚本有执行权限
2. **路径**: 所有脚本假设在项目根目录下执行
3. **Python环境**: 确保虚拟环境已激活
4. **时区**: 时间设置基于本地时区
5. **网络**: 确保能访问股票数据源

## 🆘 故障排查

### 常见问题

1. **任务不执行**: 检查Windows任务计划程序或crontab设置
2. **Python错误**: 检查虚拟环境和依赖包
3. **数据获取失败**: 检查网络连接和akshare可用性
4. **权限错误**: 检查文件和目录权限

### 诊断命令

```powershell
# 检查任务状态
.\scripts\manage_trading.ps1 status

# 检查Python环境
C:\dev\stock\.venv\Scripts\python.exe --version

# 测试数据获取
C:\dev\stock\.venv\Scripts\python.exe -c "import akshare as ak; print('OK')"
```
