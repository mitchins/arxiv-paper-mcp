# arxiv-paper-mcp

Local-only FastAPI + FastMCP server for fast keyword search over arXiv metadata using SQLite FTS5.

## What it does

- Full-text search over titles/abstracts (FTS5 + bm25)
- Paper lookup by arXiv ID
- Exposes both:
  - FastAPI endpoints (`/health`, `/search`, `/paper`)
  - MCP tools (`search_arxiv_database`, `get_paper_details`)

## Quick start

1. Create and activate a virtualenv

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Configure env (copy template)

```bash
cp .env.example .env
```

3. Download dataset (requires Kaggle auth)

```bash
bash scripts/pull_kaggle.sh
```

4. Build SQLite index

```bash
python -m scripts.build_index --jsonl ./data/arxiv-metadata-oai-snapshot.json --db ./data/arxiv.db
```

5. Run server

```bash
python main.py
```

Useful flags:

```bash
python main.py --help
python main.py --port 9000
python main.py --host 0.0.0.0 --port 9000
python main.py --reload
```

## API basics

- Health: `GET /health`
- Search: `POST /search` with body:

```json
{"query": "transformer", "limit": 10}
```

- Paper details: `POST /paper` with body:

```json
{"arxiv_id": "arXiv:2301.12345v2"}
```

## Jargon expansion

Optional jargon-aware query expansion can be enabled with:

```bash
ARXIV_ENABLE_JARGON_EXPANSION=1 python main.py
```

When enabled and `ARXIV_JARGON_GLOSSARY` is not set, the server will prefer:

1. `jargon_glossary.json`
2. `benchmarks/queries/jargon_glossary.v2.json`

To force a specific glossary file:

```bash
ARXIV_ENABLE_JARGON_EXPANSION=1 \
ARXIV_JARGON_GLOSSARY=benchmarks/queries/jargon_glossary.v2.json \
python main.py
```

## MCP endpoint

- Streamable HTTP MCP endpoint: `/mcp/`
- Example local URL: `http://127.0.0.1:8000/mcp/`
- Example LAN URL: `http://192.168.1.26:8010/mcp/`

## Kaggle auth note

You must authenticate Kaggle before download:

- Install CLI: `pip install kaggle`
- Set `KAGGLE_USERNAME` and `KAGGLE_KEY`, or place `kaggle.json` in `~/.kaggle/`

## Benchmark harness

Use the harness to evaluate retrieval quality over time with a fixed query set.

- Query set: `benchmarks/queries/v1.json`
- Reference baseline template: `benchmarks/reference_baselines/v1.template.json`
- Run outputs: `benchmarks/runs/`

### Workflow

1. Fill a frozen reference baseline once

- Copy `benchmarks/reference_baselines/v1.template.json` to `benchmarks/reference_baselines/v1.json`
- For each query id, paste top-k arXiv IDs from your chosen reference standard.

2. Run local benchmark

```bash
python -m scripts.benchmark_harness \
  --endpoint http://192.168.1.26:8010 \
  --query-set benchmarks/queries/v1.json \
  --baseline benchmarks/reference_baselines/v1.json \
  --k 10
```

3. Review outputs

- `run_*.local_results.json`: local raw results for reproducibility
- `run_*.overlap.csv`: overlap@k plus columns for human/judge scoring

Naive metric in v1:

- Overlap@k = how many reference IDs are also in local top-k for each query.

## Docker deployment

This repo includes a Docker-first deployment baseline for 1.0.

Build and run with compose:

```bash
docker compose build
docker compose up -d
```

Health check:

```bash
curl -fsS http://127.0.0.1:8000/health
```

Default container profile keeps search on the frozen production path:

- `ARXIV_ENABLE_JARGON_EXPANSION=1`
- `ARXIV_ENABLE_BROAD_QUERY_ROUTING=0`

The compose file mounts `./data` as read-only at `/data`, and the service uses
`DB_PATH=/data/arxiv.db`.

## Runtime smoke/perf check

Run a quick runtime check (health + repeated search latency):

```bash
python scripts/smoke_runtime.py --endpoint http://127.0.0.1:8000 --iterations 7 --query "transformer"
```

For cold starts or slower environments, add:

```bash
python scripts/smoke_runtime.py --endpoint http://127.0.0.1:8000 --iterations 7 --query "transformer" --search-timeout 180 --warmup
```

## 1.0 operations guide

For deployment, performance gates, and update runbook, see:

- `docs/ops_1_0_checklist.md`
