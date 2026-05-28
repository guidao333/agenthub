@echo off
chcp 65001 >nul
title AgentHub Unified Client

echo ==========================================
echo   AgentHub 统一客户端
echo ==========================================
echo.

set SCRIPT_DIR=%~dp0
set VENV_DIR=%SCRIPT_DIR%.venv

if exist "%VENV_DIR%\Scripts\activate.bat" (
    call "%VENV_DIR%\Scripts\activate.bat"
)

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 未检测到 Python，请先安装 Python 3.10+，或运行 install.bat。
    pause
    exit /b 1
)

if not exist "%SCRIPT_DIR%requirements.txt" (
    echo 客户端文件不完整，请重新下载统一客户端。
    pause
    exit /b 1
)

set SERVER=wss://www.agenthub.wang
echo.
echo 正在连接 %SERVER%
echo 按 Ctrl+C 可停止客户端。
echo 本地工作台启动后会在窗口中显示访问地址。
echo 如未绑定 API Key，请打开本地工作台填写。
echo.
python "%SCRIPT_DIR%main.py" --server "%SERVER%"
pause
