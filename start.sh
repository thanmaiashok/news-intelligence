#!/usr/bin/env bash
set -e

export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$PROJECT_DIR/.logs"
mkdir -p "$LOG_DIR"
mkdir -p "$PROJECT_DIR/.data/faiss"

API_PORT="${API_PORT:-8001}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
BIND_HOST="${BIND_HOST:-0.0.0.0}"

detect_server_host() {
  if [ -n "${SERVER_HOST:-}" ]; then
    echo "$SERVER_HOST"
    return
  fi

  if command -v tailscale &>/dev/null; then
    local ts_ip
    ts_ip="$(tailscale ip -4 2>/dev/null | head -n 1 || true)"
    if [ -n "$ts_ip" ]; then
      echo "$ts_ip"
      return
    fi
  fi

  if command -v hostname &>/dev/null; then
    local lan_ip
    lan_ip="$(hostname -I 2>/dev/null | awk '{print $1}' || true)"
    if [ -n "$lan_ip" ]; then
      echo "$lan_ip"
      return
    fi
  fi

  echo "127.0.0.1"
}

SERVER_HOST="$(detect_server_host)"
API_BASE_URL="http://${SERVER_HOST}:${API_PORT}/api/v1"
WS_URL="ws://${SERVER_HOST}:${API_PORT}/ws/feed"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log()  { echo -e "${GREEN}[START]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC}  $1"; }
err()  { echo -e "${RED}[ERR]${NC}   $1"; }

# ── 1. Copy .env if missing ────────────────────────────────────────────────────
if [ ! -f "$PROJECT_DIR/.env" ]; then
  if [ -f "$PROJECT_DIR/.env.example" ]; then
    cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
    warn ".env not found — copied from .env.example. Edit credentials before production use."
  else
    err ".env missing and no .env.example found. Create .env first."
    exit 1
  fi
fi

# ── 2. Start infrastructure via Docker Compose ────────────────────────────────
log "Starting infrastructure (Kafka, Postgres, ClickHouse, Neo4j, Redis, MinIO, Kafka UI)..."
docker compose -f "$PROJECT_DIR/deployment/docker/docker-compose.yml" \
  up -d zookeeper kafka kafka-ui postgres clickhouse neo4j redis minio

# Health-check Postgres (fast check, no fixed sleep)
log "Waiting for Postgres..."
for i in {1..30}; do
  if docker exec "$(docker compose -f "$PROJECT_DIR/deployment/docker/docker-compose.yml" ps -q postgres 2>/dev/null)" \
       pg_isready -U news -d newsdb &>/dev/null 2>&1; then
    log "Postgres ready."
    break
  fi
  [ "$i" -eq 30 ] && warn "Postgres health check timed out — continuing anyway."
  sleep 2
done

# Health-check Kafka
log "Waiting for Kafka..."
for i in {1..20}; do
  if docker exec "$(docker compose -f "$PROJECT_DIR/deployment/docker/docker-compose.yml" ps -q kafka 2>/dev/null | head -1)" \
       kafka-broker-api-versions --bootstrap-server localhost:9092 &>/dev/null 2>&1; then
    log "Kafka ready."
    break
  fi
  [ "$i" -eq 20 ] && warn "Kafka health check timed out — continuing anyway."
  sleep 3
done

# ── 3. Python venv + deps ─────────────────────────────────────────────────────
VENV="$PROJECT_DIR/backend/.venv"
if [ ! -d "$VENV" ]; then
  log "Creating Python venv (python3.12)..."
  python3.12 -m venv "$VENV"
fi

log "Installing Python dependencies..."
if command -v uv &>/dev/null; then
  uv pip install -r "$PROJECT_DIR/backend/requirements.txt" --python "$VENV/bin/python" --quiet
else
  "$VENV/bin/pip" install --quiet --upgrade pip
  "$VENV/bin/pip" install --quiet -r "$PROJECT_DIR/backend/requirements.txt"
fi

# spaCy model
if ! "$VENV/bin/python" -c "import spacy; spacy.load('en_core_web_sm')" &>/dev/null 2>&1; then
  log "Downloading spaCy model..."
  "$VENV/bin/python" -m spacy download en_core_web_sm --quiet
fi

# Playwright browsers
if ! "$VENV/bin/python" -c "from playwright.sync_api import sync_playwright; p=sync_playwright().start(); p.chromium.launch(); p.stop()" &>/dev/null 2>&1; then
  log "Installing Playwright Chromium..."
  "$VENV/bin/playwright" install chromium --quiet 2>/dev/null || true
fi

# Pre-download embedding model so first article has no delay
log "Pre-warming embedding model..."
"$VENV/bin/python" -c "
from sentence_transformers import SentenceTransformer
SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
print('Embedding model ready.')
" 2>/dev/null || warn "Embedding model pre-warm failed — will download on first use"

# ── 4. Start FastAPI backend ──────────────────────────────────────────────────
log "Starting FastAPI backend (${BIND_HOST}:${API_PORT})..."
cd "$PROJECT_DIR"
PYTHONPATH="$PROJECT_DIR" "$VENV/bin/uvicorn" \
  backend.api.main:app \
  --host "$BIND_HOST" \
  --port "$API_PORT" \
  --loop uvloop \
  > "$LOG_DIR/api.log" 2>&1 &
echo $! > "$LOG_DIR/api.pid"
log "API PID: $(cat "$LOG_DIR/api.pid") → logs: $LOG_DIR/api.log"

# ── 5. Crawler ────────────────────────────────────────────────────────────────
log "Crawler auto-starts with API — no action needed"

# ── 6. Frontend ───────────────────────────────────────────────────────────────
FRONTEND_DIR="$PROJECT_DIR/frontend"
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
  log "Installing frontend dependencies (npm install)..."
  cd "$FRONTEND_DIR" && npm install --silent
fi

log "Starting Next.js frontend (${BIND_HOST}:${FRONTEND_PORT})..."
cd "$FRONTEND_DIR"
NEXT_PUBLIC_API_URL="$API_BASE_URL" \
NEXT_PUBLIC_WS_URL="$WS_URL" \
npm run dev -- -H "$BIND_HOST" -p "$FRONTEND_PORT" > "$LOG_DIR/frontend.log" 2>&1 &
echo $! > "$LOG_DIR/frontend.pid"
log "Frontend PID: $(cat "$LOG_DIR/frontend.pid") → logs: $LOG_DIR/frontend.log"

# ── 7. Summary ────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  News Intelligence System — RUNNING${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  Dashboard   →  http://${SERVER_HOST}:${FRONTEND_PORT}"
echo -e "  API         →  http://${SERVER_HOST}:${API_PORT}"
echo -e "  API Docs    →  http://${SERVER_HOST}:${API_PORT}/docs"
echo -e "  Kafka UI    →  http://localhost:8080"
echo -e "  Neo4j       →  http://localhost:7474  (neo4j / newspass123)"
echo -e "  MinIO       →  http://localhost:9001  (minioadmin / minioadmin)"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  Logs dir    →  $LOG_DIR"
echo -e "  FAISS data  →  $PROJECT_DIR/.data/faiss"
echo -e "  Stop all    →  ./kill.sh"
echo ""
