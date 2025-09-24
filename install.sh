#!/bin/bash

# A股量化交易系统 - Linux/Mac一键安装脚本

echo "=========================================="
echo "🚀 A股量化交易系统 - 一键安装"
echo "=========================================="
echo ""
echo "正在启动智能安装程序..."
echo "📡 将自动检测网络环境并选择最优镜像源"
echo ""

python3 install.py

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ 安装成功！"
    echo "💡 使用 ./activate.sh 激活环境"
else
    echo ""
    echo "❌ 安装失败，请检查错误信息"
    echo "💡 建议："
    echo "  1. 确保已安装Python 3.8+"
    echo "  2. 检查网络连接"  
    echo "  3. 尝试 sudo 权限运行"
    echo ""
fi