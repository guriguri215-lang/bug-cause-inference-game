"""Shipping helpers for the P1b checkout scaffold."""

from __future__ import annotations

from typing import Any

from bug_cause_inference.p1b.checkout import config as config_helpers


def resolve_region_rate(address: dict[str, Any], config: dict[str, Any], variant_id: str | None = None) -> int:
    if "region" not in address:
        if variant_id == "P1B-BUG-006":
            raise KeyError("region")
        region = config_helpers.get_region_defaults(config).get("missing", "domestic")
    else:
        region = address["region"]

    if variant_id != "P1B-BUG-011":
        region = config_helpers.get_region_aliases(config).get(region, region)
    return int(config.get("region_rates", {}).get(region, config["region_rates"]["domestic"]))


def free_shipping_eligible(subtotal: int, config: dict[str, Any], variant_id: str | None = None) -> bool:
    threshold = config_helpers.get_shipping_threshold(config)
    if variant_id == "P1B-BUG-001":
        return subtotal > threshold
    return subtotal >= threshold


def calculate_shipping(
    items: list[dict[str, Any]],
    subtotal: int,
    address: dict[str, Any],
    config: dict[str, Any],
    variant_id: str | None = None,
) -> int:
    has_physical_item = any(item.get("requires_shipping", True) for item in items)
    if not has_physical_item and variant_id != "P1B-BUG-019":
        return 0
    if free_shipping_eligible(subtotal, config, variant_id=variant_id):
        return 0
    return resolve_region_rate(address, config, variant_id=variant_id)

