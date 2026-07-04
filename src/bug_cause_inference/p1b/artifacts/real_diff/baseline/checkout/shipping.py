"""Shipping helpers for the P1b real-diff artifact baseline."""

from __future__ import annotations

from typing import Any

from . import config as config_helpers


def resolve_region_rate(address: dict[str, Any], config: dict[str, Any]) -> int:
    if "region" not in address:
        region = config_helpers.get_region_defaults(config).get("missing", "domestic")
    else:
        region = address["region"]

    region = config_helpers.get_region_aliases(config).get(region, region)
    return int(config.get("region_rates", {}).get(region, config["region_rates"]["domestic"]))


def free_shipping_eligible(subtotal: int, config: dict[str, Any]) -> bool:
    threshold = config_helpers.get_shipping_threshold(config)
    return subtotal >= threshold


def calculate_shipping(
    items: list[dict[str, Any]],
    subtotal: int,
    address: dict[str, Any],
    config: dict[str, Any],
) -> int:
    has_physical_item = any(item.get("requires_shipping", True) for item in items)
    if not has_physical_item:
        return 0
    if free_shipping_eligible(subtotal, config):
        return 0
    return resolve_region_rate(address, config)
