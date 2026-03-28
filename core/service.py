from __future__ import annotations

import os

from core.cache import TTLCache
from core.models import Paper, SearchResult
from core.normalization import normalize_arxiv_id, normalize_query
from core.repository import PaperRepository

MAX_LIMIT = 50

# TODO(dev-cleanup): dev-only escape hatch for offline experiments (e.g. widenet
# judging).  Remove or gate behind a proper feature-flag before exposing to
# untrusted callers.  Set env var ARXIV_DEV_MAX_LIMIT=5000 to raise the cap.
_DEV_MAX_LIMIT: int | None = int(os.environ["ARXIV_DEV_MAX_LIMIT"]) if os.environ.get("ARXIV_DEV_MAX_LIMIT") else None


class PaperSearchService:
    """Application-level search and lookup logic."""

    def __init__(self, repo: PaperRepository, *, cache: TTLCache | None = None) -> None:
        self._repo = repo
        self._cache = cache

    # -- public API ----------------------------------------------------------

    def search(self, query: str, limit: int | None = 10) -> list[SearchResult]:
        cleaned = normalize_query(query)
        if not cleaned:
            return []

        clamped = _clamp_limit(limit)
        cache_key = f"search:{cleaned}:{clamped}"

        if self._cache is not None:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        results = self._repo.search(cleaned, clamped)

        if self._cache is not None:
            self._cache.set(cache_key, results)

        return results

    def get_paper(self, arxiv_id: str) -> Paper | None:
        normalized = normalize_arxiv_id(arxiv_id)
        if normalized is None:
            return None

        cache_key = f"paper:{normalized}"

        if self._cache is not None:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        paper = self._repo.get_by_id(normalized)

        if paper is not None and self._cache is not None:
            self._cache.set(cache_key, paper)

        return paper


def _clamp_limit(value: int | None) -> int:
    try:
        v = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        v = 10
    ceiling = _DEV_MAX_LIMIT if _DEV_MAX_LIMIT is not None else MAX_LIMIT
    return max(1, min(v, ceiling))
