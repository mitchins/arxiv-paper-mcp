# Production Freeze - 2026-03-29

This snapshot records the current best-performing retrieval path validated against
`benchmarks/runs/exp_widenet_judge_20260328T213320Z.summary.csv` via
`scripts/eval_live_search_vs_120b_truth.py`.

## Best Known Configuration

- Keep broad reranker disabled.
  - `ARXIV_ENABLE_BROAD_QUERY_ROUTING=0`
- Enable jargon expansion.
  - `ARXIV_ENABLE_JARGON_EXPANSION=1`
- Do not set `ARXIV_JARGON_GLOSSARY` unless overriding default source.
  - Default source priority:
    1. `jargon_glossary.json`
    2. `benchmarks/queries/jargon_glossary.v2.json`

Launch example:

```bash
ARXIV_ENABLE_JARGON_EXPANSION=1 \
ARXIV_DB_IMMUTABLE=1 \
ARXIV_DEV_MAX_LIMIT=1000 \
DB_PATH=/Volumes/data-2/deploy/arxiv-mcp/data/arxiv.db \
python main.py --host 0.0.0.0 --port 8010
```

## Validation Result (Live 8010)

Measured with:

```bash
/opt/miniconda3/envs/t5_inference_env/bin/python scripts/eval_live_search_vs_120b_truth.py \
  --endpoint http://127.0.0.1:8010 \
  --query-set benchmarks/queries/v1.json \
  --truth-summary benchmarks/runs/exp_widenet_judge_20260328T213320Z.summary.csv \
  --k 10
```

Result:

- `macro_hit_rate=0.820`
- `weighted_hit_rate=0.875`
- `broad_macro_hit_rate=0.750`

## Guardrail

Treat this as current control. Any new broad-query strategy must match or beat:

- `weighted_hit_rate >= 0.875`
- `broad_macro_hit_rate >= 0.750`

No rollout for a new mode unless both pass.