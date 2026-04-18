def classify_query(query: str) -> str:
    q = query.lower().strip()

    if "which section" in q or "what section" in q or "section" in q:
        return "section_lookup"

    if "punishment" in q or "penalty" in q or "sentence" in q or "fine" in q or "imprisonment" in q:
        return "punishment"

    if (
        "what is" in q
        or "define" in q
        or "meaning of" in q
        or "legal meaning" in q
        or "who is called" in q
        or "who is" in q
    ):
        return "definition"

    return "concept"