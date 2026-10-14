"""
Hybrid Retrieval Service (PostgreSQL + pgvector + GraphRAG)
Executes Reciprocal Rank Fusion (RRF) combining:
1. Dense Multilingual Vector Search (HNSW Cosine Similarity via pgvector)
2. Sparse Full-Text Keyword Search (PostgreSQL tsvector)
3. 1-hop GraphRAG Traversal (Relational section_relationships expansion)
Includes graceful fallback to local cache if PostgreSQL is offline.
"""

import os
import re
import json
from typing import List, Dict, Any, Optional
import psycopg
from pgvector.psycopg import register_vector

from app.core.config import settings
from app.core.embeddings import get_embedding_model
from app.core.logging import get_logger
from app.services.classifier_service import ClassifierService

logger = get_logger("app.services.retrieval")

# Optional Chroma fallback imports
try:
    from langchain_chroma import Chroma
    from rank_bm25 import BM25Okapi
    from app.core.registry import LAW_REGISTRY
except ImportError:
    Chroma = None
    BM25Okapi = None
    LAW_REGISTRY = {}

_VECTORSTORES: Dict[str, Any] = {}


def get_pg_connection():
    try:
        conn = psycopg.connect(settings.DATABASE_URL, autocommit=True, connect_timeout=3)
        register_vector(conn)
        return conn
    except Exception as e:
        logger.warning(f"PostgreSQL connection unavailable ({e}); utilizing local fallback.")
        return None


