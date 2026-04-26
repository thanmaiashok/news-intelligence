import logging
from functools import lru_cache
from typing import List, Union

import numpy as np

from backend.config import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _load_model():
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(settings.EMBEDDING_MODEL)
        logger.info("Embedding model loaded: %s", settings.EMBEDDING_MODEL)
        return model
    except Exception as e:
        logger.warning("Embedding model load failed: %s", e)
        return None


class EmbeddingService:
    def __init__(self):
        self._model = None

    def warm(self):
        """Pre-load model at startup so first article doesn't pay download cost."""
        self._model = _load_model()

    def _ensure_loaded(self):
        if self._model is None:
            self._model = _load_model()

    def encode(self, text: str) -> np.ndarray:
        self._ensure_loaded()
        if self._model:
            try:
                vec = self._model.encode(text, normalize_embeddings=True)
                return vec
            except Exception as e:
                logger.warning("Encode error: %s", e)
        # Fallback: zero vector
        return np.zeros(settings.EMBEDDING_DIM, dtype="float32")

    def encode_batch(self, texts: List[str]) -> np.ndarray:
        self._ensure_loaded()
        if self._model:
            try:
                return self._model.encode(texts, normalize_embeddings=True, batch_size=32)
            except Exception as e:
                logger.warning("Batch encode error: %s", e)
        return np.zeros((len(texts), settings.EMBEDDING_DIM), dtype="float32")
