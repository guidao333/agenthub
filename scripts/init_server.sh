#!/bin/bash
# AgentHub 服务器初始化脚本
# 在全新 Debian 系统上执行
# 用法: bash init_server.sh

set -e

echo "========================================="
echo "  AgentHub 服务器初始化"
echo "========================================="

# 1. 系统更新
echo "[1/8] 系统更新..."
apt update && apt upgrade -y

# 2. 安装基础工具
echo "[2/8] 安装基础工具..."
apt install -y \
    curl wget git vim htop \
    openssh-server \
    nginx \
    python3 python3-pip python3-venv \
    certbot python3-certbot-nginx \
    ufw

# 3. 配置 SSH
echo "[3/8] 配置 SSH..."
SSH_PORT=${SSH_PORT:-22}
sed -i "s/^#Port 22/Port ${SSH_PORT}/" /etc/ssh/sshd_config
sed -i 's/^#PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config
systemctl enable --now sshd

# 4. 配置防火墙
echo "[4/8] 配置防火墙..."
ufw allow ${SSH_PORT}/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# 5. 创建项目目录
echo "[5/8] 创建项目目录..."
mkdir -p /opt/agenthub/{backend,frontend,capabilities,data,logs,backups,scripts,config}
mkdir -p /opt/agenthub/capabilities/.temp  # 能力运行临时目录
mkdir -p /var/www/certbot

# 6. 配置 Nginx（先配 HTTP，证书后面申请）
echo "[6/8] 配置 Nginx..."
cat > /etc/nginx/sites-available/agenthub << 'NGINX_CONF'
# HTTP - 证书验证 + 重定向
server {
    listen 80;
    server_name www.agenthub.wang agenthub.wang;
    
    # Let's Encrypt 验证
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    
    location / {
        return 301 https://$host$request_uri;
    }
}
NGINX_CONF

ln -sf /etc/nginx/sites-available/agenthub /etc/nginx/sites-enabled/agenthub
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl enable --now nginx

# 7. Python 虚拟环境
echo "[7/8] 创建 Python 虚拟环境..."
python3 -m venv /opt/agenthub/venv
source /opt/agenthub/venv/bin/activate
pip install --upgrade pip

# 8. 创建 systemd 服务
echo "[8/8] 创建 systemd 服务..."
cat > /etc/systemd/system/agenthub.service << 'SERVICE_CONF'
[Unit]
Description=AgentHub API Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/agenthub/backend
ExecStart=/opt/agenthub/venv/bin/python run.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
SERVICE_CONF

systemctl daemon-reload

echo ""
echo "========================================="
echo "  ✅ 基础环境安装完成！"
echo "========================================="
echo ""
echo "下一步："
echo "  1. 把代码部署到 /opt/agenthub/"
echo "  2. 安装 Python 依赖: source /opt/agenthub/venv/bin/activate && pip install -r /opt/agenthub/backend/requirements.txt"
echo "  3. 申请 SSL 证书: bash /opt/agenthub/scripts/setup_ssl.sh"
echo "  4. 启动服务: systemctl start agenthub"
