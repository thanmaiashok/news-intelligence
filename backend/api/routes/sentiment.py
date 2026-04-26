from typing import Optional

from fastapi import APIRouter, Depends, Query

from backend.storage.clickhouse_client import ClickHouseClient
from backend.api.deps import get_clickhouse

router = APIRouter(prefix="/sentiment", tags=["sentiment"])


@router.get("/breakdown")
async def sentiment_breakdown(
    hours: int = Query(24, ge=1, le=168),
    ch: ClickHouseClient = Depends(get_clickhouse),
):
    return await ch.get_sentiment_breakdown(hours=hours)


@router.get("/by-source")
async def sentiment_by_source(
    hours: int = Query(24, ge=1, le=168),
    ch: ClickHouseClient = Depends(get_clickhouse),
):
    return await ch.get_source_stats(hours=hours)
