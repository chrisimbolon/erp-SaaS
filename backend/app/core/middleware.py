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

        if path in PUBLIC_PATHS or path.startswith("/docs") or path.startswith("/openapi"):
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing Authorization header"},
            )

        token = auth_header.split(" ", 1)[1]

        try:
            payload = decode_jwt(token)
        except Exception:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid token"},
            )

        # ALWAYS set state safely
        request.state.tenant_id = payload.get("tenant_id", None)
        request.state.user_id = payload.get("user_id", 0)
        request.state.user_role = payload.get("role", "")
        request.state.email = payload.get("email", "")
        request.state.full_name = payload.get("full_name", "")

        return await call_next(request)