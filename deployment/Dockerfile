# ── Stage 1: Builder ──────────────────────────────────────────────────────
FROM python:3.13-slim AS builder

WORKDIR /build

RUN apt-get update && \
    apt-get install -y --no-install-recommends libgomp1 && \
    rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: Runtime ─────────────────────────────────────────────────────
FROM python:3.13-slim

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
ENV PYTHONPATH=/app

# Copy application code
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY ml/ ./ml/
COPY shared/ ./shared/
COPY config/ ./config/
COPY data/ ./data/
COPY monitoring/ ./monitoring/

# Own the app directory
RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# Health check using curl
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/api || exit 1

CMD ["gunicorn", "backend.app.main:app", "-w", "1", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000", "--timeout", "15", "--keep-alive", "30", "--access-logfile", "-", "--error-logfile", "-"]
