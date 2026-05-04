import asyncio
import hashlib
import time
import random
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import AsyncGenerator, Dict, List, Optional
from urllib.robotparser import RobotFileParser
from urllib.parse import urlparse

import aiohttp
import redis.asyncio as aioredis

from backend.config import settings

logger = logging.getLogger(__name__)


@dataclass
class RawArticle:
    url: str
    title: str
    content: str
    source: str
    source_type: str  # rss | web | reddit | twitter | api
    published_at: Optional[datetime] = None
    author: Optional[str] = None
    language: str = "en"
    region: Optional[str] = None
    raw_html: Optional[str] = None
    metadata: Dict = field(default_factory=dict)
    crawled_at: datetime = field(default_factory=datetime.utcnow)
    content_hash: str = field(init=False)

    def __post_init__(self):
        self.content_hash = hashlib.sha256(
            (self.title + self.content[:500]).encode()
        ).hexdigest()


class RobotsTxtCache:
    def __init__(self, ttl: int = 3600):
        self._cache: Dict[str, tuple] = {}
        self._ttl = ttl

    def _fetch_robots(self, base: str) -> RobotFileParser:
        rp = RobotFileParser()
        rp.set_url(f"{base}/robots.txt")
        rp.read()
        return rp

    async def can_fetch_async(self, url: str, user_agent: str = "*") -> bool:
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        now = time.time()

        if base in self._cache:
            parser, ts = self._cache[base]
            if now - ts < self._ttl:
                return parser.can_fetch(user_agent, url)

        try:
            loop = asyncio.get_event_loop()
            rp = await loop.run_in_executor(None, self._fetch_robots, base)
            self._cache[base] = (rp, now)
            return rp.can_fetch(user_agent, url)
        except Exception:
            return True


robots_cache = RobotsTxtCache()


class BaseCrawler(ABC):
    def __init__(self, source_config: Dict):
        self.source_config = source_config
        self.name = source_config.get("name", "unknown")
        self.priority = source_config.get("priority", 5)
        self._session: Optional[aiohttp.ClientSession] = None
        self._redis: Optional[aioredis.Redis] = None
        self._crawl_count = 0
        self._error_count = 0

    async def setup(self):
        try:
            import aiodns
            resolver = aiohttp.AsyncResolver()
        except ImportError:
            resolver = aiohttp.ThreadedResolver()
        connector = aiohttp.TCPConnector(
            limit=100,
            limit_per_host=10,
            ttl_dns_cache=300,
            ssl=False,
            resolver=resolver,
        )
        timeout = aiohttp.ClientTimeout(total=settings.CRAWL_TIMEOUT_SECONDS)
        self._session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={"User-Agent": self._random_user_agent()},
        )
        self._redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

    async def teardown(self):
        if self._session:
            await self._session.close()
        if self._redis:
            await self._redis.aclose()

    def _random_user_agent(self) -> str:
        return random.choice(settings.USER_AGENTS)

    def _random_proxy(self) -> Optional[str]:
        if settings.PROXY_LIST:
            return random.choice(settings.PROXY_LIST)
        return None

    async def _is_seen(self, content_hash: str) -> bool:
        key = f"seen:{content_hash}"
        result = await self._redis.set(key, "1", nx=True, ex=86400 * 7)
        return result is None  # None means key already existed

    async def _fetch(self, url: str, headers: Optional[Dict] = None) -> Optional[str]:
        if not await robots_cache.can_fetch_async(url):
            logger.debug("robots.txt block: %s", url)
            return None

        # Random delay 0.5–2.5s to avoid looking like a bot
        await asyncio.sleep(random.uniform(0.5, 2.5))

        proxy = self._random_proxy()
        try:
            async with self._session.get(url, proxy=proxy, headers=headers) as resp:
                if resp.status == 200:
                    return await resp.text(errors="replace")
                if resp.status == 429:
                    retry_after = int(resp.headers.get("Retry-After", 60))
                    logger.warning("Rate limited %s — backing off %ds", url, retry_after)
                    await asyncio.sleep(min(retry_after, 120))
                    return None
                if resp.status in (403, 451):
                    logger.warning("Blocked (HTTP %d): %s", resp.status, url)
                    return None
                logger.warning("HTTP %d for %s", resp.status, url)
                return None
        except asyncio.TimeoutError:
            logger.warning("Timeout: %s", url)
            self._error_count += 1
            return None
        except Exception as e:
            logger.warning("Fetch error %s: %s", url, e)
            self._error_count += 1
            return None

    async def _fetch_json(self, url: str, headers: Optional[Dict] = None) -> Optional[dict]:
        text = await self._fetch(url, headers=headers)
        if not text:
            return None
        import json
        try:
            return json.loads(text)
        except Exception as e:
            logger.warning("JSON parse error %s: %s", url, e)
            return None

    @abstractmethod
    async def crawl(self) -> AsyncGenerator[RawArticle, None]:
        ...

    async def run(self) -> AsyncGenerator[RawArticle, None]:
        await self.setup()
        try:
            async for article in self.crawl():
                if not await self._is_seen(article.content_hash):
                    self._crawl_count += 1
                    yield article
                else:
                    logger.debug("Duplicate skip: %s", article.url)
        finally:
            await self.teardown()

    @property
    def stats(self) -> Dict:
        return {
            "name": self.name,
            "crawled": self._crawl_count,
            "errors": self._error_count,
        }
