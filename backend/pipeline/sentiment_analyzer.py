import logging
from functools import lru_cache
from typing import Dict, Tuple

from transformers import pipeline as hf_pipeline

logger = logging.getLogger(__name__)

POSITIVE_WORDS = [
    "growth", "rise", "gain", "surge", "recover", "improve", "success",
    "breakthrough", "achieve", "positive", "strong", "boost", "advance",
]
NEGATIVE_WORDS = [
    "fall", "drop", "crash", "decline", "loss", "risk", "crisis", "war",
    "attack", "threat", "collapse", "fail", "concern", "warning", "death",
]


@lru_cache(maxsize=1)
def _load_sentiment_pipeline():
    try:
        pipe = hf_pipeline(
            "sentiment-analysis",
            model="cardiffnlp/twitter-roberta-base-sentiment-latest",
            device=-1,
        )
        logger.info("Sentiment model loaded")
        return pipe
    except Exception as e:
        logger.warning("Sentiment model load failed: %s", e)
        return None


def keyword_sentiment(text: str) -> Tuple[str, float]:
    t = text.lower()
    pos = sum(1 for w in POSITIVE_WORDS if w in t)
    neg = sum(1 for w in NEGATIVE_WORDS if w in t)
    total = pos + neg or 1
    score = (pos - neg) / total
    if score > 0.1:
        return "positive", round(0.5 + score * 0.5, 4)
    elif score < -0.1:
        return "negative", round(0.5 - abs(score) * 0.5, 4)
    return "neutral", 0.5


class SentimentAnalyzer:
    LABEL_MAP = {
        "LABEL_0": "negative",
        "LABEL_1": "neutral",
        "LABEL_2": "positive",
        "negative": "negative",
        "neutral": "neutral",
        "positive": "positive",
    }

    def __init__(self):
        self._pipe = None

    def _ensure_loaded(self):
        if self._pipe is None:
            self._pipe = _load_sentiment_pipeline()

    def analyze(self, title: str, content: str) -> Dict:
        self._ensure_loaded()
        text = f"{title}. {content[:512]}"

        if self._pipe:
            try:
                result = self._pipe(text[:512], truncation=True)[0]
                label = self.LABEL_MAP.get(result["label"], "neutral")
                score = round(result["score"], 4)
                return {
                    "label": label,
                    "score": score,
                    "positive": score if label == "positive" else round(1 - score, 4) * 0.3,
                    "negative": score if label == "negative" else round(1 - score, 4) * 0.3,
                    "neutral": score if label == "neutral" else round(1 - score, 4) * 0.4,
                }
            except Exception as e:
                logger.warning("Sentiment analysis error: %s", e)

        label, score = keyword_sentiment(text)
        return {
            "label": label,
            "score": score,
            "positive": score if label == "positive" else 0.2,
            "negative": score if label == "negative" else 0.2,
            "neutral": score if label == "neutral" else 0.6,
        }
