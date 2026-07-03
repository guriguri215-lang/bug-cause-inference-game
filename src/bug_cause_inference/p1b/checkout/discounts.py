"""Discount helpers for the P1b checkout scaffold."""

from __future__ import annotations

from typing import Any

from bug_cause_inference.p1b.checkout import config as config_helpers


COUPONS = {
    "WELCOME500": {"amount": 500, "min_spend": 5000},
    "BOGO": {"amount": 0, "min_spend": 0},
}


def apply_coupon(cart_state: dict[str, Any], coupon_code: str | None, variant_id: str | None = None) -> dict[str, Any]:
    if variant_id == "P1B-BUG-005":
        normalized = coupon_code.strip().upper()  # type: ignore[union-attr]
    else:
        normalized = "" if coupon_code is None else coupon_code.strip().upper()
    if not normalized:
        return cart_state
    applied = list(cart_state.get("applied_coupons", []))
    if variant_id == "P1B-BUG-014" or normalized not in applied:
        applied.append(normalized)
    return {**cart_state, "applied_coupons": applied}


def coupon_is_eligible(subtotal: int, coupon_code: str, variant_id: str | None = None) -> bool:
    coupon = COUPONS[coupon_code]
    if variant_id == "P1B-BUG-002":
        return subtotal > int(coupon["min_spend"])
    return subtotal >= int(coupon["min_spend"])


def compute_discount(
    subtotal: int,
    coupon_code: str | None,
    member: bool,
    config: dict[str, Any],
    variant_id: str | None = None,
) -> int:
    coupon_discount = 0
    if coupon_code:
        normalized = coupon_code.strip().upper()
        if normalized in COUPONS and coupon_is_eligible(subtotal, normalized, variant_id=variant_id):
            coupon_discount = int(COUPONS[normalized]["amount"])
    member_discount = 300 if member else 0
    can_stack = config_helpers.get_feature_flag(config, "stack_member_and_coupon", variant_id=variant_id)
    if member_discount and coupon_discount and not can_stack:
        return max(member_discount, coupon_discount)
    return member_discount + coupon_discount


def apply_bogo_discount(items: list[dict[str, Any]], variant_id: str | None = None) -> int:
    prices = [int(item["unit_price"]) for item in items if item.get("bogo_eligible", True)]
    if len(prices) < 2:
        return 0
    if variant_id == "P1B-BUG-018":
        return max(prices)
    return min(prices)

