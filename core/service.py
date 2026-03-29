from __future__ import annotations

import logging
import os
import re
from typing import Any

from core.cache import TTLCache
from core.models import Paper, SearchResult
from core.normalization import normalize_arxiv_id, normalize_query
from core.repository import PaperRepository

MAX_LIMIT = 50

# TODO(dev-cleanup): dev-only escape hatch for offline experiments (e.g. widenet
# judging).  Remove or gate behind a proper feature-flag before exposing to
# untrusted callers.  Set env var ARXIV_DEV_MAX_LIMIT=5000 to raise the cap.
_DEV_MAX_LIMIT: int | None = int(os.environ["ARXIV_DEV_MAX_LIMIT"]) if os.environ.get("ARXIV_DEV_MAX_LIMIT") else None

# Default off until broad-case routing shows consistent wins on 120B-truth metrics.
_BROAD_QUERY_ROUTING_ENABLED = os.getenv("ARXIV_ENABLE_BROAD_QUERY_ROUTING", "0").lower() in {"1", "true", "yes"}
_BROAD_PROBE_LIMIT = int(os.getenv("ARXIV_BROAD_PROBE_LIMIT", "200"))
_BROAD_RESULT_THRESHOLD = int(os.getenv("ARXIV_BROAD_RESULT_THRESHOLD", "80"))
_BROAD_POOL_MULTIPLIER = int(os.getenv("ARXIV_BROAD_POOL_MULTIPLIER", "10"))
_BROAD_MAX_POOL = int(os.getenv("ARXIV_BROAD_MAX_POOL", "300"))
_BROAD_MMR_LAMBDA = float(os.getenv("ARXIV_BROAD_MMR_LAMBDA", "0.75"))
_BROAD_RERANK_MODE = os.getenv("ARXIV_BROAD_RERANK_MODE", "mmr").strip().lower()
_BROAD_RERANK_FAILURE_MODE = os.getenv("ARXIV_BROAD_RERANK_FAILURE_MODE", "error").strip().lower()
_BROAD_MINILM_MODEL = os.getenv(
    "ARXIV_BROAD_MINILM_MODEL",
    "ahmedfarazsyk/ms-marco-MiniLM-L6-v2-finetuned-scidocs",
)
_BROAD_MINILM_BATCH_SIZE = int(os.getenv("ARXIV_BROAD_MINILM_BATCH_SIZE", "32"))

_MINILM_RERANKER: Any | None = None
_MINILM_RERANKER_INIT_ATTEMPTED = False
_MINILM_RERANKER_INIT_ERROR: str | None = None

_logger = logging.getLogger(__name__)

_TEXT_TOKEN_RE = re.compile(r"[a-z0-9]+")


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
        broad_flag = self._should_route_broad(cleaned, clamped)
        cache_key = f"search:{cleaned}:{clamped}:broad={int(broad_flag)}"

        if self._cache is not None:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        if broad_flag:
            results = self._search_broad(cleaned, clamped)
        else:
            results = self._repo.search(cleaned, clamped)

        if self._cache is not None:
            self._cache.set(cache_key, results)

        return results

    def _should_route_broad(self, cleaned_query: str, limit: int) -> bool:
        if not _BROAD_QUERY_ROUTING_ENABLED:
            return False

        # For tiny result requests, avoid expensive probe/rerank path.
        if limit <= 3:
            return False

        probe_limit = max(limit, min(_BROAD_PROBE_LIMIT, _clamp_limit(_BROAD_PROBE_LIMIT)))
        probe_rows = self._repo.search(cleaned_query, probe_limit)

        if len(probe_rows) >= min(_BROAD_RESULT_THRESHOLD, probe_limit):
            return True

        return False

    def _search_broad(self, cleaned_query: str, limit: int) -> list[SearchResult]:
        pool_limit = min(_BROAD_MAX_POOL, max(limit * _BROAD_POOL_MULTIPLIER, _BROAD_RESULT_THRESHOLD))
        pool_limit = _clamp_limit(pool_limit)
        pool = self._repo.search(cleaned_query, pool_limit)
        if len(pool) <= limit:
            return pool

        if _BROAD_RERANK_MODE == "minilm":
            reranked, reason = _minilm_rerank(cleaned_query, pool, limit)
            if reranked is not None:
                return reranked

            msg = (
                "Broad minilm reranker failed: "
                f"reason={reason or 'unknown'}; "
                f"model={_BROAD_MINILM_MODEL}; "
                f"failure_mode={_BROAD_RERANK_FAILURE_MODE}"
            )
            if _BROAD_RERANK_FAILURE_MODE == "mmr":
                _logger.warning("%s; explicit fallback to MMR", msg)
                return _mmr_rerank(cleaned_query, pool, limit, lambda_diversity=_BROAD_MMR_LAMBDA)
            raise RuntimeError(msg)

        return _mmr_rerank(cleaned_query, pool, limit, lambda_diversity=_BROAD_MMR_LAMBDA)

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


