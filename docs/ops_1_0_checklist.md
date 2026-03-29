# 1.0 Operations Checklist

This checklist is the release path after search optimization freeze.

## Scope Freeze

- Retrieval behavior for 1.0:
  - `ARXIV_ENABLE_JARGON_EXPANSION=1`
  - `ARXIV_ENABLE_BROAD_QUERY_ROUTING=0`
- Do not ship new reranking modes without explicit benchmark re-approval.

Reference: `docs/production_freeze_20260329.md`

## Docker Deployment Baseline

1. Build image

```bash
export ARXIV_DB_HOST_PATH=/Volumes/data-2/deploy/arxiv-mcp/data/arxiv.db
docker compose build
```

2. Start service

```bash
docker compose up -d
```

3. Verify health

```bash
curl -fsS http://127.0.0.1:8000/health
```

4. Run smoke/perf check

```bash
python scripts/smoke_runtime.py --endpoint http://127.0.0.1:8000 --iterations 7 --query "transformer" --search-timeout 180 --warmup
```

## Performance Gate (Pre-Release)

- Run with realistic host and mounted DB path.
- Run smoke script at least 3 times.
- Log and keep:
  - p50 latency
  - p95 latency
  - returned result count sanity
- If p95 regresses >20% vs last accepted build, block release and investigate.

## Update Runbook (Container)

Preferred update mode for 1.0: explicit pull + recreate.

```bash
docker compose pull
docker compose up -d --force-recreate
```

Post-update checks:

1. `/health` returns `{"status":"ok"}`
2. `scripts/smoke_runtime.py` passes
3. Spot query sanity checks for known user workflows

Rollback:

1. Re-run previous image tag.
2. Re-run health + smoke checks.

## Auto-Update Strategy (After 1.0)

For 1.0, avoid unattended auto-updates by default.

Recommended staged path:

1. Manual updates with explicit operator approval.
2. Add scheduled pull notifications only.
3. Add supervised auto-update in a maintenance window after enough operational confidence.
