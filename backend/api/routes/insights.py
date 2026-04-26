import time
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from backend.ai.insights_generator import InsightsGenerator
from backend.ai.rag_engine import RAGEngine
from backend.pipeline.trend_detector import TrendDetector
from backend.storage.clickhouse_client import ClickHouseClient
from backend.api.deps import get_insights, get_rag, get_trends, get_clickhouse

_insights_cache: dict = {"data": None, "ts": 0}
_INSIGHTS_TTL = 300  # 5 minutes — LLM not called every dashboard poll


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(default=10, ge=1, le=50)


router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("/")
async def generate_insights(
    ig: InsightsGenerator = Depends(get_insights),
    detector: TrendDetector = Depends(get_trends),
    ch: ClickHouseClient = Depends(get_clickhouse),
):
    now = time.time()
    if _insights_cache["data"] and (now - _insights_cache["ts"]) < _INSIGHTS_TTL:
        return _insights_cache["data"]

    trends = await detector.top_trends_cached()
    sentiment = await ch.get_sentiment_breakdown(hours=6)
    categories = await ch.get_category_distribution(hours=6)
    result = await ig.generate_insights(
        trends=trends,
        sentiment_data=sentiment,
        top_entities=[],
        category_dist=categories,
    )
    _insights_cache["data"] = result
    _insights_cache["ts"] = now
    return result


@router.post("/query")
async def rag_query(
    req: QueryRequest,
    rag: RAGEngine = Depends(get_rag),
):
    return await rag.query(req.question, top_k=req.top_k)
