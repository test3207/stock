#!/usr/bin/env python3
"""
GitHub Actions 工作流摘要生成脚本
"""

import json
import os
import sys
from datetime import datetime

# 尝试导入时区助手，如果失败则使用基本实现
try:
    # 添加项目路径
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    sys.path.insert(0, os.path.join(project_root, 'python'))
    from stock.utils.timezone_helper import get_iso_timestamp, get_cst_now
    
    def get_timestamp():
        return get_iso_timestamp()
        
except ImportError:
    # 回退到基本实现
    def get_timestamp():
        return datetime.now().isoformat()

def generate_workflow_summary(output_dir, run_id, commit_sha, trigger, output_format):
    """生成工作流摘要"""
    
    # 生成工作流摘要
    summary = {
        'workflow_info': {
            'timestamp': get_timestamp(),
            'run_id': run_id,
            'commit_sha': commit_sha,
            'trigger': trigger,
            'python_version': '3.13.7'
        },
        'system_info': {
            'backtest_system': 'main_quantitative_system.py',
            'strategy': 'Enhanced Drawdown Strategy',
            'output_format': output_format
        }
    }

    # 检查是否有结果文件
    result_files = []
    if os.path.exists(output_dir):
        result_files = [f for f in os.listdir(output_dir) if f.endswith('.json')]

    summary['results'] = {
        'files_generated': len(result_files),
        'file_list': result_files
    }

    # 保存摘要
    summary_path = os.path.join(output_dir, 'workflow_summary.json')
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
        
    print('✅ Workflow summary generated')
    print(f'📁 Found {len(result_files)} result files')
    
    return summary

if __name__ == "__main__":
    if len(sys.argv) != 6:
        print("Usage: python generate_workflow_summary.py <output_dir> <run_id> <commit_sha> <trigger> <output_format>")
        sys.exit(1)
        
    output_dir, run_id, commit_sha, trigger, output_format = sys.argv[1:6]
    generate_workflow_summary(output_dir, run_id, commit_sha, trigger, output_format)