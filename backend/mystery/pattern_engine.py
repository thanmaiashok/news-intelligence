"""
Pattern Detection Engine

Three-layer linking:
1. Signal matching  — same entity / location across events
2. Semantic similarity — embedding cosine similarity
3. Neo4j graph linking — SAME_PATTERN, SAME_ENTITY, POSSIBLE_LINK

Only creates connections when confidence > threshold.
Explicitly returns "NO_STRONG_CONNECTION" when no pattern found.
"""

import logging
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

import numpy as np
from neo4j import AsyncDriver

from backend.config import settings
from backend.mystery.mystery_classifier import MysteryEvent
from backend.mystery.anomaly_detector import AnomalyDetector
from backend.ai.embeddings import EmbeddingService
from backend.storage.vector_store import VectorStore

logger = logging.getLogger(__name__)

# Confidence thresholds
ENTITY_LINK_THRESHOLD = 0.70        # min confidence for SAME_ENTITY edge
SEMANTIC_LINK_THRESHOLD = 0.82      # cosine similarity for POSSIBLE_LINK
PATTERN_LINK_THRESHOLD = 0.65       # for SAME_PATTERN
EMIT_CLUSTER_THRESHOLD = 0.55       # min to emit cluster to LLM


class PatternEngine:
    def __init__(
        self,
        neo4j_driver: AsyncDriver,
        embedder: EmbeddingService,
        vector_store: VectorStore,
        detector: AnomalyDetector,
    ):
        self._neo4j = neo4j_driver
        self._embedder = embedder
        self._vectors = vector_store
        self._detector = detector

    async def link_events(
        self, events: List[MysteryEvent]
    ) -> List[Dict]:
        """
        Full pattern linking pass over mystery event batch.
        Returns event clusters with confidence + relationship type.
        """
        if not events:
            return []

        entity_clusters = self._link_by_entity(events)
        semantic_clusters = await self._link_by_semantics(events)
        temporal_clusters = self._detector.detect_temporal_clusters(events)
        spatial_clusters = self._detector.detect_spatial_clusters(events)

        all_clusters = (
            entity_clusters
            + semantic_clusters
            + temporal_clusters
            + spatial_clusters
        )

        # Merge overlapping clusters
        merged = self._merge_clusters(all_clusters)

        # Filter below threshold
        strong = [c for c in merged if c.get("confidence", 0) >= EMIT_CLUSTER_THRESHOLD]

        # Write to Neo4j
        for cluster in strong:
            await self._write_graph(cluster, events)

        return strong if strong else [{"verdict": "NO_STRONG_CONNECTION", "confidence": 0.0}]

    # ─── Entity linking ────────────────────────────────────────────────────────

    def _link_by_entity(self, events: List[MysteryEvent]) -> List[Dict]:
        """
        Groups events sharing a named entity (person/org/location).
        Confidence = avg(anomaly_score) of group * overlap_ratio.
        """
        entity_map: Dict[str, List[MysteryEvent]] = defaultdict(list)
        for event in events:
            for ent in event.entities:
                name = ent.get("name", "").lower().strip()
                ent_type = ent.get("type", "")
                if name and ent_type in ("person", "organization", "country_city", "location"):
                    entity_map[f"{ent_type}:{name}"].append(event)

        clusters = []
        for entity_key, group in entity_map.items():
            if len(group) < 2:
                continue
            avg_anomaly = sum(e.anomaly_score for e in group) / len(group)
            avg_cred = sum(e.credibility_score for e in group) / len(group)
            confidence = min(avg_anomaly * avg_cred * 1.4, 1.0)

            if confidence < ENTITY_LINK_THRESHOLD:
                continue

            clusters.append({
                "cluster_type": "entity_match",
                "relationship": "SAME_ENTITY",
                "entity": entity_key,
                "events": [e.article_hash for e in group],
                "event_titles": [e.title[:100] for e in group],
                "size": len(group),
                "confidence": round(confidence, 3),
                "avg_anomaly": round(avg_anomaly, 3),
                "avg_credibility": round(avg_cred, 3),
            })

        return clusters

    # ─── Semantic linking ──────────────────────────────────────────────────────

    async def _link_by_semantics(
        self, events: List[MysteryEvent]
    ) -> List[Dict]:
        """
        Embeds event titles + snippets, computes pairwise cosine similarity.
        Pairs above threshold → POSSIBLE_LINK cluster.
        """
        if len(events) < 2:
            return []

        texts = [f"{e.title}. {e.content_snippet[:256]}" for e in events]
        embeddings = self._embedder.encode_batch(texts)

        clusters = []
        used_pairs = set()

        for i in range(len(events)):
            for j in range(i + 1, len(events)):
                pair_key = tuple(sorted([events[i].article_hash, events[j].article_hash]))
                if pair_key in used_pairs:
                    continue

                # Cosine similarity (vectors already normalized by encode_batch)
                sim = float(np.dot(embeddings[i], embeddings[j]))

                if sim < SEMANTIC_LINK_THRESHOLD:
                    continue

                used_pairs.add(pair_key)
                avg_anomaly = (events[i].anomaly_score + events[j].anomaly_score) / 2
                avg_cred = (events[i].credibility_score + events[j].credibility_score) / 2
                confidence = min(sim * avg_anomaly * avg_cred * 1.5, 1.0)

                if confidence < EMIT_CLUSTER_THRESHOLD:
                    continue

                clusters.append({
                    "cluster_type": "semantic",
                    "relationship": "POSSIBLE_LINK",
                    "similarity": round(sim, 4),
                    "events": [events[i].article_hash, events[j].article_hash],
                    "event_titles": [events[i].title[:100], events[j].title[:100]],
                    "size": 2,
                    "confidence": round(confidence, 3),
                    "avg_anomaly": round(avg_anomaly, 3),
                    "avg_credibility": round(avg_cred, 3),
                })

        return clusters

    # ─── Cluster merge ─────────────────────────────────────────────────────────

    def _merge_clusters(self, clusters: List[Dict]) -> List[Dict]:
        """
        Merges clusters sharing ≥50% event overlap.
        Takes union of events, max confidence.
        """
        if not clusters:
            return []

        merged = []
        used = set()

        for i, c1 in enumerate(clusters):
            if i in used:
                continue
            base = dict(c1)
            base_events = set(c1.get("events", []))

            for j, c2 in enumerate(clusters):
                if j <= i or j in used:
                    continue
                c2_events = set(c2.get("events", []))
                overlap = len(base_events & c2_events)
                if overlap / max(len(base_events), 1) >= 0.5:
                    base_events |= c2_events
                    base["confidence"] = max(
                        base.get("confidence", 0), c2.get("confidence", 0)
                    )
                    base["cluster_type"] = f"{base['cluster_type']}+{c2['cluster_type']}"
                    if "SAME_ENTITY" in (c2.get("relationship", "") or ""):
                        base["relationship"] = "SAME_ENTITY"
                    elif base.get("relationship") != "SAME_ENTITY":
                        base["relationship"] = "SAME_PATTERN"
                    used.add(j)

            base["events"] = list(base_events)
            base["size"] = len(base_events)
            merged.append(base)
            used.add(i)

        return merged

    # ─── Neo4j write ───────────────────────────────────────────────────────────

    async def _write_graph(self, cluster: Dict, events: List[MysteryEvent]):
        """
        Writes MysteryCluster node + SAME_PATTERN / SAME_ENTITY / POSSIBLE_LINK edges.
        Only writes if confidence > threshold.
        """
        if cluster.get("confidence", 0) < EMIT_CLUSTER_THRESHOLD:
            return

        relationship = cluster.get("relationship", "POSSIBLE_LINK")
        confidence = cluster.get("confidence", 0)
        event_hashes = cluster.get("events", [])

        # Build lookup
        event_map = {e.article_hash: e for e in events}

        async with self._neo4j.session() as session:
            # Merge MysteryCluster node
            cluster_id = cluster.get("entity") or cluster.get("cluster_type", "unknown")
            await session.run(
                """
                MERGE (mc:MysteryCluster {cluster_id: $cid})
                ON CREATE SET
                    mc.cluster_type = $ctype,
                    mc.relationship_type = $rel,
                    mc.confidence = $conf,
                    mc.created_at = datetime()
                ON MATCH SET
                    mc.confidence = CASE WHEN $conf > mc.confidence THEN $conf ELSE mc.confidence END,
                    mc.last_updated = datetime()
                """,
                cid=str(cluster_id)[:200],
                ctype=cluster.get("cluster_type", "unknown"),
                rel=relationship,
                conf=confidence,
            )

            # Link each mystery article to cluster
            for h in event_hashes[:10]:
                evt = event_map.get(h)
                if not evt:
                    continue

                await session.run(
                    """
                    MERGE (ma:MysteryArticle {content_hash: $hash})
                    ON CREATE SET
                        ma.title = $title,
                        ma.url = $url,
                        ma.subcategory = $subcat,
                        ma.anomaly_score = $anomaly,
                        ma.credibility_score = $cred,
                        ma.source_reliability = $src_rel,
                        ma.published_at = $pub,
                        ma.created_at = datetime()
                    WITH ma
                    MATCH (mc:MysteryCluster {cluster_id: $cid})
                    MERGE (ma)-[r:BELONGS_TO_CLUSTER]->(mc)
                    ON CREATE SET r.confidence = $conf
                    """,
                    hash=h,
                    title=evt.title[:500],
                    url=evt.url,
                    subcat=evt.subcategory,
                    anomaly=evt.anomaly_score,
                    cred=evt.credibility_score,
                    src_rel=evt.source_reliability,
                    pub=evt.published_at,
                    cid=str(cluster_id)[:200],
                    conf=confidence,
                )

            # Direct SAME_ENTITY / SAME_PATTERN edges between pairs
            for idx_a in range(len(event_hashes)):
                for idx_b in range(idx_a + 1, min(idx_a + 5, len(event_hashes))):
                    ha = event_hashes[idx_a]
                    hb = event_hashes[idx_b]
                    await session.run(
                        f"""
                        MATCH (a:MysteryArticle {{content_hash: $ha}})
                        MATCH (b:MysteryArticle {{content_hash: $hb}})
                        MERGE (a)-[r:{relationship}]->(b)
                        ON CREATE SET r.confidence = $conf, r.created_at = datetime()
                        ON MATCH SET r.confidence = CASE WHEN $conf > r.confidence THEN $conf ELSE r.confidence END
                        """,
                        ha=ha,
                        hb=hb,
                        conf=confidence,
                    )
