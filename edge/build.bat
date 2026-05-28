@echo off
chcp 65001 >nul
REM AgentHub Edge 一键打包脚本

echo ==========================================
echo   AgentHub Edge - 打包 Windows EXE
echo ==========================================

cd /d "%~dp0"

REM 检查依赖
python -c "import ultralytics; import cv2; import psutil; import PyInstaller" 2>nul
if %errorlevel% neq 0 (
    echo 📦 安装依赖...
    pip install ultralytics opencv-python psutil requests pyinstaller
)

REM 下载模型（如果不存在）
if not exist "models\yolov8n.pt" (
    echo 📥 下载 YOLOv8n 模型...
    mkdir models 2>nul
    python -c "from ultralytics import YOLO; YOLO('yolov8n.pt'); import shutil; shutil.copy('yolov8n.pt', 'models/yolov8n.pt')"
    if exist "yolov8n.pt" del "yolov8n.pt"
)

REM 打包
echo 📦 开始打包（可能需要几分钟）...
pyinstaller build.spec --clean --noconfirm

if %errorlevel% equ 0 (
    echo.
    echo ✅ 打包成功！
    echo 📁 输出: dist\AgentHubEdge.exe
    echo.
    echo 使用方法:
    echo   1. 将 dist\AgentHubEdge.exe 复制到客户电脑
    echo   2. 双击运行
    echo   3. 首次运行输入平台地址和API Key
    echo.
) else (
    echo ❌ 打包失败，请检查错误信息
)

pause
