"""
modules/inventory/infrastructure/repository.py
================================================
All DB operations for the Inventory module.
Follows hr-app pattern: repository.py for writes, queries.py for reads.

Key methods:
  get_product()            → load Product entity
  get_current_stock()      → raw stock number
  get_available_stock()    → current_stock - active reservations (for SO confirm check)
  save_movement()          → write StockMovement row
  update_product_stock()   → update product.current_stock
  create_reservation()     → soft-lock stock for a sales order
  release_reservations()   → deactivate reservations on SO cancel
  deduct_and_release()     → stock OUT + release reservation atomically (on SJ issued)
"""

from decimal import Decimal
from typing import Optional

from app.modules.inventory.domain.entities import Product, StockMovement
from sqlalchemy import func
from sqlalchemy.orm import Session


class InventoryRepository:

    def __init__(self, db: Session, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id

    # ── Product ───────────────────────────────────────────────────────────────

    def get_product(self, product_id: int) -> Optional[Product]:
        from app.modules.inventory.infrastructure.models import ProductModel
        row = self.db.query(ProductModel).filter(
            ProductModel.id == product_id,
            ProductModel.tenant_id == self.tenant_id,
        ).first()
        if not row:
            return None
        return Product(
            id=row.id, tenant_id=row.tenant_id, sku=row.sku, name=row.name,
            unit=row.unit, current_stock=row.current_stock,
            minimum_stock=row.minimum_stock, cost_price=row.cost_price,
            sell_price=row.sell_price, category_id=row.category_id,
            is_active=row.is_active,
        )

    def get_current_stock(self, product_id: int) -> Decimal:
        from app.modules.inventory.infrastructure.models import ProductModel
        val = self.db.query(ProductModel.current_stock).filter(
            ProductModel.id == product_id,
            ProductModel.tenant_id == self.tenant_id,
        ).scalar()
        return val or Decimal("0")

    def get_available_stock(self, product_id: int) -> Decimal:
        """
        Available = current_stock − active reservations.
        This is what we check before confirming a SalesOrder.
        """
        from app.modules.inventory.infrastructure.models import (
            ProductModel, StockReservationModel)
        current = self.get_current_stock(product_id)

        reserved = self.db.query(
            func.coalesce(func.sum(StockReservationModel.quantity_reserved), 0)
        ).filter(
            StockReservationModel.product_id == product_id,
            StockReservationModel.tenant_id == self.tenant_id,
            StockReservationModel.is_active == True,
        ).scalar()

        return current - Decimal(str(reserved))

    def get_available_stock_bulk(self, product_ids: list[int]) -> dict[int, Decimal]:
        """
        Batch version — gets available stock for multiple products at once.
        Used in SalesOrderPolicy.validate_stock_availability().
        """
        return {pid: self.get_available_stock(pid) for pid in product_ids}

    def update_product_stock(self, product_id: int, new_stock: Decimal) -> None:
        from app.modules.inventory.infrastructure.models import ProductModel
        self.db.query(ProductModel).filter(
            ProductModel.id == product_id,
            ProductModel.tenant_id == self.tenant_id,
        ).update({"current_stock": new_stock})

    # ── Stock Movements ───────────────────────────────────────────────────────

    def save_movement(self, movement: StockMovement) -> StockMovement:
        from app.modules.inventory.infrastructure.models import \
            StockMovementModel
        row = StockMovementModel(
            tenant_id=movement.tenant_id,
            product_id=movement.product_id,
            movement_type=movement.movement_type.value,
            quantity=movement.quantity,
            stock_before=movement.stock_before,
            stock_after=movement.stock_after,
            reference_type=movement.reference_type,
            reference_id=movement.reference_id,
            reference_number=movement.reference_number,
            movement_date=movement.movement_date,
            notes=movement.notes,
        )
        self.db.add(row)
        self.db.flush()
        movement.id = row.id
        return movement

    # ── Reservations ──────────────────────────────────────────────────────────

    def create_reservation(
        self,
        product_id: int,
        sales_order_id: int,
        order_number: str,
        quantity: Decimal,
    ) -> None:
        """
        Create an active stock reservation for a sales order line.
        Called when SalesOrder is CONFIRMED.
        """
        from app.modules.inventory.infrastructure.models import \
            StockReservationModel
        reservation = StockReservationModel(
            tenant_id=self.tenant_id,
            product_id=product_id,
            sales_order_id=sales_order_id,
            order_number=order_number,
            quantity_reserved=quantity,
            is_active=True,
        )
        self.db.add(reservation)
        self.db.flush()

    def release_reservations(self, sales_order_id: int) -> None:
        """
        Deactivate all reservations for a sales order.
        Called when SalesOrder is CANCELLED.
        """
        from app.modules.inventory.infrastructure.models import \
            StockReservationModel
        self.db.query(StockReservationModel).filter(
            StockReservationModel.sales_order_id == sales_order_id,
            StockReservationModel.tenant_id == self.tenant_id,
            StockReservationModel.is_active == True,
        ).update({"is_active": False})

    def deduct_and_release(
        self,
        product_id: int,
        sales_order_id: int,
        quantity: Decimal,
    ) -> tuple[Decimal, Decimal]:
        """
        Atomic operation on Surat Jalan issue:
          1. Deduct quantity from current_stock
          2. Release reservation for this product/order

        Returns (stock_before, stock_after).
        Called by StockOutUseCase — not directly by routes.
        """
        current = self.get_current_stock(product_id)
        new_stock = current - quantity

        if new_stock < 0:
            raise ValueError(
                f"Stock would go negative for product {product_id}. "
                f"Current: {current}, Deducting: {quantity}"
            )

        self.update_product_stock(product_id, new_stock)
        self.release_reservations_for_product(product_id, sales_order_id, quantity)

        return current, new_stock

    def release_reservations_for_product(
        self,
        product_id: int,
        sales_order_id: int,
        quantity: Decimal,
    ) -> None:
        """Release reservation for a specific product within a sales order."""
        from app.modules.inventory.infrastructure.models import \
            StockReservationModel
        self.db.query(StockReservationModel).filter(
            StockReservationModel.product_id == product_id,
            StockReservationModel.sales_order_id == sales_order_id,
            StockReservationModel.tenant_id == self.tenant_id,
            StockReservationModel.is_active == True,
        ).update({"is_active": False})
