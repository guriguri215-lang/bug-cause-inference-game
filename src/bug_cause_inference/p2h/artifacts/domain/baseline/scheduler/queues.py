"""Queue selection and completion helpers."""

from typing import Any


def select_next(jobs: list[dict[str, Any]], current_tick: int) -> str | None:
    eligible = [
        job
        for job in jobs
        if job.get("state") == "queued"
        and not job.get("cancelled", False)
        and int(job.get("release_tick", 0)) <= current_tick
    ]
    if not eligible:
        return None
    selected = min(
        eligible,
        key=lambda job: (
            -int(job["priority"]),
            int(job["due_tick"]),
            str(job["job_id"]),
        ),
    )
    return str(selected["job_id"])


def complete_job(snapshot: dict[str, list[str]], job_id: str) -> dict[str, list[str]]:
    running = list(snapshot.get("running", []))
    completed = list(snapshot.get("completed", []))
    if job_id not in running:
        raise ValueError("job must be running before completion")
    running.remove(job_id)
    if job_id not in completed:
        completed.append(job_id)
    return {"running": running, "completed": completed}
