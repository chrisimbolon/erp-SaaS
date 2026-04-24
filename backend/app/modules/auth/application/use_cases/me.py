"""
modules/auth/application/use_cases/me.py
==========================================
Returns current user profile from JWT.
No DB query needed — all info is in the token.
Used by the frontend to hydrate the user session.
"""

from app.core.dependencies import TenantContext
from app.modules.auth.application.schemas import UserResponse
from app.shared.rbac.permissions import Role


class MeUseCase:

    @staticmethod
    def execute(ctx: TenantContext) -> UserResponse:
        return UserResponse(
            id=ctx.user_id,
            email=ctx.email,
            full_name=ctx.full_name,
            role=Role(ctx.user_role),
            is_active=True,
            tenant_id=ctx.tenant_id if ctx.tenant_id != 0 else None,
        )
