"""
Authentication & JWT Token Management Service
Implements the "Optional Authentication" architecture pattern for Bangladesh Legal AI,
supporting seamless Guest access alongside authenticated advocate/user sessions.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import jwt
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("app.core.auth")


class AuthToken(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int
    is_guest: bool = False
    user_id: str


class CurrentUser(BaseModel):
    user_id: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: str = "guest"
    is_guest: bool = True
    is_authenticated: bool = False


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
    is_guest: bool = False,
) -> str:
    """
    Encodes a signed JWT bearer token with claims, issued-at, and expiration timestamps.
    """
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "iat": now,
        "exp": expire,
        "is_guest": is_guest,
    })

    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verifies and decodes a signed JWT bearer token.
    Returns the decoded payload dict if valid, or None if expired/tampered.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("JWT validation failed: Token has expired.")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"JWT validation failed: Invalid token ({e}).")
        return None
    except Exception as e:
        logger.error(f"Unexpected error decoding JWT: {e}", exc_info=True)
        return None


def create_guest_session() -> AuthToken:
    """
    Issues a non-blocking temporary guest session token.
    Provides civic users instant zero-friction query access without registration.
    """
    guest_uuid = f"guest_{uuid.uuid4().hex[:10]}"
    expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(
        data={"sub": guest_uuid, "role": "guest", "email": None},
        expires_delta=expires,
        is_guest=True,
    )
    return AuthToken(
        access_token=token,
        token_type="bearer",
        expires_in_seconds=int(expires.total_seconds()),
        is_guest=True,
        user_id=guest_uuid,
    )


def authenticate_user_token(token: str) -> Optional[CurrentUser]:
    """
    Extracts and maps CurrentUser from a decoded JWT bearer token.
    """
    payload = decode_access_token(token)
    if not payload:
        return None

    user_id = payload.get("sub", "")
    is_guest = payload.get("is_guest", False)
    role = payload.get("role", "guest" if is_guest else "advocate")
    email = payload.get("email")
    full_name = payload.get("full_name")

    return CurrentUser(
        user_id=user_id,
        email=email,
        full_name=full_name,
        role=role,
        is_guest=is_guest,
        is_authenticated=not is_guest,
    )
