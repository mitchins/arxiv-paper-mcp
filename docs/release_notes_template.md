# Release Notes Template

Use this template for `vX.Y.Z` tags.

## Highlights

- 
- 

## Runtime Defaults

- `ARXIV_ENABLE_JARGON_EXPANSION=1`
- `ARXIV_ENABLE_BROAD_QUERY_ROUTING=0`

## Docker / GHCR

- Image: `ghcr.io/mitchins/arxiv-paper-mcp:<tag>`
- Multi-arch: `linux/amd64`, `linux/arm64`

## Validation

- CI checks passed: `lint-and-test`, `docker-build`
- Local/host smoke check:

```bash
python scripts/smoke_runtime.py --endpoint http://127.0.0.1:8000 --iterations 7 --query "transformer" --search-timeout 180 --startup-wait 60 --warmup
```

## Upgrade notes

- 

## Known limitations

- Search reranking remains frozen off for broad-query route pending further evidence.
