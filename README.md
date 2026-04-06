# Bangladesh Legal AI Assistant

RAG-based legal assistant for Bangladesh law with citation-grounded answers using hybrid retrieval (Chroma + BM25).
Built with hybrid retrieval (Chroma + BM25), Streamlit, Docker, and Hugging Face Spaces/Datasets.

## Live Demo
[Hugging Face Space](https://huggingface.co/spaces/bringerofdarkness/bd-legal-ai)

## Screenshots

### App Interface
![UI](assets/home.png)

### Answer with Citations
![Answer](assets/questionAns.png)

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
This public deployment downloads the vector database from a Hugging Face Dataset at startup.

## Limitations
- currently supports only selected laws
- still a demo / portfolio prototype
- not legal advice

## Roadmap
- FastAPI backend for production architecture
- Improved answer formatting and UX
- Additional law coverage
- Evaluation and benchmarking improvements

## Author

Shahrul Zakaria  
https://github.com/bringerofdarkness

## Local Run
```bash
docker build -t bd-legal-ai .
docker run -p 8501:8501 bd-legal-ai

## Author

Shahrul Zakaria  
https://github.com/bringerofdarkness