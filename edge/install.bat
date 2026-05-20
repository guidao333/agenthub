@echo off
chcp 65001 >nul
REM AgentHub Edge 一键安装脚本 (Windows)

echo ==========================================
echo   AgentHub Edge - AI视觉推理盒子 安装
echo ==========================================

REM 检查Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 未找到 Python，请先安装 Python 3.9+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo ✅ Python 已安装

REM 创建虚拟环境
set SCRIPT_DIR=%~dp0
set VENV_DIR=%SCRIPT_DIR%.venv

echo 📦 创建虚拟环境...
python -m venv "%VENV_DIR%"
call "%VENV_DIR%\Scripts\activate.bat"

REM 安装依赖
echo 📦 安装依赖（首次安装需要下载YOLO模型，可能需要几分钟）...
pip install --upgrade pip
pip install -r "%SCRIPT_DIR%requirements.txt"

echo.
echo ✅ 安装完成！
echo.
echo 使用方法:
echo   1. 交互式配置:  python main.py setup
echo   2. 命令行配置:  python main.py setup --server https://www.agenthub.wang --api-key YOUR_KEY
echo   3. 发现摄像头:  python main.py discover
echo   4. 启动服务:    python main.py start
echo.
pause
