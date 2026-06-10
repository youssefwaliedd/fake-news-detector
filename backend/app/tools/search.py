"""Web-search wrapper for evidence retrieval.

Two free providers behind one interface (selected by ``settings.search_provider``):
  - "tavily" : Tavily API (free tier, needs TAVILY_API_KEY)
  - "ddgs"   : DuckDuckGo via the keyless ``ddgs`` package (no limits, no key)

Network/SDK errors are swallowed and logged so a single failed claim search never
kills an analysis run — the claim is just reported as "unverified".
"""
from __future__ import annotations

import logging
from typing import TypedDict

from app.core.config import get_settings

logger = logging.getLogger("tools.search")


class SearchResult(TypedDict):
    title: str
    url: str
    content: str


def search(query: str, max_results: int | None = None) -> list[SearchResult]:
    """Run a web search and return normalized results (capped 1..5)."""
    settings = get_settings()
    k = max(1, min(max_results or settings.results_per_claim, 5))
    provider = settings.search_provider.lower()
    try:
        if provider == "ddgs":
            return _search_ddgs(query, k)
        return _search_tavily(query, k)
    except Exception as exc:  # noqa: BLE001 - degrade gracefully
        logger.warning("search_failed", extra={"provider": provider, "query": query, "error": str(exc)})
        return []


def _search_tavily(query: str, k: int) -> list[SearchResult]:
    from tavily import TavilyClient

    client = TavilyClient(api_key=get_settings().tavily_api_key)
    response = client.search(query=query, max_results=k, search_depth="basic")
    return [
        SearchResult(
            title=item.get("title", "Untitled"),
            url=item.get("url", ""),
            content=(item.get("content") or "")[:600],
        )
        for item in response.get("results", [])[:k]
    ]


def _search_ddgs(query: str, k: int) -> list[SearchResult]:
    from ddgs import DDGS

    results: list[SearchResult] = []
    with DDGS() as ddgs:
        for item in ddgs.text(query, max_results=k):
            results.append(
                SearchResult(
                    title=item.get("title", "Untitled"),
                    url=item.get("href", ""),
                    content=(item.get("body") or "")[:600],
                )
            )
    return results
