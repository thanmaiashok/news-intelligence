"""
GDELT 2.0 DOC API — completely free, no key, updates every 15 min.
Covers 100+ languages, 65+ countries, from 6000+ global news outlets.
"""
import logging
from datetime import datetime
from typing import AsyncGenerator, Dict, List

from .base_crawler import BaseCrawler, RawArticle

logger = logging.getLogger(__name__)

GDELT_API = "https://api.gdeltproject.org/api/v2/doc/doc"

# queries targeting major topics — runs one per cycle, rotates
GDELT_QUERIES: List[Dict] = [
    {"query": "war conflict", "label": "conflict"},
    {"query": "economy finance market", "label": "finance"},
    {"query": "technology artificial intelligence", "label": "tech"},
    {"query": "climate environment", "label": "climate"},
    {"query": "politics election government", "label": "politics"},
    {"query": "health disease pandemic", "label": "health"},
    {"query": "crime security terrorism", "label": "security"},
    {"query": "science discovery research", "label": "science"},
]

SOURCE_CONFIG = {"name": "GDELT", "priority": 1, "region": None}


class GDELTCrawler(BaseCrawler):
    def __init__(self):
        super().__init__(SOURCE_CONFIG)
        self._query_idx = 0

    async def crawl(self) -> AsyncGenerator[RawArticle, None]:
        # rotate through queries each cycle
        for q_config in GDELT_QUERIES:
            url = (
                f"{GDELT_API}"
                f"?query={q_config['query'].replace(' ', '%20')}"
                f"&mode=artlist&maxrecords=75&format=json&timespan=15min"
                f"&sort=HybridRel"
            )
            data = await self._fetch_json(url)
            if not data or "articles" not in data:
                continue

            for art in data["articles"]:
                title = art.get("title", "").strip()
                article_url = art.get("url", "").strip()
                if not title or not article_url:
                    continue

                seendate = art.get("seendate", "")
                published_at = datetime.utcnow()
                if seendate:
                    try:
                        published_at = datetime.strptime(seendate, "%Y%m%dT%H%M%SZ")
                    except Exception:
                        pass

                yield RawArticle(
                    url=article_url,
                    title=title,
                    content=art.get("seendate", "") + " " + title,  # GDELT doesn't return body
                    source=f"gdelt/{art.get('domain', 'unknown')}",
                    source_type="api",
                    published_at=published_at,
                    region=art.get("sourcecountry"),
                    language=art.get("language", "English"),
                    metadata={
                        "domain": art.get("domain"),
                        "socialimage": art.get("socialimage"),
                        "gdelt_topic": q_config["label"],
                        "tone": art.get("tone"),
                    },
                )
