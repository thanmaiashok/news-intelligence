from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    APP_NAME: str = "News Intelligence System"
    DEBUG: bool = False
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8001

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_RAW_TOPIC: str = "news.raw"
    KAFKA_PROCESSED_TOPIC: str = "news.processed"
    KAFKA_TRENDS_TOPIC: str = "news.trends"
    KAFKA_GROUP_ID: str = "news-processor"
    KAFKA_CONSUMER_THREADS: int = 4

    # PostgreSQL
    POSTGRES_URL: str = "postgresql+asyncpg://news:newspass@localhost:5432/newsdb"

    # ClickHouse
    CLICKHOUSE_HOST: str = "localhost"
    CLICKHOUSE_PORT: int = 8123
    CLICKHOUSE_USER: str = "default"
    CLICKHOUSE_PASSWORD: str = ""
    CLICKHOUSE_DB: str = "news_analytics"

    # Neo4j
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "newspass123"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # MinIO (local S3-compatible)
    S3_ENDPOINT_URL: str = "http://localhost:9010"
    S3_BUCKET: str = "news-raw"
    AWS_ACCESS_KEY_ID: str = "minioadmin"
    AWS_SECRET_ACCESS_KEY: str = "minioadmin"
    AWS_REGION: str = "us-east-1"

    # Crawler
    CRAWL_INTERVAL_SECONDS: int = 120
    MAX_CONCURRENT_CRAWLERS: int = 25
    CRAWL_TIMEOUT_SECONDS: int = 30
    PROXY_LIST: List[str] = []
    USER_AGENTS: List[str] = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:124.0) Gecko/20100101 Firefox/124.0",
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
    ]

    # Ollama (local LLM — using llama3.1:8b-instruct-q4_K_M, already pulled)
    OLLAMA_BASE_URL: str = "http://localhost:11434/v1"
    OLLAMA_MODEL: str = "llama3.1:8b-instruct-q4_K_M"

    # Embeddings (local sentence-transformers, no API needed)
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIM: int = 384

    # Dedup thresholds
    SIMHASH_THRESHOLD: int = 5
    MINHASH_THRESHOLD: float = 0.85

    model_config = {"case_sensitive": True}


settings = Settings()
