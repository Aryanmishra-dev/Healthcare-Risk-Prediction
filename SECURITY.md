# Security Architecture

This document describes the production security architecture for HealthPredict AI.

## Architecture

```
User Browser
     │
     ▼
   HTTPS (443)
     │
     ▼
┌──────────────────────┐
│   Nginx Reverse      │  • SSL termination
│   Proxy              │  • Rate limiting
│                      │  • Security headers
│                      │  • Request size limits
│                      │  • Static file serving
└──────────┬───────────┘
           │ (internal Docker network)
           ▼
┌──────────────────────┐
│   FastAPI Backend     │  • App-level rate limiting
│   (port 8000)        │  • CORS policy
│                      │  • Trusted host validation
│                      │  • Request-ID tracing
│                      │  • Structured logging
│                      │  • Prometheus metrics
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│   ML Models /        │
│   Database           │
└──────────────────────┘
```

## Security Layers

### Layer 1: Nginx Reverse Proxy
- **SSL/TLS** — TLSv1.2 and TLSv1.3 only
- **HTTP→HTTPS redirect** — all HTTP traffic redirected to HTTPS
- **Rate limiting** — 10 req/s for predictions, 20 req/s for API
- **Request size** — max 2MB payload
- **Security headers** — HSTS, X-Frame-Options, CSP, etc.
- **Port isolation** — only ports 80/443 exposed publicly
- **Dotfile blocking** — `.env`, `.git` etc. are blocked

### Layer 2: Docker Network Isolation
- FastAPI runs on an **internal Docker network** only
- Port 8000 is **not published** to the host
- Service-to-service communication via Docker DNS

### Layer 3: FastAPI Application
- **TrustedHostMiddleware** — rejects requests with spoofed Host headers
- **CORS policy** — only configured origins allowed (environment variable)
- **Rate limiting** — 60 req/min per IP (configurable)
- **X-Request-ID** — unique ID per request for traceability
- **Structured logging** — JSON logs with structlog
- **Non-root user** — application runs as `appuser` (UID 1000)

### Layer 4: Monitoring
- **Prometheus** — scrapes `/metrics` for request counts, latency, errors
- **Grafana** — visual dashboards with auto-provisioned data source
- **Health probes** — `/healthz` (liveness) and `/api/v1/health/ready` (readiness)

## Configuration

### Environment Variables

| Variable               | Default                                | Description                    |
|------------------------|----------------------------------------|--------------------------------|
| `CORS_ORIGINS`         | `https://yourdomain.com,...`           | Allowed CORS origins           |
| `TRUSTED_HOSTS`        | `localhost,127.0.0.1,yourdomain.com`   | Allowed Host header values     |
| `RATE_LIMIT_PER_MINUTE`| `60`                                   | App-level rate limit per IP    |
| `APP_ENV`              | `development`                          | `production` for JSON logging  |
| `LOG_LEVEL`            | `INFO`                                 | Logging verbosity              |

### Deployment Checklist

- [ ] Replace `yourdomain.com` in `docker-compose.yml` and `nginx/nginx.conf`
- [ ] Set up SSL certificates (see `nginx/ssl/README.md`)
- [ ] Configure firewall to block port 8000 externally
- [ ] Set `APP_ENV=production` in environment
- [ ] Update `CORS_ORIGINS` to your actual domain
- [ ] Update `TRUSTED_HOSTS` to your actual domain
- [ ] Review Grafana default password and change it
- [ ] Run `./deploy.sh --with-monitoring` to start all services

## Quick Start

```bash
# Development (HTTP only, with Nginx proxy)
docker compose --profile dev up -d

# Production (HTTPS)
./deploy.sh

# Production + Monitoring
./deploy.sh --with-monitoring
```
