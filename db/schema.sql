-- ==============================================================================
-- Bangladesh Legal AI — PostgreSQL + pgvector Master Production Schema
-- Polyglot Persistence: Relational Statutory Metadata + Dense Vectors + Full-Text
-- ==============================================================================

-- 1. Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. Acts Table (Statutes)
CREATE TABLE IF NOT EXISTS acts (
    act_id VARCHAR(32) PRIMARY KEY, -- e.g. '11', '26', '1282'
    slug VARCHAR(128) UNIQUE NOT NULL, -- e.g. 'penal_code_1860'
    title_en TEXT NOT NULL,
    title_bn TEXT,
    act_year INT NOT NULL,
    act_no VARCHAR(64),
    source_url TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Chapters Table
CREATE TABLE IF NOT EXISTS chapters (
    chapter_id VARCHAR(64) PRIMARY KEY, -- e.g. '11::chap_XVII'
    act_id VARCHAR(32) NOT NULL REFERENCES acts(act_id) ON DELETE CASCADE,
    chapter_no VARCHAR(32), -- e.g. 'Chapter XVII'
    title_en TEXT,
    title_bn TEXT,
    sort_order INT DEFAULT 0
);

-- 4. Sections Table (Core Legal Units with Vectors and Full-Text Search)
CREATE TABLE IF NOT EXISTS sections (
    section_id VARCHAR(64) PRIMARY KEY, -- e.g. '11::378'
    act_id VARCHAR(32) NOT NULL REFERENCES acts(act_id) ON DELETE CASCADE,
    chapter_id VARCHAR(64) REFERENCES chapters(chapter_id) ON DELETE SET NULL,
    section_no VARCHAR(32) NOT NULL, -- e.g. '378', '304A', '171E'
    heading_en TEXT,
    heading_bn TEXT,
    body_en TEXT NOT NULL,
    body_bn TEXT,
    full_text_en TEXT NOT NULL,
    full_text_bn TEXT,
    
    -- Procedural Metadata (from CrPC Schedule II)
    is_bailable BOOLEAN,
    is_cognizable BOOLEAN,
    is_compoundable BOOLEAN,
    triable_by TEXT,
    max_penalty_en TEXT,
    
    -- Pagination & Provenance
    page_start INT,
    page_end INT,
    source_pdf TEXT,

    -- BGE-M3 Dense Multilingual Vector Embeddings (1024 Dimensions)
    embedding_en vector(1024),
    embedding_bn vector(1024),

    -- Sparse Keyword Search Vectors (PostgreSQL tsvector)
    search_vector_en tsvector GENERATED ALWAYS AS (
        to_tsvector('english', coalesce(section_no, '') || ' ' || coalesce(heading_en, '') || ' ' || coalesce(body_en, ''))
    ) STORED,
    search_vector_bn tsvector,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. Clauses Table (Sub-sections, Illustrations, Explanations)
CREATE TABLE IF NOT EXISTS clauses (
    clause_id VARCHAR(96) PRIMARY KEY, -- e.g. '11::378::c1'
    section_id VARCHAR(64) NOT NULL REFERENCES sections(section_id) ON DELETE CASCADE,
    clause_label VARCHAR(32), -- e.g. '(1)', '(a)', 'Explanation 1'
    content_en TEXT NOT NULL,
    content_bn TEXT
);

-- 6. Lightweight Knowledge Graph Junction (GraphRAG)
CREATE TABLE IF NOT EXISTS section_relationships (
    source_section_id VARCHAR(64) NOT NULL REFERENCES sections(section_id) ON DELETE CASCADE,
    target_section_id VARCHAR(64) NOT NULL REFERENCES sections(section_id) ON DELETE CASCADE,
    relationship_type VARCHAR(64) NOT NULL, -- 'DEFINES', 'PUNISHED_BY', 'AGGRAVATED_FORM', 'PROCEDURE_LINK', 'REQUIRES_CONCEPT'
    PRIMARY KEY (source_section_id, target_section_id, relationship_type)
);

-- 7. Search History Table (Optional Auth & Guest Session Support)
CREATE TABLE IF NOT EXISTS search_history (
    history_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID, -- Nullable for unauthenticated guest citizens
    session_id VARCHAR(128), -- Anonymous client session identifier
    query_text TEXT NOT NULL,
    answer_text TEXT NOT NULL,
    citations JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ==============================================================================
-- INDEXING: Fast Dense Vector Search & Sparse Full-Text Search
-- ==============================================================================

-- HNSW Vector Index on BGE-M3 1024-d embeddings (Cosine Similarity)
CREATE INDEX IF NOT EXISTS idx_sections_embedding_en_hnsw 
ON sections USING hnsw (embedding_en vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- GIN Full-Text Search Indexes
CREATE INDEX IF NOT EXISTS idx_sections_search_vector_en 
ON sections USING gin(search_vector_en);

-- Relational Filtering Indexes
CREATE INDEX IF NOT EXISTS idx_sections_act_id ON sections(act_id);
CREATE INDEX IF NOT EXISTS idx_sections_section_no ON sections(section_no);
CREATE INDEX IF NOT EXISTS idx_sections_is_bailable ON sections(is_bailable);
CREATE INDEX IF NOT EXISTS idx_sections_is_cognizable ON sections(is_cognizable);
CREATE INDEX IF NOT EXISTS idx_section_relationships_source ON section_relationships(source_section_id);
CREATE INDEX IF NOT EXISTS idx_section_relationships_target ON section_relationships(target_section_id);
