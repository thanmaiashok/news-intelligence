import logging
import re
from datetime import datetime
from typing import AsyncGenerator, Dict, List

import feedparser

from .base_crawler import BaseCrawler, RawArticle

logger = logging.getLogger(__name__)

# Public Reddit RSS — no API key needed
NEWS_SUBREDDITS: List[Dict] = [
    {"name": "worldnews", "priority": 1, "region": None},
    {"name": "news", "priority": 1, "region": "US"},
    {"name": "geopolitics", "priority": 2, "region": None},
    {"name": "technology", "priority": 2, "region": None},
    {"name": "finance", "priority": 2, "region": None},
    {"name": "Economics", "priority": 2, "region": None},
    {"name": "investing", "priority": 2, "region": None},
    {"name": "UkrainianConflict", "priority": 1, "region": None},
    {"name": "MiddleEastNews", "priority": 2, "region": None},
    {"name": "science", "priority": 3, "region": None},
    {"name": "artificial", "priority": 2, "region": None},
    {"name": "MachineLearning", "priority": 2, "region": None},
]

_TAG_RE = re.compile(r"<[^>]+>")


class RedditCrawler(BaseCrawler):
    def __init__(self, source_config: Dict):
        super().__init__(source_config)
        self._subreddit = source_config["name"]
        self._region = source_config.get("region")

    async def crawl(self) -> AsyncGenerator[RawArticle, None]:
        feed_url = f"https://www.reddit.com/r/{self._subreddit}/hot.rss?limit=50"
        html = await self._fetch(feed_url, headers={"User-Agent": "NewsBot/1.0"})
        if not html:
            return

        feed = feedparser.parse(html)
        for entry in feed.entries:
            try:
                title = entry.get("title", "").strip()
                url = entry.get("link", "").strip()
                if not title or not url:
                    continue

                raw_content = entry.get("summary", "")
                if not raw_content and entry.get("content"):
                    raw_content = entry["content"][0].get("value", "")
                content = _TAG_RE.sub(" ", raw_content).strip()[:5000]

                published_at = datetime.utcnow()
                if entry.get("published_parsed"):
                    try:
                        published_at = datetime(*entry.published_parsed[:6])
                    except Exception:
                        pass

                yield RawArticle(
                    url=url,
                    title=title,
                    content=content,
                    source=f"reddit/r/{self._subreddit}",
                    source_type="reddit",
                    published_at=published_at,
                    author=entry.get("author"),
                    region=self._region,
                    metadata={"subreddit": self._subreddit},
                )
            except Exception as e:
                logger.warning("Reddit RSS entry error [%s]: %s", self._subreddit, e)


def build_reddit_crawlers() -> List[RedditCrawler]:
    return [RedditCrawler(s) for s in NEWS_SUBREDDITS]
