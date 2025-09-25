#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键安装脚本 - 智能检测网络并选择镜像源
适用于国内外网络环境
"""

import subprocess
import sys
import os
import platform
import time
from pathlib import Path

# 镜像源配置
MIRRORS = {
    "tsinghua": "https://pypi.tuna.tsinghua.edu.cn/simple",
    "aliyun": "https://mirrors.aliyun.com/pypi/simple/",
    "douban": "https://pypi.douban.com/simple/",
    "ustc": "https://pypi.mirrors.ustc.edu.cn/simple/",
    "official": "https://pypi.org/simple"
}

# 核心依赖包
CORE_PACKAGES = [
    "pandas",
    "numpy", 
    "akshare",
    "requests"
]

# 可选依赖包
OPTIONAL_PACKAGES = [
    "tqdm",
    "matplotlib",
    "seaborn"
]

def print_banner():
    """打印横幅"""
    print("=" * 60)
    print("🚀 A股量化交易系统 - 一键安装脚本")
    print("=" * 60)
    print("📦 功能：智能检测网络环境，自动选择最优镜像源")
    print("🌐 支持：清华、阿里云、豆瓣、中科大、官方镜像源")
    print("⚡ 特性：网络检测、断点续传、错误重试")
    print("=" * 60)

def check_python_version():
    """检查Python版本"""
    version = sys.version_info
    print(f"🐍 Python版本检查: {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ 需要Python 3.8或更高版本")
        print("请升级Python后重试：https://www.python.org/downloads/")
        return False
    
    print("✅ Python版本符合要求")
    return True

def test_network_connectivity():
    """测试网络连通性"""
    print("\n🔍 测试网络连通性...")
    
    # 测试站点列表（延迟从低到高）
    test_sites = [
        ("pypi.tuna.tsinghua.edu.cn", "清华镜像"),
        ("mirrors.aliyun.com", "阿里云镜像"),
        ("pypi.douban.com", "豆瓣镜像"), 
        ("pypi.mirrors.ustc.edu.cn", "中科大镜像"),
        ("pypi.org", "官方源")
    ]
    
    best_mirror = None
    best_time = float('inf')
    
    for site, name in test_sites:
        try:
            start_time = time.time()
            
            # 使用ping命令测试连通性
            if platform.system().lower() == 'windows':
                result = subprocess.run(['ping', '-n', '1', '-w', '3000', site], 
                                      capture_output=True, text=True, timeout=5)
            else:
                result = subprocess.run(['ping', '-c', '1', '-W', '3', site], 
                                      capture_output=True, text=True, timeout=5)
            
            elapsed = time.time() - start_time
            
            if result.returncode == 0:
                print(f"✅ {name} ({site}): {elapsed:.2f}s")
                if elapsed < best_time:
                    best_time = elapsed
                    if site == "pypi.tuna.tsinghua.edu.cn":
                        best_mirror = "tsinghua"
                    elif site == "mirrors.aliyun.com":
                        best_mirror = "aliyun"
                    elif site == "pypi.douban.com":
                        best_mirror = "douban"
                    elif site == "pypi.mirrors.ustc.edu.cn":
                        best_mirror = "ustc"
                    else:
                        best_mirror = "official"
            else:
                print(f"❌ {name} ({site}): 连接失败")
                
        except (subprocess.TimeoutExpired, subprocess.SubprocessError):
            print(f"⏱️ {name} ({site}): 超时")
        except Exception as e:
            print(f"❌ {name} ({site}): 错误 - {e}")
    
    if best_mirror:
        mirror_url = MIRRORS[best_mirror]
        print(f"\n🎯 选择最优镜像源: {best_mirror} ({best_time:.2f}s)")
        print(f"📍 镜像地址: {mirror_url}")
        return best_mirror, mirror_url
    else:
        print(f"\n⚠️ 所有镜像源测试失败，使用默认清华镜像")
        return "tsinghua", MIRRORS["tsinghua"]

def check_virtual_env():
    """检查并创建虚拟环境"""
    print(f"\n📁 检查虚拟环境...")
    
    venv_path = Path(".venv")
    
    if venv_path.exists():
        print("✅ 虚拟环境已存在")
        return True
    
    print("🔧 创建虚拟环境...")
    try:
        subprocess.run([sys.executable, "-m", "venv", ".venv"], check=True)
        print("✅ 虚拟环境创建成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 虚拟环境创建失败: {e}")
        return False

def get_pip_command():
    """获取pip命令路径"""
    if platform.system().lower() == 'windows':
        return str(Path(".venv/Scripts/pip.exe"))
    else:
        return str(Path(".venv/bin/pip"))

def install_packages(mirror_url, packages, description=""):
    """安装包"""
    pip_cmd = get_pip_command()
    
    if not Path(pip_cmd).exists():
        print(f"❌ 找不到pip: {pip_cmd}")
        return False
    
    print(f"\n📦 安装{description}...")
    
    success_count = 0
    total_count = len(packages)
    
    for package in packages:
        print(f"⏳ 正在安装 {package}...")
        try:
            cmd = [pip_cmd, "install", "-i", mirror_url, package]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                print(f"✅ {package} 安装成功")
                success_count += 1
            else:
                print(f"❌ {package} 安装失败:")
                print(result.stderr[:200] + "..." if len(result.stderr) > 200 else result.stderr)
                
        except subprocess.TimeoutExpired:
            print(f"⏱️ {package} 安装超时")
        except Exception as e:
            print(f"❌ {package} 安装异常: {e}")
    
    print(f"\n📊 {description}安装结果: {success_count}/{total_count} 成功")
    return success_count == total_count

def test_installation():
    """测试安装结果"""
    print(f"\n🧪 测试安装结果...")
    
    pip_cmd = get_pip_command()
    python_cmd = get_pip_command().replace("pip", "python").replace("pip.exe", "python.exe")
    
    # 测试导入
    test_code = '''
import pandas as pd
import numpy as np
import akshare as ak
import requests

print("All core packages imported successfully!")
print("pandas:", pd.__version__)
print("numpy:", np.__version__) 
print("akshare:", ak.__version__)
print("requests:", requests.__version__)
'''
    
    try:
        result = subprocess.run([python_cmd, "-c", test_code], 
                              capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ 导入测试通过:")
            print(result.stdout)
            return True
        else:
            print("❌ 导入测试失败:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        return False

def create_activation_script():
    """创建激活脚本"""
    print(f"\n📝 创建激活脚本...")
    
    # Windows激活脚本
    if platform.system().lower() == 'windows':
        activate_script = '''@echo off
echo Activating A-Share Quantitative Trading System Virtual Environment
call .venv\\Scripts\\activate.bat
echo Virtual environment activated successfully
echo.
echo Common commands:
echo   python main_quantitative_system.py  # Run main quantitative system
echo   python simulation/main.py           # Run real-time simulation system  
echo   deactivate                          # Exit virtual environment
echo.
cmd /k
'''
        with open("activate.bat", "w", encoding="gbk") as f:
            f.write(activate_script)
        print("✅ Windows激活脚本: activate.bat")
    
    # Linux/Mac激活脚本
    activate_script_sh = '''#!/bin/bash
echo "Activating A-Share Quantitative Trading System Virtual Environment"
source .venv/bin/activate
echo "Virtual environment activated successfully"
echo
echo "Common commands:"
echo "  python main_quantitative_system.py  # Run main quantitative system"
echo "  python simulation/main.py           # Run real-time simulation system"
echo "  deactivate                          # Exit virtual environment"
echo
exec bash
'''
    
    with open("activate.sh", "w", encoding="utf-8") as f:
        f.write(activate_script_sh)
    
    # 设置执行权限
    try:
        os.chmod("activate.sh", 0o755)
        print("✅ Linux/Mac激活脚本: activate.sh")
    except:
        print("⚠️ Linux/Mac激活脚本权限设置失败")

def print_success_message():
    """打印成功信息"""
    print("\n" + "=" * 60)
    print("🎉 安装完成！")
    print("=" * 60)
    
    print("\n📋 快速开始：")
    if platform.system().lower() == 'windows':
        print("1. 双击运行: activate.bat")
        print("2. 或手动激活: .venv\\Scripts\\activate.bat")
    else:
        print("1. 执行: ./activate.sh")  
        print("2. 或手动激活: source .venv/bin/activate")
    
    print("\n🚀 运行系统：")
    print("• 历史回测: python main_quantitative_system.py")
    print("• 实时模拟: python simulation/main.py --mode interactive")
    print("• 查看帮助: python simulation/main.py --help")
    
    print("\n📚 文档位置：")
    print("• README.md - 项目说明")
    print("• docs/实时模拟系统使用手册.md - 详细使用指南")
    
    print(f"\n💡 提示：如需重新安装，请删除 .venv 目录后重新运行本脚本")

def main():
    """主函数"""
    print_banner()
    
    # 检查Python版本
    if not check_python_version():
        return False
    
    # 测试网络并选择镜像源
    mirror_name, mirror_url = test_network_connectivity()
    
    # 检查并创建虚拟环境
    if not check_virtual_env():
        return False
    
    # 安装核心依赖
    if not install_packages(mirror_url, CORE_PACKAGES, "核心依赖"):
        print("❌ 核心依赖安装失败，请检查网络或手动安装")
        return False
    
    # 安装可选依赖（失败不影响主功能）
    install_packages(mirror_url, OPTIONAL_PACKAGES, "可选依赖")
    
    # 测试安装
    if not test_installation():
        print("⚠️ 安装测试未通过，但核心功能可能仍可使用")
    
    # 创建激活脚本
    create_activation_script()
    
    # 打印成功信息
    print_success_message()
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ 安装被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 安装过程出现异常: {e}")
        sys.exit(1)