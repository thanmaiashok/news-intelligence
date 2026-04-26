import json
import logging
from dataclasses import asdict
from datetime import datetime
from typing import Optional

from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError

from backend.config import settings
from backend.crawler.base_crawler import RawArticle

logger = logging.getLogger(__name__)


def _default_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not JSON serializable")


class NewsKafkaProducer:
    def __init__(self):
        self._producer: Optional[AIOKafkaProducer] = None

    async def start(self):
        self._producer = AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v, default=_default_serializer).encode(),
            compression_type="gzip",
            max_batch_size=163840,
            linger_ms=10,
            acks="all",
            enable_idempotence=True,
            max_in_flight_requests_per_connection=5,
        )
        await self._producer.start()
        logger.info("Kafka producer started")

    async def stop(self):
        if self._producer:
            await self._producer.stop()

    async def publish(self, article: RawArticle):
        if not self._producer:
            raise RuntimeError("Producer not started")

        payload = asdict(article)
        try:
            await self._producer.send_and_wait(
                settings.KAFKA_RAW_TOPIC,
                value=payload,
                key=article.content_hash.encode(),
            )
        except KafkaError as e:
            logger.error("Kafka publish error: %s", e)
            raise

    async def publish_processed(self, article_dict: dict):
        await self._producer.send_and_wait(
            settings.KAFKA_PROCESSED_TOPIC,
            value=article_dict,
            key=article_dict.get("content_hash", "").encode(),
        )

    async def publish_trend(self, trend_dict: dict):
        await self._producer.send_and_wait(
            settings.KAFKA_TRENDS_TOPIC,
            value=trend_dict,
        )
