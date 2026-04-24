"""
shared/rbac/permissions.py
============================
Role-Based Access Control for KLA SaaS.

Two-level model:
  Level 1 — Platform: SuperAdmin manages tenants
  Level 2 — Tenant:   Owner / Admin / Sales / Warehouse / Finance

Permission matrix:
  Module        Owner  Admin  Sales  Warehouse  Finance
  ─────────────────────────────────────────────────────
  Purchase       ✓      ✓      ✗       ✓          ✗
  Sales          ✓      ✓      ✓       ✗          ✓*
  Inventory      ✓      ✓      ✗       ✓          ✗
  Invoices       ✓      ✓      ✗       ✗          ✓
  Payments       ✓      ✗      ✗       ✗          ✓
  Users/Settings ✓      ✓      ✗       ✗          ✗
  Tenants        SuperAdmin only

  * Finance sees invoices + payments, but not SO creation/confirm

Usage in routes:
    from app.shared.rbac.permissions import require_roles, Role

    @router.post("/orders")
    def create_order(
        ...,
        ctx: TenantContext = Depends(get_tenant_context),
        _: None = Depends(require_roles(Role.OWNER, Role.ADMIN, Role.SALES)),
    ):
        ...
"""

from enum import Enum
from functools import wraps
from typing import Callable

from app.core.dependencies import TenantContext, get_tenant_context
from fastapi import Depends, HTTPException, status


class Role(str, Enum):
    SUPER_ADMIN = "super_admin"   # platform level — no tenant_id
    OWNER       = "owner"         # full access within tenant
    ADMIN       = "admin"         # manage users + settings
    SALES       = "sales"         # sales module
    WAREHOUSE   = "warehouse"     # inventory module
    FINANCE     = "finance"       # invoices + payments


# ─── Permission sets ──────────────────────────────────────────────────────────
# Named permission sets map to groups of roles.
# Use these in route decorators for clarity.

class Permission:
    # Purchase
    VIEW_PURCHASE   = [Role.OWNER, Role.ADMIN, Role.WAREHOUSE]
    MANAGE_PURCHASE = [Role.OWNER, Role.ADMIN, Role.WAREHOUSE]

    # Sales orders + Surat Jalan
    VIEW_SALES      = [Role.OWNER, Role.ADMIN, Role.SALES, Role.FINANCE]
    MANAGE_SALES    = [Role.OWNER, Role.ADMIN, Role.SALES]

    # Invoices
    VIEW_INVOICES   = [Role.OWNER, Role.ADMIN, Role.FINANCE]
    MANAGE_INVOICES = [Role.OWNER, Role.ADMIN, Role.FINANCE]

    # Payments
    MANAGE_PAYMENTS = [Role.OWNER, Role.FINANCE]

    # Inventory
    VIEW_INVENTORY  = [Role.OWNER, Role.ADMIN, Role.WAREHOUSE]
    MANAGE_INVENTORY = [Role.OWNER, Role.ADMIN, Role.WAREHOUSE]

    # Users + Settings
    MANAGE_USERS    = [Role.OWNER, Role.ADMIN]
    MANAGE_SETTINGS = [Role.OWNER, Role.ADMIN]

    # Platform
    SUPER_ADMIN_ONLY = [Role.SUPER_ADMIN]


# ─── FastAPI dependency factory ───────────────────────────────────────────────

def require_roles(*allowed_roles: Role):
    """
    FastAPI dependency that enforces role-based access.

    Usage:
        @router.post("/orders")
        def create_order(
            ...,
            _: None = Depends(require_roles(Role.OWNER, Role.ADMIN, Role.SALES)),
        ):
            ...

    Raises 403 if the user's role is not in allowed_roles.
    SuperAdmin always passes (they can do everything).
    """
    def _check(ctx: TenantContext = Depends(get_tenant_context)):
        if ctx.user_role == Role.SUPER_ADMIN:
            return  # super admin bypasses all role checks
        if ctx.user_role not in [r.value for r in allowed_roles]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Access denied. Required roles: "
                    f"{[r.value for r in allowed_roles]}. "
                    f"Your role: {ctx.user_role}"
                ),
            )
    return _check


def require_permission(permission: list[Role]):
    """
    Convenience wrapper using named permission sets.

    Usage:
        @router.post("/payments")
        def record_payment(
            ...,
            _: None = Depends(require_permission(Permission.MANAGE_PAYMENTS)),
        ):
            ...
    """
    return require_roles(*permission)
