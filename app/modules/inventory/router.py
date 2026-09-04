"""Inventory API routes."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.deps import require_auth
from app.modules.inventory import repository as repo

router = APIRouter(prefix="/inventory", tags=["inventory"])


class ProductCreate(BaseModel):
    name: str
    stock: int = 0
    price: float = 0
    category_id: int | None = None


class CategoryCreate(BaseModel):
    name: str


class StockMovementCreate(BaseModel):
    product_id: int
    delta: int
    reason: str = ""


@router.get("/products")
def get_products(ctx=Depends(require_auth)):
    return repo.list_products(ctx.company_id)


@router.post("/products", status_code=201)
def post_product(body: ProductCreate, ctx=Depends(require_auth)):
    return repo.create_product(ctx.company_id, body.name, body.stock, body.price, body.category_id)


@router.get("/categories")
def get_categories(ctx=Depends(require_auth)):
    return repo.list_categories(ctx.company_id)


@router.post("/categories", status_code=201)
def post_category(body: CategoryCreate, ctx=Depends(require_auth)):
    row = repo.create_category(ctx.company_id, body.name)
    if row is None:
        raise HTTPException(status_code=409, detail="Category already exists.")
    return row


@router.get("/stock-movements")
def get_movements(ctx=Depends(require_auth)):
    return repo.list_stock_movements(ctx.company_id)


@router.post("/stock-movements", status_code=201)
def post_movement(body: StockMovementCreate, ctx=Depends(require_auth)):
    return repo.record_stock_movement(ctx.company_id, body.product_id, body.delta, body.reason)
