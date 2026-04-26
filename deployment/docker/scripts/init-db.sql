CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS articles (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content_hash    VARCHAR(64) UNIQUE NOT NULL,
    url             TEXT NOT NULL,
    title           TEXT NOT NULL,
    content         TEXT,
    source          VARCHAR(255),
    source_type     VARCHAR(50),
    author          VARCHAR(255),
    language        VARCHAR(10) DEFAULT 'en',
    region          VARCHAR(10),
    published_at    TIMESTAMPTZ,
    crawled_at      TIMESTAMPTZ DEFAULT NOW(),
    processed_at    TIMESTAMPTZ,
    categories      TEXT[],
    category_scores JSONB DEFAULT '{}',
    sentiment_label VARCHAR(20),
    sentiment_score FLOAT,
    sentiment_data  JSONB DEFAULT '{}',
    entities        JSONB DEFAULT '[]',
    metadata        JSONB DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_articles_published   ON articles(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_articles_source      ON articles(source);
CREATE INDEX IF NOT EXISTS idx_articles_categories  ON articles USING GIN(categories);
CREATE INDEX IF NOT EXISTS idx_articles_sentiment   ON articles(sentiment_label);
CREATE INDEX IF NOT EXISTS idx_articles_region      ON articles(region);
CREATE INDEX IF NOT EXISTS idx_articles_crawled     ON articles(crawled_at DESC);

CREATE TABLE IF NOT EXISTS crawler_sources (
    id           SERIAL PRIMARY KEY,
    name         VARCHAR(255) UNIQUE NOT NULL,
    url          TEXT NOT NULL,
    source_type  VARCHAR(50),
    priority     INTEGER DEFAULT 5,
    region       VARCHAR(10),
    enabled      BOOLEAN DEFAULT TRUE,
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    last_crawled TIMESTAMPTZ,
    article_count BIGINT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS crawler_runs (
    id               SERIAL PRIMARY KEY,
    started_at       TIMESTAMPTZ DEFAULT NOW(),
    ended_at         TIMESTAMPTZ,
    articles_crawled INTEGER DEFAULT 0,
    errors           INTEGER DEFAULT 0,
    status           VARCHAR(20) DEFAULT 'running'
);
