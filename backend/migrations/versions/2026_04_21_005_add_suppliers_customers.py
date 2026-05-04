"""add suppliers and customers tables

Revision ID: 2026_04_21_005
Revises: 2026_04_21_004
Create Date: 2026-04-21

NOTE: suppliers and customers were previously created inline in seed_dev.py
using CREATE TABLE IF NOT EXISTS. This migration formalises them so fresh
deployments work without running the seed script first.
"""
from alembic import op
import sqlalchemy as sa

revision = "2026_04_21_005"
down_revision = "2026_04_21_004"
branch_labels = None
depends_on = None


def upgrade() -> None:

    op.create_table(
        "suppliers",
        sa.Column("id",         sa.Integer(),     primary_key=True),
        sa.Column("tenant_id",  sa.Integer(),     nullable=False, index=True),
        sa.Column("name",       sa.String(255),   nullable=False),
        sa.Column("contact",    sa.String(255),   nullable=True),
        sa.Column("phone",      sa.String(50),    nullable=True),
        sa.Column("email",      sa.String(255),   nullable=True),
        sa.Column("address",    sa.Text(),         nullable=True),
        sa.Column("npwp",       sa.String(30),    nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "customers",
        sa.Column("id",           sa.Integer(),     primary_key=True),
        sa.Column("tenant_id",    sa.Integer(),     nullable=False, index=True),
        sa.Column("name",         sa.String(255),   nullable=False),
        sa.Column("contact",      sa.String(255),   nullable=True),
        sa.Column("phone",        sa.String(50),    nullable=True),
        sa.Column("email",        sa.String(255),   nullable=True),
        sa.Column("address",      sa.Text(),         nullable=True),
        sa.Column("npwp",         sa.String(30),    nullable=True),
        sa.Column("credit_limit", sa.Numeric(15, 2), server_default="50000000"),
        sa.Column("created_at",   sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at",   sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("customers")
    op.drop_table("suppliers")
