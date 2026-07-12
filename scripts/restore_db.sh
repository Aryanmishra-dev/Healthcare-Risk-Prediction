#!/bin/bash
set -e

if [ -z "$1" ]; then
  echo "Usage: $0 <path_to_backup_file.sql.gz>"
  exit 1
fi

BACKUP_FILE="$1"
DB_CONTAINER="${DB_CONTAINER:-postgres-db}"
DB_USER="${DB_USER:-admin}"
DB_NAME="${DB_NAME:-healthcare_audit}"

if [ ! -f "${BACKUP_FILE}" ]; then
  echo "Backup file not found: ${BACKUP_FILE}"
  exit 1
fi

echo "Warning: This will overwrite the existing database '${DB_NAME}'."
read -p "Are you sure you want to proceed? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo "Restore aborted."
    exit 1
fi

echo "Restoring database ${DB_NAME} from ${BACKUP_FILE}..."
gunzip -c "${BACKUP_FILE}" | docker exec -i "${DB_CONTAINER}" pg_restore -U "${DB_USER}" -d "${DB_NAME}" --clean --if-exists

echo "Restore completed successfully."
