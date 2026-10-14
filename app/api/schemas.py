"""
Pydantic Schemas for Bangladesh Legal AI API
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Any, Tuple


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=1000, description="Legal question or incident description")
    language: Optional[str] = Field("auto", description="Preferred response language ('bn', 'en', or 'auto')")


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=1000, description="Search query")
    act_filter: Optional[str] = Field(None, description="Optional Act ID filter (e.g. 'penal_code')")
    top_k: int = Field(5, ge=1, le=20, description="Number of results to retrieve")


class CitationItem(BaseModel):
    citation_text: str = Field(..., description="Formatted statute citation (Act, Section, Pages)")


class EvidenceItem(BaseModel):
    act: str = Field(..., description="Act name")
    section: Any = Field(..., description="Section number")
    heading: Optional[str] = Field(None, description="Section heading")
    text: str = Field(..., description="Raw statutory text")
    score: Optional[float] = Field(None, description="Relevance similarity score")
    pages: Optional[Tuple[Optional[int], Optional[int]]] = Field(None, description="Start and end page tuple")
    source_pdf: Optional[str] = Field(None, description="Source PDF name")


class QueryResponse(BaseModel):
    status: str = Field(..., description="'ok' or 'refused'")
    answer_text: str = Field(..., description="Verified plain-language explanation and statutory text")
    citations: List[str] = Field(default_factory=list, description="Array of verifiable legal citations")
    evidence: List[EvidenceItem] = Field(default_factory=list, description="Retrieved statutory provisions")
    refusal_reason: Optional[str] = Field(None, description="Reason if query was out-of-scope or refused")
    verification_verdict: Optional[str] = Field("VERIFIED", description="NLI verification verdict ('VERIFIED', 'GROUND_TRUTH_FALLBACK', 'REFUSED')")
    entailment_score: Optional[float] = Field(None, description="DeBERTa-v3 NLI entailment probability [0.0 - 1.0]")


class HealthResponse(BaseModel):
    status: str = "healthy"
    version: str = "2.0.0"
    laws_indexed: int
    environment: str = "production"
