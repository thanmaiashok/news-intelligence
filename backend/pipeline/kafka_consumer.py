import asyncio
import json
import logging
from typing import Callable, Awaitable

from aiokafka import AIOKafkaConsumer

from backend.config import settings

logger = logging.getLogger(__name__)

MessageHandler = Callable[[dict], Awaitable[None]]


class NewsKafkaConsumer:
    def __init__(self, topic: str, group_id: str = None, handler: MessageHandler = None):
        self._topic = topic
        self._group_id = group_id or settings.KAFKA_GROUP_ID
        self._handler = handler
        self._consumer = None
        self._running = False

    async def start(self, handler: MessageHandler = None):
        if handler:
            self._handler = handler

        self._consumer = AIOKafkaConsumer(
            self._topic,
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            group_id=self._group_id,
            value_deserializer=lambda v: json.loads(v.decode()),
            auto_offset_reset="earliest",
            enable_auto_commit=True,
            auto_commit_interval_ms=5000,
            max_poll_records=100,
            fetch_max_bytes=52428800,  # 50MB
        )
        await self._consumer.start()
        self._running = True
        logger.info("Kafka consumer started on topic: %s", self._topic)
        await self._consume_loop()

    async def _consume_loop(self):
        try:
            async for msg in self._consumer:
                if not self._running:
                    break
                try:
                    await self._handler(msg.value)
                except Exception as e:
                    logger.error(
                        "Message handler error [topic=%s offset=%d]: %s",
                        self._topic, msg.offset, e
                    )
        finally:
            await self._consumer.stop()

    async def stop(self):
        self._running = False
        if self._consumer:
            await self._consumer.stop()


class PipelineConsumer:
    """Multi-topic consumer that chains the full processing pipeline."""

    def __init__(self, pipeline_processor):
        self._processor = pipeline_processor
        self._raw_consumer = NewsKafkaConsumer(
            topic=settings.KAFKA_RAW_TOPIC,
            group_id=f"{settings.KAFKA_GROUP_ID}-raw",
        )

    async def start(self):
        await self._raw_consumer.start(handler=self._processor.process)

    async def stop(self):
        await self._raw_consumer.stop()
