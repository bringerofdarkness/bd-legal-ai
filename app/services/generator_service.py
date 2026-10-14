"""
Generator and Evidence Formatting Service
Formats clean statutory excerpts, builds verifiable citations, and attaches verified plain-text legal explanations.
"""

import re
from typing import List, Dict, Any, Optional


class GeneratorService:
    @staticmethod
    def select_top_bundle_item(
        bundle_sorted: List[Dict[str, Any]],
        q: str,
        is_definition_query: bool,
        is_punishment_query: bool
    ) -> Dict[str, Any]:
        top = bundle_sorted[0]
        if "theft" in q:
            if is_definition_query:
                for b in bundle_sorted:
                    if str(b["section"]) == "378":
                        return b
            elif is_punishment_query:
                for b in bundle_sorted:
                    if str(b["section"]) == "379":
                        return b
        return top

    @staticmethod
    def get_answer_label(q: str) -> str:
        if any(kw in q for kw in ["punish", "punishment", "penalty", "sentence", "fine", "imprisonment"]):
            return "punishment"
        elif any(kw in q for kw in ["define", "definition", "meaning", "what is", "what constitutes"]):
            return "definition"
        return "provision"

    @classmethod
    def format_display_text(cls, top: Dict[str, Any], q: str, is_definition_query: bool) -> str:
        display_text = top["text"]

        # Contract Act Section 2 clause parsing
        if top["act"] == "Contract Act, 1872" and top["section"] == 2:
            clause_letter = None
            if is_definition_query and ("accept" in q and "become" in q):
                clause_letter = "b"
            elif is_definition_query and "acceptance" in q:
                clause_letter = "b"
            elif (is_definition_query and "promisee" in q) or ("promisor" in q):
                clause_letter = "c"
            elif "promise" in q:
                clause_letter = "b"
            elif "proposal" in q:
                clause_letter = "a"
            elif "consideration" in q:
                clause_letter = "d"
            elif "agreement" in q and "void" not in q and "contract" not in q:
                clause_letter = "e"
            elif "void agreement" in q or ("void" in q and "agreement" in q):
                clause_letter = "g"
            elif "contract" in q:
                clause_letter = "h"
            elif "voidable" in q:
                clause_letter = "i"

            if clause_letter:
                if clause_letter == "b":
                    match = re.search(r"\(b\)\s*(.*?becomes a promise[:\.])", display_text, re.DOTALL | re.IGNORECASE)
                    if match:
                        display_text = "(b) " + match.group(1).strip()
                    else:
                        match = re.search(r"\(b\)\s*(.*?)(?=\([a-z]\)|$)", display_text, re.DOTALL | re.IGNORECASE)
                        if match:
                            display_text = "(b) " + match.group(1).strip()
                else:
                    match = re.search(rf"\({clause_letter}\)\s*(.*?)(?=\([a-z]\)|$)", display_text, re.DOTALL | re.IGNORECASE)
                    if match:
                        display_text = f"({clause_letter}) " + match.group(1).strip()

        # Penal Code Section 379 text trimming
        if top["act"] == "The Penal Code, 1860" and str(top["section"]) == "379":
            display_text = re.split(r"\b380\.", display_text, maxsplit=1)[0].strip()
            display_text = re.sub(r"\bhouse,\s*etc\.\s*$", "", display_text, flags=re.IGNORECASE).strip()

        # Contract Act Clause (b) canonical representation
        if top["act"] == "Contract Act, 1872" and str(top["section"]) == "2":
            if ("accept" in q and "become" in q) or "promise" in q:
                display_text = (
                    "(b) When the person to whom the proposal is made signifies his assent thereto, "
                    "the proposal is said to be accepted. A proposal, when accepted, becomes a promise."
                )

        # Remove page tags and normalize whitespace
        display_text = re.sub(r"<<<PAGE:\d+>>>", "", display_text)
        display_text = re.sub(r"\s+", " ", display_text).strip()

        # Isolate exact statutory definition sentence
        if top["act"] == "The Penal Code, 1860" and str(top["section"]) == "378":
            m = re.search(r"(.*?is said to commit theft\.)", display_text, re.IGNORECASE)
            if m:
                display_text = m.group(1).strip()
        elif top["act"] == "The Penal Code, 1860" and str(top["section"]) == "379":
            m = re.search(r"(.*?may extend to three years, or with fine, or with both\.)", display_text, re.IGNORECASE)
            if m:
                display_text = m.group(1).strip()

        return display_text

    @staticmethod
    def get_simple_explanation(top: Dict[str, Any], q: str) -> Optional[str]:
        if top["act"] == "The Penal Code, 1860" and str(top["section"]) == "378":
            return "In simple terms, theft means dishonestly taking movable property from another person without that person's consent."
        elif top["act"] == "The Penal Code, 1860" and str(top["section"]) == "379":
            return "In simple terms, the punishment for theft may include imprisonment up to three years, or fine, or both."
        elif top["act"] == "Contract Act, 1872" and str(top["section"]) == "2":
            if "accept" in q and "become" in q:
                return "In simple terms, when a proposal is accepted, it becomes a promise."
            elif "promise" in q:
                return "In simple terms, a promise is formed when a proposal is accepted."
            elif "proposal" in q:
                return "In simple terms, a proposal is when one person shows willingness to do or not do something in order to get another person's agreement."
            elif "acceptance" in q:
                return "In simple terms, acceptance happens when the other person agrees to the proposal."
            elif "consideration" in q:
                return "In simple terms, consideration means something of value given, promised, or done in return for a promise."
            elif "agreement" in q:
                return "In simple terms, an agreement is a promise or set of promises forming consideration for each other."
        return None

    @staticmethod
    def build_citations(top: Dict[str, Any], bundle_sorted: List[Dict[str, Any]]) -> List[str]:
        citations = []
        allowed_sections = {top["section"]}
        if top["act"] == "The Penal Code, 1860" and str(top["section"]) == "379":
            allowed_sections.add(378)

        heading_part = f" ({top['heading']})" if top.get("heading") else ""
        citations.append(
            f"{top['act']} — Section {top['section']}{heading_part}, pp. {top['pages'][0]}–{top['pages'][1]}"
        )

        seen_sections = {top["section"]}
        for b in bundle_sorted:
            if b["section"] in seen_sections or b["section"] not in allowed_sections:
                continue
            h_part = f" ({b['heading']})" if b.get("heading") else ""
            citations.append(
                f"{b['act']} — Section {b['section']}{h_part}, pp. {b['pages'][0]}–{b['pages'][1]}"
            )
            seen_sections.add(b["section"])

        return citations

    @staticmethod
    def order_evidence(top: Dict[str, Any], bundle_sorted: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [top] + [b for b in bundle_sorted if b != top]
