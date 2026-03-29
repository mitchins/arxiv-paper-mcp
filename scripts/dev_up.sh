#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

: "${ARXIV_DB_HOST_PATH:?Set ARXIV_DB_HOST_PATH to a readable host sqlite path}"
export ARXIV_CONFIG_HOST_PATH="${ARXIV_CONFIG_HOST_PATH:-$ROOT_DIR/config}"

COMPOSE_FILES="-f docker-compose.yml -f docker-compose.build.yml"
# shellcheck disable=SC2086
docker compose $COMPOSE_FILES build
# shellcheck disable=SC2086
docker compose $COMPOSE_FILES up -d --wait

PYTHON_BIN="python3"
if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
  PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
fi

"$PYTHON_BIN" scripts/smoke_runtime.py \
  --endpoint http://127.0.0.1:8000 \
  --iterations 7 \
  --query transformer \
  --search-timeout 180 \
  --startup-wait 60 \
  --warmup
