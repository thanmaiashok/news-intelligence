# News Intelligence System

> Production-grade distributed news crawler, real-time processing pipeline, and AI-powered analytics dashboard.

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-14-black?logo=next.js)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi)
![Kafka](https://img.shields.io/badge/Apache_Kafka-7.6-231F20?logo=apache-kafka)
![License](https://img.shields.io/badge/License-MIT-green)
![Open Source](https://img.shields.io/badge/Open%20Source-%E2%9D%A4-red)

---

## What Is This?

A self-hosted news intelligence platform that crawls dozens of sources, processes articles through an NLP pipeline, and surfaces insights via an interactive dashboard — all running on your own hardware.

**Sources:** RSS feeds, Reddit, Bluesky, Mastodon, Hacker News, GDELT, web pages (static + JS)  
**AI:** Deduplication, multi-label classification, sentiment (RoBERTa), NER (spaCy), RAG queries, LLM insights  
**Storage:** PostgreSQL · ClickHouse · Neo4j · Redis · FAISS · S3/MinIO  
**Dashboard:** 7 live pages — Overview, Feed, Trends, Sentiment, Graph, Leads, Control

---

## One-Step Setup

```bash
git clone https://github.com/thanmaiashok/news-intelligence.git
cd news-intelligence
./start.sh
```

That's it. `start.sh` handles everything:
- Copies `.env.example` → `.env` if missing
- Starts all infrastructure (Kafka, Postgres, ClickHouse, Neo4j, Redis, MinIO) via Docker
- Creates Python venv, installs deps, downloads spaCy model + Playwright
- Pre-warms the embedding model
- Starts FastAPI backend + Next.js frontend

**Prerequisites:** Docker Desktop · Python 3.11+ · Node.js 20+

Open your browser:

| Service | URL |
|---------|-----|
| Dashboard | http://localhost:3000 |
| API | http://localhost:8001 |
| API Docs | http://localhost:8001/docs |
| Kafka UI | http://localhost:8080 |
| Neo4j Browser | http://localhost:7474 |
| MinIO Console | http://localhost:9001 |

Stop everything: `./kill.sh`

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       NEWS INTELLIGENCE SYSTEM                               │
├──────────────┬──────────────────┬─────────────────┬────────────────────────┤
│  SOURCES     │  CRAWLER LAYER   │   KAFKA TOPICS  │  PROCESSING PIPELINE   │
│              │                  │                 │                        │
│  RSS Feeds   │  RSSCrawlerPool  │  news.raw  ──►  │  Deduplication         │
│  Web Pages   │  StaticWeb       │                 │  (SimHash + MinHash)   │
│  JS Sites    │  Playwright      │                 │  Multi-label Classify  │
│  Reddit      │  RedditCrawler   │  news.processed │  Sentiment (RoBERTa)   │
│  Bluesky     │  BlueskyCrawler  │                 │  NER (spaCy)           │
│  Mastodon    │  MastodonCrawler │  news.trends    │  Trend Detection       │
│  HN / GDELT  │  Scheduler       │                 │                        │
│              │  (every 2min)    │                 │                        │
├──────────────┴──────────────────┴─────────────────┴────────────────────────┤
│                              STORAGE LAYER                                   │
│                                                                              │
│  S3/MinIO         PostgreSQL          ClickHouse         Neo4j              │
│  (raw JSON)       (articles,          (analytics,        (knowledge graph:  │
│                    structured)         time-series)       Article→Topic     │
│                                                           Article→Entity    │
│  FAISS/Pinecone   Redis                                   Entity→Entity)    │
│  (embeddings)     (dedup cache,                                             │
│                    trend windows)                                            │
├──────────────────────────────────────────────────────────────────────────────┤
│                               AI LAYER                                       │
│                                                                              │
│  EmbeddingService          RAGEngine              InsightsGenerator         │
│  (sentence-transformers)   (FAISS + GPT-4o-mini)  (LLM + rule-based)       │
│                            Mystery Engine         Anomaly Detector          │
├──────────────────────────────────────────────────────────────────────────────┤
│                             FASTAPI BACKEND                                  │
│                                                                              │
│  REST API (/api/v1/*)      WebSocket (/ws/feed)   Kafka→WS Bridge           │
├──────────────────────────────────────────────────────────────────────────────┤
│                           NEXT.JS DASHBOARD                                  │
│                                                                              │
│  Overview │ Live Feed │ Trends │ Sentiment │ Graph │ Leads │ Control        │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
news-intelligence/
├── backend/
│   ├── ai/            Embeddings, RAG engine, insights generator, mystery pipeline
│   ├── api/           FastAPI app, REST routes, WebSocket bridge
│   ├── config/        Pydantic settings (env-driven)
│   ├── crawler/       RSS, web (Playwright), Reddit, Bluesky, Mastodon, HN, GDELT
│   ├── mystery/       Anomaly detection, LLM reasoning, pattern engine
│   ├── pipeline/      Kafka producer/consumer, dedup, classify, sentiment, NER, trends
│   ├── storage/       PostgreSQL, ClickHouse, Neo4j, S3, vector store clients
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── app/       7 Next.js pages
│       ├── components/ Per-page UI components
│       ├── hooks/     useWebSocket, usePolling
│       ├── lib/       API client
│       └── types/     TypeScript interfaces
├── deployment/
│   ├── docker/        docker-compose.yml (full infrastructure stack)
│   ├── k8s/           Kubernetes manifests (Namespace, Deployments, HPA)
│   └── scripts/       DB init SQL + Neo4j Cypher
├── .env.example       All config vars with comments
├── start.sh           One-command local startup
└── kill.sh            Graceful shutdown
```

---

## Configuration

Copy `.env.example` → `.env` and fill in your values. All API keys are **optional** — the system works without them using free/local alternatives.

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `POSTGRES_PASSWORD` | No | `newspass` | PostgreSQL auth |
| `NEO4J_PASSWORD` | No | `newspass123` | Neo4j auth |
| `OPENAI_API_KEY` | No | — | RAG queries + AI insights |
| `REDDIT_CLIENT_ID` | No | — | Reddit crawling |
| `TWITTER_BEARER_TOKEN` | No | — | Twitter/X crawling |
| `PINECONE_API_KEY` | No | — | Cloud vectors (falls back to FAISS) |

---

## Optional API Keys

| Service | Where to get | What it unlocks |
|---------|-------------|-----------------|
| OpenAI | platform.openai.com | RAG query answering + AI insights |
| Reddit | reddit.com/prefs/apps | Reddit news crawling |
| Twitter Bearer | developer.twitter.com | Twitter/X feed crawling |
| Pinecone | pinecone.io | Cloud vector search (vs local FAISS) |

---

## Home Server / Tailscale

Run on a home server and access from any device on your Tailscale network:

```bash
./start.sh   # auto-detects Tailscale IP
```

Or force a specific host:

```bash
SERVER_HOST=my-server-hostname ./start.sh
```

Startup output prints the exact URLs to open from other devices.

---

## Full Docker Stack

```bash
cp .env.example .env
cd deployment/docker
docker compose up --build
```

---

## Kubernetes

```bash
# Build and push images
docker build -t your-registry/news-api:latest ./backend
docker build -t your-registry/news-frontend:latest ./frontend
docker push your-registry/news-api:latest
docker push your-registry/news-frontend:latest

# Deploy
kubectl create secret generic news-secrets --from-env-file=.env -n news-intelligence
kubectl apply -f deployment/k8s/
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend API | FastAPI + uvicorn (asyncio) |
| Frontend | Next.js 14 + Tailwind CSS |
| Message Queue | Apache Kafka |
| Databases | PostgreSQL · ClickHouse · Neo4j |
| Cache | Redis |
| Object Storage | MinIO (S3-compatible) |
| Vector Search | FAISS (local) or Pinecone (cloud) |
| NLP | spaCy · HuggingFace Transformers · sentence-transformers |
| Deduplication | SimHash + MinHash (datasketch) |
| Containerization | Docker Compose · Kubernetes |

---

## Contributing

Contributions welcome. Open an issue first for large changes.

1. Fork the repo
2. Create a branch: `git checkout -b feature/your-feature`
3. Commit your changes
4. Push and open a PR

---

## License

MIT — see [LICENSE](LICENSE)
