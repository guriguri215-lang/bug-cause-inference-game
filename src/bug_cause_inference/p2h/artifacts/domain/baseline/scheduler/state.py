"""Explicit task lifecycle transitions."""


def transition_state(current_state: str, event: str) -> str:
    transitions = {
        ("queued", "start"): "running",
        ("running", "succeed"): "succeeded",
        ("running", "fail"): "failed",
        ("failed", "retry"): "queued",
    }
    try:
        return transitions[(current_state, event)]
    except KeyError as exc:
        raise ValueError(f"invalid transition: {current_state}/{event}") from exc
