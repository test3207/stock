# 股票交易系统快速监控
Set-Location "C:\dev\stock"

Write-Host "=== $(Get-Date) 快速监控开始 ===" -ForegroundColor Green

# 检查prod实例状态
Write-Host "检查prod实例状态..." -ForegroundColor Yellow
& "C:\dev\stock\.venv\Scripts\python.exe" -c "
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
& "C:\dev\stock\.venv\Scripts\python.exe" "C:\dev\stock\realtime_asset_calculator.py" --instance prod

Write-Host "=== 快速监控完成 ===" -ForegroundColor Green
