"""
Localization engine — timezones, currency conversion, regional date/number formats,
and tax settings per country.
"""

from __future__ import annotations
from datetime import datetime, timezone, timedelta

# ── Timezone registry ─────────────────────────────────────────────────────────
TIMEZONES: dict[str, dict] = {
    "UTC":        {"offset": 0,    "label": "UTC",                         "country": "Global"},
    "Asia/Manila":{"offset": 8,    "label": "Philippine Standard Time",    "country": "PH"},
    "Asia/Shanghai":{"offset": 8,  "label": "China Standard Time",         "country": "CN"},
    "Asia/Tokyo": {"offset": 9,    "label": "Japan Standard Time",         "country": "JP"},
    "Asia/Seoul": {"offset": 9,    "label": "Korea Standard Time",         "country": "KR"},
    "Europe/Madrid":{"offset": 1,  "label": "Central European Time",       "country": "ES"},
    "America/New_York":{"offset":-5,"label": "Eastern Standard Time",      "country": "US"},
    "America/Los_Angeles":{"offset":-8,"label":"Pacific Standard Time",    "country": "US"},
    "Europe/London":{"offset": 0,  "label": "Greenwich Mean Time",         "country": "GB"},
    "Australia/Sydney":{"offset":10,"label":"Australian Eastern Standard", "country": "AU"},
}

# ── Currency registry ─────────────────────────────────────────────────────────
# Rates relative to PHP (Philippine Peso) as base — updated periodically
CURRENCY_RATES: dict[str, dict] = {
    "PHP": {"rate": 1.0,     "symbol": "₱",  "name": "Philippine Peso",   "locale": "fil-PH"},
    "USD": {"rate": 0.0175,  "symbol": "$",  "name": "US Dollar",          "locale": "en-US"},
    "CNY": {"rate": 0.126,   "symbol": "¥",  "name": "Chinese Yuan",       "locale": "zh-CN"},
    "JPY": {"rate": 2.65,    "symbol": "¥",  "name": "Japanese Yen",       "locale": "ja-JP"},
    "KRW": {"rate": 23.5,    "symbol": "₩",  "name": "South Korean Won",   "locale": "ko-KR"},
    "EUR": {"rate": 0.0161,  "symbol": "€",  "name": "Euro",               "locale": "es-ES"},
    "GBP": {"rate": 0.0138,  "symbol": "£",  "name": "British Pound",      "locale": "en-GB"},
    "AUD": {"rate": 0.0271,  "symbol": "A$", "name": "Australian Dollar",  "locale": "en-AU"},
    "SGD": {"rate": 0.0235,  "symbol": "S$", "name": "Singapore Dollar",   "locale": "en-SG"},
}

# ── Regional formats ──────────────────────────────────────────────────────────
REGIONAL_FORMATS: dict[str, dict] = {
    "PH": {"date": "MM/DD/YYYY", "time": "12h",  "number": "1,234.56",  "decimal": ".", "thousands": ","},
    "US": {"date": "MM/DD/YYYY", "time": "12h",  "number": "1,234.56",  "decimal": ".", "thousands": ","},
    "CN": {"date": "YYYY/MM/DD", "time": "24h",  "number": "1,234.56",  "decimal": ".", "thousands": ","},
    "JP": {"date": "YYYY/MM/DD", "time": "24h",  "number": "1,234",     "decimal": ".", "thousands": ","},
    "KR": {"date": "YYYY.MM.DD", "time": "24h",  "number": "1,234.56",  "decimal": ".", "thousands": ","},
    "ES": {"date": "DD/MM/YYYY", "time": "24h",  "number": "1.234,56",  "decimal": ",", "thousands": "."},
    "EU": {"date": "DD/MM/YYYY", "time": "24h",  "number": "1.234,56",  "decimal": ",", "thousands": "."},
    "GB": {"date": "DD/MM/YYYY", "time": "12h",  "number": "1,234.56",  "decimal": ".", "thousands": ","},
}

