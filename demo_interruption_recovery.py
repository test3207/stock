#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中断恢复示例脚本
演示实时模拟系统的中断恢复功能
"""

import sys
import time
import logging
from pathlib import Path

# 添加项目根路径
sys.path.append(str(Path(__file__).parent.parent))

from simulation.core.task_execution_manager import TaskExecutionManager

def demo_interruption_recovery():
    """演示中断恢复功能"""
    print("=== 中断恢复功能演示 ===\n")
    
    # 设置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # 创建任务管理器
    task_manager = TaskExecutionManager("demo_instance")
    
    # 创建演示任务
    task_id = task_manager.create_task("demo_task", "2025-09-23")
    print(f"创建演示任务: {task_id}")
    
    # 添加演示步骤
    task_manager.add_step("step1", "初始化演示", demo_step1)
    task_manager.add_step("step2", "数据准备演示", demo_step2)
    task_manager.add_step("step3", "长时间处理演示（可中断）", demo_step3)
    task_manager.add_step("step4", "结果保存演示", demo_step4)
    
    print("\n任务步骤已定义:")
    progress = task_manager.get_task_progress()
    print(f"总步骤数: {progress['total_steps']}")
    
    print("\n开始执行任务...")
    print("提示: 可以按 Ctrl+C 中断任务，然后重新运行脚本恢复执行")
    
    try:
        # 执行任务
        success = task_manager.execute_task()
        
        if success:
            print("\n✅ 任务执行完成！")
        else:
            print("\n❌ 任务执行失败")
        
        # 显示最终进度
        final_progress = task_manager.get_task_progress()
        print(f"最终进度: {final_progress}")
        
    except KeyboardInterrupt:
        print("\n\n⚠️ 任务被中断！")
        print("任务状态已保存，重新运行此脚本将从中断点继续执行")
        
        # 显示中断时的进度
        progress = task_manager.get_task_progress()
        print(f"中断时进度: {progress}")

def demo_step1(checkpoint_data=None, **kwargs):
    """演示步骤1"""
    if checkpoint_data:
        print("从检查点恢复步骤1数据")
        return checkpoint_data
    
    print("执行步骤1: 初始化...")
    time.sleep(2)  # 模拟处理时间
    
    result = {"initialized": True, "timestamp": time.time()}
    print("步骤1完成")
    return result

def demo_step2(checkpoint_data=None, **kwargs):
    """演示步骤2"""
    if checkpoint_data:
        print("从检查点恢复步骤2数据")
        return checkpoint_data
    
    print("执行步骤2: 数据准备...")
    time.sleep(3)  # 模拟处理时间
    
    result = {"data_prepared": True, "records": 1000}
    print("步骤2完成")
    return result

def demo_step3(checkpoint_data=None, **kwargs):
    """演示步骤3（长时间处理）"""
    if checkpoint_data:
        print("从检查点恢复步骤3数据")
        return checkpoint_data
    
    print("执行步骤3: 长时间处理（10秒）...")
    print("提示: 可以在这里按 Ctrl+C 中断")
    
    # 模拟长时间处理
    for i in range(10):
        print(f"处理进度: {i+1}/10")
        time.sleep(1)
    
    result = {"processing_completed": True, "total_time": 10}
    print("步骤3完成")
    return result

def demo_step4(checkpoint_data=None, **kwargs):
    """演示步骤4"""
    if checkpoint_data:
        print("从检查点恢复步骤4数据")
        return checkpoint_data
    
    print("执行步骤4: 保存结果...")
    time.sleep(1)  # 模拟处理时间
    
    result = {"results_saved": True, "final_status": "success"}
    print("步骤4完成")
    return result

if __name__ == "__main__":
    demo_interruption_recovery()