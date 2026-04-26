import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional

from backend.config import settings
from backend.pipeline.deduplicator import Deduplicator
from backend.pipeline.classifier import ArticleClassifier
from backend.pipeline.sentiment_analyzer import SentimentAnalyzer
from backend.pipeline.ner_extractor import NERExtractor
from backend.pipeline.trend_detector import TrendDetector
from backend.storage.postgres_client import PostgresClient
from backend.storage.clickhouse_client import ClickHouseClient
from backend.storage.neo4j_client import Neo4jClient
from backend.storage.s3_client import S3Client
from backend.storage.vector_store import VectorStore
from backend.ai.embeddings import EmbeddingService

logger = logging.getLogger(__name__)

# Lazy import to avoid circular deps — mystery pipeline attached post-startup
_mystery_pipeline = None


def set_mystery_pipeline(pipeline):
    global _mystery_pipeline
    _mystery_pipeline = pipeline


class ArticleProcessor:
    """
    Full pipeline: dedup → classify → sentiment → NER → trend → store.
    Called by Kafka consumer per raw article.
    """

    def __init__(self):
        self._dedup = Deduplicator()
        self._classifier = ArticleClassifier()
        self._sentiment = SentimentAnalyzer()
        self._ner = NERExtractor()
        self._trends = TrendDetector()
        self._pg: Optional[PostgresClient] = None
        self._ch: Optional[ClickHouseClient] = None
        self._neo4j: Optional[Neo4jClient] = None
        self._s3: Optional[S3Client] = None
        self._vectors: Optional[VectorStore] = None
        self._embedder: Optional[EmbeddingService] = None

    async def setup(self):
        await self._dedup.setup()
        await self._trends.setup()

        self._pg = PostgresClient()
        await self._pg.connect()

        self._ch = ClickHouseClient()
        await self._ch.connect()

        self._neo4j = Neo4jClient()
        await self._neo4j.connect()

        self._s3 = S3Client()
        self._vectors = VectorStore()
        await self._vectors.setup()

        self._embedder = EmbeddingService()
        logger.info("ArticleProcessor fully initialized")

    async def teardown(self):
        await self._dedup.teardown()
        await self._trends.teardown()
        if self._pg:
            await self._pg.disconnect()
        if self._neo4j:
            await self._neo4j.disconnect()
        if self._vectors:
            await self._vectors.teardown()

    async def process(self, raw: Dict):
        try:
            # Dedup check
            is_dup = await self._dedup.is_duplicate(
                raw.get("content_hash", ""),
                raw.get("title", ""),
                raw.get("content", ""),
            )
            if is_dup:
                return

            title = raw.get("title", "")
            content = raw.get("content", "")

            # Classify
            categories = self._classifier.classify(title, content)
            cat_labels = [c[0] for c in categories]

            # Sentiment
            sentiment = self._sentiment.analyze(title, content)

            # NER
            entities = self._ner.flat_entities(title, content)

            # Embedding
            embedding = self._embedder.encode(f"{title}. {content[:512]}")

            enriched = {
                **raw,
                "categories": cat_labels,
                "category_scores": dict(categories),
                "sentiment": sentiment,
                "entities": entities,
                "embedding": embedding.tolist() if hasattr(embedding, "tolist") else list(embedding),
                "processed_at": datetime.utcnow().isoformat(),
            }

            # Store concurrently
            tasks = [
                self._store_s3(enriched),
                self._store_postgres(enriched),
                self._store_clickhouse(enriched),
                self._store_neo4j(enriched),
                self._store_vector(enriched),
                self._update_trends(enriched),
            ]
            if _mystery_pipeline:
                tasks.append(_mystery_pipeline.process_article(enriched))

            await asyncio.gather(*tasks, return_exceptions=True)

        except Exception as e:
            logger.error("Processor error: %s", e, exc_info=True)

    async def _store_s3(self, article: Dict):
        try:
            await self._s3.store_article(article)
        except Exception as e:
            logger.warning("S3 store error: %s", e)

    async def _store_postgres(self, article: Dict):
        try:
            await self._pg.upsert_article(article)
        except Exception as e:
            logger.warning("Postgres store error: %s", e)

    async def _store_clickhouse(self, article: Dict):
        try:
            await self._ch.insert_article(article)
        except Exception as e:
            logger.warning("ClickHouse store error: %s", e)

    async def _store_neo4j(self, article: Dict):
        try:
            await self._neo4j.store_article(article)
        except Exception as e:
            logger.warning("Neo4j store error: %s", e)

    async def _store_vector(self, article: Dict):
        try:
            await self._vectors.upsert(
                article["content_hash"],
                article["embedding"],
                metadata={
                    "title": article["title"][:200],
                    "url": article["url"],
                    "categories": article.get("categories", []),
                    "sentiment": article.get("sentiment", {}).get("label", "neutral"),
                    "published_at": str(article.get("published_at", "")),
                },
            )
        except Exception as e:
            logger.warning("Vector store error: %s", e)

    async def _update_trends(self, article: Dict):
        try:
            await self._trends.ingest(
                categories=article.get("categories", []),
                entities=article.get("entities", []),
                title=article.get("title", ""),
            )
        except Exception as e:
            logger.warning("Trend update error: %s", e)
