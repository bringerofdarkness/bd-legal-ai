"""
Hybrid Retrieval Service
Coordinates Chroma vector search, BM25 Okapi lexical search, and evidence bundle assembly.
"""

import os
import re
from typing import List, Dict, Any, Optional
from langchain_chroma import Chroma
from rank_bm25 import BM25Okapi

from app.core.registry import LAW_REGISTRY, LawConfig
from app.core.embeddings import get_embedding_model
from app.core.config import settings
from app.services.classifier_service import ClassifierService
from app.services.reranker_service import RerankerService

_VECTORSTORES: Dict[str, Optional[Chroma]] = {}
_BM25_PENAL: Optional[BM25Okapi] = None


def tokenize_for_bm25(text: str) -> List[str]:
    return re.findall(r"\w+", text.lower())


def get_vectorstore(law_id: str) -> Optional[Chroma]:
    global _VECTORSTORES
    if law_id not in _VECTORSTORES:
        config = LAW_REGISTRY.get(law_id)
        if not config or not os.path.exists(config.persist_dir):
            _VECTORSTORES[law_id] = None
        else:
            emb_model = get_embedding_model()
            _VECTORSTORES[law_id] = Chroma(
                collection_name=config.collection_name,
                persist_directory=config.persist_dir,
                embedding_function=emb_model,
            )
    return _VECTORSTORES.get(law_id)


def get_bm25_penal() -> Optional[BM25Okapi]:
    global _BM25_PENAL
    if _BM25_PENAL is None:
        vs = get_vectorstore("penal_code")
        if vs is not None:
            all_docs = vs.get().get("documents", [])
            corpus = [tokenize_for_bm25(d) for d in all_docs if d and d.strip()]
            if corpus:
                _BM25_PENAL = BM25Okapi(corpus)
    return _BM25_PENAL


class RetrievalService:
    @classmethod
    def build_evidence_bundle(
        cls,
        query: str,
        k_initial: int = settings.INITIAL_CANDIDATE_K,
        k_final: int = settings.FINAL_EVIDENCE_K
    ) -> List[Dict[str, Any]]:
        q = query.lower()
        analysis = ClassifierService.analyze_query(query)

        active_law_id = analysis["law_hint"] or ClassifierService.choose_active_law(query)
        if active_law_id is None:
            return []

        active_db = get_vectorstore(active_law_id)
        active_config = LAW_REGISTRY.get(active_law_id)
        if active_db is None or active_config is None:
            return []

        retrieval_query = RerankerService.normalize_query(query, analysis)

        # Classifier-aware adjustment
        if analysis["intent"] == "definition":
            retrieval_query += " definition meaning"
        elif analysis["intent"] == "punishment":
            retrieval_query += " punishment penalty imprisonment"

        # Penal Code: Hard-routed filter for theft definition
        if (
            active_law_id == "penal_code"
            and analysis["concept_hint"] == "theft"
            and analysis["intent"] == "definition"
        ):
            vector_results = active_db.similarity_search_with_score(
                "theft definition dishonestly moveable property section 378",
                k=10,
                filter={"section_number": 378}
            )
            bundle = []
            for doc, score in vector_results[:k_final]:
                md = doc.metadata
                bundle.append({
                    "score": float(score),
                    "act": md.get("act_name"),
                    "section": md.get("section_number"),
                    "heading": md.get("section_heading"),
                    "pages": (md.get("page_start"), md.get("page_end")),
                    "source_pdf": md.get("source_pdf"),
                    "text": doc.page_content,
                })
            return bundle

        # Penal Code: Hard-routed filter for theft punishment
        if (
            active_law_id == "penal_code"
            and analysis["concept_hint"] == "theft"
            and analysis["intent"] == "punishment"
        ):
            vector_results = active_db.similarity_search_with_score(
                "punishment for theft imprisonment fine section 379",
                k=10,
                filter={"section_number": 379}
            )
            bundle = []
            for doc, score in vector_results[:k_final]:
                md = doc.metadata
                bundle.append({
                    "score": float(score),
                    "act": md.get("act_name"),
                    "section": md.get("section_number"),
                    "heading": md.get("section_heading"),
                    "pages": (md.get("page_start"), md.get("page_end")),
                    "source_pdf": md.get("source_pdf"),
                    "text": doc.page_content,
                })
            return bundle

        if active_law_id == "penal_code" and analysis["intent"] == "provision":
            theft_phrases = [
                "theft", "stole", "stolen", "steal", "stealing",
                "someone stole", "took my property", "lost my",
                "my watch", "my phone", "my mobile", "my bag", "my property",
                "he took", "someone took", "took my"
            ]
            legal_actions = ["sue", "file case", "legal action", "how can i"]
            objects = ["watch", "phone", "mobile", "bag", "property", "stolen", "lost"]

            if any(p in q for p in theft_phrases) or (any(k in q for k in legal_actions) and any(o in q for o in objects)):
                retrieval_query = "theft dishonestly taking moveable property section 378"

        vector_results = active_db.similarity_search_with_score(
            retrieval_query,
            k=active_config.retrieval_k
        )

        if analysis["law_hint"] == "contract_act" and analysis["concept_hint"] == "section_2_definition":
            vector_results = active_db.similarity_search_with_score(
                "section 2 definitions contract act",
                k=10,
                filter={"section_number": 2}
            )

        bm25_scores = None
        top_bm25_idx = []
        bm25_penal = get_bm25_penal()

        if active_config.use_bm25 and active_law_id == "penal_code" and bm25_penal is not None:
            tokenized_query = tokenize_for_bm25(query)
            bm25_scores = bm25_penal.get_scores(tokenized_query)
            top_bm25_idx = sorted(
                range(len(bm25_scores)),
                key=lambda i: bm25_scores[i],
                reverse=True
            )[:k_initial]

        combined = []
        for i, (doc, v_score) in enumerate(vector_results):
            bm25_bonus = 0.0
            if bm25_scores is not None and i < len(top_bm25_idx):
                bm25_bonus = bm25_scores[top_bm25_idx[i]] * 0.05

            text = doc.page_content.lower()
            lexical_bonus = 0.0

            if "theft" in q and "theft" in text:
                lexical_bonus += 0.5

            if analysis["law_hint"] == "contract_act" and doc.metadata.get("section_number") == 2:
                if "proposal" in q:
                    lexical_bonus += 2.0
                if "acceptance" in q:
                    lexical_bonus += 2.0
                if "consideration" in q:
                    lexical_bonus += 2.0
                if "agreement" in q:
                    lexical_bonus += 1.5
                if "contract" in q:
                    lexical_bonus += 1.5

            if "murder" in q and "murder" in text:
                lexical_bonus += 0.5
            if "punish" in q and "punish" in text:
                lexical_bonus += 0.3

            combined.append((doc, v_score - bm25_bonus - lexical_bonus))

        boosted = RerankerService.apply_intent_boost(query, combined)
        reranked = RerankerService.rerank_definition(query, boosted)
        top = reranked[:k_final]

        bundle = []
        for doc, score in top:
            md = doc.metadata
            bundle.append({
                "score": float(score),
                "act": md.get("act_name"),
                "section": md.get("section_number"),
                "heading": md.get("section_heading"),
                "pages": (md.get("page_start"), md.get("page_end")),
                "source_pdf": md.get("source_pdf"),
                "text": doc.page_content,
            })

        return bundle