@echo off
chcp 65001 >nul
echo.
echo ==========================================
echo 🚀 A股量化交易系统 - 一键安装
echo ==========================================
echo.
echo 正在启动智能安装程序...
echo 📡 将自动检测网络环境并选择最优镜像源
echo.

python install.py

if %errorlevel% equ 0 (
    echo.
    echo ✅ 安装成功！按任意键继续...
    pause >nul
) else (
    echo.
    echo ❌ 安装失败，请检查错误信息
    echo 💡 建议：
    echo   1. 确保已安装Python 3.8+
    echo   2. 检查网络连接
    echo   3. 尝试管理员权限运行
    echo.
    pause
)