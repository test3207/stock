#!/usr/bin/env python3
"""
GitHub Token 配置验证脚本
"""

import os
import sys
import requests
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "python"))

from stock.data import IntegratedDataProvider, DataUploader

def test_github_token():
    """测试GitHub Token配置"""
    print("=" * 50)
    print("GitHub Token 配置测试")
    print("=" * 50)
    
    # 检查环境变量
    token = os.environ.get('GITHUB_TOKEN')
    
    if token:
        print(f"✅ GITHUB_TOKEN 已设置")
        print(f"📝 Token前缀: {token[:4]}...")
        print(f"📏 Token长度: {len(token)} 字符")
        
        if len(token) < 20:
            print("⚠️ Token长度似乎太短，请检查")
            return False
            
    else:
        print("❌ GITHUB_TOKEN 未设置")
        print("💡 请运行以下命令之一：")
        print("   Windows: .\\setup_github_token.ps1")
        print("   Linux/Mac: source setup_github_token.sh")
        return False
    
    # 测试DataUploader
    print("\n📤 测试DataUploader...")
    try:
        uploader = DataUploader()
        
        if uploader.github_token:
            print("✅ DataUploader Token配置正确")
            
            # 测试GitHub API连接
            import requests
            headers = {
                'Authorization': f'token {uploader.github_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            print("🔍 测试GitHub API连接...")
            response = requests.get("https://api.github.com/user", headers=headers, timeout=10)
            
            if response.status_code == 200:
                user_info = response.json()
                print(f"✅ GitHub API连接成功")
                print(f"👤 用户: {user_info.get('login', 'Unknown')}")
                print(f"📊 API剩余次数: {response.headers.get('X-RateLimit-Remaining', 'Unknown')}")
                return True
            else:
                print(f"❌ GitHub API连接失败: {response.status_code}")
                print(f"🔍 响应: {response.text}")
                return False
                
        else:
            print("❌ DataUploader Token未配置")
            return False
            
    except Exception as e:
        print(f"❌ 测试DataUploader时出错: {e}")
        return False

def test_integrated_provider():
    """测试集成数据提供者的上传功能"""
    print("\n" + "=" * 50)
    print("集成数据提供者上传测试")
    print("=" * 50)
    
    try:
        # 启用自动上传模式
        provider = IntegratedDataProvider(auto_upload=True)
        
        if provider.data_uploader and provider.data_uploader.github_token:
            print("✅ 集成数据提供者Token配置正确")
            print("📤 可以执行自动上传功能")
            
            # 简单的上传测试（不实际执行，只检查权限）
            print("🔍 检查仓库写入权限...")
            
            repo_url = f"https://api.github.com/repos/{provider.data_uploader.repo_owner}/{provider.data_uploader.repo_name}"
            headers = provider.data_uploader.headers
            
            response = requests.get(repo_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                repo_info = response.json()
                print(f"✅ 仓库访问成功: {repo_info['full_name']}")
                
                # 检查写入权限
                permissions = repo_info.get('permissions', {})
                if permissions.get('push', False):
                    print("✅ 具有写入权限，可以上传数据")
                    return True
                else:
                    print("⚠️ 没有写入权限，请检查Token权限设置")
                    return False
                    
            elif response.status_code == 404:
                print("ℹ️ 仓库不存在，将在首次上传时自动创建")
                return True
            else:
                print(f"❌ 仓库访问失败: {response.status_code}")
                return False
                
        else:
            print("❌ 集成数据提供者Token未配置")
            return False
            
    except Exception as e:
        print(f"❌ 测试集成数据提供者时出错: {e}")
        return False

def main():
    """主测试函数"""
    print("GitHub Token 配置验证开始\n")
    
    success = True
    
    success &= test_github_token()
    success &= test_integrated_provider()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 所有测试通过！GitHub Token配置正确")
        print("💡 现在可以使用自动上传功能了")
    else:
        print("❌ 部分测试失败，请检查配置")
        
    print("\n📋 配置说明:")
    print("1. 本地开发: 运行 setup_github_token.ps1 或 setup_github_token.sh")
    print("2. GitHub Actions: Token会自动配置")
    print("3. 权限要求: repo (完整权限)")
    print("=" * 50)

if __name__ == "__main__":
    main()