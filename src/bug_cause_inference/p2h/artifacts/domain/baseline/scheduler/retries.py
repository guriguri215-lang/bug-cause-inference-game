"""Retry-limit and retry-tick calculations."""


def should_retry(attempts: int, max_attempts: int) -> bool:
    return attempts < max_attempts


def next_retry_tick(
    failure_tick: int,
    attempts: int,
    base_delay: int,
    max_delay: int,
) -> int:
    delay = base_delay * (2 ** attempts)
    return failure_tick + min(delay, max_delay)
