"""
app/core/middleware.py
=======================
TenantMiddleware: decodes JWT and populates request.state
with all fields needed by TenantContext downstream.

Public paths bypass auth entirely.
All other paths MUST have a valid Bearer token.
"""

from app.core.security import decode_jwt
from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware

PUBLIC_PATHS = {
    "/health",
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/docs",
    "/openapi.json",
    "/redoc",
}


class TenantMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Allow public paths without auth
        if path in PUBLIC_PATHS or path.startswith("/docs") or path.startswith("/openapi"):
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or invalid Authorization header.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = auth_header.split(" ", 1)[1]
        try:
            payload = decode_jwt(token)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Inject all fields into request state
        # TenantContext dependency reads from here
        request.state.tenant_id = payload.get("tenant_id")   # 0 = SuperAdmin
        request.state.user_id   = payload["user_id"]
        request.state.user_role = payload["role"]
        request.state.email     = payload.get("email", "")
        request.state.full_name = payload.get("full_name", "")

        return await call_next(request)
