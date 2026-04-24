"""
modules/auth/application/use_cases/register_tenant.py
=======================================================
Registers a new tenant company + creates the Owner user.
Both happen in a single DB transaction — either both succeed or neither does.

Called by:
  - SuperAdmin via POST /api/v1/tenants (creates tenant for a client)
  - (Future: self-service signup page)

Flow:
  1. Validate slug is unique
  2. Validate owner email is not already in use
  3. Create Tenant row
  4. Create User row (role=OWNER, tenant_id=tenant.id)
  5. Commit both atomically
"""

from app.core.security import hash_password
from app.modules.auth.application.schemas import (RegisterTenantRequest,
                                                  RegisterTenantResponse)
from app.modules.tenants.domain.entities import Tenant, TenantStatus, User
from app.modules.tenants.infrastructure.repository import (TenantRepository,
                                                           UserRepository)
from app.shared.rbac.permissions import Role
from sqlalchemy.orm import Session


class RegisterTenantUseCase:

    def __init__(self, db: Session):
        self.db = db
        self.tenant_repo = TenantRepository(db)
        self.user_repo = UserRepository(db)

    def execute(self, request: RegisterTenantRequest) -> RegisterTenantResponse:

        # ── Validate uniqueness ───────────────────────────────────────────────
        existing_slug = self.tenant_repo.get_by_slug(request.slug)
        if existing_slug:
            raise ValueError(f"Slug '{request.slug}' is already taken.")

        existing_email = self.user_repo.get_by_email(request.owner_email)
        if existing_email:
            raise ValueError(f"Email '{request.owner_email}' is already registered.")

        # ── Create Tenant ─────────────────────────────────────────────────────
        tenant = Tenant(
            id=None,
            name=request.company_name,
            slug=request.slug,
            status=TenantStatus.TRIAL,
            plan=request.plan or "starter",
            owner_email=request.owner_email,
            phone=request.phone,
            address=request.address,
            npwp=request.npwp,
        )
        saved_tenant = self.tenant_repo.save(tenant)

        # ── Create Owner user ─────────────────────────────────────────────────
        owner = User(
            id=None,
            tenant_id=saved_tenant.id,
            email=request.owner_email,
            full_name=request.owner_name,
            role=Role.OWNER,
            hashed_password=hash_password(request.owner_password),
            is_active=True,
        )
        saved_owner = self.user_repo.save(owner)

        return RegisterTenantResponse(
            tenant_id=saved_tenant.id,
            company_name=saved_tenant.name,
            slug=saved_tenant.slug,
            owner_id=saved_owner.id,
            owner_email=saved_owner.email,
            status=saved_tenant.status,
        )
