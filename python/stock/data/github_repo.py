#!/usr/bin/env python3
"""
GitHub数据仓库管理器
用于管理GitHub数据仓库，作为akshare的备用数据源
"""

import os
import json
import pandas as pd
from datetime import date, timedelta, datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
import requests
import time

class GitHubDataRepo:
    """GitHub数据仓库管理器"""
    
    def __init__(self, 
                 repo_owner: str = "test3207",
                 repo_name: str = "stock-data",
                 local_cache_dir: str = None):
        
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.base_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}"
        self.raw_base_url = f"https://raw.githubusercontent.com/{repo_owner}/{repo_name}/main"
        
        # 设置缓存目录
        if local_cache_dir is None:
            project_root = Path(__file__).parent.parent.parent
            local_cache_dir = project_root / "data" / "repo_cache"
        
        self.local_cache_dir = Path(local_cache_dir)
        self.local_cache_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"GitHub数据仓库: {repo_owner}/{repo_name}")
        print(f"本地缓存目录: {self.local_cache_dir}")
    
    def check_repo_exists(self) -> bool:
        """检查数据仓库是否存在"""
        try:
            response = requests.get(self.base_url, timeout=10)
            return response.status_code == 200
        except:
            return False
    
    def get_available_dates(self) -> List[str]:
        """获取可用的数据日期列表"""
        try:
            # 从GitHub API获取daily目录内容
            url = f"{self.base_url}/contents/daily"
            response = requests.get(url, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                dates = [item['name'] for item in data if item['type'] == 'dir']
                return sorted(dates)
            else:
                print(f"获取日期列表失败: {response.status_code}")
                return []
        except Exception as e:
            print(f"获取可用日期失败: {e}")
            return []
    
    def download_daily_data(self, target_date: str) -> Optional[pd.DataFrame]:
        """
        下载指定交易日的所有股票数据
        
        Args:
            target_date: 交易日期 (YYYY-MM-DD格式)
            
        返回数据结构 (已验证 2025-09-25):
        DataFrame包含以下列 (与上传格式一致):
        - ts_code: str, 股票代码 (如'000001.SZ')
        - trade_date: str, 交易日期 YYYYMMDD格式 (如'20250925')
        - open/high/low/close: float, OHLC价格
        - vol: float, 成交量(手)
        - amount: float, 成交额(元)
        
        数据来源路径 (修正后): daily_data/{target_date交易日期}/{股票代码}.json
        每个文件包含该股票该交易日的数据(通常1条记录)JSON数组
        
        缓存策略: 本地parquet文件，文件名daily_{target_date}.parquet
        
        Returns:
            pd.DataFrame | None: 合并后的所有股票数据，失败返回None
        """
        try:
            print(f"正在下载 {target_date} 的数据...")
            
            # 检查本地缓存
            cache_file = self.local_cache_dir / f"daily_{target_date}.parquet"
            if cache_file.exists():
                print(f"  从本地缓存加载: {cache_file}")
                return pd.read_parquet(cache_file)
            
            # 从GitHub下载
            url = f"{self.base_url}/contents/daily/{target_date}"
            response = requests.get(url, timeout=15)
            
            if response.status_code != 200:
                print(f"  日期 {target_date} 数据不存在")
                return None
            
            files_info = response.json()
            all_data = []
            
            print(f"  发现 {len(files_info)} 个股票文件")
            
            for file_info in files_info:
                if file_info['name'].endswith('.json'):
                    symbol = file_info['name'].replace('.json', '')
                    
                    # 下载单个股票文件
                    file_url = file_info['download_url']
                    file_response = requests.get(file_url, timeout=10)
                    
                    if file_response.status_code == 200:
                        stock_data = file_response.json()
                        stock_data['symbol'] = symbol
                        all_data.append(stock_data)
                    
                    time.sleep(0.1)  # 避免API限制
            
            if all_data:
                df = pd.DataFrame(all_data)
                df['date'] = target_date
                
                # 保存到本地缓存
                try:
                    df.to_parquet(cache_file, index=False)
                    print(f"  成功下载并缓存 {len(df)} 条记录")
                except Exception as e:
                    print(f"  缓存失败: {e}")
                
                return df
            else:
                print(f"  {target_date} 无有效数据")
                return None
                
        except Exception as e:
            print(f"下载 {target_date} 数据失败: {e}")
            return None
    
    def download_basic_info(self) -> Optional[pd.DataFrame]:
        """
        下载股票基础信息
        
        返回数据结构 (已验证 2025-09-25):
        DataFrame包含以下列 (与AkShareProvider.get_basic_info()格式一致):
        - symbol: str, 股票代码 (如'000001.SZ', '600000.SH')
        - name: str, 股票名称 (如'平安银行')
        - exchange: str, 交易所代码 ('SH'|'SZ')
        - is_st: bool, 是否ST股票
        - market: str, 市场类型 (固定'A')
        - list_date: str|None, 上市日期 (YYYY-MM-DD格式)
        
        数据来源路径: basic_info.json (根目录)
        文件格式: {
          "last_updated": "2025-09-25T10:00:00",
          "record_count": 5434,
          "records": [股票信息对象数组]
        }
        
        缓存策略: 本地parquet文件，文件名basic_info.parquet
        
        Returns:
            pd.DataFrame | None: 基础信息数据，失败返回None
        """
        try:
            print("正在下载基础信息...")
            
            # 检查本地缓存
            cache_file = self.local_cache_dir / "basic_info.parquet"
            
            # 从GitHub下载
            url = f"{self.raw_base_url}/basic_info.json"
            response = requests.get(url, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                # 提取实际的股票数据（跳过元数据）
                if 'data' in data:
                    records = data['data']
                    last_updated = data.get('last_updated', 'unknown')
                    print(f"  GitHub数据更新时间: {last_updated}")
                else:
                    # 兼容旧格式
                    records = data
                
                df = pd.DataFrame(records)
                
                # 保存到本地缓存
                try:
                    df.to_parquet(cache_file, index=False)
                    print(f"  成功下载基础信息 {len(df)} 条记录")
                except Exception as e:
                    print(f"  缓存失败: {e}")
                
                return df
            else:
                print("  GitHub基础信息不可用")
                
                # 尝试从缓存加载
                if cache_file.exists():
                    print(f"  从本地缓存加载: {cache_file}")
                    return pd.read_parquet(cache_file)
                
                return None
                
        except Exception as e:
            print(f"下载基础信息失败: {e}")
            
            # 出错时尝试从缓存恢复
            cache_file = self.local_cache_dir / "basic_info.parquet"
            if cache_file.exists():
                print(f"  从缓存恢复: {cache_file}")
                return pd.read_parquet(cache_file)
            
            return None
    
    def download_date_range(self, start_date: str, end_date: str, 
                          max_requests: int = 50) -> Optional[pd.DataFrame]:
        """下载日期范围内的数据（有请求数限制）"""
        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        all_data = []
        current_date = start
        request_count = 0
        
        print(f"下载日期范围数据: {start_date} 至 {end_date} (最多{max_requests}个请求)")
        
        while current_date <= end and request_count < max_requests:
            # 只尝试工作日
            if current_date.weekday() < 5:  # 0-4是周一到周五
                date_str = current_date.strftime('%Y-%m-%d')
                daily_data = self.download_daily_data(date_str)
                
                if daily_data is not None:
                    all_data.append(daily_data)
                
                request_count += 1
                time.sleep(1)  # 避免过于频繁的API调用
            
            current_date += timedelta(days=1)
        
        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            print(f"合并完成: {len(combined_df)} 条记录")
            return combined_df
        else:
            print("没有获取到任何数据")
            return None