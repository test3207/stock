# 股票交易系统 - 自动化任务配置脚本
# 运行此脚本设置Windows定时任务

Write-Host "🚀 开始配置股票交易系统自动化任务..." -ForegroundColor Green

# 设置工作目录
$WorkDir = "C:\dev\stock"
$PythonExe = "$WorkDir\.venv\Scripts\python.exe"

# 检查路径是否存在
if (-not (Test-Path $WorkDir)) {
    Write-Host "❌ 工作目录不存在: $WorkDir" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $PythonExe)) {
    Write-Host "❌ Python环境不存在: $PythonExe" -ForegroundColor Red
    exit 1
}

Write-Host "✅ 环境检查通过" -ForegroundColor Green

# 1. 创建高频风控检查任务（每30分钟一次，交易时间内）
Write-Host "1. 创建高频风控检查任务..." -ForegroundColor Yellow

# 定义风控检查时间点（每30分钟）
$RiskCheckTimes = @("09:45", "10:15", "10:45", "11:15", "13:15", "13:45", "14:15", "14:45")
$RiskCheckCmd = "`"$PythonExe`" `"$WorkDir\simulation\main.py`" --mode cronjob --instance prod --task risk_monitoring"

$successCount = 0
for ($i = 0; $i -lt $RiskCheckTimes.Length; $i++) {
    $taskName = "StockTradingRiskCheck_$($i+1)"
    $time = $RiskCheckTimes[$i]
    
    Write-Host "  创建风控任务: $taskName ($time)" -ForegroundColor Gray
    schtasks /create /tn $taskName /tr $RiskCheckCmd /sc weekly /d MON,TUE,WED,THU,FRI /st $time /f | Out-Null
    
    if ($LASTEXITCODE -eq 0) {
        $successCount++
    } else {
        Write-Host "  ❌ $taskName 创建失败" -ForegroundColor Red
    }
}

if ($successCount -eq $RiskCheckTimes.Length) {
    Write-Host "✅ 风控检查任务创建成功 ($successCount/$($RiskCheckTimes.Length))" -ForegroundColor Green
    Write-Host "   检查频率: 每30分钟 (交易时间内)" -ForegroundColor Gray
} else {
    Write-Host "⚠️  风控检查任务部分创建成功 ($successCount/$($RiskCheckTimes.Length))" -ForegroundColor Yellow
}

# 2. 创建实时监控任务（简化版，每日中午执行）
Write-Host "2. 创建实时监控任务..." -ForegroundColor Yellow
$MonitorTask = "StockTradingMonitor"
$MonitorCmd = "`"$PythonExe`" `"$WorkDir\realtime_asset_calculator.py`" --instance prod"

schtasks /create /tn $MonitorTask /tr $MonitorCmd /sc daily /st 12:00 /f | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ 实时监控任务创建成功" -ForegroundColor Green
} else {
    Write-Host "❌ 实时监控任务创建失败" -ForegroundColor Red
}

# 3. 创建智能调仓脚本
Write-Host "3. 创建智能调仓脚本..." -ForegroundColor Yellow
$SmartRebalanceScript = @"
# 智能调仓脚本 - 检查交易日和交易时间
Set-Location "$WorkDir"

`$today = Get-Date
`$dayOfWeek = `$today.DayOfWeek
`$hour = `$today.Hour
`$minute = `$today.Minute
`$currentTime = `$hour * 100 + `$minute

Write-Host "当前时间: `$today" -ForegroundColor Cyan

# 检查是否为工作日
if (`$dayOfWeek -eq [System.DayOfWeek]::Saturday -or `$dayOfWeek -eq [System.DayOfWeek]::Sunday) {
    Write-Host "今天是周末，跳过调仓" -ForegroundColor Yellow
    exit 0
}

# 检查是否在交易时间内（9:30-15:00）
if (`$currentTime -lt 930 -or `$currentTime -gt 1500) {
    Write-Host "非交易时间（当前: `$(`$hour):`$(`$minute.ToString('00'))），跳过调仓" -ForegroundColor Yellow
    exit 0
}

Write-Host "执行智能调仓..." -ForegroundColor Green
& "$PythonExe" "$WorkDir\simulation\main.py" --mode cronjob --instance prod --task daily_rebalance

if (`$LASTEXITCODE -eq 0) {
    Write-Host "调仓完成，查看结果..." -ForegroundColor Green
    & "$PythonExe" "$WorkDir\realtime_asset_calculator.py" --instance prod
} else {
    Write-Host "调仓执行失败" -ForegroundColor Red
}
"@

$SmartRebalanceScript | Out-File -FilePath "$WorkDir\scripts\smart_rebalance.ps1" -Encoding UTF8
Write-Host "✅ 智能调仓脚本已创建: scripts\smart_rebalance.ps1" -ForegroundColor Green

# 4. 创建月末调仓任务（每月28日）
Write-Host "4. 创建月末调仓任务..." -ForegroundColor Yellow
$RebalanceTask = "StockTradingRebalance"
$RebalanceCmd = "PowerShell.exe -File `"$WorkDir\scripts\smart_rebalance.ps1`""

schtasks /create /tn $RebalanceTask /tr $RebalanceCmd /sc monthly /m JAN,FEB,MAR,APR,MAY,JUN,JUL,AUG,SEP,OCT,NOV,DEC /d 28 /st 15:30 /f | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ 月末调仓任务创建成功" -ForegroundColor Green
} else {
    Write-Host "❌ 月末调仓任务创建失败" -ForegroundColor Red
}

# 5. 创建快速监控脚本
Write-Host "5. 创建快速监控脚本..." -ForegroundColor Yellow
$QuickMonitorScript = @"
# 股票交易系统快速监控
Set-Location "$WorkDir"

Write-Host "=== `$(Get-Date) 快速监控开始 ===" -ForegroundColor Green

# 检查prod实例状态
Write-Host "检查prod实例状态..." -ForegroundColor Yellow
& "$PythonExe" -c "
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

# 获取实时价值
Write-Host "获取实时价值..." -ForegroundColor Yellow
& "$PythonExe" "$WorkDir\realtime_asset_calculator.py" --instance prod

Write-Host "=== 快速监控完成 ===" -ForegroundColor Green
"@

$QuickMonitorScript | Out-File -FilePath "$WorkDir\scripts\quick_monitor.ps1" -Encoding UTF8
Write-Host "✅ 快速监控脚本已创建: scripts\quick_monitor.ps1" -ForegroundColor Green

# 显示配置摘要
Write-Host "`n📋 自动化任务配置摘要:" -ForegroundColor Cyan
Write-Host "   ✅ 高频风控检查: 工作日每30分钟 (9:45-14:45)" -ForegroundColor White
Write-Host "   ✅ 实时监控: 每日 12:00" -ForegroundColor White
Write-Host "   ✅ 月末调仓: 每月28日 15:30" -ForegroundColor White

Write-Host "`n🔧 管理命令:" -ForegroundColor Cyan
Write-Host "   查看任务: schtasks /query | findstr StockTrading" -ForegroundColor White
Write-Host "   手动监控: .\scripts\quick_monitor.ps1" -ForegroundColor White
Write-Host "   手动调仓: .\scripts\smart_rebalance.ps1" -ForegroundColor White
Write-Host "   系统管理: .\scripts\manage_trading.ps1 <command>" -ForegroundColor White

Write-Host "`n🎉 自动化配置完成！系统将按计划自动运行。" -ForegroundColor Green