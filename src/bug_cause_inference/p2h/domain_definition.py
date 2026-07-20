"""Outcome-free definition and artifact authoring for the P2h toy domain.

This module contains only the pre-outcome task-scheduler baseline, exact source
replacements, deterministic oracle cases, and action-case mapping. It does not
select a policy or execute a policy trajectory.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
from pathlib import Path
from typing import Any


DOMAIN_ID = "toy_task_scheduler_v1"
DOMAIN_SCHEMA_VERSION = "p2h_task_scheduler_domain.v1"
INPUT_ORDER = tuple(
    [f"P2H-BUG-{index:03d}" for index in range(1, 11)]
    + [f"P2H-CLEAN-{index:03d}" for index in range(1, 6)]
)
ACTION_ORDER = (
    "run_smoke_tests",
    "run_boundary_tests",
    "run_null_missing_tests",
    "run_config_matrix_tests",
    "run_state_sequence_tests",
    "run_property_search",
    "inspect_traceback",
    "inspect_coverage_spectrum",
    "inspect_recent_diff",
    "inspect_spec_clause",
)


BASELINE_FILES: dict[str, str] = {
    "scheduler/__init__.py": '"""Pure deterministic toy task scheduler."""\n',
    "scheduler/jobs.py": '''"""Job validation helpers for the toy scheduler."""


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
''',
    "scheduler/queues.py": '''"""Queue selection and completion helpers."""

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
''',
    "scheduler/retries.py": '''"""Retry-limit and retry-tick calculations."""


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
''',
    "scheduler/config.py": '''"""Configuration normalization for the toy scheduler."""

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
''',
    "scheduler/state.py": '''"""Explicit task lifecycle transitions."""


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
''',
}


def _input(
    input_id: str,
    *,
    family: str,
    path: str,
    function: str,
    before: str,
    after: str,
    expected_failing_oracle_ids: tuple[str, ...],
    cause: str | None = None,
    fix_intent: str | None = None,
    trigger: str,
    expected_behavior: str,
    actual_behavior: str,
    clean_family: str | None = None,
) -> dict[str, Any]:
    return {
        "input_id": input_id,
        "is_buggy": cause is not None,
        "cause_family": cause,
        "clean_family": clean_family,
        "family": family,
        "target_path": path,
        "target_function": function,
        "replacement_before": before,
        "replacement_after": after,
        "expected_failing_oracle_ids": list(expected_failing_oracle_ids),
        "fix_intent": fix_intent,
        "trigger": trigger,
        "expected_behavior": expected_behavior,
        "actual_behavior": actual_behavior,
    }


INPUT_DEFINITIONS = (
    _input(
        "P2H-BUG-001",
        family="release_tick_inclusive_boundary",
        path="scheduler/jobs.py",
        function="jobs.is_released",
        before="    return current_tick >= release_tick\n",
        after="    return current_tick > release_tick\n",
        expected_failing_oracle_ids=("boundary.release_equal", "coverage.release_equal"),
        cause="boundary_condition",
        fix_intent="change_comparison",
        trigger="release_tick=5, current_tick=5",
        expected_behavior="A job is eligible at its exact release tick.",
        actual_behavior="The patched function delays eligibility by one tick.",
    ),
    _input(
        "P2H-BUG-002",
        family="retry_attempt_limit_boundary",
        path="scheduler/retries.py",
        function="retries.should_retry",
        before="    return attempts < max_attempts\n",
        after="    return attempts <= max_attempts\n",
        expected_failing_oracle_ids=("boundary.retry_limit_equal",),
        cause="boundary_condition",
        fix_intent="change_comparison",
        trigger="attempts=3, max_attempts=3",
        expected_behavior="No retry is allowed once attempts reaches the limit.",
        actual_behavior="The patched function allows one retry beyond the limit.",
    ),
    _input(
        "P2H-BUG-003",
        family="optional_tags_null_guard",
        path="scheduler/jobs.py",
        function="jobs.normalize_tags",
        before="    if tags is None:\n        tags = []\n",
        after="    if tags is None:\n        tags = None\n",
        expected_failing_oracle_ids=("null.tags_none", "trace.tags_none"),
        cause="missing_null_handling",
        fix_intent="add_missing_value_guard",
        trigger="tags=None",
        expected_behavior="Missing optional tags normalize to an empty tuple.",
        actual_behavior="The patched function iterates over None and raises TypeError.",
    ),
    _input(
        "P2H-BUG-004",
        family="missing_queue_limits_default",
        path="scheduler/config.py",
        function="config.retry_limit",
        before='    raw_limits = config.get("queue_limits") or {}\n',
        after='    raw_limits = config["queue_limits"]\n',
        expected_failing_oracle_ids=("null.queue_limits_absent", "trace.queue_limits_absent"),
        cause="missing_null_handling",
        fix_intent="fix_config_default",
        trigger="config without queue_limits",
        expected_behavior="The configured default retry limit is returned.",
        actual_behavior="The patched function raises KeyError for an absent optional map.",
    ),
    _input(
        "P2H-BUG-005",
        family="queue_name_whitespace_normalization",
        path="scheduler/config.py",
        function="config.normalize_queue_name",
        before="    normalized = name.strip().lower()\n",
        after="    normalized = name.lower()\n",
        expected_failing_oracle_ids=("config.queue_name_trim", "config.queue_retry_limit"),
        cause="configuration_environment",
        fix_intent="normalize_config_or_input",
        trigger='queue name " Critical "',
        expected_behavior="Equivalent queue names ignore surrounding whitespace.",
        actual_behavior="The patched function preserves whitespace and misses the canonical queue.",
    ),
    _input(
        "P2H-BUG-006",
        family="queue_limit_lookup_normalization",
        path="scheduler/config.py",
        function="config.retry_limit",
        before='    normalized_queue = normalize_queue_name(queue_name, aliases)\n',
        after='    normalized_queue = queue_name.lower()\n',
        expected_failing_oracle_ids=("config.queue_retry_limit",),
        cause="configuration_environment",
        fix_intent="normalize_config_or_input",
        trigger='queue name " Critical " with a critical queue limit',
        expected_behavior="The queue-specific retry limit is selected after normalization.",
        actual_behavior="The patched lookup falls back to the default limit.",
    ),
    _input(
        "P2H-BUG-007",
        family="completion_requires_running_state",
        path="scheduler/state.py",
        function="state.transition_state",
        before='    try:\n        return transitions[(current_state, event)]\n    except KeyError as exc:\n        raise ValueError(f"invalid transition: {current_state}/{event}") from exc\n',
        after='    if current_state == "queued" and event == "succeed":\n        return "succeeded"\n    try:\n        return transitions[(current_state, event)]\n    except KeyError as exc:\n        raise ValueError(f"invalid transition: {current_state}/{event}") from exc\n',
        expected_failing_oracle_ids=("state.invalid_completion",),
        cause="state_order_dependence",
        fix_intent="fix_state_transition",
        trigger="queued + succeed without start",
        expected_behavior="Completion before a start event is rejected.",
        actual_behavior="The patched state machine skips the running state.",
    ),
    _input(
        "P2H-BUG-008",
        family="completion_moves_out_of_running",
        path="scheduler/queues.py",
        function="queues.complete_job",
        before="    running.remove(job_id)\n    if job_id not in completed:\n",
        after="    if job_id in running:\n        pass\n    if job_id not in completed:\n",
        expected_failing_oracle_ids=("state.queue_complete_moves",),
        cause="state_order_dependence",
        fix_intent="fix_state_transition",
        trigger="complete a running job",
        expected_behavior="Completion atomically removes the job from running and adds it to completed.",
        actual_behavior="The patched function leaves the completed job in running.",
    ),
    _input(
        "P2H-BUG-009",
        family="priority_before_due_selection_rule",
        path="scheduler/queues.py",
        function="queues.select_next",
        before='        key=lambda job: (\n            -int(job["priority"]),\n            int(job["due_tick"]),\n            str(job["job_id"]),\n        ),\n',
        after='        key=lambda job: (\n            int(job["due_tick"]),\n            -int(job["priority"]),\n            str(job["job_id"]),\n        ),\n',
        expected_failing_oracle_ids=("coverage.selection_priority", "spec.priority_before_due"),
        cause="specification_mismatch",
        fix_intent="align_selection_rule_with_spec",
        trigger="higher-priority job has a later due tick",
        expected_behavior="Priority is the primary scheduler ordering key.",
        actual_behavior="The patched selector gives due tick precedence over priority.",
    ),
    _input(
        "P2H-BUG-010",
        family="retry_cap_after_exponential_growth",
        path="scheduler/retries.py",
        function="retries.next_retry_tick",
        before="    delay = base_delay * (2 ** attempts)\n    return failure_tick + min(delay, max_delay)\n",
        after="    delay = min(base_delay, max_delay) * (2 ** attempts)\n    return failure_tick + delay\n",
        expected_failing_oracle_ids=("property.retry_cap", "spec.retry_cap_after_growth"),
        cause="specification_mismatch",
        fix_intent="align_calculation_order_with_spec",
        trigger="exponential delay exceeds the configured cap",
        expected_behavior="The fully grown delay is capped before it is added to the failure tick.",
        actual_behavior="The patched calculation caps the base and then grows past the limit.",
    ),
    _input(
        "P2H-CLEAN-001",
        family="boundary_adjacent_valid_behavior",
        clean_family="boundary_adjacent_valid_behavior",
        path="scheduler/jobs.py",
        function="jobs.is_released",
        before="    return current_tick >= release_tick\n",
        after="    return (current_tick - release_tick) >= 0\n",
        expected_failing_oracle_ids=(),
        trigger="release ticks before, at, and after the current tick",
        expected_behavior="Inclusive release behavior is preserved.",
        actual_behavior="Inclusive release behavior is preserved by equivalent arithmetic.",
    ),
    _input(
        "P2H-CLEAN-002",
        family="optional_absence_default",
        clean_family="optional_absence_default",
        path="scheduler/jobs.py",
        function="jobs.normalize_tags",
        before="    if tags is None:\n        tags = []\n",
        after="    tags = [] if tags is None else tags\n",
        expected_failing_oracle_ids=(),
        trigger="tags=None and ordinary tag lists",
        expected_behavior="Optional absence still normalizes to an empty tuple.",
        actual_behavior="The explicit conditional expression preserves the same behavior.",
    ),
    _input(
        "P2H-CLEAN-003",
        family="config_equivalent_normalization",
        clean_family="config_equivalent_normalization",
        path="scheduler/config.py",
        function="config.normalize_queue_name",
        before="    normalized = name.strip().lower()\n",
        after="    normalized = name.strip().casefold()\n",
        expected_failing_oracle_ids=(),
        trigger="ASCII queue names and aliases in the frozen oracle matrix",
        expected_behavior="Equivalent ASCII configuration forms normalize identically.",
        actual_behavior="casefold preserves the frozen ASCII normalization behavior.",
    ),
    _input(
        "P2H-CLEAN-004",
        family="valid_state_sequence",
        clean_family="valid_state_sequence",
        path="scheduler/state.py",
        function="state.transition_state",
        before='    try:\n        return transitions[(current_state, event)]\n    except KeyError as exc:\n        raise ValueError(f"invalid transition: {current_state}/{event}") from exc\n',
        after='    key = (current_state, event)\n    if key not in transitions:\n        raise ValueError(f"invalid transition: {current_state}/{event}")\n    return transitions[key]\n',
        expected_failing_oracle_ids=(),
        trigger="all frozen valid and invalid lifecycle transitions",
        expected_behavior="Valid order and invalid-order rejection are preserved.",
        actual_behavior="An explicit membership check preserves the same transition contract.",
    ),
    _input(
        "P2H-CLEAN-005",
        family="nonintuitive_spec_conformance",
        clean_family="nonintuitive_spec_conformance",
        path="scheduler/queues.py",
        function="queues.select_next",
        before='    selected = min(\n        eligible,\n        key=lambda job: (\n            -int(job["priority"]),\n            int(job["due_tick"]),\n            str(job["job_id"]),\n        ),\n    )\n    return str(selected["job_id"])\n',
        after='    ranked = sorted(\n        eligible,\n        key=lambda job: (\n            -int(job["priority"]),\n            int(job["due_tick"]),\n            str(job["job_id"]),\n        ),\n    )\n    return str(ranked[0]["job_id"])\n',
        expected_failing_oracle_ids=(),
        trigger="priority first, then due tick, then lexical job ID",
        expected_behavior="The nonintuitive priority-first specification remains exact.",
        actual_behavior="Sorting and taking the first row is equivalent to min with the same key.",
    ),
)


def _case(
    oracle_id: str,
    action_id: str,
    module: str,
    function: str,
    args: list[Any],
    expected: Any = None,
    *,
    kwargs: dict[str, Any] | None = None,
    expected_exception: str | None = None,
    evidence_tags: tuple[str, ...] = (),
    fix_intent_hints: tuple[str, ...] = (),
) -> dict[str, Any]:
    return {
        "oracle_id": oracle_id,
        "action_id": action_id,
        "module": module,
        "function": function,
        "args": args,
        "kwargs": kwargs or {},
        "expected": expected,
        "expected_exception": expected_exception,
        "evidence_tags": list(evidence_tags),
        "fix_intent_hints": list(fix_intent_hints),
    }


_SELECTION_JOBS = [
    {"job_id": "low", "priority": 3, "due_tick": 2, "release_tick": 0, "state": "queued"},
    {"job_id": "high", "priority": 8, "due_tick": 9, "release_tick": 0, "state": "queued"},
]
_TIE_JOBS = [
    {"job_id": "b", "priority": 5, "due_tick": 4, "release_tick": 0, "state": "queued"},
    {"job_id": "a", "priority": 5, "due_tick": 4, "release_tick": 0, "state": "queued"},
]

ORACLE_CASES = (
    _case("smoke.priority_normal", "run_smoke_tests", "jobs", "validate_priority", [4], 4),
    _case("smoke.release_past", "run_smoke_tests", "jobs", "is_released", [1, 2], True),
    _case("smoke.selection_tie", "run_smoke_tests", "queues", "select_next", [_TIE_JOBS, 0], "a"),
    _case("smoke.transition_start", "run_smoke_tests", "state", "transition_state", ["queued", "start"], "running"),
    _case(
        "boundary.release_equal", "run_boundary_tests", "jobs", "is_released", [5, 5], True,
        evidence_tags=("boundary_failure",), fix_intent_hints=("change_comparison",),
    ),
    _case(
        "boundary.retry_limit_equal", "run_boundary_tests", "retries", "should_retry", [3, 3], False,
        evidence_tags=("boundary_failure",), fix_intent_hints=("change_comparison",),
    ),
    _case("boundary.priority_upper", "run_boundary_tests", "jobs", "validate_priority", [9], 9),
    _case(
        "null.tags_none", "run_null_missing_tests", "jobs", "normalize_tags", [None], [],
        evidence_tags=("null_exception",), fix_intent_hints=("add_missing_value_guard",),
    ),
    _case(
        "null.queue_limits_absent", "run_null_missing_tests", "config", "retry_limit",
        [{"default_retry_limit": 3}, "critical"], 3,
        evidence_tags=("missing_key_exception",), fix_intent_hints=("fix_config_default",),
    ),
    _case(
        "config.queue_name_trim", "run_config_matrix_tests", "config", "normalize_queue_name",
        [" Critical "], "critical", evidence_tags=("config_matrix_failure",),
        fix_intent_hints=("normalize_config_or_input",),
    ),
    _case(
        "config.alias_case", "run_config_matrix_tests", "config", "normalize_queue_name",
        ["FAST", {"fast": "critical"}], "critical", evidence_tags=("config_matrix_failure",),
        fix_intent_hints=("normalize_config_or_input",),
    ),
    _case(
        "config.queue_retry_limit", "run_config_matrix_tests", "config", "retry_limit",
        [{"queue_limits": {"critical": 5}, "default_retry_limit": 3}, " Critical "], 5,
        evidence_tags=("config_matrix_failure",), fix_intent_hints=("normalize_config_or_input",),
    ),
    _case("state.valid_completion", "run_state_sequence_tests", "state", "transition_state", ["running", "succeed"], "succeeded"),
    _case(
        "state.invalid_completion", "run_state_sequence_tests", "state", "transition_state",
        ["queued", "succeed"], expected_exception="ValueError", evidence_tags=("state_invariant_failure",),
        fix_intent_hints=("fix_state_transition",),
    ),
    _case(
        "state.queue_complete_moves", "run_state_sequence_tests", "queues", "complete_job",
        [{"running": ["job-1", "job-2"], "completed": []}, "job-1"],
        {"running": ["job-2"], "completed": ["job-1"]}, evidence_tags=("state_invariant_failure",),
        fix_intent_hints=("fix_state_transition",),
    ),
    _case("property.release_monotonic", "run_property_search", "jobs", "is_released", [5, 6], True),
    _case(
        "property.retry_cap", "run_property_search", "retries", "next_retry_tick", [10, 5, 2, 8], 18,
        evidence_tags=("spec_rule_failure",), fix_intent_hints=("align_calculation_order_with_spec",),
    ),
    _case("property.selection_deterministic", "run_property_search", "queues", "select_next", [_TIE_JOBS, 0], "a"),
    _case(
        "trace.tags_none", "inspect_traceback", "jobs", "normalize_tags", [None], [],
        evidence_tags=("null_exception",), fix_intent_hints=("add_missing_value_guard",),
    ),
    _case(
        "trace.queue_limits_absent", "inspect_traceback", "config", "retry_limit",
        [{"default_retry_limit": 3}, "critical"], 3, evidence_tags=("missing_key_exception",),
        fix_intent_hints=("fix_config_default",),
    ),
    _case(
        "coverage.release_equal", "inspect_coverage_spectrum", "jobs", "is_released", [0, 0], True,
        evidence_tags=("boundary_failure",), fix_intent_hints=("change_comparison",),
    ),
    _case(
        "coverage.selection_priority", "inspect_coverage_spectrum", "queues", "select_next",
        [_SELECTION_JOBS, 0], "high", evidence_tags=("spec_rule_failure",),
        fix_intent_hints=("align_selection_rule_with_spec",),
    ),
    _case("coverage.transition_retry", "inspect_coverage_spectrum", "state", "transition_state", ["failed", "retry"], "queued"),
    _case(
        "spec.priority_before_due", "inspect_spec_clause", "queues", "select_next",
        [_SELECTION_JOBS, 0], "high", evidence_tags=("spec_rule_failure",),
        fix_intent_hints=("align_selection_rule_with_spec",),
    ),
    _case(
        "spec.retry_cap_after_growth", "inspect_spec_clause", "retries", "next_retry_tick",
        [100, 4, 3, 10], 110, evidence_tags=("spec_rule_failure",),
        fix_intent_hints=("align_calculation_order_with_spec",),
    ),
)


ACTION_CASE_MAPPING = {
    action_id: [case["oracle_id"] for case in ORACLE_CASES if case["action_id"] == action_id]
    for action_id in ACTION_ORDER
}
ACTION_CASE_MAPPING["inspect_recent_diff"] = ["diff.exact_patch_identity"]


def _lf_bytes(text: str) -> bytes:
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return _sha256_bytes(_canonical_json(value).encode("utf-8"))


def _post_image(definition: dict[str, Any]) -> str:
    baseline = BASELINE_FILES[definition["target_path"]]
    before = definition["replacement_before"]
    if baseline.count(before) != 1:
        raise ValueError(f"{definition['input_id']} replacement anchor is not unique")
    return baseline.replace(before, definition["replacement_after"], 1)


def patch_text(definition: dict[str, Any]) -> str:
    path = definition["target_path"]
    return "".join(
        difflib.unified_diff(
            BASELINE_FILES[path].splitlines(keepends=True),
            _post_image(definition).splitlines(keepends=True),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
            lineterm="\n",
        )
    )


def build_manifest() -> dict[str, Any]:
    baseline_rows = [
        {
            "path": path,
            "size": len(_lf_bytes(content)),
            "sha256_lf": _sha256_bytes(_lf_bytes(content)),
        }
        for path, content in BASELINE_FILES.items()
    ]
    inputs = []
    for order, definition in enumerate(INPUT_DEFINITIONS, start=1):
        patch = patch_text(definition)
        post = _post_image(definition)
        public = {key: value for key, value in definition.items() if not key.startswith("replacement_")}
        public.update(
            {
                "order": order,
                "patch_path": f"patches/{definition['input_id']}.patch",
                "patch_size": len(_lf_bytes(patch)),
                "patch_sha256_lf": _sha256_bytes(_lf_bytes(patch)),
                "baseline_file_sha256_lf": _sha256_bytes(_lf_bytes(BASELINE_FILES[definition["target_path"]])),
                "post_image_size": len(_lf_bytes(post)),
                "post_image_sha256_lf": _sha256_bytes(_lf_bytes(post)),
                "replacement_operation_digest": _digest(
                    {
                        "path": definition["target_path"],
                        "before": definition["replacement_before"],
                        "after": definition["replacement_after"],
                    }
                ),
            }
        )
        inputs.append(public)
    payload = {
        "schema_version": DOMAIN_SCHEMA_VERSION,
        "domain_id": DOMAIN_ID,
        "domain_boundary": {
            "language": "pure deterministic Python",
            "forbidden_runtime_inputs": [
                "network", "filesystem_domain_io", "database", "subprocess", "thread",
                "async", "wall_clock", "locale", "operating_system_state",
            ],
            "time_model": "explicit integer ticks only",
        },
        "baseline_files": baseline_rows,
        "input_order": list(INPUT_ORDER),
        "inputs": inputs,
        "oracle_order": [case["oracle_id"] for case in ORACLE_CASES],
        "oracle_cases": list(ORACLE_CASES),
        "action_order": list(ACTION_ORDER),
        "action_case_mapping": ACTION_CASE_MAPPING,
    }
    return {"manifest_digest": _digest(payload), **payload}


def artifact_root() -> Path:
    return Path(__file__).resolve().parent / "artifacts" / "domain"


def write_frozen_artifacts(root: Path | None = None) -> None:
    destination = root or artifact_root()
    if destination.exists() and any(destination.rglob("*")):
        raise FileExistsError(f"refusing to overwrite non-empty artifact root: {destination}")
    baseline_root = destination / "baseline"
    patch_root = destination / "patches"
    for relative, content in BASELINE_FILES.items():
        path = baseline_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(_lf_bytes(content))
    patch_root.mkdir(parents=True, exist_ok=True)
    for definition in INPUT_DEFINITIONS:
        (patch_root / f"{definition['input_id']}.patch").write_bytes(_lf_bytes(patch_text(definition)))
    (destination / "manifest.json").write_text(
        json.dumps(build_manifest(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Author frozen P2h domain artifacts before outcome execution.")
    parser.add_argument("--write", action="store_true", help="write the tracked outcome-free artifacts")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    if not args.write:
        parser.error("--write is required")
    write_frozen_artifacts(args.output)


if __name__ == "__main__":
    main()
