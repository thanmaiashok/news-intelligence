import logging
from functools import lru_cache
from typing import Dict, List, Tuple

from transformers import pipeline as hf_pipeline

logger = logging.getLogger(__name__)

CATEGORIES = [
    "politics",
    "finance",
    "technology",
    "war_conflict",
    "climate_environment",
    "health_medical",
    "science",
    "sports",
    "entertainment",
    "business",
    "crime_law",
    "social_issues",
    "energy",
    "diplomacy",
]

# Keyword fallback for fast pre-filtering
KEYWORD_MAP: Dict[str, List[str]] = {
    "finance": ["stock", "market", "gdp", "inflation", "fed", "interest rate", "bond", "crypto", "bitcoin", "nasdaq", "s&p", "earnings", "ipo"],
    "technology": ["ai", "machine learning", "software", "hardware", "apple", "google", "microsoft", "startup", "chip", "semiconductor", "cyber"],
    "war_conflict": ["war", "military", "troops", "attack", "bomb", "missile", "nato", "ukraine", "russia", "israel", "gaza", "conflict", "airstrike"],
    "health_medical": ["covid", "cancer", "vaccine", "fda", "who", "pandemic", "drug", "clinical trial", "hospital", "disease", "health"],
    "climate_environment": ["climate", "carbon", "emission", "fossil fuel", "renewable", "solar", "wind energy", "deforestation", "flood", "drought"],
    "sports": ["football", "basketball", "soccer", "nba", "nfl", "championship", "tournament", "olympic", "athlete", "score"],
    "politics": ["president", "congress", "senate", "election", "vote", "democrat", "republican", "parliament", "minister", "government", "policy"],
    "business": ["acquisition", "merger", "revenue", "profit", "ceo", "company", "corporate", "supply chain", "trade"],
    "crime_law": ["arrest", "murder", "court", "judge", "trial", "lawsuit", "indicted", "conviction", "investigation", "fbi", "police"],
    "energy": ["oil", "gas", "opec", "barrel", "refinery", "lng", "pipeline", "petroleum", "coal"],
    "diplomacy": ["sanction", "treaty", "summit", "un ", "united nations", "ambassador", "bilateral", "foreign minister"],
}


@lru_cache(maxsize=1)
def _load_classifier():
    try:
        clf = hf_pipeline(
            "zero-shot-classification",
            model="facebook/bart-large-mnli",
            device=-1,  # CPU; set to 0 for GPU
        )
        logger.info("Zero-shot classifier loaded")
        return clf
    except Exception as e:
        logger.warning("Classifier load failed, using keyword fallback: %s", e)
        return None


def keyword_classify(text: str) -> List[Tuple[str, float]]:
    text_lower = text.lower()
    scores = {}
    for cat, keywords in KEYWORD_MAP.items():
        count = sum(1 for kw in keywords if kw in text_lower)
        if count > 0:
            scores[cat] = min(count / 3, 1.0)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


class ArticleClassifier:
    def __init__(self, use_ml: bool = True):
        self._use_ml = use_ml
        self._clf = None

    def _ensure_loaded(self):
        if self._use_ml and self._clf is None:
            self._clf = _load_classifier()

    def classify(
        self, title: str, content: str, top_k: int = 3
    ) -> List[Tuple[str, float]]:
        self._ensure_loaded()
        text = f"{title}. {content[:512]}"

        if self._clf:
            try:
                result = self._clf(text, CATEGORIES, multi_label=True)
                pairs = list(zip(result["labels"], result["scores"]))
                return [(label, round(score, 4)) for label, score in pairs[:top_k] if score > 0.3]
            except Exception as e:
                logger.warning("ML classify error: %s", e)

        # Keyword fallback
        results = keyword_classify(text)
        return results[:top_k] if results else [("general", 0.5)]
