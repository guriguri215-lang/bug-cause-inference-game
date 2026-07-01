"""Cart helpers for the P1b checkout scaffold."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from bug_cause_inference.p1b.checkout import config as config_helpers
from bug_cause_inference.p1b.checkout import discounts, shipping


def validate_item(item: dict[str, Any], variant_id: str | None = None) -> None:
    quantity = int(item.get("quantity", 0))
    if quantity <= 0:
        raise ValueError("quantity must be positive")
    if variant_id == "P1B-BUG-003":
        if quantity >= 99:
            raise ValueError("quantity exceeds maximum")
    elif quantity > 99:
        raise ValueError("quantity exceeds maximum")


def add_item(cart: list[dict[str, Any]], sku: str, unit_price: int, quantity: int, variant_id: str | None = None) -> list[dict[str, Any]]:
    item = {"sku": sku, "unit_price": unit_price, "quantity": quantity, "requires_shipping": True}
    validate_item(item, variant_id=variant_id)
    return [*cart, item]


def cart_subtotal(items: list[dict[str, Any]] | None, variant_id: str | None = None) -> int:
    if items is None and variant_id != "P1B-BUG-007":
        return 0
    return sum(int(item["unit_price"]) * int(item.get("quantity", 1)) for item in items)  # type: ignore[union-attr]


def calculate_tax(amount: int, tax_rate: float, variant_id: str | None = None) -> int:
    raw = Decimal(str(amount)) * Decimal(str(tax_rate))
    if variant_id == "P1B-BUG-004":
        return int(raw)
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
    variant_id: str | None = None,
) -> int:
    subtotal = cart_subtotal(items, variant_id=variant_id)
    discount = discounts.compute_discount(
        subtotal,
        coupon_code,
        member=member,
        config=config,
        variant_id=variant_id,
    )
    tax_rate = config_helpers.get_tax_rate(config, region, variant_id=variant_id)
    if variant_id == "P1B-BUG-017":
        return subtotal + calculate_tax(subtotal, tax_rate, variant_id=variant_id) - discount
    taxable_amount = max(0, subtotal - discount)
    return taxable_amount + calculate_tax(taxable_amount, tax_rate, variant_id=variant_id)


def checkout_quote(
    items: list[dict[str, Any]],
    address: dict[str, Any],
    config: dict[str, Any],
    variant_id: str | None = None,
) -> dict[str, int]:
    subtotal = cart_subtotal(items, variant_id=variant_id)
    quote_items = items
    if variant_id == "P1B-BUG-016":
        quote_items = list(items[:-1]) if len(items) > 1 else items
    shipping_subtotal = cart_subtotal(quote_items, variant_id=variant_id)
    shipping_fee = shipping.calculate_shipping(quote_items, shipping_subtotal, address, config, variant_id=variant_id)
    return {"subtotal": subtotal, "shipping": shipping_fee, "total": subtotal + shipping_fee}

