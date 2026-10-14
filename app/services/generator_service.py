import os
import re
import json
from typing import List, Dict, Any, Optional

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("app.services.generator")

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None


class GeneratorService:
    _genai_client: Optional[Any] = None

    @classmethod
    def get_llm_client(cls) -> Optional[Any]:
        if cls._genai_client is None and genai is not None and settings.GEMINI_API_KEY:
            try:
                cls._genai_client = genai.Client(api_key=settings.GEMINI_API_KEY)
            except Exception as e:
                logger.error(f"Failed to initialize Google GenAI Client: {e}")
        return cls._genai_client
    @staticmethod
    def select_top_bundle_item(
        bundle_sorted: List[Dict[str, Any]],
        q: str,
        is_definition_query: bool = False,
        is_punishment_query: bool = False,
        target_section_no: Optional[str] = None
    ) -> Dict[str, Any]:
        """Selects the best statutory provision matching the user's intent and explicit section numbers."""
        if not bundle_sorted:
            return {}

        # 1. If user explicitly specified a section number (e.g. 'section 302'), prioritize that section
        if target_section_no:
            for b in bundle_sorted:
                if str(b.get("section", "")).upper() == target_section_no.upper():
                    return b

        # 2. If intent is punishment vs definition, check for penal or definitional relationship links
        top = bundle_sorted[0]
        if is_punishment_query:
            for b in bundle_sorted:
                heading = (b.get("heading") or "").lower()
                text = (b.get("text") or "").lower()
                if "punishment" in heading or "penalty" in heading or "punished with" in text:
                    return b
        elif is_definition_query:
            for b in bundle_sorted:
                heading = (b.get("heading") or "").lower()
                text = (b.get("text") or "").lower()
                if "is said to" in text or "means" in text or "defined" in heading:
                    return b

        return top

    @staticmethod
    def get_answer_label(q: str) -> str:
        """Determines the legal classification label for the statutory excerpt."""
        q_lower = q.lower()
        if any(kw in q_lower for kw in ["punish", "punishment", "penalty", "sentence", "fine", "imprisonment", "শাস্তি"]):
            return "punishment provision"
        elif any(kw in q_lower for kw in ["define", "definition", "meaning", "what is", "what constitutes", "সংজ্ঞা"]):
            return "statutory definition"
        elif any(kw in q_lower for kw in ["bail", "bailable", "cognizable", "arrest", "জামিন"]):
            return "procedural rule"
        return "statutory provision"

    @classmethod
    def format_display_text(cls, top: Dict[str, Any], q: str, is_definition_query: bool = False) -> str:
        """Cleans and standardizes raw statutory text for user display."""
        raw_text = top.get("text") or ""

        # Normalize whitespace and strip internal page tags
        cleaned = re.sub(r"<<<PAGE:\d+>>>", "", raw_text)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        # Extract primary definition sentence if available
        if is_definition_query and "is said to" in cleaned:
            match = re.search(r"([^.]*?is said to[^.]*\.)", cleaned, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return cleaned

    @staticmethod
    def get_simple_explanation(top: Dict[str, Any], q: str) -> Optional[str]:
        """
        Synthesizes a plain-language summary of the provision for civic accessibility.
        This summary is later subjected to NLI entailment verification against the statutory ground truth.
        """
        heading = (top.get("heading") or "").strip()
        body = (top.get("text") or "").strip()
        act = top.get("act", "Bangladesh Law")
        sec = top.get("section", "")

        if not heading and not body:
            return None

        # Clean heading
        clean_heading = re.sub(r"^[A-Z0-9\.\-\s]+", "", heading).strip() or heading

        # If heading clearly describes the offence or rule
        return (
            f"Under {act}, Section {sec} establishes the legal standard for '{clean_heading}'. "
            f"It governs the statutory definitions, rights, liabilities, or penalties applicable under Bangladesh law."
        )

    @classmethod
    def synthesize_answer_with_llm(
        cls,
        top: Dict[str, Any],
        query: str,
        intent: str
    ) -> Dict[str, Any]:
        """
        Synthesizes a legally constrained, fluent answer using Gemini Flash with temperature=0.0.
        Returns:
            {
                "direct_answer": str,
                "supporting_quote": str,
                "explanation_en": str,
                "is_llm_generated": bool
            }
        """
        fallback_exp = cls.get_simple_explanation(top, query)
        client = cls.get_llm_client()
        if client is None or not top:
            return {
                "direct_answer": fallback_exp or "",
                "supporting_quote": top.get("heading") or "",
                "explanation_en": fallback_exp or "",
                "is_llm_generated": False,
            }

        act_name = top.get("act", "Bangladesh Law")
        sec_no = top.get("section", "")
        heading = top.get("heading", "")
        clean_text = cls.format_display_text(top, query)

        prompt = f"""You are the Official Bangladesh Legal AI Assistant.
Analyze the provided statutory provision and answer the user's legal question accurately.

<verified_legal_context>
Act: {act_name}
Section: {sec_no}
Heading: {heading}
Text:
{clean_text}
</verified_legal_context>

User Query: "{query}"
Query Intent: {intent}

Strict Synthesis Rules:
1. Grounding: Answer ONLY from facts and legal provisions directly stated in <verified_legal_context>. Do NOT extrapolate, speculate, or reference unmentioned sections.
2. Language:
   - If the user query is in Bengali, provide 'direct_answer' in natural, formal Bengali (বাংলা).
   - If the user query is in English, provide 'direct_answer' in clear, professional English.
3. Supporting Quote: In 'supporting_quote', copy an exact verbatim English sentence directly from the Text above that supports the answer.
4. NLI Verification Statement: In 'explanation_en', write a concise 1-sentence English factual statement directly asserting the rule, liability, or penalty without conversational preamble or statutory section numbers (e.g. "Whoever commits theft shall be punished with imprisonment for a term which may extend to three years, or with fine, or with both.").

Return a JSON object with this exact structure:
{{
  "direct_answer": "...",
  "supporting_quote": "...",
  "explanation_en": "..."
}}
"""

        try:
            model_name = settings.GEMINI_MODEL
            resp = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.0
                )
            )
            raw_text = resp.text.strip()
            data = json.loads(raw_text)

            direct_ans = data.get("direct_answer", "").strip()
            sup_quote = data.get("supporting_quote", "").strip()
            exp_en = data.get("explanation_en", "").strip()

            return {
                "direct_answer": direct_ans or fallback_exp or "",
                "supporting_quote": sup_quote,
                "explanation_en": exp_en or fallback_exp or "",
                "is_llm_generated": True,
            }
        except Exception as e:
            logger.warning(f"Gemini LLM generation failed or unavailable ({e}); utilizing fallback template.")
            return {
                "direct_answer": fallback_exp or "",
                "supporting_quote": top.get("heading") or "",
                "explanation_en": fallback_exp or "",
                "is_llm_generated": False,
            }

    @staticmethod
    def build_citations(top: Dict[str, Any], bundle_sorted: List[Dict[str, Any]]) -> List[str]:
        """Constructs formal statutory citations with Act title, Section, and official Gazette pagination."""
        citations = []
        if not top:
            return citations

        heading_part = f" ({top['heading'][:60]}...)" if top.get("heading") else ""
        pages_part = f", pp. {top['pages'][0]}–{top['pages'][1]}" if top.get("pages") and top['pages'][0] is not None else ""
        citations.append(f"{top.get('act', 'Act')} — Section {top.get('section', '')}{heading_part}{pages_part}")

        seen_sections = {str(top.get("section", ""))}
        for b in bundle_sorted[:3]:
            sec = str(b.get("section", ""))
            if sec in seen_sections:
                continue
            h_part = f" ({b['heading'][:60]}...)" if b.get("heading") else ""
            p_part = f", pp. {b['pages'][0]}–{b['pages'][1]}" if b.get("pages") and b['pages'][0] is not None else ""
            citations.append(f"{b.get('act', 'Act')} — Section {sec}{h_part}{p_part}")
            seen_sections.add(sec)

        return citations

    @staticmethod
    def order_evidence(top: Dict[str, Any], bundle_sorted: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Ensures the primary supporting provision is placed at index 0 followed by auxiliary evidence."""
        if not bundle_sorted:
            return [top] if top else []
        return [top] + [b for b in bundle_sorted if b.get("section") != top.get("section")]
