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

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_tenant_context, TenantContext
from app.shared.rbac.permissions import require_permission, Permission
from app.modules.sales.application.schemas import (
    CreateSalesOrderRequest, SalesOrderResponse,
    IssueSuratJalanRequest, SuratJalanResponse,
    CreateInvoiceRequest, InvoiceResponse,
    RecordPaymentRequest, PaymentResponse,
)
from app.modules.sales.application.use_cases.create_sales_order import CreateSalesOrderUseCase
from app.modules.sales.application.use_cases.confirm_sales_order import ConfirmSalesOrderUseCase
from app.modules.sales.application.use_cases.cancel_sales_order import CancelSalesOrderUseCase
from app.modules.sales.application.use_cases.issue_surat_jalan import IssueSuratJalanUseCase
from app.modules.sales.application.use_cases.create_invoice import CreateInvoiceUseCase
from app.modules.sales.application.use_cases.record_payment import RecordPaymentUseCase

router = APIRouter()


# ─── Sales Orders ─────────────────────────────────────────────────────────────

@router.post(
    "/orders",
    response_model=SalesOrderResponse,
    status_code=201,
    dependencies=[Depends(require_permission(Permission.MANAGE_SALES))],
)
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


@router.post(
    "/orders/{order_id}/confirm",
    response_model=SalesOrderResponse,
    dependencies=[Depends(require_permission(Permission.MANAGE_SALES))],
)
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


@router.post(
    "/orders/{order_id}/cancel",
    response_model=SalesOrderResponse,
    dependencies=[Depends(require_permission(Permission.MANAGE_SALES))],
)
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
    from app.modules.sales.infrastructure.models import SalesOrderModel
    from app.modules.sales.infrastructure.repository import SalesRepository
    from app.modules.sales.domain.entities import SalesOrderStatus
    from decimal import Decimal

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

