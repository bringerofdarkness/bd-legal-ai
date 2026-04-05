---
title: BD Legal AI
emoji: ⚖️
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 8501
---
# AI-Powered Bangladesh Legal Assistant

## Project Goal
Build a precision-first legal AI assistant for Bangladesh law using official law PDFs.

The system:
- answers legal questions with grounded citations
- refuses when evidence is weak or out of scope
- supports natural user phrasing
- is designed for scalable multi-law expansion

## Current Supported Laws
- The Penal Code, 1860
- The Contract Act, 1872

## Current Supported Query Types
- Definitions
- Punishment queries
- Legal meaning queries
- Natural language incident queries

## Architecture Files
- `app.py` - Streamlit UI
- `rag_backend.py` - retrieval, routing, answer generation
- `law_registry.py` - law configuration and registry
- `run_eval.py` - evaluation runner
- `eval_queries.json` - evaluation dataset
- `eval_results.json` - saved evaluation results


---

## Then run these 3 commands

```bat
git add README.md
git commit -m "fix readme"
git push hf main