#!/bin/bash
set -e

# Backup Configuration
BACKUP_DIR="${BACKUP_DIR:-/backups}"
DB_CONTAINER="${DB_CONTAINER:-postgres-db}"
DB_USER="${DB_USER:-admin}"
DB_NAME="${DB_NAME:-healthcare_audit}"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/db_backup_${TIMESTAMP}.sql.gz"

mkdir -p "${BACKUP_DIR}"

echo "Starting database backup for ${DB_NAME}..."
docker exec -t "${DB_CONTAINER}" pg_dump -U "${DB_USER}" -d "${DB_NAME}" -F c | gzip > "${BACKUP_FILE}"

echo "Backup completed: ${BACKUP_FILE}"

# Optional: Cleanup backups older than 7 days
find "${BACKUP_DIR}" -name "db_backup_*.sql.gz" -type f -mtime +7 -exec rm {} \;
echo "Old backups cleaned up."
