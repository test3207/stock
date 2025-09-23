#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实时模拟系统部署脚本
用于生产环境部署和配置
"""

import sys
import os
import json
import logging
from pathlib import Path
from datetime import datetime
import subprocess

def setup_logging():
    """设置部署日志"""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / f"deployment_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def check_python_environment():
    """检查Python环境"""
    print("🔍 检查Python环境...")
    
    # 检查Python版本
    python_version = sys.version_info
    if python_version.major < 3 or python_version.minor < 8:
        print("❌ 需要Python 3.8或更高版本")
        return False
    
    print(f"✅ Python版本: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    # 检查必要的包
    required_packages = [
        'pandas', 'numpy', 'akshare', 'requests'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}: 已安装")
        except ImportError:
            print(f"❌ {package}: 未安装")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️  需要安装以下包: {', '.join(missing_packages)}")
        print("运行命令: pip install " + " ".join(missing_packages))
        return False
    
    return True

def create_directory_structure():
    """创建目录结构"""
    print("\n📁 创建目录结构...")
    
    directories = [
        "data/simulation/instances/default",
        "data/simulation/cache/market_data",
        "data/simulation/cache/reference_data", 
        "data/simulation/cache/metadata",
        "data/simulation/templates",
        "logs",
        "logs/simulation",
        "logs/cronjobs"
    ]
    
    for directory in directories:
        dir_path = Path(directory)
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"✅ 创建目录: {directory}")
    
    return True

def create_default_instance():
    """创建默认实例"""
    print("\n🏗️  创建默认实例...")
    
    try:
        # 添加项目路径
        sys.path.append(str(Path(__file__).parent))
        
        from simulation.core.instance_manager import InstanceManager
        
        manager = InstanceManager()
        
        # 创建默认实例
        success = manager.create_instance("default")
        
        if success:
            print("✅ 默认实例创建成功")
            
            # 创建初始状态
            from simulation.core.state_manager import StateManager
            state_manager = StateManager("default")
            
            initial_capital = 1000000.0  # 100万初始资金
            state_success = state_manager.create_initial_state(initial_capital)
            
            if state_success:
                print(f"✅ 初始状态创建成功，初始资金: {initial_capital:,.2f}")
            else:
                print("⚠️  初始状态创建失败")
                
        else:
            print("❌ 默认实例创建失败")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ 默认实例创建异常: {e}")
        return False

def create_global_config():
    """创建全局配置"""
    print("\n⚙️  创建全局配置...")
    
    global_config = {
        "version": "1.0.0",
        "created_at": datetime.now().isoformat(),
        "default_instance": "default",
        "data_sources": {
            "primary": "akshare",
            "backup": None
        },
        "cache_settings": {
            "default_ttl_hours": 24,
            "max_cache_size_mb": 1024,
            "cleanup_interval_hours": 6
        },
        "logging": {
            "level": "INFO",
            "rotation": "daily",
            "retention_days": 30
        },
        "monitoring": {
            "health_check_interval_minutes": 15,
            "alert_thresholds": {
                "memory_usage_percent": 80,
                "disk_usage_percent": 85
            }
        }
    }
    
    config_path = Path("data/simulation/global_config.json")
    
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(global_config, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 全局配置已保存: {config_path}")
        return True
        
    except Exception as e:
        print(f"❌ 全局配置创建失败: {e}")
        return False

def setup_cronjob_examples():
    """设置cronjob示例"""
    print("\n⏰ 设置cronjob示例...")
    
    # 创建cronjob示例脚本
    cronjob_scripts = {
        "daily_rebalance.sh": f"""#!/bin/bash
# 每日调仓任务
cd {Path.cwd()}
python -c "
import sys
sys.path.append('.')
from simulation.cronjobs.daily_rebalance import run_daily_rebalance
run_daily_rebalance('default')
" >> logs/cronjobs/daily_rebalance.log 2>&1
""",
        "risk_monitoring.sh": f"""#!/bin/bash
# 风控监控任务
cd {Path.cwd()}
python -c "
import sys
sys.path.append('.')
from simulation.cronjobs.risk_monitoring import run_risk_monitoring
run_risk_monitoring('default')
" >> logs/cronjobs/risk_monitoring.log 2>&1
""",
        "data_update.sh": f"""#!/bin/bash
# 数据更新任务
cd {Path.cwd()}
python -c "
import sys
sys.path.append('.')
from simulation.cronjobs.data_update import run_data_update
run_data_update('default')
" >> logs/cronjobs/data_update.log 2>&1
"""
    }
    
    scripts_dir = Path("scripts")
    scripts_dir.mkdir(exist_ok=True)
    
    for script_name, script_content in cronjob_scripts.items():
        script_path = scripts_dir / script_name
        
        try:
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(script_content)
            
            # 在类Unix系统上设置执行权限
            if os.name != 'nt':  # 非Windows系统
                os.chmod(script_path, 0o755)
            
            print(f"✅ 创建脚本: {script_path}")
            
        except Exception as e:
            print(f"❌ 创建脚本失败 {script_name}: {e}")
    
    # 创建crontab示例
    crontab_example = """
