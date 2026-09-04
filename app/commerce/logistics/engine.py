"""
Logistics system — shipments, delivery, warehouses, inventory sync.
"""

from __future__ import annotations

from app.commerce import repository as commerce_repo
from app.modules.inventory import repository as inventory_repo


SHIPMENT_STATUSES = ["pending", "picked_up", "in_transit", "out_for_delivery", "delivered", "cancelled"]


def create_shipment_for_order(company_id: int, order_id: int, data: dict, user_id: int | None = None) -> dict:
    order = commerce_repo.get_order(company_id, order_id)
    if not order:
        raise ValueError("Order not found")
    shipment = commerce_repo.create_shipment(company_id, {
        **data,
        "order_id": order_id,
        "destination": data.get("destination") or order.get("customer_name", ""),
    })
    commerce_repo.update_order_status(company_id, order_id, status="processing")
    commerce_repo.log_commerce_action(
        company_id, "logistics.shipment.create", user_id, shipment["tracking_number"]
    )
    return shipment


def track_shipment(company_id: int, tracking_number: str) -> dict:
    shipments = commerce_repo.list_shipments(company_id)
    for s in shipments:
        if s.get("tracking_number") == tracking_number:
            return {
                **s,
                "timeline": _status_timeline(s.get("status", "pending")),
            }
    raise ValueError(f"Tracking number not found: {tracking_number}")


def _status_timeline(current: str) -> list[dict]:
    timeline = []
    reached = True
    for status in SHIPMENT_STATUSES[:5]:  # exclude cancelled
        if status == current:
            timeline.append({"status": status, "completed": True, "current": True})
            reached = False
        else:
            timeline.append({"status": status, "completed": reached, "current": False})
    return timeline


def update_delivery(company_id: int, tracking_number: str, status: str, user_id: int | None = None) -> dict:
    if status not in SHIPMENT_STATUSES:
        raise ValueError(f"Invalid status. Choose: {SHIPMENT_STATUSES}")
    shipment = commerce_repo.update_shipment_status(company_id, tracking_number, status)
    if not shipment:
        raise ValueError("Shipment not found")
    if status == "delivered" and shipment.get("order_id"):
        commerce_repo.update_order_status(company_id, shipment["order_id"], status="completed")
    commerce_repo.log_commerce_action(
        company_id, "logistics.delivery.update", user_id, f"{tracking_number} → {status}"
    )
    return shipment


def warehouse_monitoring(company_id: int) -> dict:
    warehouses = commerce_repo.list_warehouses(company_id)
    if not warehouses:
        return {
            "warehouses": [],
            "total_capacity": 0,
            "total_stock": 0,
            "utilization_pct": 0,
            "alerts": ["No warehouses configured"],
        }

    total_capacity = sum(w.get("capacity", 0) for w in warehouses)
    total_stock = sum(w.get("current_stock", 0) for w in warehouses)
    utilization = round(total_stock / max(total_capacity, 1) * 100, 1)

    alerts = []
    for w in warehouses:
        util = w.get("current_stock", 0) / max(w.get("capacity", 1), 1) * 100
        if util > 90:
            alerts.append(f"{w['name']} near capacity ({util:.0f}%)")
        elif util < 10:
            alerts.append(f"{w['name']} underutilized ({util:.0f}%)")

    return {
        "warehouses": warehouses,
        "total_capacity": total_capacity,
        "total_stock": total_stock,
        "utilization_pct": utilization,
        "alerts": alerts or ["All warehouses within normal range"],
    }


def sync_inventory(company_id: int, user_id: int | None = None) -> dict:
    """Synchronize commerce product stock with inventory module."""
    inv_products = inventory_repo.list_products(company_id)
    commerce_products = commerce_repo.list_products(company_id, "product")

    synced = 0
    for cp in commerce_products:
        match = next((ip for ip in inv_products if ip.get("name", "").lower() == cp.get("name", "").lower()), None)
        if match:
            commerce_repo.update_product_stock(company_id, cp["id"], match.get("stock", 0))
            synced += 1

    # Aggregate warehouse stock from commerce products
    total_stock = sum(p.get("stock", 0) for p in commerce_repo.list_products(company_id, "product"))
    warehouses = commerce_repo.list_warehouses(company_id)
    if warehouses:
        commerce_repo.update_warehouse_stock(company_id, warehouses[0]["id"], total_stock)

    commerce_repo.log_commerce_action(
        company_id, "logistics.inventory.sync", user_id, f"synced={synced}"
    )
    return {
        "synced_products": synced,
        "total_commerce_stock": total_stock,
        "inventory_products": len(inv_products),
        "message": f"Synchronized {synced} products with inventory module",
    }


def delivery_management(company_id: int) -> dict:
    shipments = commerce_repo.list_shipments(company_id)
    by_status = {}
    for s in shipments:
        st = s.get("status", "pending")
        by_status[st] = by_status.get(st, 0) + 1

    return {
        "total_shipments": len(shipments),
        "by_status": by_status,
        "in_transit": by_status.get("in_transit", 0) + by_status.get("out_for_delivery", 0),
        "delivered": by_status.get("delivered", 0),
        "pending": by_status.get("pending", 0) + by_status.get("picked_up", 0),
        "recent": shipments[:10],
    }
