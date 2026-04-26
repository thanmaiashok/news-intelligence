"""
Bluesky AT Protocol public search API — no auth, no key.
https://public.api.bsky.app — open public endpoint.
"""
import logging
import re
from datetime import datetime
from typing import AsyncGenerator, Dict, List

from .base_crawler import BaseCrawler, RawArticle

logger = logging.getLogger(__name__)

BSKY_API = "https://public.api.bsky.app/xrpc"

SEARCH_QUERIES: List[Dict] = [
    {"q": "breaking news", "label": "breaking"},
    {"q": "world news", "label": "world"},
    {"q": "politics", "label": "politics"},
    {"q": "economy finance", "label": "finance"},
    {"q": "technology AI", "label": "tech"},
    {"q": "climate science", "label": "climate"},
    {"q": "war conflict", "label": "conflict"},
    {"q": "health medicine", "label": "health"},
]

_TAG_RE = re.compile(r"<[^>]+>")

SOURCE_CONFIG = {"name": "Bluesky", "priority": 2, "region": None}


class BlueskyCrawler(BaseCrawler):
    def __init__(self):
        super().__init__(SOURCE_CONFIG)

    async def crawl(self) -> AsyncGenerator[RawArticle, None]:
        headers = {"Accept": "application/json"}

        for query in SEARCH_QUERIES:
            url = f"{BSKY_API}/app.bsky.feed.searchPosts?q={query['q'].replace(' ', '%20')}&limit=25&sort=latest"
            data = await self._fetch_json(url, headers=headers)
            if not data or "posts" not in data:
                continue

            for post in data["posts"]:
                record = post.get("record", {})
                text = record.get("text", "").strip()
                if len(text) < 30:
                    continue

                # prefer embed external link
                embed = post.get("embed") or {}
                external = embed.get("external") or {}
                ext_url = external.get("uri", "")
                ext_title = external.get("title", "")
                ext_desc = external.get("description", "")

                uri = post.get("uri", "")
                # convert at:// uri to bsky.app url
                if uri.startswith("at://"):
                    parts = uri.replace("at://", "").split("/")
                    if len(parts) >= 3:
                        post_url = f"https://bsky.app/profile/{parts[0]}/post/{parts[2]}"
                    else:
                        post_url = ext_url or uri
                else:
                    post_url = ext_url or uri

                if not post_url:
                    continue

                title = ext_title or text[:120]
                content = "\n".join(filter(None, [text, ext_desc]))

                indexed_at = post.get("indexedAt", "")
                published_at = datetime.utcnow()
                if indexed_at:
                    try:
                        published_at = datetime.fromisoformat(
                            indexed_at.replace("Z", "+00:00")
                        ).replace(tzinfo=None)
                    except Exception:
                        pass

                author = post.get("author", {})
                yield RawArticle(
                    url=ext_url or post_url,
                    title=title[:300],
                    content=content[:5000],
                    source=f"bluesky/{query['label']}",
                    source_type="social",
                    published_at=published_at,
                    author=author.get("handle"),
                    region=None,
                    metadata={
                        "like_count": post.get("likeCount", 0),
                        "repost_count": post.get("repostCount", 0),
                        "reply_count": post.get("replyCount", 0),
                        "post_url": post_url,
                        "query": query["label"],
                    },
                )
