<p align="center"><img src="docs/flow.svg" alt="Animated News Intelligence pipeline: Crawl → Queue → Dedupe → Analyze → Store → Dashboard" width="100%"/></p>

<p align="center"><sub>10-second tour: Crawl → Queue → Dedupe → Analyze → Store → Dashboard</sub></p>

<p align="center"><img src="docs/mc/intro.svg" width="100%" alt="Production-grade distributed news crawler, real-time processing pipeline and AI-powered analytics dashboard, self-hosted on your own hardware."/></p>

<p align="center"><img src="docs/mc/features.svg" width="100%" alt="Key features"/></p>

<a id="what-is-this"></a>
<h2><img src="docs/mc/h2-what-is-this.svg" width="100%" alt="What Is This?"/></h2>

<p align="center"><img src="docs/mc/t-01.svg" width="100%" alt="A self-hosted news intelligence platform that crawls dozens of sources, processes articles through an NLP pipeline, and surfaces insights via an interactive dashboard - all running on your own hardware. Sources: RSS feeds, Reddit, Bluesky, Mastodon, Hacker News, GDELT, web pages (static + JS)AI: Deduplication, multi-label classification, sentiment (RoBERTa), NER (spaCy), RAG queries, LLM insightsStorage: PostgreSQL | ClickHouse | Neo4j | Redis | FAISS | S3/MinIODashboard: 7 live pages - Overview, Feed, Trends, Sentiment, Graph, Leads, Control"/></p>

<a id="one-step-setup"></a>
<h2><img src="docs/mc/h2-one-step-setup.svg" width="100%" alt="One-Step Setup"/></h2>

```bash
git clone https://github.com/thanmaiashok/news-intelligence.git
cd news-intelligence
./start.sh
```

<p align="center"><img src="docs/mc/t-02.svg" width="100%" alt="That&#x27;s it. start.sh handles everything: Copies .env.example -&gt; .env if missing Starts all infrastructure (Kafka, Postgres, ClickHouse, Neo4j, Redis, MinIO) via Docker Creates Python venv, installs deps, downloads spaCy model + Playwright Pre-warms the embedding model Starts FastAPI backend + Next.js frontend Prerequisites: Docker Desktop | Python 3.11+ | Node.js 20+ Open your browser: Service | URL Dashboard | http://localhost:3000 API | http://localhost:8001 API Docs | http://localhost:8001/docs Kafka UI | http://localhost:8080 Neo4j Browser | http://localhost:7474 MinIO Console | http://localhost:9001 Stop everything: ./kill.sh"/></p>

<a id="architecture"></a>
<h2><img src="docs/mc/h2-architecture.svg" width="100%" alt="Architecture"/></h2>

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

<a id="project-structure"></a>
<h2><img src="docs/mc/h2-project-structure.svg" width="100%" alt="Project Structure"/></h2>

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

<a id="configuration"></a>
<h2><img src="docs/mc/h2-configuration.svg" width="100%" alt="Configuration"/></h2>

<p align="center"><img src="docs/mc/t-03.svg" width="100%" alt="Copy .env.example -&gt; .env and fill in your values. All API keys are optional - the system works without them using free/local alternatives. Variable | Required | Default | Purpose POSTGRES_PASSWORD | No | newspass | PostgreSQL auth NEO4J_PASSWORD | No | newspass123 | Neo4j auth OPENAI_API_KEY | No | - | RAG queries + AI insights REDDIT_CLIENT_ID | No | - | Reddit crawling TWITTER_BEARER_TOKEN | No | - | Twitter/X crawling PINECONE_API_KEY | No | - | Cloud vectors (falls back to FAISS)"/></p>

<a id="optional-api-keys"></a>
<h2><img src="docs/mc/h2-optional-api-keys.svg" width="100%" alt="Optional API Keys"/></h2>

<p align="center"><img src="docs/mc/t-04.svg" width="100%" alt="Service | Where to get | What it unlocks OpenAI | platform.openai.com | RAG query answering + AI insights Reddit | reddit.com/prefs/apps | Reddit news crawling Twitter Bearer | developer.twitter.com | Twitter/X feed crawling Pinecone | pinecone.io | Cloud vector search (vs local FAISS)"/></p>

<a id="home-server--tailscale"></a>
<h2><img src="docs/mc/h2-home-server-tailscale.svg" width="100%" alt="Home Server / Tailscale"/></h2>

<p align="center"><img src="docs/mc/t-05.svg" width="100%" alt="Run on a home server and access from any device on your Tailscale network:"/></p>

```bash
./start.sh   # auto-detects Tailscale IP
```

<p align="center"><img src="docs/mc/t-06.svg" width="100%" alt="Or force a specific host:"/></p>

```bash
SERVER_HOST=my-server-hostname ./start.sh
```

<p align="center"><img src="docs/mc/t-07.svg" width="100%" alt="Startup output prints the exact URLs to open from other devices."/></p>

<a id="full-docker-stack"></a>
<h2><img src="docs/mc/h2-full-docker-stack.svg" width="100%" alt="Full Docker Stack"/></h2>

```bash
cp .env.example .env
cd deployment/docker
docker compose up --build
```

<a id="kubernetes"></a>
<h2><img src="docs/mc/h2-kubernetes.svg" width="100%" alt="Kubernetes"/></h2>

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

<a id="tech-stack"></a>
<h2><img src="docs/mc/h2-tech-stack.svg" width="100%" alt="Tech Stack"/></h2>

<p align="center"><img src="docs/mc/t-08.svg" width="100%" alt="Layer | Technology Backend API | FastAPI + uvicorn (asyncio) Frontend | Next.js 14 + Tailwind CSS Message Queue | Apache Kafka Databases | PostgreSQL | ClickHouse | Neo4j Cache | Redis Object Storage | MinIO (S3-compatible) Vector Search | FAISS (local) or Pinecone (cloud) NLP | spaCy | HuggingFace Transformers | sentence-transformers Deduplication | SimHash + MinHash (datasketch) Containerization | Docker Compose | Kubernetes"/></p>

<a id="contributing"></a>
<h2><img src="docs/mc/h2-contributing.svg" width="100%" alt="Contributing"/></h2>

<p align="center"><img src="docs/mc/t-09.svg" width="100%" alt="Contributions welcome. Open an issue first for large changes. Fork the repo Create a branch: git checkout -b feature/your-feature Commit your changes Push and open a PR"/></p>

<a id="license"></a>
<h2><img src="docs/mc/h2-license.svg" width="100%" alt="License"/></h2>

<p align="center"><img src="docs/mc/t-10.svg" width="100%" alt="MIT - see LICENSE"/></p>

<p align="center"><a href="LICENSE"><img src="docs/mc/link-01.svg" height="34" alt="LICENSE"/></a></p>

<p align="center"><a href="https://github.com/thanmaiashok"><img src="docs/mc/footer.svg" width="100%" alt="Built by Thanmai A, founder of FoxynAI"/></a></p>