class RetrievalService:
    @classmethod
    def query_pgvector_hybrid(
        cls,
        query: str,
        top_k: int = 5,
        target_act_id: Optional[str] = None,
        target_section_no: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Executes native PostgreSQL Hybrid Search:
        Combines HNSW Cosine Vector search + tsvector Full-Text search via Reciprocal Rank Fusion (RRF).
        Enriches top results with 1-hop GraphRAG traversal links.
        """
        conn = get_pg_connection()
        if conn is None:
            return []

        try:
            embedder = get_embedding_model()
            q_emb = embedder.embed_query(query)

            # Clean query text for tsvector
            clean_q = re.sub(r"[^\w\s]", " ", query).strip()
            if not clean_q:
                clean_q = query

            act_filter_clause = "AND s.act_id = %(act_id)s" if target_act_id else ""

            sql_hybrid = f"""
            WITH exact_search AS (
                SELECT 
                    s.section_id, s.act_id, a.title_en AS act_name, s.section_no, s.heading_en, 
                    s.body_en, s.full_text_en, s.source_pdf, s.page_start, s.page_end,
                    (s.embedding_en <=> %(q_emb)s::vector) AS cosine_distance,
                    1 AS dense_rank
                FROM sections s
                JOIN acts a ON s.act_id = a.act_id
                WHERE s.section_no = %(target_sec)s {act_filter_clause}
                LIMIT 5
            ),
            dense_search AS (
                SELECT 
                    s.section_id, s.act_id, a.title_en AS act_name, s.section_no, s.heading_en, 
                    s.body_en, s.full_text_en, s.source_pdf, s.page_start, s.page_end,
                    (s.embedding_en <=> %(q_emb)s::vector) AS cosine_distance,
                    ROW_NUMBER() OVER (ORDER BY s.embedding_en <=> %(q_emb)s::vector ASC) AS dense_rank
                FROM sections s
                JOIN acts a ON s.act_id = a.act_id
                WHERE s.embedding_en IS NOT NULL {act_filter_clause}
                LIMIT 50
            ),
            sparse_search AS (
                SELECT 
                    s.section_id, s.section_no,
                    ts_rank_cd(s.search_vector_en, plainto_tsquery('english', %(q_text)s)) AS bm25_score,
                    ROW_NUMBER() OVER (ORDER BY ts_rank_cd(s.search_vector_en, plainto_tsquery('english', %(q_text)s)) DESC) AS sparse_rank
                FROM sections s
                WHERE s.search_vector_en @@ plainto_tsquery('english', %(q_text)s) {act_filter_clause}
                LIMIT 25
            ),
            combined_candidates AS (
                SELECT section_id FROM exact_search
                UNION
                SELECT section_id FROM dense_search
                UNION
                SELECT section_id FROM sparse_search
            ),
            hybrid_fused AS (
                SELECT 
                    c.section_id,
                    COALESCE(ex.act_id, d.act_id, s.act_id) AS act_id,
                    COALESCE(ex.act_name, d.act_name, a.title_en) AS act_name,
                    COALESCE(ex.section_no, d.section_no, s.section_no) AS section_no,
                    COALESCE(ex.heading_en, d.heading_en, s.heading_en) AS heading_en,
                    COALESCE(ex.body_en, d.body_en, s.body_en) AS body_en,
                    COALESCE(ex.full_text_en, d.full_text_en, s.full_text_en) AS full_text_en,
                    COALESCE(ex.source_pdf, d.source_pdf, s.source_pdf) AS source_pdf,
                    COALESCE(ex.page_start, d.page_start, s.page_start) AS page_start,
                    COALESCE(ex.page_end, d.page_end, s.page_end) AS page_end,
                    COALESCE(ex.cosine_distance, d.cosine_distance) AS cosine_distance,
                    sp.sparse_rank,
                    (
                        COALESCE(1.0 / (60.0 + d.dense_rank), 0.0) + 
                        COALESCE(1.0 / (60.0 + sp.sparse_rank), 0.0) +
                        (CASE WHEN ex.section_id IS NOT NULL THEN 5.0 ELSE 0.0 END)
                    ) AS rrf_score
                FROM combined_candidates c
                LEFT JOIN exact_search ex ON c.section_id = ex.section_id
                LEFT JOIN dense_search d ON c.section_id = d.section_id
                LEFT JOIN sparse_search sp ON c.section_id = sp.section_id
                JOIN sections s ON c.section_id = s.section_id
                JOIN acts a ON s.act_id = a.act_id
            )
            SELECT section_id, act_id, act_name, section_no, heading_en, body_en, full_text_en, source_pdf, page_start, page_end, rrf_score, cosine_distance, sparse_rank
            FROM hybrid_fused
            ORDER BY rrf_score DESC
            LIMIT %(top_k)s;
            """

            params = {
                "q_emb": q_emb,
                "q_text": clean_q,
                "act_id": target_act_id,
                "target_sec": str(target_section_no) if target_section_no else "",
                "top_k": top_k
            }

            bundle = []
            with conn.cursor() as cur:
                cur.execute(sql_hybrid, params)
                rows = cur.fetchall()

                # Semantic distance threshold: detect completely out-of-scope queries
                if rows:
                    top_dist = rows[0][11]
                    top_sparse = rows[0][12]
                    if top_dist is not None and top_dist > 0.65 and top_sparse is None and not target_section_no:
                        logger.info(f"Query rejected as out-of-scope (cosine distance {top_dist:.3f} > 0.65 with no keyword match).")
                        return []

                for row in rows:
                    sec_id = row[0]
                    act_name = row[2]
                    sec_no = row[3]
                    heading = row[4]
                    body = row[5]
                    full_text = row[6] or f"{sec_no}. {heading}\n{body}"
                    source_pdf = row[7]
                    pages = (row[8], row[9]) if row[8] is not None else None
                    score = float(row[10])

                    # 1-hop GraphRAG Expansion: Pull related section headings
                    cur.execute(
                        """
                        SELECT r.target_section_id, r.relationship_type, s.section_no, s.heading_en
                        FROM section_relationships r
                        JOIN sections s ON r.target_section_id = s.section_id
                        WHERE r.source_section_id = %s
                        LIMIT 5;
                        """,
                        (sec_id,)
                    )
                    graph_links = [
                        {"target_id": r[0], "relation": r[1], "target_sec": r[2], "target_heading": r[3]}
                        for r in cur.fetchall()
                    ]

                    bundle.append({
                        "score": score,
                        "act": act_name,
                        "section": sec_no,
                        "heading": heading,
                        "pages": pages,
                        "source_pdf": source_pdf,
                        "text": full_text,
                        "graph_relationships": graph_links
                    })

            return bundle
        except Exception as e:
            logger.error(f"Error during pgvector hybrid search: {e}", exc_info=True)
            return []
        finally:
            conn.close()

    @classmethod
    def build_evidence_bundle(
        cls,
        query: str,
        k_initial: int = settings.INITIAL_CANDIDATE_K,
        k_final: int = settings.FINAL_EVIDENCE_K
    ) -> List[Dict[str, Any]]:
        """
        Coordinates statutory evidence retrieval.
        Attempts native PostgreSQL + pgvector Hybrid Search first;
        falls back gracefully to local Chroma store if database is offline.
        """
        analysis = ClassifierService.analyze_query(query)
        law_hint = analysis.get("law_hint")
        target_section = analysis.get("section_no")
        target_act_id = None
        if law_hint:
            if law_hint in LAW_REGISTRY:
                target_act_id = LAW_REGISTRY[law_hint].act_id
            else:
                target_act_id = str(law_hint)

        # 1. Attempt PostgreSQL Hybrid Retrieval (Bilingual + Full 10 Acts)
        pg_bundle = cls.query_pgvector_hybrid(
            query=query,
            top_k=k_final,
            target_act_id=target_act_id,
            target_section_no=target_section,
        )
        if pg_bundle:
            return pg_bundle

        # 2. Local Fallback for offline development / legacy benchmarks
        logger.info("Executing local fallback (Chroma / Parsed JSON).")
        return cls._local_fallback(query, analysis, k_final)

    @classmethod
    def _local_fallback(
        cls,
        query: str,
        analysis: Dict[str, Any],
        k_final: int
    ) -> List[Dict[str, Any]]:
        """
        Local statutory fallback for offline development and CI environments.
        Uses local Chroma vectorstore if available; otherwise falls back to
        parsed statutory JSON files in data/parsed_acts/.
        """
        active_law_id = analysis.get("law_hint") or ClassifierService.choose_active_law(query)
        if active_law_id is None:
            if analysis.get("section_no"):
                active_law_id = "11"
            else:
                return []

        config = LAW_REGISTRY.get(active_law_id)
        if not config:
            for c in LAW_REGISTRY.values():
                if c.act_id == str(active_law_id):
                    config = c
                    break

        if not config:
            return []

        # 1. Try local Chroma vector store if present on disk
        if Chroma is not None and os.path.exists(config.persist_dir):
            try:
                emb_model = get_embedding_model()
                vs = Chroma(
                    collection_name=config.collection_name,
                    persist_directory=config.persist_dir,
                    embedding_function=emb_model,
                )
                results = vs.similarity_search_with_score(query, k=k_final)
                bundle = []
                for doc, score in results:
                    md = doc.metadata
                    bundle.append({
                        "score": float(score),
                        "act": md.get("act_name"),
                        "section": md.get("section_number"),
                        "heading": md.get("section_heading"),
                        "pages": (md.get("page_start"), md.get("page_end")),
                        "source_pdf": md.get("source_pdf"),
                        "text": doc.page_content,
                        "graph_relationships": []
                    })
                if bundle:
                    return bundle
            except Exception as e:
                logger.warning(f"Local Chroma fallback encountered an error: {e}")

        # 2. Resilient Offline JSON fallback from data/parsed_acts/ (tracked in git)
        parsed_acts_dir = os.path.abspath(os.path.join(settings.DATA_DIR, "parsed_acts"))
        if not os.path.exists(parsed_acts_dir):
            return []

        target_sec = analysis.get("section_no")
        q_lower = query.lower()

        # Find matching act JSON file (e.g. 11_penal_code_1860_sections.json)
        json_file = None
        for f in os.listdir(parsed_acts_dir):
            if f.startswith(f"{config.act_id}_") and f.endswith(".json"):
                json_file = os.path.join(parsed_acts_dir, f)
                break

        if not json_file or not os.path.exists(json_file):
            return []

        try:
            with open(json_file, "r", encoding="utf-8") as f:
                act_data = json.load(f)

            sections = act_data.get("sections", [])
            matches = []

            # Exact section match priority
            if target_sec:
                for s in sections:
                    if str(s.get("section_no")) == str(target_sec):
                        matches.append(s)
                        break

            # Keyword / Semantic fallback in JSON
            if not matches:
                keywords = [w for w in re.findall(r"\w+", q_lower) if len(w) > 3]
                scored_sections = []
                for s in sections:
                    full_text = (s.get("full_text") or "").lower()
                    heading = (s.get("section_heading") or "").lower()
                    match_count = sum(1 for kw in keywords if kw in full_text or kw in heading)
                    if match_count > 0:
                        scored_sections.append((match_count, s))
                scored_sections.sort(key=lambda x: x[0], reverse=True)
                matches = [s for _, s in scored_sections[:k_final]]

            bundle = []
            for s in matches[:k_final]:
                sec_no = s.get("section_no")
                heading = s.get("section_heading")
                full_text = s.get("full_text") or f"{sec_no}. {heading}\n{s.get('body_text')}"
                bundle.append({
                    "score": 1.0,
                    "act": config.display_name,
                    "section": sec_no,
                    "heading": heading,
                    "pages": None,
                    "source_pdf": None,
                    "text": full_text,
                    "graph_relationships": []
                })
            return bundle
        except Exception as e:
            logger.error(f"Error reading offline parsed act JSON: {e}")
            return []