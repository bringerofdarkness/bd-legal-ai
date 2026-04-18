def build_refusal(reason: str) -> dict:
    return {
        "status": "refused",
        "answer_text": "",
        "citations": [],
        "evidence": [],
        "refusal_reason": reason,
    }