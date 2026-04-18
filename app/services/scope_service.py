def is_cyber_query(q: str) -> bool:
    cyber_terms = ["cyber", "facebook", "hack", "hacked", "online account", "account"]
    return any(term in q for term in cyber_terms)


def is_supported_scope(q: str, analysis: dict) -> bool:
    supported_contract_terms = {
        "proposal", "acceptance", "promise", "promisor", "promisee",
        "consideration", "agreement", "contract"
    }

    theft_terms = {
        "theft", "steal", "stole", "stolen", "steals", "stealing",
        "took", "taken", "bag", "phone", "mobile", "money", "watch", "property"
    }

    return (
        analysis.get("law_hint") in {"penal_code", "contract_act"}
        or any(term in q for term in supported_contract_terms)
        or any(term in q for term in theft_terms)
    )