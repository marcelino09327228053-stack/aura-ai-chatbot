"""Inventory sync example plugin."""

from app.plugins.sdk.base import BasePlugin


class Plugin(BasePlugin):
    def execute(self, context, settings=None, **kwargs):
        settings = settings or {}
        profile = context.read_company_profile()
        products = context.access_inventory()

        low_stock = [p for p in products if p.get("stock", 0) < settings.get("low_stock_threshold", 5)]
        total_units = sum(p.get("stock", 0) for p in products)

        return {
            "status": "synced",
            "company": profile["company_name"],
            "product_count": len(products),
            "total_units": total_units,
            "low_stock_items": [{"name": p["name"], "stock": p["stock"]} for p in low_stock[:10]],
            "message": f"Synced {len(products)} products ({total_units} total units).",
        }
