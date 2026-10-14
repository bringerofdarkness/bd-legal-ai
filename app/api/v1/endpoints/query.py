"""
Statutory Q&A Endpoint
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional
from app.api.schemas import QueryRequest, QueryResponse, EvidenceItem
from app.api.dependencies import User, get_optional_current_user
from app.pipeline.orchestrator import legal_rag_orchestrator
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/query", response_model=QueryResponse, summary="Statutory Question Answering")
async def process_legal_query(
    request: QueryRequest,
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """
    Main statutory legal question-answering endpoint.
    Performs language normalization, intent classification, hybrid retrieval,
    lexical reranking, statutory selection, and zero-hallucination citation formatting.
    """
    try:
        logger.info(f"Processing legal query (User: {current_user.id if current_user else 'Guest'}): {request.query[:80]}...")
        raw_resp = legal_rag_orchestrator.answer_query(request.query)

        evidence_items = []
        for e in raw_resp.get("evidence", []):
            evidence_items.append(
                EvidenceItem(
                    act=e.get("act", ""),
                    section=e.get("section", ""),
                    heading=e.get("heading"),
                    text=e.get("text", ""),
                    score=e.get("score"),
                    pages=e.get("pages"),
                    source_pdf=e.get("source_pdf")
                )
            )

        return QueryResponse(
            status=raw_resp.get("status", "ok"),
            answer_text=raw_resp.get("answer_text", ""),
            citations=raw_resp.get("citations", []),
            evidence=evidence_items,
            refusal_reason=raw_resp.get("refusal_reason")
        )
    except Exception as e:
        logger.error(f"Error processing legal query: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while analyzing the legal query: {str(e)}"
        )
