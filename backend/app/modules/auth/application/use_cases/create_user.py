"""
modules/auth/application/use_cases/create_user.py
===================================================
Creates a new user within a tenant.
Only Owner or Admin can do this (enforced at route level via require_roles).

Rules:
  - Email must be unique across ALL tenants (users table has unique constraint)
  - Cannot create a SuperAdmin via this endpoint
  - Cannot create an Owner via this endpoint (only one Owner per tenant)
    → use transfer_ownership for that
"""

from app.core.security import hash_password
from app.modules.auth.application.schemas import (CreateUserRequest,
                                                  UserResponse)
from app.modules.tenants.domain.entities import User
from app.modules.tenants.infrastructure.repository import UserRepository
from app.shared.rbac.permissions import Role
from sqlalchemy.orm import Session


class CreateUserUseCase:

    def __init__(self, db: Session, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.repo = UserRepository(db)

    def execute(self, request: CreateUserRequest) -> UserResponse:

        # ── Guard: forbidden roles via this endpoint ───────────────────────
        if request.role in (Role.SUPER_ADMIN, Role.OWNER):
            raise ValueError(
                f"Cannot create a user with role '{request.role}' via this endpoint."
            )

        # ── Check email uniqueness ─────────────────────────────────────────
        existing = self.repo.get_by_email(request.email)
        if existing:
            raise ValueError(f"Email '{request.email}' is already registered.")

        # ── Create user ────────────────────────────────────────────────────
        user = User(
            id=None,
            tenant_id=self.tenant_id,
            email=request.email,
            full_name=request.full_name,
            role=request.role,
            hashed_password=hash_password(request.password),
            is_active=True,
        )
        saved = self.repo.save(user)

        return UserResponse(
            id=saved.id,
            email=saved.email,
            full_name=saved.full_name,
            role=saved.role,
            is_active=saved.is_active,
            tenant_id=saved.tenant_id,
        )


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
