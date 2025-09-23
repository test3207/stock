#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
缓存管理器
负责市场数据、参考数据的缓存管理
"""

import json
import pickle
import logging
from pathlib import Path
from typing import Any, Optional, Dict
from datetime import datetime, timedelta
import pandas as pd

class CacheManager:
    """缓存管理器"""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent.parent
        self.cache_dir = self.base_dir / "data" / "simulation" / "cache"
        self.market_data_dir = self.cache_dir / "market_data"
        self.reference_data_dir = self.cache_dir / "reference_data"
        self.metadata_dir = self.cache_dir / "metadata"
        
        self.logger = logging.getLogger(__name__)
        self._ensure_directories()
    
    def _ensure_directories(self):
        """确保缓存目录存在"""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.market_data_dir.mkdir(exist_ok=True)
        self.reference_data_dir.mkdir(exist_ok=True)
        self.metadata_dir.mkdir(exist_ok=True)
    
    def cache_market_data(self, key: str, data: Any, ttl_hours: int = 24) -> bool:
        """
        缓存市场数据
        
        Args:
            key: 缓存键
            data: 数据
            ttl_hours: 过期时间（小时）
            
        Returns:
            bool: 是否缓存成功
        """
        try:
            cache_file = self.market_data_dir / f"{key}.pkl"
            metadata_file = self.metadata_dir / f"{key}_market.json"
            
            # 保存数据
            with open(cache_file, 'wb') as f:
                pickle.dump(data, f)
            
            # 保存元数据
            metadata = {
                "key": key,
                "cached_at": datetime.now().isoformat(),
                "expires_at": (datetime.now() + timedelta(hours=ttl_hours)).isoformat(),
                "type": "market_data",
                "size": len(data) if hasattr(data, '__len__') else 0
            }
            
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            self.logger.debug(f"缓存市场数据: {key}")
            return True
            
        except Exception as e:
            self.logger.error(f"缓存市场数据失败 {key}: {e}")
            return False
    
    def get_market_data(self, key: str) -> Optional[Any]:
        """
        获取缓存的市场数据
        
        Args:
            key: 缓存键
            
        Returns:
            缓存的数据或None
        """
        try:
            cache_file = self.market_data_dir / f"{key}.pkl"
            metadata_file = self.metadata_dir / f"{key}_market.json"
            
            if not cache_file.exists() or not metadata_file.exists():
                return None
            
            # 检查是否过期
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            expires_at = datetime.fromisoformat(metadata["expires_at"])
            if datetime.now() > expires_at:
                self.logger.debug(f"缓存已过期: {key}")
                return None
            
            # 加载数据
            with open(cache_file, 'rb') as f:
                data = pickle.load(f)
            
            self.logger.debug(f"命中缓存: {key}")
            return data
            
        except Exception as e:
            self.logger.error(f"获取缓存失败 {key}: {e}")
            return None
    
    def cache_reference_data(self, key: str, data: Any, ttl_hours: int = 168) -> bool:
        """
        缓存参考数据（较长TTL）
        
        Args:
            key: 缓存键
            data: 数据
            ttl_hours: 过期时间（小时），默认一周
            
        Returns:
            bool: 是否缓存成功
        """
        try:
            cache_file = self.reference_data_dir / f"{key}.pkl"
            metadata_file = self.metadata_dir / f"{key}_reference.json"
            
            # 保存数据
            with open(cache_file, 'wb') as f:
                pickle.dump(data, f)
            
            # 保存元数据
            metadata = {
                "key": key,
                "cached_at": datetime.now().isoformat(),
                "expires_at": (datetime.now() + timedelta(hours=ttl_hours)).isoformat(),
                "type": "reference_data",
                "size": len(data) if hasattr(data, '__len__') else 0
            }
            
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            self.logger.debug(f"缓存参考数据: {key}")
            return True
            
        except Exception as e:
            self.logger.error(f"缓存参考数据失败 {key}: {e}")
            return False
    
    def get_reference_data(self, key: str) -> Optional[Any]:
        """获取缓存的参考数据"""
        try:
            cache_file = self.reference_data_dir / f"{key}.pkl"
            metadata_file = self.metadata_dir / f"{key}_reference.json"
            
            if not cache_file.exists() or not metadata_file.exists():
                return None
            
            # 检查是否过期
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            expires_at = datetime.fromisoformat(metadata["expires_at"])
            if datetime.now() > expires_at:
                self.logger.debug(f"参考数据缓存已过期: {key}")
                return None
            
            # 加载数据
            with open(cache_file, 'rb') as f:
                data = pickle.load(f)
            
            self.logger.debug(f"命中参考数据缓存: {key}")
            return data
            
        except Exception as e:
            self.logger.error(f"获取参考数据缓存失败 {key}: {e}")
            return None
    
    def cleanup_expired_cache(self) -> Dict[str, int]:
        """
        清理过期缓存
        
        Returns:
            Dict: 清理统计
        """
        stats = {"market_data": 0, "reference_data": 0}
        
        try:
            # 获取所有元数据文件
            metadata_files = list(self.metadata_dir.glob("*.json"))
            
            for metadata_file in metadata_files:
                try:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    
                    # 检查是否过期
                    expires_at = datetime.fromisoformat(metadata["expires_at"])
                    if datetime.now() > expires_at:
                        key = metadata["key"]
                        data_type = metadata["type"]
                        
                        # 删除缓存文件
                        if data_type == "market_data":
                            cache_file = self.market_data_dir / f"{key}.pkl"
                        else:
                            cache_file = self.reference_data_dir / f"{key}.pkl"
                        
                        if cache_file.exists():
                            cache_file.unlink()
                            stats[data_type] += 1
                        
                        # 删除元数据文件
                        metadata_file.unlink()
                        
                except Exception as e:
                    self.logger.warning(f"清理缓存文件失败 {metadata_file}: {e}")
            
            self.logger.info(f"清理过期缓存完成: {stats}")
            return stats
            
        except Exception as e:
            self.logger.error(f"清理过期缓存失败: {e}")
            return stats
    
    def get_cache_stats(self) -> Dict:
        """获取缓存统计信息"""
        try:
            stats = {
                "market_data_count": len(list(self.market_data_dir.glob("*.pkl"))),
                "reference_data_count": len(list(self.reference_data_dir.glob("*.pkl"))),
                "total_size_mb": 0.0,
                "cache_hit_info": []
            }
            
            # 计算总大小
            for cache_dir in [self.market_data_dir, self.reference_data_dir]:
                for cache_file in cache_dir.glob("*.pkl"):
                    stats["total_size_mb"] += cache_file.stat().st_size / (1024 * 1024)
            
            stats["total_size_mb"] = round(stats["total_size_mb"], 2)
            
            return stats
            
        except Exception as e:
            self.logger.error(f"获取缓存统计失败: {e}")
            return {}
    
    def clear_all_cache(self) -> bool:
        """清除所有缓存"""
        try:
            # 清除市场数据缓存
            for cache_file in self.market_data_dir.glob("*.pkl"):
                cache_file.unlink()
            
            # 清除参考数据缓存
            for cache_file in self.reference_data_dir.glob("*.pkl"):
                cache_file.unlink()
            
            # 清除元数据
            for metadata_file in self.metadata_dir.glob("*.json"):
                metadata_file.unlink()
            
            self.logger.info("已清除所有缓存")
            return True
            
        except Exception as e:
            self.logger.error(f"清除缓存失败: {e}")
            return False