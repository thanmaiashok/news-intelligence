import logging
import os
import pickle
from typing import Dict, List

import numpy as np

from backend.config import settings

logger = logging.getLogger(__name__)

_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".data", "faiss")
os.makedirs(_DATA_DIR, exist_ok=True)
FAISS_INDEX_PATH = os.path.join(_DATA_DIR, "news.index")
FAISS_META_PATH = os.path.join(_DATA_DIR, "news_meta.pkl")


class VectorStore:
    def __init__(self):
        self._index = None
        self._metadata: Dict[int, Dict] = {}
        self._id_map: Dict[str, int] = {}
        self._next_id = 0

    async def setup(self):
        try:
            import faiss

            if os.path.exists(FAISS_INDEX_PATH):
                self._index = faiss.read_index(FAISS_INDEX_PATH)
                with open(FAISS_META_PATH, "rb") as f:
                    data = pickle.load(f)
                    self._metadata = data["metadata"]
                    self._id_map = data["id_map"]
                    self._next_id = data["next_id"]
                logger.info("FAISS index loaded: %d vectors", self._index.ntotal)
            else:
                quantizer = faiss.IndexFlatIP(settings.EMBEDDING_DIM)
                self._index = faiss.IndexIVFFlat(
                    quantizer, settings.EMBEDDING_DIM, 100, faiss.METRIC_INNER_PRODUCT
                )
                self._index.train(
                    np.random.rand(1000, settings.EMBEDDING_DIM).astype("float32")
                )
                logger.info("FAISS index created (dim=%d)", settings.EMBEDDING_DIM)
        except ImportError:
            logger.warning("faiss not installed — vector search disabled")

    async def upsert(self, doc_id: str, embedding: List[float], metadata: Dict):
        if self._index is None:
            return

        import faiss

        vec = np.array([embedding], dtype="float32")
        faiss.normalize_L2(vec)
        int_id = self._id_map.get(doc_id)
        if int_id is None:
            int_id = self._next_id
            self._next_id += 1
            self._id_map[doc_id] = int_id

        if not self._index.is_trained:
            return

        self._index.add_with_ids(vec, np.array([int_id], dtype="int64"))
        self._metadata[int_id] = metadata

        if self._next_id % 100 == 0:
            self._persist_faiss()

    def _persist_faiss(self):
        if self._index is None:
            return
        try:
            import faiss

            faiss.write_index(self._index, FAISS_INDEX_PATH)
            with open(FAISS_META_PATH, "wb") as f:
                pickle.dump(
                    {"metadata": self._metadata, "id_map": self._id_map, "next_id": self._next_id},
                    f,
                )
        except Exception as e:
            logger.warning("FAISS persist error: %s", e)

    async def search(self, query_embedding: List[float], top_k: int = 10) -> List[Dict]:
        if self._index is None or self._index.ntotal == 0:
            return []

        import faiss

        vec = np.array([query_embedding], dtype="float32")
        faiss.normalize_L2(vec)
        scores, ids = self._index.search(vec, top_k)

        results = []
        for score, int_id in zip(scores[0], ids[0]):
            if int_id == -1:
                continue
            meta = self._metadata.get(int_id, {})
            results.append({"score": float(score), **meta})
        return results

    async def teardown(self):
        self._persist_faiss()
