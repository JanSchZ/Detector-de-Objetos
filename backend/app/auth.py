"""
Authentication module for Argos.
Implements JWT-based authentication with API key support for WebSocket.
"""
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from pathlib import Path

from fastapi import Depends, HTTPException, status, Request, WebSocket
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import hashlib
import hmac
import base64
import json

# Load environment variables
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

# Configuration
SECRET_KEY = os.getenv("VM_SECRET_KEY", secrets.token_hex(32))
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("VM_TOKEN_EXPIRE_MINUTES", "60"))
API_KEY = os.getenv("VM_API_KEY", "")  # Optional API key for simple auth
AUTH_ENABLED = os.getenv("VM_AUTH_ENABLED", "false").lower() == "true"

# Simple user store (in production, use database)
USERS_DB: dict[str, dict] = {}

# Initialize default admin user if not exists
DEFAULT_ADMIN_USER = os.getenv("VM_ADMIN_USER", "admin")
DEFAULT_ADMIN_PASS = os.getenv("VM_ADMIN_PASS", "argos")


class TokenData(BaseModel):
    username: str
    exp: datetime


class User(BaseModel):
    username: str
    disabled: bool = False


class UserInDB(User):
    password_hash: str


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


# Security scheme
security = HTTPBearer(auto_error=False)


def _hash_password(password: str) -> str:
    """Hash password using SHA-256 with salt."""
    salt = SECRET_KEY[:16]
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()


def _verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return _hash_password(plain_password) == hashed_password


def _create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT-like token (simplified, no external dependencies)."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode["exp"] = expire.isoformat()
    
    # Create token: base64(payload).signature
    payload = base64.urlsafe_b64encode(json.dumps(to_encode).encode()).decode()
    signature = hmac.new(
        SECRET_KEY.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()[:32]
    
    return f"{payload}.{signature}"


def _decode_token(token: str) -> Optional[TokenData]:
    """Decode and verify a token."""
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None
        
        payload_b64, signature = parts
        
        # Verify signature
        expected_sig = hmac.new(
            SECRET_KEY.encode(),
            payload_b64.encode(),
            hashlib.sha256
        ).hexdigest()[:32]
        
        if not hmac.compare_digest(signature, expected_sig):
            return None
        
        # Decode payload
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        
        # Check expiration
        exp = datetime.fromisoformat(payload["exp"])
        if datetime.now(timezone.utc) > exp:
            return None
        
        return TokenData(username=payload["sub"], exp=exp)
    except Exception:
        return None


def get_user(username: str) -> Optional[UserInDB]:
    """Get user from database."""
    # Initialize default admin if needed
    if not USERS_DB and username == DEFAULT_ADMIN_USER:
        USERS_DB[DEFAULT_ADMIN_USER] = {
            "username": DEFAULT_ADMIN_USER,
            "password_hash": _hash_password(DEFAULT_ADMIN_PASS),
            "disabled": False,
        }
    
    if username in USERS_DB:
        user_dict = USERS_DB[username]
        return UserInDB(**user_dict)
    return None


def authenticate_user(username: str, password: str) -> Optional[User]:
    """Authenticate a user with username and password."""
    user = get_user(username)
    if not user:
        return None
    if not _verify_password(password, user.password_hash):
        return None
    return User(username=user.username, disabled=user.disabled)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[User]:
    """Get current user from JWT token."""
    # If auth is disabled, return a default user
    if not AUTH_ENABLED:
        return User(username="anonymous")
    
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token_data = _decode_token(credentials.credentials)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = get_user(token_data.username)
    if not user or user.disabled:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or disabled",
        )
    
    return User(username=user.username, disabled=user.disabled)


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[User]:
    """Get current user if authenticated, otherwise None."""
    if not AUTH_ENABLED:
        return User(username="anonymous")
    
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


def verify_websocket_token(token: str) -> Optional[User]:
    """Verify token for WebSocket connections."""
    if not AUTH_ENABLED:
        return User(username="anonymous")
    
    # Check API key first
    if API_KEY and token == API_KEY:
        return User(username="api_key_user")
    
    # Try JWT token
    token_data = _decode_token(token)
    if token_data:
        user = get_user(token_data.username)
        if user and not user.disabled:
            return User(username=user.username)
    
    return None


async def websocket_auth(websocket: WebSocket) -> Optional[User]:
    """Authenticate WebSocket connection."""
    if not AUTH_ENABLED:
        return User(username="anonymous")
    
    # Try to get token from query params
    token = websocket.query_params.get("token")
    
    # Or from headers
    if not token:
        auth_header = websocket.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    
    if not token:
        return None
    
    return verify_websocket_token(token)


def create_user(username: str, password: str) -> User:
    """Create a new user."""
    if username in USERS_DB:
        raise ValueError("User already exists")
    
    USERS_DB[username] = {
        "username": username,
        "password_hash": _hash_password(password),
        "disabled": False,
    }
    
    return User(username=username)


def login(username: str, password: str) -> TokenResponse:
    """Authenticate user and return access token."""
    user = authenticate_user(username, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = _create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    
    return TokenResponse(
        access_token=access_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


def get_auth_status() -> dict:
    """Get current authentication status and configuration."""
    return {
        "enabled": AUTH_ENABLED,
        "api_key_configured": bool(API_KEY),
        "token_expire_minutes": ACCESS_TOKEN_EXPIRE_MINUTES,
    }
