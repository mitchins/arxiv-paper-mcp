from __future__ import annotations

from fastmcp import FastMCP

from core.service import PaperSearchService

mcp = FastMCP("arxiv-paper-mcp")

# Injected at startup from main.py
_service: PaperSearchService | None = None


def init_mcp(service: PaperSearchService) -> None:
    global _service
    _service = service


def _get_service() -> PaperSearchService:
    assert _service is not None, "Service not initialised"
    return _service


@mcp.tool
def search_arxiv_database(query: str, limit: int = 10) -> list[dict]:
    """Search the local arXiv paper database using full-text search.

    Args:
        query: Keywords to search for in paper titles and abstracts.
        limit: Maximum number of results to return (1-50, default 10).

    Returns:
        A list of matching papers with id, title, and a snippet from the abstract.
    """
    results = _get_service().search(query, limit)
    return [r.model_dump() for r in results]


@mcp.tool
def get_paper_details(arxiv_id: str) -> dict | None:
    """Get full metadata for a specific arXiv paper by its ID.

    Args:
        arxiv_id: The arXiv paper ID (e.g. '2301.12345' or 'arXiv:2301.12345v2').

    Returns:
        Full paper metadata including title, abstract, authors, categories,
        and update date. Returns None if the paper is not found.
    """
    paper = _get_service().get_paper(arxiv_id)
    if paper is None:
        return None
    return paper.model_dump()
