"""Cart helpers for the P1b real-diff artifact baseline."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from . import config as config_helpers
from . import discounts, shipping


def validate_item(item: dict[str, Any]) -> None:
    quantity = int(item.get("quantity", 0))
    if quantity <= 0:
        raise ValueError("quantity must be positive")
    if quantity > 99:
        raise ValueError("quantity exceeds maximum")


def add_item(cart: list[dict[str, Any]], sku: str, unit_price: int, quantity: int) -> list[dict[str, Any]]:
    item = {"sku": sku, "unit_price": unit_price, "quantity": quantity, "requires_shipping": True}
    validate_item(item)
    return [*cart, item]


def cart_subtotal(items: list[dict[str, Any]] | None) -> int:
    if items is None:
        return 0
    return sum(int(item["unit_price"]) * int(item.get("quantity", 1)) for item in items)


def calculate_tax(amount: int, tax_rate: float) -> int:
    raw = Decimal(str(amount)) * Decimal(str(tax_rate))
    return int(raw.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def item_requires_shipping(item: dict[str, Any]) -> bool:
    return bool(item.get("requires_shipping", True))


def remove_item(items: list[dict[str, Any]], sku: str) -> list[dict[str, Any]]:
    return [item for item in items if item.get("sku") != sku]


def calculate_total(
    items: list[dict[str, Any]],
    coupon_code: str | None,
    member: bool,
    region: str,
    config: dict[str, Any],
) -> int:
    subtotal = cart_subtotal(items)
    discount = discounts.compute_discount(
        subtotal,
        coupon_code,
        member=member,
        config=config,
    )
    tax_rate = config_helpers.get_tax_rate(config, region)
    taxable_amount = max(0, subtotal - discount)
    return taxable_amount + calculate_tax(taxable_amount, tax_rate)


def checkout_quote(
    items: list[dict[str, Any]],
    address: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, int]:
    subtotal = cart_subtotal(items)
    shipping_fee = shipping.calculate_shipping(items, subtotal, address, config)
    return {"subtotal": subtotal, "shipping": shipping_fee, "total": subtotal + shipping_fee}
