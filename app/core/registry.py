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
    source_label: str
    description: str = ""
    retrieval_k: int = 6
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

            # Common statutory abbreviations and domain keywords
            if "penal code" in title_en.lower():
                aliases.extend(["penal code", "theft", "murder", "criminal law", "দণ্ডবিধি", "খুন", "হত্যা", "চুরি", "ডাকাতি", "ছিনতাই", "প্রতারণা", "চাঁদাবাজি", "মার্ডার", "extortion", "cheating", "fraud", "mischief", "ধর্ষণ", "rape", "defamation", "মানহানি"])
            elif "contract" in title_en.lower():
                aliases.extend(["contract", "contract act", "agreement", "proposal", "acceptance", "consideration", "চুক্তি", "চুক্তি আইন", "প্রতিদান", "সম্মতি", "প্রস্তাব", "চুক্তিভঙ্গ", "breach of contract"])
            elif "criminal procedure" in title_en.lower():
                aliases.extend(["crpc", "criminal procedure", "bail", "arrest", "ফৌজদারী", "এজাহার", "এফআইআর", "নালিশ", "মামলা দায়ের", "জিডি", "fir", "complaint", "police station", "investigation"])
            elif "civil procedure" in title_en.lower():
                aliases.extend(["cpc", "civil procedure", "deed", "appeal", "দেওয়ানী", "দেওয়ানী কার্যবিধি", "আরজি", "ডিক্রি", "রিভিশন"])
            elif "evidence" in title_en.lower():
                aliases.extend(["evidence act", "witness", "confession", "সাক্ষ্য আইন", "সাক্ষী", "স্বীকারোক্তি", "প্রমাণের দায়ভার", "burden of proof"])
            elif "cyber" in title_en.lower():
                aliases.extend(["cyber security", "hacking", "digital security", "সাইবার নিরাপত্তা", "হ্যাকিং", "সাইবার অপরাধ", "অবৈধ অনুপ্রবেশ", "কম্পিউটার"])
            elif "nari o shishu" in title_en.lower():
                aliases.extend(["nari shishu", "women and children", "নারী ও শিশু", "নারী নির্যাতন", "শিশু নির্যাতন", "যৌতুক", "যৌতুকের জন্য", "dowry"])
            elif "negotiable" in title_en.lower():
                aliases.extend(["cheque bounce", "cheque dishonor", "cheque dishonour", "section 138", "চেক", "ডিজঅনার", "বাউন্স", "চেক ডিজঅনার", "চেক বাউন্স", "হস্তান্তরযোগ্য দলিল", "negotiable instruments", "dishonour", "dishonor"])
            elif "specific relief" in title_en.lower():
                aliases.extend(["specific relief", "injunction", "recovery of possession", "সুনির্দিষ্ট", "সুনির্দিষ্ট প্রতিকার", "দখল উদ্ধার", "দলিল বাতিল", "নিষেধাজ্ঞা"])
            elif "muslim family" in title_en.lower():
                aliases.extend(["muslim family", "talaq", "divorce", "dower", "দেনমোহর", "তালাক", "মুসলিম পারিবারিক", "পারিবারিক আইন", "তালাকের নোটিশ", "বহুবিবাহ", "দ্বিতীয় বিয়ে", "polygamy", "maintenance", "খোরপোশ"])

            registry[slug] = LawConfig(
                law_id=slug,
                act_id=act_id,
                display_name=title_en,
                title_bn=title_bn,
                year=year,
                collection_name=f"bd_{slug}_v1",
                source_label=f"{title_en} (Official Bangladesh Code)",
                description=item.get("description", ""),
                retrieval_k=settings.DEFAULT_RETRIEVAL_K,
                aliases=list(set(aliases)),
            )
            # Also register by act_id as key for fast lookup
            registry[act_id] = registry[slug]
            # Register secondary legacy bdlaws web URL IDs
            if act_id == "41":
                registry["63"] = registry[slug]
            elif act_id == "312":
                registry["305"] = registry[slug]
            elif act_id == "356":
                registry["802"] = registry[slug]
            elif act_id == "1282":
                registry["1457"] = registry[slug]
            elif act_id == "27":
                registry["24"] = registry[slug]

    except Exception as e:
        logger.error(f"Failed to load statutory manifest registry: {e}", exc_info=True)

    return registry


LAW_REGISTRY: Dict[str, LawConfig] = _load_manifest_registry()
