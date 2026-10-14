"""
Statutory Catalog & Manifest Endpoint
"""

from fastapi import APIRouter
from typing import List, Dict, Any
from app.core.registry import LAW_REGISTRY

router = APIRouter()


@router.get("/statutes", summary="List Cataloged Bangladesh Acts")
async def list_registered_statutes() -> List[Dict[str, Any]]:
    """
    Returns metadata on all Bangladesh statutory acts currently indexed and supported.
    """
    results = []
    for law_key, law in LAW_REGISTRY.items():
        results.append({
            "key": law_key,
            "display_name": law.display_name,
            "source_label": law.source_label,
            "collection_name": law.collection_name,
            "aliases": law.aliases,
            "has_bilingual_support": True
        })
    return results
