"""
LLM Reasoning Layer

Takes event clusters + context from pipeline.
Calls OpenAI once per cluster with strict anti-hallucination instructions.
Returns structured JSON verdict.

If OpenAI unavailable → returns rule-based verdict with explicit "LLM_UNAVAILABLE" flag.
"""

import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional

from openai import AsyncOpenAI

from backend.config import settings
from backend.mystery.mystery_classifier import MysteryEvent

_VERDICT_CACHE: Dict[str, tuple] = {}  # cluster_id → (verdict, timestamp)
_CACHE_TTL = 3600  # 1 hour

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a strict anomaly analysis system integrated into a global news intelligence platform.

Your role: analyze clusters of potentially related unusual news events and determine whether they represent:
1. Pure coincidence
2. Emerging pattern (statistically notable but not yet confirmed)
3. Confirmed anomaly (multiple independent verified sources, clear pattern)

CRITICAL RULES — failure to follow these disqualifies your response:
- NEVER invent facts, sources, or connections not present in the input data
- NEVER speculate beyond what the evidence supports
- If evidence is insufficient → set classification to "coincidence" and state "INSUFFICIENT EVIDENCE" in reasoning
- Treat low-credibility sources (< 0.4 credibility_score) with extreme skepticism
- Distinguish correlation from causation explicitly
- Your confidence score must reflect actual evidence strength, not narrative appeal
- Output ONLY valid JSON — no markdown, no explanation outside the JSON structure

OUTPUT FORMAT (strict):
{
  "event_cluster_id": "<string>",
  "summary": "<1-2 sentence factual summary of what the events describe>",
  "connected_events": ["<title1>", "<title2>"],
  "pattern_detected": <true|false>,
  "confidence": <float 0.0–1.0>,
  "reasoning": "<explicit step-by-step reasoning citing specific evidence from input>",
  "classification": "<coincidence|emerging_pattern|anomaly>",
  "verdict": "<no strong connection|weak signal|strong signal>",
  "data_gaps": "<what additional evidence would change this assessment>",
  "credibility_note": "<explicit note on source credibility limitations>"
}"""

ANALYSIS_PROMPT_TEMPLATE = """Analyze this cluster of unusual news events:

CLUSTER ID: {cluster_id}
CLUSTER TYPE: {cluster_type}
DETECTED RELATIONSHIP: {relationship}
CLUSTER CONFIDENCE SCORE: {confidence}

EVENTS IN CLUSTER ({n_events} events):
{events_block}

ENTITY OVERLAPS:
{entity_block}

ANOMALY STATISTICS:
- Average anomaly score: {avg_anomaly}
- Average credibility score: {avg_credibility}
- Subcategory: {subcategory}
- Regions involved: {regions}

TEMPORAL DATA:
{temporal_block}

GRAPH RELATIONSHIPS FOUND:
{graph_block}

