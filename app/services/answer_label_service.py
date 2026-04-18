def get_answer_label(q: str) -> str:
    if any(kw in q for kw in ["punish", "punishment", "penalty", "sentence", "fine", "imprisonment"]):
        return "punishment"
    elif any(kw in q for kw in ["define", "definition", "meaning", "what is", "what constitutes"]):
        return "definition"
    return "provision"