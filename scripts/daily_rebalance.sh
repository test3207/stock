#!/bin/bash
# 每日调仓任务
cd C:\dev\stock
python -c "
import sys
sys.path.append('.')
from simulation.cronjobs.daily_rebalance import run_daily_rebalance
run_daily_rebalance('default')
" >> logs/cronjobs/daily_rebalance.log 2>&1