@router.get(
    "/orders/{order_id}/items",
    dependencies=[Depends(require_permission(Permission.VIEW_SALES))],
)
def get_sales_order_items(
    order_id: int,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    """
    Returns SO header + line items to pre-fill the Surat Jalan form.
    Called when user selects a confirmed SO in the SJ drawer.
    """
    from app.modules.sales.infrastructure.models import (
        SalesOrderModel, SalesOrderItemModel,
    )
    from sqlalchemy import text

    so = db.query(SalesOrderModel).filter(
        SalesOrderModel.id == order_id,
        SalesOrderModel.tenant_id == ctx.tenant_id,
    ).first()

    if not so:
        raise HTTPException(status_code=404, detail="Sales Order tidak ditemukan.")

    item_rows = db.query(SalesOrderItemModel).filter(
        SalesOrderItemModel.sales_order_id == order_id,
    ).all()

    # Resolve customer name
    customer_row = db.execute(
        text("SELECT name FROM customers WHERE id = :cid AND tenant_id = :tid"),
        {"cid": so.customer_id, "tid": ctx.tenant_id},
    ).fetchone()

    return {
        "so_id":         so.id,
        "order_number":  so.order_number,
        "status":        so.status,
        "customer_id":   so.customer_id,
        "customer_name": customer_row.name if customer_row else f"Customer #{so.customer_id}",
        "items": [
            {
                "id":           item.id,
                "product_id":   item.product_id,
                "product_name": item.product_name,
                "quantity":     str(item.quantity),
                "unit_price":   str(item.unit_price),
                "unit":         item.unit,
                "discount_pct": str(item.discount_pct),
            }
            for item in item_rows
        ],
    }


@router.get(
    "/surat-jalan",
    dependencies=[Depends(require_permission(Permission.VIEW_SALES))],
)
def list_surat_jalan(
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    """List all Surat Jalan for this tenant, with SO number + customer name."""
    from app.modules.sales.infrastructure.models import (
        SuratJalanModel, SalesOrderModel,
    )
    from sqlalchemy import text

    rows = db.query(SuratJalanModel).filter(
        SuratJalanModel.tenant_id == ctx.tenant_id,
    ).order_by(SuratJalanModel.issued_date.desc().nullslast()).all()

    # Batch-resolve SO numbers + customer names
    so_ids = list({r.sales_order_id for r in rows})
    so_map: dict = {}
    customer_map: dict = {}

    if so_ids:
        so_rows = db.query(SalesOrderModel).filter(
            SalesOrderModel.id.in_(so_ids),
            SalesOrderModel.tenant_id == ctx.tenant_id,
        ).all()
        so_map = {r.id: r for r in so_rows}

        cust_ids = list({r.customer_id for r in so_rows})
        if cust_ids:
            c_rows = db.execute(
                text("SELECT id, name FROM customers WHERE tenant_id = :tid"),
                {"tid": ctx.tenant_id},
            ).fetchall()
            customer_map = {r.id: r.name for r in c_rows}

    return [
        {
            "id":            r.id,
            "sj_number":     r.sj_number,
            "sales_order_id": r.sales_order_id,
            "order_number":  so_map[r.sales_order_id].order_number
                             if r.sales_order_id in so_map else f"SO #{r.sales_order_id}",
            "customer_name": customer_map.get(
                so_map[r.sales_order_id].customer_id
                if r.sales_order_id in so_map else 0, "—"
            ),
            "status":        r.status,
            "issued_date":   r.issued_date.isoformat() if r.issued_date else None,
            "notes":         r.notes,
        }
        for r in rows
    ]


@router.post(
    "/surat-jalan",
    response_model=SuratJalanResponse,
    status_code=201,
    dependencies=[Depends(require_permission(Permission.MANAGE_SALES))],
)
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

@router.get(
    "/fulfilled-orders",
    dependencies=[Depends(require_permission(Permission.VIEW_INVOICES))],
)
def list_fulfilled_orders_without_invoice(
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    """
    Returns fulfilled SOs that don't yet have an invoice.
    Used to populate the dropdown in the Create Invoice drawer.
    """
    from app.modules.sales.infrastructure.models import SalesOrderModel, InvoiceModel
    from sqlalchemy import text

    invoiced_so_ids = db.query(InvoiceModel.sales_order_id).filter(
        InvoiceModel.tenant_id == ctx.tenant_id,
    ).scalar_subquery()

    rows = db.query(SalesOrderModel).filter(
        SalesOrderModel.tenant_id == ctx.tenant_id,
        SalesOrderModel.status == "fulfilled",
        SalesOrderModel.id.notin_(invoiced_so_ids),
    ).order_by(SalesOrderModel.order_date.desc()).all()

    cust_ids = list({r.customer_id for r in rows})
    cust_map: dict = {}
    if cust_ids:
        c_rows = db.execute(
            text("SELECT id, name FROM customers WHERE tenant_id = :tid"),
            {"tid": ctx.tenant_id},
        ).fetchall()
        cust_map = {r.id: r.name for r in c_rows}

    return [
        {
            "id":            r.id,
            "order_number":  r.order_number,
            "customer_id":   r.customer_id,
            "customer_name": cust_map.get(r.customer_id, f"Customer #{r.customer_id}"),
            "order_date":    r.order_date.isoformat(),
        }
        for r in rows
    ]


@router.post(
    "/invoices",
    response_model=InvoiceResponse,
    status_code=201,
    dependencies=[Depends(require_permission(Permission.MANAGE_INVOICES))],
)
def create_invoice(
    body: CreateInvoiceRequest,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    """Create invoice for a fulfilled SO. One invoice per SO enforced."""
    try:
        use_case = CreateInvoiceUseCase(db, ctx.tenant_id, ctx.user_id)
        result = use_case.execute(body)
        db.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.get(
    "/invoices",
    response_model=list[InvoiceResponse],
    dependencies=[Depends(require_permission(Permission.VIEW_INVOICES))],
)
def list_invoices(
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    """List all invoices with SO number and customer name resolved."""
    from app.modules.sales.infrastructure.models import (
        InvoiceModel, SalesOrderModel,
    )
    from app.modules.sales.domain.entities import InvoiceStatus
    from sqlalchemy import text

    rows = db.query(InvoiceModel).filter(
        InvoiceModel.tenant_id == ctx.tenant_id,
    ).order_by(InvoiceModel.issue_date.desc()).limit(100).all()

    so_ids = list({r.sales_order_id for r in rows})
    so_map: dict = {}
    cust_map: dict = {}

    if so_ids:
        so_rows = db.query(SalesOrderModel).filter(
            SalesOrderModel.id.in_(so_ids),
        ).all()
        so_map = {r.id: r for r in so_rows}
        cust_ids = list({r.customer_id for r in so_rows})
        if cust_ids:
            c_rows = db.execute(
                text("SELECT id, name FROM customers WHERE tenant_id = :tid"),
                {"tid": ctx.tenant_id},
            ).fetchall()
            cust_map = {r.id: r.name for r in c_rows}

    return [
        InvoiceResponse(
            id=r.id,
            invoice_number=r.invoice_number,
            sales_order_id=r.sales_order_id,
            order_number=so_map[r.sales_order_id].order_number if r.sales_order_id in so_map else None,
            customer_id=r.customer_id,
            customer_name=cust_map.get(
                so_map[r.sales_order_id].customer_id if r.sales_order_id in so_map else 0, "—"
            ),
            status=InvoiceStatus(r.status),
            subtotal=r.subtotal,
            tax_amount=r.tax_amount,
            total_amount=r.total_amount,
            issue_date=r.issue_date,
            due_date=r.due_date,
            notes=r.notes,
        )
        for r in rows
    ]


# ─── Payments ─────────────────────────────────────────────────────────────────

@router.get(
    "/unpaid-invoices",
    dependencies=[Depends(require_permission(Permission.MANAGE_PAYMENTS))],
)
def list_unpaid_invoices(
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    """
    Returns sent/overdue invoices that haven't been paid yet.
    Used to populate the dropdown in the Record Payment drawer.
    """
    from app.modules.sales.infrastructure.models import InvoiceModel, SalesOrderModel
    from sqlalchemy import text

    rows = db.query(InvoiceModel).filter(
        InvoiceModel.tenant_id == ctx.tenant_id,
        InvoiceModel.status.in_(["sent", "overdue"]),
    ).order_by(InvoiceModel.due_date.asc()).all()

    # Resolve customer names
    so_ids = list({r.sales_order_id for r in rows})
    so_map: dict = {}
    cust_map: dict = {}
    if so_ids:
        so_rows = db.query(SalesOrderModel).filter(
            SalesOrderModel.id.in_(so_ids),
        ).all()
        so_map = {r.id: r for r in so_rows}
        cust_ids = list({r.customer_id for r in so_rows})
        if cust_ids:
            c_rows = db.execute(
                text("SELECT id, name FROM customers WHERE tenant_id = :tid"),
                {"tid": ctx.tenant_id},
            ).fetchall()
            cust_map = {r.id: r.name for r in c_rows}

    return [
        {
            "id":             r.id,
            "invoice_number": r.invoice_number,
            "customer_name":  cust_map.get(
                so_map[r.sales_order_id].customer_id
                if r.sales_order_id in so_map else 0, "—"
            ),
            "total_amount":   str(r.total_amount),
            "due_date":       r.due_date.isoformat(),
            "status":         r.status,
        }
        for r in rows
    ]


@router.get(
    "/payments",
    response_model=list[PaymentResponse],
    dependencies=[Depends(require_permission(Permission.MANAGE_PAYMENTS))],
)
def list_payments(
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    """List all payments with invoice number and customer name resolved."""
    from app.modules.sales.infrastructure.models import (
        PaymentModel, InvoiceModel, SalesOrderModel,
    )
    from app.modules.sales.domain.entities import PaymentMethod
    from sqlalchemy import text

    rows = db.query(PaymentModel).filter(
        PaymentModel.tenant_id == ctx.tenant_id,
    ).order_by(PaymentModel.payment_date.desc()).limit(100).all()

    # Batch-resolve invoice numbers + customer names
    inv_ids = list({r.invoice_id for r in rows})
    inv_map: dict = {}
    so_map: dict = {}
    cust_map: dict = {}

    if inv_ids:
        inv_rows = db.query(InvoiceModel).filter(
            InvoiceModel.id.in_(inv_ids),
        ).all()
        inv_map = {r.id: r for r in inv_rows}

        so_ids = list({r.sales_order_id for r in inv_rows})
        if so_ids:
            so_rows = db.query(SalesOrderModel).filter(
                SalesOrderModel.id.in_(so_ids),
            ).all()
            so_map = {r.id: r for r in so_rows}

            cust_ids = list({r.customer_id for r in so_rows})
            if cust_ids:
                c_rows = db.execute(
                    text("SELECT id, name FROM customers WHERE tenant_id = :tid"),
                    {"tid": ctx.tenant_id},
                ).fetchall()
                cust_map = {r.id: r.name for r in c_rows}

    def resolve_customer(invoice_id: int) -> str:
        inv = inv_map.get(invoice_id)
        if not inv:
            return "—"
        so = so_map.get(inv.sales_order_id)
        if not so:
            return "—"
        return cust_map.get(so.customer_id, "—")

    return [
        PaymentResponse(
            id=r.id,
            payment_number=r.payment_number,
            invoice_id=r.invoice_id,
            invoice_number=inv_map[r.invoice_id].invoice_number if r.invoice_id in inv_map else None,
            customer_name=resolve_customer(r.invoice_id),
            amount=r.amount,
            payment_method=PaymentMethod(r.payment_method),
            payment_date=r.payment_date,
            reference_no=r.reference_no,
            notes=r.notes,
        )
        for r in rows
    ]


@router.post(
    "/payments",
    response_model=PaymentResponse,
    status_code=201,
    dependencies=[Depends(require_permission(Permission.MANAGE_PAYMENTS))],
)
def record_payment(
    body: RecordPaymentRequest,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    """Record payment against an invoice. Marks invoice as PAID."""
    try:
        use_case = RecordPaymentUseCase(db, ctx.tenant_id, ctx.user_id)
        result = use_case.execute(body)
        db.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
