"""
app/core/middleware.py
=======================
TenantMiddleware: extracts tenant_id from JWT and injects into request state.

Every request that hits a module route will have:
  request.state.tenant_id  → int
  request.state.user_id    → int
  request.state.user_role  → str

Modules NEVER read tenant_id from the request body.
They always use request.state.tenant_id set here.
This prevents tenant spoofing.
"""

from app.core.security import decode_jwt
from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware

# Routes that don't require a tenant context
PUBLIC_PATHS = {"/health", "/api/v1/auth/login", "/api/v1/auth/register", "/docs", "/openapi.json"}


class TenantMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):
        if request.url.path in PUBLIC_PATHS or request.url.path.startswith("/docs"):
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or invalid Authorization header",
            )

        token = auth_header.split(" ")[1]
        try:
            payload = decode_jwt(token)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )

        # Inject into request state — available everywhere downstream
        request.state.tenant_id = payload["tenant_id"]
        request.state.user_id = payload["user_id"]
        request.state.user_role = payload.get("role", "staff")

        return await call_next(request)
