#!/usr/bin/env python3
"""
IDE导入测试脚本
验证IDE是否能正确识别模块导入
"""

# 方法1：直接导入（推荐给IDE使用）
try:
    from python.stock.data.akshare_provider import AkShareProvider
    print("✅ 方法1成功: from python.stock.data.akshare_provider import AkShareProvider")
except ImportError as e:
    print(f"❌ 方法1失败: {e}")

# 方法2：sys.path导入
try:
    import sys
    import os
    
    # 添加python目录到路径
    python_path = os.path.join(os.path.dirname(__file__), 'python')
    if python_path not in sys.path:
        sys.path.insert(0, python_path)
    
    from stock.data.akshare_provider import AkShareProvider as AkShareProvider2
    print("✅ 方法2成功: sys.path + from stock.data.akshare_provider import AkShareProvider")
except ImportError as e:
    print(f"❌ 方法2失败: {e}")

# 验证两个导入是否指向同一个类
try:
    print(f"\n模块信息:")
    print(f"  AkShareProvider模块: {AkShareProvider.__module__}")
    print(f"  文件路径: {AkShareProvider.__module__.replace('.', os.sep)}.py")
except:
    pass

print(f"\n💡 IDE配置建议:")
print(f"  1. 确保VS Code中Python解释器路径正确")
print(f"  2. 在VS Code设置中添加: python.analysis.extraPaths = ['./python']")
print(f"  3. 重新加载VS Code窗口: Ctrl+Shift+P -> 'Developer: Reload Window'")
print(f"  4. 使用 'from python.stock.data.akshare_provider import AkShareProvider' 导入方式")