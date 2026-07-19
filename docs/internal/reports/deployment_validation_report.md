# Deployment Validation Report

## Nginx & Edge Proxy
- **Reverse Proxy**: Traffic hitting ports 80 and 443 routes effectively to the internal `web:8000` container.
- **Health Routes**: `/healthz` is successfully routed and responds with 200 OK without getting rate limited.
- **Static Assets**: `/static/` serves frontend assets effectively with long-lived `Cache-Control` headers (7 days).
- **Security Headers**: HSTS, CSP, and X-XSS-Protection headers are present in all Nginx responses.

## MLflow Integration
- **Artifacts**: MLflow successfully boots using the Postgres backend.
- **Connectivity**: The web application communicates seamlessly with MLflow via internal docker networking.
- **Persistence**: Metrics and models are properly persisted across container restarts in the `mlflow_artifacts` Docker volume.

## Monitoring
- **Prometheus**: Scrapes `/metrics` from the API successfully every 15s. All configured targets map to `UP`.
- **Grafana**: Boots properly and loads the provisioned dashboard automatically. Telemetry visualizes system stats and request distributions correctly.
- **Metrics Accuracy**: HTTP rate equations (e.g. `rate(http_requests_total[5m])`) align accurately with the Locust load testing footprint.

## Status
All deployment boundaries and integrations passed successfully.
