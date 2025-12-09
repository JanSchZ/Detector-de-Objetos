"""
Middleware for Argos API.
Implements rate limiting, request validation, and security headers.
"""
import time
from collections import defaultdict
from typing import Callable
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import os

# Rate limiting configuration
RATE_LIMIT_REQUESTS = int(os.getenv("VM_RATE_LIMIT_REQUESTS", "100"))
RATE_LIMIT_WINDOW = int(os.getenv("VM_RATE_LIMIT_WINDOW", "60"))  # seconds


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiting middleware.
    Limits requests per IP address within a time window.
    """
    
    def __init__(self, app: ASGIApp, requests_limit: int = RATE_LIMIT_REQUESTS, window_seconds: int = RATE_LIMIT_WINDOW):
        super().__init__(app)
        self.requests_limit = requests_limit
        self.window_seconds = window_seconds
        self.requests: dict[str, list[float]] = defaultdict(list)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for WebSocket connections
        if request.url.path.startswith("/ws"):
            return await call_next(request)
        
        # Get client IP
        client_ip = self._get_client_ip(request)
        current_time = time.time()
        
        # Clean old requests
        self.requests[client_ip] = [
            req_time for req_time in self.requests[client_ip]
            if current_time - req_time < self.window_seconds
        ]
        
        # Check rate limit
        if len(self.requests[client_ip]) >= self.requests_limit:
            return Response(
                content='{"detail": "Rate limit exceeded. Please try again later."}',
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={
                    "Content-Type": "application/json",
                    "Retry-After": str(self.window_seconds),
                    "X-RateLimit-Limit": str(self.requests_limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(current_time + self.window_seconds)),
                }
            )
        
        # Record request
        self.requests[client_ip].append(current_time)
        
        # Add rate limit headers to response
        response = await call_next(request)
        remaining = self.requests_limit - len(self.requests[client_ip])
        response.headers["X-RateLimit-Limit"] = str(self.requests_limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(current_time + self.window_seconds))
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP, considering proxies."""
        # Check X-Forwarded-For header (for reverse proxies)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        # Check X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fall back to direct client IP
        if request.client:
            return request.client.host
        
        return "unknown"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Cache control for API responses
        if request.url.path.startswith("/api"):
            response.headers["Cache-Control"] = "no-store, max-age=0"
        
        return response


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """
    Validate incoming requests for common issues.
    """
    
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check content length
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > self.MAX_CONTENT_LENGTH:
                    return Response(
                        content='{"detail": "Request body too large"}',
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        headers={"Content-Type": "application/json"}
                    )
            except ValueError:
                pass
        
        return await call_next(request)


def setup_middleware(app):
    """
    Configure all middleware for the application.
    Call this in main.py after creating the FastAPI app.
    """
    # Order matters: first added = outermost (runs first on request, last on response)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestValidationMiddleware)
    app.add_middleware(RateLimitMiddleware)
