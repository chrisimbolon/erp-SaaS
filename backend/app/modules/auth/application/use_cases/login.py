"""
modules/auth/application/use_cases/login.py
=============================================
Login use case — works for both SuperAdmin and tenant users.

Returns JWT with:
  { tenant_id, user_id, role, email, full_name }

SuperAdmin: tenant_id = 0 (special sentinel value)
"""

from datetime import datetime

from app.core.security import create_access_token, verify_password
from app.modules.auth.application.schemas import LoginRequest, TokenResponse
from app.modules.tenants.infrastructure.repository import UserRepository
from sqlalchemy.orm import Session


class LoginUseCase:

    def __init__(self, db: Session):
        self.db = db
        self.repo = UserRepository(db)

    def execute(self, request: LoginRequest) -> TokenResponse:

        # ── Find user ─────────────────────────────────────────────────────────
        user = self.repo.get_by_email(request.email)

        if not user:
            # Use same error as wrong password — prevents user enumeration
            raise ValueError("Invalid email or password.")

        if not user.is_active:
            raise ValueError("Account is deactivated. Contact your administrator.")

        # ── Verify password ───────────────────────────────────────────────────
        if not verify_password(request.password, user.hashed_password):
            raise ValueError("Invalid email or password.")

        # ── Update last login ─────────────────────────────────────────────────
        self.repo.update_last_login(user.id)

        # ── Issue JWT ─────────────────────────────────────────────────────────
        # SuperAdmin has no tenant — use 0 as sentinel
        tenant_id_for_token = user.tenant_id or 0

        token = create_access_token(
            tenant_id=tenant_id_for_token,
            user_id=user.id,
            role=user.role.value,
            email=user.email,
            full_name=user.full_name,
        )

        return TokenResponse(
            access_token=token,
            token_type="bearer",
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role.value,
            tenant_id=user.tenant_id,
        )
