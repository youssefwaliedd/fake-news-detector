"""Turn raw user input (pasted text OR an article URL) into clean article text.

``ingest`` is the first node in the pipeline. It decides whether the input is a
URL or free text, and for URLs fetches + extracts the main article body with
trafilatura (boilerplate/nav stripped). Everything downstream only sees text.
"""
from __future__ import annotations

import logging
import re
from typing import TypedDict

logger = logging.getLogger("ingest.extract")

_URL_RE = re.compile(r"^https?://\S+$", re.IGNORECASE)


class Article(TypedDict):
    title: str
    text: str
    source: str        # the URL if input was a URL, else "text"


def looks_like_url(value: str) -> bool:
    """True if the (stripped) input is a single http(s) URL."""
    value = (value or "").strip()
    return bool(_URL_RE.match(value)) and " " not in value


def extract(raw_input: str) -> Article:
    """Normalize ``raw_input`` into an Article.

    Pasted text is returned as-is. A URL is fetched and reduced to its main
    article body; on any fetch/parse failure we degrade to an empty body so the
    pipeline can still report that extraction failed rather than crashing.
    """
    raw_input = (raw_input or "").strip()
    if not looks_like_url(raw_input):
        return Article(title="", text=raw_input, source="text")

    url = raw_input
    try:
        import trafilatura

        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            raise RuntimeError("empty download")
        text = trafilatura.extract(downloaded, include_comments=False) or ""
        meta = trafilatura.extract_metadata(downloaded)
        title = (meta.title if meta and meta.title else "") or ""
        return Article(title=title, text=text.strip(), source=url)
    except Exception as exc:  # noqa: BLE001 - degrade gracefully
        logger.warning("url_extract_failed", extra={"url": url, "error": str(exc)})
        return Article(title="", text="", source=url)
