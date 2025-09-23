#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实例管理器
负责管理多个模拟交易实例的生命周期
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

class InstanceManager:
    """实例管理器"""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent.parent
        self.simulation_dir = self.base_dir / "data" / "simulation"
        self.instances_dir = self.simulation_dir / "instances"
        self.global_config_path = self.simulation_dir / "global_config.json"
        
        self.logger = logging.getLogger(__name__)
        self._ensure_directories()
        self._load_global_config()
    
    def _ensure_directories(self):
        """确保目录存在"""
        self.simulation_dir.mkdir(parents=True, exist_ok=True)
        self.instances_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_global_config(self):
        """加载全局配置"""
        if self.global_config_path.exists():
            try:
                with open(self.global_config_path, 'r', encoding='utf-8') as f:
                    self.global_config = json.load(f)
            except Exception as e:
                self.logger.warning(f"加载全局配置失败: {e}")
                self._create_default_global_config()
        else:
            self._create_default_global_config()
    
    def _create_default_global_config(self):
        """创建默认全局配置"""
        self.global_config = {
            "version": "1.0.0",
            "created_at": datetime.now().isoformat(),
            "default_instance": "default",
            "instances": {},
            "cache_settings": {
                "market_data_ttl_hours": 24,
                "reference_data_ttl_hours": 168,  # 一周
                "cleanup_after_days": 30
            }
        }
        self._save_global_config()
    
    def _save_global_config(self):
        """保存全局配置"""
        try:
            with open(self.global_config_path, 'w', encoding='utf-8') as f:
                json.dump(self.global_config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"保存全局配置失败: {e}")
    
    def list_instances(self) -> List[str]:
        """列出所有实例"""
        instances = []
        for item in self.instances_dir.iterdir():
            if item.is_dir():
                instances.append(item.name)
        return sorted(instances)
    
    def create_instance(self, name: str, config: Dict = None) -> bool:
        """
        创建新实例
        
        Args:
            name: 实例名称
            config: 实例配置
            
        Returns:
            bool: 是否创建成功
        """
        try:
            instance_dir = self.instances_dir / name
            
            if instance_dir.exists():
                self.logger.warning(f"实例已存在: {name}")
                return False
            
            # 创建实例目录结构
            instance_dir.mkdir()
            (instance_dir / "state").mkdir()
            (instance_dir / "trades").mkdir()
            (instance_dir / "logs").mkdir()
            (instance_dir / "performance").mkdir()
            
            # 创建实例配置
            instance_config = config or self._get_default_instance_config()
            instance_config["name"] = name
            instance_config["created_at"] = datetime.now().isoformat()
            
            config_path = instance_dir / "config.json"
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(instance_config, f, ensure_ascii=False, indent=2)
            
            # 更新全局配置
            self.global_config["instances"][name] = {
                "created_at": instance_config["created_at"],
                "status": "active",
                "last_run": None
            }
            self._save_global_config()
            
            self.logger.info(f"成功创建实例: {name}")
            return True
            
        except Exception as e:
            self.logger.error(f"创建实例失败 {name}: {e}")
            return False
    
    def _get_default_instance_config(self) -> Dict:
        """获取默认实例配置"""
        return {
            "initial_capital": 1000000.0,
            "stock_count": 35,
            "rebalance_frequency": "monthly",
            "risk_control": {
                "stop_loss_threshold": -0.15,
                "take_profit_threshold": 0.20,
                "max_position_pct": 0.05,
                "check_interval_minutes": 5
            },
            "trading_costs": {
                "commission_rate": 0.0001,
                "stamp_tax_rate": 0.001,
                "slippage_bps": 8
            },
            "strategy": {
                "name": "drawdown_reversal",
                "lookback_months": 6,
                "drawdown_threshold": 0.20,
                "min_listing_years": 5
            },
            "data_source": {
                "provider": "akshare",
                "cache_enabled": True,
                "realtime_update": True
            }
        }
    
    def get_instance_config(self, name: str) -> Optional[Dict]:
        """获取实例配置"""
        try:
            config_path = self.instances_dir / name / "config.json"
            if not config_path.exists():
                return None
            
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"读取实例配置失败 {name}: {e}")
            return None
    
    def update_instance_status(self, name: str, status: str, last_run: str = None):
        """更新实例状态"""
        try:
            # 确保instances键存在
            if "instances" not in self.global_config:
                self.global_config["instances"] = {}
            
            # 确保实例记录存在
            if name not in self.global_config["instances"]:
                self.global_config["instances"][name] = {
                    "created_at": datetime.now().isoformat(),
                    "status": "unknown"
                }
            
            # 更新状态
            self.global_config["instances"][name]["status"] = status
            if last_run:
                self.global_config["instances"][name]["last_run"] = last_run
                
            self._save_global_config()
            self.logger.debug(f"实例状态已更新: {name} -> {status}")
            
        except Exception as e:
            self.logger.error(f"更新实例状态失败: {e}")
            # 不抛出异常，避免影响主流程
    
    def show_instances_status(self):
        """显示所有实例状态"""
        instances = self.list_instances()
        
        if not instances:
            print("没有找到任何实例")
            return
        
        print(f"\n{'实例名称':<15} {'状态':<10} {'最后运行':<20} {'创建时间':<20}")
        print("-" * 70)
        
        for name in instances:
            info = self.global_config["instances"].get(name, {})
            status = info.get("status", "unknown")
            last_run = info.get("last_run", "从未运行")
            created_at = info.get("created_at", "未知")
            
            if isinstance(created_at, str) and len(created_at) > 19:
                created_at = created_at[:19]
            if isinstance(last_run, str) and len(last_run) > 19:
                last_run = last_run[:19]
            
            print(f"{name:<15} {status:<10} {last_run:<20} {created_at:<20}")