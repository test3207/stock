#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
风控监控 cronjob 任务
负责实时监控投资组合风险，执行止损止盈
"""

import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# 添加项目根路径
sys.path.append(str(Path(__file__).parent.parent.parent))

from simulation.core.instance_manager import InstanceManager
from simulation.core.state_manager import StateManager
from simulation.core.cache_manager import CacheManager
from simulation.engines.risk_engine import RiskEngine
from simulation.engines.trading_engine import TradingEngine

def run_risk_monitoring(instance_name: str):
    """
    执行风控监控任务
    
    Args:
        instance_name: 实例名称
    """
    logger = logging.getLogger(f"risk_monitoring.{instance_name}")
    
    try:
        logger.info(f"开始风控监控: 实例={instance_name}")
        
        # 初始化管理器
        instance_manager = InstanceManager()
        state_manager = StateManager(instance_name)
        cache_manager = CacheManager()
        
        # 获取实例配置
        config = instance_manager.get_instance_config(instance_name)
        if not config:
            logger.error(f"实例配置不存在: {instance_name}")
            return False
        
        # 加载当前状态
        current_state = state_manager.load_latest_state()
        if not current_state:
            logger.warning("没有找到当前状态，跳过风控监控")
            return True
        
        portfolio_state = current_state["portfolio"]
        risk_control_state = current_state["risk_control"]
        
        # 如果没有持仓，跳过监控
        positions = portfolio_state.get("positions", {})
        if not positions:
            logger.info("当前无持仓，跳过风控监控")
            return True
        
        # 初始化风控引擎
        risk_engine = RiskEngine(config, cache_manager)
        trading_engine = TradingEngine(config, cache_manager)
        
        # 执行风控检查
        risk_triggers = risk_engine.check_portfolio_risk(
            portfolio_state, risk_control_state
        )
        
        if not risk_triggers:
            logger.info("风控检查通过，无需执行交易")
            # 更新检查时间
            risk_control_state["last_check_time"] = datetime.now().isoformat()
            
            # 保存更新的状态
            today = datetime.now().strftime('%Y-%m-%d')
            state_manager.save_daily_state(today, portfolio_state, risk_control_state)
            return True
        
        logger.info(f"检测到 {len(risk_triggers)} 个风控触发")
        
        # 执行风控交易
        trading_results = trading_engine.execute_risk_control_trades(
            portfolio_state, risk_triggers
        )
        
        if not trading_results:
            logger.error("风控交易执行失败")
            return False
        
        # 更新状态
        new_portfolio_state = trading_results["new_portfolio_state"]
        trading_records = trading_results["trading_records"]
        
        # 更新风控状态
        for trigger in risk_triggers:
            stock_code = trigger["stock_code"]
            trigger_type = trigger["type"]
            
            # 添加到已触发列表
            if stock_code not in risk_control_state["triggered_stocks"]:
                risk_control_state["triggered_stocks"].append(stock_code)
            
            # 更新计数
            if trigger_type == "stop_loss":
                risk_control_state["stop_loss_count"] += 1
            elif trigger_type == "take_profit":
                risk_control_state["take_profit_count"] += 1
        
        risk_control_state["last_check_time"] = datetime.now().isoformat()
        
        # 保存状态
        today = datetime.now().strftime('%Y-%m-%d')
        success = state_manager.save_daily_state(
            today, new_portfolio_state, risk_control_state, trading_records
        )
        
        if success:
            instance_manager.update_instance_status(instance_name, "active", today)
            logger.info(f"风控监控完成，执行了 {len(trading_records)} 笔交易")
            return True
        else:
            logger.error("保存风控状态失败")
            return False
        
    except Exception as e:
        logger.error(f"风控监控执行失败: {e}", exc_info=True)
        return False

def run_portfolio_health_check(instance_name: str) -> Dict:
    """
    执行投资组合健康检查
    
    Args:
        instance_name: 实例名称
        
    Returns:
        Dict: 健康检查结果
    """
    logger = logging.getLogger(f"health_check.{instance_name}")
    
    try:
        state_manager = StateManager(instance_name)
        current_state = state_manager.load_latest_state()
        
        if not current_state:
            return {"status": "error", "message": "无法加载当前状态"}
        
        portfolio_state = current_state["portfolio"]
        risk_control_state = current_state["risk_control"]
        
        health_result = {
            "timestamp": datetime.now().isoformat(),
            "instance": instance_name,
            "status": "healthy",
            "checks": {},
            "summary": {}
        }
        
        # 检查资金配置
        total_value = portfolio_state.get("total_value", 0)
        cash = portfolio_state.get("cash", 0)
        idle_cash = portfolio_state.get("idle_cash", 0)
        market_value = portfolio_state.get("market_value", 0)
        
        cash_ratio = (cash + idle_cash) / max(total_value, 1)
        position_ratio = market_value / max(total_value, 1)
        
        health_result["checks"]["cash_allocation"] = {
            "status": "ok" if 0.05 <= cash_ratio <= 0.95 else "warning",
            "cash_ratio": round(cash_ratio, 4),
            "position_ratio": round(position_ratio, 4)
        }
        
        # 检查持仓分散度
        positions = portfolio_state.get("positions", {})
        position_count = len(positions)
        
        if position_count == 0:
            concentration_status = "warning"
        elif position_count < 10:
            concentration_status = "warning"
        elif position_count > 50:
            concentration_status = "warning"
        else:
            concentration_status = "ok"
        
        health_result["checks"]["diversification"] = {
            "status": concentration_status,
            "position_count": position_count,
            "target_count": 35
        }
        
        # 检查风控触发情况
        triggered_count = len(risk_control_state.get("triggered_stocks", []))
        stop_loss_count = risk_control_state.get("stop_loss_count", 0)
        take_profit_count = risk_control_state.get("take_profit_count", 0)
        
        risk_status = "ok"
        if stop_loss_count > position_count * 0.3:  # 超过30%止损
            risk_status = "warning"
        
        health_result["checks"]["risk_control"] = {
            "status": risk_status,
            "triggered_stocks": triggered_count,
            "stop_loss_count": stop_loss_count,
            "take_profit_count": take_profit_count
        }
        
        # 综合评估
        failed_checks = [name for name, check in health_result["checks"].items() 
                        if check["status"] != "ok"]
        
        if failed_checks:
            health_result["status"] = "warning"
            health_result["issues"] = failed_checks
        
        # 汇总信息
        health_result["summary"] = {
            "total_value": total_value,
            "position_count": position_count,
            "cash_ratio": round(cash_ratio, 4),
            "risk_events": stop_loss_count + take_profit_count
        }
        
        return health_result
        
    except Exception as e:
        logger.error(f"投资组合健康检查失败: {e}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    # 支持命令行调用
    import argparse
    
    parser = argparse.ArgumentParser(description='执行风控监控任务')
    parser.add_argument('--instance', type=str, default='default', help='实例名称')
    parser.add_argument('--health-check', action='store_true', help='执行健康检查')
    
    args = parser.parse_args()
    
    # 设置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    if args.health_check:
        result = run_portfolio_health_check(args.instance)
        print(f"健康检查结果: {result}")
        sys.exit(0)
    else:
        success = run_risk_monitoring(args.instance)
        sys.exit(0 if success else 1)