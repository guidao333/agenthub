@echo off
chcp 65001 >nul
title AgentHub Edge - AI视觉推理盒子
echo ==========================================
echo   AgentHub Edge 启动器(绿色版)
echo   无需安装，本机有Python即可运行
echo ==========================================
echo.

REM 检测Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 未检测到Python！
    echo 请先安装 Python 3.9+：https://www.python.org/downloads/
    echo 安装时务必勾选 "Add Python to PATH"
    pause
    exit /b 1
)

echo ✅ Python 已检测到
python --version
echo.

REM 检查ultralytics是否安装
python -c "import ultralytics" >nul 2>&1
if %errorlevel% neq 0 (
    echo 📦 首次运行需要安装依赖，正在安装...
    python -m pip install --upgrade pip -q
    pip install ultralytics opencv-python numpy requests psutil -q
    if %errorlevel% neq 0 (
        echo ❌ 安装失败，请尝试手动运行:
        echo pip install ultralytics opencv-python numpy requests psutil
        pause
        exit /b 1
    )
    echo ✅ 依赖安装完成
) else (
    echo ✅ 依赖已就绪
)
echo.

REM 显示菜单
echo ╔═══════════════════════════════════════════╗
echo ║            AgentHub Edge 菜单             ║
echo ╠═══════════════════════════════════════════╣
echo ║                                           ║
echo ║  1. 🔧  首次配置（连接平台 + 发现摄像头）   ║
echo ║  2. 🔍  ONVIF发现局域网摄像头               ║
echo ║  3. ▶  启动推理服务                         ║
echo ║  4. 📋  查看帮助                            ║
echo ║  0. ❌  退出                                ║
echo ║                                           ║
echo ╚═══════════════════════════════════════════╝
echo.
set /p choice="请选择 (0-4): "

if "%choice%"=="1" goto setup
if "%choice%"=="2" goto discover
if "%choice%"=="3" goto start
if "%choice%"=="4" goto help
if "%choice%"=="0" exit /b
goto end

:setup
echo.
echo ========== 首次配置 ==========
echo.
set /p server="平台地址 (如 https://www.agenthub.wang): "
set /p apikey="API Key (在平台购买后获取，暂无则留空): "
echo.
echo 📷 选择摄像头添加方式：
echo   1. 自动ONVIF发现
echo   2. 手动输入IP
set /p cam_mode="选择 (1/2): "

if "%cam_mode%"=="1" (
    echo.
    echo 🔍 正在搜索局域网摄像头...
    python main.py discover
    echo.
    echo 手动添加: python main.py add_camera --ip 192.168.x.x --username admin --password xxx
) else (
    set /p ip="摄像头IP: "
    set /p user="用户名 (默认admin): "
    if "%user%"=="" set user=admin
    set /p pwd="密码: "
    set /p port="端口 (默认554): "
    if "%port%"=="" set port=554
    set /p loc="位置说明 (如: 客厅): "
    
    python main.py setup --server "%server%" --api-key "%apikey%"
    if "%apikey%"=="" (
        echo ⚠️ 未设置API Key，跳过配置保存
    )
    echo.
    echo 摄像头手动添加后，运行选项3启动服务
)

goto end

:discover
echo.
echo 🔍 正在搜索局域网内的ONVIF摄像头...
python main.py discover
echo.
echo 按任意键返回菜单
pause >nul
goto menu

:start
echo.
echo ▶ 启动推理服务...
echo   按 Ctrl+C 停止
echo.
python main.py start
pause
goto menu

:help
echo.
echo ========== 使用说明 ==========
echo.
echo  AgentHub Edge 是AI视觉能力的边缘推理端
echo.
echo  完整使用流程:
echo   1. 登录 www.agenthub.wang 购买AI视觉能力
echo   2. 获取 API Key
echo   3. 在本机运行本启动器 → 选项1配置
echo   4. 系统自动发现摄像头 → 连接平台
echo   5. 开始AI检测 → 结果上报云端
echo.
echo  支持摄像头: 海康威视 / 大华 / TP-Link / 水星 / 天地伟业 / 宇视
echo  要求: 网络摄像机支持RTSP/ONVIF协议（2010年后基本都支持）
echo.
echo  手动命令:
echo    python main.py setup --server URL --api-key KEY   配置
echo    python main.py discover                            发现摄像头
echo    python main.py start                               启动服务
echo    python main.py version                             查看版本
echo.
pause
goto menu

:end
echo.
echo 按任意键退出...
pause >nul
