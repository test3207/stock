#!/usr/bin/env python3
"""
环境配置加载器
统一管理项目环境变量
"""

import os
from pathlib import Path
from typing import Optional


def load_env(env_file: str = '.env') -> bool:
    """
    加载.env文件中的环境变量
    
    Args:
        env_file: .env文件路径，相对于项目根目录
        
    Returns:
        bool: 加载是否成功
    """
    # 找到项目根目录（包含.env文件的目录）
    current = Path(__file__).parent  # stock/config/
    project_root = current.parent.parent.parent  # 从 python/stock/config 到项目根目录
    env_path = project_root / env_file
    
    if not env_path.exists():
        return False
    
    try:
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # 跳过注释和空行
                if not line or line.startswith('#'):
                    continue
                
                # 解析 KEY=VALUE
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # 移除引号
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    
                    # 只有在环境变量不存在时才设置
                    if key not in os.environ:
                        os.environ[key] = value
        
        return True
        
    except Exception as e:
        print(f"加载 {env_file} 失败: {e}")
        return False


def get_github_token() -> Optional[str]:
    """
    获取GitHub Token，按优先级顺序：
    1. 环境变量 GITHUB_TOKEN
    2. .env 文件
    3. .env.local 文件
    
    Returns:
        Optional[str]: GitHub Token 或 None
    """
    # 1. 检查环境变量
    token = os.environ.get('GITHUB_TOKEN')
    if token:
        return token
    
    # 2. 尝试加载 .env.local (本地开发)
    if load_env('.env.local'):
        token = os.environ.get('GITHUB_TOKEN')
        if token:
            return token
    
    # 3. 尝试加载 .env
    if load_env('.env'):
        token = os.environ.get('GITHUB_TOKEN')
        if token:
            return token
    
    return None


def ensure_env_setup() -> bool:
    """
    确保环境配置正确，如果没有配置则引导用户设置
    
    Returns:
        bool: 配置是否完成
    """
    token = get_github_token()
    
    if token:
        print(f"✅ GitHub Token 已配置: {token[:4]}...")
        return True
    
    project_root = Path(__file__).parent.parent
    env_example = project_root / '.env.example'
    env_file = project_root / '.env'
    
    print("❌ GitHub Token 未配置")
    print("\n📋 配置步骤:")
    print(f"1. 复制模板: cp {env_example.name} {env_file.name}")
    print("2. 编辑 .env 文件，设置你的 GITHUB_TOKEN")
    print("3. 从 https://github.com/settings/tokens 获取token")
    print("4. 确保token有 'repo' 完整权限")
    
    if env_example.exists() and not env_file.exists():
        choice = input("\n是否自动复制模板文件？(Y/n): ").strip()
        if choice.lower() != 'n':
            try:
                import shutil
                shutil.copy2(env_example, env_file)
                print(f"✅ 已创建 {env_file.name}")
                print("💡 请编辑该文件并设置你的 GITHUB_TOKEN")
            except Exception as e:
                print(f"❌ 复制失败: {e}")
    
    return False


def validate_github_token(token: str) -> bool:
    """
    验证GitHub Token是否有效
    
    Args:
        token: GitHub Token
        
    Returns:
        bool: Token是否有效
    """
    try:
        import requests
        headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        response = requests.get("https://api.github.com/user", headers=headers, timeout=10)
        
        if response.status_code == 200:
            user_info = response.json()
            print(f"✅ Token有效，用户: {user_info.get('login', 'Unknown')}")
            
            # 检查API限制
            remaining = response.headers.get('X-RateLimit-Remaining', 'Unknown')
            print(f"📊 API剩余次数: {remaining}")
            
            return True
        else:
            print(f"❌ Token验证失败: {response.status_code}")
            if response.status_code == 401:
                print("💡 请检查token是否正确")
            elif response.status_code == 403:
                print("💡 请检查token权限设置")
            return False
            
    except Exception as e:
        print(f"❌ 验证Token时出错: {e}")
        return False


if __name__ == "__main__":
    print("🔧 环境配置检查")
    print("=" * 30)
    
    # 自动加载环境变量
    load_env()
    
    # 确保配置完成
    if ensure_env_setup():
        token = get_github_token()
        if token:
            validate_github_token(token)
    
    print("\n💡 使用说明:")
    print("from python.stock.config import get_github_token")
    print("token = get_github_token()")