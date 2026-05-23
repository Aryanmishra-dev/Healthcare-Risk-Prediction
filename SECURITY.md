# Security Policy

HealthPredict AI handles medical-style inputs and must be deployed with a conservative security posture.

## Supported Deployment

- Production traffic should terminate TLS at the platform or reverse proxy.
- Set `APP_ENV=production`, `JWT_SECRET_KEY`, `API_KEY`, `CORS_ORIGINS`, `TRUSTED_HOSTS`, and `DATABASE_URL` in the hosting provider.
- Do not commit real `.env` files, databases, model binaries, uploaded PDFs, or secrets.

## Reporting Issues

Please report suspected vulnerabilities privately to the repository maintainer before public disclosure. Include reproduction steps, affected endpoints, and relevant logs with secrets redacted.

## Additional Details

See [docs/SECURITY.md](docs/SECURITY.md) for the deployment security architecture and checklist.
