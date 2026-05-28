@echo off
chcp 65001 >nul
setlocal

echo ==========================================
echo   AgentHub Client EXE Build
echo ==========================================

cd /d "%~dp0"

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 未检测到 Python，无法构建。
    exit /b 1
)

python -c "import PyInstaller" >nul 2>&1
if %errorlevel% neq 0 (
    echo 正在安装 PyInstaller...
    python -m pip install pyinstaller
    if %errorlevel% neq 0 exit /b 1
)

echo 正在打包 AgentHubClient.exe...
pyinstaller build.spec --clean --noconfirm
if %errorlevel% neq 0 (
    echo 打包失败。
    exit /b 1
)

if exist "dist\AgentHubClient.exe" (
    echo.
    echo 打包完成: %cd%\dist\AgentHubClient.exe
    echo 客户电脑无需安装 Python，直接运行该 EXE 即可启动本地工作台。
) else (
    echo 未找到输出文件 dist\AgentHubClient.exe
    exit /b 1
)

endlocal
