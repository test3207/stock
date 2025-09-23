#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实时数据模拟交易系统
A股量化交易系统 - 实时数据模拟层

核心功能：
1. 状态持久化与恢复机制
2. cronjob兼容的单日执行模块
3. 实时风控监控与交易执行
4. 断点恢复与跨机器迁移支持

设计原则：可中断、可恢复、完整状态保存
"""

import json
import os
import logging
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import time
import sys

# 添加项目路径以导入核心模块
sys.path.append(str(Path(__file__).parent / "python"))
from stock.data.akshare_provider import AkshareDataProvider
from stock.strategies.drawdown_reversal import DrawdownReversalStrategy
from stock.engine.metrics import PerformanceMetrics

class RealtimeSimulationSystem:
    """实时数据模拟交易系统"""
    
    def __init__(self, config_path: str = None):
        """
        初始化实时模拟系统
        
        Args:
            config_path: 配置文件路径，默认为 data/simulation/system_config.json
        """
        # 路径设置
        self.base_dir = Path(__file__).parent
        self.simulation_dir = self.base_dir / "data" / "simulation"
        self.portfolio_dir = self.simulation_dir / "portfolio_state"
        self.trading_dir = self.simulation_dir / "trading_records"
        
        # 确保目录存在
        self._ensure_directories()
        
        # 配置文件路径
        self.config_path = config_path or str(self.simulation_dir / "system_config.json")
        
        # 初始化组件
        self.data_provider = AkshareDataProvider()
        self.strategy = DrawdownReversalStrategy()
        self.metrics = PerformanceMetrics()
        
        # 系统状态
        self.portfolio_state = {}
        self.risk_control_state = {}
        self.system_config = {}
        
        # 设置日志
        self._setup_logging()
        
        # 加载系统配置
        self._load_system_config()
        
        self.logger.info("实时模拟系统初始化完成")
    
    def _ensure_directories(self):
        """确保所有必要目录存在"""
        self.simulation_dir.mkdir(parents=True, exist_ok=True)
        self.portfolio_dir.mkdir(parents=True, exist_ok=True)
        self.trading_dir.mkdir(parents=True, exist_ok=True)
    
    def _setup_logging(self):
        """设置日志记录"""
        log_dir = self.simulation_dir / "logs"
        log_dir.mkdir(exist_ok=True)
        
        log_file = log_dir / f"simulation_{datetime.now().strftime('%Y%m%d')}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def _load_system_config(self):
        """加载系统配置"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.system_config = json.load(f)
                self.logger.info(f"已加载系统配置: {self.config_path}")
            except Exception as e:
                self.logger.warning(f"加载配置文件失败: {e}, 使用默认配置")
                self._create_default_config()
        else:
            self.logger.info("配置文件不存在，创建默认配置")
            self._create_default_config()
    
    def _create_default_config(self):
        """创建默认系统配置"""
        self.system_config = {
            "initial_capital": 1000000.0,  # 初始资金100万
            "stock_count": 35,  # 股票数量
            "rebalance_frequency": "monthly",  # 月度调仓
            "risk_control": {
                "stop_loss_threshold": -0.15,  # 止损-15%
                "take_profit_threshold": 0.20,  # 止盈+20%
                "max_position_pct": 0.05,  # 最大单股持仓5%
                "check_interval_minutes": 5  # 风控检查间隔5分钟
            },
            "trading_costs": {
                "commission_rate": 0.0001,  # 佣金万1
                "stamp_tax_rate": 0.001,    # 印花税千1（仅卖出）
                "slippage_bps": 8           # 滑点8bp
            },
            "data_source": {
                "provider": "akshare",
                "cache_enabled": True,
                "realtime_update": True
            },
            "last_run_date": None,
            "next_rebalance_date": None,
            "system_status": "initialized"
        }
        self._save_system_config()
    
    def _save_system_config(self):
        """保存系统配置"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.system_config, f, ensure_ascii=False, indent=2)
            self.logger.info("系统配置已保存")
        except Exception as e:
            self.logger.error(f"保存系统配置失败: {e}")
    
    def load_portfolio_state(self, date: str = None) -> bool:
        """
        加载投资组合状态
        
        Args:
            date: 指定日期，默认为最新日期
            
        Returns:
            bool: 是否成功加载
        """
        try:
            if date is None:
                # 查找最新的状态文件
                state_files = list(self.portfolio_dir.glob("*.json"))
                if not state_files:
                    self.logger.info("没有找到历史状态文件，将从初始状态开始")
                    self._initialize_portfolio()
                    return True
                
                # 按日期排序，取最新的
                state_files.sort(key=lambda x: x.stem)
                latest_file = state_files[-1]
                date = latest_file.stem
            else:
                latest_file = self.portfolio_dir / f"{date}.json"
                if not latest_file.exists():
                    self.logger.warning(f"指定日期的状态文件不存在: {date}")
                    return False
            
            with open(latest_file, 'r', encoding='utf-8') as f:
                state_data = json.load(f)
            
            self.portfolio_state = state_data.get('portfolio', {})
            self.risk_control_state = state_data.get('risk_control', {})
            
            self.logger.info(f"成功加载 {date} 的投资组合状态")
            self.logger.info(f"总资产: {self.portfolio_state.get('total_value', 0):,.2f}")
            self.logger.info(f"持仓数量: {len(self.portfolio_state.get('positions', {}))}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"加载投资组合状态失败: {e}")
            return False
    
    def _initialize_portfolio(self):
        """初始化投资组合"""
        self.portfolio_state = {
            "cash": self.system_config["initial_capital"],
            "idle_cash": 0.0,
            "positions": {},
            "market_value": 0.0,
            "total_value": self.system_config["initial_capital"]
        }
        
        self.risk_control_state = {
            "triggered_stocks": [],
            "stop_loss_count": 0,
            "take_profit_count": 0,
            "last_risk_check": None
        }
        
        self.logger.info("投资组合已初始化")
    
    def save_portfolio_state(self, date: str):
        """
        保存投资组合状态
        
        Args:
            date: 保存日期
        """
        try:
            state_data = {
                "date": date,
                "portfolio": self.portfolio_state,
                "risk_control": self.risk_control_state,
                "next_rebalance_date": self.system_config.get("next_rebalance_date"),
                "timestamp": datetime.now().isoformat()
            }
            
            state_file = self.portfolio_dir / f"{date}.json"
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"投资组合状态已保存: {date}")
            
        except Exception as e:
            self.logger.error(f"保存投资组合状态失败: {e}")
    
    def save_trading_record(self, date: str, trades: List[Dict]):
        """
        保存交易记录
        
        Args:
            date: 交易日期
            trades: 交易记录列表
        """
        try:
            if not trades:
                return
            
            trading_data = {
                "date": date,
                "trades": trades,
                "portfolio_summary": {
                    "total_value": self.portfolio_state.get("total_value", 0),
                    "cash": self.portfolio_state.get("cash", 0),
                    "market_value": self.portfolio_state.get("market_value", 0),
                    "position_count": len(self.portfolio_state.get("positions", {}))
                },
                "timestamp": datetime.now().isoformat()
            }
            
            trading_file = self.trading_dir / f"{date}_trades.json"
            with open(trading_file, 'w', encoding='utf-8') as f:
                json.dump(trading_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"交易记录已保存: {date}, 交易笔数: {len(trades)}")
            
        except Exception as e:
            self.logger.error(f"保存交易记录失败: {e}")
    
    def get_trading_dates(self) -> pd.DatetimeIndex:
        """获取交易日历"""
        try:
            # 获取最近一年的交易日历
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365)
            
            # 使用akshare获取交易日历
            trading_calendar = self.data_provider.get_trading_calendar(
                start_date.strftime('%Y%m%d'),
                end_date.strftime('%Y%m%d')
            )
            
            return pd.to_datetime(trading_calendar)
            
        except Exception as e:
            self.logger.error(f"获取交易日历失败: {e}")
            # 返回简单的工作日日历作为备选
            return pd.bdate_range(start=datetime.now() - timedelta(days=365), 
                                 end=datetime.now(), freq='B')
    
    def is_trading_day(self, date: datetime = None) -> bool:
        """
        检查是否为交易日
        
        Args:
            date: 检查日期，默认为今天
            
        Returns:
            bool: 是否为交易日
        """
        if date is None:
            date = datetime.now()
        
        try:
            trading_dates = self.get_trading_dates()
            date_str = date.strftime('%Y-%m-%d')
            return pd.Timestamp(date_str) in trading_dates
        except Exception as e:
            self.logger.error(f"检查交易日失败: {e}")
            # 简单检查：非周末
            return date.weekday() < 5
    
    def is_market_open(self) -> bool:
        """
        检查市场是否开盘
        
        Returns:
            bool: 市场是否开盘
        """
        now = datetime.now()
        
        # 检查是否为交易日
        if not self.is_trading_day(now):
            return False
        
        # 检查时间（简化版本：9:30-11:30, 13:00-15:00）
        current_time = now.time()
        morning_start = datetime.strptime("09:30", "%H:%M").time()
        morning_end = datetime.strptime("11:30", "%H:%M").time()
        afternoon_start = datetime.strptime("13:00", "%H:%M").time()
        afternoon_end = datetime.strptime("15:00", "%H:%M").time()
        
        return ((morning_start <= current_time <= morning_end) or 
                (afternoon_start <= current_time <= afternoon_end))


if __name__ == "__main__":
    # 测试代码
    print("实时模拟系统初始化测试...")
    
    system = RealtimeSimulationSystem()
    
    # 测试加载状态
    system.load_portfolio_state()
    
    # 测试保存状态
    test_date = datetime.now().strftime('%Y-%m-%d')
    system.save_portfolio_state(test_date)
    
    # 测试交易日检查
    print(f"今天是否为交易日: {system.is_trading_day()}")
    print(f"市场是否开盘: {system.is_market_open()}")
    
    print("实时模拟系统测试完成！")