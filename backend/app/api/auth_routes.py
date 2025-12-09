"""
Authentication API routes.
"""
from fastapi import APIRouter, Depends, HTTPException

from app.auth import (
    login,
    get_auth_status,
    get_current_user,
    get_optional_user,
    create_user,
    LoginRequest,
    TokenResponse,
    User,
    AUTH_ENABLED,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/status")
async def auth_status() -> dict:
    """Get authentication status and configuration."""
    return get_auth_status()


@router.post("/login", response_model=TokenResponse)
async def login_user(request: LoginRequest) -> TokenResponse:
    """Authenticate user and get access token."""
    if not AUTH_ENABLED:
        return TokenResponse(
            access_token="auth_disabled",
            expires_in=0,
        )
    return login(request.username, request.password)


@router.get("/me")
async def get_current_user_info(user: User = Depends(get_current_user)) -> dict:
    """Get current authenticated user info."""
    return {
        "username": user.username,
        "disabled": user.disabled,
        "authenticated": True,
    }


@router.post("/register", response_model=dict)
async def register_user(request: LoginRequest, current_user: User = Depends(get_current_user)) -> dict:
    """
    Register a new user. Requires authentication (admin only).
    """
    if not AUTH_ENABLED:
        raise HTTPException(status_code=400, detail="Authentication is disabled")
    
    try:
        new_user = create_user(request.username, request.password)
        return {
            "status": "created",
            "username": new_user.username,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/logout")
async def logout() -> dict:
    """
    Logout is handled client-side by discarding the token.
    This endpoint is provided for API completeness.
    """
    return {"status": "ok", "message": "Token should be discarded client-side"}
