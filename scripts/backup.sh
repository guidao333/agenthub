#!/bin/bash
# AgentHub Daily Backup Script
# Run via cron: 0 3 * * * /opt/agenthub/scripts/backup.sh

BACKUP_DIR="/opt/agenthub/backups"
DATE=$(date +%Y-%m-%d)
mkdir -p $BACKUP_DIR

# Backup SQLite database
cp /opt/agenthub/data/agenthub.db "$BACKUP_DIR/agenthub-$DATE.db"

# Compress
gzip -f "$BACKUP_DIR/agenthub-$DATE.db"

# Keep only last 30 days
find $BACKUP_DIR -name "agenthub-*.db.gz" -mtime +30 -delete

echo "$(date): Backup completed - agenthub-$DATE.db.gz" >> /opt/agenthub/logs/backup.log
