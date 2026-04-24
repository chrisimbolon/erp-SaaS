"""
modules/auth/presentation/api/v1/routes.py
============================================
Auth endpoints:

  POST /auth/login              → returns JWT (public)
  GET  /auth/me                 → current user profile
  POST /auth/register           → register new tenant + owner (SuperAdmin only)
  POST /auth/users              → create user within tenant (Owner/Admin only)
  GET  /auth/users              → list users in tenant (Owner/Admin only)
  PUT  /auth/users/{id}/deactivate  → deactivate user (Owner/Admin only)
"""

from app.core.dependencies import TenantContext, get_db, get_tenant_context
from app.modules.auth.application.schemas import (CreateUserRequest,
                                                  LoginRequest,
                                                  RegisterTenantRequest,
                                                  RegisterTenantResponse,
                                                  TokenResponse,
                                                  UserListResponse,
                                                  UserResponse)
from app.modules.auth.application.use_cases.create_user import (
    CreateUserUseCase, MeUseCase)
from app.modules.auth.application.use_cases.login import LoginUseCase
from app.modules.auth.application.use_cases.register_tenant import \
    RegisterTenantUseCase
from app.shared.rbac.permissions import (Permission, Role, require_permission,
                                         require_roles)
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
def login(
    body: LoginRequest,
    db: Session = Depends(get_db),
):
    """Authenticate and receive a JWT. Works for all roles including SuperAdmin."""
    try:
        return LoginUseCase(db).execute(body)
    except ValueError as e:
        # Always 401 for auth failures — never 404 (prevents user enumeration)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.get("/me", response_model=UserResponse)
def me(ctx: TenantContext = Depends(get_tenant_context)):
    """Returns current user profile decoded from JWT. No DB query."""
    return MeUseCase.execute(ctx)


@router.post(
    "/register",
    response_model=RegisterTenantResponse,
    status_code=201,
    dependencies=[Depends(require_roles(Role.SUPER_ADMIN))],
)
def register_tenant(
    body: RegisterTenantRequest,
    db: Session = Depends(get_db),
):
    """
    Register a new tenant company + Owner user. SuperAdmin only.
    Creates both atomically — either both succeed or neither does.
    """
    try:
        return RegisterTenantUseCase(db).execute(body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.post(
    "/users",
    response_model=UserResponse,
    status_code=201,
    dependencies=[Depends(require_permission(Permission.MANAGE_USERS))],
)
def create_user(
    body: CreateUserRequest,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    """Create a new user in the current tenant. Owner/Admin only."""
    try:
        return CreateUserUseCase(db, ctx.tenant_id).execute(body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.get(
    "/users",
    response_model=UserListResponse,
    dependencies=[Depends(require_permission(Permission.MANAGE_USERS))],
)
def list_users(
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    """List all users in the current tenant. Owner/Admin only."""
    from app.modules.tenants.infrastructure.repository import UserRepository
    users = UserRepository(db).get_by_tenant(ctx.tenant_id)
    return UserListResponse(
        users=[
            UserResponse(
                id=u.id, email=u.email, full_name=u.full_name,
                role=u.role, is_active=u.is_active, tenant_id=u.tenant_id,
            )
            for u in users
        ],
        total=len(users),
    )


@router.put(
    "/users/{user_id}/deactivate",
    response_model=UserResponse,
    dependencies=[Depends(require_permission(Permission.MANAGE_USERS))],
)
def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    """Deactivate a user. Owner/Admin only. Cannot deactivate yourself."""
    from app.modules.tenants.infrastructure.repository import UserRepository
    repo = UserRepository(db)

    if user_id == ctx.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account.",
        )

    user = repo.get_by_id(user_id)
    if not user or user.tenant_id != ctx.tenant_id:
        raise HTTPException(status_code=404, detail="User not found.")

    repo.deactivate(user_id)
    db.commit()

    user.is_active = False
    return UserResponse(
        id=user.id, email=user.email, full_name=user.full_name,
        role=user.role, is_active=False, tenant_id=user.tenant_id,
    )
