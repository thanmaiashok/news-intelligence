import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.websockets import WebSocket

from backend.config import settings
from backend.storage.postgres_client import PostgresClient
from backend.storage.clickhouse_client import ClickHouseClient
from backend.storage.neo4j_client import Neo4jClient
from backend.storage.vector_store import VectorStore
from backend.pipeline.trend_detector import TrendDetector
from backend.pipeline.processor import ArticleProcessor
from backend.pipeline.kafka_consumer import PipelineConsumer
from backend.ai.embeddings import EmbeddingService
from backend.ai.rag_engine import RAGEngine
from backend.ai.insights_generator import InsightsGenerator
from backend.api.websocket import ws_endpoint, KafkaWebSocketBridge
from backend.mystery.pipeline import MysteryPipeline
from backend.api.routes import articles, trends, sentiment, graph, insights, crawler_control
from backend.api.routes import mystery as mystery_routes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Global News Intelligence API",
    version="1.0.0",
    description="Real-time news crawling, processing, and intelligence platform",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Route registration
app.include_router(articles.router, prefix="/api/v1")
app.include_router(trends.router, prefix="/api/v1")
app.include_router(sentiment.router, prefix="/api/v1")
app.include_router(graph.router, prefix="/api/v1")
app.include_router(insights.router, prefix="/api/v1")
app.include_router(crawler_control.router, prefix="/api/v1")
app.include_router(mystery_routes.router, prefix="/api/v1")


@app.websocket("/ws/feed")
async def websocket_feed(websocket: WebSocket):
    await ws_endpoint(websocket)


@app.on_event("startup")
async def startup():
    logger.info("Starting News Intelligence API...")

    # Storage
    app.state.postgres = PostgresClient()
    await app.state.postgres.connect()

    app.state.clickhouse = ClickHouseClient()
    await app.state.clickhouse.connect()

    app.state.neo4j = Neo4jClient()
    await app.state.neo4j.connect()

    app.state.vectors = VectorStore()
    await app.state.vectors.setup()

    # Pipeline
    app.state.trends = TrendDetector()
    await app.state.trends.setup()

    # AI — warm models now so first article has no download delay
    app.state.embedder = EmbeddingService()
    app.state.embedder.warm()
    from backend.pipeline.sentiment_analyzer import _load_sentiment_pipeline
    _load_sentiment_pipeline()
    app.state.rag = RAGEngine(app.state.vectors, app.state.embedder)
    app.state.insights = InsightsGenerator()

    # Mystery Intelligence Pipeline
    app.state.mystery = MysteryPipeline(
        neo4j_driver=app.state.neo4j._driver,
        embedder=app.state.embedder,
        vector_store=app.state.vectors,
    )
    await app.state.mystery.setup()

    # Kafka pipeline consumer — share already-connected clients, no duplicate connections
    processor = ArticleProcessor()
    processor.inject_shared(
        pg=app.state.postgres,
        ch=app.state.clickhouse,
        neo4j=app.state.neo4j,
        vectors=app.state.vectors,
        embedder=app.state.embedder,
    )
    await processor.setup()

    # Wire mystery pipeline into article processor
    from backend.pipeline.processor import set_mystery_pipeline
    set_mystery_pipeline(app.state.mystery)

    consumer = PipelineConsumer(processor)
    asyncio.create_task(consumer.start())

    # Kafka → WebSocket bridge
    app.state.ws_bridge = KafkaWebSocketBridge()
    await app.state.ws_bridge.start()

    # Auto-start crawler
    from backend.api.routes.crawler_control import _scheduler as existing_scheduler
    import backend.api.routes.crawler_control as crawler_ctrl
    if not existing_scheduler:
        crawler_ctrl._scheduler = crawler_ctrl.CrawlerScheduler()
        asyncio.create_task(crawler_ctrl._scheduler.start())
        logger.info("Crawler auto-started")

    logger.info("API startup complete")


@app.on_event("shutdown")
async def shutdown():
    await app.state.postgres.disconnect()
    await app.state.neo4j.disconnect()
    await app.state.trends.teardown()
    await app.state.vectors.teardown()
    if hasattr(app.state, "ws_bridge"):
        await app.state.ws_bridge.stop()
    if hasattr(app.state, "mystery"):
        await app.state.mystery.teardown()
    import backend.api.routes.crawler_control as crawler_ctrl
    if crawler_ctrl._scheduler:
        await crawler_ctrl._scheduler.stop()
    logger.info("API shutdown complete")


@app.get("/health")
async def health():
    checks = {
        "postgres": "ok" if getattr(app.state, "postgres", None) and app.state.postgres._pool else "error",
        "clickhouse": "ok" if getattr(app.state, "clickhouse", None) and app.state.clickhouse._client else "error",
        "neo4j": "ok" if getattr(app.state, "neo4j", None) and app.state.neo4j._driver else "error",
    }
    overall = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": overall, "version": "1.0.0", "checks": checks}
