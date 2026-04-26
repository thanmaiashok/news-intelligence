import hashlib
import logging
import re
from typing import Optional

import redis.asyncio as aioredis
from datasketch import MinHash, MinHashLSH

from backend.config import settings

logger = logging.getLogger(__name__)


def normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def compute_simhash(text: str) -> int:
    """64-bit SimHash for near-duplicate detection."""
    words = normalize_text(text).split()
    v = [0] * 64

    for word in words:
        h = int(hashlib.md5(word.encode()).hexdigest(), 16)
        for i in range(64):
            if h & (1 << i):
                v[i] += 1
            else:
                v[i] -= 1

    fingerprint = 0
    for i in range(64):
        if v[i] > 0:
            fingerprint |= 1 << i
    return fingerprint


def hamming_distance(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def build_minhash(text: str, num_perm: int = 128) -> MinHash:
    m = MinHash(num_perm=num_perm)
    words = normalize_text(text).split()
    for w in words:
        m.update(w.encode())
    return m


class Deduplicator:
    def __init__(self):
        self._redis: Optional[aioredis.Redis] = None
        self._lsh = MinHashLSH(threshold=settings.MINHASH_THRESHOLD, num_perm=128)
        self._lsh_keys: set = set()

    async def setup(self):
        self._redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

    async def teardown(self):
        if self._redis:
            await self._redis.aclose()

    async def is_duplicate(self, content_hash: str, title: str, content: str) -> bool:
        """Three-layer dedup: exact hash, simhash, minhash LSH."""

        # Layer 1: exact content hash (already checked in base crawler, but double-check)
        exact_key = f"hash:{content_hash}"
        if await self._redis.exists(exact_key):
            return True
        await self._redis.setex(exact_key, 86400 * 7, "1")

        # Layer 2: SimHash title
        text = (title + " " + content[:300])
        sim = compute_simhash(text)
        sim_key = f"simhash:{sim}"
        existing = await self._redis.get(sim_key)
        if existing:
            stored_sim = int(existing)
            if hamming_distance(sim, stored_sim) <= settings.SIMHASH_THRESHOLD:
                return True
        await self._redis.setex(sim_key, 86400 * 3, str(sim))

        # Layer 3: MinHash LSH (in-memory, best-effort)
        try:
            m = build_minhash(title + " " + content[:500])
            candidates = self._lsh.query(m)
            if candidates:
                return True
            lsh_key = content_hash[:16]
            if lsh_key not in self._lsh_keys:
                self._lsh.insert(lsh_key, m)
                self._lsh_keys.add(lsh_key)
                if len(self._lsh_keys) > 50000:
                    # evict oldest — simple LRU approximation
                    oldest = next(iter(self._lsh_keys))
                    try:
                        self._lsh.remove(oldest)
                    except Exception:
                        pass
                    self._lsh_keys.discard(oldest)
        except Exception as e:
            logger.debug("MinHash error: %s", e)

        return False
