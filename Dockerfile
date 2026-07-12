# ── Stage 1: Builder ──────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && \
    apt-get install -y --no-install-recommends libgomp1 gcc python3-dev && \
    rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: Runtime ─────────────────────────────────────────────────────
FROM python:3.11-slim

LABEL org.opencontainers.image.title="HealthPredict AI" \
      org.opencontainers.image.description="AI-powered clinical risk prediction (Diabetes, Heart Disease, Lung Cancer)" \
      org.opencontainers.image.version="3.0.0" \
      org.opencontainers.image.source="https://github.com/theogengineer/Healthcare_risk_prediction" \
      org.opencontainers.image.licenses="MIT"

# System deps (XGBoost needs libgomp)
RUN apt-get update && \
    apt-get install -y --no-install-recommends libgomp1 curl && \
    rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Create non-root user
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/sh --create-home appuser

WORKDIR /app
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Copy application code securely
COPY --chown=appuser:appuser backend/ ./backend/
COPY --chown=appuser:appuser frontend/ ./frontend/
COPY --chown=appuser:appuser ml/ ./ml/
COPY --chown=appuser:appuser shared/ ./shared/
COPY --chown=appuser:appuser config/ ./config/
COPY --chown=appuser:appuser data/ ./data/
COPY --chown=appuser:appuser monitoring/ ./monitoring/

USER appuser

EXPOSE 8000

# Health check — probes /healthz (the correct endpoint)
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1

# 2 workers: minimum viable concurrency for production.
# Scale to 2*$(nproc)+1 in production orchestration.
CMD ["gunicorn", "backend.app.main:app", "-w", "2", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000", "--timeout", "120", "--keep-alive", "30", "--worker-tmp-dir", "/dev/shm", "--access-logfile", "-", "--error-logfile", "-"]
