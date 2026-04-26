"""
Nitter RSS — open-source Twitter frontend with RSS feeds.
No API key. No Twitter account. Crawls public accounts and hashtags.
Falls back across multiple public Nitter instances if one is down.
"""
import logging
from datetime import datetime
from typing import AsyncGenerator, Dict, List, Optional

import feedparser

from .base_crawler import BaseCrawler, RawArticle

logger = logging.getLogger(__name__)

# Public Nitter instances — rotated on failure
NITTER_INSTANCES = [
    "https://nitter.privacydev.net",
    "https://nitter.poast.org",
    "https://nitter.cz",
    "https://nitter.1d4.us",
]

# High-signal public accounts (no auth needed via Nitter RSS)
TWITTER_ACCOUNTS: List[Dict] = [
    {"handle": "BBCWorld", "region": "GB", "priority": 1},
    {"handle": "Reuters", "region": "US", "priority": 1},
    {"handle": "AP", "region": "US", "priority": 1},
    {"handle": "AJEnglish", "region": "QA", "priority": 2},
    {"handle": "CNN", "region": "US", "priority": 1},
    {"handle": "nytimes", "region": "US", "priority": 1},
    {"handle": "guardian", "region": "GB", "priority": 2},
    {"handle": "business", "region": "US", "priority": 2},      # Bloomberg
    {"handle": "WSJ", "region": "US", "priority": 2},
    {"handle": "FT", "region": "GB", "priority": 2},
    {"handle": "euronews", "region": "EU", "priority": 2},
    {"handle": "DW_English", "region": "DE", "priority": 2},
    {"handle": "NASA", "region": "US", "priority": 3},
    {"handle": "WHO", "region": None, "priority": 2},
    {"handle": "IMFNews", "region": None, "priority": 2},
]

# Hashtag/search feeds
NITTER_SEARCHES: List[Dict] = [
    {"query": "breaking+news", "label": "breaking", "priority": 1},
    {"query": "geopolitics", "label": "geopolitics", "priority": 2},
    {"query": "economy+market", "label": "economy", "priority": 2},
]

SOURCE_CONFIG = {"name": "Nitter", "priority": 2, "region": None}


class NitterCrawler(BaseCrawler):
    def __init__(self):
        super().__init__(SOURCE_CONFIG)

    async def _fetch_rss(self, path: str) -> Optional[str]:
        for instance in NITTER_INSTANCES:
            url = f"{instance}{path}"
            html = await self._fetch(url, headers={"User-Agent": "NewsBot/1.0"})
            if html:
                return html
        return None

    async def crawl(self) -> AsyncGenerator[RawArticle, None]:
        # accounts
        for acc in TWITTER_ACCOUNTS:
            raw = await self._fetch_rss(f"/{acc['handle']}/rss")
            if not raw:
                continue
            feed = feedparser.parse(raw)
            for entry in feed.entries[:20]:
                title = entry.get("title", "").strip()
                url = entry.get("link", "").strip()
                if not title or not url:
                    continue

                import re
                content = re.sub(r"<[^>]+>", " ", entry.get("summary", "")).strip()

                published_at = datetime.utcnow()
                if entry.get("published_parsed"):
                    try:
                        published_at = datetime(*entry.published_parsed[:6])
                    except Exception:
                        pass

                yield RawArticle(
                    url=url,
                    title=title[:300],
                    content=content[:3000],
                    source=f"twitter/@{acc['handle']}",
                    source_type="social",
                    published_at=published_at,
                    author=acc["handle"],
                    region=acc.get("region"),
                    metadata={"handle": acc["handle"], "priority": acc["priority"]},
                )

        # search/hashtag feeds
        for search in NITTER_SEARCHES:
            raw = await self._fetch_rss(f"/search/rss?q={search['query']}&f=tweets")
            if not raw:
                continue
            feed = feedparser.parse(raw)
            for entry in feed.entries[:30]:
                title = entry.get("title", "").strip()
                url = entry.get("link", "").strip()
                if not title or not url:
                    continue

                import re
                content = re.sub(r"<[^>]+>", " ", entry.get("summary", "")).strip()

                published_at = datetime.utcnow()
                if entry.get("published_parsed"):
                    try:
                        published_at = datetime(*entry.published_parsed[:6])
                    except Exception:
                        pass

                yield RawArticle(
                    url=url,
                    title=title[:300],
                    content=content[:3000],
                    source=f"twitter/search/{search['label']}",
                    source_type="social",
                    published_at=published_at,
                    region=None,
                    metadata={"search_query": search["query"]},
                )
