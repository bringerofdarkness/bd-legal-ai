"""
PostgreSQL + pgvector Statutory Indexer
Batch embeds and indexes structured Bangladesh statutes from data/parsed_acts/
into PostgreSQL with Dense Vector (HNSW) and Sparse Full-Text (tsvector) representations.
"""

import os
import sys
import json
import argparse
from typing import List, Dict, Any
import psycopg
from pgvector.psycopg import register_vector

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
from app.core.embeddings import get_embedding_model
from app.core.logging import setup_logging, get_logger

setup_logging("INFO")
logger = get_logger("ingestion.indexer")

MANIFEST_PATH = os.path.join(os.path.dirname(__file__), "laws_manifest.json")
PARSED_ACTS_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "parsed_acts")


# Curated foundational statutory relationships for GraphRAG
FOUNDATIONAL_RELATIONSHIPS = [
    # Penal Code Theft cluster
    ("11::378", "11::379", "PUNISHED_BY"),
    ("11::378", "11::380", "AGGRAVATED_FORM"),
    ("11::378", "11::381", "AGGRAVATED_FORM"),
    ("11::378", "11::382", "AGGRAVATED_FORM"),
    ("11::378", "11::22", "REQUIRES_CONCEPT"), # Moveable property
    # Murder & Homicide cluster
    ("11::299", "11::300", "DEFINES"),
    ("11::300", "11::302", "PUNISHED_BY"),
    ("11::300", "11::304", "AGGRAVATED_FORM"),
    # Cheating & Fraud cluster
    ("11::415", "11::417", "PUNISHED_BY"),
    ("11::415", "11::420", "AGGRAVATED_FORM"),
    # Rape & Sexual Offenses cluster
    ("11::375", "11::376", "PUNISHED_BY"),
    # Extortion cluster
    ("11::383", "11::384", "PUNISHED_BY"),
    ("11::383", "11::385", "AGGRAVATED_FORM"),
    # Contract Act cluster
    ("26::2", "26::10", "REQUIRES_CONCEPT"), # What agreements are contracts
    ("26::10", "26::25", "REQUIRES_CONCEPT"), # Agreement without consideration void
]


def load_manifest() -> List[Dict[str, Any]]:
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_db_connection(db_url: str):
    conn = psycopg.connect(db_url, autocommit=False)
    register_vector(conn)
    return conn


