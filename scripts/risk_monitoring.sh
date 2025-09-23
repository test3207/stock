#!/bin/bash
# 风控监控任务
cd C:\dev\stock
python -c "
import sys
sys.path.append('.')
from simulation.cronjobs.risk_monitoring import run_risk_monitoring
run_risk_monitoring('default')
" >> logs/cronjobs/risk_monitoring.log 2>&1
