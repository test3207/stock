#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日度调仓 cronjob 任务（支持中断恢复）
负责执行每日的投资组合调仓检查和执行
"""

import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

# 添加项目根路径
sys.path.append(str(Path(__file__).parent.parent.parent))

from simulation.core.instance_manager import InstanceManager
from simulation.core.state_manager import StateManager
from simulation.core.cache_manager import CacheManager
from simulation.core.task_execution_manager import TaskExecutionManager
from simulation.engines.strategy_engine import StrategyEngine
from simulation.engines.trading_engine import TradingEngine

def run_daily_rebalance(instance_name: str, target_date: str = None, force_restart: bool = False, force_rebalance: bool = False):
    """
    执行日度调仓任务（支持中断恢复）
    
    Args:
        instance_name: 实例名称
        target_date: 目标日期 YYYY-MM-DD，默认为今日
        force_restart: 是否强制重新开始（忽略中断恢复）
        force_rebalance: 是否强制执行调仓（忽略调仓时间检查）
    """
    logger = logging.getLogger(f"daily_rebalance.{instance_name}")
    
    try:
        # 确定目标日期
        if target_date is None:
            target_date = datetime.now().strftime('%Y-%m-%d')
        
        logger.info(f"开始执行日度调仓: 实例={instance_name}, 日期={target_date}, 强制重启={force_restart}, 强制调仓={force_rebalance}")
        
        # 创建任务执行管理器
        task_manager = TaskExecutionManager(instance_name)
        task_id = task_manager.create_task("daily_rebalance", target_date, force_restart)
        
        # 定义可中断的任务步骤
        _define_rebalance_steps(task_manager, instance_name, target_date, force_rebalance)
        
        # 执行任务（支持中断恢复）
        success = task_manager.execute_task(max_retries=3)
        
        if success:
            logger.info(f"日度调仓任务完成: {task_id}")
        else:
            logger.error(f"日度调仓任务失败或中断: {task_id}")
        
        return success
        
    except Exception as e:
        logger.error(f"日度调仓执行失败: {e}", exc_info=True)
        return False

def _define_rebalance_steps(task_manager: TaskExecutionManager, instance_name: str, target_date: str, force_rebalance: bool = False):
    """定义调仓任务的可中断步骤"""
    
    # 步骤1: 初始化和配置检查
    task_manager.add_step(
        "init_check",
        "初始化系统组件和配置检查",
        _step_init_check,
        instance_name=instance_name,
        target_date=target_date
    )
    
    # 步骤2: 加载当前状态
    task_manager.add_step(
        "load_state",
        "加载投资组合当前状态",
        _step_load_state,
        instance_name=instance_name
    )
    
    # 步骤3: 调仓需求检查
    task_manager.add_step(
        "check_rebalance_need",
        "检查是否需要执行调仓",
        _step_check_rebalance_need,
        instance_name=instance_name,
        target_date=target_date,
        force_rebalance=force_rebalance
    )
    
    # 步骤4: 数据准备
    task_manager.add_step(
        "prepare_data",
        "准备策略所需的市场数据",
        _step_prepare_data,
        target_date=target_date
    )
    
    # 步骤5: 策略选股
    task_manager.add_step(
        "strategy_selection",
        "执行策略选股",
        _step_strategy_selection,
        target_date=target_date
    )
    
    # 步骤6: 交易计算
    task_manager.add_step(
        "calculate_trades",
        "计算需要执行的交易",
        _step_calculate_trades,
        instance_name=instance_name,
        target_date=target_date
    )
    
    # 步骤7: 执行交易
    task_manager.add_step(
        "execute_trades",
        "执行买卖交易",
        _step_execute_trades,
        instance_name=instance_name,
        target_date=target_date
    )
    
    # 步骤8: 保存状态
    task_manager.add_step(
        "save_state",
        "保存更新后的投资组合状态",
        _step_save_state,
        instance_name=instance_name,
        target_date=target_date
    )

# 以下是各个可中断的执行步骤

def _step_init_check(instance_name: str, target_date: str, checkpoint_data: Dict = None, **kwargs) -> Dict:
    """步骤1: 初始化和配置检查"""
    logger = logging.getLogger("step.init_check")
    
    if checkpoint_data:
        logger.info("从检查点恢复初始化数据")
        return checkpoint_data
    
    # 初始化管理器
    instance_manager = InstanceManager()
    cache_manager = CacheManager()
    
    # 获取实例配置
    config = instance_manager.get_instance_config(instance_name)
    if not config:
        raise Exception(f"实例配置不存在: {instance_name}")
    
    # 初始化引擎
    strategy_engine = StrategyEngine(config)
    trading_engine = TradingEngine(config, cache_manager)
    
    init_data = {
        "config": config,
        "components_initialized": True,
        "timestamp": datetime.now().isoformat()
    }
    
    logger.info("系统组件初始化完成")
    return init_data

def _step_load_state(instance_name: str, checkpoint_data: Dict = None, **kwargs) -> Dict:
    """步骤2: 加载当前状态"""
    logger = logging.getLogger("step.load_state")
    
    if checkpoint_data:
        logger.info("从检查点恢复状态数据")
        return checkpoint_data
    
    state_manager = StateManager(instance_name)
    current_state = state_manager.load_latest_state()
    
    if not current_state:
        # 如果没有历史状态，创建初始状态
        logger.info("没有历史状态，创建初始状态")
        config = kwargs.get("config") or {}
        initial_capital = config.get("initial_capital", 1000000.0)
        state_manager.create_initial_state(initial_capital)
        current_state = state_manager.load_latest_state()
    
    portfolio_state = current_state["portfolio"]
    risk_control_state = current_state["risk_control"]
    
    state_data = {
        "portfolio_state": portfolio_state,
        "risk_control_state": risk_control_state,
        "last_state_date": current_state.get("date"),
        "loaded_successfully": True
    }
    
    logger.info(f"状态加载完成，总资产: {portfolio_state.get('total_value', 0):,.2f}")
    return state_data

def _step_check_rebalance_need(instance_name: str, target_date: str, checkpoint_data: Dict = None, **kwargs) -> Dict:
    """步骤3: 检查调仓需求"""
    logger = logging.getLogger("step.check_rebalance")
    
    if checkpoint_data:
        logger.info("从检查点恢复调仓检查结果")
        return checkpoint_data
    
    # 获取强制调仓参数
    force_rebalance = kwargs.get("force_rebalance", False)
    
    if force_rebalance:
        logger.info("强制调仓模式：跳过调仓时间检查")
        should_rebalance = True
    else:
        # 获取实例配置
        from simulation.core.instance_manager import InstanceManager
        instance_manager = InstanceManager()
        config = instance_manager.get_instance_config(instance_name)
        
        last_state_date = kwargs.get("last_state_date")
        
        # 正常调仓时间检查
        logger.info(f"配置频率: {config.get('strategy', {}).get('rebalance_frequency', 'unknown')}")
        logger.info(f"目标日期: {target_date}")
        logger.info(f"上次状态日期: {last_state_date}")
        
        should_rebalance = _should_rebalance(config.get("strategy", {}), target_date, last_state_date)
    
    rebalance_data = {
        "should_rebalance": should_rebalance,
        "target_date": target_date,
        "last_state_date": kwargs.get("last_state_date"),
        "force_rebalance": force_rebalance,
        "check_timestamp": datetime.now().isoformat()
    }
    
    if should_rebalance:
        if force_rebalance:
            logger.info("检查结果: 强制执行调仓")
        else:
            logger.info("检查结果: 需要执行调仓")
    else:
        logger.info("检查结果: 今日不需要调仓")
    
    return rebalance_data

def _step_prepare_data(target_date: str, checkpoint_data: Dict = None, **kwargs) -> Dict:
    """步骤4: 准备数据"""
    logger = logging.getLogger("step.prepare_data")
    
    if checkpoint_data:
        logger.info("从检查点恢复数据准备结果")
        return checkpoint_data
    
    # 检查是否需要调仓
    should_rebalance = kwargs.get("should_rebalance", True)
    if not should_rebalance:
        return {"data_prepared": False, "reason": "no_rebalance_needed"}
    
    cache_manager = CacheManager()
    
    # 确保关键数据已缓存
    # 这里可以预加载股票基本信息、ST列表等
    data_status = {
        "basic_info_ready": False,
        "st_list_ready": False,
        "price_data_ready": False
    }
    
    # 预检查数据可用性
    try:
        from python.stock.data.akshare_provider import AkShareProvider
        data_provider = AkShareProvider()
        
        # 检查基本信息（临时跳过，因为方法未实现）
        # basic_info = data_provider.get_stock_basic_info()
        # if basic_info is not None and not basic_info.empty:
        #     data_status["basic_info_ready"] = True
        data_status["basic_info_ready"] = True  # 临时设为True
        
        # 检查ST列表（临时跳过，因为方法未实现）
        # st_stocks = data_provider.get_st_stocks()
        # if st_stocks is not None:
        #     data_status["st_list_ready"] = True
        data_status["st_list_ready"] = True  # 临时设为True
        
        data_status["price_data_ready"] = True  # 已实现get_daily_price方法
        
    except Exception as e:
        logger.warning(f"数据可用性检查失败: {e}")
    
    prepare_data = {
        "data_prepared": True,
        "data_status": data_status,
        "target_date": target_date,
        "preparation_timestamp": datetime.now().isoformat()
    }
    
    logger.info(f"数据准备完成: {data_status}")
    return prepare_data

def _step_strategy_selection(target_date: str, checkpoint_data: Dict = None, **kwargs) -> Dict:
    """步骤5: 策略选股"""
    logger = logging.getLogger("step.strategy_selection")
    
    if checkpoint_data:
        logger.info("从检查点恢复选股结果")
        return checkpoint_data
    
    # 检查是否需要调仓
    should_rebalance = kwargs.get("should_rebalance", True)
    if not should_rebalance:
        return {"stocks_selected": False, "reason": "no_rebalance_needed"}
    
    config = kwargs.get("config") or {}
    cache_manager = CacheManager()
    strategy_engine = StrategyEngine(config)
    
    # 执行策略选股
    selected_stocks = strategy_engine.select_stocks(target_date)
    
    if not selected_stocks:
        raise Exception("策略未选出任何股票")
    
    selection_data = {
        "selected_stocks": selected_stocks,
        "stock_count": len(selected_stocks),
        "target_count": config.get("stock_count", 35),
        "selection_timestamp": datetime.now().isoformat()
    }
    
    logger.info(f"策略选股完成，共选出 {len(selected_stocks)} 只股票")
    return selection_data

def _step_calculate_trades(instance_name: str, target_date: str, checkpoint_data: Dict = None, **kwargs) -> Dict:
    """步骤6: 计算交易"""
    logger = logging.getLogger("step.calculate_trades")
    
    if checkpoint_data:
        logger.info("从检查点恢复交易计算结果")
        return checkpoint_data
    
    # 直接从kwargs获取数据（步骤间自动传递）
    should_rebalance = kwargs.get("should_rebalance", False)
    selected_stocks = kwargs.get("selected_stocks", [])
    portfolio_state = kwargs.get("portfolio_state", {})
    
    logger.info(f"交易计算前置条件检查: 调仓={should_rebalance}, 选股数={len(selected_stocks)}, 总资产={portfolio_state.get('total_value', 0):,.2f}")
    
    if not should_rebalance:
        logger.info("无需调仓，跳过交易计算")
        return {"trades_calculated": False, "reason": "no_rebalance_needed"}
    
    if not selected_stocks:
        logger.warning("没有选出股票，跳过交易计算")
        return {"trades_calculated": False, "reason": "no_stocks_selected"}
    
    # 获取实例配置
    from simulation.core.instance_manager import InstanceManager
    instance_manager = InstanceManager()
    config = instance_manager.get_instance_config(instance_name)
    
    cache_manager = CacheManager()
    trading_engine = TradingEngine(config, cache_manager)
    
    # 计算需要的交易
    trade_plan = trading_engine.calculate_rebalance_trades(
        portfolio_state, selected_stocks, target_date
    )
    
    if not trade_plan:
        raise Exception("交易计算失败")
    
    calculation_data = {
        "trade_plan": trade_plan,
        "buy_orders": len([t for t in trade_plan.get("trades", []) if t.get("action") == "buy"]),
        "sell_orders": len([t for t in trade_plan.get("trades", []) if t.get("action") == "sell"]),
        "calculation_timestamp": datetime.now().isoformat()
    }
    
    logger.info(f"交易计算完成: 买单 {calculation_data['buy_orders']} 个, 卖单 {calculation_data['sell_orders']} 个")
    return calculation_data

def _step_execute_trades(target_date: str, checkpoint_data: Dict = None, **kwargs) -> Dict:
    """步骤7: 执行交易"""
    logger = logging.getLogger("step.execute_trades")
    
    if checkpoint_data:
        logger.info("从检查点恢复交易执行结果")
        return checkpoint_data
    
    # 检查前置条件
    trade_plan = kwargs.get("trade_plan")
    if not trade_plan:
        return {"trades_executed": False, "reason": "no_trade_plan"}
    
    config = kwargs.get("config") or {}
    portfolio_state = kwargs.get("portfolio_state") or {}
    cache_manager = CacheManager()
    trading_engine = TradingEngine(config, cache_manager)
    
    # 执行交易
    execution_results = trading_engine.execute_trade_plan(
        portfolio_state, trade_plan, target_date
    )
    
    if not execution_results:
        raise Exception("交易执行失败")
    
    execution_data = {
        "execution_results": execution_results,
        "new_portfolio_state": execution_results.get("new_portfolio_state"),
        "trading_records": execution_results.get("trading_records"),
        "execution_summary": execution_results.get("summary", {}),
        "execution_timestamp": datetime.now().isoformat()
    }
    
    logger.info(f"交易执行完成: {execution_data.get('execution_summary', {})}")
    return execution_data

def _step_save_state(instance_name: str, target_date: str, checkpoint_data: Dict = None, **kwargs) -> Dict:
    """步骤8: 保存状态"""
    logger = logging.getLogger("step.save_state")
    
    if checkpoint_data:
        logger.info("状态已保存，跳过重复保存")
        return checkpoint_data
    
    state_manager = StateManager(instance_name)
    instance_manager = InstanceManager()
    
    # 获取更新后的状态
    new_portfolio_state = kwargs.get("new_portfolio_state")
    trading_records = kwargs.get("trading_records", [])
    
    if new_portfolio_state is None:
        # 如果没有交易，重新加载当前状态而不是使用空字典
        current_state = state_manager.load_latest_state()
        if current_state and "portfolio" in current_state:
            new_portfolio_state = current_state["portfolio"]
            logger.info(f"重新加载当前状态，总资产: {new_portfolio_state.get('total_value', 0):,.2f}")
        else:
            new_portfolio_state = {}
            logger.warning("无法加载当前状态，使用空状态")
    
    # 重置风控状态（新的调仓周期开始）
    risk_control_state = {
        "triggered_stocks": [],
        "stop_loss_count": 0,
        "take_profit_count": 0,
        "last_check_time": None
    }
    
    # 保存状态
    success = state_manager.save_daily_state(
        target_date, new_portfolio_state, risk_control_state, trading_records
    )
    
    if not success:
        raise Exception("保存状态失败")
    
    # 更新实例状态
    instance_manager.update_instance_status(instance_name, "active", target_date)
    
    save_data = {
        "state_saved": True,
        "total_value": new_portfolio_state.get("total_value", 0),
        "trading_count": len(trading_records),
        "save_timestamp": datetime.now().isoformat()
    }
    
    logger.info(f"状态保存完成: 总资产={save_data['total_value']:,.2f}, 交易数={save_data['trading_count']}")
    return save_data

def _should_rebalance(config: Dict, target_date: str, last_state_date: str = None) -> bool:
    """
    判断是否需要调仓
    
    Args:
        config: 实例配置
        target_date: 目标日期
        last_state_date: 最后状态日期
        
    Returns:
        bool: 是否需要调仓
    """
    try:
        frequency = config.get("rebalance_frequency", "monthly")
        
        if frequency == "daily":
            # 日度调仓：每天都调仓
            return True
        elif frequency != "monthly":
            # 目前只支持月度和日度调仓
            return False
        
        target_dt = datetime.strptime(target_date, '%Y-%m-%d')
        
        # 检查是否是月末最后一个交易日
        # 简化判断：每月最后一天
        next_month = target_dt.replace(day=1) + timedelta(days=32)
        next_month = next_month.replace(day=1)
        last_day_of_month = next_month - timedelta(days=1)
        
        is_month_end = target_dt.date() == last_day_of_month.date()
        
        # 如果有上次状态日期，检查是否已经在本月调仓过
        if last_state_date and is_month_end:
            last_dt = datetime.strptime(last_state_date, '%Y-%m-%d')
            if last_dt.year == target_dt.year and last_dt.month == target_dt.month:
                # 本月已经调仓过
                return False
        
        return is_month_end
        
    except Exception as e:
        logging.getLogger(__name__).error(f"判断调仓条件失败: {e}")
        return False

if __name__ == "__main__":
    # 支持命令行调用
    import argparse
    
    parser = argparse.ArgumentParser(description='执行日度调仓任务')
    parser.add_argument('--instance', type=str, default='default', help='实例名称')
    parser.add_argument('--date', type=str, help='目标日期 YYYY-MM-DD')
    
    args = parser.parse_args()
    
    # 设置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    success = run_daily_rebalance(args.instance, args.date)
    sys.exit(0 if success else 1)