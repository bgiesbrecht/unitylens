"""Search API route: keyword and NL-powered metadata search."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query

from unitylens.auth.deps import current_user
from unitylens.context.builder import get_cached_context
from unitylens.llm.client import get_llm_client
from unitylens.store import db

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api",
    tags=["search"],
    dependencies=[Depends(current_user)],
)


@router.get("/search")
def search(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(default=50, ge=1, le=200, description="Max results"),
    mode: str = Query(
        default="keyword",
        description="Search mode: 'keyword' for FTS, 'nl' for NL via LLM",
    ),
) -> dict:
    """Search metadata by keyword or natural language.

    - **keyword** mode: uses the SQLite FTS5 index for fast full-text
      search across object names and comments.
    - **nl** mode: sends the query to the configured LLM with full
      metadata context, then also returns keyword matches as supporting
      results.
    """
    conn = db.get_connection()
    try:
        # Keyword search (always performed)
        try:
            keyword_results = db.keyword_search(conn, q, limit=limit)
        except Exception:
            logger.debug("FTS search failed, falling back to LIKE search")
            keyword_results = db.keyword_search_like(conn, q, limit=limit)

        response: dict = {
            "query": q,
            "mode": mode,
            "keyword_results": keyword_results,
            "llm_answer": None,
        }

        if mode == "nl":
            llm = get_llm_client()
            if llm is None:
                response["llm_answer"] = (
                    "LLM is not configured. Set UNITYLENS_LLM_ENDPOINT and "
                    "UNITYLENS_LLM_TOKEN environment variables."
                )
            else:
                context = get_cached_context()
                answer = llm.send_query(question=q, context=context)
                response["llm_answer"] = answer

        return response
    finally:
        conn.close()
