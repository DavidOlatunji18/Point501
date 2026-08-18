"""Pulls fantasy football news from RSS feeds and ingests each new entry as
an article for the RAG pipeline (app/services/articles.py), so /chat has
fresh analysis to ground answers in without anyone manually pasting text in.

Runs on a schedule (see the APScheduler job registered in app/main.py's
lifespan) and can also be triggered on demand via POST /articles/fetch-feeds.
"""

import html
import logging
import re

import feedparser

from app.db.session import SessionLocal
from app.services import articles as articles_service

logger = logging.getLogger(__name__)

# Free, publicly available fantasy football RSS feeds - no API key needed.
# ESPN's feed mixes in fantasy baseball/basketball items too; those get
# filtered out below rather than trusted to just not match football queries,
# since they'd otherwise sit in the corpus as noise.
FEED_URLS = [
    "https://www.rotoballer.com/feed",
    "https://www.espn.com/espn/rss/fantasy/news",
]

_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")
_NON_FOOTBALL_RE = re.compile(r"\b(baseball|basketball|hockey|mlb|nba|nhl)\b", re.IGNORECASE)


def _clean_html(raw: str) -> str:
    """RSS descriptions sometimes embed HTML (img tags, etc) - strip it down
    to plain text, since chunk_text() isn't HTML-aware."""
    text = _TAG_RE.sub(" ", raw)
    text = html.unescape(text)
    return _WHITESPACE_RE.sub(" ", text).strip()


def fetch_and_ingest_feeds() -> dict[str, int]:
    """Fetches all configured feeds and ingests any new entries. Safe to run
    repeatedly - ingest_article() already dedupes on exact content hash, so
    re-fetching the same feed only ever adds genuinely new items.

    Synchronous by design (feedparser and the DB session are both sync) so
    it can run in APScheduler's thread-pool executor without blocking the
    event loop.
    """
    ingested = 0
    skipped = 0
    errors = 0

    db = SessionLocal()
    try:
        for feed_url in FEED_URLS:
            parsed = feedparser.parse(feed_url)
            if parsed.bozo and not parsed.entries:
                logger.warning("Failed to parse feed %s: %s", feed_url, parsed.bozo_exception)
                errors += 1
                continue

            source = parsed.feed.get("title") or feed_url
            for entry in parsed.entries:
                title = entry.get("title")
                summary = entry.get("summary") or entry.get("description")
                if not title or not summary:
                    continue
                if _NON_FOOTBALL_RE.search(title) or _NON_FOOTBALL_RE.search(summary):
                    continue

                content = _clean_html(summary)
                if not content:
                    continue

                try:
                    articles_service.ingest_article(
                        db, title=title, content=content, source=source
                    )
                    ingested += 1
                except articles_service.DuplicateArticleError:
                    skipped += 1
                except ValueError:
                    # No content left after chunking - skip, not a real error.
                    skipped += 1
    finally:
        db.close()

    logger.info(
        "Feed ingestion complete: %d new, %d skipped/duplicate, %d feed errors",
        ingested,
        skipped,
        errors,
    )
    return {"ingested": ingested, "skipped": skipped, "errors": errors}
