"""
Direct Statutory Retrieval Endpoint
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from app.api.schemas import SearchRequest, EvidenceItem
from app.api.dependencies import User, get_optional_current_user
from app.pipeline.orchestrator import legal_rag_orchestrator
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/search", response_model=List[EvidenceItem], summary="Direct Statutory Search")
async def direct_statute_search(
    request: SearchRequest,
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """
    Direct statutory search endpoint.
    Fetches raw section matches from the hybrid vector/keyword store without synthesis.
    """
    try:
        logger.info(f"Direct search query (Top K: {request.top_k}): {request.query[:80]}...")
        bundle = legal_rag_orchestrator.build_evidence_bundle(request.query, k_final=request.top_k)
        results = []
        for doc in bundle:
            results.append(
                EvidenceItem(
                    act=doc.get("act", ""),
                    section=doc.get("section", ""),
                    heading=doc.get("heading"),
                    text=doc.get("text", ""),
                    score=doc.get("score"),
                    pages=doc.get("pages"),
                    source_pdf=doc.get("source_pdf")
                )
            )
        return results
    except Exception as e:
        logger.error(f"Error during statutory search: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute statutory search: {str(e)}"
        )
