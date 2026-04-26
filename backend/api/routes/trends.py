from fastapi import APIRouter, Depends

from backend.pipeline.trend_detector import TrendDetector
from backend.storage.neo4j_client import Neo4jClient
from backend.storage.clickhouse_client import ClickHouseClient
from backend.api.deps import get_trends, get_neo4j, get_clickhouse

router = APIRouter(prefix="/trends", tags=["trends"])


@router.get("/")
async def get_trends_endpoint(
    detector: TrendDetector = Depends(get_trends),
):
    return await detector.top_trends_cached()


@router.get("/topics")
async def trending_topics(neo4j: Neo4jClient = Depends(get_neo4j)):
    return await neo4j.get_trending_topics(limit=20)


@router.get("/categories")
async def category_distribution(
    hours: int = 24,
    ch: ClickHouseClient = Depends(get_clickhouse),
):
    return await ch.get_category_distribution(hours=hours)


@router.get("/volume")
async def articles_per_minute(
    minutes: int = 60,
    ch: ClickHouseClient = Depends(get_clickhouse),
):
    return await ch.get_articles_per_minute(minutes=minutes)
