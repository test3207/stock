#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实时模拟系统主程序入口
A股量化交易系统 - 实时数据模拟层主控程序

核心功能：
1. 统一入口管理多个实例
2. 调度器驱动的定时任务执行
3. 系统监控与异常处理
4. cronjob兼容模式
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime
import logging

# 添加项目根路径
sys.path.append(str(Path(__file__).parent.parent))

# 导入时区感知工具
try:
    from python.stock.utils.timezone_helper import get_trading_timestamp, get_trading_date, get_cst_now
except ImportError:
    # 回退实现
    def get_trading_timestamp():
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    def get_trading_date():
        return datetime.now().strftime('%Y-%m-%d')
    def get_cst_now():
        return datetime.now()

from simulation.core.instance_manager import InstanceManager
from simulation.core.scheduler import Scheduler
from simulation.core.monitor import SystemMonitor

def setup_logging():
    """设置日志"""
    log_dir = Path(__file__).parent.parent / "data" / "simulation" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / f"main_{get_trading_date().replace('-', '')}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def main():
    """主程序入口"""
    parser = argparse.ArgumentParser(description='实时模拟交易系统')
    parser.add_argument('--mode', choices=['daemon', 'cronjob', 'interactive'], 
                       default='interactive', help='运行模式')
    parser.add_argument('--instance', type=str, default='default', 
                       help='实例名称')
    parser.add_argument('--task', type=str, 
                       help='特定任务: daily_rebalance, risk_monitoring, data_update')
    parser.add_argument('--date', type=str, 
                       help='指定日期 YYYY-MM-DD')
    parser.add_argument('--force-restart', action='store_true',
                       help='强制重新开始任务（忽略中断恢复）')
    parser.add_argument('--force-rebalance', action='store_true',
                       help='强制执行调仓（忽略调仓时间检查）')
    parser.add_argument('--show-progress', action='store_true',
                       help='显示任务执行进度')
    
    args = parser.parse_args()
    logger = setup_logging()
    
    try:
        logger.info(f"启动实时模拟系统 - 模式: {args.mode}, 实例: {args.instance}")
        
        # 初始化实例管理器
        instance_manager = InstanceManager()
        
        # 初始化系统监控
        monitor = SystemMonitor()
        
        if args.show_progress:
            # 显示任务进度
            from simulation.core.task_execution_manager import TaskExecutionManager
            task_manager = TaskExecutionManager(args.instance)
            progress = task_manager.get_task_progress()
            print(f"任务进度: {progress}")
            return 0
        
        if args.mode == 'cronjob':
            # cronjob模式：执行单次任务
            logger.info(f"cronjob模式 - 执行任务: {args.task}")
            
            if args.task == 'daily_rebalance':
                from simulation.cronjobs.daily_rebalance import run_daily_rebalance
                success = run_daily_rebalance(args.instance, args.date, args.force_restart, args.force_rebalance)
                return 0 if success else 1
            elif args.task == 'risk_monitoring':
                from simulation.cronjobs.risk_monitoring import run_risk_monitoring
                success = run_risk_monitoring(args.instance)
                return 0 if success else 1
            elif args.task == 'data_update':
                from simulation.cronjobs.data_update import run_data_update
                success = run_data_update()
                return 0 if success else 1
            else:
                logger.error(f"未知任务: {args.task}")
                return 1
                
        elif args.mode == 'daemon':
            # 守护进程模式：持续运行调度器
            logger.info("守护进程模式 - 启动调度器")
            scheduler = Scheduler()
            scheduler.start_daemon()
            
        elif args.mode == 'interactive':
            # 交互模式：手动操作
            logger.info("交互模式启动")
            interactive_mode(instance_manager, monitor)
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("用户中断程序")
        return 0
    except Exception as e:
        logger.error(f"系统异常: {e}", exc_info=True)
        return 1

def interactive_mode(instance_manager, monitor):
    """交互模式"""
    print("\n=== 实时模拟交易系统 ===")
    print("1. 查看实例状态")
    print("2. 创建新实例")
    print("3. 运行日度调仓")
    print("4. 运行风控监控")
    print("5. 系统监控")
    print("6. 查看任务进度")
    print("7. 恢复中断任务")
    print("8. 强制重启任务")
    print("0. 退出")
    
    while True:
        try:
            choice = input("\n请选择操作: ").strip()
            
            if choice == '0':
                break
            elif choice == '1':
                instance_manager.show_instances_status()
            elif choice == '2':
                name = input("实例名称: ").strip()
                instance_manager.create_instance(name)
            elif choice == '3':
                instance = input("实例名称 (默认default): ").strip() or 'default'
                date = input("日期 YYYY-MM-DD (默认今日): ").strip()
                force_restart = input("强制重启? (y/n): ").strip().lower() == 'y'
                from simulation.cronjobs.daily_rebalance import run_daily_rebalance
                success = run_daily_rebalance(instance, date if date else None, force_restart)
                print(f"调仓任务{'成功' if success else '失败'}")
            elif choice == '4':
                instance = input("实例名称 (默认default): ").strip() or 'default'
                from simulation.cronjobs.risk_monitoring import run_risk_monitoring
                success = run_risk_monitoring(instance)
                print(f"风控监控{'成功' if success else '失败'}")
            elif choice == '5':
                monitor.show_system_status()
            elif choice == '6':
                instance = input("实例名称 (默认default): ").strip() or 'default'
                from simulation.core.task_execution_manager import TaskExecutionManager
                task_manager = TaskExecutionManager(instance)
                progress = task_manager.get_task_progress()
                print(f"任务进度: {progress}")
            elif choice == '7':
                print("恢复中断任务功能：任务会自动检测并恢复中断的执行")
                print("请使用选项3或4执行任务，系统会自动恢复中断点")
            elif choice == '8':
                instance = input("实例名称 (默认default): ").strip() or 'default'
                task_type = input("任务类型 (daily_rebalance/risk_monitoring): ").strip()
                date = input("日期 YYYY-MM-DD (默认今日): ").strip() or get_trading_date()
                
                if task_type == 'daily_rebalance':
                    from simulation.cronjobs.daily_rebalance import run_daily_rebalance
                    success = run_daily_rebalance(instance, date, force_restart=True)
                    print(f"强制重启调仓任务{'成功' if success else '失败'}")
                else:
                    print("目前只支持强制重启日度调仓任务")
            else:
                print("无效选择")
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"操作失败: {e}")

if __name__ == "__main__":
    sys.exit(main())