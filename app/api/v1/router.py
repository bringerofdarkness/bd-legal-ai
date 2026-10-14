"""
API v1 Router Aggregator
Combines all v1 endpoint sub-routers under standardized URL prefixes and tags.
"""

from fastapi import APIRouter
from app.api.v1.endpoints import health, query, search, statutes, auth

api_v1_router = APIRouter()

api_v1_router.include_router(auth.router, prefix="/auth", tags=["Authentication & Sessions"])
api_v1_router.include_router(health.router, tags=["System Health"])
api_v1_router.include_router(query.router, tags=["Legal Assistant"])
api_v1_router.include_router(search.router, tags=["Statutory Retrieval"])
api_v1_router.include_router(statutes.router, tags=["Statutes & Catalog"])
