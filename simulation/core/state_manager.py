#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
状态管理器
负责实例状态的持久化、恢复和完整性验证
"""

import json
import hashlib
import logging
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime

# 导入时区感知工具
try:
    import sys
    sys.path.append(str(Path(__file__).parent.parent.parent))
    from python.stock.utils.timezone_helper import get_trading_timestamp, get_trading_date, get_cst_now
except ImportError:
    # 回退实现
    def get_trading_timestamp():
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    def get_trading_date():
        return datetime.now().strftime('%Y-%m-%d')
    def get_cst_now():
        return datetime.now()

class StateManager:
    """状态管理器"""
    
    def __init__(self, instance_name: str):
        self.instance_name = instance_name
        self.base_dir = Path(__file__).parent.parent.parent
        self.instance_dir = self.base_dir / "data" / "simulation" / "instances" / instance_name
        self.state_dir = self.instance_dir / "state"
        self.trades_dir = self.instance_dir / "trades"
        
        self.logger = logging.getLogger(f"{__name__}.{instance_name}")
        
        # 确保目录存在
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.trades_dir.mkdir(parents=True, exist_ok=True)
    
    def save_daily_state(self, date: str, portfolio_state: Dict, 
                        risk_control_state: Dict, trading_records: List = None) -> bool:
        """
        保存每日状态
        
        Args:
            date: 日期 YYYY-MM-DD
            portfolio_state: 投资组合状态
            risk_control_state: 风控状态
            trading_records: 交易记录
            
        Returns:
            bool: 是否保存成功
        """
        try:
            # 准备状态数据
            state_data = {
                "date": date,
                "timestamp": get_trading_timestamp(),
                "instance": self.instance_name,
                "portfolio": portfolio_state,
                "risk_control": risk_control_state,
                "metadata": {
                    "positions_count": len(portfolio_state.get("positions", {})),
                    "total_value": portfolio_state.get("total_value", 0.0),
                    "cash_ratio": portfolio_state.get("cash", 0.0) / max(portfolio_state.get("total_value", 1.0), 1.0)
                }
            }
            
            # 计算校验和
            state_data["checksum"] = self._calculate_checksum(state_data)
            
            # 保存状态文件
            state_file = self.state_dir / f"{date}.json"
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, ensure_ascii=False, indent=2)
            
            # 保存交易记录
            if trading_records:
                trades_data = {
                    "date": date,
                    "instance": self.instance_name,
                    "trades": trading_records,
                    "summary": {
                        "total_trades": len(trading_records),
                        "buy_count": sum(1 for t in trading_records if t.get("action") == "buy"),
                        "sell_count": sum(1 for t in trading_records if t.get("action") == "sell")
                    }
                }
                
                trades_file = self.trades_dir / f"{date}_trades.json"
                with open(trades_file, 'w', encoding='utf-8') as f:
                    json.dump(trades_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"成功保存 {date} 状态")
            return True
            
        except Exception as e:
            self.logger.error(f"保存状态失败 {date}: {e}")
            return False
    
    def load_latest_state(self) -> Optional[Dict]:
        """加载最新状态"""
        try:
            state_files = list(self.state_dir.glob("*.json"))
            if not state_files:
                self.logger.info("没有找到历史状态文件")
                return None
            
            # 按日期排序，取最新的
            state_files.sort(key=lambda x: x.stem)
            latest_file = state_files[-1]
            
            return self.load_state_by_date(latest_file.stem)
            
        except Exception as e:
            self.logger.error(f"加载最新状态失败: {e}")
            return None
    
    def load_state_by_date(self, date: str) -> Optional[Dict]:
        """
        根据日期加载状态
        
        Args:
            date: 日期 YYYY-MM-DD
            
        Returns:
            Dict: 状态数据
        """
        try:
            state_file = self.state_dir / f"{date}.json"
            if not state_file.exists():
                self.logger.warning(f"状态文件不存在: {date}")
                return None
            
            with open(state_file, 'r', encoding='utf-8') as f:
                state_data = json.load(f)
            
            # 验证校验和
            if not self._verify_checksum(state_data):
                self.logger.error(f"状态文件校验失败: {date}")
                return None
            
            self.logger.info(f"成功加载 {date} 状态")
            return state_data
            
        except Exception as e:
            self.logger.error(f"加载状态失败 {date}: {e}")
            return None
    
    def get_available_dates(self) -> List[str]:
        """获取所有可用的状态日期"""
        try:
            state_files = list(self.state_dir.glob("*.json"))
            dates = [f.stem for f in state_files]
            return sorted(dates)
        except Exception as e:
            self.logger.error(f"获取可用日期失败: {e}")
            return []
    
    def cleanup_old_states(self, keep_days: int = 30) -> int:
        """
        清理旧的状态文件
        
        Args:
            keep_days: 保留天数
            
        Returns:
            int: 清理的文件数量
        """
        try:
            dates = self.get_available_dates()
            if len(dates) <= keep_days:
                return 0
            
            # 保留最新的N天
            dates_to_remove = dates[:-keep_days]
            removed_count = 0
            
            for date in dates_to_remove:
                state_file = self.state_dir / f"{date}.json"
                trades_file = self.trades_dir / f"{date}_trades.json"
                
                if state_file.exists():
                    state_file.unlink()
                    removed_count += 1
                
                if trades_file.exists():
                    trades_file.unlink()
            
            self.logger.info(f"清理了 {removed_count} 个旧状态文件")
            return removed_count
            
        except Exception as e:
            self.logger.error(f"清理旧状态失败: {e}")
            return 0
    
    def _calculate_checksum(self, data: Dict) -> str:
        """计算数据校验和"""
        # 移除checksum字段（如果存在）
        data_copy = data.copy()
        data_copy.pop("checksum", None)
        data_copy.pop("timestamp", None)  # 时间戳不参与校验
        
        # 转换为JSON字符串并计算MD5
        json_str = json.dumps(data_copy, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(json_str.encode('utf-8')).hexdigest()
    
    def _verify_checksum(self, data: Dict) -> bool:
        """验证数据校验和"""
        if "checksum" not in data:
            return True  # 没有校验和的文件视为有效（向后兼容）
        
        expected_checksum = data["checksum"]
        calculated_checksum = self._calculate_checksum(data)
        
        return expected_checksum == calculated_checksum
    
    def create_initial_state(self, initial_capital: float) -> bool:
        """创建初始状态"""
        try:
            today = get_trading_date()
            
            portfolio_state = {
                "cash": initial_capital,
                "idle_cash": 0.0,
                "positions": {},
                "market_value": 0.0,
                "total_value": initial_capital
            }
            
            risk_control_state = {
                "triggered_stocks": [],
                "stop_loss_count": 0,
                "take_profit_count": 0,
                "last_check_time": None
            }
            
            return self.save_daily_state(today, portfolio_state, risk_control_state)
            
        except Exception as e:
            self.logger.error(f"创建初始状态失败: {e}")
            return False