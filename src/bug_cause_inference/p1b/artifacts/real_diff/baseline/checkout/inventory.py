"""Inventory helpers for the P1b real-diff artifact baseline."""

from __future__ import annotations

from typing import Any


def reserve_stock(record: dict[str, Any], quantity: int) -> dict[str, Any]:
    if record.get("preorder"):
        return {**record, "reserved": int(record.get("reserved", 0)) + quantity}
    reserved = int(record.get("reserved", 0))
    if int(record.get("on_hand", 0)) - reserved < quantity:
        raise ValueError("out of stock")
    return {**record, "reserved": reserved + quantity}


def cancel_reservation(record: dict[str, Any], quantity: int) -> dict[str, Any]:
    reserved = int(record.get("reserved", 0))
    return {**record, "reserved": max(0, reserved - quantity)}


def sync_after_cart_update(record: dict[str, Any], removed_quantity: int) -> dict[str, Any]:
    return cancel_reservation(record, removed_quantity)