def _tokenize_text(value: str) -> set[str]:
    return {t for t in _TEXT_TOKEN_RE.findall(value.lower()) if len(t) > 1}


def _query_terms_from_match(cleaned_query: str) -> set[str]:
    # Extract lexical terms from normalized FTS MATCH query.
    return _tokenize_text(cleaned_query.replace("\"", " "))


def _doc_terms(doc: SearchResult) -> set[str]:
    return _tokenize_text(f"{doc.title} {doc.snippet}")


def _overlap(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    denom = max(len(a), 1)
    return inter / denom


def _mmr_rerank(
    cleaned_query: str,
    docs: list[SearchResult],
    top_k: int,
    *,
    lambda_diversity: float,
) -> list[SearchResult]:
    q_terms = _query_terms_from_match(cleaned_query)
    doc_terms = [_doc_terms(d) for d in docs]

    # BM25 prior from initial rank remains important for relevance stability.
    bm25_prior = [1.0 / (i + 1) for i in range(len(docs))]
    query_sim = [_overlap(q_terms, terms) for terms in doc_terms]

    selected: list[int] = []
    remaining = set(range(len(docs)))

    for _ in range(min(top_k, len(docs))):
        best_idx = None
        best_score = float("-inf")

        for idx in remaining:
            novelty_penalty = 0.0
            if selected:
                novelty_penalty = max(_overlap(doc_terms[idx], doc_terms[s]) for s in selected)

            score = (
                lambda_diversity * (0.8 * query_sim[idx] + 0.2 * bm25_prior[idx])
                - (1.0 - lambda_diversity) * novelty_penalty
            )

            if score > best_score:
                best_score = score
                best_idx = idx

        assert best_idx is not None
        selected.append(best_idx)
        remaining.remove(best_idx)

    return [docs[i] for i in selected]


def _get_minilm_reranker() -> tuple[Any | None, str | None]:
    global _MINILM_RERANKER
    global _MINILM_RERANKER_INIT_ATTEMPTED
    global _MINILM_RERANKER_INIT_ERROR

    if _MINILM_RERANKER_INIT_ATTEMPTED:
        return _MINILM_RERANKER, _MINILM_RERANKER_INIT_ERROR

    _MINILM_RERANKER_INIT_ATTEMPTED = True
    try:
        from sentence_transformers import CrossEncoder

        _MINILM_RERANKER = CrossEncoder(_BROAD_MINILM_MODEL)
        _MINILM_RERANKER_INIT_ERROR = None
    except Exception as exc:
        _MINILM_RERANKER = None
        _MINILM_RERANKER_INIT_ERROR = f"{type(exc).__name__}: {exc}"

    return _MINILM_RERANKER, _MINILM_RERANKER_INIT_ERROR


def _minilm_rerank(
    cleaned_query: str,
    docs: list[SearchResult],
    top_k: int,
) -> tuple[list[SearchResult] | None, str | None]:
    reranker, init_err = _get_minilm_reranker()
    if reranker is None:
        return None, init_err or "reranker_not_initialized"

    # Convert normalized FTS query back into a plain lexical prompt for the cross-encoder.
    plain_query = " ".join(_query_terms_from_match(cleaned_query))
    if not plain_query:
        plain_query = cleaned_query

    pairs = [(plain_query, f"{d.title}\n{d.snippet}") for d in docs]
    try:
        scores = reranker.predict(
            pairs,
            batch_size=max(1, _BROAD_MINILM_BATCH_SIZE),
            show_progress_bar=False,
        )
    except Exception as exc:
        return None, f"predict_failed: {type(exc).__name__}: {exc}"

    scored = list(zip(docs, scores))
    scored.sort(key=lambda x: float(x[1]), reverse=True)
    return [d for d, _ in scored[:top_k]], None
