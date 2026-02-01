"""FastAPI middleware for authentication per ADR-005."""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import Callable

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from redletters.engine_spine.auth import (
    get_auth_token,
    mask_token,
    validate_token,
)

logger = logging.getLogger(__name__)

# Rate limiting for failed auth attempts
_failed_attempts: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX = 10  # max failures per window


def reset_rate_limiter() -> None:
    """Reset the auth rate limiter. Used in tests."""
    _failed_attempts.clear()


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware requiring Bearer token authentication.

    All requests (except health/docs) require:
    - Authorization: Bearer <token> header
    - Token matches per-install auth token
    """

    # Paths that don't require authentication
    EXEMPT_PATHS = {
        "/",
        "/docs",
        "/redoc",
        "/openapi.json",
    }

    async def dispatch(self, request: Request, call_next: Callable):
        path = request.url.path

        # Allow CORS preflight requests through (browser sends OPTIONS before actual request)
        if request.method == "OPTIONS":
            return await call_next(request)

        # Allow exempt paths
        if path in self.EXEMPT_PATHS:
            return await call_next(request)

        # Check rate limiting
        client_id = self._get_client_id(request)
        if self._is_rate_limited(client_id):
            logger.warning(f"Rate limited auth attempt from {client_id}")
            return JSONResponse(
                status_code=429,
                content={
                    "error": "E_AUTH_RATE_LIMITED",
                    "code": "rate_limited",
                    "message": "Too many authentication failures. Wait 60 seconds before retrying.",
                },
            )

        # Get auth header
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            self._record_failure(client_id)
            return JSONResponse(
                status_code=401,
                content={
                    "error": "E_AUTH_MISSING",
                    "code": "missing_auth",
                    "message": "Authorization header required. Include 'Authorization: Bearer <token>' in your request.",
                },
            )

        # Parse Bearer token
        if not auth_header.startswith("Bearer "):
            self._record_failure(client_id)
            return JSONResponse(
                status_code=401,
                content={
                    "error": "E_AUTH_INVALID",
                    "code": "invalid_auth",
                    "message": "Invalid authorization header format. Expected 'Bearer <token>'.",
                },
            )

        provided_token = auth_header[7:]  # Skip "Bearer "

        # Validate token
        try:
            expected_token = get_auth_token()
        except Exception as e:
            logger.error(f"Failed to get auth token: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "error": "E_AUTH_CONFIG",
                    "code": "config_error",
                    "message": "Authentication configuration error.",
                },
            )

        if not validate_token(provided_token, expected_token):
            self._record_failure(client_id)
            logger.warning(
                f"Invalid token from {client_id}: {mask_token(provided_token)}"
            )
            return JSONResponse(
                status_code=401,
                content={
                    "error": "E_AUTH_INVALID",
                    "code": "invalid_token",
                    "message": "Invalid authentication token. Run 'redletters auth show' to view your token, or 'redletters auth reset' to generate a new one.",
                },
            )

        # Auth successful
        return await call_next(request)

    def _get_client_id(self, request: Request) -> str:
        """Get identifier for rate limiting (IP + port for localhost)."""
        if request.client:
            return f"{request.client.host}:{request.client.port}"
        return "unknown"

    def _is_rate_limited(self, client_id: str) -> bool:
        """Check if client is rate limited."""
        now = time.time()
        attempts = _failed_attempts[client_id]

        # Clean old attempts
        attempts[:] = [t for t in attempts if now - t < RATE_LIMIT_WINDOW]

        return len(attempts) >= RATE_LIMIT_MAX

    def _record_failure(self, client_id: str) -> None:
        """Record a failed auth attempt."""
        _failed_attempts[client_id].append(time.time())


def require_auth(request: Request) -> None:
    """Dependency for routes requiring authentication.

    Use as:
        @router.get("/protected")
        async def protected(_: None = Depends(require_auth)):
            ...
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "E_AUTH_MISSING",
                "code": "missing_auth",
                "message": "Authorization header required.",
            },
        )

    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail={
                "error": "E_AUTH_INVALID",
                "code": "invalid_auth",
                "message": "Invalid authorization header format.",
            },
        )

    provided_token = auth_header[7:]
    expected_token = get_auth_token()

    if not validate_token(provided_token, expected_token):
        raise HTTPException(
            status_code=401,
            detail={
                "error": "E_AUTH_INVALID",
                "code": "invalid_token",
                "message": "Invalid authentication token.",
            },
        )


class MaskingFilter(logging.Filter):
    """Log filter that masks auth tokens."""

    def filter(self, record: logging.LogRecord) -> bool:
        if hasattr(record, "msg") and isinstance(record.msg, str):
            from redletters.engine_spine.auth import scrub_secrets

            record.msg = scrub_secrets(record.msg)
        return True


def setup_secure_logging() -> None:
    """Configure logging with token masking."""
    # Add masking filter to root logger
    root_logger = logging.getLogger()
    root_logger.addFilter(MaskingFilter())

    # Also add to uvicorn loggers
    for name in ["uvicorn", "uvicorn.access", "uvicorn.error"]:
        logging.getLogger(name).addFilter(MaskingFilter())
