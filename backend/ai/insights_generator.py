import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

from openai import AsyncOpenAI

from backend.config import settings

logger = logging.getLogger(__name__)


class InsightsGenerator:
    """Auto-generates market opportunities, emerging risks, and viral topic insights."""

    def __init__(self):
        self._client = AsyncOpenAI(
            base_url=settings.OLLAMA_BASE_URL,
            api_key="ollama",
        )

    async def generate_insights(
        self,
        trends: List[Dict],
        sentiment_data: List[Dict],
        top_entities: List[Dict],
        category_dist: List[Dict],
    ) -> Dict:
        prompt = self._build_prompt(trends, sentiment_data, top_entities, category_dist)

        try:
            response = await self._client.chat.completions.create(
                model=settings.OLLAMA_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a strategic intelligence analyst. "
                            "Generate actionable insights from news data. "
                            "Be specific, concise, and data-driven. "
                            "Output ONLY valid JSON with keys: market_opportunities, emerging_risks, viral_topics. "
                            "No markdown, no explanation outside the JSON."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.4,
                max_tokens=1000,
            )
            raw = response.choices[0].message.content.strip()
            # strip markdown code fences if model adds them
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            result = json.loads(raw)
            result["generated_at"] = datetime.utcnow().isoformat()
            return result
        except Exception as e:
            logger.warning("Insights generation error: %s", e)
            return self._rule_based_insights(trends, sentiment_data, top_entities)

    def _build_prompt(
        self,
        trends: List[Dict],
        sentiment_data: List[Dict],
        top_entities: List[Dict],
        category_dist: List[Dict],
    ) -> str:
        trend_str = "\n".join(
            f"- {t.get('name', '')} (velocity: {t.get('velocity', 1):.1f}x, spike: {t.get('is_spike', False)})"
            for t in trends[:10]
        )
        sentiment_str = "\n".join(
            f"- {s.get('label', '')}: {s.get('count', 0)} articles ({s.get('avg_score', 0):.2f} avg score)"
            for s in sentiment_data
        )
        entity_str = "\n".join(
            f"- {e.get('name', '')} ({e.get('type', '')})"
            for e in top_entities[:10]
        )
        cat_str = "\n".join(
            f"- {c.get('category', '')}: {c.get('count', 0)} articles"
            for c in category_dist[:10]
        )

        return f"""Analyze this real-time news intelligence data and generate strategic insights:

TRENDING TOPICS (velocity = current/previous period ratio):
{trend_str}

SENTIMENT DISTRIBUTION:
{sentiment_str}

TOP MENTIONED ENTITIES:
{entity_str}

CATEGORY DISTRIBUTION:
{cat_str}

Generate JSON with:
- market_opportunities: List of 3-5 specific market opportunities based on trends
- emerging_risks: List of 3-5 emerging risks/threats identified
- viral_topics: List of 3-5 viral/trending topics with brief analysis
Each item should have: title, description, confidence (high/medium/low), category"""

    def _rule_based_insights(
        self,
        trends: List[Dict],
        sentiment_data: List[Dict],
        top_entities: List[Dict],
    ) -> Dict:
        spikes = [t for t in trends if t.get("is_spike")]

        opportunities = []
        risks = []
        viral = []

        for spike in spikes[:3]:
            name = spike.get("name", "")
            kind = spike.get("kind", "")
            if kind == "cat" and name in ("technology", "finance", "energy"):
                opportunities.append({
                    "title": f"Surge in {name.title()} News Coverage",
                    "description": f"{name.title()} sector showing {spike.get('velocity', 1):.1f}x velocity spike",
                    "confidence": "high" if spike.get("velocity", 1) > 3 else "medium",
                    "category": name,
                })
            if kind == "cat" and name in ("war_conflict", "crime_law", "climate_environment"):
                risks.append({
                    "title": f"Elevated {name.replace('_', ' ').title()} Activity",
                    "description": f"News volume {spike.get('velocity', 1):.1f}x above baseline",
                    "confidence": "high",
                    "category": name,
                })

        for spike in spikes[:5]:
            viral.append({
                "title": spike.get("name", "").replace(":", " → "),
                "description": f"Velocity: {spike.get('velocity', 1):.1f}x | Count: {spike.get('current_count', 0)}",
                "confidence": "high" if spike.get("is_spike") else "medium",
                "category": spike.get("kind", "unknown"),
            })

        return {
            "market_opportunities": opportunities,
            "emerging_risks": risks,
            "viral_topics": viral,
            "generated_at": datetime.utcnow().isoformat(),
        }
