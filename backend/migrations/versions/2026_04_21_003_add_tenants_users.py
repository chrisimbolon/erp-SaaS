"""add tenants and users tables

Revision ID: 2026_04_21_003
Revises: 2026_04_21_002
Create Date: 2026-04-21
"""
from alembic import op
import sqlalchemy as sa

revision = "2026_04_21_003"
down_revision = "2026_04_21_002"
branch_labels = None
depends_on = None


def upgrade() -> None:

    op.create_table("tenants",
        sa.Column("id",          sa.Integer(), primary_key=True),
        sa.Column("name",        sa.String(255), nullable=False),
        sa.Column("slug",        sa.String(100), nullable=False, unique=True),
        sa.Column("status",      sa.String(50),  nullable=False, server_default="trial"),
        sa.Column("plan",        sa.String(50),  nullable=False, server_default="starter"),
        sa.Column("owner_email", sa.String(255), nullable=False),
        sa.Column("phone",       sa.String(50),  nullable=True),
        sa.Column("address",     sa.Text(),       nullable=True),
        sa.Column("npwp",        sa.String(30),   nullable=True),
        sa.Column("logo_url",    sa.String(500),  nullable=True),
        sa.Column("created_at",  sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at",  sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table("users",
        sa.Column("id",              sa.Integer(),     primary_key=True),
        sa.Column("tenant_id",       sa.Integer(),     nullable=True, index=True),
        sa.Column("email",           sa.String(255),   nullable=False, unique=True),
        sa.Column("full_name",       sa.String(255),   nullable=False),
        sa.Column("role",            sa.String(50),    nullable=False),
        sa.Column("hashed_password", sa.String(255),   nullable=False),
        sa.Column("is_active",       sa.Boolean(),     nullable=False, server_default="true"),
        sa.Column("last_login",      sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at",      sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at",      sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # FK from users to tenants — nullable for SuperAdmin
    op.create_foreign_key(
        "fk_users_tenant_id",
        "users", "tenants",
        ["tenant_id"], ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_users_tenant_id", "users", type_="foreignkey")
    op.drop_table("users")
    op.drop_table("tenants")
