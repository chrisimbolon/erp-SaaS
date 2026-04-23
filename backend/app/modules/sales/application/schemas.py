"""
modules/sales/application/schemas.py
======================================
Pydantic schemas for the Sales module.
Request = what comes IN from the API.
Response = what goes OUT to the client.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from app.modules.sales.domain.entities import (InvoiceStatus, PaymentMethod,
                                               SalesOrderStatus,
                                               SuratJalanStatus)
from pydantic import BaseModel, Field

# ─── Sales Order ──────────────────────────────────────────────────────────────

class SalesOrderItemIn(BaseModel):
    product_id:   int
    product_name: str
    quantity:     Decimal = Field(gt=0)
    unit_price:   Decimal = Field(gt=0)
    unit:         str
    discount_pct: Decimal = Field(default=Decimal("0"), ge=0, le=100)


class CreateSalesOrderRequest(BaseModel):
    customer_id: int
    items:       List[SalesOrderItemIn]
    notes:       Optional[str] = None


class SalesOrderItemResponse(BaseModel):
    product_id:   int
    product_name: str
    quantity:     Decimal
    unit_price:   Decimal
    unit:         str
    discount_pct: Decimal
    subtotal:     Decimal
    model_config = {"from_attributes": True}


class SalesOrderResponse(BaseModel):
    id:           int
    order_number: str
    customer_id:  int
    status:       SalesOrderStatus
    subtotal:     Decimal
    tax_amount:   Decimal
    total_amount: Decimal
    order_date:   datetime
    notes:        Optional[str] = None
    model_config = {"from_attributes": True}


class StockShortageItem(BaseModel):
    """Returned in 422 when stock check fails on confirm."""
    product_id:   int
    product_name: str
    requested:    Decimal
    available:    Decimal
    shortage:     Decimal


# ─── Surat Jalan ──────────────────────────────────────────────────────────────

class SuratJalanItemIn(BaseModel):
    product_id:            int
    sales_order_item_id:   int
    quantity_shipped:      Decimal = Field(gt=0)
    unit:                  str


class IssueSuratJalanRequest(BaseModel):
    sales_order_id: int
    items:          List[SuratJalanItemIn]
    notes:          Optional[str] = None


class SuratJalanResponse(BaseModel):
    id:             int
    sj_number:      str
    sales_order_id: int
    status:         SuratJalanStatus
    issued_date:    Optional[datetime] = None
    notes:          Optional[str] = None
    model_config = {"from_attributes": True}


# ─── Invoice ──────────────────────────────────────────────────────────────────

class CreateInvoiceRequest(BaseModel):
    sales_order_id:      int
    payment_terms_days:  Optional[int] = 30
    notes:               Optional[str] = None


class InvoiceResponse(BaseModel):
    id:             int
    invoice_number: str
    sales_order_id: int
    customer_id:    int
    status:         InvoiceStatus
    subtotal:       Decimal
    tax_amount:     Decimal
    total_amount:   Decimal
    issue_date:     datetime
    due_date:       datetime
    notes:          Optional[str] = None
    model_config = {"from_attributes": True}


# ─── Payment ──────────────────────────────────────────────────────────────────

class RecordPaymentRequest(BaseModel):
    invoice_id:     int
    amount:         Decimal = Field(gt=0)
    payment_method: PaymentMethod
    payment_date:   Optional[datetime] = None
    reference_no:   Optional[str] = None
    notes:          Optional[str] = None


class PaymentResponse(BaseModel):
    id:             int
    payment_number: str
    invoice_id:     int
    amount:         Decimal
    payment_method: PaymentMethod
    payment_date:   datetime
    reference_no:   Optional[str] = None
    model_config = {"from_attributes": True}