Analyze whether these events represent coincidence, an emerging pattern, or a confirmed anomaly.
Apply maximum skepticism. Only upgrade from coincidence if evidence is substantial and multi-source.
If any source has credibility_score < 0.4, explicitly flag this in your credibility_note."""


def _build_events_block(events: List[MysteryEvent]) -> str:
    lines = []
    for i, e in enumerate(events, 1):
        lines.append(
            f"[{i}] Title: {e.title}\n"
            f"    Source: {e.source} (reliability: {e.source_reliability})\n"
            f"    Credibility: {e.credibility_score} | Anomaly: {e.anomaly_score}\n"
            f"    Subcategory: {e.subcategory_label}\n"
            f"    Matched signals: {', '.join(e.matched_signals[:5])}\n"
            f"    Snippet: {e.content_snippet[:200]}\n"
        )
    return "\n".join(lines)


def _build_entity_block(events: List[MysteryEvent]) -> str:
    from collections import Counter
    all_entities = []
    for e in events:
        for ent in e.entities:
            all_entities.append(f"{ent.get('type', '?')}:{ent.get('name', '?')}")
    counter = Counter(all_entities)
    shared = [(k, v) for k, v in counter.items() if v > 1]
    if not shared:
        return "No shared entities detected across events."
    return "\n".join(f"  - {name} (appears in {cnt} events)" for name, cnt in shared[:10])


def _rule_based_verdict(
    cluster: Dict, events: List[MysteryEvent]
) -> Dict:
    """
    Fallback when OpenAI unavailable.
    Pure rule-based, conservative, clearly marked.
    """
    avg_anomaly = sum(e.anomaly_score for e in events) / max(len(events), 1)
    avg_cred = sum(e.credibility_score for e in events) / max(len(events), 1)
    confidence = cluster.get("confidence", 0)

    if avg_cred < 0.35:
        classification = "coincidence"
        verdict = "no strong connection"
        pattern = False
        reasoning = "Average source credibility below 0.35. Insufficient reliable evidence to establish pattern."
    elif confidence >= 0.75 and avg_anomaly >= 0.65 and len(events) >= 4:
        classification = "emerging_pattern"
        verdict = "weak signal"
        pattern = True
        reasoning = f"Multiple events ({len(events)}) with elevated anomaly score ({avg_anomaly:.2f}) and acceptable credibility ({avg_cred:.2f}). Pattern threshold met but confirmation requires additional independent sources."
    elif confidence >= 0.85 and avg_anomaly >= 0.75 and len(events) >= 6:
        classification = "anomaly"
        verdict = "strong signal"
        pattern = True
        reasoning = f"Strong cluster: {len(events)} events, anomaly={avg_anomaly:.2f}, credibility={avg_cred:.2f}. Consistent signal across multiple sources."
    else:
        classification = "coincidence"
        verdict = "no strong connection"
        pattern = False
        reasoning = "INSUFFICIENT EVIDENCE. Cluster confidence or event count below anomaly threshold. No connection established."

    return {
        "event_cluster_id": cluster.get("cluster_id", "unknown"),
        "summary": f"Rule-based analysis of {len(events)} events in subcategory {events[0].subcategory if events else 'unknown'}.",
        "connected_events": [e.title[:80] for e in events[:5]],
        "pattern_detected": pattern,
        "confidence": round(confidence, 3),
        "reasoning": reasoning,
        "classification": classification,
        "verdict": verdict,
        "data_gaps": "LLM analysis unavailable. Manual review recommended for high-anomaly clusters.",
        "credibility_note": f"Average source reliability: {avg_cred:.2f}. {'Low credibility — treat with skepticism.' if avg_cred < 0.5 else 'Acceptable credibility.'}",
        "llm_used": False,
        "analyzed_at": datetime.utcnow().isoformat(),
    }


class LLMReasoner:
    def __init__(self):
        self._client = AsyncOpenAI(
            base_url=settings.OLLAMA_BASE_URL,
            api_key="ollama",
        )

    async def analyze_cluster(
        self,
        cluster: Dict,
        events: List[MysteryEvent],
    ) -> Dict:
        """
        Analyzes one event cluster.
        Returns structured verdict dict.
        Always returns something — falls back to rule-based if LLM unavailable.
        """
        cluster_id = str(cluster.get("cluster_id") or cluster.get("entity") or id(cluster))
        cached, ts = _VERDICT_CACHE.get(cluster_id, (None, 0))
        if cached and (time.time() - ts) < _CACHE_TTL:
            return cached

        if not events:
            return {
                "event_cluster_id": cluster.get("cluster_id", "unknown"),
                "verdict": "no strong connection",
                "classification": "coincidence",
                "confidence": 0.0,
                "reasoning": "INSUFFICIENT EVIDENCE: no events in cluster.",
                "pattern_detected": False,
                "llm_used": False,
                "analyzed_at": datetime.utcnow().isoformat(),
            }

        avg_anomaly = sum(e.anomaly_score for e in events) / len(events)
        avg_cred = sum(e.credibility_score for e in events) / len(events)
        regions = list({e.region for e in events if e.region})

        events_block = _build_events_block(events[:10])
        entity_block = _build_entity_block(events)
        temporal_block = f"Events span: {cluster.get('temporal_span_hours', 'unknown')} hours"
        graph_block = f"Relationship type detected: {cluster.get('relationship', 'unknown')} (confidence: {cluster.get('confidence', 0)})"

        prompt = ANALYSIS_PROMPT_TEMPLATE.format(
            cluster_id=cluster.get("cluster_id") or cluster.get("entity") or "cluster_" + str(id(cluster))[:8],
            cluster_type=cluster.get("cluster_type", "unknown"),
            relationship=cluster.get("relationship", "unknown"),
            confidence=cluster.get("confidence", 0),
            n_events=len(events),
            events_block=events_block,
            entity_block=entity_block,
            avg_anomaly=round(avg_anomaly, 3),
            avg_credibility=round(avg_cred, 3),
            subcategory=events[0].subcategory_label if events else "unknown",
            regions=", ".join(regions) if regions else "unknown",
            temporal_block=temporal_block,
            graph_block=graph_block,
        )

        try:
            response = await self._client.chat.completions.create(
                model=settings.OLLAMA_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=800,
            )

            raw = response.choices[0].message.content.strip()
            # strip markdown code fences if model adds them
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            verdict = json.loads(raw)
            verdict["llm_used"] = True
            verdict["analyzed_at"] = datetime.utcnow().isoformat()

            # Enforce confidence cap based on avg credibility
            if avg_cred < 0.35 and verdict.get("confidence", 0) > 0.4:
                verdict["confidence"] = 0.4
                verdict["credibility_note"] = (
                    verdict.get("credibility_note", "")
                    + " [CAPPED: low source credibility limits max confidence to 0.4]"
                )

            _VERDICT_CACHE[cluster_id] = (verdict, time.time())
            return verdict

        except Exception as e:
            logger.warning("LLM reasoning error: %s — falling back to rule-based", e)
            result = _rule_based_verdict(cluster, events)
            result["llm_error"] = str(e)
            _VERDICT_CACHE[cluster_id] = (result, time.time())
            return result

    async def analyze_batch(
        self,
        clusters: List[Dict],
        event_map: Dict[str, MysteryEvent],
    ) -> List[Dict]:
        """Processes multiple clusters. Skips NO_STRONG_CONNECTION entries."""
        results = []
        for cluster in clusters:
            if cluster.get("verdict") == "NO_STRONG_CONNECTION":
                results.append({
                    "verdict": "no strong connection",
                    "classification": "coincidence",
                    "pattern_detected": False,
                    "confidence": 0.0,
                    "reasoning": "NO_STRONG_CONNECTION: pattern engine found no links above threshold.",
                    "llm_used": False,
                    "analyzed_at": datetime.utcnow().isoformat(),
                })
                continue

            event_hashes = cluster.get("events", [])
            events = [event_map[h] for h in event_hashes if h in event_map]
            result = await self.analyze_cluster(cluster, events)
            results.append(result)

        return results
