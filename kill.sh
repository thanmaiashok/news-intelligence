#!/usr/bin/env bash

export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$PROJECT_DIR/.logs"

RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m'

log()  { echo -e "${GREEN}[KILL]${NC}  $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC}  $1"; }

kill_pid() {
  local name="$1"
  local pidfile="$LOG_DIR/$2.pid"
  if [ -f "$pidfile" ]; then
    local pid
    pid=$(cat "$pidfile")
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" && log "Stopped $name (PID $pid)"
    else
      warn "$name PID $pid already stopped"
    fi
    rm -f "$pidfile"
  else
    warn "$name pidfile not found — may already be stopped"
  fi
}

echo ""
echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${RED}  Stopping News Intelligence System${NC}"
echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# ── Stop app processes ─────────────────────────────────────────────────────────
kill_pid "Frontend (Next.js)" "frontend"
kill_pid "FastAPI Backend"    "api"

# ── Kill any stray processes on those ports ───────────────────────────────────
for port in 3000 8001; do
  pids=$(lsof -ti tcp:"$port" 2>/dev/null || true)
  if [ -n "$pids" ]; then
    echo "$pids" | xargs kill -9 2>/dev/null && log "Killed stray process on port $port"
  fi
done

# ── Stop Docker infrastructure ────────────────────────────────────────────────
COMPOSE_FILE="$PROJECT_DIR/deployment/docker/docker-compose.yml"
if [ -f "$COMPOSE_FILE" ]; then
  log "Stopping Docker services..."
  docker compose -f "$COMPOSE_FILE" stop 2>/dev/null && log "Docker services stopped."
else
  warn "docker-compose.yml not found — skipping Docker stop"
fi

echo ""
echo -e "${GREEN}All services stopped.${NC}"
echo -e "Data volumes preserved. Run ${GREEN}./start.sh${NC} to restart."
echo ""
