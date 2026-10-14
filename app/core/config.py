"""
Application Configuration and Settings
Centralized environment variables, directory paths, and model parameters using Pydantic.
"""

import os
from typing import List, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load .env file automatically
load_dotenv()


class Settings(BaseModel):
    # Project Identity
    PROJECT_NAME: str = "Bangladesh Legal AI"
    VERSION: str = "2.0.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Server Configuration
    API_HOST: str = os.getenv("API_HOST", "127.0.0.1")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    CORS_ORIGINS: List[str] = ["*"]

    # Database Configuration (PostgreSQL + pgvector)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:5433/bd_legal_db")

    # Storage Paths
    BASE_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    DATA_DIR: str = os.path.join(BASE_DIR, "data")
    DOCS_DIR: str = os.path.join(BASE_DIR, "docs")
    
    # Remote Vector DB Download URL
    DATA_URL: str = "https://huggingface.co/datasets/bringerofdarkness/bd-legal-ai-db/resolve/main/data.zip"

    # Embedding Model Parameters
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

    # LLM Synthesis (Google Gemini Flash)
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    SYNTHESIS_TEMPERATURE: float = 0.0

    # Security & Authentication (JWT Bearer & Guest Mode)
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "dev-insecure-secret-key-32-chars-long")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

    # Retrieval Defaults
    DEFAULT_RETRIEVAL_K: int = 6
    INITIAL_CANDIDATE_K: int = 15
    FINAL_EVIDENCE_K: int = 5
    SIMILARITY_THRESHOLD: float = 0.35


# Global Settings Instance
settings = Settings()
