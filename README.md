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

## Kaggle auth note

You must authenticate Kaggle before download:

- Install CLI: `pip install kaggle`
- Set `KAGGLE_USERNAME` and `KAGGLE_KEY`, or place `kaggle.json` in `~/.kaggle/`
