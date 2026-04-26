import asyncio
import json
import logging
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import redis.asyncio as aioredis

from backend.config import settings

logger = logging.getLogger(__name__)


class TrendDetector:
    """
    Sliding-window trend detection over topic/keyword frequency.
    Compares recent 30-min window vs previous 30-min window.
    Spike = current_count / max(prev_count, 1) > threshold.
    """

    WINDOW_SECONDS = 1800  # 30 min
    SPIKE_THRESHOLD = 2.5
    TOP_K = 20

    def __init__(self):
        self._redis: Optional[aioredis.Redis] = None

    async def setup(self):
        self._redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

    async def teardown(self):
        if self._redis:
            await self._redis.aclose()

    async def ingest(self, categories: List[str], entities: List[Dict], title: str):
        now = int(datetime.utcnow().timestamp())
        pipe = self._redis.pipeline()

        # Category counts
        for cat in categories:
            key = f"trend:cat:{cat}"
            pipe.zadd(key, {str(now): now})
            pipe.expire(key, self.WINDOW_SECONDS * 4)

        # Entity counts
        for ent in entities:
            name = ent.get("name", "")
            ent_type = ent.get("type", "unknown")
            if name and len(name) > 2:
                key = f"trend:ent:{ent_type}:{name[:50]}"
                pipe.zadd(key, {str(now): now})
                pipe.expire(key, self.WINDOW_SECONDS * 4)

        # Title keywords (top 5 non-stopwords)
        stopwords = {"the", "a", "an", "in", "of", "to", "and", "is", "for", "on", "at", "by"}
        words = [
            w.lower() for w in title.split()
            if len(w) > 4 and w.lower() not in stopwords
        ][:5]
        for word in words:
            key = f"trend:kw:{word}"
            pipe.zadd(key, {str(now): now})
            pipe.expire(key, self.WINDOW_SECONDS * 4)

        await pipe.execute()

    async def compute_trends(self) -> List[Dict]:
        now = int(datetime.utcnow().timestamp())
        current_start = now - self.WINDOW_SECONDS
        prev_start = current_start - self.WINDOW_SECONDS

        # Scan all trend keys
        keys = []
        async for key in self._redis.scan_iter("trend:*"):
            keys.append(key)

        if not keys:
            return []

        pipe = self._redis.pipeline()
        for key in keys:
            pipe.zcount(key, current_start, now)
            pipe.zcount(key, prev_start, current_start)
        results = await pipe.execute()

        trends = []
        for i, key in enumerate(keys):
            current = results[i * 2]
            prev = results[i * 2 + 1]
            if current == 0:
                continue

            velocity = current / max(prev, 1)
            parts = key.split(":", 2)
            kind = parts[1] if len(parts) > 1 else "unknown"
            name = parts[2] if len(parts) > 2 else key

            trends.append({
                "key": key,
                "name": name,
                "kind": kind,
                "current_count": current,
                "prev_count": prev,
                "velocity": round(velocity, 3),
                "is_spike": velocity >= self.SPIKE_THRESHOLD,
                "computed_at": datetime.utcnow().isoformat(),
            })

        return sorted(trends, key=lambda x: x["velocity"], reverse=True)[: self.TOP_K]

    async def top_trends_cached(self) -> List[Dict]:
        """Cached version updated every 2 minutes."""
        cache_key = "trend:cache:top"
        cached = await self._redis.get(cache_key)
        if cached:
            return json.loads(cached)

        trends = await self.compute_trends()
        await self._redis.setex(cache_key, 120, json.dumps(trends))
        return trends
