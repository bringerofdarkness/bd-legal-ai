"""
Legal RAG Pipeline Orchestrator (Facade Pattern)
Coordinates classifier, retrieval, reranker, and generator services in a clean, decoupled workflow.
"""

from typing import Dict, Any, Optional
from app.services.classifier_service import ClassifierService
from app.services.retrieval_service import RetrievalService
from app.services.generator_service import GeneratorService


def build_refusal_response(reason: str) -> Dict[str, Any]:
    return {
        "status": "refused",
        "answer_text": "",
        "citations": [],
        "evidence": [],
        "refusal_reason": reason,
    }


class LegalRAGOrchestrator:
    @classmethod
    def answer_query(cls, query: str, debug: bool = False) -> Dict[str, Any]:
        query_type = ClassifierService.classify_query(query)
        q = query.strip().lower()
        analysis = ClassifierService.analyze_query(q)

        is_definition_query = query_type == "definition"
        is_punishment_query = query_type == "punishment"

        # 1. Out-of-scope Cyber Filter
        if ClassifierService.is_cyber_query(q):
            return build_refusal_response(
                "Cyber-related offences are outside the scope of the currently indexed laws."
            )

        # 2. Scope Verification
        if not ClassifierService.is_supported_scope(q, analysis):
            return build_refusal_response(
                "This version currently supports theft-related Penal Code questions "
                "and Contract Act Section 2 concepts such as proposal, acceptance, "
                "promise, promisor, promisee, agreement, contract, and consideration."
            )

        # 3. Active Law Resolution
        active_law_id = analysis.get("law_hint") or ClassifierService.choose_active_law(query)
        if active_law_id is None:
            return build_refusal_response(
                "Query is outside the scope of the currently indexed laws."
            )

        # 4. Hybrid Evidence Retrieval
        bundle = RetrievalService.build_evidence_bundle(query, k_initial=15, k_final=5)
        if not bundle:
            return build_refusal_response("No relevant legal sections found.")

        # 5. Top Bundle Item Selection
        bundle_sorted = sorted(bundle, key=lambda x: x["score"])
        top = GeneratorService.select_top_bundle_item(
            bundle_sorted,
            q,
            is_definition_query,
            is_punishment_query
        )

        # 6. Statutory Text Formatting
        display_text = GeneratorService.format_display_text(top, q, is_definition_query)
        simple_explanation = GeneratorService.get_simple_explanation(top, q)
        label = GeneratorService.get_answer_label(q)

        # 7. Answer Construction
        if simple_explanation:
            answer_text = (
                f"{simple_explanation}\n\n"
                f"Legal text: According to {top['act']} Section {top['section']}, "
                f"the relevant {label} is:\n\n{display_text}"
            )
        else:
            answer_text = (
                f"According to {top['act']} Section {top['section']}, "
                f"the relevant {label} is:\n\n{display_text}"
            )

        # 8. Citations & Evidence Ordering
        citations = GeneratorService.build_citations(top, bundle_sorted)
        ordered_evidence = GeneratorService.order_evidence(top, bundle_sorted)

        if debug:
            print(f"[DEBUG] Query: {query} | Type: {query_type} | Section: {top['section']}")

        return {
            "status": "ok",
            "answer_text": answer_text,
            "citations": citations,
            "evidence": ordered_evidence,
            "refusal_reason": None,
        }
