import asyncio
import json
import logging
from datetime import datetime
from typing import Set

from fastapi import WebSocket, WebSocketDisconnect
from aiokafka import AIOKafkaConsumer

from backend.config import settings

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self._active: Set[WebSocket] = set()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self._active.add(ws)
        logger.info("WS connected (total=%d)", len(self._active))

    def disconnect(self, ws: WebSocket):
        self._active.discard(ws)
        logger.info("WS disconnected (total=%d)", len(self._active))

    async def broadcast(self, data: dict):
        dead = set()
        message = json.dumps(data, default=str)
        for ws in list(self._active):
            try:
                await ws.send_text(message)
            except Exception:
                dead.add(ws)
        self._active -= dead


manager = ConnectionManager()


async def ws_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            try:
                # Keep alive — client sends pings
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
            except asyncio.TimeoutError:
                await websocket.send_text(json.dumps({"type": "ping"}))
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.warning("WS error: %s", e)
        manager.disconnect(websocket)


class KafkaWebSocketBridge:
    """
    Consumes processed articles from Kafka and broadcasts to all WS clients.
    """

    def __init__(self):
        self._consumer = None
        self._running = False

    async def start(self):
        self._consumer = AIOKafkaConsumer(
            settings.KAFKA_PROCESSED_TOPIC,
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            group_id="ws-bridge",
            value_deserializer=lambda v: json.loads(v.decode()),
            auto_offset_reset="latest",
        )
        await self._consumer.start()
        self._running = True
        asyncio.create_task(self._consume())
        logger.info("Kafka→WebSocket bridge started")

    async def _consume(self):
        try:
            async for msg in self._consumer:
                if not self._running:
                    break
                article = msg.value
                await manager.broadcast({
                    "type": "article",
                    "data": {
                        "title": article.get("title", ""),
                        "url": article.get("url", ""),
                        "source": article.get("source", ""),
                        "categories": article.get("categories", []),
                        "sentiment": article.get("sentiment", {}),
                        "region": article.get("region"),
                        "published_at": article.get("published_at"),
                        "entities": article.get("entities", [])[:5],
                    },
                })
        finally:
            await self._consumer.stop()

    async def stop(self):
        self._running = False
        if self._consumer:
            await self._consumer.stop()
