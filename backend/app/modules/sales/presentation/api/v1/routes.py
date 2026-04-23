"""
modules/sales/presentation/api/v1/routes.py
=============================================
Sales API endpoints — full flow.

  POST /sales/orders              → create (DRAFT)
  POST /sales/orders/{id}/confirm → confirm + reserve stock
  POST /sales/orders/{id}/cancel  → cancel + release reservation
  POST /sales/surat-jalan         → issue SJ → fulfill + deduct stock
  POST /sales/invoices            → create invoice
  POST /sales/payments            → record payment
  GET  /sales/orders              → list
  GET  /sales/orders/{id}         → detail
  GET  /sales/invoices            → list
"""

from app.core.dependencies import TenantContext, get_db, get_tenant_context
from app.modules.sales.application.schemas import (CreateInvoiceRequest,
                                                   CreateSalesOrderRequest,
                                                   InvoiceResponse,
                                                   IssueSuratJalanRequest,
                                                   PaymentResponse,
                                                   RecordPaymentRequest,
                                                   SalesOrderResponse,
                                                   SuratJalanResponse)
from app.modules.sales.application.use_cases.cancel_sales_order import \
    CancelSalesOrderUseCase
from app.modules.sales.application.use_cases.confirm_sales_order import \
    ConfirmSalesOrderUseCase
from app.modules.sales.application.use_cases.create_invoice import \
    CreateInvoiceUseCase
from app.modules.sales.application.use_cases.create_sales_order import \
    CreateSalesOrderUseCase
from app.modules.sales.application.use_cases.issue_surat_jalan import \
    IssueSuratJalanUseCase
from app.modules.sales.application.use_cases.record_payment import \
    RecordPaymentUseCase
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

router = APIRouter()


# ─── Sales Orders ─────────────────────────────────────────────────────────────

@router.post("/orders", response_model=SalesOrderResponse, status_code=201)
def create_sales_order(
    body: CreateSalesOrderRequest,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    """Create a new sales order in DRAFT status."""
    use_case = CreateSalesOrderUseCase(db, ctx.tenant_id, ctx.user_id)
    result = use_case.execute(body)
    db.commit()
    return result


@router.post("/orders/{order_id}/confirm", response_model=SalesOrderResponse)
def confirm_sales_order(
    order_id: int,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    """
    Confirm order. Checks ALL stock shortages upfront.
    Returns 422 with detailed shortage list if any item is short.
    On success: fires StockReservedEvent → Inventory reserves stock.
    """
    try:
        use_case = ConfirmSalesOrderUseCase(db, ctx.tenant_id, ctx.user_id)
        result = use_case.execute(order_id)
        db.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.post("/orders/{order_id}/cancel", response_model=SalesOrderResponse)
def cancel_sales_order(
    order_id: int,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    """
    Cancel order.
    CONFIRMED → also fires StockReservationReleasedEvent.
    FULFILLED → blocked, returns 422.
    """
    try:
        use_case = CancelSalesOrderUseCase(db, ctx.tenant_id, ctx.user_id)
        result = use_case.execute(order_id)
        db.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.get("/orders", response_model=list[SalesOrderResponse])
def list_sales_orders(
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    from decimal import Decimal

    from app.modules.sales.domain.entities import SalesOrderStatus
    from app.modules.sales.infrastructure.models import SalesOrderModel
    from app.modules.sales.infrastructure.repository import SalesRepository

    rows = db.query(SalesOrderModel).filter(
        SalesOrderModel.tenant_id == ctx.tenant_id
    ).order_by(SalesOrderModel.order_date.desc()).limit(100).all()

    return [
        SalesOrderResponse(
            id=r.id, order_number=r.order_number, customer_id=r.customer_id,
            status=SalesOrderStatus(r.status),
            subtotal=Decimal("0"), tax_amount=Decimal("0"), total_amount=Decimal("0"),
            order_date=r.order_date, notes=r.notes,
        )
        for r in rows
    ]


@router.get("/orders/{order_id}", response_model=SalesOrderResponse)
def get_sales_order(
    order_id: int,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    from app.modules.sales.infrastructure.repository import SalesRepository
    order = SalesRepository(db, ctx.tenant_id).get_sales_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail=f"SalesOrder {order_id} not found")
    return SalesOrderResponse.model_validate(order)


# ─── Surat Jalan ──────────────────────────────────────────────────────────────

@router.post("/surat-jalan", response_model=SuratJalanResponse, status_code=201)
def issue_surat_jalan(
    body: IssueSuratJalanRequest,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    """
    Issue Surat Jalan. Goods physically leave the warehouse.
    Fires OrderFulfilledEvent → deducts stock + releases reservation.
    SalesOrder → FULFILLED.
    """
    try:
        use_case = IssueSuratJalanUseCase(db, ctx.tenant_id, ctx.user_id)
        result = use_case.execute(body)
        db.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


# ─── Invoices ─────────────────────────────────────────────────────────────────

@router.post("/invoices", response_model=InvoiceResponse, status_code=201)
def create_invoice(
    body: CreateInvoiceRequest,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    """Create invoice. SalesOrder must be FULFILLED."""
    try:
        use_case = CreateInvoiceUseCase(db, ctx.tenant_id, ctx.user_id)
        result = use_case.execute(body)
        db.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.get("/invoices", response_model=list[InvoiceResponse])
def list_invoices(
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    from app.modules.sales.infrastructure.models import InvoiceModel
    from app.modules.sales.infrastructure.repository import SalesRepository
    rows = db.query(InvoiceModel).filter(
        InvoiceModel.tenant_id == ctx.tenant_id
    ).order_by(InvoiceModel.issue_date.desc()).limit(100).all()
    repo = SalesRepository(db, ctx.tenant_id)
    return [repo._row_to_invoice(r) for r in rows]


# ─── Payments ─────────────────────────────────────────────────────────────────

@router.post("/payments", response_model=PaymentResponse, status_code=201)
def record_payment(
    body: RecordPaymentRequest,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    """Record payment. Marks invoice as PAID."""
    try:
        use_case = RecordPaymentUseCase(db, ctx.tenant_id, ctx.user_id)
        result = use_case.execute(body)
        db.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
