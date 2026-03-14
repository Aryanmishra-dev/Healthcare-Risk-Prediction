# ── Stage 1: Builder ──────────────────────────────────────────────────────
FROM python:3.13-slim AS builder

WORKDIR /build

RUN apt-get update && \
    apt-get install -y --no-install-recommends libgomp1 && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
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

# Copy application code
COPY app/ ./app/
COPY fastapi_backend/ ./fastapi_backend/
COPY utils/ ./utils/
COPY models/ ./models/
COPY feature_store/ ./feature_store/
COPY scripts/ ./scripts/
COPY monitoring/ ./monitoring/

# Own the app directory
RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# Health check using curl
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/api || exit 1

CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "2", \
     "--timeout-keep-alive", "30", \
     "--proxy-headers", \
     "--forwarded-allow-ips", "*", \
     "--access-log"]
