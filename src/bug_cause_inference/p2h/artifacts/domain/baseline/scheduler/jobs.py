"""Job validation helpers for the toy scheduler."""


def validate_priority(priority: int) -> int:
    if not isinstance(priority, int):
        raise TypeError("priority must be an integer")
    if priority < 0 or priority > 9:
        raise ValueError("priority must be between 0 and 9")
    return priority


def is_released(release_tick: int, current_tick: int) -> bool:
    return current_tick >= release_tick


def normalize_tags(tags: list[str] | None) -> tuple[str, ...]:
    if tags is None:
        tags = []
    return tuple(sorted({str(tag).strip() for tag in tags if str(tag).strip()}))
