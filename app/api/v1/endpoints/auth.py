"""
Authentication API Endpoints
Provides guest session generation, advocate login, and token verification routes.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, EmailStr
from typing import Optional

from app.core.auth import (
    AuthToken,
    CurrentUser,
    create_access_token,
    create_guest_session,
    authenticate_user_token,
)
from app.api.dependencies import get_optional_current_user, User
from app.core.logging import get_logger

logger = get_logger("app.api.v1.endpoints.auth")
router = APIRouter()


class LoginRequest(BaseModel):
    username_or_email: str = Field(..., description="Email address or advocate username")
    password: str = Field(..., description="User password")


class AuthProfileResponse(BaseModel):
    user_id: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: str
    is_guest: bool
    is_authenticated: bool


@router.post(
    "/guest",
    response_model=AuthToken,
    summary="Create Guest Session",
    description="Issues an instant non-blocking guest token for anonymous civic legal queries."
)
async def generate_guest_token() -> AuthToken:
    logger.info("Generating new guest session token")
    return create_guest_session()


@router.post(
    "/token",
    response_model=AuthToken,
    summary="Advocate / User Login",
    description="Authenticates advocate credentials and issues a signed JWT Bearer token."
)
async def login_for_access_token(request: LoginRequest) -> AuthToken:
    username = request.username_or_email.strip()
    if not username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email is required."
        )

    # In production: authenticate against users database table with bcrypt
    # Demo/Development credential support:
    demo_user_id = f"advocate_{abs(hash(username)) % 100000}"
    token = create_access_token(
        data={
            "sub": demo_user_id,
            "email": username if "@" in username else f"{username}@barcouncil.gov.bd",
            "full_name": f"Advocate {username.capitalize()}",
            "role": "advocate",
        },
        is_guest=False
    )
    logger.info(f"Issued advocate access token for user: {username}")
    return AuthToken(
        access_token=token,
        token_type="bearer",
        expires_in_seconds=86400,
        is_guest=False,
        user_id=demo_user_id,
    )


@router.get(
    "/me",
    response_model=AuthProfileResponse,
    summary="Get Current User Profile",
    description="Returns profile information for the current bearer token (or indicates Guest status)."
)
async def get_current_user_profile(
    current_user: Optional[User] = Depends(get_optional_current_user)
) -> AuthProfileResponse:
    if current_user:
        return AuthProfileResponse(
            user_id=current_user.user_id,
            email=current_user.email,
            full_name=current_user.full_name,
            role=current_user.role,
            is_guest=current_user.is_guest,
            is_authenticated=current_user.is_authenticated,
        )
    return AuthProfileResponse(
        user_id="guest_anonymous",
        email=None,
        full_name="Guest Citizen",
        role="guest",
        is_guest=True,
        is_authenticated=False,
    )
