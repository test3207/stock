#!/usr/bin/env python3
"""
数据上传器 - 将本地数据上传到GitHub数据仓库
"""

import os
import json
import pandas as pd
import requests
import base64
from datetime import date, datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from ..config import get_github_token

class DataUploader:
    """数据上传到GitHub仓库"""
    
    def __init__(self, 
                 repo_owner: str = "test3207",
                 repo_name: str = "stock-data",
                 github_token: Optional[str] = None):
        
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.base_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}"
        
        # 获取GitHub Token：优先使用参数，然后使用配置系统
        self.github_token = github_token or get_github_token()
        if not self.github_token:
            print("警告: 未设置 GITHUB_TOKEN，只能读取公开数据")
        
        self.headers = {
            'Authorization': f'token {self.github_token}' if self.github_token else None,
            'Accept': 'application/vnd.github.v3+json'
        }
        
        print(f"数据上传器初始化: {repo_owner}/{repo_name}")
    
    def create_or_update_file(self, file_path: str, content: str, 
                            commit_message: str = None, skip_if_exists: bool = False) -> bool:
        """
        创建或更新GitHub仓库中的文件
        
        Args:
            file_path: 文件路径
            content: 文件内容
            commit_message: 提交信息
            skip_if_exists: 如果文件已存在则跳过上传
            
        Returns:
            bool: 成功/失败/跳过
        """
        if not self.github_token:
            print("错误: 需要 GITHUB_TOKEN 才能上传文件")
            return False
        
        try:
            if commit_message is None:
                commit_message = f"Update {file_path} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            # 检查文件是否已存在
            get_url = f"{self.base_url}/contents/{file_path}"
            get_response = requests.get(get_url, headers=self.headers)
            
            # 如果设置了跳过已存在文件，且文件存在，则跳过
            if skip_if_exists and get_response.status_code == 200:
                # print(f"跳过已存在文件: {file_path}")  # 减少日志输出
                return "skipped"  # 返回特殊值表示跳过
            
            # 准备PUT请求数据
            put_data = {
                "message": commit_message,
                "content": base64.b64encode(content.encode('utf-8')).decode('utf-8')
            }
            
            # 如果文件存在，需要提供SHA
            if get_response.status_code == 200:
                existing_file = get_response.json()
                put_data["sha"] = existing_file["sha"]
                print(f"更新现有文件: {file_path}")
            else:
                print(f"创建新文件: {file_path}")
            
            # 上传文件
            put_url = f"{self.base_url}/contents/{file_path}"
            put_response = requests.put(put_url, json=put_data, headers=self.headers)
            
            if put_response.status_code in [200, 201]:
                print(f"上传成功: {file_path}")
                return True
            else:
                print(f"上传失败: {put_response.status_code} - {put_response.text}")
                return False
                
        except Exception as e:
            print(f"上传文件 {file_path} 失败: {e}")
            return False
    
    def upload_daily_data(self, df: pd.DataFrame, target_date: str, skip_existing: bool = True) -> bool:
        """
        上传日K线数据到GitHub仓库
        
        Args:
            df: 日K线数据DataFrame
            target_date: 目标日期标识 (YYYY-MM-DD格式, 仅用于日志显示)
            skip_existing: 是否跳过已存在的数据文件
            
        输入数据结构要求 (已验证兼容):
        DataFrame包含以下列之一作为股票代码:
        - ts_code: str (akshare格式, 如'000001.SZ') 
        - symbol: str (通用格式, 如'000001.SZ')
        
        其他必需列 (来自akshare):
        - trade_date: str, 交易日期 YYYYMMDD格式 (如'20250925')
        - open/high/low/close: float, OHLC价格
        - vol: float, 成交量(手) 
        - amount: float, 成交额(元)
        
        输出文件结构 (修正后):
        - 路径: daily_data/{交易日期YYYY-MM-DD}/{股票代码}.json
        - 格式: JSON数组，包含该股票该交易日的数据(通常只有1条记录)
        - 示例: [{"ts_code":"000001.SZ","trade_date":"20250925","open":11.50,...}]
        - 说明: 历史数据按实际交易日期存储，默认跳过已存在文件
        
        返回: bool 上传成功/失败
        """
        if df is None or df.empty:
            print(f"没有数据可上传 ({target_date})")
            return False
        
        print(f"上传 {target_date} 数据，共 {len(df)} 条记录...")
        
        success_count = 0
        skip_count = 0
        
        # 检查symbol列名（兼容ts_code和symbol）
        symbol_col = 'symbol' if 'symbol' in df.columns else 'ts_code'
        
        if symbol_col not in df.columns:
            print(f"错误：数据中没有找到股票代码列。可用列：{list(df.columns)}")
            return False
        
        # 按股票代码分组，然后按交易日期分别上传
        for symbol in df[symbol_col].unique():
            stock_data = df[df[symbol_col] == symbol]
            
            # 按交易日期分组 - 每个交易日单独存储
            for trade_date in stock_data['trade_date'].unique():
                daily_data = stock_data[stock_data['trade_date'] == trade_date]
                
                if len(daily_data) == 0:
                    continue
                
                # 转换trade_date格式：YYYYMMDD -> YYYY-MM-DD
                if len(str(trade_date)) == 8:
                    formatted_date = f"{str(trade_date)[:4]}-{str(trade_date)[4:6]}-{str(trade_date)[6:8]}"
                else:
                    formatted_date = str(trade_date)
                
                # 清理单日数据
                daily_records = []
                for _, row in daily_data.iterrows():
                    clean_record = {}
                    for k, v in row.items():
                        if pd.notna(v):
                            if isinstance(v, (pd.Timestamp, datetime)):
                                clean_record[k] = v.strftime('%Y-%m-%d')
                            elif isinstance(v, (int, float)) and not pd.isna(v):
                                clean_record[k] = float(v)
                            else:
                                clean_record[k] = str(v)
                    daily_records.append(clean_record)
                
                # 按交易日期存储：daily_data/{交易日期}/{股票代码}.json
                file_path = f"daily_data/{formatted_date}/{symbol}.json"
                content = json.dumps(daily_records, ensure_ascii=False, indent=2)
                
                result = self.create_or_update_file(file_path, content, skip_if_exists=skip_existing)
                if result == "skipped":
                    skip_count += 1
                elif result:
                    success_count += 1
                    print(f"上传成功: {file_path}")
                    
                    # 避免API频率限制，但跳过文件时不需要延迟
                    import time
                    time.sleep(0.05)  # 减少延迟，因为跳过文件不消耗API
        
        # 统计信息：成功上传的文件数 (每个股票每个交易日一个文件)
        total_records = len(df)
        unique_combinations = len(df.groupby([symbol_col, 'trade_date']))
        print(f"上传完成: 新增{success_count}个, 跳过{skip_count}个, 总计{unique_combinations}个文件 (数据记录{total_records}条)")
        return success_count > 0 or skip_count > 0  # 有跳过文件也算成功
    
    def upload_basic_info(self, df: pd.DataFrame) -> bool:
        """
        上传股票基础信息到GitHub仓库
        
        输入数据结构要求 (已验证 AkShareProvider.get_basic_info() 2025-09-25):
        DataFrame包含以下列:
        - symbol: str, 股票代码 (如'000001.SZ', '600000.SH')
        - name: str, 股票名称 (如'平安银行')
        - exchange: str, 交易所代码 ('SH'|'SZ') 
        - is_st: bool, 是否ST股票
        - market: str, 市场类型 (固定'A')
        - list_date: str|None, 上市日期 (YYYY-MM-DD格式)
        
        输出文件结构:
        - 路径: basic_info.json (根目录)
        - 格式: JSON对象包含metadata和records
        - 示例: {
            "last_updated": "2025-09-25T10:00:00", 
            "record_count": 5434,
            "records": [{"symbol":"000001.SZ","name":"平安银行",...}, ...]
          }
        
        返回: bool 上传成功/失败
        """
        if df is None or df.empty:
            print("没有基础信息可上传")
            return False
        
        print(f"上传基础信息，共 {len(df)} 条记录...")
        
        # 清理数据
        clean_records = []
        for _, row in df.iterrows():
            clean_record = {}
            for k, v in row.items():
                if pd.notna(v):
                    if isinstance(v, (pd.Timestamp, datetime)):
                        clean_record[k] = v.strftime('%Y-%m-%d')
                    elif isinstance(v, (int, float)) and not pd.isna(v):
                        clean_record[k] = float(v)
                    else:
                        clean_record[k] = str(v)
            clean_records.append(clean_record)
        
        # 添加更新时间戳
        metadata = {
            "last_updated": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "record_count": len(clean_records),
            "data": clean_records
        }
        
        # 上传统一的基础信息文件
        file_path = "basic_info.json"
        content = json.dumps(metadata, ensure_ascii=False, indent=2)
        
        success = self.create_or_update_file(
            file_path, 
            content, 
            f"Update stock basic info: {len(clean_records)} records"
        )
        
        if success:
            print(f"基础信息上传成功: {len(clean_records)} 条记录")
        
        return success
    
    def create_summary_file(self, data_dates: List[str]) -> bool:
        """创建数据总览文件"""
        try:
            summary = {
                "last_updated": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "available_dates": sorted(data_dates),
                "date_count": len(data_dates),
                "description": "A股历史数据备份仓库"
            }
            
            content = json.dumps(summary, ensure_ascii=False, indent=2)
            
            return self.create_or_update_file(
                "summary.json", 
                content, 
                "Update data summary"
            )
            
        except Exception as e:
            print(f"创建总览文件失败: {e}")
            return False