# Disaster Recovery Plan

## Overview
This document outlines the Disaster Recovery (DR) procedures for the HealthPredict AI platform.

## 1. Database Backups
### Automated Backups
Database backups should be scheduled via a daily cron job using `scripts/backup_db.sh`.
```bash
# Crontab example for daily backup at 2 AM
0 2 * * * /path/to/project/scripts/backup_db.sh
```

### Manual Backup
To manually backup the database:
```bash
./scripts/backup_db.sh
```

## 2. Database Restoration
To restore a backup file to the active database container:
> [!WARNING]
> This will overwrite all current database content.
```bash
./scripts/restore_db.sh /backups/db_backup_20260712_020000.sql.gz
```

## 3. MLflow Artifacts Backup
All MLflow artifacts and models are stored in the `/mlruns` volume.
To backup this volume:
```bash
docker run --rm --volumes-from mlflow-server -v $(pwd):/backup ubuntu tar cvf /backup/mlflow_backup.tar /mlruns
```

## 4. Configuration Backup
Ensure that `.env` is backed up securely (e.g., in a secure vault or password manager) as it contains secrets necessary to recover the deployment state.

## 5. Recovery Time Objective (RTO) and Recovery Point Objective (RPO)
- **RTO**: Target recovery time is < 15 minutes, provided infrastructure is available.
- **RPO**: Target data loss is < 24 hours (based on daily backups).
