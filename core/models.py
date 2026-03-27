from __future__ import annotations

from pydantic import BaseModel


class Paper(BaseModel):
    id: str
    title: str
    abstract: str
    authors: str
    categories: str
    update_date: str


class SearchRequest(BaseModel):
    query: str
    limit: int = 10


class PaperIdRequest(BaseModel):
    arxiv_id: str


class SearchResult(BaseModel):
    id: str
    title: str
    snippet: str
