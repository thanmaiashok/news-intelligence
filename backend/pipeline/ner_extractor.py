import logging
from functools import lru_cache
from typing import Dict, List

import spacy

logger = logging.getLogger(__name__)

SPACY_MODEL = "en_core_web_sm"


@lru_cache(maxsize=1)
def _load_spacy():
    try:
        nlp = spacy.load(SPACY_MODEL)
        logger.info("spaCy model loaded: %s", SPACY_MODEL)
        return nlp
    except OSError:
        logger.warning("spaCy model not found, run: python -m spacy download en_core_web_sm")
        return None


class NERExtractor:
    ENTITY_TYPES = {
        "PERSON": "person",
        "ORG": "organization",
        "GPE": "country_city",
        "LOC": "location",
        "NORP": "nationality_group",
        "MONEY": "financial",
        "PERCENT": "financial",
        "DATE": "temporal",
        "EVENT": "event",
        "PRODUCT": "product",
        "LAW": "law",
        "WORK_OF_ART": "media",
    }

    def __init__(self):
        self._nlp = None

    def _ensure_loaded(self):
        if self._nlp is None:
            self._nlp = _load_spacy()

    def extract(self, title: str, content: str) -> Dict[str, List[Dict]]:
        self._ensure_loaded()
        entities: Dict[str, List[Dict]] = {}

        if not self._nlp:
            return entities

        text = f"{title}. {content[:2000]}"
        try:
            doc = self._nlp(text)
            for ent in doc.ents:
                ent_type = self.ENTITY_TYPES.get(ent.label_, None)
                if not ent_type:
                    continue

                name = ent.text.strip()
                if len(name) < 2:
                    continue

                if ent_type not in entities:
                    entities[ent_type] = []

                # dedup within article
                existing_names = {e["name"] for e in entities[ent_type]}
                if name not in existing_names:
                    entities[ent_type].append({
                        "name": name,
                        "label": ent.label_,
                        "start": ent.start_char,
                        "end": ent.end_char,
                    })
        except Exception as e:
            logger.warning("NER error: %s", e)

        return entities

    def flat_entities(self, title: str, content: str) -> List[Dict]:
        """Returns flat list for graph storage."""
        nested = self.extract(title, content)
        result = []
        for ent_type, items in nested.items():
            for item in items:
                result.append({**item, "type": ent_type})
        return result
