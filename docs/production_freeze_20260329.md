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

## B-Mode Follow-up (Bounded MiniLM Fusion)

Implemented new broad reranker mode:

- `ARXIV_BROAD_RERANK_MODE=minilm_fusion`
- Windowed rerank with lexical-anchor bonus and displacement caps.

Evaluated on `2026-03-29` with default and stricter tuning variants.
Both variants produced the same result:

- `macro_hit_rate=0.810`
- `weighted_hit_rate=0.859`
- `broad_macro_hit_rate=0.700`

Decision: keep this mode non-default and non-rollout (below guardrail).

## Final B-Avenue Sweep (Comprehensive)

Ran 11 variants (control, MMR baselines, and multiple bounded-fusion settings)
using `scripts/sweep_b_variants.py` against the same truth set.

Summary:

| Variant | macro | weighted | broad_macro |
|---|---:|---:|---:|
| control_broad_off | 0.820 | 0.875 | 0.750 |
| mmr_l085 | 0.750 | 0.766 | 0.400 |
| mmr_l075 | 0.720 | 0.719 | 0.250 |
| mmr_l065 | 0.720 | 0.719 | 0.250 |
| fusion_ref | 0.810 | 0.859 | 0.700 |
| fusion_lex_heavy | 0.810 | 0.859 | 0.700 |
| fusion_balanced | 0.810 | 0.859 | 0.700 |
| fusion_wide_no_anchor_gate | 0.800 | 0.844 | 0.650 |
| fusion_high_anchor | 0.810 | 0.859 | 0.700 |
| fusion_minilm_edge | 0.810 | 0.859 | 0.700 |
| fusion_tightest | 0.810 | 0.859 | 0.700 |

Outcome:

- Best variant remained `control_broad_off`.
- Guardrail pass count: `1` (control only).
- No B-mode variant matched control on both weighted and broad metrics.

Close recommendation for this avenue:

- Keep B available only as experimental mode.
- Do not roll out broad reranking in production path at this time.