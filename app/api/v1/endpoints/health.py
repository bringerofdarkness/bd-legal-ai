"""
Health & System Status Endpoint
"""

from fastapi import APIRouter
from app.api.schemas import HealthResponse
from app.core.config import settings
from app.core.registry import LAW_REGISTRY

router = APIRouter()


@router.get("/health", response_model=HealthResponse, summary="System Health & Diagnostic Status")
async def health_check():
    """
    Validates backend readiness, loaded statutory catalog, and active runtime environment.
    """
    indexed_count = len(LAW_REGISTRY)
    return HealthResponse(
        status="healthy",
        version=settings.VERSION,
        laws_indexed=indexed_count,
        environment=settings.ENVIRONMENT
    )
