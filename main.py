"""arxiv-paper-mcp – local arXiv full-text search server.

Starts both FastAPI (HTTP) and FastMCP (MCP) interfaces backed by the same
PaperSearchService.
"""
from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()

import os

from api.mcp_tools import init_mcp, mcp
from api.routes import init_routes, router
from core.cache import TTLCache
from core.repository import PaperRepository
from core.service import PaperSearchService

log = logging.getLogger(__name__)

DB_PATH = os.getenv("DB_PATH", "./data/arxiv.db")


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = Path(DB_PATH)
    if not db.exists():
        log.error("Database not found at %s. Run `python -m scripts.build_index` first.", db)
        sys.exit(1)

    repo = PaperRepository(db)
    repo.connect()

    cache = TTLCache()
    service = PaperSearchService(repo, cache=cache)

    init_routes(service)
    init_mcp(service)

    log.info("Server ready – DB: %s", db)
    yield

    repo.close()


app = FastAPI(title="arxiv-paper-mcp", lifespan=lifespan)
app.include_router(router)
app.mount("/mcp", mcp.http_app(transport="streamable-http"))

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, log_level="info")
