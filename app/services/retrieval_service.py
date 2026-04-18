from app.law_registry import LAW_REGISTRY


def get_supported_laws():
    return list(LAW_REGISTRY.keys())