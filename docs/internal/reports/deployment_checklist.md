# Deployment Checklist — HealthPredict AI (RC2)

**Version:** 3.1.0 (RC2) | **Date:** 2026-07-12

Use this checklist for every production deployment. Check every item before going live.

---

## Pre-Deployment

### Environment Variables

| Variable | Required | Notes |
|----------|----------|-------|
| `APP_ENV` | ✅ | Must be `production` |
| `DATABASE_URL` | ✅ | `postgresql+asyncpg://...` |
| `SYNC_DATABASE_URL` | ✅ | `postgresql://...` (synchronous Alembic) |
| `JWT_SECRET_KEY` | ✅ | ≥ 32 chars, cryptographically random |
| `API_KEY` | ✅ | ≥ 32 chars, cryptographically random |
| `REDIS_URL` | ✅ | Required for distributed rate limiting |
| `EMAIL_BACKEND` | ✅ | Set to `smtp` for real email delivery |
| `SMTP_HOST` | ✅ (if smtp) | SMTP relay hostname |
| `SMTP_PORT` | ✅ (if smtp) | 587 (STARTTLS) or 465 (TLS) |
| `SMTP_USERNAME` | ✅ (if smtp) | SMTP credential |
| `SMTP_PASSWORD` | ✅ (if smtp) | SMTP credential (never commit) |
| `EMAIL_FROM_ADDRESS` | ✅ | Sender address (must be verified in your email provider) |
| `APP_BASE_URL` | ✅ | Full public URL e.g. `https://app.yourdomain.com` |
| `CORS_ORIGINS` | ✅ | Comma-separated allowed origins |
| `TRUSTED_HOSTS` | ✅ | Comma-separated trusted host headers |
| `MLFLOW_TRACKING_URI` | ⚠️ | Point to persistent MLflow server, not `file://` |

### Generate Secrets

```bash
# Generate API_KEY
python -c "import secrets; print(secrets.token_urlsafe(48))"

# Generate JWT_SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"
```

### Database

- [ ] Run Alembic migrations on target database:
  ```bash
  cd backend && alembic upgrade head
  ```
- [ ] Verify migration 0010 (performance indexes) applied:
  ```sql
  SELECT indexname FROM pg_indexes WHERE tablename = 'prediction_audit_logs';
  -- Should include: ix_prediction_audit_logs_user_id, _disease_model, _created_at
  ```
- [ ] Confirm `pool_size=10, max_overflow=20` in DB engine config

### Image Build

- [ ] Build with no cache to pick up requirement changes:
  ```bash
  docker build --no-cache -t healthpredict-ai:rc2 .
  ```
- [ ] Verify HEALTHCHECK points to `/healthz`:
  ```bash
  docker inspect healthpredict-ai:rc2 | grep -A5 Healthcheck
  ```
- [ ] Verify gunicorn starts with `-w 2`:
  ```bash
  docker run --rm healthpredict-ai:rc2 bash -c "echo \$0"
  ```

### Security Validation

- [ ] Confirm CSP header present on responses:
  ```bash
  curl -sI https://app.yourdomain.com/healthz | grep -i "content-security-policy"
  ```
- [ ] Confirm HSTS header present:
  ```bash
  curl -sI https://app.yourdomain.com/ | grep -i "strict-transport-security"
  ```
- [ ] Test rate limiting active:
  ```bash
  for i in $(seq 1 65); do
    curl -s -o /dev/null -w "%{http_code}" -X POST https://app.yourdomain.com/auth/login \
      -H "Content-Type: application/json" \
      -d '{"email":"x@x.com","password":"x"}'
    echo ""
  done
  # Should see 429 responses after 60 requests
  ```
- [ ] Test password reset email delivers:
  ```bash
  curl -X POST https://app.yourdomain.com/auth/password-reset-request \
    -H "Content-Type: application/json" \
    -d '{"email":"your-test-account@yourdomain.com"}'
  # Check inbox for HTML password reset email
  ```

---

## Deployment

- [ ] Deploy with zero-downtime (blue/green or rolling)
- [ ] Run Alembic migrations before routing traffic to new version
- [ ] Confirm health check passes:
  ```bash
  curl -f https://app.yourdomain.com/healthz
  # Expected: {"status": "ok", ...}
  ```
- [ ] Confirm readiness endpoint:
  ```bash
  curl https://app.yourdomain.com/api/v1/health/ready
  ```

---

## Post-Deployment Verification

- [ ] Login flow works end-to-end
- [ ] Prediction endpoints return results
- [ ] Password reset email received (check inbox)
- [ ] Dashboard loads with correct data
- [ ] File upload accepted
- [ ] Report processing completes
- [ ] Model registry returns data at `/api/v1/models`
- [ ] No `ERROR` entries in application logs in first 5 minutes
- [ ] Prometheus metrics endpoint responding: `GET /metrics`

---

## Rollback

If deployment fails:

1. Route traffic back to previous version (blue/green) or roll back image tag
2. **No migration rollback needed** unless schema was changed (migrations 0001–0010 are additive)
3. If rollback to pre-0010 needed:
   ```bash
   alembic downgrade 0009
   ```
4. Verify health check passes on rolled-back version

---

## Monitoring Checklist (First 24 Hours)

- [ ] Application error rate < 0.1%
- [ ] P99 prediction latency < 2000 ms
- [ ] P99 DB query latency < 200 ms
- [ ] Redis hit rate for rate limiting > 99%
- [ ] Email delivery success rate (check SMTP provider dashboard)
- [ ] No unexpected 429 responses for legitimate users
- [ ] `exports_data/` directory size stable
- [ ] Container health check consistently HEALTHY

---

## Backup Checklist

- [ ] PostgreSQL: Automated daily snapshots configured (verify on cloud provider)
- [ ] Verify point-in-time recovery (PITR) enabled
- [ ] Test restore from latest snapshot in staging before production deployment
- [ ] MLflow artifacts: confirm S3 bucket versioning enabled
- [ ] `exports_data/` mounted on persistent volume (not ephemeral container storage)
