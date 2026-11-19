#!/usr/bin/env bash
set -euo pipefail
STAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=${BACKUP_DIR:-/var/backups/silver}
mkdir -p "$BACKUP_DIR"
set -a; . ./.env; set +a
docker exec silver_db pg_dump -U "${DB_USER}" "${DB_NAME}" | gzip > "$BACKUP_DIR/db_${STAMP}.sql.gz"
tar czf "$BACKUP_DIR/media_${STAMP}.tar.gz" -C backend media 2>/dev/null || true
find "$BACKUP_DIR" -type f -mtime +14 -delete
echo "Backup done: $STAMP"