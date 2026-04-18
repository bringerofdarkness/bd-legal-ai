# Target Architecture — Bangladesh Legal AI Assistant

## 1) Current system

The current system is a citation-grounded legal RAG assistant for Bangladesh law.

### Current main components
- `app/streamlit_app.py` → demo/UI layer
- `app/rag_backend.py` → retrieval, routing, answer generation
- `app/law_registry.py` → law metadata / source registry
- `run_eval.py` → evaluation runner
- `docs/eval_queries.json` → benchmark dataset
- `docs/eval_results.json` → saved evaluation output
- `ingestion/` → ingestion and indexing pipeline

### Current behavior
- User asks a legal question in Streamlit
- Backend identifies legal intent / route
- Relevant law source is selected
- Hybrid retrieval is used to fetch relevant sections
- Answer is generated with citations
- Evaluation runs separately through `run_eval.py`
- GitHub Actions fails if evaluation quality drops

### Current limitations
- App is mainly demo-first, not API-first
- Retrieval, routing, and answer building are tightly coupled
- Evaluation is mostly aggregate, not typed/diagnostic
- No dedicated cache layer
- No structured logging / observability layer
- No background job system for long report generation
- No export pipeline for legal research reports
- Streamlit is the main interface, so system boundaries are less clear


## 2) Target system

The target is a production-style AI legal research system with measurable quality, modular retrieval, and clear runtime boundaries.

### Target goals
- Preserve citation-grounded answers
- Keep evaluation as a first-class engineering component
- Separate orchestration from retrieval
- Support both UI and API usage
- Add observability and reproducibility
- Support report generation as an extended workflow
- Make the project look like strong ML/AI engineering, not only a demo

### Non-goals for now
- No autonomous agent system
- No uncontrolled browsing across the web
- No fully general legal reasoning over all Bangladesh law at once
- No feature additions that break evaluation discipline


## 3) Core runtime components

### A. Interface layer
Responsible for user-facing access.

- `Streamlit UI`
  - interactive demo
  - query input
  - answer display
  - citation display

- `FastAPI API`
  - programmatic access
  - request/response schema
  - health endpoint
  - future integration point for external clients

### B. Orchestration layer
Responsible for controlling the pipeline steps.

Proposed responsibilities:
- classify query type
- decide whether query is in-scope
- select legal source(s)
- call retrieval layer
- call answer builder
- apply fallback/refusal logic
- route long-form report generation to background job

This should be lightweight orchestration, not an autonomous agent.

### C. Retrieval layer
Responsible for finding the best legal text evidence.

Proposed responsibilities:
- law-aware retrieval
- hybrid search (Chroma + BM25)
- section ranking
- section deduplication
- support for query-type-sensitive retrieval
- return structured retrieved evidence

### D. Answer generation layer
Responsible for building grounded answers.

Proposed responsibilities:
- synthesize answer from retrieved sections
- preserve section references
- distinguish definition vs punishment vs concept queries
- avoid unsupported claims
- return answer plus citations

### E. Citation layer
Responsible for formatting and validating citations.

Proposed responsibilities:
- normalize citation format
- ensure cited sections actually exist in retrieved evidence
- make citations readable in both UI and API

### F. Cache layer
Redis-backed cache for repeated requests.

Use cases:
- repeated user queries
- repeated retrieval results for same normalized query
- optionally cached report jobs

### G. Background worker layer
Responsible for long-running tasks.

Use cases:
- legal research report generation
- report export jobs
- future batch evaluation/report creation

### H. Logging and observability layer
Responsible for runtime visibility.

Track:
- query text
- normalized query
- predicted query category
- selected law source
- retrieved section ids
- answer success/failure
- latency
- cache hit/miss
- evaluation metrics


## 4) Request lifecycle

## Standard answer request
1. User submits question from Streamlit or FastAPI
2. Query is normalized
3. Query is classified
4. System decides if question is in-scope
5. Relevant law source(s) are selected
6. Retrieval layer fetches candidate sections
7. Ranking/filtering chooses best evidence
8. Answer builder generates grounded response
9. Citation formatter prepares final citations
10. Response is returned to UI/API
11. Request metadata is logged

## Cached request path
1. User submits question
2. Query is normalized
3. Cache is checked
4. If hit, cached response is returned
5. If miss, standard retrieval/generation path runs
6. Result is stored in cache

## Long legal report request
1. User requests report generation
2. Request is validated
3. Background job is created
4. Worker runs retrieval + synthesis workflow
5. Report is assembled
6. Export artifact is produced
7. Job status/result is returned to user


## 5) Evaluation lifecycle

Evaluation should remain a first-class system, not a side utility.

### Planned evaluation design
- typed evaluation dataset
- category-aware scoring
- per-law metrics
- error breakdown
- regression detection in CI
- saved reports for comparison over time

### Proposed typed fields in eval dataset
Each eval sample should eventually contain:
- `question`
- `expected_answer`
- `category`
- `law`
- `expected_sections`
- `difficulty`
- `notes` (optional)

### Evaluation flow
1. Load evaluation dataset
2. Run each query through the real backend
3. Compare output against expected behavior
4. Compute overall score
5. Compute per-category score
6. Compute per-law score
7. Save results
8. Fail CI if metrics regress below threshold

### Why evaluation stays first
This project should show:
- measurable retrieval quality
- measurable routing quality
- reproducible improvement
- engineering discipline


## 6) Future extensions

These are planned only after the core architecture becomes modular and measurable.

### Near-term
- typed evaluation dataset
- refactor `rag_backend.py` into explicit stages
- FastAPI layer
- structured logging

### Mid-term
- Redis caching
- background report job
- export to PDF/DOCX
- richer evaluation reports

### Long-term
- multi-law expansion
- better ranking strategies
- query reformulation
- retrieval diagnostics dashboard


## 7) Success criteria

This architecture is successful if:
- answers remain citation-grounded
- evaluation becomes more diagnostic, not just pass/fail
- backend logic becomes modular and readable
- API and UI can share the same backend pipeline
- long-form report generation does not block normal queries
- new features do not weaken measurable quality