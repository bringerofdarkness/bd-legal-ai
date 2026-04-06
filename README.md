# Bangladesh Legal AI Assistant

RAG-based legal assistant for Bangladesh law with citation-grounded answers using hybrid retrieval (Chroma + BM25).

## Live Demo
https://huggingface.co/spaces/bringerofdarkness/bd-legal-ai

## Features
- legal question answering
- law-aware retrieval
- citation-grounded responses
- hybrid retrieval (vector + keyword)
- deployed with Docker
- remote DB loading from Hugging Face Dataset

## Demo Note
This is a public demo deployment. The system downloads its knowledge base at runtime and currently supports selected laws only.  
This tool is for educational purposes and does not provide legal advice.

## Current Law Coverage
- The Penal Code, 1860
- The Contract Act, 1872

## Tech Stack
- Python
- Streamlit
- Chroma
- BM25
- sentence-transformers
- LangChain
- Docker
- Hugging Face Spaces / Datasets

## System Architecture
User → Streamlit UI → retrieval pipeline → Chroma + BM25 → answer + citations

## Repository Structure
- `app/streamlit_app.py` — UI
- `app/rag_backend.py` — retrieval and answer generation
- `app/law_registry.py` — law config
- `ingestion/` — ingestion notebooks
- `docs/` — project notes and evaluation artifacts

## Deployment Notes
This deployment downloads the vector database from a Hugging Face Dataset at startup.

## Limitations
- limited law coverage
- demo/prototype system
- not legal advice

## Local Run

```bash
docker build -t bd-legal-ai .
docker run -p 8501:8501 bd-legal-ai