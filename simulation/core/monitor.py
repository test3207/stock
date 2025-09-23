#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统监控器
负责系统健康状态监控和异常检测
"""

import json
import logging
import psutil
from pathlib import Path
from typing import Dict, List
from datetime import datetime, timedelta

class SystemMonitor:
    """系统监控器"""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent.parent
        self.simulation_dir = self.base_dir / "data" / "simulation"
        self.instances_dir = self.simulation_dir / "instances"
        
        self.logger = logging.getLogger(__name__)
    
    def check_system_health(self) -> Dict:
        """检查系统健康状态"""
        health_status = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "healthy",
            "checks": {}
        }
        
        try:
            # 检查磁盘空间
            disk_check = self._check_disk_space()
            health_status["checks"]["disk_space"] = disk_check
            
            # 检查内存使用
            memory_check = self._check_memory_usage()
            health_status["checks"]["memory"] = memory_check
            
            # 检查实例状态
            instances_check = self._check_instances_status()
            health_status["checks"]["instances"] = instances_check
            
            # 检查数据文件完整性
            data_check = self._check_data_integrity()
            health_status["checks"]["data_integrity"] = data_check
            
            # 检查缓存状态
            cache_check = self._check_cache_status()
            health_status["checks"]["cache"] = cache_check
            
            # 综合评估
            failed_checks = [name for name, check in health_status["checks"].items() 
                           if check["status"] != "ok"]
            
            if failed_checks:
                health_status["overall_status"] = "warning" if len(failed_checks) <= 2 else "critical"
                health_status["failed_checks"] = failed_checks
            
        except Exception as e:
            health_status["overall_status"] = "error"
            health_status["error"] = str(e)
            self.logger.error(f"系统健康检查失败: {e}")
        
        return health_status
    
    def _check_disk_space(self) -> Dict:
        """检查磁盘空间"""
        try:
            disk_usage = psutil.disk_usage(str(self.simulation_dir))
            free_gb = disk_usage.free / (1024**3)
            total_gb = disk_usage.total / (1024**3)
            used_pct = (disk_usage.used / disk_usage.total) * 100
            
            status = "ok"
            if free_gb < 1.0:  # 小于1GB
                status = "critical"
            elif free_gb < 5.0:  # 小于5GB
                status = "warning"
            
            return {
                "status": status,
                "free_gb": round(free_gb, 2),
                "total_gb": round(total_gb, 2),
                "used_pct": round(used_pct, 1),
                "message": f"可用空间: {free_gb:.2f}GB"
            }
            
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def _check_memory_usage(self) -> Dict:
        """检查内存使用"""
        try:
            memory = psutil.virtual_memory()
            used_pct = memory.percent
            available_gb = memory.available / (1024**3)
            
            status = "ok"
            if used_pct > 90:
                status = "critical"
            elif used_pct > 80:
                status = "warning"
            
            return {
                "status": status,
                "used_pct": round(used_pct, 1),
                "available_gb": round(available_gb, 2),
                "message": f"内存使用率: {used_pct:.1f}%"
            }
            
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def _check_instances_status(self) -> Dict:
        """检查实例状态"""
        try:
            instances = []
            issues = []
            
            if not self.instances_dir.exists():
                return {
                    "status": "warning", 
                    "message": "实例目录不存在",
                    "instances": []
                }
            
            for instance_dir in self.instances_dir.iterdir():
                if instance_dir.is_dir():
                    instance_name = instance_dir.name
                    instance_status = self._check_single_instance(instance_name)
                    instances.append(instance_status)
                    
                    if instance_status["status"] != "ok":
                        issues.append(f"{instance_name}: {instance_status.get('message', '未知错误')}")
            
            overall_status = "ok"
            if issues:
                overall_status = "warning" if len(issues) <= len(instances) // 2 else "critical"
            
            return {
                "status": overall_status,
                "instances_count": len(instances),
                "healthy_count": len([i for i in instances if i["status"] == "ok"]),
                "instances": instances,
                "issues": issues
            }
            
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def _check_single_instance(self, instance_name: str) -> Dict:
        """检查单个实例状态"""
        try:
            instance_dir = self.instances_dir / instance_name
            
            # 检查配置文件
            config_file = instance_dir / "config.json"
            if not config_file.exists():
                return {"status": "error", "message": "配置文件缺失"}
            
            # 检查状态文件
            state_dir = instance_dir / "state"
            state_files = list(state_dir.glob("*.json")) if state_dir.exists() else []
            
            if not state_files:
                return {"status": "warning", "message": "没有状态文件"}
            
            # 检查最近的状态文件
            latest_state = max(state_files, key=lambda x: x.stem)
            days_old = (datetime.now() - datetime.strptime(latest_state.stem, "%Y-%m-%d")).days
            
            if days_old > 7:
                return {"status": "warning", "message": f"状态文件过旧({days_old}天)"}
            
            return {
                "status": "ok",
                "state_files_count": len(state_files),
                "latest_state_date": latest_state.stem,
                "days_since_update": days_old
            }
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def _check_data_integrity(self) -> Dict:
        """检查数据完整性"""
        try:
            # 检查关键数据文件
            data_dir = self.base_dir / "data"
            issues = []
            
            # 检查历史数据
            clean_dir = data_dir / "clean"
            if not clean_dir.exists():
                issues.append("清洗数据目录不存在")
            else:
                required_files = ["price_history_5year.parquet", "basic_info_5year.parquet"]
                for file_name in required_files:
                    file_path = clean_dir / file_name
                    if not file_path.exists():
                        issues.append(f"缺失关键数据文件: {file_name}")
            
            status = "ok" if not issues else "warning"
            
            return {
                "status": status,
                "issues": issues,
                "message": f"发现 {len(issues)} 个数据问题" if issues else "数据完整"
            }
            
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def _check_cache_status(self) -> Dict:
        """检查缓存状态"""
        try:
            cache_dir = self.simulation_dir / "cache"
            
            if not cache_dir.exists():
                return {"status": "ok", "message": "缓存目录不存在（正常）"}
            
            # 统计缓存文件
            market_data_count = len(list((cache_dir / "market_data").glob("*.pkl"))) if (cache_dir / "market_data").exists() else 0
            reference_data_count = len(list((cache_dir / "reference_data").glob("*.pkl"))) if (cache_dir / "reference_data").exists() else 0
            
            # 计算缓存大小
            total_size = 0
            for cache_subdir in cache_dir.iterdir():
                if cache_subdir.is_dir():
                    for file in cache_subdir.glob("*"):
                        if file.is_file():
                            total_size += file.stat().st_size
            
            size_mb = total_size / (1024**2)
            
            status = "ok"
            if size_mb > 1000:  # 大于1GB
                status = "warning"
            
            return {
                "status": status,
                "market_data_files": market_data_count,
                "reference_data_files": reference_data_count,
                "total_size_mb": round(size_mb, 2),
                "message": f"缓存大小: {size_mb:.2f}MB"
            }
            
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def show_system_status(self):
        """显示系统状态"""
        health = self.check_system_health()
        
        print(f"\n=== 系统健康状态 ({health['timestamp'][:19]}) ===")
        print(f"总体状态: {health['overall_status'].upper()}")
        
        if health['overall_status'] != 'healthy':
            failed_checks = health.get('failed_checks', [])
            if failed_checks:
                print(f"问题检查项: {', '.join(failed_checks)}")
        
        print("\n--- 详细检查结果 ---")
        for check_name, check_result in health['checks'].items():
            status = check_result['status']
            message = check_result.get('message', '')
            
            status_icon = {"ok": "✓", "warning": "⚠", "error": "✗", "critical": "✗"}
            icon = status_icon.get(status, "?")
            
            print(f"{icon} {check_name}: {status.upper()} - {message}")
            
            # 显示额外信息
            if check_name == "instances" and "instances" in check_result:
                for instance in check_result["instances"]:
                    inst_status = instance["status"]
                    inst_icon = status_icon.get(inst_status, "?")
                    inst_message = instance.get("message", "")
                    print(f"    {inst_icon} 实例状态: {inst_status.upper()} - {inst_message}")
    
    def generate_health_report(self) -> str:
        """生成健康报告"""
        health = self.check_system_health()
        
        report = f"""
# 系统健康报告

**生成时间**: {health['timestamp'][:19]}
**总体状态**: {health['overall_status'].upper()}

## 检查结果

"""
        
        for check_name, check_result in health['checks'].items():
            status = check_result['status']
            message = check_result.get('message', '')
            
            report += f"### {check_name}\n"
            report += f"- **状态**: {status.upper()}\n"
            report += f"- **信息**: {message}\n\n"
        
        return report