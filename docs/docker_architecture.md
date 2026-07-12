# Docker Architecture

## Container Strategy
The platform utilizes a multi-container Docker Compose architecture for local development and base production readiness.

### Multi-stage Dockerfile
The API is built using a multi-stage Dockerfile:
1. **Builder Stage**: Compiles Python packages and dependencies (like XGBoost via `libgomp1`) into a clean layer.
2. **Runtime Stage**: Copies the pre-compiled packages. Sets up a non-root user (`appuser`) for security. Exposes only port 8000 internally. Uses Gunicorn with Uvicorn workers for high concurrency.

### Docker Compose Services
1. **web**: The core FastAPI application. Reads from `.env`. Cannot be accessed directly from the host.
2. **db**: PostgreSQL 15 database container. Data is persisted to a Docker volume.
3. **redis**: Redis 7 cache. Used for session management and rate limiting.
4. **mlflow**: MLflow tracking server backed by the Postgres DB. Exposed internally on port 5000.
5. **nginx**: Reverse proxy. Handles rate limiting, SSL termination, static file serving, and routes traffic to `web`.
6. **prometheus & grafana**: Active only under the `monitoring` profile. Handles system telemetry.
