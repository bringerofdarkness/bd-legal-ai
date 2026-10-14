"""
Authentication and Dependency Injection for Bangladesh Legal AI API
Supports the "Optional Authentication" pattern for guest and logged-in users.
"""

from fastapi import Header
from typing import Optional
from pydantic import BaseModel, Field

from app.core.auth import decode_access_token, authenticate_user_token, CurrentUser
from app.core.logging import get_logger

logger = get_logger("app.api.dependencies")


class User(BaseModel):
    user_id: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: str = "guest"
    is_guest: bool = True
    is_authenticated: bool = False

    @property
    def id(self) -> str:
        """Convenience property for backward compatibility."""
        return self.user_id


async def get_optional_current_user(
    authorization: Optional[str] = Header(None)
) -> Optional[User]:
    """
    Extracts authenticated user details if a valid JWT Bearer token is provided.
    Returns None for guest/unauthenticated users without blocking query execution.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None

    token = authorization.split(" ")[1].strip()
    if not token:
        return None

    user = authenticate_user_token(token)
    if user:
        return User(
            user_id=user.user_id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            is_guest=user.is_guest,
            is_authenticated=user.is_authenticated,
        )

    return None
