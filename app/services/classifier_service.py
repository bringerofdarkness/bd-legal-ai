"""
Classifier and Routing Service for Bangladesh Legal AI
Consolidates intent classification, out-of-scope cyber filtering, and statute routing.
"""

from typing import Optional, Dict, Any
from numpy import dot
from numpy.linalg import norm
from app.core.registry import LAW_REGISTRY
from app.core.embeddings import get_embedding_model
from app.core.config import settings

_LAW_EMBEDDINGS: Optional[Dict[str, Any]] = None


def _get_law_embeddings() -> Dict[str, Any]:
    global _LAW_EMBEDDINGS
    if _LAW_EMBEDDINGS is None:
        emb_model = get_embedding_model()
        _LAW_EMBEDDINGS = {}
        for law_id, config in LAW_REGISTRY.items():
            text = config.display_name + " " + " ".join(config.aliases)
            _LAW_EMBEDDINGS[law_id] = emb_model.embed_query(text)
    return _LAW_EMBEDDINGS


def cosine_sim(a, b) -> float:
    return float(dot(a, b) / (norm(a) * norm(b)))


class ClassifierService:
    @staticmethod
    def classify_query(query: str) -> str:
        q = query.lower().strip()
        if "which section" in q or "what section" in q or "section" in q:
            return "section_lookup"
        if any(term in q for term in ["punishment", "penalty", "sentence", "fine", "imprisonment"]):
            return "punishment"
        if any(term in q for term in ["what is", "define", "meaning of", "legal meaning", "who is called", "who is"]):
            return "definition"
        return "concept"

    @staticmethod
    def is_cyber_query(q: str) -> bool:
        cyber_terms = ["cyber", "facebook", "hack", "hacked", "online account", "account"]
        q_lower = q.lower()
        return any(term in q_lower for term in cyber_terms)

    @staticmethod
    def is_supported_scope(q: str, analysis: Dict[str, Any]) -> bool:
        supported_contract_terms = {
            "proposal", "acceptance", "promise", "promisor", "promisee",
            "consideration", "agreement", "contract"
        }
        theft_terms = {
            "theft", "steal", "stole", "stolen", "steals", "stealing",
            "took", "taken", "bag", "phone", "mobile", "money", "watch", "property"
        }
        q_lower = q.lower()
        return (
            analysis.get("law_hint") in {"penal_code", "contract_act"}
            or any(term in q_lower for term in supported_contract_terms)
            or any(term in q_lower for term in theft_terms)
        )

    @classmethod
    def analyze_query(cls, query: str) -> Dict[str, Any]:
        q = query.lower().strip()
        analysis = {
            "law_hint": None,
            "concept_hint": None,
            "intent": "provision",
        }

        theft_like = (
            any(word in q for word in ["theft", "stole", "stolen", "steal", "stealing"])
            or ("lost" in q and any(obj in q for obj in ["watch", "phone", "mobile", "money", "bag", "property"]))
            or ("took" in q and any(obj in q for obj in ["watch", "phone", "mobile", "money", "bag", "property"]))
            or any(
                phrase in q
                for phrase in [
                    "took my", "took my bag", "took my phone", "took my money",
                    "he took", "someone took", "took without permission"
                ]
            )
        )

        if theft_like:
            analysis["law_hint"] = "penal_code"
            analysis["concept_hint"] = "theft"
            if any(
                kw in q for kw in [
                    "what is", "define", "definition", "meaning", "what does",
                    "explains", "defines", "which section defines"
                ]
            ) or "not the penalty" in q:
                analysis["intent"] = "definition"
            elif any(
                kw in q for kw in [
                    "punishment", "punish", "penalty", "sentence", "imprisonment",
                    "what happens if"
                ]
            ):
                analysis["intent"] = "punishment"
            return analysis

        if any(
            word in q
            for word in [
                "proposal", "offer", "acceptance", "accepted", "assent",
                "consideration", "agreement", "contract",
                "void agreement", "voidable", "promise", "promisor", "promisee"
            ]
        ):
            analysis["law_hint"] = "contract_act"
            analysis["concept_hint"] = "section_2_definition"

            if (
                ("accept" in q or "accepted" in q or "assent" in q)
                and ("becomes" in q or "become" in q)
                and ("promise" in q or "offer" in q or "proposal" in q)
            ):
                analysis["intent"] = "definition"
            elif any(
                kw in q for kw in [
                    "what is", "define", "definition", "meaning", "what does",
                    "explains", "defines"
                ]
            ):
                analysis["intent"] = "definition"
            return analysis

        if any(kw in q for kw in ["punishment", "punish", "penalty", "sentence", "fine", "imprisonment", "what happens if"]):
            analysis["intent"] = "punishment"
        elif any(kw in q for kw in ["what is", "define", "definition", "meaning", "what does", "explains", "defines"]):
            analysis["intent"] = "definition"

        return analysis

    @classmethod
    def choose_active_law(cls, query: str) -> Optional[str]:
        q = query.lower().strip()
        best_law_id = None
        best_alias_score = 0

        for law_id, config in LAW_REGISTRY.items():
            score = 0
            for alias in config.aliases:
                alias_l = alias.lower()
                if alias_l in q:
                    score += len(alias_l)
            if score > best_alias_score:
                best_alias_score = score
                best_law_id = law_id

        if best_alias_score > 0:
            return best_law_id

        emb_model = get_embedding_model()
        q_emb = emb_model.embed_query(q)
        law_embs = _get_law_embeddings()

        best_score = 0.0
        for law_id, law_emb in law_embs.items():
            sim = cosine_sim(q_emb, law_emb)
            if sim > best_score:
                best_score = sim
                best_law_id = law_id

        if best_score < settings.SIMILARITY_THRESHOLD:
            return None

        return best_law_id
