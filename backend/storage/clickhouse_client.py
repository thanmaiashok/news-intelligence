import asyncio
import logging
from datetime import datetime
from functools import partial
from typing import Dict, List, Optional

import clickhouse_connect

from backend.config import settings

logger = logging.getLogger(__name__)

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS news_articles (
    content_hash    String,
    url             String,
    title           String,
    source          String,
    source_type     String,
    language        String,
    region          String,
    published_at    DateTime,
    crawled_at      DateTime DEFAULT now(),
    categories      Array(String),
    sentiment_label String,
    sentiment_score Float32,
    entity_count    UInt16,
    word_count      UInt32
)
ENGINE = MergeTree()
ORDER BY (published_at, source, sentiment_label)
PARTITION BY toYYYYMM(published_at)
SETTINGS index_granularity = 8192;

CREATE TABLE IF NOT EXISTS trend_snapshots (
    snapshot_at     DateTime DEFAULT now(),
    kind            String,
    name            String,
    current_count   UInt32,
    prev_count      UInt32,
    velocity        Float32,
    is_spike        UInt8
)
ENGINE = MergeTree()
ORDER BY (snapshot_at, kind, name)
PARTITION BY toYYYYMMDD(snapshot_at);
"""


class ClickHouseClient:
    def __init__(self):
        self._client = None
        self._loop = None

    async def connect(self):
        self._loop = asyncio.get_event_loop()
        self._client = await self._loop.run_in_executor(
            None,
            partial(
                clickhouse_connect.get_client,
                host=settings.CLICKHOUSE_HOST,
                port=settings.CLICKHOUSE_PORT,
                username=settings.CLICKHOUSE_USER,
                password=settings.CLICKHOUSE_PASSWORD,
                database=settings.CLICKHOUSE_DB,
            ),
        )
        await self._loop.run_in_executor(None, self._init_schema)
        logger.info("ClickHouse connected")

    def _init_schema(self):
        for statement in CREATE_TABLE_SQL.strip().split(";"):
            stmt = statement.strip()
            if stmt:
                try:
                    self._client.command(stmt)
                except Exception as e:
                    logger.warning("ClickHouse schema init: %s", e)

    async def _run(self, fn, *args, **kwargs):
        """Run a sync ClickHouse call in thread pool to avoid blocking event loop."""
        loop = self._loop or asyncio.get_event_loop()
        return await loop.run_in_executor(None, partial(fn, *args, **kwargs))

    async def insert_article(self, article: Dict):
        if not self._client:
            return

        published_at = article.get("published_at", datetime.utcnow())
        if isinstance(published_at, str):
            try:
                from dateutil.parser import parse
                published_at = parse(published_at)
            except Exception:
                published_at = datetime.utcnow()

        content = article.get("content", "")
        word_count = len(content.split()) if content else 0

        row = [
            article.get("content_hash", ""),
            article.get("url", ""),
            article.get("title", "")[:500],
            article.get("source", ""),
            article.get("source_type", ""),
            article.get("language", "en"),
            article.get("region", "") or "",
            published_at,
            article.get("categories", []),
            article.get("sentiment", {}).get("label", "neutral"),
            float(article.get("sentiment", {}).get("score", 0.5)),
            len(article.get("entities", [])),
            word_count,
        ]

        try:
            await self._run(
                self._client.insert,
                "news_articles",
                [row],
                column_names=[
                    "content_hash", "url", "title", "source", "source_type",
                    "language", "region", "published_at", "categories",
                    "sentiment_label", "sentiment_score", "entity_count", "word_count",
                ],
            )
        except Exception as e:
            logger.warning("ClickHouse insert error: %s", e)

    async def get_sentiment_breakdown(self, hours: int = 24) -> List[Dict]:
        sql = f"""
        SELECT
            sentiment_label,
            count() as count,
            avg(sentiment_score) as avg_score
        FROM news_articles
        WHERE crawled_at >= now() - INTERVAL {hours} HOUR
        GROUP BY sentiment_label
        ORDER BY count DESC
        """
        try:
            result = await self._run(self._client.query, sql)
            return [
                {"label": r[0], "count": r[1], "avg_score": round(r[2], 4)}
                for r in result.result_rows
            ]
        except Exception as e:
            logger.warning("ClickHouse query error: %s", e)
            return []

    async def get_articles_per_minute(self, minutes: int = 60) -> List[Dict]:
        sql = f"""
        SELECT
            toStartOfMinute(crawled_at) as minute,
            count() as count
        FROM news_articles
        WHERE crawled_at >= now() - INTERVAL {minutes} MINUTE
        GROUP BY minute
        ORDER BY minute
        """
        try:
            result = await self._run(self._client.query, sql)
            return [
                {"minute": str(r[0]), "count": r[1]}
                for r in result.result_rows
            ]
        except Exception as e:
            logger.warning("ClickHouse query error: %s", e)
            return []

    async def get_category_distribution(self, hours: int = 24) -> List[Dict]:
        sql = f"""
        SELECT
            arrayJoin(categories) as category,
            count() as count
        FROM news_articles
        WHERE crawled_at >= now() - INTERVAL {hours} HOUR
        GROUP BY category
        ORDER BY count DESC
        LIMIT 20
        """
        try:
            result = await self._run(self._client.query, sql)
            return [{"category": r[0], "count": r[1]} for r in result.result_rows]
        except Exception as e:
            logger.warning("ClickHouse query error: %s", e)
            return []

    async def get_source_stats(self, hours: int = 24) -> List[Dict]:
        sql = f"""
        SELECT source, count() as count, max(crawled_at) as last_seen
        FROM news_articles
        WHERE crawled_at >= now() - INTERVAL {hours} HOUR
        GROUP BY source
        ORDER BY count DESC
        LIMIT 50
        """
        try:
            result = await self._run(self._client.query, sql)
            return [
                {"source": r[0], "count": r[1], "last_seen": str(r[2])}
                for r in result.result_rows
            ]
        except Exception as e:
            logger.warning("ClickHouse query error: %s", e)
            return []
