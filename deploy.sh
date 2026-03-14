#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
#  Healthcare Risk Prediction — Production deployment script
#  Usage:
#    ./deploy.sh                     # app + nginx
#    ./deploy.sh --with-monitoring   # app + nginx + prometheus + grafana
# ─────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"

# ── Colours ──────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}✅  $1${NC}"; }
warn()  { echo -e "${YELLOW}⚠️   $1${NC}"; }
error() { echo -e "${RED}❌  $1${NC}"; exit 1; }

# ── Pre-flight checks ───────────────────────────────────────
command -v docker >/dev/null 2>&1 || error "Docker is not installed"
docker compose version >/dev/null 2>&1 || error "Docker Compose V2 is required"

# ── SSL certificate check ───────────────────────────────────
SSL_DIR="$SCRIPT_DIR/nginx/ssl"
if [ ! -f "$SSL_DIR/fullchain.pem" ] || [ ! -f "$SSL_DIR/privkey.pem" ]; then
    warn "SSL certificates not found in nginx/ssl/"
    echo "    For production: follow nginx/ssl/README.md to set up Let's Encrypt"
    echo "    For testing: generating self-signed certificate..."
    mkdir -p "$SSL_DIR"
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "$SSL_DIR/privkey.pem" \
        -out "$SSL_DIR/fullchain.pem" \
        -subj "/CN=localhost" 2>/dev/null
    info "Self-signed certificate created"
fi

# ── Parse arguments ──────────────────────────────────────────
PROFILES=""
for arg in "$@"; do
    case $arg in
        --with-monitoring)
            PROFILES="--profile monitoring"
            ;;
        --dev)
            PROFILES="--profile dev"
            ;;
        *)
            warn "Unknown argument: $arg"
            ;;
    esac
done

# ── Build and deploy ─────────────────────────────────────────
echo ""
echo "─────────────────────────────────────────────"
echo "  🏗️   Building and deploying HealthPredict AI"
echo "─────────────────────────────────────────────"
echo ""

docker compose -f "$COMPOSE_FILE" $PROFILES build
docker compose -f "$COMPOSE_FILE" $PROFILES up -d

# ── Wait for health ──────────────────────────────────────────
echo ""
echo "⏳  Waiting for services to become healthy..."
sleep 5

for i in $(seq 1 20); do
    if curl -sf -k https://localhost/healthz -o /dev/null 2>/dev/null || \
       curl -sf http://localhost/healthz -o /dev/null 2>/dev/null; then
        break
    fi
    sleep 2
done

# ── Status ───────────────────────────────────────────────────
echo ""
echo "─────────────────────────────────────────────"

if curl -sf -k https://localhost/healthz -o /dev/null 2>/dev/null; then
    info "Application is healthy!"
    echo ""
    echo "  🌐  Application  →  https://localhost"
    echo "  📖  API Docs     →  https://localhost/api/docs"
elif curl -sf http://localhost/healthz -o /dev/null 2>/dev/null; then
    info "Application is healthy (HTTP mode)"
    echo ""
    echo "  🌐  Application  →  http://localhost"
    echo "  📖  API Docs     →  http://localhost/api/docs"
else
    warn "Application may still be starting. Check: docker compose logs"
fi

if echo "$PROFILES" | grep -q "monitoring"; then
    echo "  📊  Prometheus   →  http://localhost:9090"
    echo "  📈  Grafana      →  http://localhost:3000  (admin / healthpredict)"
fi

echo ""
echo "─────────────────────────────────────────────"
echo "  Logs:    docker compose logs -f"
echo "  Stop:    docker compose down"
echo "─────────────────────────────────────────────"
echo ""
