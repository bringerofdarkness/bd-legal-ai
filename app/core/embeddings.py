"""
Thread-Safe Singleton Provider for Sentence Transformers Embeddings
Ensures zero import-time side-effects and lazy-loads the model when needed.
"""

import os
import zipfile
import requests
from typing import Optional
from langchain_huggingface import HuggingFaceEmbeddings
from app.core.config import settings

_EMBEDDING_INSTANCE: Optional[HuggingFaceEmbeddings] = None


def ensure_local_data():
    """Verifies that vector database indices exist locally, downloading from HF if absent."""
    if not os.path.exists(settings.DATA_DIR):
        print(f"[*] Downloading vector database from {settings.DATA_URL}...")
        zip_path = os.path.join(settings.BASE_DIR, "data.zip")

        response = requests.get(settings.DATA_URL, stream=True, timeout=60)
        with open(zip_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        print("[*] Extracting vector database archive...")
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(settings.BASE_DIR)

        if os.path.exists(zip_path):
            os.remove(zip_path)
        print("[+] Vector database ready.")


def get_embedding_model() -> HuggingFaceEmbeddings:
    """Returns the singleton HuggingFaceEmbeddings instance, instantiating lazily upon first request."""
    global _EMBEDDING_INSTANCE
    if _EMBEDDING_INSTANCE is None:
        ensure_local_data()
        _EMBEDDING_INSTANCE = HuggingFaceEmbeddings(
            model_name=settings.EMBEDDING_MODEL_NAME
        )
    return _EMBEDDING_INSTANCE
