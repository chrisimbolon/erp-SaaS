"""add goods_receipt_items table

Revision ID: 2026_04_21_004
Revises: 2026_04_21_003
Create Date: 2026-04-21
"""
from alembic import op
import sqlalchemy as sa

revision = "2026_04_21_004"
down_revision = "2026_04_21_003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "goods_receipt_items",
        sa.Column("id",                     sa.Integer(),      primary_key=True),
        sa.Column("tenant_id",              sa.Integer(),      nullable=False, index=True),
        sa.Column("goods_receipt_id",       sa.Integer(),
                  sa.ForeignKey("goods_receipts.id"), nullable=False, index=True),
        sa.Column("purchase_order_item_id", sa.Integer(),
                  sa.ForeignKey("purchase_order_items.id"), nullable=False),
        sa.Column("product_id",             sa.Integer(),      nullable=False, index=True),
        sa.Column("quantity_received",      sa.Numeric(12, 3), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("goods_receipt_items")
