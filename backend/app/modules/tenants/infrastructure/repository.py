"""
modules/tenants/infrastructure/repository.py
"""

from typing import Optional

from app.modules.tenants.domain.entities import Tenant, TenantStatus, User
from app.shared.rbac.permissions import Role
from sqlalchemy.orm import Session


class TenantRepository:

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, tenant_id: int) -> Optional[Tenant]:
        from app.modules.tenants.infrastructure.models import TenantModel
        row = self.db.query(TenantModel).filter(TenantModel.id == tenant_id).first()
        return self._to_entity(row) if row else None

    def get_by_slug(self, slug: str) -> Optional[Tenant]:
        from app.modules.tenants.infrastructure.models import TenantModel
        row = self.db.query(TenantModel).filter(TenantModel.slug == slug).first()
        return self._to_entity(row) if row else None

    def save(self, tenant: Tenant) -> Tenant:
        from app.modules.tenants.infrastructure.models import TenantModel
        row = TenantModel(
            name=tenant.name, slug=tenant.slug, status=tenant.status,
            plan=tenant.plan, owner_email=tenant.owner_email,
            phone=tenant.phone, address=tenant.address,
            npwp=tenant.npwp, logo_url=tenant.logo_url,
        )
        self.db.add(row)
        self.db.flush()
        tenant.id = row.id
        return tenant

    def list_all(self) -> list[Tenant]:
        from app.modules.tenants.infrastructure.models import TenantModel
        rows = self.db.query(TenantModel).order_by(TenantModel.name).all()
        return [self._to_entity(r) for r in rows]

    def _to_entity(self, row) -> Tenant:
        return Tenant(
            id=row.id, name=row.name, slug=row.slug,
            status=row.status, plan=row.plan, owner_email=row.owner_email,
            phone=row.phone, address=row.address, npwp=row.npwp,
            logo_url=row.logo_url, created_at=row.created_at,
        )


class UserRepository:

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: int) -> Optional[User]:
        from app.modules.tenants.infrastructure.models import UserModel
        row = self.db.query(UserModel).filter(UserModel.id == user_id).first()
        return self._to_entity(row) if row else None

    def get_by_email(self, email: str) -> Optional[User]:
        from app.modules.tenants.infrastructure.models import UserModel
        row = self.db.query(UserModel).filter(
            UserModel.email == email.lower().strip()
        ).first()
        return self._to_entity(row) if row else None

    def get_by_tenant(self, tenant_id: int) -> list[User]:
        from app.modules.tenants.infrastructure.models import UserModel
        rows = self.db.query(UserModel).filter(
            UserModel.tenant_id == tenant_id
        ).order_by(UserModel.full_name).all()
        return [self._to_entity(r) for r in rows]

    def save(self, user: User) -> User:
        from app.modules.tenants.infrastructure.models import UserModel
        row = UserModel(
            tenant_id=user.tenant_id, email=user.email.lower().strip(),
            full_name=user.full_name, role=user.role.value,
            hashed_password=user.hashed_password, is_active=user.is_active,
        )
        self.db.add(row)
        self.db.flush()
        user.id = row.id
        return user

    def update_last_login(self, user_id: int) -> None:
        from app.modules.tenants.infrastructure.models import UserModel
        from sqlalchemy import func
        self.db.query(UserModel).filter(
            UserModel.id == user_id
        ).update({"last_login": func.now()})

    def update_role(self, user_id: int, new_role: Role) -> None:
        from app.modules.tenants.infrastructure.models import UserModel
        self.db.query(UserModel).filter(
            UserModel.id == user_id
        ).update({"role": new_role.value})

    def deactivate(self, user_id: int) -> None:
        from app.modules.tenants.infrastructure.models import UserModel
        self.db.query(UserModel).filter(
            UserModel.id == user_id
        ).update({"is_active": False})

    def _to_entity(self, row) -> User:
        return User(
            id=row.id, tenant_id=row.tenant_id, email=row.email,
            full_name=row.full_name, role=Role(row.role),
            hashed_password=row.hashed_password, is_active=row.is_active,
            last_login=row.last_login, created_at=row.created_at,
        )
