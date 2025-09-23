# 智能调仓脚本 - 检查交易日和交易时间
Set-Location "C:\dev\stock"

$today = Get-Date
$dayOfWeek = $today.DayOfWeek
$hour = $today.Hour
$minute = $today.Minute
$currentTime = $hour * 100 + $minute

Write-Host "当前时间: $today" -ForegroundColor Cyan

# 检查是否为工作日
if ($dayOfWeek -eq [System.DayOfWeek]::Saturday -or $dayOfWeek -eq [System.DayOfWeek]::Sunday) {
    Write-Host "今天是周末，跳过调仓" -ForegroundColor Yellow
    exit 0
}

# 检查是否在交易时间内（9:30-15:00）
if ($currentTime -lt 930 -or $currentTime -gt 1500) {
    Write-Host "非交易时间（当前: $($hour):$($minute.ToString('00'))），跳过调仓" -ForegroundColor Yellow
    exit 0
}

Write-Host "执行智能调仓..." -ForegroundColor Green
& "C:\dev\stock\.venv\Scripts\python.exe" "C:\dev\stock\simulation\main.py" --mode cronjob --instance prod --task daily_rebalance

if ($LASTEXITCODE -eq 0) {
    Write-Host "调仓完成，查看结果..." -ForegroundColor Green
    & "C:\dev\stock\.venv\Scripts\python.exe" "C:\dev\stock\realtime_asset_calculator.py" --instance prod
} else {
    Write-Host "调仓执行失败" -ForegroundColor Red
}
