import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

import asyncpg

from backend.config import settings

logger = logging.getLogger(__name__)

CREATE_TABLES_SQL = """
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS articles (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content_hash    VARCHAR(64) UNIQUE NOT NULL,
    url             TEXT NOT NULL,
    title           TEXT NOT NULL,
    content         TEXT,
    source          VARCHAR(255),
    source_type     VARCHAR(50),
    author          VARCHAR(255),
    language        VARCHAR(10) DEFAULT 'en',
    region          VARCHAR(10),
    published_at    TIMESTAMPTZ,
    crawled_at      TIMESTAMPTZ DEFAULT NOW(),
    processed_at    TIMESTAMPTZ,
    categories      TEXT[],
    category_scores JSONB DEFAULT '{}',
    sentiment_label VARCHAR(20),
    sentiment_score FLOAT,
    sentiment_data  JSONB DEFAULT '{}',
    entities        JSONB DEFAULT '[]',
    metadata        JSONB DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_articles_published ON articles(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source);
CREATE INDEX IF NOT EXISTS idx_articles_categories ON articles USING GIN(categories);
CREATE INDEX IF NOT EXISTS idx_articles_sentiment ON articles(sentiment_label);
CREATE INDEX IF NOT EXISTS idx_articles_region ON articles(region);
CREATE INDEX IF NOT EXISTS idx_articles_crawled ON articles(crawled_at DESC);

CREATE TABLE IF NOT EXISTS crawler_sources (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(255) UNIQUE NOT NULL,
    url         TEXT NOT NULL,
    source_type VARCHAR(50),
    priority    INTEGER DEFAULT 5,
    region      VARCHAR(10),
    enabled     BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    last_crawled TIMESTAMPTZ,
    article_count BIGINT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS crawler_runs (
    id          SERIAL PRIMARY KEY,
    started_at  TIMESTAMPTZ DEFAULT NOW(),
    ended_at    TIMESTAMPTZ,
    articles_crawled INTEGER DEFAULT 0,
    errors      INTEGER DEFAULT 0,
    status      VARCHAR(20) DEFAULT 'running'
);
"""


class PostgresClient:
    def __init__(self):
        self._pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        dsn = settings.POSTGRES_URL.replace("+asyncpg", "")
        self._pool = await asyncpg.create_pool(
            dsn,
            min_size=5,
            max_size=20,
            command_timeout=30,
        )
        await self._init_schema()
        logger.info("PostgreSQL connected")

    async def _init_schema(self):
        async with self._pool.acquire() as conn:
            await conn.execute(CREATE_TABLES_SQL)

    async def disconnect(self):
        if self._pool:
            await self._pool.close()

    async def upsert_article(self, article: Dict):
        sql = """
        INSERT INTO articles (
            content_hash, url, title, content, source, source_type,
            author, language, region, published_at, crawled_at, processed_at,
            categories, category_scores, sentiment_label, sentiment_score,
            sentiment_data, entities, metadata
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12,
            $13, $14, $15, $16, $17, $18, $19
        )
        ON CONFLICT (content_hash) DO UPDATE SET
            processed_at = EXCLUDED.processed_at,
            categories = EXCLUDED.categories,
            category_scores = EXCLUDED.category_scores,
            sentiment_label = EXCLUDED.sentiment_label,
            sentiment_score = EXCLUDED.sentiment_score,
            sentiment_data = EXCLUDED.sentiment_data,
            entities = EXCLUDED.entities
        """
        sentiment = article.get("sentiment", {})
        published_at = article.get("published_at")
        if isinstance(published_at, str):
            try:
                from dateutil.parser import parse
                published_at = parse(published_at)
            except Exception:
                published_at = datetime.utcnow()

        async with self._pool.acquire() as conn:
            await conn.execute(
                sql,
                article.get("content_hash"),
                article.get("url"),
                article.get("title"),
                article.get("content", "")[:50000],
                article.get("source"),
                article.get("source_type"),
                article.get("author"),
                article.get("language", "en"),
                article.get("region"),
                published_at,
                datetime.utcnow(),
                datetime.utcnow(),
                article.get("categories", []),
                json.dumps(article.get("category_scores", {})),
                sentiment.get("label", "neutral"),
                sentiment.get("score", 0.5),
                json.dumps(sentiment),
                json.dumps(article.get("entities", [])),
                json.dumps(article.get("metadata", {})),
            )

    async def get_articles(
        self,
        category: Optional[str] = None,
        sentiment: Optional[str] = None,
        region: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict]:
        conditions = []
        params = []
        p = 1

        if category:
            conditions.append(f"${p} = ANY(categories)")
            params.append(category)
            p += 1
        if sentiment:
            conditions.append(f"sentiment_label = ${p}")
            params.append(sentiment)
            p += 1
        if region:
            conditions.append(f"region = ${p}")
            params.append(region)
            p += 1

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"""
            SELECT content_hash, url, title, source, source_type, published_at,
                   categories, sentiment_label, sentiment_score, region, author
            FROM articles
            {where}
            ORDER BY published_at DESC
            LIMIT ${p} OFFSET ${p+1}
        """
        params.extend([limit, offset])

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [dict(r) for r in rows]

    async def get_stats(self) -> Dict:
        sql = """
        SELECT
            COUNT(*) as total,
            COUNT(CASE WHEN crawled_at > NOW() - INTERVAL '1 hour' THEN 1 END) as last_hour,
            COUNT(CASE WHEN crawled_at > NOW() - INTERVAL '1 day' THEN 1 END) as last_day,
            COUNT(DISTINCT source) as sources
        FROM articles
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(sql)
            return dict(row)
