"""
Marketplace engine — product/service listings, reviews, and ratings.
"""

from __future__ import annotations

from app.commerce import repository as commerce_repo


def list_catalog(company_id: int, listing_type: str | None = None) -> list[dict]:
    products = commerce_repo.list_products(company_id, listing_type)
    enriched = []
    for p in products:
        rating = commerce_repo.product_avg_rating(company_id, p["id"])
        enriched.append({**p, **rating})
    return enriched


def create_listing(company_id: int, data: dict, user_id: int | None = None) -> dict:
    if not data.get("name"):
        raise ValueError("Listing name is required")
    product = commerce_repo.create_product(company_id, data)
    commerce_repo.log_commerce_action(
        company_id, "marketplace.listing.create", user_id, data.get("name", "")
    )
    return {**product, "avg_rating": 0, "review_count": 0}


def submit_review(
    company_id: int,
    product_id: int,
    customer_name: str,
    rating: int,
    comment: str = "",
    user_id: int | None = None,
) -> dict:
    product = commerce_repo.get_product(company_id, product_id)
    if not product:
        raise ValueError("Product not found")
    review = commerce_repo.add_review(company_id, product_id, customer_name, rating, comment)
    commerce_repo.log_commerce_action(
        company_id, "marketplace.review", user_id, f"product={product_id} rating={rating}"
    )
    return review


def product_detail(company_id: int, product_id: int) -> dict:
    product = commerce_repo.get_product(company_id, product_id)
    if not product:
        raise ValueError("Product not found")
    reviews = commerce_repo.list_reviews(company_id, product_id)
    rating = commerce_repo.product_avg_rating(company_id, product_id)
    return {**product, **rating, "reviews": reviews}


def marketplace_summary(company_id: int) -> dict:
    products = commerce_repo.list_products(company_id, "product")
    services = commerce_repo.list_products(company_id, "service")
    all_reviews = commerce_repo.list_reviews(company_id)
    avg = (
        round(sum(r.get("rating", 0) for r in all_reviews) / len(all_reviews), 2)
        if all_reviews else 0
    )
    return {
        "product_count": len(products),
        "service_count": len(services),
        "total_listings": len(products) + len(services),
        "review_count": len(all_reviews),
        "average_rating": avg,
        "low_stock": [p for p in products if p.get("stock", 0) < 5],
    }
