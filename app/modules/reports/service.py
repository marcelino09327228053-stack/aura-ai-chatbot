"""Report generation and export helpers."""

import csv
import io
from datetime import datetime

from app.modules.accounting import repository as accounting_repo
from app.modules.crm import repository as crm_repo
from app.modules.hr import repository as hr_repo
from app.modules.inventory import repository as inventory_repo


def daily_summary(company_id: int) -> dict:
    accounting = accounting_repo.get_daily_report(company_id)
    return {
        "period": "daily",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "accounting": accounting,
        "customers": crm_repo.count_customers(company_id),
        "employees": hr_repo.count_employees(company_id),
        "inventory_units": inventory_repo.total_stock_units(company_id),
    }


def monthly_summary(company_id: int) -> dict:
    accounting = accounting_repo.get_summary(company_id)
    return {
        "period": "monthly",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "accounting": accounting,
        "customers": crm_repo.count_customers(company_id),
        "employees": hr_repo.count_employees(company_id),
        "inventory_units": inventory_repo.total_stock_units(company_id),
    }


def export_excel_csv(company_id: int) -> str:
    """Return CSV content suitable for Excel import (stdlib only)."""
    summary = monthly_summary(company_id)
    transactions = accounting_repo.list_transactions(company_id)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["MB Future Tech AI Chatbot Business Report"])
    writer.writerow(["Generated", summary["generated_at"]])
    writer.writerow([])
    writer.writerow(["Metric", "Value"])
    writer.writerow(["Income", summary["accounting"]["income"]])
    writer.writerow(["Expenses", summary["accounting"]["expenses"]])
    writer.writerow(["Profit", summary["accounting"]["profit"]])
    writer.writerow(["Customers", summary["customers"]])
    writer.writerow(["Employees", summary["employees"]])
    writer.writerow(["Inventory Units", summary["inventory_units"]])
    writer.writerow([])
    writer.writerow(["Transactions"])
    writer.writerow(["ID", "Type", "Amount", "Description", "Created"])
    for txn in transactions:
        writer.writerow([
            txn["id"], txn["type"], txn["amount"],
            txn.get("description", ""), txn["created_at"],
        ])
    return output.getvalue()


def export_pdf_bytes(company_id: int) -> bytes:
    """Generate a simple PDF report using fpdf2."""
    from fpdf import FPDF

    summary = monthly_summary(company_id)
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "MB Future Tech AI Chatbot Business Report", ln=True)
    pdf.set_font("Helvetica", size=12)
    pdf.cell(0, 8, f"Generated: {summary['generated_at']}", ln=True)
    pdf.ln(4)
    acc = summary["accounting"]
    for label, value in [
        ("Income", acc["income"]),
        ("Expenses", acc["expenses"]),
        ("Profit", acc["profit"]),
        ("Customers", summary["customers"]),
        ("Employees", summary["employees"]),
        ("Inventory Units", summary["inventory_units"]),
    ]:
        pdf.cell(0, 8, f"{label}: {value}", ln=True)
    return pdf.output()
