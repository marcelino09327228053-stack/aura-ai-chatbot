"""
Optional business modules (CRM, Inventory, Accounting, HR, Reports, Analytics).

Each module can be disabled via environment variable:
  MODULE_CRM_ENABLED=false
"""

from app.core.config import is_module_enabled


def register_modules(application) -> None:
    """Mount module routers when enabled."""
    if is_module_enabled("crm"):
        from app.modules.crm.router import router as crm_router
        application.include_router(crm_router)

    if is_module_enabled("inventory"):
        from app.modules.inventory.router import router as inventory_router
        application.include_router(inventory_router)

    if is_module_enabled("accounting"):
        from app.modules.accounting.router import router as accounting_router
        application.include_router(accounting_router)

    if is_module_enabled("hr"):
        from app.modules.hr.router import router as hr_router
        application.include_router(hr_router)

    if is_module_enabled("reports"):
        from app.modules.reports.router import router as reports_router
        application.include_router(reports_router)

    if is_module_enabled("analytics"):
        from app.modules.analytics.router import router as analytics_router
        application.include_router(analytics_router)
