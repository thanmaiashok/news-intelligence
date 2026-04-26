import logging
from typing import Dict, List, Optional

from openai import AsyncOpenAI

from backend.config import settings
from backend.ai.embeddings import EmbeddingService
from backend.storage.vector_store import VectorStore

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a global news intelligence analyst with access to a continuously updated database of news articles from thousands of sources worldwide.

You analyze news data to provide:
- Trend insights and pattern recognition
- Sentiment analysis across topics and entities
- Cross-category correlations
- Market and geopolitical risk assessments
- Emerging opportunity identification

Always cite specific sources and events when available. Be precise, analytical, and data-driven."""


class RAGEngine:
    def __init__(self, vector_store: VectorStore, embedder: EmbeddingService):
        self._vector_store = vector_store
        self._embedder = embedder
        self._client = AsyncOpenAI(
            base_url=settings.OLLAMA_BASE_URL,
            api_key="ollama",
        )

    async def query(
        self,
        question: str,
        top_k: int = 10,
        filters: Optional[Dict] = None,
    ) -> Dict:
        query_vec = self._embedder.encode(question)
        results = await self._vector_store.search(query_vec.tolist(), top_k=top_k)

        if not results:
            return {
                "answer": "No relevant articles found for this query.",
                "sources": [],
                "context_count": 0,
            }

        context_parts = []
        sources = []
        for i, r in enumerate(results, 1):
            title = r.get("title", "Unknown")
            url = r.get("url", "")
            cats = ", ".join(r.get("categories", []))
            sentiment = r.get("sentiment", "neutral")
            context_parts.append(
                f"[{i}] Title: {title}\n    Categories: {cats}\n    Sentiment: {sentiment}\n    URL: {url}"
            )
            sources.append({"title": title, "url": url, "score": r.get("score", 0)})

        context = "\n\n".join(context_parts)
        prompt = f"""Based on the following news articles from our database, answer this question:

Question: {question}

Relevant Articles:
{context}

Provide a comprehensive, analytical answer citing the article numbers [1], [2], etc. where relevant."""

        try:
            response = await self._client.chat.completions.create(
                model=settings.OLLAMA_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=1500,
            )
            return {
                "answer": response.choices[0].message.content,
                "sources": sources,
                "context_count": len(results),
                "model": settings.OLLAMA_MODEL,
            }
        except Exception as e:
            logger.warning("RAG LLM error: %s", e)
            return {
                "answer": f"LLM unavailable. Found {len(results)} relevant articles: {', '.join(r.get('title', '') for r in results[:3])}...",
                "sources": sources,
                "context_count": len(results),
            }
