# 股票交易系统管理脚本
param(
    [Parameter(Position=0)]
    [ValidateSet("status", "monitor", "rebalance", "risk", "start", "stop", "remove", "help")]
    [string]$Action = "help"
)

$WorkDir = "C:\dev\stock"
$PythonExe = "$WorkDir\.venv\Scripts\python.exe"

function Show-Help {
    Write-Host "🎯 股票交易系统管理工具" -ForegroundColor Green
    Write-Host ""
    Write-Host "用法: .\manage_trading.ps1 <action>" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "可用操作:" -ForegroundColor Yellow
    Write-Host "  status     - 查看定时任务状态" -ForegroundColor White
    Write-Host "  monitor    - 立即执行监控" -ForegroundColor White
    Write-Host "  rebalance  - 立即执行调仓" -ForegroundColor White
    Write-Host "  risk       - 立即执行风控检查" -ForegroundColor White
    Write-Host "  start      - 启用所有定时任务" -ForegroundColor White
    Write-Host "  stop       - 停用所有定时任务" -ForegroundColor White
    Write-Host "  remove     - 删除所有定时任务" -ForegroundColor White
    Write-Host "  help       - 显示此帮助" -ForegroundColor White
    Write-Host ""
    Write-Host "示例:" -ForegroundColor Cyan
    Write-Host "  .\manage_trading.ps1 status" -ForegroundColor Gray
    Write-Host "  .\manage_trading.ps1 monitor" -ForegroundColor Gray
}

function Show-TaskStatus {
    Write-Host "📋 定时任务状态:" -ForegroundColor Green
    
    # 检查风控任务（多个）
    Write-Host "  🛡️  风控检查任务:" -ForegroundColor Yellow
    $riskTasks = 1..8 | ForEach-Object { "StockTradingRiskCheck_$_" }
    $riskCount = 0
    
    foreach ($task in $riskTasks) {
        $status = schtasks /query /tn $task 2>$null
        if ($LASTEXITCODE -eq 0) {
            $riskCount++
        }
    }
    
    if ($riskCount -gt 0) {
        Write-Host "     ✅ $riskCount/8 个风控任务已创建" -ForegroundColor Green
    } else {
        Write-Host "     ❌ 未找到风控任务" -ForegroundColor Red
    }
    
    # 检查其他任务
    $otherTasks = @("StockTradingMonitor", "StockTradingRebalance")
    
    foreach ($task in $otherTasks) {
        $status = schtasks /query /tn $task 2>$null
        if ($LASTEXITCODE -eq 0) {
            $statusLine = $status | Select-String "状态:|Status:" | Select-Object -First 1
            if ($statusLine) {
                $state = $statusLine.ToString().Split(":")[1].Trim()
                Write-Host "  ✅ $task : $state" -ForegroundColor Green
            } else {
                Write-Host "  ✅ $task : 已创建" -ForegroundColor Green
            }
        } else {
            Write-Host "  ❌ $task : 未找到" -ForegroundColor Red
        }
    }
}

function Invoke-Monitor {
    Write-Host "🔍 执行实时监控..." -ForegroundColor Yellow
    Set-Location $WorkDir
    & $PythonExe "$WorkDir\python\stock\tools\realtime_asset_calculator.py" --instance prod
}

function Invoke-Rebalance {
    Write-Host "⚖️  执行调仓..." -ForegroundColor Yellow
    Set-Location $WorkDir
    
    # 询问是否强制调仓
    $force = Read-Host "是否强制调仓？(y/N)"
    if ($force -eq "y" -or $force -eq "Y") {
        & $PythonExe "$WorkDir\simulation\main.py" --mode cronjob --instance prod --task daily_rebalance --force-rebalance
    } else {
        & $PythonExe "$WorkDir\simulation\main.py" --mode cronjob --instance prod --task daily_rebalance
    }
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "调仓完成，显示结果..." -ForegroundColor Green
        Invoke-Monitor
    }
}

function Invoke-RiskCheck {
    Write-Host "🛡️  执行风控检查..." -ForegroundColor Yellow
    Set-Location $WorkDir
    & $PythonExe "$WorkDir\simulation\main.py" --mode cronjob --instance prod --task risk_monitoring
}

function Start-Tasks {
    Write-Host "▶️  启用所有定时任务..." -ForegroundColor Green
    
    # 启用风控任务
    $riskTasks = 1..8 | ForEach-Object { "StockTradingRiskCheck_$_" }
    $otherTasks = @("StockTradingMonitor", "StockTradingRebalance")
    $allTasks = $riskTasks + $otherTasks
    
    foreach ($task in $allTasks) {
        schtasks /change /tn $task /enable 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✅ 已启用: $task" -ForegroundColor Green
        }
    }
}

function Stop-Tasks {
    Write-Host "⏸️  停用所有定时任务..." -ForegroundColor Yellow
    
    # 停用风控任务
    $riskTasks = 1..8 | ForEach-Object { "StockTradingRiskCheck_$_" }
    $otherTasks = @("StockTradingMonitor", "StockTradingRebalance")
    $allTasks = $riskTasks + $otherTasks
    
    foreach ($task in $allTasks) {
        schtasks /change /tn $task /disable 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✅ 已停用: $task" -ForegroundColor Yellow
        }
    }
}

function Remove-Tasks {
    Write-Host "🗑️  删除所有定时任务..." -ForegroundColor Red
    
    $confirm = Read-Host "确定要删除所有任务吗？这将移除所有自动化配置 (y/N)"
    if ($confirm -ne "y" -and $confirm -ne "Y") {
        Write-Host "操作已取消" -ForegroundColor Gray
        return
    }
    
    # 删除风控任务
    $riskTasks = 1..8 | ForEach-Object { "StockTradingRiskCheck_$_" }
    $otherTasks = @("StockTradingMonitor", "StockTradingRebalance")
    $allTasks = $riskTasks + $otherTasks
    
    foreach ($task in $allTasks) {
        schtasks /delete /tn $task /f 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✅ 已删除: $task" -ForegroundColor Red
        }
    }
}

# 主逻辑
switch ($Action) {
    "status" { Show-TaskStatus }
    "monitor" { Invoke-Monitor }
    "rebalance" { Invoke-Rebalance }
    "risk" { Invoke-RiskCheck }
    "start" { Start-Tasks }
    "stop" { Stop-Tasks }
    "remove" { Remove-Tasks }
    "help" { Show-Help }
    default { Show-Help }
}