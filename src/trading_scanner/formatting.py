"""Human-readable price formatting. Formatting never rounds away source digits."""

from __future__ import annotations

from decimal import Decimal


def _indian_grouping(digits: str) -> str:
    if len(digits) <= 3:
        return digits
    head, tail = digits[:-3], digits[-3:]
    groups: list[str] = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    return ",".join(groups + [tail])


def format_price(value: Decimal | None) -> str:
    """Format a price with Indian digit grouping and at least two decimals, e.g. 1,384.90."""
    if value is None:
        return "—"
    sign = "-" if value < 0 else ""
    text = format(abs(value), "f")
    whole, _, fraction = text.partition(".")
    fraction = fraction.ljust(2, "0")
    return f"{sign}{_indian_grouping(whole)}.{fraction}"


def format_inr(value: Decimal | None) -> str:
    return "—" if value is None else f"₹{format_price(value)}"
