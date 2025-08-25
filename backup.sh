#!/bin/bash
# Automated backup script for PressVPN

BACKUP_DIR="/opt/backups"
PROJECT_DIR="/opt/remnawave-tg-bot"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/remnawave_backup_$DATE.tar.gz"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Create compressed backup
tar -czf "$BACKUP_FILE" -C "$PROJECT_DIR" .

# Keep only last 7 backups
ls -t "$BACKUP_DIR"/remnawave_backup_*.tar.gz | tail -n +8 | xargs -r rm

# Backup database
docker exec remnawave-tg-shop-db pg_dump -U postgres pressvpn_shop > "$BACKUP_DIR/db_backup_$DATE.sql"

# Keep only last 7 database backups
ls -t "$BACKUP_DIR"/db_backup_*.sql | tail -n +8 | xargs -r rm

echo "$(date '+%Y-%m-%d %H:%M:%S') - Backup completed: $BACKUP_FILE" >> "/var/log/remnawave_backup.log"
