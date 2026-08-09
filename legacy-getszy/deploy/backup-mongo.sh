#!/bin/bash
# ================================================================
# MongoDB Backup Script for Getszy
# Run via cron: 0 2 * * * /opt/getszy/legacy-getszy/deploy/backup-mongo.sh
# ================================================================
set -euo pipefail

BACKUP_DIR="/opt/getszy/backups/mongo"
CONTAINER="getszy-mongo"
DB="getszy_db"
RETENTION_DAYS=7
DATE=$(date +%Y%m%d_%H%M%S)
KEEP_WEEKLY=4

mkdir -p "$BACKUP_DIR/daily" "$BACKUP_DIR/weekly"

echo "=== MongoDB Backup $(date) ==="

# Daily backup
docker exec "$CONTAINER" mongodump --db="$DB" --archive --gzip > "$BACKUP_DIR/daily/$DATE.gz"
DAILY_SIZE=$(du -sh "$BACKUP_DIR/daily/$DATE.gz" | cut -f1)
echo "Daily backup: $BACKUP_DIR/daily/$DATE.gz ($DAILY_SIZE)"

# Weekly backup (Sunday)
if [ $(date +%u) -eq 7 ]; then
    cp "$BACKUP_DIR/daily/$DATE.gz" "$BACKUP_DIR/weekly/$DATE.gz"
    echo "Weekly backup: $BACKUP_DIR/weekly/$DATE.gz"
fi

# Cleanup old daily backups
find "$BACKUP_DIR/daily" -name "*.gz" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true

# Cleanup old weekly backups (keep last 4)
ls -t "$BACKUP_DIR/weekly"/*.gz 2>/dev/null | tail -n +$((KEEP_WEEKLY + 1)) | xargs rm -f 2>/dev/null || true

# Show disk usage
echo "=== Backup Disk Usage ==="
du -sh "$BACKUP_DIR"/*
echo ""
echo "=== Backup Complete ==="
