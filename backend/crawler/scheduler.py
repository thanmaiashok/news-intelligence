import asyncio
import logging
import signal
from datetime import datetime
from typing import Dict, List

from backend.config import settings
from backend.pipeline.kafka_producer import NewsKafkaProducer
from .rss_crawler import RSSCrawler, RSS_SOURCES
from .web_crawler import build_web_crawler, WEB_SOURCES
from .reddit_crawler import build_reddit_crawlers
from .hackernews_crawler import HackerNewsCrawler
from .gdelt_crawler import GDELTCrawler
from .mastodon_crawler import MastodonCrawler
from .nitter_crawler import NitterCrawler
from .bluesky_crawler import BlueskyCrawler

logger = logging.getLogger(__name__)


class CrawlerScheduler:
    """Orchestrates all crawlers on configurable intervals."""

    def __init__(self):
        self._producer = NewsKafkaProducer()
        self._running = False
        self._tasks: List[asyncio.Task] = []
        self._stats: Dict = {
            "total_crawled": 0,
            "total_errors": 0,
            "last_run": None,
            "active_crawlers": 0,
            "crawlers_per_minute": 0,
        }
        self._cycle_counts: List[int] = []

    async def start(self):
        await self._producer.start()
        self._running = True
        logger.info("CrawlerScheduler started — sources: RSS(%d) + Web + Reddit + HN + GDELT + Mastodon + Nitter + Bluesky",
                    len(RSS_SOURCES))

        loop = asyncio.get_running_loop()
        loop.add_signal_handler(signal.SIGTERM, self._handle_shutdown)
        loop.add_signal_handler(signal.SIGINT, self._handle_shutdown)

        await asyncio.gather(
            self._rss_loop(),
            self._web_loop(),
            self._social_loop(),      # Reddit + Nitter + Bluesky + Mastodon
            self._api_loop(),         # HN + GDELT
            self._metrics_loop(),
        )

    def _handle_shutdown(self):
        logger.info("Shutdown signal received")
        self._running = False
        for task in self._tasks:
            task.cancel()

    async def _rss_loop(self):
        while self._running:
            try:
                await self._run_rss_batch()
            except Exception as e:
                logger.error("RSS loop error: %s", e)
            await asyncio.sleep(settings.CRAWL_INTERVAL_SECONDS)

    async def _web_loop(self):
        await asyncio.sleep(30)
        while self._running:
            try:
                await self._run_web_batch()
            except Exception as e:
                logger.error("Web loop error: %s", e)
            await asyncio.sleep(settings.CRAWL_INTERVAL_SECONDS * 2)

    async def _social_loop(self):
        """Reddit + Nitter (Twitter) + Bluesky + Mastodon — all free, no auth."""
        await asyncio.sleep(60)
        while self._running:
            try:
                await asyncio.gather(
                    self._run_reddit_batch(),
                    self._run_single_crawler(NitterCrawler()),
                    self._run_single_crawler(BlueskyCrawler()),
                    self._run_single_crawler(MastodonCrawler()),
                    return_exceptions=True,
                )
            except Exception as e:
                logger.error("Social loop error: %s", e)
            await asyncio.sleep(settings.CRAWL_INTERVAL_SECONDS * 3)

    async def _api_loop(self):
        """HackerNews + GDELT — free APIs, no auth."""
        await asyncio.sleep(90)
        while self._running:
            try:
                await asyncio.gather(
                    self._run_single_crawler(HackerNewsCrawler()),
                    self._run_single_crawler(GDELTCrawler()),
                    return_exceptions=True,
                )
            except Exception as e:
                logger.error("API loop error: %s", e)
            await asyncio.sleep(settings.CRAWL_INTERVAL_SECONDS)

    async def _run_rss_batch(self):
        semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_CRAWLERS)
        cycle_count = 0

        async def crawl_source(src):
            nonlocal cycle_count
            async with semaphore:
                crawler = RSSCrawler(src)
                async for article in crawler.run():
                    await self._producer.publish(article)
                    cycle_count += 1
                    self._stats["total_crawled"] += 1

        tasks = [crawl_source(src) for src in RSS_SOURCES]
        self._stats["active_crawlers"] = len(tasks)
        await asyncio.gather(*tasks, return_exceptions=True)
        self._stats["active_crawlers"] = 0
        self._stats["last_run"] = datetime.utcnow().isoformat()
        self._cycle_counts.append(cycle_count)
        if len(self._cycle_counts) > 60:
            self._cycle_counts.pop(0)

    async def _run_web_batch(self):
        semaphore = asyncio.Semaphore(20)

        async def crawl_source(src):
            async with semaphore:
                crawler = build_web_crawler(src)
                async for article in crawler.run():
                    await self._producer.publish(article)
                    self._stats["total_crawled"] += 1

        tasks = [crawl_source(src) for src in WEB_SOURCES]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _run_reddit_batch(self):
        semaphore = asyncio.Semaphore(10)

        async def crawl_sub(crawler):
            async with semaphore:
                async for article in crawler.run():
                    await self._producer.publish(article)
                    self._stats["total_crawled"] += 1

        tasks = [crawl_sub(c) for c in build_reddit_crawlers()]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _run_single_crawler(self, crawler):
        try:
            async for article in crawler.run():
                await self._producer.publish(article)
                self._stats["total_crawled"] += 1
        except Exception as e:
            logger.warning("%s crawl error: %s", type(crawler).__name__, e)

    async def _metrics_loop(self):
        while self._running:
            await asyncio.sleep(60)
            if self._cycle_counts:
                self._stats["crawlers_per_minute"] = sum(self._cycle_counts[-5:]) // min(
                    5, len(self._cycle_counts)
                )

    @property
    def stats(self) -> Dict:
        return self._stats

    async def stop(self):
        self._running = False
        await self._producer.stop()
