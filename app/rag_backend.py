"""
Backward-Compatible Facade Wrapper for Bangladesh Legal AI
Delegates pipeline requests to app.pipeline.orchestrator and app.services.retrieval_service.
"""

from typing import Dict, Any, List
from app.pipeline.orchestrator import LegalRAGOrchestrator
from app.services.retrieval_service import RetrievalService


def answer_query(query: str, debug: bool = False) -> Dict[str, Any]:
    """Primary entrypoint for statutory legal inquiries."""
    return LegalRAGOrchestrator.answer_query(query, debug=debug)


def build_evidence_bundle(
    query: str,
    k_initial: int = 15,
    k_final: int = 5
) -> List[Dict[str, Any]]:
    """Retrieval entrypoint for statutory candidate sections."""
    return RetrievalService.build_evidence_bundle(query, k_initial=k_initial, k_final=k_final)
