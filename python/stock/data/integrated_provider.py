#!/usr/bin/env python3
"""
集成数据提供者 - 优先使用GitHub数据仓库，akshare作为备用
"""

import pandas as pd
from datetime import date, datetime, timedelta
from typing import Optional, Dict, Any
import os
from pathlib import Path

from .akshare_provider import AkShareProvider
from .github_repo import GitHubDataRepo
from .data_uploader import DataUploader


class IntegratedDataProvider:
    """集成数据提供者：GitHub仓库 + akshare备用"""
    
    def __init__(self, 
                 use_github_first: bool = True,
                 repo_owner: str = "test3207",
                 repo_name: str = "stock-data",
                 cache_days: int = 3,
                 auto_upload: bool = True):
        
        self.use_github_first = use_github_first
        self.cache_days = cache_days
        self.auto_upload = auto_upload
        
        # 初始化数据源
        self.github_repo = GitHubDataRepo(repo_owner, repo_name)
        self.akshare_provider = AkShareProvider()
        
        # 初始化数据上传器（如果开启自动上传）
        self.data_uploader = DataUploader(repo_owner, repo_name) if auto_upload else None
        
        print(f"集成数据提供者初始化完成")
        print(f"GitHub优先: {use_github_first}")
        print(f"自动上传: {auto_upload}")
        print(f"仓库: {repo_owner}/{repo_name}")
    
    def get_stock_daily(self, symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """获取股票日线数据"""
        
        if self.use_github_first:
            # 首先尝试GitHub数据仓库
            try:
                github_data = self._get_from_github(symbol, start_date, end_date)
                if github_data is not None and not github_data.empty:
                    print(f"从GitHub获取 {symbol} 数据成功: {len(github_data)} 条记录")
                    return github_data
                else:
                    print(f"GitHub数据不完整，使用akshare备用")
            except Exception as e:
                print(f"GitHub数据获取失败: {e}，使用akshare备用")
        
        # akshare备用方案
        try:
            # 使用get_daily_price方法，传入单个股票代码列表
            akshare_data = self.akshare_provider.get_daily_price([symbol], start_date, end_date)
            if akshare_data is not None and not akshare_data.empty:
                # akshare返回的列名是 ts_code, trade_date，需要转换
                if 'ts_code' in akshare_data.columns:
                    # 筛选特定股票的数据
                    symbol_data = akshare_data[akshare_data['ts_code'] == symbol].copy()
                    
                    # 标准化列名以便后续处理
                    symbol_data['symbol'] = symbol_data['ts_code']
                    if 'trade_date' in symbol_data.columns:
                        symbol_data['date'] = pd.to_datetime(symbol_data['trade_date'], format='%Y%m%d')
                    
                    if not symbol_data.empty:
                        print(f"从akshare获取 {symbol} 数据成功: {len(symbol_data)} 条记录")
                        
                        # 自动上传到GitHub仓库（如果启用）
                        if self.auto_upload and self.data_uploader:
                            # 为上传准备完整的数据集（包含所有股票）
                            upload_data = akshare_data.copy()
                            upload_data['symbol'] = upload_data['ts_code']
                            if 'trade_date' in upload_data.columns:
                                upload_data['date'] = pd.to_datetime(upload_data['trade_date'], format='%Y%m%d')
                            self._upload_akshare_data_to_repo(upload_data, start_date, end_date)
                        
                        return symbol_data
                    else:
                        print(f"akshare返回数据中未找到 {symbol}")
                        return None
                else:
                    print(f"akshare返回数据格式异常，缺少ts_code列")
                    return None
            else:
                print(f"akshare也无法获取 {symbol} 数据")
                return None
        except Exception as e:
            print(f"akshare数据获取失败: {e}")
            return None
    
    def get_stock_basic(self) -> Optional[pd.DataFrame]:
        """获取股票基础信息"""
        
        if self.use_github_first:
            # 首先尝试GitHub
            try:
                github_basic = self.github_repo.download_basic_info()
                
                if github_basic is not None and not github_basic.empty:
                    print(f"从GitHub获取基础信息成功: {len(github_basic)} 条记录")
                    return github_basic
                else:
                    print("GitHub基础信息不可用，使用akshare备用")
            except Exception as e:
                print(f"GitHub基础信息获取失败: {e}，使用akshare备用")
        
        # akshare备用方案
        try:
            akshare_basic = self.akshare_provider.get_basic_info()
            if akshare_basic is not None and not akshare_basic.empty:
                print(f"从akshare获取基础信息成功: {len(akshare_basic)} 条记录")
                
                # 自动上传基础信息到GitHub仓库（如果启用）
                if self.auto_upload and self.data_uploader:
                    try:
                        upload_success = self.data_uploader.upload_basic_info(akshare_basic)
                        if upload_success:
                            print(f"基础信息已自动上传到GitHub仓库")
                        else:
                            print(f"基础信息上传失败")
                    except Exception as e:
                        print(f"自动上传基础信息时出错: {e}")
                
                return akshare_basic
            else:
                print("akshare基础信息获取失败")
                return None
        except Exception as e:
            print(f"akshare基础信息获取失败: {e}")
            return None
    
    def _get_from_github(self, symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """从GitHub仓库获取数据"""
        
        # 生成日期范围（只包含工作日）
        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        all_data = []
        current_date = start
        
        while current_date <= end:
            # 只处理工作日
            if current_date.weekday() < 5:
                date_str = current_date.strftime('%Y-%m-%d')
                
                # 下载当日所有数据
                daily_data = self.github_repo.download_daily_data(date_str)
                if daily_data is not None:
                    # 筛选特定股票
                    symbol_data = daily_data[daily_data['symbol'] == symbol]
                    if not symbol_data.empty:
                        all_data.append(symbol_data)
            
            current_date += timedelta(days=1)
        
        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            
            # 确保数据格式一致
            if 'date' in combined_df.columns:
                combined_df['date'] = pd.to_datetime(combined_df['date'])
                combined_df = combined_df.sort_values('date')
            
            return combined_df
        else:
            return None
    
    def check_data_availability(self) -> Dict[str, Any]:
        """检查数据源可用性"""
        result = {
            'github_available': False,
            'akshare_available': False,
            'github_dates': [],
            'akshare_test': False
        }
        
        # 检查GitHub
        try:
            if self.github_repo.check_repo_exists():
                result['github_available'] = True
                result['github_dates'] = self.github_repo.get_available_dates()
                print(f"GitHub仓库可用，包含 {len(result['github_dates'])} 个日期")
        except Exception as e:
            print(f"GitHub检查失败: {e}")
        
        # 检查akshare
        try:
            test_data = self.akshare_provider.get_basic_info()
            if test_data is not None and not test_data.empty:
                result['akshare_available'] = True
                result['akshare_test'] = True
                print(f"akshare可用，测试获取 {len(test_data)} 条基础信息")
        except Exception as e:
            print(f"akshare检查失败: {e}")
        
        return result
    
    def get_best_data_source(self, date_str: str = None) -> str:
        """判断最佳数据源"""
        if date_str is None:
            date_str = date.today().strftime('%Y-%m-%d')
        
        availability = self.check_data_availability()
        
        if self.use_github_first and availability['github_available']:
            if date_str in availability['github_dates']:
                return "github"
        
        if availability['akshare_available']:
            return "akshare"
        
        return "none"
    
    def get_data_summary(self) -> Dict[str, Any]:
        """获取数据源总览"""
        availability = self.check_data_availability()
        
        summary = {
            'primary_source': 'github' if self.use_github_first else 'akshare',
            'fallback_source': 'akshare' if self.use_github_first else 'github',
            'github_status': 'available' if availability['github_available'] else 'unavailable',
            'akshare_status': 'available' if availability['akshare_available'] else 'unavailable',
            'github_date_count': len(availability['github_dates']),
            'latest_github_date': max(availability['github_dates']) if availability['github_dates'] else 'none',
            'recommendation': self.get_best_data_source()
        }
        
        return summary
    
    def _upload_akshare_data_to_repo(self, akshare_data: pd.DataFrame, start_date: str, end_date: str):
        """将akshare数据上传到GitHub仓库"""
        if not self.data_uploader:
            print("未启用自动上传功能")
            return
        
        try:
            # 按日期分组上传
            if 'date' in akshare_data.columns:
                akshare_data['date'] = pd.to_datetime(akshare_data['date'])
                
                # 获取日期范围内的所有唯一日期
                unique_dates = akshare_data['date'].dt.strftime('%Y-%m-%d').unique()
                upload_count = 0
                
                print(f"开始上传akshare数据到GitHub仓库，共 {len(unique_dates)} 个日期")
                
                for date_str in unique_dates:
                    # 筛选该日期的数据
                    daily_data = akshare_data[
                        akshare_data['date'].dt.strftime('%Y-%m-%d') == date_str
                    ].copy()
                    
                    if not daily_data.empty:
                        # 上传该日期的数据
                        success = self.data_uploader.upload_daily_data(daily_data, date_str)
                        if success:
                            upload_count += 1
                            print(f"  ✅ {date_str}: {len(daily_data)} 条记录上传成功")
                        else:
                            print(f"  ❌ {date_str}: 上传失败")
                        
                        # 避免API频率限制
                        import time
                        time.sleep(1)
                
                print(f"akshare数据上传完成: {upload_count}/{len(unique_dates)} 个日期成功")
                
                # 更新数据总览
                if upload_count > 0:
                    try:
                        all_dates = list(unique_dates)
                        self.data_uploader.create_summary_file(all_dates)
                        print("数据总览文件已更新")
                    except Exception as e:
                        print(f"更新数据总览失败: {e}")
            else:
                print("akshare数据缺少date列，无法按日期上传")
                
        except Exception as e:
            print(f"上传akshare数据时出错: {e}")
    
    def manual_upload_data(self, symbol: str, start_date: str, end_date: str) -> bool:
        """手动上传指定股票的数据到GitHub仓库"""
        if not self.data_uploader:
            print("未启用数据上传功能")
            return False
        
        try:
            print(f"手动上传 {symbol} 从 {start_date} 到 {end_date} 的数据...")
            
            # 从akshare获取数据
            akshare_data = self.akshare_provider.get_daily_price([symbol], start_date, end_date)
            
            if akshare_data is not None and not akshare_data.empty:
                # 上传数据
                self._upload_akshare_data_to_repo(akshare_data, start_date, end_date)
                return True
            else:
                print(f"无法获取 {symbol} 的数据")
                return False
                
        except Exception as e:
            print(f"手动上传数据失败: {e}")
            return False