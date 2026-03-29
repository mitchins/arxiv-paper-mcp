# Development Guide

This page contains development-focused workflows that are intentionally kept out
of the top-level README.

## Local Python run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
python main.py --host 127.0.0.1 --port 8000
```

Useful flags:

```bash
python main.py --help
python main.py --reload
python main.py --host 0.0.0.0 --port 8010
```

## Dataset and index build

Download source data (Kaggle auth required):

```bash
bash scripts/pull_kaggle.sh
```

Build SQLite index:

```bash
python -m scripts.build_index --jsonl ./data/arxiv-metadata-oai-snapshot.json --db ./data/arxiv.db
```

## Docker details

Container layout:

- /app: application code
- /data/arxiv.db: mounted SQLite database (read-only recommended)
- /config: mounted runtime config (optional, read-only recommended)

Mount-first run example (no exported shell vars required):

```bash
docker run -d --name arxiv-paper-mcp \
  -p 8000:8000 \
  --mount type=bind,src=/absolute/path/to/arxiv.db,dst=/data/arxiv.db,readonly \
  --mount type=bind,src=$PWD/config,dst=/config,readonly \
  -e DB_PATH=/data/arxiv.db \
  ghcr.io/mitchins/arxiv-paper-mcp:latest
```

Compose knobs (if using docker compose):

- ARXIV_DB_HOST_PATH: host path to sqlite file
- ARXIV_CONFIG_HOST_PATH: host path to config directory

Compose one-liner without export:

```bash
ARXIV_DB_HOST_PATH=/absolute/path/to/arxiv.db ARXIV_CONFIG_HOST_PATH=$PWD/config docker compose up -d --wait
```

Local source build (used by scripts/dev_up.sh):

```bash
docker compose -f docker-compose.yml -f docker-compose.build.yml build
docker compose -f docker-compose.yml -f docker-compose.build.yml up -d --wait
```

## Config and glossary behavior

Runtime environment loading priority:

1. /config/.env
2. repo-local .env

Glossary priority when jargon expansion is enabled and no explicit override is
provided:

1. /config/jargon_glossary.json
2. jargon_glossary.json
3. benchmarks/queries/jargon_glossary.v2.json

## Benchmarking workflow

Primary harness inputs:

- Query set: benchmarks/queries/v1.json
- Baseline template: benchmarks/reference_baselines/v1.template.json
- Output directory: benchmarks/runs/

Prepare baseline:

1. Copy benchmarks/reference_baselines/v1.template.json to benchmarks/reference_baselines/v1.json
2. Fill reference ids for each query id

Run harness:

```bash
python -m scripts.benchmark_harness \
  --endpoint http://127.0.0.1:8010 \
  --query-set benchmarks/queries/v1.json \
  --baseline benchmarks/reference_baselines/v1.json \
  --k 10
```

Other experiment scripts are in scripts/ and intentionally left out of the
default release runbook.

## Quality checks

```bash
python -m pytest -q
python -m ruff check main.py api core scripts/smoke_runtime.py scripts/sweep_b_variants.py tests
```

## CI and release

- CI workflow: .github/workflows/ci.yml
- GHCR publish workflow: .github/workflows/docker-publish.yml
- Release setup notes: docs/github_release_setup.md
