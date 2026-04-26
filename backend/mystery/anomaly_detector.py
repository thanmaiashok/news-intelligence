"""
Anomaly Detection Engine

Detects statistical anomalies in event frequency, spatial clustering,
and temporal correlation. Operates on mystery-classified events.
No ML required — deterministic scoring with configurable thresholds.
"""

import asyncio
import logging
import math
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import redis.asyncio as aioredis

from backend.config import settings
from backend.mystery.mystery_classifier import MysteryEvent

logger = logging.getLogger(__name__)

# Thresholds
FREQ_SPIKE_THRESHOLD = 3.0      # 3x baseline → anomalous frequency
TEMPORAL_WINDOW_HOURS = 72      # events within 72h are temporally correlated
SPATIAL_CLUSTER_DISTANCE = 3    # within same country/region counts as cluster
MIN_CLUSTER_SIZE = 3            # need ≥ 3 events to flag cluster
CONFIDENCE_EMIT_THRESHOLD = 0.45  # min confidence to emit pattern


try:
    from dataclasses import dataclass

    @dataclass
    class AnomalySignal:
        signal_id: str
        signal_type: str        # freq_spike | temporal_cluster | spatial_cluster | combined
        events: List[str]       # list of article_hash
        subcategory: str
        region: Optional[str]
        event_count: int
        baseline_count: float
        frequency_ratio: float  # current / baseline
        temporal_span_hours: float
        confidence: float       # 0–1
        detected_at: str

except Exception:
    pass


