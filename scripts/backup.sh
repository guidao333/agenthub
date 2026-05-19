#!/bin/bash
# AgentHub 数据库备份脚本
# 配合 cron 每日执行
# 用法: bash backup.sh

set -e

BACKUP_DIR="/opt/agenthub/backups"
DB_PATH="/opt/agenthub/data/agenthub.db"
CAP_DIR="/opt/agenthub/capabilities"
DATE=$(date +%Y%m%d_%H%M%S)
RETAIN_DAYS=30

mkdir -p ${BACKUP_DIR}

# 1. 备份数据库
if [ -f "${DB_PATH}" ]; then
    # SQLite 安全备份（使用 .backup 命令保证一致性）
    sqlite3 "${DB_PATH}" ".backup '${BACKUP_DIR}/agenthub_${DATE}.db'"
    gzip "${BACKUP_DIR}/agenthub_${DATE}.db"
    echo "✅ 数据库备份: agenthub_${DATE}.db.gz"
else
    echo "⚠️ 数据库文件不存在: ${DB_PATH}"
fi

# 2. 备份能力包（增量）
if [ -d "${CAP_DIR}" ]; then
    tar czf "${BACKUP_DIR}/capabilities_${DATE}.tar.gz" -C "$(dirname ${CAP_DIR})" "$(basename ${CAP_DIR})"
    echo "✅ 能力包备份: capabilities_${DATE}.tar.gz"
fi

# 3. 清理旧备份
find ${BACKUP_DIR} -name "*.gz" -mtime +${RETAIN_DAYS} -delete
echo "✅ 清理 ${RETAIN_DAYS} 天前的旧备份"

# 4. 可选：同步到飞牛 NAS（如果网络可达）
# NAS_IP="172.16.88.2"
# ping -c 1 -W 2 ${NAS_IP} >/dev/null 2>&1 && \
#     scp ${BACKUP_DIR}/agenthub_${DATE}.db.gz admin@${NAS_IP}:/volume1/backups/agenthub/ 2>/dev/null && \
#     echo "✅ 已同步到飞牛 NAS" || echo "⚠️ NAS 不可达，跳过同步"

echo "备份完成: $(date)"
