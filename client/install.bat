@echo off
chcp 65001 >nul
title AgentHub Unified Client - Install

echo ==========================================
echo   AgentHub 统一客户端安装
echo ==========================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 未检测到 Python，请先安装 Python 3.10+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

set SCRIPT_DIR=%~dp0
set VENV_DIR=%SCRIPT_DIR%.venv

echo 创建虚拟环境...
python -m venv "%VENV_DIR%"
if %errorlevel% neq 0 (
    echo 虚拟环境创建失败
    pause
    exit /b 1
)

call "%VENV_DIR%\Scripts\activate.bat"

echo 安装依赖...
python -m pip install --upgrade pip
pip install -r "%SCRIPT_DIR%requirements.txt"
if %errorlevel% neq 0 (
    echo 依赖安装失败，请检查网络或手动执行 pip install -r requirements.txt
    pause
    exit /b 1
)

echo.
echo 安装完成。运行 run.bat，输入平台 API Key 即可启动客户端。
pause
