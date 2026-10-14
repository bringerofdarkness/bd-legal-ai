"""
Classifier and Routing Service for Bangladesh Legal AI
AI-driven intent classification, statute routing, and section reference extraction
across all 10 indexed Bangladesh enactments.
"""

import re
from typing import Optional, Dict, Any
from numpy import dot
from numpy.linalg import norm
from app.core.registry import LAW_REGISTRY
from app.core.embeddings import get_embedding_model
from app.core.config import settings

_LAW_EMBEDDINGS: Optional[Dict[str, Any]] = None

# Multi-lingual Bengali digit transliterator
BN_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")


def _get_law_embeddings() -> Dict[str, Any]:
    global _LAW_EMBEDDINGS
    if _LAW_EMBEDDINGS is None:
        emb_model = get_embedding_model()
        _LAW_EMBEDDINGS = {}
        for law_id, config in LAW_REGISTRY.items():
            text = f"{config.display_name} {config.description} {' '.join(config.aliases)}"
            _LAW_EMBEDDINGS[law_id] = emb_model.embed_query(text)
    return _LAW_EMBEDDINGS


def cosine_sim(a, b) -> float:
    return float(dot(a, b) / (norm(a) * norm(b)))


class ClassifierService:
    @staticmethod
    def classify_query(query: str) -> str:
        """Categorizes legal query intent."""
        q = query.lower().strip()
        if any(term in q for term in ["which section", "what section", "section", "ধারা", "sec."]):
            return "section_lookup"
        if any(term in q for term in ["punishment", "penalty", "sentence", "fine", "imprisonment", "শাস্তি", "দণ্ড"]):
            return "punishment"
        if any(term in q for term in ["bail", "bailable", "cognizable", "arrest", "warrant", "জামিন", "গ্রেপ্তার"]):
            return "procedure"
        if any(term in q for term in ["what is", "define", "meaning of", "legal meaning", "who is", "সংজ্ঞা", "কাকে বলে"]):
            return "definition"
        return "concept"

    @staticmethod
    def extract_section_no(query: str) -> Optional[str]:
        """Extracts mentioned section number in English or Bengali (e.g. 'section 302', 'ধারা ৩৭৮', '৩৭৯ ধারায়')."""
        q_norm = query.translate(BN_DIGITS)
        # Prefix match: "section 302", "sec 302", "ধারা ৩০২"
        match = re.search(r"(?:section|sec|ধারা)\s*[:#]?\s*(\d{1,4}[A-Z]?)", q_norm, re.IGNORECASE)
        if match:
            return match.group(1).upper()
        # Postfix match: "302 section", "৩৭৯ ধারায়", "৪২০ ধারা"
        match2 = re.search(r"(\d{1,4}[A-Z]?)\s*(?:section|sec|ধারা|ধারায়)", q_norm, re.IGNORECASE)
        if match2:
            return match2.group(1).upper()
        # Direct number if query is very short like "302" or "378"
        if re.match(r"^\s*(\d{1,4}[A-Z]?)\s*$", q_norm):
            return q_norm.strip().upper()
        return None

    @classmethod
    def analyze_query(cls, query: str) -> Dict[str, Any]:
        """Deep query analysis: intent, explicit section mentions, and statute routing."""
        q = query.lower().strip()
        intent = cls.classify_query(q)
        section_no = cls.extract_section_no(query)
        law_id = cls.choose_active_law(query)

        return {
            "query": query,
            "intent": intent,
            "section_no": section_no,
            "law_hint": law_id,
        }

    @classmethod
    def choose_active_law(cls, query: str) -> Optional[str]:
        """
        Identifies if a specific enactment is explicitly referenced in the query.
        Returns the act_id if matched; returns None if query spans general law.
        """
        q = query.lower().strip()

        # 1. Exact alias / title matching (longest matches first to avoid subphrase collisions)
        all_candidates = []
        for law_id, config in LAW_REGISTRY.items():
            for alias in config.aliases:
                alias_l = alias.lower().strip()
                if len(alias_l) >= 3:
                    all_candidates.append((alias_l, config.act_id))

        # Sort descending by length
        all_candidates.sort(key=lambda x: len(x[0]), reverse=True)

        for alias_l, act_id in all_candidates:
            if alias_l in q:
                return act_id

        # 2. Return None to allow global hybrid search across all 10 Acts
        return None

    # Legacy compatibility stubs for deprecation
    @staticmethod
    def is_cyber_query(q: str) -> bool:
        return False

    @staticmethod
    def is_supported_scope(q: str, analysis: Dict[str, Any]) -> bool:
        return True
