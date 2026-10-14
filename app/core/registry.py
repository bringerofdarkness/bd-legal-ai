"""
Statutory Law Registry and Configuration
Dynamically loads and registers all active Bangladesh statutes from ingestion/laws_manifest.json
and provides unified metadata, aliases, and statutory configurations.
"""

import os
import json
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("app.core.registry")

MANIFEST_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "ingestion", "laws_manifest.json")
)


@dataclass
class LawConfig:
    law_id: str
    act_id: str
    display_name: str
    title_bn: Optional[str]
    year: int
    collection_name: str
    persist_dir: str
    source_label: str
    description: str = ""
    retrieval_k: int = 6
    use_bm25: bool = False
    bm25_corpus_path: Optional[str] = None
    aliases: List[str] = field(default_factory=list)


def _load_manifest_registry() -> Dict[str, LawConfig]:
    registry: Dict[str, LawConfig] = {}
    if not os.path.exists(MANIFEST_PATH):
        logger.warning(f"Laws manifest not found at {MANIFEST_PATH}; using empty registry.")
        return registry

    try:
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            manifest_items = json.load(f)

        for item in manifest_items:
            slug = item["slug"]
            act_id = str(item["act_id"])
            title_en = item.get("title_en", slug)
            title_bn = item.get("title_bn")
            year = item.get("year", 0)

            # Generate natural aliases for search routing
            aliases = [
                title_en.lower(),
                slug.replace("_", " ").lower(),
                f"act {act_id}",
                f"{year}",
            ]
            if title_bn:
                aliases.append(title_bn)

            # Common statutory abbreviations
            if "penal code" in title_en.lower():
                aliases.extend(["penal code", "theft", "murder", "criminal law", "দণ্ডবিধি"])
            elif "contract" in title_en.lower():
                aliases.extend(["contract", "contract act", "agreement", "proposal", "acceptance", "consideration", "চুক্তি", "চুক্তি আইন"])
            elif "criminal procedure" in title_en.lower():
                aliases.extend(["crpc", "criminal procedure", "bail", "arrest", "ফৌজদারী"])
            elif "civil procedure" in title_en.lower():
                aliases.extend(["cpc", "civil procedure", "deed", "appeal", "দেওয়ানী"])
            elif "evidence" in title_en.lower():
                aliases.extend(["evidence act", "witness", "confession", "সাক্ষ্য আইন"])
            elif "cyber" in title_en.lower():
                aliases.extend(["cyber security", "hacking", "digital security", "সাইবার নিরাপত্তা"])
            elif "nari o shishu" in title_en.lower():
                aliases.extend(["nari shishu", "women and children", "নারী ও শিশু"])
            elif "negotiable" in title_en.lower():
                aliases.extend(["cheque bounce", "cheque dishonor", "section 138", "চেক"])
            elif "specific relief" in title_en.lower():
                aliases.extend(["specific relief", "injunction", "recovery of possession", "সুনির্দিষ্ট"])
            elif "muslim family" in title_en.lower():
                aliases.extend(["muslim family", "talaq", "divorce", "dower", "দেনমোহর", "তালাক"])

            registry[slug] = LawConfig(
                law_id=slug,
                act_id=act_id,
                display_name=title_en,
                title_bn=title_bn,
                year=year,
                collection_name=f"bd_{slug}_v1",
                persist_dir=os.path.join(settings.DATA_DIR, f"chroma_{slug}_v1"),
                source_label=f"{title_en} (Official Bangladesh Code)",
                description=item.get("description", ""),
                retrieval_k=settings.DEFAULT_RETRIEVAL_K,
                aliases=list(set(aliases)),
            )
            # Also register by act_id as key for fast lookup
            registry[act_id] = registry[slug]

    except Exception as e:
        logger.error(f"Failed to load statutory manifest registry: {e}", exc_info=True)

    return registry


LAW_REGISTRY: Dict[str, LawConfig] = _load_manifest_registry()
