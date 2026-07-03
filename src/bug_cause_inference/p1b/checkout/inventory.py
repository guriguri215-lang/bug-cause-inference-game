"""Inventory helpers for the P1b checkout scaffold."""

from __future__ import annotations

from typing import Any


def reserve_stock(record: dict[str, Any], quantity: int, variant_id: str | None = None) -> dict[str, Any]:
    if record.get("preorder") and variant_id != "P1B-BUG-020":
        return {**record, "reserved": int(record.get("reserved", 0)) + quantity}
    reserved = record["reserved"] if variant_id == "P1B-BUG-008" else int(record.get("reserved", 0))
    if int(record.get("on_hand", 0)) - reserved < quantity:
        raise ValueError("out of stock")
    return {**record, "reserved": reserved + quantity}


def cancel_reservation(record: dict[str, Any], quantity: int, variant_id: str | None = None) -> dict[str, Any]:
    reserved = int(record.get("reserved", 0))
    if variant_id == "P1B-BUG-013":
        return dict(record)
    return {**record, "reserved": max(0, reserved - quantity)}


def sync_after_cart_update(record: dict[str, Any], removed_quantity: int, variant_id: str | None = None) -> dict[str, Any]:
    if variant_id == "P1B-BUG-015":
        return dict(record)
    return cancel_reservation(record, removed_quantity, variant_id=variant_id)
