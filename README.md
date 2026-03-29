# arxiv-paper-mcp

FastAPI + FastMCP search service over arXiv metadata using SQLite FTS5.

## What is included


## Recommended run path (Docker)

Use your existing SQLite file as a read-only mount.

```bash
export ARXIV_DB_HOST_PATH=/Volumes/data-2/deploy/arxiv-mcp/data/arxiv.db
export ARXIV_CONFIG_HOST_PATH=$PWD/config
bash scripts/dev_up.sh
```

Stop local Docker services:

```bash
bash scripts/dev_down.sh
```

Manual equivalent:

Published image platforms:

- `linux/amd64`
- `linux/arm64`
```bash
docker compose build
docker compose up -d --wait
python scripts/smoke_runtime.py --endpoint http://127.0.0.1:8000 --iterations 7 --query "transformer" --search-timeout 180 --startup-wait 60 --warmup
```

## API quick check

```bash
curl -fsS http://127.0.0.1:8000/health
```

```bash
curl -fsS -X POST http://127.0.0.1:8000/search \
  -H 'Content-Type: application/json' \
  -d '{"query":"transformer","limit":10}'
```

## Search defaults for v1.0

- Jargon expansion enabled
- Broad-query reranking disabled

These are the frozen production defaults and should not be changed without re-evaluation.

## Where detailed docs live

- Development and benchmarking: docs/development.md
- Operations and rollout checklist: docs/ops_1_0_checklist.md
- Search freeze/baseline evidence: docs/production_freeze_20260329.md
- GitHub release and branch protection setup: docs/github_release_setup.md
