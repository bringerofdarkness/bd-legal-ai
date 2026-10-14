"""
Automated Statutory Knowledge Graph Extractor (GraphRAG)
Scans parsed statutory text using legal syntax patterns to automatically discover and extract:
- Cross-references ('section X', 'ধারা X')
- Definitional prerequisites ('defined in section X', 'meaning of section X')
- Punishment linkages ('punishable under section X')
- Subordinations & Exceptions ('subject to section X')
Inserts all discovered directed edges into PostgreSQL section_relationships.
"""

import os
import sys
import re
import json
import psycopg
from typing import List, Dict, Tuple, Set

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
from app.core.logging import setup_logging, get_logger

setup_logging("INFO")
logger = get_logger("ingestion.graph_extractor")

PARSED_ACTS_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "parsed_acts")

# Multi-lingual Bengali digit transliterator
BN_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")

# Targeted Legal Relationship Regex Patterns
PATTERNS = [
    # 1. Definitional / Conceptual Links
    (
        re.compile(
            r"(?:defined in|meaning of|definition of|within the meaning of)\s+section\s+(\d{1,4}[A-Z]?)",
            re.IGNORECASE,
        ),
        "REQUIRES_CONCEPT",
    ),
    # 2. Punishment / Penalty Links
    (
        re.compile(
            r"(?:punished under|punishable under|penalty provided in|punishment under)\s+section\s+(\d{1,4}[A-Z]?)",
            re.IGNORECASE,
        ),
        "PUNISHED_BY",
    ),
    # 3. Subordination / Conditions
    (
        re.compile(
            r"(?:subject to the provisions of|subject to|save as provided in)\s+section\s+(\d{1,4}[A-Z]?)",
            re.IGNORECASE,
        ),
        "SUBJECT_TO",
    ),
    # 4. General Statutory References
    (
        re.compile(
            r"(?:under section|in section|of section|section)\s+(\d{1,4}[A-Z]?)",
            re.IGNORECASE,
        ),
        "REFERENCES",
    ),
    # 5. Bengali Reference Patterns
    (
        re.compile(
            r"(?:ধারা|ধারায়|ধারার অধীন|ধারার অর্থ অনুযায়ী)\s*([০-৯]+|[0-9]+[A-Z]?)",
            re.IGNORECASE,
        ),
        "REFERENCES",
    ),
]


def normalize_sec_no(sec_raw: str) -> str:
    """Normalizes Bengali and English section numbers into standardized alphanumeric strings."""
    return sec_raw.translate(BN_DIGITS).strip().upper()


def extract_relationships_from_text(
    source_sec_id: str,
    act_id: str,
    text: str,
    existing_sections: Set[str]
) -> List[Tuple[str, str, str]]:
    """
    Extracts valid statutory relationship tuples (source, target, relation_type)
    ensuring target exists within the statutory dataset.
    """
    relationships = []
    seen = set()

    for pattern, rel_type in PATTERNS:
        matches = pattern.finditer(text)
        for m in matches:
            target_raw = m.group(1)
            target_no = normalize_sec_no(target_raw)
            target_sec_id = f"{act_id}::{target_no}"

            # Avoid self-loops and ensure the target section exists in this statute
            if target_sec_id != source_sec_id and target_sec_id in existing_sections:
                edge_key = (source_sec_id, target_sec_id, rel_type)
                if edge_key not in seen:
                    seen.add(edge_key)
                    relationships.append(edge_key)

    return relationships


def extract_and_index_all_relationships(db_url: str = settings.DATABASE_URL):
    logger.info(f"Connecting to database at: {db_url}")
    conn = psycopg.connect(db_url, autocommit=False)

    try:
        # 1. Fetch all valid section_ids from the database
        with conn.cursor() as cur:
            cur.execute("SELECT section_id FROM sections;")
            existing_sections = {row[0] for row in cur.fetchall()}

        logger.info(f"Loaded {len(existing_sections)} registered statutory sections from database.")

        total_relationships = 0
        parsed_files = [f for f in os.listdir(PARSED_ACTS_DIR) if f.endswith("_sections.json")]

        with conn.cursor() as cur:
            for fname in parsed_files:
                fpath = os.path.join(PARSED_ACTS_DIR, fname)
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)

                act_id = str(data.get("act_id", ""))
                sections = data.get("sections", [])
                act_relations = []

                for s in sections:
                    sec_no = normalize_sec_no(str(s.get("section_no", "")))
                    if not sec_no:
                        continue
                    source_sec_id = f"{act_id}::{sec_no}"
                    body = s.get("body_text", "")
                    heading = s.get("section_heading", "")
                    combined_text = f"{heading}\n{body}"

                    rels = extract_relationships_from_text(
                        source_sec_id=source_sec_id,
                        act_id=act_id,
                        text=combined_text,
                        existing_sections=existing_sections
                    )
                    act_relations.extend(rels)

                # Batch insert into database
                for src, tgt, r_type in act_relations:
                    cur.execute(
                        """
                        INSERT INTO section_relationships (source_section_id, target_section_id, relationship_type)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (source_section_id, target_section_id, relationship_type) DO NOTHING;
                        """,
                        (src, tgt, r_type)
                    )

                conn.commit()
                total_relationships += len(act_relations)
                logger.info(f"Act {act_id} ({data.get('title_en', '')}): Extracted {len(act_relations)} automated statutory links.")

        logger.info(f"=== AUTOMATED KNOWLEDGE GRAPH EXTRACTION COMPLETE: {total_relationships} total links established ===")
        return total_relationships
    finally:
        conn.close()


if __name__ == "__main__":
    extract_and_index_all_relationships()
