"""Configuration normalization for the toy scheduler."""

from typing import Any


def normalize_queue_name(name: str, aliases: dict[str, str] | None = None) -> str:
    normalized = name.strip().lower()
    normalized_aliases = {
        str(key).strip().lower(): str(value).strip().lower()
        for key, value in (aliases or {}).items()
    }
    return normalized_aliases.get(normalized, normalized)


def retry_limit(config: dict[str, Any], queue_name: str) -> int:
    aliases = config.get("queue_aliases") or {}
    normalized_queue = normalize_queue_name(queue_name, aliases)
    raw_limits = config.get("queue_limits") or {}
    limits = {
        normalize_queue_name(str(key), aliases): int(value)
        for key, value in raw_limits.items()
    }
    return limits.get(normalized_queue, int(config.get("default_retry_limit", 3)))
