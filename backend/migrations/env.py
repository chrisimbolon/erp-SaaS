"""
migrations/env.py
==================
Alembic migration environment.
Reads DATABASE_URL from .env so you never hardcode credentials.
Sets search_path to 'public' explicitly so all tables land there.
"""

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool, text

# Load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
except ImportError:
    pass

config = context.config

# Override sqlalchemy.url from environment variable
database_url = os.environ.get("DATABASE_URL")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

from app.modules.inventory.infrastructure.models import (ProductModel,
                                                         StockMovementModel,
                                                         StockReservationModel)
from app.modules.purchase.infrastructure.models import (GoodsReceiptItemModel,
                                                        GoodsReceiptModel,
                                                        PurchaseOrderItemModel,
                                                        PurchaseOrderModel)
from app.modules.sales.infrastructure.models import (InvoiceModel,
                                                     PaymentModel,
                                                     SalesOrderItemModel,
                                                     SalesOrderModel,
                                                     SuratJalanItemModel,
                                                     SuratJalanModel)
from app.modules.tenants.infrastructure.models import TenantModel, UserModel
# Import all models so Alembic sees them for autogenerate
from app.shared.models.base import Base

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Force public schema
        include_schemas=False,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # Force public schema so tables don't land in 'core' or other schemas
        connection.execute(text("SET search_path TO public"))

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=False,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
