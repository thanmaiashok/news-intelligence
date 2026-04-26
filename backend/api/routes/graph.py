from typing import Optional

from fastapi import APIRouter, Depends, Query

from backend.storage.neo4j_client import Neo4jClient
from backend.api.deps import get_neo4j

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("/subgraph")
async def get_subgraph(
    center: Optional[str] = Query(None),
    depth: int = Query(2, ge=1, le=3),
    limit: int = Query(100, le=500),
    neo4j: Neo4jClient = Depends(get_neo4j),
):
    return await neo4j.get_graph_subgraph(center=center, depth=depth, limit=limit)


@router.get("/entity/{name}/connections")
async def entity_connections(
    name: str,
    neo4j: Neo4jClient = Depends(get_neo4j),
):
    return await neo4j.get_entity_connections(entity_name=name)
