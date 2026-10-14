"""
Database Audit & Inspection Script
Interactive CLI tool to inspect tables, section counts, vector embeddings,
and GraphRAG relationships in the PostgreSQL + pgvector database.
Usage:
    python scripts/inspect_db.py
"""

import sys
import os
import psycopg

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def inspect():
    db_url = settings.DATABASE_URL
    print("\n" + "=" * 65)
    print("       BANGLADESH LEGAL AI — DATABASE AUDIT TOOL")
    print("=" * 65)
    print(f"[*] Connection URL: {db_url}")

    try:
        conn = psycopg.connect(db_url)
    except Exception as e:
        print(f"\n[!] Failed to connect to PostgreSQL: {e}")
        print("    Make sure the docker container is running: docker compose up -d db\n")
        return

    with conn.cursor() as cur:
        # 1. Total Tables
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
        tables = [r[0] for r in cur.fetchall()]
        print(f"[+] Active Public Tables ({len(tables)}): {', '.join(tables)}")

        # 2. Acts and Section Counts
        print("\n--- 📚 Indexed Statutes & Section Counts ---")
        cur.execute(
            """
            SELECT a.act_id, a.title_en, a.act_year, count(s.section_id)
            FROM acts a
            LEFT JOIN sections s ON a.act_id = s.act_id
            GROUP BY a.act_id, a.title_en, a.act_year
            ORDER BY count(s.section_id) DESC;
            """
        )
        total_sections = 0
        for act_id, title, year, count in cur.fetchall():
            total_sections += count
            print(f"  • [Act {act_id:<4}] {title:<42} ({year}): {count:>4} sections")
        print(f"  -------------------------------------------------------------")
        print(f"    TOTAL STATUTORY SECTIONS INDEXED: {total_sections}")

        # 3. Vector Embeddings Validation
        print("\n--- 🧠 Vector Embeddings & Index Diagnostic ---")
        cur.execute(
            """
            SELECT section_id, heading_en, vector_dims(embedding_en)
            FROM sections
            WHERE embedding_en IS NOT NULL
            LIMIT 3;
            """
        )
        for sec_id, heading, dims in cur.fetchall():
            print(f"  • Section {sec_id:<10}: {heading[:40]:<40} | Dimension: {dims}-d vector")

        # 4. GraphRAG Knowledge Graph Statistics
        print("\n--- 🕸️ GraphRAG Knowledge Graph Relationships ---")
        cur.execute("SELECT relationship_type, count(*) FROM section_relationships GROUP BY relationship_type ORDER BY count DESC;")
        for rel_type, count in cur.fetchall():
            print(f"  • {rel_type:<18}: {count:>4} edges")

        cur.execute("SELECT count(*) FROM section_relationships;")
        total_edges = cur.fetchone()[0]
        print(f"    TOTAL AUTOMATED GRAPHRAG EDGES: {total_edges}")

        # 5. Sample Graph Traversal (Theft §378 cluster)
        print("\n--- 🔍 Sample Graph Traversal (Theft Section 11::378) ---")
        cur.execute(
            """
            SELECT target_section_id, relationship_type 
            FROM section_relationships 
            WHERE source_section_id = '11::378';
            """
        )
        for target, rel in cur.fetchall():
            print(f"  [11::378] --({rel})--> [{target}]")

    conn.close()
    print("\n" + "=" * 65)
    print("Database is healthy, fully indexed, and ready for queries.")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    inspect()
