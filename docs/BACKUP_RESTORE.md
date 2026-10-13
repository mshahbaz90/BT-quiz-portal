# BreakThru Assessments — Backup & Disaster Recovery Guide

## 1. PostgreSQL Database Backups

### Automated Daily Cron Dump
Create a backup script `/usr/local/bin/backup_breakthru.sh`:
```bash
#!/bin/bash
BACKUP_DIR="/var/backups/breakthru"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
mkdir -p "$BACKUP_DIR"

# Dump database compressed
pg_dump -U breakthru_user -h localhost breakthru_db | gzip > "$BACKUP_DIR/db_$TIMESTAMP.sql.gz"

# Retain last 30 days of backups
find "$BACKUP_DIR" -type f -name "db_*.sql.gz" -mtime +30 -delete
```

Set executable permission and add to crontab:
```bash
chmod +x /usr/local/bin/backup_breakthru.sh
# Run every night at 2:00 AM
0 2 * * * /usr/local/bin/backup_breakthru.sh
```

## 2. Restoring from Backup

To restore from a backup file:
```bash
# Decompress and restore
gunzip -c /var/backups/breakthru/db_YYYYMMDD_HHMMSS.sql.gz | psql -U breakthru_user -d breakthru_db
```

## 3. Media Files Backup
Include the media directory in your backup routine:
```bash
tar -czf "$BACKUP_DIR/media_$TIMESTAMP.tar.gz" -C /var/www/breakthru-portal media
```
