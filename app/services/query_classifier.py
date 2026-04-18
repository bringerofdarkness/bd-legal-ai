def classify_query(query: str) -> str:
    q = query.lower()

    if "punishment" in q or "penalty" in q:
        return "punishment"

    if "which section" in q or "what section" in q:
        return "section_lookup"

    if "what is" in q or "define" in q or "meaning of" in q:
        return "definition"

    return "concept"