#!/bin/bash
# AgentHub SSL 证书申请脚本
# 前提: Nginx 已安装并运行, DNS 已指向本机
# 用法: bash setup_ssl.sh

set -e

DOMAIN="www.agenthub.wang"
EMAIL="460552193@qq.com"
WEBROOT="/var/www/certbot"

echo "========================================="
echo "  申请 SSL 证书: ${DOMAIN}"
echo "========================================="

# 确认 Nginx 在运行
systemctl status nginx --no-pager -l || systemctl start nginx

# 确认 webroot 目录存在
mkdir -p ${WEBROOT}

# 申请证书（standalone 模式不可用因为端口映射非标准，用 webroot）
echo "[1/3] 申请证书..."
certbot certonly \
    --webroot \
    --webroot-path=${WEBROOT} \
    --domain ${DOMAIN} \
    --domain agenthub.wang \
    --email ${EMAIL} \
    --agree-tos \
    --non-interactive \
    --rsa-key-size 2048

echo "[2/3] 配置 Nginx HTTPS..."
cat > /etc/nginx/sites-available/agenthub << NGINX_CONF
# HTTP → HTTPS 重定向
server {
    listen 80;
    server_name www.agenthub.wang agenthub.wang;
    
    location /.well-known/acme-challenge/ {
        root ${WEBROOT};
    }
    
    location / {
        return 301 https://\$host\$request_uri;
    }
}

# HTTPS 主服务
server {
    listen 443 ssl http2;
    server_name www.agenthub.wang agenthub.wang;
    
    ssl_certificate /etc/letsencrypt/live/${DOMAIN}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${DOMAIN}/privkey.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # 安全头
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # 前端静态文件
    location / {
        root /opt/agenthub/frontend/dist;
        try_files \$uri \$uri/ /index.html;
        expires 1h;
        add_header Cache-Control "public, immutable";
    }
    
    # 后端 API
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 60s;
        proxy_send_timeout 60s;
    }
    
    # 对话 SSE 流式（不缓冲）
    location /api/v1/chat/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_buffering off;
        proxy_cache off;
        proxy_set_header Connection '';
        proxy_http_version 1.1;
        chunked_transfer_encoding off;
        proxy_read_timeout 300s;
    }
    
    # 桥接 API
    location /api/v1/bridge/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_read_timeout 120s;
    }
    
    # 静态资源缓存
    location /assets/ {
        root /opt/agenthub/frontend/dist;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
NGINX_CONF

echo "[3/3] 测试并重载 Nginx..."
nginx -t && systemctl reload nginx

# 设置自动续期（certbot 已自动添加 cron/renew timer）
echo "设置证书自动续期..."
systemctl enable --now certbot.timer 2>/dev/null || true

# 测试续期流程
certbot renew --dry-run 2>/dev/null && echo "✅ 自动续期测试通过" || echo "⚠️ 续期测试失败，请手动检查"

echo ""
echo "========================================="
echo "  ✅ SSL 证书配置完成！"
echo "========================================="
echo ""
echo "  访问地址: https://www.agenthub.wang:1443"
echo "  证书位置: /etc/letsencrypt/live/${DOMAIN}/"
echo "  自动续期: certbot.timer 已启用"
