# Global News Intelligence System

Production-grade distributed news crawler, processing pipeline, and analytics dashboard.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       GLOBAL NEWS INTELLIGENCE SYSTEM                        │
├──────────────┬──────────────────┬─────────────────┬────────────────────────┤
│  SOURCES     │  CRAWLER LAYER   │   KAFKA TOPICS  │  PROCESSING PIPELINE   │
│              │                  │                 │                        │
│  RSS Feeds   │  RSSCrawlerPool  │  news.raw  ──►  │  Deduplication         │
│  Web Pages   │  StaticWeb       │                 │  (SimHash + MinHash)   │
│  JS Sites    │  Playwright      │                 │  Multi-label Classify  │
│  Reddit      │  RedditCrawler   │  news.processed │  Sentiment (RoBERTa)   │
│  (ext. API)  │  TwitterCrawler  │                 │  NER (spaCy)           │
│              │                  │  news.trends    │  Trend Detection       │
│              │  Scheduler       │                 │                        │
│              │  (every 5min)    │                 │                        │
├──────────────┴──────────────────┴─────────────────┴────────────────────────┤
│                              STORAGE LAYER                                   │
│                                                                              │
│  S3/MinIO         PostgreSQL          ClickHouse         Neo4j              │
│  (raw JSON)       (articles,          (analytics,        (graph:            │
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

## Folder Structure

```
news-intelligence/
├── backend/
│   ├── api/           FastAPI app + REST routes + WebSocket
│   ├── ai/            Embeddings, RAG, Insights generator
│   ├── config/        Pydantic settings
│   ├── crawler/       RSS, Web (Playwright), Reddit crawlers + Scheduler
│   ├── pipeline/      Kafka producer/consumer, Dedup, Classify, Sentiment, NER, Trends
│   └── storage/       PostgreSQL, ClickHouse, Neo4j, S3, VectorStore clients
├── frontend/
│   └── src/
│       ├── app/       7 Next.js pages (overview, feed, trends, sentiment, graph, leads, control)
│       ├── components/ UI components per page
│       ├── hooks/     useWebSocket, usePolling
│       ├── lib/       API client
│       └── types/     TypeScript interfaces
├── deployment/
│   ├── docker/        docker-compose.yml (all services)
│   └── k8s/           Namespace, Deployments, HPA configs
└── .env.example
```

---

## Quick Start (Local / VS Code)

### Prerequisites
- Docker Desktop
- Python 3.11+
- Node.js 20+

### Step 1 — Start infrastructure

```bash
cd deployment/docker
docker compose up -d zookeeper kafka postgres clickhouse neo4j redis minio
```

Wait ~30s for services to be ready. Check:
- Kafka UI: http://localhost:8080
- Neo4j Browser: http://localhost:7474 (neo4j / newspass123)
- MinIO Console: http://localhost:9001 (minioadmin / minioadmin)

### Step 2 — Backend setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -r requirements.txt

# Install spaCy model
python -m spacy download en_core_web_sm

# Install Playwright browsers
playwright install chromium
```

Copy `.env.example` → `.env` and fill in your API keys (all optional for basic run).

```bash
cp ../.env.example ../.env
```

### Step 3 — Run backend API

```bash
cd backend
uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8001
```

API docs: http://localhost:8001/docs

### Step 4 — Run crawler scheduler

In a separate terminal:
```bash
cd backend
python -m backend.crawler.scheduler
```

### Step 5 — Frontend

```bash
cd frontend
npm install
npm run dev
```

Dashboard: http://localhost:3000

---

## Docker (full stack)

```bash
cp .env.example .env
# Edit .env with your credentials

cd deployment/docker
docker compose up --build
```

- Dashboard: http://localhost:3000
- API: http://localhost:8001
- Kafka UI: http://localhost:8080
- Neo4j: http://localhost:7474

---

## Home Server / Tailscale

No public domain is required. Put the server and your devices on the same
Tailscale network, then start the project on the server:

```bash
./start.sh
```

`start.sh` binds the API and frontend to `0.0.0.0` and auto-detects the
server's Tailscale IPv4 address when `tailscale` is installed. The startup
summary prints the URLs to open from your other devices, usually:

```text
Dashboard: http://100.x.x.x:3000
API Docs:  http://100.x.x.x:8001/docs
```

To force a specific hostname or MagicDNS name:

```bash
SERVER_HOST=spoosh-Aspire-A715-42G ./start.sh
```

For Docker-only frontend builds, set browser-facing URLs before building:

```bash
export NEXT_PUBLIC_API_URL=http://100.x.x.x:8001/api/v1
export NEXT_PUBLIC_WS_URL=ws://100.x.x.x:8001/ws/feed
docker compose -f deployment/docker/docker-compose.yml up --build
```

---

## Kubernetes

```bash
# Build and push images
docker build -t your-registry/news-api:latest ./backend
docker build -t your-registry/news-frontend:latest ./frontend
docker push your-registry/news-api:latest
docker push your-registry/news-frontend:latest

# Create secret
kubectl create secret generic news-secrets \
  --from-env-file=.env \
  -n news-intelligence

# Deploy
kubectl apply -f deployment/k8s/namespace.yaml
kubectl apply -f deployment/k8s/crawler-deployment.yaml
kubectl apply -f deployment/k8s/api-deployment.yaml
kubectl apply -f deployment/k8s/hpa.yaml
```

---

## Optional API Keys

| Service | Where to get | What it unlocks |
|---------|-------------|-----------------|
| OpenAI | platform.openai.com | RAG query + AI insights |
| Reddit | reddit.com/prefs/apps | Reddit news crawling |
| Twitter Bearer | developer.twitter.com | Twitter/X crawling |
| Pinecone | pinecone.io | Cloud vector search (vs local FAISS) |

---

## VS Code Extensions (Recommended)

- Python (ms-python.python)
- Pylance
- ESLint
- Prettier
- Docker
- Thunder Client (API testing)
