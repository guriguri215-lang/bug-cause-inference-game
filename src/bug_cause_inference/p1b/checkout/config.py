"""Small configuration helpers for the P1b checkout scaffold."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


DEFAULT_CONFIG: dict[str, Any] = {
    "tax_rates": {"JP": 0.10, "US": 0.07},
    "feature_flags": {"stack_member_and_coupon": False, "allow_preorder": True},
    "shipping_threshold": 10000,
    "region_rates": {"domestic": 800, "okinawa": 1600, "international": 3000},
    "region_defaults": {"missing": "domestic"},
    "region_aliases": {"okinawa": "okinawa", "jp-okinawa": "okinawa"},
}


def load_config(overrides: dict[str, Any] | None = None, variant_id: str | None = None) -> dict[str, Any]:
    config = deepcopy(DEFAULT_CONFIG)
    overrides = overrides or {}
    for key, value in overrides.items():
        if key == "FREE_SHIPPING_THRESHOLD":
            if variant_id == "P1B-BUG-012":
                config["shipping_threshold"] = value
            else:
                config["shipping_threshold"] = int(value)
        else:
            config[key] = value
    return config


def get_tax_rate(config: dict[str, Any], region: str, variant_id: str | None = None) -> float:
    rates = config.get("tax_rates", {})
    if region in rates:
        return float(rates[region])
    if variant_id == "P1B-BUG-009" and region == "JP":
        return 0.08
    if region == "JP":
        return 0.10
    return 0.0


def get_feature_flag(config: dict[str, Any], flag_name: str, variant_id: str | None = None) -> bool:
    flags = config.get("feature_flags", {})
    if flag_name in flags:
        return bool(flags[flag_name])
    if variant_id == "P1B-BUG-010" and flag_name == "stack_member_and_coupon":
        return True
    return False


def get_shipping_threshold(config: dict[str, Any]) -> Any:
    return config.get("shipping_threshold", 10000)


def get_region_defaults(config: dict[str, Any]) -> dict[str, str]:
    return dict(config.get("region_defaults", {"missing": "domestic"}))


def get_region_aliases(config: dict[str, Any]) -> dict[str, str]:
    return dict(config.get("region_aliases", {}))