# 实时模拟系统 Crontab 配置示例
# 复制并修改路径后添加到 crontab -e

# 每日上午9:00执行数据更新
0 9 * * 1-5 /path/to/stock/scripts/data_update.sh

# 每日上午9:30执行调仓检查  
30 9 * * 1-5 /path/to/stock/scripts/daily_rebalance.sh

# 每小时执行风控监控（交易时间）
0 9-15 * * 1-5 /path/to/stock/scripts/risk_monitoring.sh

# 注意事项:
# 1. 将 /path/to/stock 替换为实际项目路径
# 2. 确保脚本有执行权限: chmod +x scripts/*.sh  
# 3. 检查Python环境路径是否正确
# 4. 建议先在测试环境验证
"""
    
    crontab_path = scripts_dir / "crontab_example.txt"
    
    try:
        with open(crontab_path, 'w', encoding='utf-8') as f:
            f.write(crontab_example)
        
        print(f"✅ Crontab示例: {crontab_path}")
        
    except Exception as e:
        print(f"❌ Crontab示例创建失败: {e}")
    
    return True

def verify_deployment():
    """验证部署"""
    print("\n🔬 验证部署...")
    
    try:
        # 运行测试脚本
        print("运行系统测试...")
        
        test_script = Path("test_realtime_simulation.py")
        if test_script.exists():
            print(f"✅ 测试脚本存在: {test_script}")
            print("建议运行: python test_realtime_simulation.py")
        else:
            print("⚠️  测试脚本不存在")
        
        # 检查关键文件
        critical_files = [
            "simulation/main.py",
            "simulation/core/instance_manager.py",
            "simulation/engines/trading_engine.py",
            "data/simulation/global_config.json"
        ]
        
        all_files_exist = True
        for file_path in critical_files:
            if Path(file_path).exists():
                print(f"✅ {file_path}")
            else:
                print(f"❌ {file_path}")
                all_files_exist = False
        
        return all_files_exist
        
    except Exception as e:
        print(f"❌ 部署验证失败: {e}")
        return False

def print_deployment_summary():
    """打印部署总结"""
    print("\n" + "="*60)
    print("🎉 实时模拟系统部署完成")
    print("="*60)
    
    print("\n📋 下一步操作:")
    print("1. 运行测试: python test_realtime_simulation.py")
    print("2. 检查配置: 查看 data/simulation/instances/default/config.json")
    print("3. 设置cronjob: 参考 scripts/crontab_example.txt")
    print("4. 启动系统: python simulation/main.py --instance default --mode cronjob")
    
    print("\n📁 重要目录:")
    print("- 实例配置: data/simulation/instances/")
    print("- 缓存数据: data/simulation/cache/")  
    print("- 日志文件: logs/")
    print("- 执行脚本: scripts/")
    
    print("\n🔧 运行模式:")
    print("- 交互模式: python simulation/main.py --mode interactive")
    print("- Cronjob模式: python simulation/main.py --mode cronjob")  
    print("- 守护进程: python simulation/main.py --mode daemon")
    
    print("\n⚠️  注意事项:")
    print("- 确保网络连接正常（akshare数据源）")
    print("- 检查系统时间和时区设置")
    print("- 定期备份 data/simulation/ 目录")
    print("- 监控系统资源使用情况")

def main():
    """主部署函数"""
    logger = setup_logging()
    
    print("🚀 开始部署实时模拟系统")
    print("=" * 60)
    
    deployment_steps = [
        ("检查Python环境", check_python_environment),
        ("创建目录结构", create_directory_structure),
        ("创建默认实例", create_default_instance),
        ("创建全局配置", create_global_config),
        ("设置Cronjob示例", setup_cronjob_examples),
        ("验证部署", verify_deployment)
    ]
    
    success_count = 0
    total_steps = len(deployment_steps)
    
    for step_name, step_func in deployment_steps:
        try:
            logger.info(f"执行步骤: {step_name}")
            success = step_func()
            
            if success:
                success_count += 1
                logger.info(f"步骤成功: {step_name}")
            else:
                logger.error(f"步骤失败: {step_name}")
                print(f"❌ 步骤失败: {step_name}")
                
        except Exception as e:
            logger.error(f"步骤异常: {step_name} - {e}")
            print(f"❌ 步骤异常: {step_name} - {e}")
    
    # 部署结果
    if success_count == total_steps:
        print("\n✅ 部署成功！")
        print_deployment_summary()
        return True
    else:
        print(f"\n⚠️  部署部分成功: {success_count}/{total_steps}")
        print("请检查失败的步骤并重新运行")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)