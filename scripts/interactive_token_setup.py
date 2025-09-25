#!/usr/bin/env python3
"""
交互式GitHub Token设置工具
"""

import sys
import os
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "python"))

def setup_token_interactive():
    """交互式设置GitHub Token"""
    print("🔑 GitHub Token 交互式设置")
    print("=" * 50)
    
    # 检查.env文件是否存在
    env_file = project_root / ".env"
    if not env_file.exists():
        print("📄 创建 .env 文件...")
        example_file = project_root / ".env.example"
        if example_file.exists():
            with open(example_file, 'r', encoding='utf-8') as f:
                content = f.read()
            with open(env_file, 'w', encoding='utf-8') as f:
                f.write(content)
            print("✅ .env 文件已创建")
        else:
            print("❌ .env.example 文件不存在")
            return False
    
    print("\n📋 获取GitHub Token步骤:")
    print("1. 访问: https://github.com/settings/tokens")
    print("2. 点击 'Generate new token' → 'Generate new token (classic)'")
    print("3. 设置token名称: 'Stock Trading System'")
    print("4. 选择权限: 勾选 'repo' (完整权限)")
    print("5. 点击 'Generate token' 并复制token")
    
    print("\n" + "="*50)
    token = input("请粘贴您的GitHub Token: ").strip()
    
    if not token or len(token) < 20:
        print("❌ Token格式不正确")
        return False
    
    # 更新.env文件
    try:
        with open(env_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 替换token
        if 'GITHUB_TOKEN=' in content:
            lines = content.split('\n')
            new_lines = []
            for line in lines:
                if line.startswith('GITHUB_TOKEN='):
                    new_lines.append(f'GITHUB_TOKEN={token}')
                else:
                    new_lines.append(line)
            content = '\n'.join(new_lines)
        else:
            content += f'\nGITHUB_TOKEN={token}\n'
        
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ Token已保存到 .env 文件")
        
        # 验证token
        print("\n🔍 验证Token...")
        from stock.config import validate_github_token
        if validate_github_token(token):
            print("✅ Token验证成功！")
            print("\n🎉 环境配置完成！")
            return True
        else:
            print("❌ Token验证失败，请检查权限设置")
            return False
            
    except Exception as e:
        print(f"❌ 保存Token时出错: {e}")
        return False

def main():
    """主函数"""
    try:
        if setup_token_interactive():
            print("\n💡 现在可以运行:")
            print("python scripts/test_system.py")
            print("或使用 IntegratedDataProvider(auto_upload=True)")
        else:
            print("\n💡 请重新运行此脚本完成设置")
    except KeyboardInterrupt:
        print("\n\n⚠️  用户取消操作")
    except Exception as e:
        print(f"\n❌ 设置过程出错: {e}")

if __name__ == "__main__":
    main()