"""
FastAPI Server for Bangladesh Legal AI Platform
Provides production-grade REST API endpoints for statutory Q&A, semantic retrieval, and legal diagnostics.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.api.v1.router import api_v1_router
from app.api.v1.endpoints.health import health_check
from app.api.v1.endpoints.query import process_legal_query
from app.api.v1.endpoints.search import direct_statute_search

# Initialize structured logging
setup_logging(settings.LOG_LEVEL)
logger = get_logger("app.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle event handler for application startup and shutdown."""
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION} [{settings.ENVIRONMENT}]")
    yield
    logger.info(f"Shutting down {settings.PROJECT_NAME}")


app = FastAPI(
    title=f"{settings.PROJECT_NAME} API",
    version=settings.VERSION,
    description=(
        "Production-grade, zero-hallucination statutory legal assistant for Bangladesh Law. "
        "Provides bilingual Q&A, statutory evidence extraction, and deterministic legal validation."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Versioned v1 Router
app.include_router(api_v1_router, prefix="/v1")

# Root endpoints & backward compatibility forwarders
@app.get("/", include_in_schema=False)
async def root_redirect():
    """Redirects root visitors directly to the Swagger UI documentation."""
    return RedirectResponse(url="/docs")


# Direct root health endpoint
app.add_api_route("/health", health_check, methods=["GET"], tags=["System Health"], include_in_schema=True)
