"""
FastAPI dependency injection providers.
All clients are singletons attached to app.state during startup.
"""
from fastapi import Request

from backend.storage.postgres_client import PostgresClient
from backend.storage.clickhouse_client import ClickHouseClient
from backend.storage.neo4j_client import Neo4jClient
from backend.storage.vector_store import VectorStore
from backend.pipeline.trend_detector import TrendDetector
from backend.ai.embeddings import EmbeddingService
from backend.ai.rag_engine import RAGEngine
from backend.ai.insights_generator import InsightsGenerator
from backend.mystery.pipeline import MysteryPipeline


def get_postgres(request: Request) -> PostgresClient:
    return request.app.state.postgres


def get_clickhouse(request: Request) -> ClickHouseClient:
    return request.app.state.clickhouse


def get_neo4j(request: Request) -> Neo4jClient:
    return request.app.state.neo4j


def get_vectors(request: Request) -> VectorStore:
    return request.app.state.vectors


def get_trends(request: Request) -> TrendDetector:
    return request.app.state.trends


def get_rag(request: Request) -> RAGEngine:
    return request.app.state.rag


def get_insights(request: Request) -> InsightsGenerator:
    return request.app.state.insights


def get_mystery(request: Request) -> MysteryPipeline:
    return request.app.state.mystery
