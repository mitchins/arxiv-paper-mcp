#!/usr/bin/env bash
set -euo pipefail

DATASET="Cornell-University/arxiv"
OUT_DIR="./data"

if ! command -v kaggle >/dev/null 2>&1; then
  echo "Error: kaggle CLI not found. Install with: pip install kaggle" >&2
  exit 1
fi

mkdir -p "$OUT_DIR"

echo "Downloading $DATASET to $OUT_DIR ..."
kaggle datasets download -d "$DATASET" -p "$OUT_DIR" --unzip

echo "Done. Files in $OUT_DIR:"
ls -1 "$OUT_DIR"

echo "If needed, build index with:"
echo "python -m scripts.build_index --jsonl ./data/arxiv-metadata-oai-snapshot.json --db ./data/arxiv.db"
