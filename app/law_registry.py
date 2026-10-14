"""
Backward-Compatible Forwarder for Law Registry
Delegates directly to app.core.registry.
"""

from app.core.registry import LawConfig, LAW_REGISTRY

__all__ = ["LawConfig", "LAW_REGISTRY"]