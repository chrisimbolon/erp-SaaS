"""
modules/purchase/application/schemas.py
"""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from app.modules.purchase.domain.entities import GoodsReceiptStatus, POStatus
from pydantic import BaseModel, Field


class PurchaseOrderItemIn(BaseModel):
    product_id: int
    product_name: str
    quantity_ordered: Decimal = Field(gt=0)
    unit_price: Decimal = Field(gt=0)
    unit: str

class CreatePurchaseOrderRequest(BaseModel):
    supplier_id: int
    items: List[PurchaseOrderItemIn]
    expected_delivery: Optional[datetime] = None
    notes: Optional[str] = None

class PurchaseOrderResponse(BaseModel):
    id: int
    po_number: str
    status: POStatus
    order_date: datetime
    model_config = {"from_attributes": True}

class ReceiveGoodsItemIn(BaseModel):
    product_id: int
    quantity_received: Decimal = Field(gt=0)
    purchase_order_item_id: int

class ReceiveGoodsRequest(BaseModel):
    purchase_order_id: int
    items: List[ReceiveGoodsItemIn]
    notes: Optional[str] = None

class GoodsReceiptResponse(BaseModel):
    id: int
    receipt_number: str
    status: GoodsReceiptStatus
    received_date: datetime
    model_config = {"from_attributes": True}
