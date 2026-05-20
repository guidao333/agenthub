#!/bin/bash
# AgentHub Edge 一键安装脚本 (Linux/macOS)
set -e

echo "=========================================="
echo "  AgentHub Edge - AI视觉推理盒子 安装"
echo "=========================================="

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到 Python3，请先安装 Python 3.9+"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "✅ Python $PYTHON_VERSION"

# 创建虚拟环境
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

echo "📦 创建虚拟环境..."
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

# 安装依赖
echo "📦 安装依赖（首次安装需要下载YOLO模型，可能需要几分钟）..."
pip install --upgrade pip
pip install -r "$SCRIPT_DIR/requirements.txt"

echo ""
echo "✅ 安装完成！"
echo ""
echo "使用方法:"
echo "  1. 交互式配置:  python main.py setup"
echo "  2. 命令行配置:  python main.py setup --server https://www.agenthub.wang --api-key YOUR_KEY"
echo "  3. 发现摄像头:  python main.py discover"
echo "  4. 启动服务:    python main.py start"
