"""
Mystery Classification Layer

Classifies incoming articles into MYSTERY_EVENT subcategories.
Assigns credibility_score, anomaly_score, source_reliability.
Strict filtering: only high-credibility sources generate mystery events.
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Sources with established editorial standards get higher base reliability
HIGH_RELIABILITY_SOURCES = {
    "reuters", "bbc", "ap news", "associated press", "the guardian",
    "new york times", "washington post", "nature", "science", "nasa",
    "noaa", "usgs", "who", "cdc", "esa", "nih", "mit", "sciencedirect",
    "new scientist", "scientific american",
}

LOW_CREDIBILITY_PATTERNS = [
    r"(daily mail|the sun|national enquirer|infowars|zerohedge"
    r"|naturalnews|beforeitsnews|superstation95|worldnewsdailyreport"
    r"|empirenews|huzlers|theonion)",
]

MYSTERY_SUBCATEGORY_SIGNALS: Dict[str, Dict] = {
    "ufo_alien": {
        "keywords": [
            "ufo", "uap", "unidentified aerial phenomenon", "flying saucer",
            "extraterrestrial", "alien craft", "alien sighting", "orb sighting",
            "gimbal video", "tic-tac ufo", "congressional uap", "pentagon uap",
            "space anomaly", "unexplained object", "non-human intelligence",
        ],
        "require_any": 1,
        "base_anomaly": 0.55,
        "label": "UFO / Alien Sighting",
    },
    "supernatural_paranormal": {
        "keywords": [
            "ghost", "haunted", "poltergeist", "possession", "exorcism",
            "demonic", "apparition", "supernatural", "paranormal", "seance",
            "cryptid", "bigfoot", "sasquatch", "loch ness", "chupacabra",
            "yeti", "mothman", "unexplained lights",
        ],
        "require_any": 1,
        "base_anomaly": 0.40,
        "label": "Supernatural / Paranormal",
    },
    "unexplained_scientific": {
        "keywords": [
            "unexplained phenomenon", "scientists baffled", "defies explanation",
            "anomalous signal", "mystery signal", "fast radio burst",
            "oumuamua", "dark matter detected", "gravitational anomaly",
            "magnetic anomaly", "radiation anomaly", "unknown pathogen",
            "mass die-off unexplained", "sudden unexplained",
            "inexplicable", "contradicts known physics",
        ],
        "require_any": 1,
        "base_anomaly": 0.65,
        "label": "Unexplained Scientific Anomaly",
    },
    "rare_impossible": {
        "keywords": [
            "rarest ever recorded", "never seen before", "once in a millennium",
            "statistically impossible", "unprecedented event",
            "broke all records", "completely unexpected",
            "defied all predictions", "zero probability",
            "freak accident", "simultaneous mass",
        ],
        "require_any": 1,
        "base_anomaly": 0.50,
        "label": "Rare / Unprecedented Event",
    },
    "emerging_pattern_signal": {
        "keywords": [
            "coordinated attack", "pattern of incidents", "series of unexplained",
            "cluster of cases", "multiple witnesses", "independently confirmed",
            "verified by multiple", "corroborated reports",
            "simultaneous occurrences", "non-coincidental timing",
        ],
        "require_any": 2,  # stricter — requires 2+ signals
        "base_anomaly": 0.45,
        "label": "Emerging Pattern Signal",
    },
}

# Credibility-boosting phrases
CREDIBILITY_BOOST_PHRASES = [
    "confirmed by", "verified by", "peer-reviewed", "published in",
    "official statement", "government confirmed", "nasa confirmed",
    "military confirmed", "multiple witnesses", "video evidence",
    "photographic evidence", "sensor data", "radar confirmed",
]

CREDIBILITY_PENALTY_PHRASES = [
    "anonymous source", "unverified claim", "rumor", "conspiracy theory",
    "some say", "people claim", "allegedly", "reportedly seen by one",
    "social media claim", "viral post", "twitter claim",
]


@dataclass
class MysteryEvent:
    article_hash: str
    url: str
    title: str
    source: str
    published_at: str
    subcategory: str
    subcategory_label: str
    credibility_score: float       # 0–1 source + content credibility
    anomaly_score: float           # 0–1 how anomalous/unusual
    source_reliability: float      # 0–1 source reputation
    matched_signals: List[str]
    region: Optional[str] = None
    entities: List[Dict] = field(default_factory=list)
    content_snippet: str = ""


def _source_reliability(source_name: str) -> float:
    name = source_name.lower()
    for low_pat in LOW_CREDIBILITY_PATTERNS:
        if re.search(low_pat, name, re.I):
            return 0.1
    for high_src in HIGH_RELIABILITY_SOURCES:
        if high_src in name:
            return 0.9
    # Default mid-tier
    return 0.5


def _content_credibility(text: str) -> float:
    text_lower = text.lower()
    boost = sum(1 for p in CREDIBILITY_BOOST_PHRASES if p in text_lower)
    penalty = sum(1 for p in CREDIBILITY_PENALTY_PHRASES if p in text_lower)
    raw = 0.5 + (boost * 0.08) - (penalty * 0.1)
    return max(0.05, min(1.0, raw))


def classify_mystery(article: Dict) -> Optional[MysteryEvent]:
    """
    Returns MysteryEvent if article qualifies, else None.
    Article must pass source reliability threshold AND keyword threshold.
    """
    source = article.get("source", "")
    src_reliability = _source_reliability(source)

    # Hard reject low-credibility sources
    if src_reliability < 0.3:
        return None

    title = article.get("title", "")
    content = article.get("content", "")
    text = f"{title} {content}".lower()

    best_match: Optional[Tuple[str, List[str], float]] = None

    for subcat, config in MYSTERY_SUBCATEGORY_SIGNALS.items():
        matched = [kw for kw in config["keywords"] if kw in text]
        if len(matched) >= config["require_any"]:
            if best_match is None or len(matched) > len(best_match[1]):
                best_match = (subcat, matched, config["base_anomaly"])

    if not best_match:
        return None

    subcat, matched_signals, base_anomaly = best_match
    config = MYSTERY_SUBCATEGORY_SIGNALS[subcat]

    content_cred = _content_credibility(text)
    credibility = round((src_reliability * 0.6) + (content_cred * 0.4), 3)

    # Anomaly score boosted by signal count and source reliability
    signal_boost = min(len(matched_signals) * 0.05, 0.3)
    anomaly_score = round(
        min(base_anomaly + signal_boost + (src_reliability * 0.1), 1.0), 3
    )

    return MysteryEvent(
        article_hash=article.get("content_hash", ""),
        url=article.get("url", ""),
        title=title,
        source=source,
        published_at=str(article.get("published_at", "")),
        subcategory=subcat,
        subcategory_label=config["label"],
        credibility_score=credibility,
        anomaly_score=anomaly_score,
        source_reliability=src_reliability,
        matched_signals=matched_signals,
        region=article.get("region"),
        entities=article.get("entities", []),
        content_snippet=content[:600],
    )
