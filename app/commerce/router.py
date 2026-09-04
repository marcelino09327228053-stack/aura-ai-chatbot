"""Aura Global Commerce Network API routes."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.deps import require_auth
from app.commerce import repository as commerce_repo
from app.commerce.analytics import engine as analytics_engine
from app.commerce.contracts import engine as contracts_engine
from app.commerce.logistics import engine as logistics_engine
from app.commerce.marketplace import engine as marketplace_engine
from app.commerce.payments import engine as payments_engine

router = APIRouter(prefix="/commerce", tags=["commerce"])


# ── Request models ────────────────────────────────────────────────────────────

class ListingRequest(BaseModel):
    listing_type: str = "product"
    name: str
    description: str = ""
    price: float = 0
    currency: str = "PHP"
    category: str = "general"
    stock: int = 0


class ReviewRequest(BaseModel):
    product_id: int
    customer_name: str
    rating: int = 5
    comment: str = ""


class OrderRequest(BaseModel):
    customer_name: str
    customer_email: str = ""
    items: list[dict]
    tax_rate: float = 0.12


class PaymentRequest(BaseModel):
    amount: float
    order_id: int | None = None
    method: str = "online"
    currency: str = "PHP"
    customer_email: str = ""


class ShipmentRequest(BaseModel):
    order_id: int
    carrier: str = "standard"
    origin: str = ""
    destination: str = ""


class DeliveryUpdateRequest(BaseModel):
    tracking_number: str
    status: str


class WarehouseRequest(BaseModel):
    name: str
    location: str = ""
    capacity: int = 1000
    current_stock: int = 0


class SubscriptionRequest(BaseModel):
    customer_name: str
    plan_name: str
    amount: float
    billing_cycle: str = "monthly"


class ContractRequest(BaseModel):
    template_type: str = "service"
    parties: list[str] = []
    renewal_months: int = 12
    custom_title: str = ""


class InvoiceFromOrderRequest(BaseModel):
    order_id: int


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard")
def commerce_dashboard(ctx=Depends(require_auth)):
    commerce_repo.log_commerce_action(ctx.company_id, "dashboard.view", ctx.user_id)
    return {
        "marketplace": marketplace_engine.marketplace_summary(ctx.company_id),
        "sales": analytics_engine.sales_performance(ctx.company_id),
        "logistics": logistics_engine.delivery_management(ctx.company_id),
        "payments": payments_engine.financial_records(ctx.company_id),
        "contracts": contracts_engine.contract_summary(ctx.company_id),
    }


# ── Products / Marketplace ────────────────────────────────────────────────────

@router.get("/products")
def get_products(listing_type: str | None = None, ctx=Depends(require_auth)):
    """List product and service catalogue with ratings."""
    return marketplace_engine.list_catalog(ctx.company_id, listing_type)


@router.post("/products")
def create_product(body: ListingRequest, ctx=Depends(require_auth)):
    try:
        return marketplace_engine.create_listing(ctx.company_id, body.model_dump(), ctx.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/products/{product_id}")
def get_product(product_id: int, ctx=Depends(require_auth)):
    try:
        return marketplace_engine.product_detail(ctx.company_id, product_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/reviews")
def add_review(body: ReviewRequest, ctx=Depends(require_auth)):
    try:
        return marketplace_engine.submit_review(
            ctx.company_id,
            body.product_id,
            body.customer_name,
            body.rating,
            body.comment,
            ctx.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/reviews")
def list_reviews(product_id: int | None = None, ctx=Depends(require_auth)):
    return commerce_repo.list_reviews(ctx.company_id, product_id)


# ── Orders ────────────────────────────────────────────────────────────────────

@router.get("/orders")
def get_orders(status: str | None = None, ctx=Depends(require_auth)):
    return commerce_repo.list_orders(ctx.company_id, status)


@router.post("/orders")
def create_order(body: OrderRequest, ctx=Depends(require_auth)):
    if not body.items:
        raise HTTPException(status_code=400, detail="Order must include at least one item")
    order = commerce_repo.create_order(ctx.company_id, body.model_dump())
    commerce_repo.log_commerce_action(
        ctx.company_id, "order.create", ctx.user_id, order["order_number"]
    )
    return order


@router.get("/orders/{order_id}")
def get_order(order_id: int, ctx=Depends(require_auth)):
    order = commerce_repo.get_order(ctx.company_id, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


# ── Payments ──────────────────────────────────────────────────────────────────

@router.post("/payments")
def process_payment(body: PaymentRequest, ctx=Depends(require_auth)):
    """Process an online payment with fraud detection."""
    try:
        return payments_engine.process_payment(ctx.company_id, body.model_dump(), ctx.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/payments")
def list_payments(ctx=Depends(require_auth)):
    return commerce_repo.list_payments(ctx.company_id)


@router.post("/payments/invoice")
def generate_invoice(body: InvoiceFromOrderRequest, ctx=Depends(require_auth)):
    try:
        return payments_engine.generate_invoice_for_order(ctx.company_id, body.order_id, ctx.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/payments/invoices")
def list_invoices(ctx=Depends(require_auth)):
    return commerce_repo.list_invoices(ctx.company_id)


@router.post("/payments/subscriptions")
def create_subscription(body: SubscriptionRequest, ctx=Depends(require_auth)):
    try:
        return payments_engine.create_subscription_billing(ctx.company_id, body.model_dump(), ctx.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/payments/subscriptions")
def list_subscriptions(ctx=Depends(require_auth)):
    return commerce_repo.list_subscriptions(ctx.company_id)


@router.get("/payments/records")
def financial_records(ctx=Depends(require_auth)):
    return payments_engine.financial_records(ctx.company_id)


# ── Logistics ─────────────────────────────────────────────────────────────────

@router.post("/logistics/shipments")
def create_shipment(body: ShipmentRequest, ctx=Depends(require_auth)):
    try:
        return logistics_engine.create_shipment_for_order(
            ctx.company_id, body.order_id, body.model_dump(), ctx.user_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/logistics/shipments")
def list_shipments(status: str | None = None, ctx=Depends(require_auth)):
    return commerce_repo.list_shipments(ctx.company_id, status)


@router.get("/logistics/track/{tracking_number}")
def track_shipment(tracking_number: str, ctx=Depends(require_auth)):
    try:
        return logistics_engine.track_shipment(ctx.company_id, tracking_number)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/logistics/delivery")
def update_delivery(body: DeliveryUpdateRequest, ctx=Depends(require_auth)):
    try:
        return logistics_engine.update_delivery(
            ctx.company_id, body.tracking_number, body.status, ctx.user_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/logistics/warehouses")
def list_warehouses(ctx=Depends(require_auth)):
    return logistics_engine.warehouse_monitoring(ctx.company_id)


@router.post("/logistics/warehouses")
def create_warehouse(body: WarehouseRequest, ctx=Depends(require_auth)):
    wh = commerce_repo.create_warehouse(ctx.company_id, body.model_dump())
    commerce_repo.log_commerce_action(ctx.company_id, "warehouse.create", ctx.user_id, body.name)
    return wh


@router.post("/logistics/sync")
def sync_inventory(ctx=Depends(require_auth)):
    return logistics_engine.sync_inventory(ctx.company_id, ctx.user_id)


@router.get("/logistics/delivery")
def delivery_management(ctx=Depends(require_auth)):
    return logistics_engine.delivery_management(ctx.company_id)


# ── Contracts ─────────────────────────────────────────────────────────────────

@router.get("/contracts")
def list_contracts(archived: bool = False, ctx=Depends(require_auth)):
    return commerce_repo.list_contracts(ctx.company_id, archived)


@router.post("/contracts")
def create_contract(body: ContractRequest, ctx=Depends(require_auth)):
    try:
        return contracts_engine.create_from_template(
            ctx.company_id,
            body.template_type,
            body.parties,
            body.renewal_months,
            body.custom_title,
            ctx.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/contracts/{contract_id}/approve")
def approve_contract(contract_id: int, ctx=Depends(require_auth)):
    try:
        return contracts_engine.electronic_approve(ctx.company_id, contract_id, ctx.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/contracts/{contract_id}/archive")
def archive_contract(contract_id: int, ctx=Depends(require_auth)):
    try:
        return contracts_engine.legal_archive(ctx.company_id, contract_id, ctx.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/contracts/renewals")
def renewal_reminders(days_ahead: int = 60, ctx=Depends(require_auth)):
    return contracts_engine.renewal_reminders(ctx.company_id, days_ahead)


@router.get("/contracts/summary")
def contract_summary(ctx=Depends(require_auth)):
    return contracts_engine.contract_summary(ctx.company_id)


# ── Reports / Analytics ───────────────────────────────────────────────────────

@router.get("/reports")
def get_reports(ctx=Depends(require_auth)):
    """Full commerce analytics report."""
    return analytics_engine.full_commerce_report(ctx.company_id)


@router.get("/reports/sales")
def sales_report(ctx=Depends(require_auth)):
    return analytics_engine.sales_performance(ctx.company_id)


@router.get("/reports/customers")
def customer_report(ctx=Depends(require_auth)):
    return analytics_engine.customer_behavior(ctx.company_id)


@router.get("/reports/trends")
def trends_report(ctx=Depends(require_auth)):
    return analytics_engine.market_trends(ctx.company_id)


@router.get("/reports/revenue")
def revenue_report(ctx=Depends(require_auth)):
    return analytics_engine.revenue_report(ctx.company_id)


# ── Audit ─────────────────────────────────────────────────────────────────────

@router.get("/audit")
def audit_log(limit: int = 50, ctx=Depends(require_auth)):
    return commerce_repo.list_audit(ctx.company_id, min(limit, 100))
