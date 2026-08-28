# ── Stage 1: Builder ──────────────────────────────────────────────────────
FROM python:3.14-slim AS builder

WORKDIR /build

RUN apt-get update && \
    apt-get install -y --no-install-recommends libgomp1 gcc python3-dev curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt && \
    rm -rf /root/.cache/pip

RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    rm -rf /var/lib/apt/lists/*

COPY frontend/package.json frontend/package-lock.json /build/frontend/
WORKDIR /build/frontend
RUN npm ci && npm cache clean --force
COPY frontend/ /build/frontend/
RUN npm run build:css
WORKDIR /build


# ── Stage 2: Runtime ─────────────────────────────────────────────────────
FROM python:3.14-slim

LABEL org.opencontainers.image.title="HealthPredict AI" \
      org.opencontainers.image.description="AI-powered clinical risk prediction (Diabetes, Heart Disease, Lung Cancer)" \
      org.opencontainers.image.version="3.0.0" \
      org.opencontainers.image.source="https://github.com/theogengineer/Healthcare_risk_prediction" \
      org.opencontainers.image.licenses="MIT"

RUN apt-get update && \
    apt-get install -y --no-install-recommends libgomp1 curl && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local

RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/sh --create-home appuser

WORKDIR /app
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY --chown=appuser:appuser backend/ ./backend/
COPY --from=builder --chown=appuser:appuser /build/frontend/ ./frontend/
COPY --chown=appuser:appuser ml/ ./ml/
COPY --chown=appuser:appuser shared/ ./shared/
COPY --chown=appuser:appuser config/ ./config/

RUN mkdir -p data/interim && chown -R appuser:appuser data

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1

CMD gunicorn backend.app.main:app -w 1 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:${PORT:-8000} --timeout 120 --worker-tmp-dir /dev/shm
