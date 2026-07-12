# Monitoring & Observability Guide

## Core Stack
- **Prometheus**: Time-series database that scrapes metrics from the FastAPI application and other components.
- **Grafana**: Data visualization layer used to build dashboards on top of Prometheus data.
- **MLflow**: Tracks model metrics, parameters, and artifacts.

## Accessing the Dashboards
1. Run `docker compose --profile monitoring up -d` to launch the monitoring stack.
2. Navigate to `http://localhost:3000` to access Grafana. Default credentials: `admin` / `<YOUR_GRAFANA_PASSWORD>` (set via `GRAFANA_PASSWORD` env variable; dev-only fallback is `dev-grafana-change-me`).

## Available Metrics
- **System Metrics**: CPU, memory, and container-level stats.
- **API Metrics**: Rate of requests (req/sec), P95/P99 latencies, error rates (HTTP 4xx/5xx).
- **Model Metrics**: Model drift and prediction distributions available via MLflow and custom Prometheus gauges exposed by the prediction pipeline.

## Alerting
Prometheus can be configured via `alertmanager` to dispatch webhooks or emails when error rates exceed threshold boundaries (e.g., Error Rate > 5% for 5 minutes).