class AnomalyDetector:
    """
    Tracks rolling windows of mystery events per subcategory/region.
    Emits AnomalySignal when patterns exceed thresholds.
    """

    WINDOW_HOURS = 24
    BASELINE_HOURS = 168  # 7-day baseline

    def __init__(self):
        self._redis: Optional[aioredis.Redis] = None
        self._in_memory: Dict[str, List[MysteryEvent]] = defaultdict(list)

    async def setup(self):
        self._redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

    async def teardown(self):
        if self._redis:
            await self._redis.aclose()

    async def ingest(self, event: MysteryEvent):
        """Record mystery event in rolling window."""
        now = datetime.utcnow()
        key = f"mystery:{event.subcategory}:{event.region or 'global'}"
        score = now.timestamp()

        await self._redis.zadd(key, {event.article_hash: score})
        await self._redis.expire(key, 86400 * 14)  # 14-day retention

        # In-memory for pattern analysis (bounded per subcat)
        bucket = f"{event.subcategory}:{event.region or 'global'}"
        self._in_memory[bucket].append(event)
        if len(self._in_memory[bucket]) > 500:
            self._in_memory[bucket] = self._in_memory[bucket][-500:]

    async def detect_signals(self) -> List[Dict]:
        """
        Runs full anomaly detection pass.
        Returns list of AnomalySignal dicts for pattern engine.
        """
        signals = []

        keys = []
        async for k in self._redis.scan_iter("mystery:*"):
            keys.append(k)

        if not keys:
            return signals

        now = datetime.utcnow().timestamp()
        window_start = now - (self.WINDOW_HOURS * 3600)
        baseline_start = now - (self.BASELINE_HOURS * 3600)

        pipe = self._redis.pipeline()
        for key in keys:
            pipe.zcount(key, window_start, now)
            pipe.zcount(key, baseline_start, window_start)
        counts = await pipe.execute()

        for i, key in enumerate(keys):
            current = counts[i * 2]
            baseline_total = counts[i * 2 + 1]
            if current == 0:
                continue

            baseline_per_day = max(baseline_total / 7, 0.5)
            freq_ratio = current / baseline_per_day

            if freq_ratio < FREQ_SPIKE_THRESHOLD:
                continue

            parts = key.split(":", 2)
            subcat = parts[1] if len(parts) > 1 else "unknown"
            region = parts[2] if len(parts) > 2 else "global"

            # Fetch event hashes in window
            hashes = await self._redis.zrangebyscore(key, window_start, now)

            # Temporal span
            if len(hashes) >= 2:
                ts_pipe = self._redis.pipeline()
                for h in hashes[:2]:
                    ts_pipe.zscore(key, h)
                ts_results = await ts_pipe.execute()
                valid_ts = [t for t in ts_results if t is not None]
                span_hours = (max(valid_ts) - min(valid_ts)) / 3600 if len(valid_ts) >= 2 else self.WINDOW_HOURS
            else:
                span_hours = 0.0

            confidence = self._compute_confidence(
                freq_ratio=freq_ratio,
                event_count=current,
                region=region,
            )

            if confidence < CONFIDENCE_EMIT_THRESHOLD:
                continue

            from datetime import datetime as dt
            signals.append({
                "signal_id": f"{subcat}:{region}:{int(now)}",
                "signal_type": "freq_spike",
                "events": list(hashes[:20]),
                "subcategory": subcat,
                "region": region if region != "global" else None,
                "event_count": current,
                "baseline_count": round(baseline_per_day, 2),
                "frequency_ratio": round(freq_ratio, 3),
                "temporal_span_hours": span_hours,
                "confidence": round(confidence, 3),
                "detected_at": dt.utcnow().isoformat(),
            })

        return sorted(signals, key=lambda x: x["confidence"], reverse=True)

    def detect_temporal_clusters(
        self, events: List[MysteryEvent]
    ) -> List[Dict]:
        """
        Groups events within TEMPORAL_WINDOW_HOURS of each other.
        Returns clusters of ≥ MIN_CLUSTER_SIZE.
        """
        if len(events) < MIN_CLUSTER_SIZE:
            return []

        # Sort by published_at
        def parse_ts(e: MysteryEvent) -> float:
            try:
                from dateutil.parser import parse
                return parse(e.published_at).timestamp()
            except Exception:
                return 0.0

        sorted_events = sorted(events, key=parse_ts)
        window_secs = TEMPORAL_WINDOW_HOURS * 3600
        clusters = []
        used = set()

        for i, anchor in enumerate(sorted_events):
            if anchor.article_hash in used:
                continue

            anchor_ts = parse_ts(anchor)
            cluster = [anchor]
            used.add(anchor.article_hash)

            for j, other in enumerate(sorted_events):
                if i == j or other.article_hash in used:
                    continue
                if abs(parse_ts(other) - anchor_ts) <= window_secs:
                    cluster.append(other)
                    used.add(other.article_hash)

            if len(cluster) >= MIN_CLUSTER_SIZE:
                avg_anomaly = sum(e.anomaly_score for e in cluster) / len(cluster)
                avg_credibility = sum(e.credibility_score for e in cluster) / len(cluster)
                clusters.append({
                    "cluster_type": "temporal",
                    "events": [e.article_hash for e in cluster],
                    "event_titles": [e.title for e in cluster],
                    "size": len(cluster),
                    "avg_anomaly_score": round(avg_anomaly, 3),
                    "avg_credibility": round(avg_credibility, 3),
                    "confidence": round(min(avg_anomaly * avg_credibility * 1.5, 1.0), 3),
                    "regions": list({e.region for e in cluster if e.region}),
                })

        return clusters

    def detect_spatial_clusters(
        self, events: List[MysteryEvent]
    ) -> List[Dict]:
        """Groups events by region. Flags regions with ≥ MIN_CLUSTER_SIZE events."""
        region_map: Dict[str, List[MysteryEvent]] = defaultdict(list)
        for e in events:
            region_map[e.region or "unknown"].append(e)

        clusters = []
        for region, evts in region_map.items():
            if region == "unknown" or len(evts) < MIN_CLUSTER_SIZE:
                continue
            avg_anomaly = sum(e.anomaly_score for e in evts) / len(evts)
            clusters.append({
                "cluster_type": "spatial",
                "region": region,
                "events": [e.article_hash for e in evts],
                "size": len(evts),
                "avg_anomaly_score": round(avg_anomaly, 3),
                "confidence": round(min(avg_anomaly * 1.2, 1.0), 3),
            })

        return clusters

    def _compute_confidence(
        self,
        freq_ratio: float,
        event_count: int,
        region: str,
    ) -> float:
        """
        Confidence = weighted combination of:
        - frequency spike magnitude (capped)
        - event count (log-scaled)
        - regional specificity bonus
        """
        freq_component = min((freq_ratio - FREQ_SPIKE_THRESHOLD) / 10, 0.5) + 0.3
        count_component = min(math.log(event_count + 1) / 5, 0.3)
        region_bonus = 0.1 if region != "global" else 0.0
        return min(freq_component + count_component + region_bonus, 1.0)
