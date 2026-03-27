from __future__ import annotations

from core.cache import TTLCache
from core.models import Paper, SearchResult
from core.normalization import normalize_arxiv_id, normalize_query
from core.repository import PaperRepository

MAX_LIMIT = 50


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
    return max(1, min(v, MAX_LIMIT))
