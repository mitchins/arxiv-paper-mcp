from __future__ import annotations

from fastapi import APIRouter, HTTPException

from core.models import Paper, PaperIdRequest, SearchRequest, SearchResult
from core.service import PaperSearchService

router = APIRouter()

# Injected at startup from main.py
_service: PaperSearchService | None = None


def init_routes(service: PaperSearchService) -> None:
    global _service
    _service = service


def _get_service() -> PaperSearchService:
    assert _service is not None, "Service not initialised"
    return _service


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/search")
def search_papers(req: SearchRequest) -> list[SearchResult]:
    return _get_service().search(req.query, req.limit)


@router.post(
    "/paper",
    responses={404: {"description": "Paper not found"}},
)
def get_paper(req: PaperIdRequest) -> Paper:
    paper = _get_service().get_paper(req.arxiv_id)
    if paper is None:
        raise HTTPException(status_code=404, detail="Paper not found")
    return paper
