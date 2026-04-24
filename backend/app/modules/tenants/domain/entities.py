"""
modules/tenants/domain/entities.py
=====================================
Tenant and User domain entities.

Tenant = a company using KLA SaaS (e.g. PT Kusuma Lestari Agro).
User   = a person who belongs to a tenant with a specific role.

SuperAdmin users have tenant_id = None (platform-level).
All other users MUST have a tenant_id.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from app.shared.rbac.permissions import Role


class TenantStatus(str):
    ACTIVE    = "active"
    SUSPENDED = "suspended"
    TRIAL     = "trial"


@dataclass
class Tenant:
    id:            Optional[int]
    name:          str              # e.g. "PT Kusuma Lestari Agro"
    slug:          str              # e.g. "pt-kusuma-lestari-agro" (URL-safe)
    status:        str              # active, suspended, trial
    plan:          str              # "starter", "pro", "enterprise"
    owner_email:   str
    phone:         Optional[str]    = None
    address:       Optional[str]    = None
    npwp:          Optional[str]    = None   # Indonesian tax ID
    logo_url:      Optional[str]    = None
    created_at:    Optional[datetime] = None

    def suspend(self) -> None:
        if self.status == TenantStatus.SUSPENDED:
            raise ValueError("Tenant is already suspended.")
        self.status = TenantStatus.SUSPENDED

    def activate(self) -> None:
        self.status = TenantStatus.ACTIVE


@dataclass
class User:
    id:             Optional[int]
    tenant_id:      Optional[int]   # None for SuperAdmin
    email:          str
    full_name:      str
    role:           Role
    hashed_password: str
    is_active:      bool = True
    last_login:     Optional[datetime] = None
    created_at:     Optional[datetime] = None

    @property
    def is_super_admin(self) -> bool:
        return self.role == Role.SUPER_ADMIN

    def deactivate(self) -> None:
        if not self.is_active:
            raise ValueError("User is already inactive.")
        self.is_active = False

    def change_role(self, new_role: Role) -> None:
        if self.role == Role.OWNER and new_role != Role.OWNER:
            raise ValueError(
                "Cannot change Owner role directly. "
                "Transfer ownership first."
            )
        self.role = new_role
