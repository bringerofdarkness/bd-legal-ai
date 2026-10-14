"""
Reranking and Intent Scoring Service
Handles intent boosting, lexical bonuses, and definition-priority reranking.
"""

import re
from typing import List, Tuple, Any


class RerankerService:
    @staticmethod
    def normalize_query(query: str, analysis: dict) -> str:
        q = query.lower()

        if analysis["law_hint"] == "penal_code" and analysis["concept_hint"] == "theft":
            if analysis["intent"] == "punishment":
                return "punishment for theft penal code section 379 imprisonment fine"
            return "theft definition penal code section 378 dishonestly moveable property"

        if analysis["law_hint"] == "contract_act" and analysis["concept_hint"] == "section_2_definition":
            if (
                ("accept" in q or "accepted" in q or "assent" in q)
                and ("becomes" in q or "become" in q)
                and ("promise" in q or "offer" in q or "proposal" in q)
            ):
                return "acceptance proposal becomes promise contract act section 2 clause b"
            elif "proposal" in q or "offer" in q:
                return "proposal contract act section 2 clause a"
            elif "acceptance" in q or "accepted" in q or "assent" in q:
                return "acceptance contract act section 2 clause b"
            elif "promisee" in q or "promisor" in q:
                return "promisor promisee contract act section 2 clause c"
            elif "promise" in q:
                return "acceptance becomes promise contract act section 2 clause b"
            elif "consideration" in q:
                return "consideration contract act section 2 clause d"
            elif "void agreement" in q or ("void" in q and "agreement" in q):
                return "void agreement contract act section 2 clause g"
            elif "contract" in q:
                return "contract contract act section 2 clause h"
            elif "agreement" in q:
                return "agreement contract act section 2 clause e"
            elif "voidable" in q:
                return "voidable contract act section 2 clause i"

        return query

    @staticmethod
    def apply_intent_boost(query: str, docs_with_scores: List[Tuple[Any, float]]) -> List[Tuple[Any, float]]:
        q = query.lower()
        wants_definition = any(
            kw in q for kw in ["define", "definition", "meaning", "what is", "explains", "defines"]
        )
        wants_punishment = any(
            kw in q for kw in ["punishment", "punish", "penalty", "sentence", "fine", "imprisonment"]
        )

        boosted = []
        for doc, score in docs_with_scores:
            md = doc.metadata
            section = str(md.get("section_number") or "")
            heading = (md.get("section_heading") or "").lower()
            text = doc.page_content.lower()

            bonus = 0.0

            # Theft definition vs punishment
            if "theft" in q:
                if wants_definition and section == "378":
                    bonus += 1.5
                if wants_punishment and section == "379":
                    bonus += 1.5

                if wants_definition and ("is said to commit theft" in text or heading == "theft"):
                    bonus += 0.8
                if wants_punishment and "shall be punished" in text:
                    bonus += 0.8

            # Contract Act Section 2 clause intent
            if section == "2":
                if ("accept" in q and "promise" in q) and "becomes a promise" in text:
                    bonus += 1.5
                if "proposal" in q and "is said to make a proposal" in text:
                    bonus += 1.0
                if "consideration" in q and "consideration" in text:
                    bonus += 1.0
                if ("promisor" in q or "promisee" in q) and ("promisor" in text or "promisee" in text):
                    bonus += 1.0

            boosted.append((doc, score - bonus))

        boosted.sort(key=lambda x: x[1])
        return boosted

    @staticmethod
    def rerank_definition(query: str, docs_with_scores: List[Tuple[Any, float]]) -> List[Tuple[Any, float]]:
        q = query.lower()
        wants_definition = any(
            kw in q for kw in ["define", "definition", "meaning", "what is", "what constitutes", "is said to"]
        )
        if not wants_definition:
            return docs_with_scores

        def_score_re = re.compile(r"\bis said to\b|\bmeans\b|\bdenotes\b|\bwhoever\b", re.IGNORECASE)
        rescored = []

        for doc, dist in docs_with_scores:
            txt = doc.page_content[:600]
            md = doc.metadata
            heading = (md.get("section_heading") or "").lower()
            bonus = 0.0

            if "theft" in q and heading.strip() == "theft":
                bonus += 2.0

            section = str(md.get("section_number") or "")
            if section == "2":
                txt_lower = txt.lower()
                if "accept" in q and "promise" in q:
                    if "accepted becomes a promise" in txt_lower:
                        bonus += 3.0
                if "promisee" in q or "promisor" in q:
                    if "promisor" in txt_lower and "promisee" in txt_lower:
                        bonus += 3.0
                if "proposal" in q:
                    if "is said to make a proposal" in txt_lower:
                        bonus += 2.0

            if def_score_re.search(txt):
                bonus += 1.0

            if "punish" in txt.lower() or "shall be punished" in txt.lower():
                bonus -= 0.8

            rescored.append((doc, dist - bonus))

        rescored.sort(key=lambda x: x[1])
        return rescored
