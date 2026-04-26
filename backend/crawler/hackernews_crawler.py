import asyncio
import logging
from datetime import datetime
from typing import AsyncGenerator, Dict, List, Optional

from .base_crawler import BaseCrawler, RawArticle

logger = logging.getLogger(__name__)

HN_API = "https://hacker-news.firebaseio.com/v0"

SOURCE_CONFIG = {"name": "HackerNews", "priority": 2, "region": "US"}


class HackerNewsCrawler(BaseCrawler):
    def __init__(self):
        super().__init__(SOURCE_CONFIG)

    async def crawl(self) -> AsyncGenerator[RawArticle, None]:
        # fetch top + new story IDs
        top = await self._fetch_json(f"{HN_API}/topstories.json") or []
        new = await self._fetch_json(f"{HN_API}/newstories.json") or []
        ids = list(dict.fromkeys(top[:100] + new[:50]))  # dedup, cap 150

        semaphore = asyncio.Semaphore(20)

        async def fetch_item(item_id: int) -> Optional[RawArticle]:
            async with semaphore:
                data = await self._fetch_json(f"{HN_API}/item/{item_id}.json")
                if not data:
                    return None
                if data.get("type") != "story":
                    return None
                title = data.get("title", "").strip()
                url = data.get("url") or f"https://news.ycombinator.com/item?id={item_id}"
                if not title:
                    return None
                content = data.get("text", "") or ""
                return RawArticle(
                    url=url,
                    title=title,
                    content=content[:5000],
                    source="hackernews",
                    source_type="api",
                    published_at=datetime.utcfromtimestamp(data.get("time", 0)),
                    author=data.get("by"),
                    region="US",
                    metadata={
                        "score": data.get("score", 0),
                        "comments": data.get("descendants", 0),
                        "hn_id": item_id,
                    },
                )

        tasks = [fetch_item(i) for i in ids]
        results = await asyncio.gather(*tasks)
        for article in results:
            if article:
                yield article
