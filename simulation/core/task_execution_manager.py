#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务执行管理器
负责可中断、可恢复的任务执行管理
"""

import json
import logging
import uuid
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum

class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    INTERRUPTED = "interrupted"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

class TaskStep:
    """任务步骤"""
    def __init__(self, step_id: str, description: str, func, **kwargs):
        self.step_id = step_id
        self.description = description
        self.func = func
        self.kwargs = kwargs
        self.status = TaskStatus.PENDING
        self.start_time = None
        self.end_time = None
        self.result = None
        self.error = None
        self.checkpoint_data = {}

class TaskExecutionManager:
    """任务执行管理器"""
    
    def __init__(self, instance_name: str):
        self.instance_name = instance_name
        self.base_dir = Path(__file__).parent.parent.parent
        self.execution_dir = self.base_dir / "data" / "simulation" / "instances" / instance_name / "execution"
        self.execution_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger(f"{__name__}.{instance_name}")
        
        self.current_task_id = None
        self.task_steps = []
        self.execution_state = {}
    
    def create_task(self, task_type: str, target_date: str, force_restart: bool = False) -> str:
        """
        创建新任务或恢复中断任务
        
        Args:
            task_type: 任务类型 (daily_rebalance, risk_monitoring, data_update)
            target_date: 目标日期
            force_restart: 是否强制重新开始
            
        Returns:
            str: 任务ID
        """
        task_id = f"{task_type}_{target_date}_{datetime.now().strftime('%H%M%S')}"
        
        # 检查是否有中断的任务可以恢复
        if not force_restart:
            existing_task = self._find_interrupted_task(task_type, target_date)
            if existing_task:
                self.logger.info(f"发现中断任务，将恢复执行: {existing_task}")
                return self._resume_task(existing_task)
        
        # 创建新任务
        self.current_task_id = task_id
        self.task_steps = []
        self.execution_state = {
            "task_id": task_id,
            "task_type": task_type,
            "target_date": target_date,
            "created_at": datetime.now().isoformat(),
            "status": TaskStatus.PENDING.value,
            "steps": [],
            "current_step": 0,
            "checkpoints": {}
        }
        
        self._save_execution_state()
        self.logger.info(f"创建新任务: {task_id}")
        return task_id
    
    def add_step(self, step_id: str, description: str, func, **kwargs):
        """添加任务步骤"""
        step = TaskStep(step_id, description, func, **kwargs)
        self.task_steps.append(step)
        
        self.execution_state["steps"].append({
            "step_id": step_id,
            "description": description,
            "status": TaskStatus.PENDING.value,
            "start_time": None,
            "end_time": None,
            "error": None
        })
        
        self._save_execution_state()
    
    def execute_task(self, max_retries: int = 3) -> bool:
        """
        执行任务（支持中断恢复）
        
        Args:
            max_retries: 最大重试次数
            
        Returns:
            bool: 是否执行成功
        """
        try:
            self.execution_state["status"] = TaskStatus.RUNNING.value
            self.execution_state["started_at"] = datetime.now().isoformat()
            self._save_execution_state()
            
            current_step = self.execution_state.get("current_step", 0)
            
            for i in range(current_step, len(self.task_steps)):
                step = self.task_steps[i]
                self.execution_state["current_step"] = i
                
                # 执行步骤
                success = self._execute_step(step, max_retries, i)
                
                if not success:
                    self.execution_state["status"] = TaskStatus.FAILED.value
                    self._save_execution_state()
                    return False
                
                # 保存检查点
                self._save_checkpoint(step.step_id, step.result)
                self._save_execution_state()
            
            # 任务完成
            self.execution_state["status"] = TaskStatus.COMPLETED.value
            self.execution_state["completed_at"] = datetime.now().isoformat()
            self._save_execution_state()
            
            self.logger.info(f"任务执行完成: {self.current_task_id}")
            return True
            
        except KeyboardInterrupt:
            self.logger.info("任务被用户中断")
            self.execution_state["status"] = TaskStatus.INTERRUPTED.value
            self.execution_state["interrupted_at"] = datetime.now().isoformat()
            self._save_execution_state()
            return False
        except Exception as e:
            self.logger.error(f"任务执行异常: {e}", exc_info=True)
            self.execution_state["status"] = TaskStatus.FAILED.value
            self.execution_state["error"] = str(e)
            self._save_execution_state()
            return False
    
    def _execute_step(self, step: TaskStep, max_retries: int, step_index: int) -> bool:
        """执行单个步骤"""
        for attempt in range(max_retries + 1):
            try:
                self.logger.info(f"执行步骤: {step.description} (尝试 {attempt + 1}/{max_retries + 1})")
                
                step.status = TaskStatus.RUNNING
                step.start_time = datetime.now().isoformat()
                
                # 更新执行状态
                step_state = self.execution_state["steps"][self.execution_state["current_step"]]
                step_state["status"] = TaskStatus.RUNNING.value
                step_state["start_time"] = step.start_time
                
                # 合并前面步骤的结果到当前步骤的kwargs
                merged_kwargs = step.kwargs.copy()
                for prev_step in self.task_steps[:step_index]:
                    if prev_step.result and isinstance(prev_step.result, dict):
                        merged_kwargs.update(prev_step.result)
                
                # 执行步骤函数
                result = step.func(**merged_kwargs, checkpoint_data=step.checkpoint_data)
                
                step.result = result
                step.status = TaskStatus.COMPLETED
                step.end_time = datetime.now().isoformat()
                
                # 更新执行状态
                step_state["status"] = TaskStatus.COMPLETED.value
                step_state["end_time"] = step.end_time
                
                self.logger.info(f"步骤完成: {step.description}")
                return True
                
            except Exception as e:
                step.error = str(e)
                step.status = TaskStatus.FAILED
                
                # 更新执行状态
                step_state = self.execution_state["steps"][self.execution_state["current_step"]]
                step_state["status"] = TaskStatus.FAILED.value
                step_state["error"] = str(e)
                
                self.logger.warning(f"步骤执行失败: {step.description}, 错误: {e}")
                
                if attempt < max_retries:
                    self.logger.info(f"将在 5 秒后重试...")
                    import time
                    time.sleep(5)
                else:
                    self.logger.error(f"步骤最终失败: {step.description}")
                    return False
        
        return False
    
    def _save_checkpoint(self, step_id: str, data: Any):
        """保存检查点数据"""
        self.execution_state["checkpoints"][step_id] = {
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
    
    def get_checkpoint_data(self, step_id: str) -> Any:
        """获取检查点数据"""
        checkpoint = self.execution_state.get("checkpoints", {}).get(step_id)
        return checkpoint["data"] if checkpoint else None
    
    def _save_execution_state(self):
        """保存执行状态"""
        try:
            state_file = self.execution_dir / f"{self.current_task_id}.json"
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(self.execution_state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"保存执行状态失败: {e}")
    
    def _find_interrupted_task(self, task_type: str, target_date: str) -> Optional[str]:
        """查找中断的任务"""
        try:
            for state_file in self.execution_dir.glob("*.json"):
                with open(state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                
                if (state.get("task_type") == task_type and 
                    state.get("target_date") == target_date and 
                    state.get("status") == TaskStatus.INTERRUPTED.value):
                    return state["task_id"]
            
            return None
        except Exception as e:
            self.logger.error(f"查找中断任务失败: {e}")
            return None
    
    def _resume_task(self, task_id: str) -> str:
        """恢复中断的任务"""
        try:
            state_file = self.execution_dir / f"{task_id}.json"
            with open(state_file, 'r', encoding='utf-8') as f:
                self.execution_state = json.load(f)
            
            self.current_task_id = task_id
            
            # 重建任务步骤（需要外部重新定义，这里只是占位）
            self.task_steps = []
            
            self.logger.info(f"恢复任务: {task_id}, 当前步骤: {self.execution_state.get('current_step', 0)}")
            return task_id
            
        except Exception as e:
            self.logger.error(f"恢复任务失败: {e}")
            raise
    
    def get_task_progress(self) -> Dict:
        """获取任务进度"""
        if not self.execution_state:
            return {"progress": 0, "status": "no_task"}
        
        total_steps = len(self.execution_state.get("steps", []))
        current_step = self.execution_state.get("current_step", 0)
        completed_steps = sum(1 for step in self.execution_state.get("steps", []) 
                             if step.get("status") == TaskStatus.COMPLETED.value)
        
        progress = (completed_steps / max(total_steps, 1)) * 100
        
        return {
            "task_id": self.current_task_id,
            "progress": round(progress, 2),
            "status": self.execution_state.get("status"),
            "current_step": current_step,
            "total_steps": total_steps,
            "completed_steps": completed_steps
        }
    
    def cleanup_old_executions(self, keep_days: int = 7):
        """清理旧的执行记录"""
        try:
            cutoff_time = datetime.now().timestamp() - (keep_days * 24 * 3600)
            removed_count = 0
            
            for state_file in self.execution_dir.glob("*.json"):
                if state_file.stat().st_mtime < cutoff_time:
                    state_file.unlink()
                    removed_count += 1
            
            self.logger.info(f"清理了 {removed_count} 个旧执行记录")
            return removed_count
        except Exception as e:
            self.logger.error(f"清理执行记录失败: {e}")
            return 0