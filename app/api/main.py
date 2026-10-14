"""
FastAPI Server for Bangladesh Legal AI Assistant
Provides high-performance, asynchronous REST API endpoints for statutory Q&A and retrieval.
"""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List

from app.api.schemas import (
    QueryRequest,
    QueryResponse,
    SearchRequest,
    EvidenceItem,
    HealthResponse
)
from app.api.dependencies import User, get_optional_current_user
from app.rag_backend import answer_query, build_evidence_bundle
from app.law_registry import LAW_REGISTRY

app = FastAPI(
    title="Bangladesh Legal AI API",
    version="2.0.0",
    description=(
        "Precision-first, citation-grounded statutory legal assistant for Bangladesh Law. "
        "Supports bilingual inquiries, intent classification, and verifiable statutory evidence."
    ),
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for web, mobile, and desktop clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["General"])
async def root():
    return {
        "message": "Welcome to Bangladesh Legal AI API",
        "docs": "/docs",
        "health": "/health",
        "version": "2.0.0"
    }


@app.get("/health", response_model=HealthResponse, tags=["General"])
async def health_check():
    indexed_count = len(LAW_REGISTRY)
    return HealthResponse(
        status="healthy",
        version="2.0.0",
        laws_indexed=indexed_count,
        environment="production"
    )


@app.post("/v1/query", response_model=QueryResponse, tags=["Legal Assistant"])
async def process_legal_query(
    request: QueryRequest,
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """
    Main statutory question-answering endpoint.
    Retrieves relevant laws, selects the most pertinent section, formats citations,
    and returns a verified answer with full evidence.
    """
    try:
        raw_resp = answer_query(request.query)

        # Convert raw dictionary into verified Pydantic QueryResponse
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while analyzing the legal query: {str(e)}"
        )


@app.post("/v1/search", response_model=List[EvidenceItem], tags=["Statute Retrieval"])
async def direct_statute_search(
    request: SearchRequest,
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """
    Direct statutory search endpoint.
    Fetches raw section matches from the hybrid vector/keyword store without synthesis.
    """
    try:
        bundle = build_evidence_bundle(request.query, k_final=request.top_k)
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute statutory search: {str(e)}"
        )
