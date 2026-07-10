"""Canonical money formatting.

Prices are canonical: always ``$`` + dot-decimal, two places, in BOTH languages.
Python's format spec (``:.2f``) is locale-independent, so this never gets
reformatted to ``$79,00`` under an Arabic/locale-aware context — the reason a
single helper is used everywhere prices render (cards, detail, cart, checkout,
order pages, dashboard, WhatsApp message). See spec M1.3.
"""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def format_money(value):
    """Return ``$X.YY`` for any numeric/Decimal/str/None value."""
    if value is None or value == "":
        value = 0
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        amount = Decimal("0")
    amount = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"${amount:.2f}"
