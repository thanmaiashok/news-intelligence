"""
Mastodon public timeline — no auth, no API key, fully open.
Uses multiple instances to maximize coverage.
"""
import logging
from datetime import datetime
from typing import AsyncGenerator, Dict, List

from .base_crawler import BaseCrawler, RawArticle

logger = logging.getLogger(__name__)

# Instances with active public timelines — no auth needed
MASTODON_INSTANCES: List[Dict] = [
    {"host": "mastodon.social", "region": None},
    {"host": "fosstodon.org", "region": None},        # tech focus
    {"host": "journalism.social", "region": None},     # journalists
    {"host": "mastodon.online", "region": None},
    {"host": "hachyderm.io", "region": "US"},          # tech/news
]

SOURCE_CONFIG = {"name": "Mastodon", "priority": 3, "region": None}


class MastodonCrawler(BaseCrawler):
    def __init__(self):
        super().__init__(SOURCE_CONFIG)

    async def crawl(self) -> AsyncGenerator[RawArticle, None]:
        for instance in MASTODON_INSTANCES:
            host = instance["host"]
            url = f"https://{host}/api/v1/timelines/public?limit=40&local=false"
            data = await self._fetch_json(url)
            if not data or not isinstance(data, list):
                continue

            for post in data:
                # skip non-news (no URL card, too short)
                card = post.get("card") or {}
                content_raw = post.get("content", "")

                # strip HTML
                import re
                text = re.sub(r"<[^>]+>", " ", content_raw).strip()
                if len(text) < 40:
                    continue

                title = card.get("title") or text[:120]
                url_out = card.get("url") or post.get("url", "")
                if not url_out:
                    continue

                created_at = post.get("created_at", "")
                published_at = datetime.utcnow()
                if created_at:
                    try:
                        published_at = datetime.fromisoformat(
                            created_at.replace("Z", "+00:00")
                        ).replace(tzinfo=None)
                    except Exception:
                        pass

                account = post.get("account", {})
                yield RawArticle(
                    url=url_out,
                    title=title[:300],
                    content=text[:5000],
                    source=f"mastodon/{host}",
                    source_type="social",
                    published_at=published_at,
                    author=account.get("acct"),
                    region=instance.get("region"),
                    metadata={
                        "instance": host,
                        "favourites": post.get("favourites_count", 0),
                        "reblogs": post.get("reblogs_count", 0),
                        "card_description": card.get("description", ""),
                    },
                )
