"""
app/core/middleware.py
=======================
TenantMiddleware: decodes JWT and populates request.state.

CRITICAL: Never raise HTTPException inside BaseHTTPMiddleware.
          It breaks Starlette's exception handling chain and causes
          'State has no attribute tenant_id' downstream.
          Always return a JSONResponse directly instead.
"""
from app.core.security import decode_jwt
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

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

        # Public paths — skip auth entirely, no state needed
        if path in PUBLIC_PATHS or path.startswith("/docs") or path.startswith("/openapi"):
            return await call_next(request)

        # ── Validate token ────────────────────────────────────────────────────
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing or invalid Authorization header."},
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = auth_header.split(" ", 1)[1]
        try:
            payload = decode_jwt(token)
        except ValueError:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or expired token."},
                headers={"WWW-Authenticate": "Bearer"},
            )

        # ── Inject into request.state ─────────────────────────────────────────
        # Always set ALL fields before calling call_next so that
        # get_tenant_context() never hits AttributeError downstream.
        request.state.tenant_id = payload.get("tenant_id")   # 0 = SuperAdmin
        request.state.user_id   = payload.get("user_id", 0)
        request.state.user_role = payload.get("role", "")
        request.state.email     = payload.get("email", "")
        request.state.full_name = payload.get("full_name", "")

        return await call_next(request)
