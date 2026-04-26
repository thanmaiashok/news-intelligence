"""
Mystery Intelligence Pipeline

Integration point with existing ArticleProcessor.
Runs after standard processing: classify → detect → pattern_link → llm_reason → store.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

import redis.asyncio as aioredis

from backend.config import settings
from backend.mystery.mystery_classifier import classify_mystery, MysteryEvent
from backend.mystery.anomaly_detector import AnomalyDetector
from backend.mystery.pattern_engine import PatternEngine
from backend.mystery.llm_reasoner import LLMReasoner
from backend.ai.embeddings import EmbeddingService
from backend.storage.vector_store import VectorStore

logger = logging.getLogger(__name__)

MYSTERY_BUFFER_MAX = 200        # max events held in memory per cycle
MYSTERY_CYCLE_SIZE = 50         # trigger pattern analysis at this many new events
VERDICT_TTL_SECONDS = 86400 * 3  # store verdicts 3 days


class MysteryPipeline:
    def __init__(
        self,
        neo4j_driver,
        embedder: EmbeddingService,
        vector_store: VectorStore,
    ):
        self._detector = AnomalyDetector()
        self._pattern_engine = PatternEngine(
            neo4j_driver=neo4j_driver,
            embedder=embedder,
            vector_store=vector_store,
            detector=self._detector,
        )
        self._reasoner = LLMReasoner()
        self._redis: Optional[aioredis.Redis] = None
        self._pending_events: List[MysteryEvent] = []

    async def setup(self):
        await self._detector.setup()
        self._redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        logger.info("MysteryPipeline initialized")

    async def teardown(self):
        await self._detector.teardown()
        if self._redis:
            await self._redis.aclose()

    async def process_article(self, article: Dict) -> Optional[MysteryEvent]:
        """
        Step 1: mystery_classification()
        Step 2: anomaly_detection() ingestion
        Step 3: buffer for batch pattern analysis
        """
        event = classify_mystery(article)
        if not event:
            return None

        logger.info(
            "Mystery event classified: [%s] %s (anomaly=%.2f cred=%.2f)",
            event.subcategory_label,
            event.title[:60],
            event.anomaly_score,
            event.credibility_score,
        )

        await self._detector.ingest(event)
        self._pending_events.append(event)

        # Store in Redis for API serving
        await self._store_mystery_event(event)

        # Trigger pattern analysis when buffer fills
        if len(self._pending_events) >= MYSTERY_CYCLE_SIZE:
            asyncio.create_task(self._run_pattern_cycle())

        return event

    async def _run_pattern_cycle(self):
        """
        Steps: pattern_linking() → llm_reasoning() → store verdicts
        """
        if not self._pending_events:
            return

        events = self._pending_events[:MYSTERY_BUFFER_MAX]
        self._pending_events = self._pending_events[MYSTERY_BUFFER_MAX:]

        try:
            # pattern_linking()
            clusters = await self._pattern_engine.link_events(events)

            if not clusters or (len(clusters) == 1 and clusters[0].get("verdict") == "NO_STRONG_CONNECTION"):
                logger.debug("No strong patterns found in mystery batch of %d events", len(events))
                return

            # llm_reasoning()
            event_map = {e.article_hash: e for e in events}
            verdicts = await self._reasoner.analyze_batch(clusters, event_map)

            # Store verdicts
            for verdict in verdicts:
                await self._store_verdict(verdict)

            logger.info(
                "Mystery cycle complete: %d events → %d clusters → %d verdicts",
                len(events), len(clusters), len(verdicts),
            )
        except Exception as e:
            logger.error("Mystery pipeline cycle error: %s", e, exc_info=True)

    async def _store_mystery_event(self, event: MysteryEvent):
        """Stores mystery event for API /mystery/feed endpoint."""
        key = "mystery:events:recent"
        payload = json.dumps({
            "article_hash": event.article_hash,
            "url": event.url,
            "title": event.title,
            "source": event.source,
            "published_at": event.published_at,
            "subcategory": event.subcategory,
            "subcategory_label": event.subcategory_label,
            "credibility_score": event.credibility_score,
            "anomaly_score": event.anomaly_score,
            "source_reliability": event.source_reliability,
            "matched_signals": event.matched_signals,
            "region": event.region,
            "content_snippet": event.content_snippet[:300],
        })
        score = datetime.utcnow().timestamp()
        await self._redis.zadd(key, {payload: score})
        await self._redis.zremrangebyrank(key, 0, -501)  # keep 500 most recent
        await self._redis.expire(key, 86400 * 7)

    async def _store_verdict(self, verdict: Dict):
        """Stores LLM verdict for /mystery/verdicts endpoint."""
        key = "mystery:verdicts:recent"
        payload = json.dumps(verdict, default=str)
        score = datetime.utcnow().timestamp()
        await self._redis.zadd(key, {payload: score})
        await self._redis.zremrangebyrank(key, 0, -101)  # keep 100 recent
        await self._redis.expire(key, VERDICT_TTL_SECONDS)

    async def get_recent_events(
        self,
        limit: int = 50,
        subcategory: Optional[str] = None,
        min_anomaly: float = 0.0,
    ) -> List[Dict]:
        items = await self._redis.zrevrange("mystery:events:recent", 0, limit * 3 - 1)
        events = []
        for item in items:
            try:
                e = json.loads(item)
                if subcategory and e.get("subcategory") != subcategory:
                    continue
                if e.get("anomaly_score", 0) < min_anomaly:
                    continue
                events.append(e)
                if len(events) >= limit:
                    break
            except Exception:
                continue
        return events

    async def get_recent_verdicts(self, limit: int = 20) -> List[Dict]:
        items = await self._redis.zrevrange("mystery:verdicts:recent", 0, limit - 1)
        results = []
        for item in items:
            try:
                results.append(json.loads(item))
            except Exception:
                continue
        return results

    async def get_anomaly_signals(self) -> List[Dict]:
        return await self._detector.detect_signals()

    async def get_scoreboard(self, limit: int = 20) -> List[Dict]:
        """Top mystery events sorted by anomaly_score."""
        events = await self.get_recent_events(limit=200)
        return sorted(events, key=lambda x: x.get("anomaly_score", 0), reverse=True)[:limit]
