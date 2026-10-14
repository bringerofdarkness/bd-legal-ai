"""
Authentication and Dependency Injection for Bangladesh Legal AI API
Supports the "Optional Authentication" pattern for guest and logged-in users.
"""

from fastapi import Header
from typing import Optional
from pydantic import BaseModel


class User(BaseModel):
    user_id: str
    email: str
    full_name: Optional[str] = None
    is_authenticated: bool = True


async def get_optional_current_user(
    authorization: Optional[str] = Header(None)
) -> Optional[User]:
    """
    Extracts user details if a valid Bearer token is provided.
    Returns None for guest/unauthenticated users without blocking query execution.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None

    token = authorization.split(" ")[1].strip()

    # In production with JWT: decode token using PyJWT/jose and query database
    # For initial implementation: mock validation for valid token strings
    if token and len(token) > 10:
        return User(
            user_id="usr_demo_12345",
            email="lawyer@example.com",
            full_name="Advocate User",
            is_authenticated=True
        )

    return None