# ── Tax registry ──────────────────────────────────────────────────────────────
TAX_SETTINGS: dict[str, dict] = {
    "PH": {
        "vat_rate": 12.0,
        "corporate_tax": 25.0,
        "withholding_tax": 2.0,
        "currency": "PHP",
        "filing_frequency": "monthly",
        "authority": "Bureau of Internal Revenue (BIR)",
    },
    "US": {
        "vat_rate": 0.0,
        "sales_tax": "0–10% varies by state",
        "corporate_tax": 21.0,
        "currency": "USD",
        "filing_frequency": "quarterly",
        "authority": "Internal Revenue Service (IRS)",
    },
    "CN": {
        "vat_rate": 13.0,
        "corporate_tax": 25.0,
        "currency": "CNY",
        "filing_frequency": "monthly",
        "authority": "State Taxation Administration",
    },
    "JP": {
        "vat_rate": 10.0,
        "corporate_tax": 23.2,
        "currency": "JPY",
        "filing_frequency": "annual",
        "authority": "National Tax Agency",
    },
    "KR": {
        "vat_rate": 10.0,
        "corporate_tax": 22.0,
        "currency": "KRW",
        "filing_frequency": "biannual",
        "authority": "National Tax Service",
    },
    "ES": {
        "vat_rate": 21.0,
        "corporate_tax": 25.0,
        "currency": "EUR",
        "filing_frequency": "quarterly",
        "authority": "Agencia Tributaria",
    },
    "EU": {
        "vat_rate": 20.0,
        "corporate_tax": 19.0,
        "currency": "EUR",
        "filing_frequency": "quarterly",
        "authority": "European Tax Authority (varies by member state)",
    },
}


# ── Functions ─────────────────────────────────────────────────────────────────

def convert_currency(amount: float, from_currency: str, to_currency: str) -> dict:
    """Convert amount from one currency to another via PHP as pivot."""
    from_info = CURRENCY_RATES.get(from_currency.upper())
    to_info = CURRENCY_RATES.get(to_currency.upper())
    if not from_info or not to_info:
        raise ValueError(f"Unsupported currency: {from_currency} or {to_currency}")
    # Convert to PHP first, then to target
    php_amount = amount / from_info["rate"]
    converted = php_amount * to_info["rate"]
    return {
        "from": {"amount": amount, "currency": from_currency, "symbol": from_info["symbol"]},
        "to": {"amount": round(converted, 4), "currency": to_currency, "symbol": to_info["symbol"]},
        "rate": round(to_info["rate"] / from_info["rate"], 6),
        "note": "Rates are indicative; verify with live exchange data for transactions.",
    }


def get_current_time_in_zone(tz_name: str) -> dict:
    tz_info = TIMEZONES.get(tz_name)
    offset_h = tz_info["offset"] if tz_info else 0
    tz_obj = timezone(timedelta(hours=offset_h))
    now = datetime.now(tz_obj)
    return {
        "timezone": tz_name,
        "label": tz_info["label"] if tz_info else tz_name,
        "offset": f"UTC{'+' if offset_h >= 0 else ''}{offset_h}",
        "current_time": now.strftime("%Y-%m-%d %H:%M:%S"),
        "iso": now.isoformat(),
    }


def get_regional_format(country_code: str) -> dict:
    return REGIONAL_FORMATS.get(country_code.upper(), REGIONAL_FORMATS["US"])


def get_tax_settings(country_code: str) -> dict:
    return TAX_SETTINGS.get(country_code.upper(), {
        "note": f"Tax settings not configured for {country_code}",
        "currency": "USD",
    })


def format_currency_amount(amount: float, currency_code: str) -> str:
    info = CURRENCY_RATES.get(currency_code.upper(), {})
    symbol = info.get("symbol", currency_code)
    return f"{symbol}{amount:,.2f}"


def list_timezones() -> list[dict]:
    return [
        {"name": name, **info}
        for name, info in sorted(TIMEZONES.items(), key=lambda x: x[1]["offset"])
    ]


def list_currencies() -> list[dict]:
    return [
        {"code": code, **info}
        for code, info in sorted(CURRENCY_RATES.items())
    ]
