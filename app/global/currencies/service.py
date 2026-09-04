"""
Currency service — conversion, multi-currency invoicing, regional pricing.
"""

from ..localization.engine import (
    CURRENCY_RATES,
    convert_currency,
    format_currency_amount,
)


def convert(amount: float, from_code: str, to_code: str) -> dict:
    return convert_currency(amount, from_code, to_code)


def multi_currency_price(amount: float, base_currency: str) -> list[dict]:
    """Return the same amount expressed in all supported currencies."""
    results = []
    for code in CURRENCY_RATES:
        if code == base_currency.upper():
            continue
        try:
            conv = convert_currency(amount, base_currency, code)
            results.append({
                "currency": code,
                "symbol": conv["to"]["symbol"],
                "amount": conv["to"]["amount"],
                "name": CURRENCY_RATES[code]["name"],
            })
        except Exception:
            pass
    return sorted(results, key=lambda x: x["currency"])


def invoice_summary(items: list[dict], currency: str, tax_rate: float = 0.0) -> dict:
    """
    Generate an invoice summary with totals in the given currency.

    Each item: { name, quantity, unit_price }
    """
    subtotal = sum(i.get("quantity", 1) * i.get("unit_price", 0) for i in items)
    tax_amount = round(subtotal * tax_rate / 100, 2)
    total = round(subtotal + tax_amount, 2)
    info = CURRENCY_RATES.get(currency.upper(), {})
    symbol = info.get("symbol", currency)
    return {
        "currency": currency.upper(),
        "symbol": symbol,
        "subtotal": round(subtotal, 2),
        "tax_rate": tax_rate,
        "tax_amount": tax_amount,
        "total": total,
        "total_formatted": f"{symbol}{total:,.2f}",
        "line_items": [
            {
                **i,
                "line_total": round(i.get("quantity", 1) * i.get("unit_price", 0), 2),
            }
            for i in items
        ],
    }
