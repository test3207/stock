#!/bin/bash
# 数据更新任务
cd C:\dev\stock
python -c "
import sys
sys.path.append('.')
from simulation.cronjobs.data_update import run_data_update
run_data_update('default')
" >> logs/cronjobs/data_update.log 2>&1
