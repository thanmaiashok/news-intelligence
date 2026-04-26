from typing import List, Optional

from fastapi import APIRouter, Depends, Query

from backend.storage.postgres_client import PostgresClient
from backend.api.deps import get_postgres

router = APIRouter(prefix="/articles", tags=["articles"])


@router.get("/")
async def list_articles(
    category: Optional[str] = Query(None),
    sentiment: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    pg: PostgresClient = Depends(get_postgres),
):
    return await pg.get_articles(
        category=category,
        sentiment=sentiment,
        region=region,
        limit=limit,
        offset=offset,
    )


@router.get("/stats")
async def article_stats(pg: PostgresClient = Depends(get_postgres)):
    return await pg.get_stats()