def index_act_file(conn, act_meta: Dict[str, Any], json_path: str, embedder, batch_size: int = 32):
    act_id = str(act_meta["act_id"])
    slug = act_meta["slug"]

    if not os.path.exists(json_path):
        logger.warning(f"Parsed JSON not found for Act {act_id} at {json_path}")
        return 0

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    sections = data.get("sections", [])
    if not sections:
        logger.warning(f"No sections found in {json_path}")
        return 0

    logger.info(f"Indexing Act {act_id} ({act_meta['title_en']}): {len(sections)} sections...")

    with conn.cursor() as cur:
        # 1. Upsert Act record
        cur.execute(
            """
            INSERT INTO acts (act_id, slug, title_en, title_bn, act_year, source_url)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (act_id) DO UPDATE SET
                title_en = EXCLUDED.title_en,
                title_bn = EXCLUDED.title_bn,
                act_year = EXCLUDED.act_year,
                source_url = EXCLUDED.source_url;
            """,
            (
                act_id,
                slug,
                act_meta.get("title_en", ""),
                act_meta.get("title_bn"),
                act_meta.get("year", 1860),
                act_meta.get("source_url")
            )
        )

        # 2. Batch embed and insert sections
        total_inserted = 0
        for i in range(0, len(sections), batch_size):
            batch = sections[i : i + batch_size]
            texts_to_embed = []
            for s in batch:
                # Semantic chunk combining act, section number, heading and body
                text = f"{act_meta['title_en']} Section {s.get('section_no', '')} {s.get('section_heading', '')}\n{s.get('body_text', '')}"
                texts_to_embed.append(text[:2000])

            embeddings = embedder.embed_documents(texts_to_embed)

            for s, emb in zip(batch, embeddings):
                sec_no = str(s.get("section_no", "")).strip()
                if not sec_no:
                    continue
                section_id = f"{act_id}::{sec_no}"
                heading = s.get("section_heading", "")
                body = s.get("body_text", "")
                full_text = s.get("full_text") or f"{sec_no}. {heading}\n{body}"

                cur.execute(
                    """
                    INSERT INTO sections (
                        section_id, act_id, section_no, heading_en, body_en, full_text_en, embedding_en
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (section_id) DO UPDATE SET
                        heading_en = EXCLUDED.heading_en,
                        body_en = EXCLUDED.body_en,
                        full_text_en = EXCLUDED.full_text_en,
                        embedding_en = EXCLUDED.embedding_en,
                        updated_at = CURRENT_TIMESTAMP;
                    """,
                    (
                        section_id,
                        act_id,
                        sec_no,
                        heading,
                        body,
                        full_text,
                        emb
                    )
                )

                # Insert clauses if available
                for c_idx, cl in enumerate(s.get("clauses", [])):
                    c_id = f"{section_id}::c{c_idx+1}"
                    cur.execute(
                        """
                        INSERT INTO clauses (clause_id, section_id, clause_label, content_en)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (clause_id) DO NOTHING;
                        """,
                        (c_id, section_id, cl.get("clause_label", ""), cl.get("text", ""))
                    )

                total_inserted += 1

        conn.commit()
        logger.info(f"Successfully indexed {total_inserted} sections for Act {act_id}.")
        return total_inserted


def index_knowledge_graph_relationships(conn):
    """Populates foundational GraphRAG section relationships."""
    logger.info("Indexing foundational GraphRAG section relationships...")
    inserted_count = 0
    with conn.cursor() as cur:
        for source, target, rel_type in FOUNDATIONAL_RELATIONSHIPS:
            try:
                cur.execute(
                    """
                    INSERT INTO section_relationships (source_section_id, target_section_id, relationship_type)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (source_section_id, target_section_id, relationship_type) DO NOTHING;
                    """,
                    (source, target, rel_type)
                )
                inserted_count += 1
            except Exception as e:
                logger.debug(f"Relationship skipped: {source} -> {target} ({e})")
        conn.commit()
    logger.info(f"Graph relationships registered: {inserted_count} links.")


def run_full_indexing(db_url: str = settings.DATABASE_URL, target_act_id: str = None):
    manifest = load_manifest()
    if target_act_id:
        manifest = [a for a in manifest if str(a["act_id"]) == str(target_act_id)]
        if not manifest:
            logger.error(f"Act ID {target_act_id} not found in manifest.")
            return

    logger.info(f"Connecting to PostgreSQL pgvector at: {db_url}")
    conn = get_db_connection(db_url)

    logger.info("Loading embedding model...")
    embedder = get_embedding_model()

    total_all_sections = 0
    try:
        for act in manifest:
            act_id = str(act["act_id"])
            slug = act["slug"]
            json_file = f"{act_id}_{slug}_sections.json"
            json_path = os.path.join(PARSED_ACTS_DIR, json_file)

            count = index_act_file(conn, act, json_path, embedder)
            total_all_sections += count

        index_knowledge_graph_relationships(conn)
        logger.info(f"=== FULL INDEXING COMPLETE: {total_all_sections} sections indexed in PostgreSQL + pgvector ===")
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Index parsed Bangladesh statutes into PostgreSQL pgvector")
    parser.add_argument("--act-id", type=str, default=None, help="Specific act ID to index (e.g. 11)")
    parser.add_argument("--db-url", type=str, default=settings.DATABASE_URL, help="PostgreSQL connection URL")
    args = parser.parse_args()

    run_full_indexing(db_url=args.db_url, target_act_id=args.act_id)
