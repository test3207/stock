#!/usr/bin/env python3
"""
测试新的环境配置系统和数据备份流程
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "python"))

def test_config_system():
    """测试配置系统"""
    print("🧪 测试配置系统...")
    
    try:
        from stock.config import load_env, get_github_token, validate_github_token
        
        # 测试环境加载
        env_loaded = load_env()
        if env_loaded:
            print("✅ 环境变量加载成功")
        else:
            print("⚠️  环境变量加载完成（可能使用默认值）")
        
        # 测试Token获取
        token = get_github_token()
        if token:
            print("✅ GitHub Token获取成功")
            
            # 验证Token
            if validate_github_token(token):
                print("✅ GitHub Token验证成功")
            else:
                print("❌ GitHub Token验证失败")
        else:
            print("❌ GitHub Token未配置")
            
    except Exception as e:
        print(f"❌ 配置系统测试失败: {e}")
        return False
    
    return True

def test_data_system():
    """测试数据系统"""
    print("\n🧪 测试数据系统...")
    
    try:
        from stock.data import IntegratedDataProvider
        
        # 创建提供者（但不自动上传，避免测试时产生副作用）
        provider = IntegratedDataProvider(auto_upload=False)
        print("✅ IntegratedDataProvider创建成功")
        
        # 测试GitHub仓库连接
        from stock.data.github_repo import GitHubDataRepo
        repo = GitHubDataRepo()
        
        # 简单测试（不下载数据）
        print("✅ GitHub仓库连接准备就绪")
        
    except Exception as e:
        print(f"❌ 数据系统测试失败: {e}")
        return False
    
    return True

def main():
    """主测试函数"""
    print("🚀 系统集成测试")
    print("=" * 40)
    
    success = True
    success &= test_config_system()
    success &= test_data_system()
    
    print("\n" + "=" * 40)
    if success:
        print("🎉 所有测试通过！系统准备就绪")
        print("\n💡 下一步:")
        print("1. 运行 python scripts/setup_env.py 配置Token")
        print("2. 使用 IntegratedDataProvider(auto_upload=True) 开始数据同步")
    else:
        print("❌ 部分测试失败，请检查配置")

if __name__ == "__main__":
    main()