#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调度器
负责定时任务的调度和管理
"""

import time
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Callable
from pathlib import Path

class Scheduler:
    """任务调度器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.tasks = {}
        self.running = False
        self.thread = None
    
    def add_task(self, name: str, func: Callable, interval_minutes: int, 
                 start_time: str = None, enabled: bool = True):
        """
        添加定时任务
        
        Args:
            name: 任务名称
            func: 执行函数
            interval_minutes: 执行间隔（分钟）
            start_time: 首次执行时间 HH:MM
            enabled: 是否启用
        """
        self.tasks[name] = {
            "func": func,
            "interval_minutes": interval_minutes,
            "start_time": start_time,
            "enabled": enabled,
            "last_run": None,
            "next_run": self._calculate_next_run(interval_minutes, start_time)
        }
        self.logger.info(f"添加任务: {name}, 间隔: {interval_minutes}分钟")
    
    def _calculate_next_run(self, interval_minutes: int, start_time: str = None) -> datetime:
        """计算下次执行时间"""
        now = datetime.now()
        
        if start_time:
            # 解析开始时间
            hour, minute = map(int, start_time.split(':'))
            next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # 如果今天的时间已过，调整到明天
            if next_run <= now:
                next_run += timedelta(days=1)
        else:
            # 立即开始，按间隔执行
            next_run = now + timedelta(minutes=interval_minutes)
        
        return next_run
    
    def start_daemon(self):
        """启动守护进程模式"""
        if self.running:
            self.logger.warning("调度器已在运行中")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()
        self.logger.info("调度器守护进程已启动")
        
        try:
            # 主线程保持运行
            while self.running:
                time.sleep(60)  # 每分钟检查一次
        except KeyboardInterrupt:
            self.stop()
    
    def stop(self):
        """停止调度器"""
        self.running = False
        if self.thread:
            self.thread.join()
        self.logger.info("调度器已停止")
    
    def _run_scheduler(self):
        """调度器主循环"""
        self.logger.info("调度器开始运行")
        
        while self.running:
            try:
                now = datetime.now()
                
                for name, task in self.tasks.items():
                    if not task["enabled"]:
                        continue
                    
                    if task["next_run"] <= now:
                        self._execute_task(name, task)
                        
                        # 计算下次执行时间
                        task["last_run"] = now
                        task["next_run"] = now + timedelta(minutes=task["interval_minutes"])
                
                time.sleep(30)  # 每30秒检查一次
                
            except Exception as e:
                self.logger.error(f"调度器运行异常: {e}")
                time.sleep(60)
    
    def _execute_task(self, name: str, task: Dict):
        """执行任务"""
        try:
            self.logger.info(f"执行任务: {name}")
            task["func"]()
            self.logger.info(f"任务完成: {name}")
        except Exception as e:
            self.logger.error(f"任务执行失败 {name}: {e}")
    
    def show_tasks_status(self):
        """显示任务状态"""
        if not self.tasks:
            print("没有注册的任务")
            return
        
        print(f"\n{'任务名称':<20} {'状态':<8} {'间隔(分钟)':<10} {'下次执行':<20} {'最后执行':<20}")
        print("-" * 85)
        
        for name, task in self.tasks.items():
            status = "启用" if task["enabled"] else "禁用"
            interval = str(task["interval_minutes"])
            next_run = task["next_run"].strftime("%Y-%m-%d %H:%M") if task["next_run"] else "未设置"
            last_run = task["last_run"].strftime("%Y-%m-%d %H:%M") if task["last_run"] else "从未执行"
            
            print(f"{name:<20} {status:<8} {interval:<10} {next_run:<20} {last_run:<20}")

def setup_default_tasks():
    """设置默认任务"""
    scheduler = Scheduler()
    
    # 每日数据更新任务 (早上6点)
    def daily_data_update():
        from simulation.cronjobs.data_update import run_data_update
        run_data_update()
    
    scheduler.add_task("daily_data_update", daily_data_update, 
                      interval_minutes=24*60, start_time="06:00")
    
    # 每日调仓检查 (早上9点)
    def daily_rebalance_check():
        from simulation.cronjobs.daily_rebalance import run_daily_rebalance
        run_daily_rebalance("default")
    
    scheduler.add_task("daily_rebalance", daily_rebalance_check, 
                      interval_minutes=24*60, start_time="09:00")
    
    # 风控监控 (每5分钟)
    def risk_monitoring():
        from simulation.cronjobs.risk_monitoring import run_risk_monitoring
        run_risk_monitoring("default")
    
    scheduler.add_task("risk_monitoring", risk_monitoring, 
                      interval_minutes=5)
    
    return scheduler