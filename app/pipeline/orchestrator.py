"""
Legal RAG Pipeline Orchestrator (Facade Pattern)
Coordinates AI query routing, PostgreSQL hybrid retrieval, NLI entailment guardrails,
and deterministic ground-truth fallback across all 10 Bangladesh enactments.
"""

from typing import Dict, Any, List, Optional
from app.services.classifier_service import ClassifierService
from app.services.retrieval_service import RetrievalService
from app.services.generator_service import GeneratorService
from app.services.nli_validator_service import NLIValidatorService
from app.core.logging import get_logger

logger = get_logger("app.pipeline.orchestrator")


def build_refusal_response(reason: str) -> Dict[str, Any]:
    return {
        "status": "refused",
        "answer_text": "",
        "citations": [],
        "evidence": [],
        "refusal_reason": reason,
        "verification_verdict": "REFUSED",
        "entailment_score": 0.0,
    }


class LegalRAGOrchestrator:
    @classmethod
    def answer_query(cls, query: str, debug: bool = False) -> Dict[str, Any]:
        """
        End-to-End Zero-Hallucination Legal Question-Answering Pipeline:
        1. AI Intent Classification & Section Extraction
        2. Native PostgreSQL Hybrid Vector (HNSW) + Full-Text (tsvector) Search
        3. 1-hop GraphRAG Legal Relationship Expansion
        4. Cross-Encoder NLI Entailment Scoring (DeBERTa-v3)
        5. Deterministic Ground-Truth Fallback if unentailed
        """
        clean_q = query.strip()
        if len(clean_q) < 2:
            return build_refusal_response("Query is too short.")

        # 1. Analyze query intent and extract explicit section references
        analysis = ClassifierService.analyze_query(clean_q)
        intent = analysis["intent"]
        explicit_section = analysis.get("section_no")

        logger.info(
            f"Processing legal query: '{clean_q}' | Intent: {intent} | "
            f"Section Mention: {explicit_section} | Law Hint: {analysis.get('law_hint')}"
        )

        # 2. Hybrid Evidence Retrieval (Dense HNSW + Sparse tsvector + GraphRAG)
        bundle = RetrievalService.build_evidence_bundle(clean_q, k_initial=15, k_final=5)
        if not bundle:
            logger.warning(f"No relevant statutory evidence retrieved for query: '{clean_q}'")
            return build_refusal_response(
                "No directly relevant statutory provisions found in the indexed Bangladesh laws."
            )

        # 3. Top Provision Selection
        top = GeneratorService.select_top_bundle_item(
            bundle,
            clean_q,
            is_definition_query=(intent == "definition"),
            is_punishment_query=(intent == "punishment"),
            target_section_no=explicit_section,
        )

        # 4. Extract Statutory Ground Truth
        statutory_text = GeneratorService.format_display_text(
            top, clean_q, is_definition_query=(intent == "definition")
        )
        label = GeneratorService.get_answer_label(clean_q)
        act_name = top.get("act", "Bangladesh Law")
        sec_no = top.get("section", "")

        # 5. Candidate Synthesis for Civic Accessibility
        candidate_explanation = GeneratorService.get_simple_explanation(top, clean_q)

        # 6. Sprint 3 Guardrail: DeBERTa-v3 NLI Entailment Verification
        nli_result = NLIValidatorService.validate_claim(
            premise=statutory_text,
            hypothesis=candidate_explanation or ""
        )

        logger.info(
            f"NLI Guardrail Result for Section {sec_no}: Verdict={nli_result.verdict} | "
            f"Entailment={nli_result.entailment_score:.3f} | Contradiction={nli_result.contradiction_score:.3f}"
        )

        # 7. Answer Construction with Deterministic Ground-Truth Fallback
        if nli_result.is_entailed and candidate_explanation:
            # Fully Verified: Explanation is mathematically entailed by statutory ground truth
            answer_text = (
                f"{candidate_explanation}\n\n"
                f"**Statutory {label.title()} ({act_name}, Section {sec_no}):**\n\n"
                f"{statutory_text}"
            )
            verdict = "VERIFIED"
        else:
            # Deterministic Fallback Activated: Serve official statute directly to eliminate hallucination
            logger.warning(
                f"Entailment score ({nli_result.entailment_score}) below threshold or contradicted. "
                f"Triggering deterministic fallback to official statutory ground truth."
            )
            answer_text = (
                f"According to {act_name}, Section {sec_no}, the relevant {label} provides:\n\n"
                f"{statutory_text}"
            )
            verdict = "GROUND_TRUTH_FALLBACK"

        # 8. Citations & Supporting Evidence Ordering
        citations = GeneratorService.build_citations(top, bundle)
        ordered_evidence = GeneratorService.order_evidence(top, bundle)

        if debug:
            logger.debug(f"Query: {clean_q} | Verdict: {verdict} | Top Section: {sec_no}")

        return {
            "status": "ok",
            "answer_text": answer_text,
            "citations": citations,
            "evidence": ordered_evidence,
            "refusal_reason": None,
            "verification_verdict": verdict,
            "entailment_score": nli_result.entailment_score,
        }

    @classmethod
    def build_evidence_bundle(cls, query: str, k_final: int = 5) -> List[Dict[str, Any]]:
        return RetrievalService.build_evidence_bundle(query, k_initial=15, k_final=k_final)


# Singleton instance for dependency injection
legal_rag_orchestrator = LegalRAGOrchestrator()
