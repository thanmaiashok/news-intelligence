from typing import Optional

from fastapi import APIRouter, Depends, Query

from backend.mystery.pipeline import MysteryPipeline
from backend.api.deps import get_mystery

router = APIRouter(prefix="/mystery", tags=["mystery"])


@router.get("/feed")
async def mystery_feed(
    limit: int = Query(50, le=200),
    subcategory: Optional[str] = Query(None),
    min_anomaly: float = Query(0.0, ge=0.0, le=1.0),
    pipeline: MysteryPipeline = Depends(get_mystery),
):
    return await pipeline.get_recent_events(
        limit=limit,
        subcategory=subcategory,
        min_anomaly=min_anomaly,
    )


@router.get("/verdicts")
async def mystery_verdicts(
    limit: int = Query(20, le=100),
    pipeline: MysteryPipeline = Depends(get_mystery),
):
    return await pipeline.get_recent_verdicts(limit=limit)


@router.get("/signals")
async def anomaly_signals(
    pipeline: MysteryPipeline = Depends(get_mystery),
):
    return await pipeline.get_anomaly_signals()


@router.get("/scoreboard")
async def anomaly_scoreboard(
    limit: int = Query(20, le=100),
    pipeline: MysteryPipeline = Depends(get_mystery),
):
    return await pipeline.get_scoreboard(limit=limit)
