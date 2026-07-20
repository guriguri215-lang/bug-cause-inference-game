"""Frozen P2h task-scheduler second-domain replication audit.

The runner validates the outcome-free domain before selecting any policy.  It
reuses the accepted P1b action registry, policy selectors, posterior updates,
settings, and stop predicate without modifying their semantics.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
import sys
import traceback
from collections import Counter, defaultdict
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
from types import ModuleType
from typing import Any

from bug_cause_inference.p1b import execution as p1b_execution
from bug_cause_inference.p1b import policies as p1b_policies
from bug_cause_inference.p1b.actions import P1B_ACTION_SPECS
from bug_cause_inference.p1b.models import (
    P1B_CAUSE_CATEGORIES,
    P1B_FIX_INTENT_CATEGORIES,
    P1BObservation,
    P1BRunResult,
    P1BSettings,
    P1BStepTrace,
    P1BVariant,
    rank_distribution,
    uniform_distribution,
    update_distribution,
)
from bug_cause_inference.p2h.domain_definition import (
    ACTION_CASE_MAPPING,
    ACTION_ORDER,
    BASELINE_FILES,
    DOMAIN_ID,
    DOMAIN_SCHEMA_VERSION,
    INPUT_DEFINITIONS,
    INPUT_ORDER,
    ORACLE_CASES,
    artifact_root,
    build_manifest,
    patch_text,
)


ANALYSIS_PHASE = "P2h"
AUDIT_ID = "p2h_task_scheduler_second_domain_replication_audit_v1"
REPORT_SCHEMA_VERSION = "p2h_task_scheduler_second_domain_replication.v1"
ROLE = "analysis_only_fixed_input_second_domain_replication"
EXPECTED_MANIFEST_DIGEST = "343746ea65d6649726e116e529c8a0e83d07f7c8d72e76c2074e21f24941304b"
EXPECTED_MANIFEST_FILE_SHA256_LF = "16bb5876d857e74fd4a8f63f43ab701a60fab018a2c9969d889b11d085227316"
EXPECTED_DEPENDENCY_DIGEST = "c3ca2a00d1729b003a6ac12ba73853cb3d1c86710d0fa29b4aee61e55c19179f"
FORMAL_POLICY_IDS = tuple(p1b_policies.P1B_POLICIES[1:])
EXPECTED_FORMAL_POLICY_IDS = (
    "fixed_checklist",
    "test_first",
    "coverage_first",
    "recent_diff_first",
    "cause_only_p1a_style",
    "expected_utility_per_cost",
)
EXPECTED_ACTION_COSTS = {
    "run_smoke_tests": 1,
    "run_boundary_tests": 2,
    "run_null_missing_tests": 2,
    "run_config_matrix_tests": 3,
    "run_state_sequence_tests": 4,
    "run_property_search": 5,
    "inspect_traceback": 1,
    "inspect_coverage_spectrum": 3,
    "inspect_recent_diff": 2,
    "inspect_spec_clause": 2,
}
EXPECTED_ACTION_SPEC_PROJECTION = {
    "run_smoke_tests": ["run_smoke_tests", 1, "test_failure", ["specification_mismatch", "missing_null_handling"], 0.45, 0.25],
    "run_boundary_tests": ["run_boundary_tests", 2, "boundary_counterexample", ["boundary_condition"], 0.70, 0.45],
    "run_null_missing_tests": ["run_null_missing_tests", 2, "exception_trace", ["missing_null_handling"], 0.70, 0.55],
    "run_config_matrix_tests": ["run_config_matrix_tests", 3, "config_counterexample", ["configuration_environment"], 0.70, 0.45],
    "run_state_sequence_tests": ["run_state_sequence_tests", 4, "state_sequence_counterexample", ["state_order_dependence"], 0.75, 0.55],
    "run_property_search": [
        "run_property_search",
        5,
        "property_counterexample",
        ["boundary_condition", "state_order_dependence", "specification_mismatch"],
        0.65,
        0.35,
    ],
    "inspect_traceback": [
        "inspect_traceback",
        1,
        "exception_trace",
        ["missing_null_handling", "configuration_environment"],
        0.30,
        0.70,
    ],
    "inspect_coverage_spectrum": ["inspect_coverage_spectrum", 3, "coverage_suspicious_location", [], 0.15, 0.85],
    "inspect_recent_diff": [
        "inspect_recent_diff",
        2,
        "recent_diff_signal",
        ["configuration_environment", "state_order_dependence", "boundary_condition"],
        0.20,
        0.55,
    ],
    "inspect_spec_clause": [
        "inspect_spec_clause",
        2,
        "spec_clause_mismatch",
        ["specification_mismatch", "boundary_condition", "configuration_environment"],
        0.45,
        0.50,
    ],
}
EXPECTED_POLICY_ORDER_PROJECTION = {
    "fixed_checklist": [
        "run_smoke_tests",
        "run_boundary_tests",
        "run_null_missing_tests",
        "run_config_matrix_tests",
        "run_state_sequence_tests",
        "inspect_coverage_spectrum",
    ],
    "test_first": [
        "run_smoke_tests",
        "run_boundary_tests",
        "run_null_missing_tests",
        "run_config_matrix_tests",
        "run_state_sequence_tests",
        "run_property_search",
        "inspect_traceback",
        "inspect_coverage_spectrum",
        "inspect_spec_clause",
        "inspect_recent_diff",
    ],
    "recent_diff_first": [
        "inspect_recent_diff",
        "run_smoke_tests",
        "run_boundary_tests",
        "run_config_matrix_tests",
        "run_null_missing_tests",
        "run_state_sequence_tests",
        "inspect_coverage_spectrum",
        "inspect_spec_clause",
    ],
}
EXPECTED_EXECUTION_WEIGHT_PROJECTION = {
    "cause_hint_by_tag": {
        "boundary_failure": "boundary_condition",
        "null_exception": "missing_null_handling",
        "missing_key_exception": "missing_null_handling",
        "config_matrix_failure": "configuration_environment",
        "config_parse_exception": "configuration_environment",
        "state_invariant_failure": "state_order_dependence",
        "idempotency_failure": "state_order_dependence",
        "stale_state_failure": "state_order_dependence",
        "spec_rule_failure": "specification_mismatch",
    },
    "cause_hint_weight": 3.0,
    "fix_intent_hint_weight": 2.5,
    "failing_function_weight": 1.8,
    "stack_function_weight": 2.2,
    "coverage_location_weight": 10.0,
    "stack_tie_breaker_weight": 0.25,
    "recent_diff_location_weight": 4.0,
}
FIXED_SETTINGS = {
    "budget_limit": 12,
    "max_steps": 6,
    "failure_cost": 14,
    "bug_presence_threshold": 0.75,
    "no_bug_probability_threshold": 0.80,
    "location_top1_threshold": 0.50,
    "cause_top1_threshold": 0.60,
    "min_expected_utility_per_cost": 0.03,
    "rng_seed": 0,
}
LOCATION_CANDIDATES = (
    "jobs.validate_priority",
    "jobs.is_released",
    "jobs.normalize_tags",
    "queues.select_next",
    "queues.complete_job",
    "retries.should_retry",
    "retries.next_retry_tick",
    "config.normalize_queue_name",
    "config.retry_limit",
    "state.transition_state",
)
EXPECTED_BUGGY_FAMILIES = {
    "boundary_condition": 2,
    "missing_null_handling": 2,
    "configuration_environment": 2,
    "state_order_dependence": 2,
    "specification_mismatch": 2,
}
EXPECTED_CLEAN_FAMILIES = (
    "boundary_adjacent_valid_behavior",
    "optional_absence_default",
    "config_equivalent_normalization",
    "valid_state_sequence",
    "nonintuitive_spec_conformance",
)
EXPECTED_STOP_PRECEDENCE = (
    "no_bug_probability_threshold",
    "bug_confidence_threshold",
    "budget_limit",
    "max_steps",
    "low_expected_utility",
    "no_available_actions",
)
EXPECTED_TOP_LEVEL_FIELDS = (
    "schema_version",
    "analysis_phase",
    "audit_id",
    "role",
    "domain_id",
    "domain_schema_version",
    "claim_boundary",
    "support",
    "action_costs",
    "settings",
    "false_positive_definition",
    "undefined_value",
    "tie_rule",
    "outcome_free_validation",
    "pre_outcome_freeze_identity",
    "rows",
    "aggregates",
    "identities",
    "summary_digest",
)
EXPECTED_ROW_FIELDS = (
    "input_id",
    "policy_id",
    "is_buggy",
    "cause_family",
    "clean_family",
    "target_function",
    "fix_intent",
    "bug_discovery",
    "first_failure_observed",
    "first_failure_cost",
    "cost_to_first_failure_with_penalty",
    "clean_false_positive",
    "location_rank",
    "location_top1",
    "location_top3",
    "location_reciprocal_rank",
    "cause_top1",
    "fix_intent_top1",
    "execution_failure_observed",
    "bug_detected_observation",
    "no_bug_evidence_observed",
    "executed_actions",
    "action_count",
    "cumulative_cost",
    "terminal_reason",
    "final_bug_presence_posterior",
    "final_cause_posterior",
    "final_location_posterior",
    "final_fix_intent_posterior",
    "trace",
)
EXPECTED_STEP_FIELDS = (
    "step",
    "policy",
    "selected_action",
    "observation",
    "prior_bug_presence_posterior",
    "updated_bug_presence_posterior",
    "prior_cause_posterior",
    "updated_cause_posterior",
    "prior_location_posterior",
    "updated_location_posterior",
    "prior_fix_intent_posterior",
    "updated_fix_intent_posterior",
    "cumulative_cost",
    "action_scores",
)
EXPECTED_CLAIM_BOUNDARY = {
    "analysis_only": True,
    "fixed_input": True,
    "hand_authored_single_second_domain": True,
    "non_iid": True,
    "non_causal": True,
    "non_deployable": True,
    "does_not_establish_policy_ranking_or_superiority": True,
    "does_not_establish_population_or_production_generalization": True,
}
FREEZE_IDENTITY_SCHEMA_VERSION = "p2h_pre_outcome_freeze_identity.v1"
EXPECTED_SPECIFICATION_IDENTITY = {
    "path": "claude_review/206_p2h_task_scheduler_second_domain_replication_specification_2026-07-19.md",
    "size": 20828,
    "sha256_lf": "544001a42c144130483ae5fd31bf2740f70f43f7819821d4f67fef6a1445a6db",
}


class P2HContractError(RuntimeError):
    """Raised when a frozen P2h identity or semantic contract drifts."""


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _lf_bytes(path: Path) -> bytes:
    return path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def _file_identity(path: Path, *, root: Path) -> dict[str, Any]:
    content = _lf_bytes(path)
    return {
        "path": path.relative_to(root).as_posix(),
        "size": len(content),
        "sha256_lf": hashlib.sha256(content).hexdigest(),
    }


def current_dependency_identity() -> dict[str, Any]:
    """Return accepted P1b dependencies used by P2h, with portable identities."""

    package_root = Path(__file__).resolve().parents[1]
    source_root = package_root.parents[1]
    paths = [
        package_root / "p1b" / name
        for name in ("models.py", "actions.py", "policies.py", "execution.py")
    ]
    files = [_file_identity(path, root=source_root) for path in paths]
    payload = {
        "files": files,
        "formal_policy_ids": list(FORMAL_POLICY_IDS),
        "action_costs": {key: P1B_ACTION_SPECS[key].cost for key in ACTION_ORDER},
        "settings": asdict(P1BSettings()),
        "stop_precedence": list(EXPECTED_STOP_PRECEDENCE),
    }
    return {"digest": canonical_digest(payload), **payload}


def _action_spec_projection() -> dict[str, Any]:
    return {
        key: [
            spec.action_id,
            spec.cost,
            spec.observation_type,
            list(spec.strong_causes),
            spec.discovery_power,
            spec.location_power,
        ]
        for key, spec in P1B_ACTION_SPECS.items()
    }


def _policy_order_projection() -> dict[str, Any]:
    return {
        "fixed_checklist": list(p1b_policies.FIXED_CHECKLIST_ORDER),
        "test_first": list(p1b_policies.TEST_FIRST_ORDER),
        "recent_diff_first": list(p1b_policies.RECENT_DIFF_FIRST_ORDER),
    }


def _execution_weight_projection() -> dict[str, Any]:
    return {
        "cause_hint_by_tag": dict(p1b_execution.CAUSE_HINT_BY_TAG),
        "cause_hint_weight": p1b_execution.CAUSE_HINT_WEIGHT,
        "fix_intent_hint_weight": p1b_execution.FIX_INTENT_HINT_WEIGHT,
        "failing_function_weight": p1b_execution.FAILING_FUNCTION_WEIGHT,
        "stack_function_weight": p1b_execution.STACK_FUNCTION_WEIGHT,
        "coverage_location_weight": p1b_execution.COVERAGE_LOCATION_WEIGHT,
        "stack_tie_breaker_weight": p1b_execution.STACK_TIE_BREAKER_WEIGHT,
        "recent_diff_location_weight": p1b_execution.RECENT_DIFF_LOCATION_WEIGHT,
    }


def _policy_behavior_projection() -> dict[str, Any]:
    state = p1b_policies._State(
        bug_presence=0.5,
        cause_posterior=uniform_distribution(P1B_CAUSE_CATEGORIES),
        location_posterior=uniform_distribution(LOCATION_CANDIDATES),
        fix_intent_posterior=uniform_distribution(P1B_FIX_INTENT_CATEGORIES),
        executed_actions=[],
        cumulative_cost=0,
        current_step=0,
        bug_detected=False,
        execution_context=None,
    )
    choices = {
        policy: p1b_policies.choose_action(policy, state, 12, random.Random(0))
        for policy in FORMAL_POLICY_IDS
    }
    strong_state = p1b_policies._State(
        bug_presence=0.8,
        cause_posterior={"boundary_condition": 1.0},
        location_posterior={"jobs.is_released": 1.0},
        fix_intent_posterior={"change_comparison": 1.0},
        executed_actions=[],
        cumulative_cost=12,
        current_step=6,
        bug_detected=True,
        execution_context=None,
    )
    budget_state = p1b_policies._State(
        bug_presence=0.5,
        cause_posterior={"boundary_condition": 1.0},
        location_posterior={"jobs.is_released": 1.0},
        fix_intent_posterior={"change_comparison": 1.0},
        executed_actions=[],
        cumulative_cost=12,
        current_step=6,
        bug_detected=False,
        execution_context=None,
    )
    max_step_state = p1b_policies._State(
        bug_presence=0.5,
        cause_posterior={"boundary_condition": 1.0},
        location_posterior={"jobs.is_released": 1.0},
        fix_intent_posterior={"change_comparison": 1.0},
        executed_actions=[],
        cumulative_cost=0,
        current_step=6,
        bug_detected=False,
        execution_context=None,
    )
    settings = P1BSettings(**FIXED_SETTINGS)
    return {
        "stable_seed": p1b_policies._stable_seed("P2H-BUG-001", 0),
        "update_bug_presence": [
            p1b_policies._update_bug_presence(0.5, True, False),
            p1b_policies._update_bug_presence(0.5, False, True),
            p1b_policies._update_bug_presence(0.5, False, False),
        ],
        "initial_choices": choices,
        "initial_score_top": p1b_policies.score_actions(state, 12)[0],
        "stop_no_bug_precedence": p1b_policies._check_stop(
            p1b_policies._State(
                bug_presence=0.2,
                cause_posterior={"boundary_condition": 1.0},
                location_posterior={"jobs.is_released": 1.0},
                fix_intent_posterior={"change_comparison": 1.0},
                executed_actions=[],
                cumulative_cost=12,
                current_step=6,
                bug_detected=True,
                execution_context=None,
            ),
            settings,
            0.0,
        ),
        "stop_bug_precedence": p1b_policies._check_stop(strong_state, settings, 0.0),
        "stop_budget_precedence": p1b_policies._check_stop(budget_state, settings, 0.0),
        "stop_max_steps": p1b_policies._check_stop(max_step_state, settings, 1.0),
        "stop_low_expected_utility": p1b_policies._check_stop(state, settings, 0.01),
        "no_available_action": p1b_policies.choose_action(
            "fixed_checklist",
            p1b_policies._State(
                bug_presence=0.5,
                cause_posterior=uniform_distribution(P1B_CAUSE_CATEGORIES),
                location_posterior=uniform_distribution(LOCATION_CANDIDATES),
                fix_intent_posterior=uniform_distribution(P1B_FIX_INTENT_CATEGORIES),
                executed_actions=list(ACTION_ORDER),
                cumulative_cost=0,
                current_step=0,
                bug_detected=False,
                execution_context=None,
            ),
            12,
            random.Random(0),
        ),
    }


EXPECTED_POLICY_BEHAVIOR_PROJECTION = {
    "stable_seed": 3724,
    "update_bug_presence": [0.85, 0.32, 0.55],
    "initial_choices": {
        "fixed_checklist": "run_smoke_tests",
        "test_first": "run_smoke_tests",
        "coverage_first": "run_smoke_tests",
        "recent_diff_first": "inspect_recent_diff",
        "cause_only_p1a_style": "inspect_traceback",
        "expected_utility_per_cost": "inspect_traceback",
    },
    "initial_score_top": {
        "action": "inspect_traceback",
        "cost": 1,
        "expected_utility": 1.45,
        "expected_utility_per_cost": 1.45,
        "discovery_utility": 0.15,
        "cause_utility": 0.4,
        "location_utility": 0.7,
    },
    "stop_no_bug_precedence": "no_bug_probability_threshold",
    "stop_bug_precedence": "bug_confidence_threshold",
    "stop_budget_precedence": "budget_limit",
    "stop_max_steps": "max_steps",
    "stop_low_expected_utility": "low_expected_utility",
    "no_available_action": None,
}


def _validate_registry_contract() -> None:
    if FORMAL_POLICY_IDS != EXPECTED_FORMAL_POLICY_IDS:
        raise P2HContractError("formal six policy identity/order drifted")
    if tuple(P1B_ACTION_SPECS) != ACTION_ORDER:
        raise P2HContractError("action registry identity/order drifted")
    observed_costs = {key: P1B_ACTION_SPECS[key].cost for key in ACTION_ORDER}
    if observed_costs != EXPECTED_ACTION_COSTS:
        raise P2HContractError("action costs drifted")
    if asdict(P1BSettings()) != FIXED_SETTINGS:
        raise P2HContractError("P1b settings drifted")
    if _action_spec_projection() != EXPECTED_ACTION_SPEC_PROJECTION:
        raise P2HContractError("P1BActionSpec semantics drifted")
    if _policy_order_projection() != EXPECTED_POLICY_ORDER_PROJECTION:
        raise P2HContractError("policy ordering semantics drifted")
    if _execution_weight_projection() != EXPECTED_EXECUTION_WEIGHT_PROJECTION:
        raise P2HContractError("execution evidence weights drifted")
    if _policy_behavior_projection() != EXPECTED_POLICY_BEHAVIOR_PROJECTION:
        raise P2HContractError("policy score/select/update/stop behavior drifted")
    if current_dependency_identity()["digest"] != EXPECTED_DEPENDENCY_DIGEST:
        raise P2HContractError("accepted P1b dependency identity drifted")


def _validate_manifest_artifacts(manifest: Mapping[str, Any]) -> None:
    expected = build_manifest()
    if dict(manifest) != expected:
        raise P2HContractError("tracked domain manifest differs from authoring definition")
    if expected["manifest_digest"] != EXPECTED_MANIFEST_DIGEST:
        raise P2HContractError("frozen domain manifest identity drifted")
    root = artifact_root()
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        raise P2HContractError("tracked domain manifest is missing")
    loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
    if loaded != expected:
        raise P2HContractError("tracked manifest bytes do not decode to the frozen manifest")
    if hashlib.sha256(_lf_bytes(manifest_path)).hexdigest() != EXPECTED_MANIFEST_FILE_SHA256_LF:
        raise P2HContractError("raw tracked manifest LF identity drifted")
    for row in expected["baseline_files"]:
        path = root / "baseline" / row["path"]
        if not path.is_file() or len(_lf_bytes(path)) != row["size"]:
            raise P2HContractError(f"baseline file identity drift: {row['path']}")
        if hashlib.sha256(_lf_bytes(path)).hexdigest() != row["sha256_lf"]:
            raise P2HContractError(f"baseline file hash drift: {row['path']}")
    for row, definition in zip(expected["inputs"], INPUT_DEFINITIONS, strict=True):
        path = root / row["patch_path"]
        if not path.is_file() or _lf_bytes(path) != patch_text(definition).encode("utf-8"):
            raise P2HContractError(f"patch artifact drift: {row['input_id']}")
    expected_paths = {"manifest.json"}
    expected_paths.update(f"baseline/{row['path']}" for row in expected["baseline_files"])
    expected_paths.update(row["patch_path"] for row in expected["inputs"])
    actual_paths = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    }
    if actual_paths != expected_paths:
        raise P2HContractError("tracked domain tree contains missing or unexpected files")


def repository_root() -> Path:
    return Path(__file__).resolve().parents[3]


def freeze_identity_path() -> Path:
    return Path(__file__).resolve().parent / "artifacts" / "pre_outcome_freeze_identity.json"


def implementation_identity_paths() -> tuple[Path, ...]:
    root = repository_root()
    paths = [
        root / "src" / "bug_cause_inference" / "p2h" / "__init__.py",
        root / "src" / "bug_cause_inference" / "p2h" / "domain_definition.py",
        root / "src" / "bug_cause_inference" / "p2h" / "task_scheduler_replication.py",
        root / "src" / "bug_cause_inference" / "p2h" / "reports.py",
        root / "tests" / "test_p2h_task_scheduler_replication.py",
        root / "tests" / "test_p2h_reports.py",
    ]
    paths.extend(
        path
        for path in artifact_root().rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    )
    return tuple(sorted(paths, key=lambda path: path.relative_to(root).as_posix()))


def current_implementation_identity() -> dict[str, Any]:
    root = repository_root()
    rows = [_file_identity(path, root=root) for path in implementation_identity_paths()]
    payload = {"files": rows}
    return {"digest": canonical_digest(payload), **payload}


def validate_pre_outcome_freeze_identity() -> dict[str, Any]:
    path = freeze_identity_path()
    if not path.is_file():
        raise P2HContractError("pre-outcome freeze identity is missing")
    try:
        frozen = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise P2HContractError("pre-outcome freeze identity is invalid JSON") from exc
    if tuple(frozen) != (
        "schema_version",
        "specification_identity",
        "formal_policy_outcomes_executed_before_freeze",
        "implementation_identity",
    ):
        raise P2HContractError("pre-outcome freeze identity schema/order drifted")
    if frozen["schema_version"] != FREEZE_IDENTITY_SCHEMA_VERSION:
        raise P2HContractError("pre-outcome freeze identity schema version drifted")
    if frozen["formal_policy_outcomes_executed_before_freeze"] != 0:
        raise P2HContractError("pre-outcome outcome count is not zero")
    if frozen["implementation_identity"] != current_implementation_identity():
        raise P2HContractError("current implementation differs from the pre-outcome freeze")
    spec = frozen["specification_identity"]
    if spec != EXPECTED_SPECIFICATION_IDENTITY:
        raise P2HContractError("pre-outcome specification identity drifted")
    return frozen


def _portable(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_portable(item) for item in value]
    if isinstance(value, list):
        return [_portable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _portable(item) for key, item in value.items()}
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    raise P2HContractError(f"oracle returned a non-portable value: {type(value).__name__}")


def _source_for(definition: Mapping[str, Any] | None) -> dict[str, str]:
    source = dict(BASELINE_FILES)
    if definition is None:
        return source
    path = str(definition["target_path"])
    before = str(definition["replacement_before"])
    after = str(definition["replacement_after"])
    if source[path].count(before) != 1:
        raise P2HContractError(f"non-unique patch anchor for {definition['input_id']}")
    source[path] = source[path].replace(before, after, 1)
    return source


def _load_modules(source: Mapping[str, str], namespace: str) -> dict[str, ModuleType]:
    modules: dict[str, ModuleType] = {}
    for path in BASELINE_FILES:
        if path.endswith("/__init__.py"):
            continue
        name = Path(path).stem
        module = ModuleType(f"{namespace}.{name}")
        module.__file__ = f"<{namespace}/{path}>"
        code = compile(source[path], module.__file__, "exec")
        exec(code, module.__dict__)
        modules[name] = module
    return modules


@contextmanager
def _module_trace(modules: Mapping[str, ModuleType]) -> Iterator[list[str]]:
    module_names = {module.__name__: name for name, module in modules.items()}
    calls: list[str] = []
    previous = sys.gettrace()

    def tracer(frame: Any, event: str, arg: Any) -> Any:
        del arg
        if event == "call" and frame.f_globals.get("__name__") in module_names:
            calls.append(f"{module_names[frame.f_globals['__name__']]}.{frame.f_code.co_name}")
        return tracer

    sys.settrace(tracer)
    try:
        yield calls
    finally:
        sys.settrace(previous)


def _stack_functions(exc: BaseException, modules: Mapping[str, ModuleType]) -> list[str]:
    module_names = {module.__name__: name for name, module in modules.items()}
    functions: list[str] = []
    for frame, _ in traceback.walk_tb(exc.__traceback__):
        module_name = frame.f_globals.get("__name__")
        if module_name in module_names:
            functions.append(f"{module_names[module_name]}.{frame.f_code.co_name}")
    return list(dict.fromkeys(functions))


def _run_case(case: Mapping[str, Any], modules: Mapping[str, ModuleType]) -> dict[str, Any]:
    function = getattr(modules[str(case["module"])], str(case["function"]))
    exception_type: str | None = None
    stack_functions: list[str] = []
    actual: Any = None
    with _module_trace(modules) as calls:
        try:
            actual = _portable(function(*deepcopy(case["args"]), **deepcopy(case["kwargs"])))
        except Exception as exc:  # noqa: BLE001 - the exception is the structured oracle result
            exception_type = type(exc).__name__
            actual = {"raised": exception_type, "message": str(exc)}
            stack_functions = _stack_functions(exc, modules)
    expected_exception = case["expected_exception"]
    passed = (
        exception_type == expected_exception
        if expected_exception is not None
        else exception_type is None and actual == case["expected"]
    )
    expected: Any = (
        {"raises": expected_exception} if expected_exception is not None else case["expected"]
    )
    return {
        "test_id": str(case["oracle_id"]),
        "group": str(case["action_id"]),
        "passed": passed,
        "expected": expected,
        "actual": actual,
        "exception_type": exception_type,
        "reproduction_input": str(case["oracle_id"]),
        "executed_functions": sorted(set(calls)),
        "stack_functions": stack_functions,
        "evidence_tags": list(case["evidence_tags"]),
        "fix_intent_hints": list(case["fix_intent_hints"]),
    }


def _oracle_results(modules: Mapping[str, ModuleType]) -> list[dict[str, Any]]:
    return [_run_case(case, modules) for case in ORACLE_CASES]


def validate_outcome_free_contract() -> dict[str, Any]:
    """Validate identities and every baseline/variant oracle without a policy run."""

    _validate_registry_contract()
    manifest = build_manifest()
    _validate_manifest_artifacts(manifest)
    if tuple(manifest["input_order"]) != INPUT_ORDER:
        raise P2HContractError("input identity/order drifted")
    if len(INPUT_DEFINITIONS) != 15:
        raise P2HContractError("P2h requires exactly 15 inputs")
    buggy = [item for item in INPUT_DEFINITIONS if item["is_buggy"]]
    clean = [item for item in INPUT_DEFINITIONS if not item["is_buggy"]]
    family_counts: dict[str, int] = defaultdict(int)
    for item in buggy:
        family_counts[str(item["cause_family"])] += 1
    if len(buggy) != 10 or len(clean) != 5 or dict(family_counts) != EXPECTED_BUGGY_FAMILIES:
        raise P2HContractError("buggy input strata/family balance drifted")
    if tuple(item["clean_family"] for item in clean) != EXPECTED_CLEAN_FAMILIES:
        raise P2HContractError("clean family identity/order drifted")
    if set(ACTION_CASE_MAPPING) != set(ACTION_ORDER):
        raise P2HContractError("action-case mapping does not cover the exact action registry")
    baseline = _oracle_results(_load_modules(_source_for(None), "p2h_baseline"))
    if any(not result["passed"] for result in baseline):
        raise P2HContractError("baseline validity oracle failed")
    validation_rows = []
    for definition in INPUT_DEFINITIONS:
        modules = _load_modules(_source_for(definition), f"p2h_{definition['input_id'].lower()}")
        results = _oracle_results(modules)
        failed = [row["test_id"] for row in results if not row["passed"]]
        expected = list(definition["expected_failing_oracle_ids"])
        if failed != expected:
            raise P2HContractError(
                f"oracle failure set drift for {definition['input_id']}: {failed!r} != {expected!r}"
            )
        validation_rows.append(
            {
                "input_id": definition["input_id"],
                "failed_oracle_ids": failed,
                "passed_oracle_count": len(results) - len(failed),
            }
        )
    payload = {
        "manifest_digest": manifest["manifest_digest"],
        "baseline_oracle_count": len(baseline),
        "input_validation": validation_rows,
        "dependency_identity": current_dependency_identity(),
    }
    return {"validation_digest": canonical_digest(payload), **payload}


def _variant(definition: Mapping[str, Any]) -> P1BVariant:
    module = Path(str(definition["target_path"])).stem
    function = str(definition["target_function"]).split(".")[-1]
    return P1BVariant(
        variant_id=str(definition["input_id"]),
        is_buggy=bool(definition["is_buggy"]),
        true_cause_category=definition["cause_family"],
        target_module=f"{module}.py",
        target_function=function,
        trigger_condition=str(definition["trigger"]),
        expected_behavior=str(definition["expected_behavior"]),
        actual_behavior=str(definition["actual_behavior"]),
        fix_intent_category=definition["fix_intent"],
        expected_clean_behavior=(
            str(definition["expected_behavior"]) if not definition["is_buggy"] else None
        ),
    )


def _recent_diff_observation(definition: Mapping[str, Any]) -> P1BObservation:
    spec = P1B_ACTION_SPECS["inspect_recent_diff"]
    patch = patch_text(dict(definition))
    changed_function = str(definition["target_function"])
    if changed_function not in LOCATION_CANDIDATES:
        raise P2HContractError("recent-diff function is outside the frozen P2h location universe")
    return P1BObservation(
        action_id="inspect_recent_diff",
        cost=spec.cost,
        observation_type=spec.observation_type,
        summary="inspect_recent_diff observed the frozen task-scheduler patch identity.",
        no_bug_evidence=False,
        location_scores={changed_function: p1b_execution.RECENT_DIFF_LOCATION_WEIGHT},
        evidence_source="p2h_frozen_patch_identity",
        diff_artifact_path=f"patches/{definition['input_id']}.patch",
        changed_files=[str(definition["target_path"])],
        changed_functions=[changed_function],
        diff_excerpt=patch,
    )


def _coverage_observation(results: list[dict[str, Any]]) -> P1BObservation:
    """Project frozen P2h cases through the accepted inspection-only coverage semantics."""

    spec = P1B_ACTION_SPECS["inspect_coverage_spectrum"]
    failed_results = [result for result in results if not result["passed"]]
    passed_results = [result for result in results if result["passed"]]
    coverage_suspicion = p1b_execution._coverage_suspicion_from_results(results)
    coverage_counts = p1b_execution._coverage_counts_from_results(results)
    stack_functions = p1b_execution._aggregate_stack_functions(failed_results)
    location_scores = p1b_execution._location_scores_from_coverage(
        coverage_suspicion, stack_functions
    )
    if failed_results:
        top_functions = sorted(
            coverage_suspicion.items(), key=lambda item: (-item[1], item[0])
        )[:3]
        top_summary = ", ".join(
            f"{function}={score:.6f}" for function, score in top_functions
        ) or "none"
        summary = (
            "inspect_coverage_spectrum computed Ochiai over "
            f"{len(failed_results)} failing and {len(passed_results)} passing frozen P2h cases; "
            f"top suspicious functions: {top_summary}."
        )
    else:
        summary = (
            "inspect_coverage_spectrum found no failing frozen P2h cases. "
            "Coverage suspicion is empty because Ochiai requires at least one failing case."
        )
    return P1BObservation(
        action_id="inspect_coverage_spectrum",
        cost=spec.cost,
        observation_type=spec.observation_type,
        summary=summary,
        bug_detected=bool(failed_results),
        failure_found=False,
        no_bug_evidence=not failed_results,
        location_scores=location_scores,
        evidence_source="execution_grounded",
        test_results=results,
        failed_test_ids=[result["test_id"] for result in failed_results],
        passed_test_ids=[result["test_id"] for result in passed_results],
        executed_functions=p1b_execution._aggregate_functions(results),
        failing_executed_functions=p1b_execution._aggregate_functions(results, passed=False),
        passing_executed_functions=p1b_execution._aggregate_functions(results, passed=True),
        stack_functions=stack_functions,
        coverage_suspicion=coverage_suspicion,
        coverage_counts=coverage_counts,
    )


def _run_action(
    action_id: str,
    definition: Mapping[str, Any],
    modules: Mapping[str, ModuleType],
) -> P1BObservation:
    spec = P1B_ACTION_SPECS[action_id]
    if action_id == "inspect_recent_diff":
        return _recent_diff_observation(definition)
    case_ids = set(ACTION_CASE_MAPPING[action_id])
    cases = [case for case in ORACLE_CASES if case["oracle_id"] in case_ids]
    if [case["oracle_id"] for case in cases] != ACTION_CASE_MAPPING[action_id]:
        raise P2HContractError(f"action-case order drifted for {action_id}")
    results = [_run_case(case, modules) for case in cases]
    if action_id == "inspect_coverage_spectrum":
        return _coverage_observation(results)
    return p1b_execution._observation_from_results(
        action_id=action_id,
        cost=spec.cost,
        observation_type=spec.observation_type,
        results=results,
    )


def _select_policy_action(
    policy_id: str,
    state: p1b_policies._State,
    remaining_budget: int,
    rng: random.Random,
) -> str | None:
    """Policy-visible adapter: no input identity, label, truth, or oracle map."""

    return p1b_policies.choose_action(policy_id, state, remaining_budget, rng)


def _run_policy(
    definition: Mapping[str, Any],
    policy_id: str,
    modules: Mapping[str, ModuleType],
) -> P1BRunResult:
    if policy_id not in FORMAL_POLICY_IDS:
        raise P2HContractError("policy is outside the frozen formal six")
    variant = _variant(definition)
    settings = P1BSettings(**FIXED_SETTINGS)
    state = p1b_policies._State(
        bug_presence=0.5,
        cause_posterior=uniform_distribution(P1B_CAUSE_CATEGORIES),
        location_posterior=uniform_distribution(LOCATION_CANDIDATES),
        fix_intent_posterior=uniform_distribution(P1B_FIX_INTENT_CATEGORIES),
        executed_actions=[],
        cumulative_cost=0,
        current_step=0,
        bug_detected=False,
        execution_context=None,
    )
    trace: list[P1BStepTrace] = []
    first_failure_cost: int | None = None
    reproduction_input: str | None = None
    rng = random.Random(p1b_policies._stable_seed(variant.variant_id, settings.rng_seed))
    while True:
        remaining = settings.budget_limit - state.cumulative_cost
        scores = p1b_policies.score_actions(state, remaining)
        best = scores[0]["expected_utility_per_cost"] if scores else None
        stop_reason = p1b_policies._check_stop(state, settings, best)
        if stop_reason is not None:
            break
        action_id = _select_policy_action(policy_id, state, remaining, rng)
        if action_id is None:
            stop_reason = "no_available_actions"
            break
        prior_bug = state.bug_presence
        prior_cause = dict(state.cause_posterior)
        prior_location = dict(state.location_posterior)
        prior_fix = dict(state.fix_intent_posterior)
        observation = _run_action(action_id, definition, modules)
        state.executed_actions.append(action_id)
        state.cumulative_cost += observation.cost
        state.current_step += 1
        state.bug_detected = state.bug_detected or observation.bug_detected
        state.bug_presence = p1b_policies._update_bug_presence(
            state.bug_presence, observation.bug_detected, observation.no_bug_evidence
        )
        state.cause_posterior = update_distribution(state.cause_posterior, observation.cause_scores)
        state.location_posterior = update_distribution(state.location_posterior, observation.location_scores)
        state.fix_intent_posterior = update_distribution(
            state.fix_intent_posterior, observation.fix_intent_scores
        )
        if observation.reproduction_input and reproduction_input is None:
            reproduction_input = observation.reproduction_input
        if observation.failure_found and first_failure_cost is None:
            first_failure_cost = state.cumulative_cost
        trace.append(
            P1BStepTrace(
                step=state.current_step,
                policy=policy_id,
                selected_action=action_id,
                observation=observation,
                prior_bug_presence_posterior=prior_bug,
                updated_bug_presence_posterior=state.bug_presence,
                prior_cause_posterior=prior_cause,
                updated_cause_posterior=dict(state.cause_posterior),
                prior_location_posterior=prior_location,
                updated_location_posterior=dict(state.location_posterior),
                prior_fix_intent_posterior=prior_fix,
                updated_fix_intent_posterior=dict(state.fix_intent_posterior),
                cumulative_cost=state.cumulative_cost,
                action_scores=scores,
            )
        )
    return P1BRunResult(
        variant_id=variant.variant_id,
        is_buggy=variant.is_buggy,
        policy=policy_id,
        bug_detected=state.bug_detected,
        reproduction_input=reproduction_input,
        bug_presence_posterior=state.bug_presence,
        cause_posterior=state.cause_posterior,
        location_posterior=state.location_posterior,
        fix_intent_posterior=state.fix_intent_posterior,
        executed_actions=state.executed_actions,
        cumulative_cost=state.cumulative_cost,
        current_step=state.current_step,
        stop_reason=stop_reason,
        trace=trace,
        first_failure_cost=first_failure_cost,
        cost_to_true_cause_top1=None,
    )


def _rank(distribution: Mapping[str, float], identity: str | None) -> int | None:
    if identity is None:
        return None
    ordered = [key for key, _ in rank_distribution(dict(distribution))]
    return ordered.index(identity) + 1 if identity in ordered else None


def _trajectory_row(definition: Mapping[str, Any], result: P1BRunResult) -> dict[str, Any]:
    is_buggy = bool(definition["is_buggy"])
    location_rank = _rank(result.location_posterior, str(definition["target_function"])) if is_buggy else None
    cause_top1 = rank_distribution(result.cause_posterior)[0][0]
    fix_top1 = rank_distribution(result.fix_intent_posterior)[0][0]
    observations = [step.observation for step in result.trace]
    false_positive = (
        not is_buggy
        and (
            result.stop_reason == "bug_confidence_threshold"
            or result.bug_presence_posterior >= FIXED_SETTINGS["bug_presence_threshold"]
        )
    )
    return {
        "input_id": definition["input_id"],
        "policy_id": result.policy,
        "is_buggy": is_buggy,
        "cause_family": definition["cause_family"],
        "clean_family": definition["clean_family"],
        "target_function": definition["target_function"] if is_buggy else None,
        "fix_intent": definition["fix_intent"] if is_buggy else None,
        "bug_discovery": result.bug_detected if is_buggy else None,
        "first_failure_observed": result.first_failure_cost is not None if is_buggy else None,
        "first_failure_cost": result.first_failure_cost if is_buggy else None,
        "cost_to_first_failure_with_penalty": (
            result.first_failure_cost
            if is_buggy and result.first_failure_cost is not None
            else FIXED_SETTINGS["failure_cost"] if is_buggy else None
        ),
        "clean_false_positive": false_positive if not is_buggy else None,
        "location_rank": location_rank,
        "location_top1": location_rank == 1 if is_buggy else None,
        "location_top3": location_rank is not None and location_rank <= 3 if is_buggy else None,
        "location_reciprocal_rank": round(1.0 / location_rank, 6) if location_rank else None,
        "cause_top1": cause_top1 == definition["cause_family"] if is_buggy else None,
        "fix_intent_top1": fix_top1 == definition["fix_intent"] if is_buggy else None,
        "execution_failure_observed": any(item.failure_found for item in observations),
        "bug_detected_observation": any(item.bug_detected for item in observations),
        "no_bug_evidence_observed": any(item.no_bug_evidence for item in observations),
        "executed_actions": list(result.executed_actions),
        "action_count": result.current_step,
        "cumulative_cost": result.cumulative_cost,
        "terminal_reason": result.stop_reason,
        "final_bug_presence_posterior": round(result.bug_presence_posterior, 6),
        "final_cause_posterior": {
            key: round(value, 6) for key, value in result.cause_posterior.items()
        },
        "final_location_posterior": {
            key: round(value, 6) for key, value in result.location_posterior.items()
        },
        "final_fix_intent_posterior": {
            key: round(value, 6) for key, value in result.fix_intent_posterior.items()
        },
        "trace": [step.to_dict() for step in result.trace],
    }


def _mean(values: list[float | int]) -> float | None:
    return round(sum(values) / len(values), 6) if values else None


def _rate(rows: list[dict[str, Any]], field: str) -> dict[str, Any]:
    defined = [row[field] for row in rows if row[field] is not None]
    successes = sum(bool(value) for value in defined)
    return {
        "successes": successes,
        "denominator": len(defined),
        "rate": round(successes / len(defined), 6) if defined else None,
    }


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    buggy = [row for row in rows if row["is_buggy"]]
    clean = [row for row in rows if not row["is_buggy"]]
    terminal_counts = {reason: 0 for reason in EXPECTED_STOP_PRECEDENCE}
    for row in rows:
        terminal_counts[row["terminal_reason"]] += 1
    return {
        "row_count": len(rows),
        "buggy_denominator": len(buggy),
        "clean_denominator": len(clean),
        "bug_discovery": _rate(buggy, "bug_discovery"),
        "first_failure_observed": _rate(buggy, "first_failure_observed"),
        "clean_false_positive": _rate(clean, "clean_false_positive"),
        "location_top1": _rate(buggy, "location_top1"),
        "location_top3": _rate(buggy, "location_top3"),
        "location_mrr": _mean(
            [row["location_reciprocal_rank"] for row in buggy if row["location_reciprocal_rank"] is not None]
        ),
        "location_mrr_denominator": sum(
            row["location_reciprocal_rank"] is not None for row in buggy
        ),
        "cause_top1": _rate(buggy, "cause_top1"),
        "fix_intent_top1": _rate(buggy, "fix_intent_top1"),
        "mean_cost_to_first_failure_with_penalty": _mean(
            [row["cost_to_first_failure_with_penalty"] for row in buggy]
        ),
        "mean_cumulative_cost": _mean([row["cumulative_cost"] for row in rows]),
        "mean_action_count": _mean([row["action_count"] for row in rows]),
        "terminal_reason_counts": terminal_counts,
    }


def _grouped(rows: list[dict[str, Any]], field: str) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        value = row[field]
        if value is not None:
            groups[str(value)].append(row)
    return {key: _aggregate(group) for key, group in groups.items()}


def _validate_rows(rows: list[dict[str, Any]]) -> None:
    expected_pairs = [
        (definition["input_id"], policy)
        for definition in INPUT_DEFINITIONS
        for policy in FORMAL_POLICY_IDS
    ]
    if [(row["input_id"], row["policy_id"]) for row in rows] != expected_pairs:
        raise P2HContractError("trajectory support/order is not exact input-major/policy-minor")
    if len(rows) != 90 or sum(row["is_buggy"] for row in rows) != 60:
        raise P2HContractError("trajectory support must be exactly 60 buggy + 30 clean rows")
    for row in rows:
        actions = row["executed_actions"]
        if len(actions) != len(set(actions)):
            raise P2HContractError("an action repeated within a trajectory")
        if row["cumulative_cost"] > FIXED_SETTINGS["budget_limit"]:
            raise P2HContractError("trajectory exceeded the frozen budget")
        if row["action_count"] > FIXED_SETTINGS["max_steps"]:
            raise P2HContractError("trajectory exceeded the frozen max steps")
        if row["terminal_reason"] not in EXPECTED_STOP_PRECEDENCE:
            raise P2HContractError("unknown terminal reason")
        if sum(step["observation"]["cost"] for step in row["trace"]) != row["cumulative_cost"]:
            raise P2HContractError("trace cost does not recompute")


def _validate_portable(value: Any, path: str = "summary") -> None:
    if value is None or isinstance(value, (bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise P2HContractError(f"non-finite number at {path}")
        return
    if isinstance(value, str):
        lowered = value.lower()
        if re.search(r"(?:^|\s)[a-zA-Z]:[\\/]", value) or value.startswith(("/tmp/", "/home/")):
            raise P2HContractError(f"absolute/private path at {path}")
        if any(token in lowered for token in ("\\users\\", "/users/", "__pycache__", ".venv/", ".venv\\")):
            raise P2HContractError(f"private/cache path at {path}")
        if re.search(r"(?:ghp_|github_pat_|sk-)[A-Za-z0-9_-]{12,}", value):
            raise P2HContractError(f"credential-like value at {path}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_portable(item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise P2HContractError(f"non-string object key at {path}")
        for key, item in value.items():
            _validate_portable(item, f"{path}.{key}")
        return
    raise P2HContractError(f"non-portable {type(value).__name__} at {path}")


def _rounded_distribution(distribution: Mapping[str, float]) -> dict[str, float]:
    return {key: round(value, 6) for key, value in distribution.items()}


def _validate_row_semantics(row: dict[str, Any], definition: Mapping[str, Any]) -> None:
    if tuple(row) != EXPECTED_ROW_FIELDS:
        raise P2HContractError("trajectory row schema/order drifted")
    is_buggy = bool(definition["is_buggy"])
    expected_truth = {
        "input_id": definition["input_id"],
        "is_buggy": is_buggy,
        "cause_family": definition["cause_family"],
        "clean_family": definition["clean_family"],
        "target_function": definition["target_function"] if is_buggy else None,
        "fix_intent": definition["fix_intent"] if is_buggy else None,
    }
    for field, expected in expected_truth.items():
        if row[field] != expected:
            raise P2HContractError(f"trajectory report-only truth drifted: {field}")
    if row["policy_id"] not in FORMAL_POLICY_IDS:
        raise P2HContractError("trajectory policy is outside the formal six")

    state = p1b_policies._State(
        bug_presence=0.5,
        cause_posterior=uniform_distribution(P1B_CAUSE_CATEGORIES),
        location_posterior=uniform_distribution(LOCATION_CANDIDATES),
        fix_intent_posterior=uniform_distribution(P1B_FIX_INTENT_CATEGORIES),
        executed_actions=[],
        cumulative_cost=0,
        current_step=0,
        bug_detected=False,
        execution_context=None,
    )
    rng = random.Random(p1b_policies._stable_seed(str(definition["input_id"]), 0))
    modules = _load_modules(
        _source_for(definition), f"p2h_validate_{str(definition['input_id']).lower()}_{row['policy_id']}"
    )
    first_failure_cost: int | None = None
    for index, step in enumerate(row["trace"], start=1):
        if type(step) is not dict or tuple(step) != EXPECTED_STEP_FIELDS:
            raise P2HContractError("trajectory step schema/order drifted")
        remaining = FIXED_SETTINGS["budget_limit"] - state.cumulative_cost
        scores = p1b_policies.score_actions(state, remaining)
        best = scores[0]["expected_utility_per_cost"] if scores else None
        if p1b_policies._check_stop(state, P1BSettings(**FIXED_SETTINGS), best) is not None:
            raise P2HContractError("trajectory continued after the accepted stop predicate")
        selected = p1b_policies.choose_action(row["policy_id"], state, remaining, rng)
        if selected != step["selected_action"] or step["action_scores"] != scores:
            raise P2HContractError("trajectory selection/score replay drifted")
        if step["step"] != index or step["policy"] != row["policy_id"]:
            raise P2HContractError("trajectory step identity/order drifted")
        if step["prior_bug_presence_posterior"] != state.bug_presence:
            raise P2HContractError("prior bug posterior drifted")
        if step["prior_cause_posterior"] != state.cause_posterior:
            raise P2HContractError("prior cause posterior drifted")
        if step["prior_location_posterior"] != state.location_posterior:
            raise P2HContractError("prior location posterior drifted")
        if step["prior_fix_intent_posterior"] != state.fix_intent_posterior:
            raise P2HContractError("prior fix-intent posterior drifted")
        expected_observation = _run_action(selected, definition, modules).to_dict()
        observation = step["observation"]
        if observation != expected_observation:
            raise P2HContractError("trajectory observation differs from fresh action execution")
        state.executed_actions.append(selected)
        state.cumulative_cost += observation["cost"]
        state.current_step += 1
        state.bug_detected = state.bug_detected or observation["bug_detected"]
        state.bug_presence = p1b_policies._update_bug_presence(
            state.bug_presence, observation["bug_detected"], observation["no_bug_evidence"]
        )
        state.cause_posterior = update_distribution(
            state.cause_posterior, observation["cause_scores"]
        )
        state.location_posterior = update_distribution(
            state.location_posterior, observation["location_scores"]
        )
        state.fix_intent_posterior = update_distribution(
            state.fix_intent_posterior, observation["fix_intent_scores"]
        )
        if observation["failure_found"] and first_failure_cost is None:
            first_failure_cost = state.cumulative_cost
        if step["updated_bug_presence_posterior"] != state.bug_presence:
            raise P2HContractError("updated bug posterior drifted")
        if step["updated_cause_posterior"] != state.cause_posterior:
            raise P2HContractError("updated cause posterior drifted")
        if step["updated_location_posterior"] != state.location_posterior:
            raise P2HContractError("updated location posterior drifted")
        if step["updated_fix_intent_posterior"] != state.fix_intent_posterior:
            raise P2HContractError("updated fix-intent posterior drifted")
        if step["cumulative_cost"] != state.cumulative_cost:
            raise P2HContractError("step cumulative cost drifted")

    remaining = FIXED_SETTINGS["budget_limit"] - state.cumulative_cost
    scores = p1b_policies.score_actions(state, remaining)
    best = scores[0]["expected_utility_per_cost"] if scores else None
    terminal = p1b_policies._check_stop(state, P1BSettings(**FIXED_SETTINGS), best)
    if terminal is None and p1b_policies.choose_action(
        row["policy_id"], state, remaining, rng
    ) is None:
        terminal = "no_available_actions"
    if terminal != row["terminal_reason"]:
        raise P2HContractError("terminal reason does not replay")

    observations = [step["observation"] for step in row["trace"]]
    location_rank = _rank(state.location_posterior, str(definition["target_function"])) if is_buggy else None
    cause_top1 = rank_distribution(state.cause_posterior)[0][0]
    fix_top1 = rank_distribution(state.fix_intent_posterior)[0][0]
    expected_projection = {
        "bug_discovery": state.bug_detected if is_buggy else None,
        "first_failure_observed": first_failure_cost is not None if is_buggy else None,
        "first_failure_cost": first_failure_cost if is_buggy else None,
        "cost_to_first_failure_with_penalty": (
            first_failure_cost
            if is_buggy and first_failure_cost is not None
            else FIXED_SETTINGS["failure_cost"] if is_buggy else None
        ),
        "clean_false_positive": (
            (
                terminal == "bug_confidence_threshold"
                or state.bug_presence >= FIXED_SETTINGS["bug_presence_threshold"]
            )
            if not is_buggy
            else None
        ),
        "location_rank": location_rank,
        "location_top1": location_rank == 1 if is_buggy else None,
        "location_top3": location_rank is not None and location_rank <= 3 if is_buggy else None,
        "location_reciprocal_rank": round(1.0 / location_rank, 6) if location_rank else None,
        "cause_top1": cause_top1 == definition["cause_family"] if is_buggy else None,
        "fix_intent_top1": fix_top1 == definition["fix_intent"] if is_buggy else None,
        "execution_failure_observed": any(item["failure_found"] for item in observations),
        "bug_detected_observation": any(item["bug_detected"] for item in observations),
        "no_bug_evidence_observed": any(item["no_bug_evidence"] for item in observations),
        "executed_actions": list(state.executed_actions),
        "action_count": state.current_step,
        "cumulative_cost": state.cumulative_cost,
        "final_bug_presence_posterior": round(state.bug_presence, 6),
        "final_cause_posterior": _rounded_distribution(state.cause_posterior),
        "final_location_posterior": _rounded_distribution(state.location_posterior),
        "final_fix_intent_posterior": _rounded_distribution(state.fix_intent_posterior),
    }
    for field, expected in expected_projection.items():
        if row[field] != expected:
            raise P2HContractError(f"trajectory derived field does not recompute: {field}")


def _independent_rate(rows: list[dict[str, Any]], field: str) -> dict[str, Any]:
    values = [row[field] for row in rows if row[field] is not None]
    numerator = sum(value is True for value in values)
    return {
        "successes": numerator,
        "denominator": len(values),
        "rate": round(numerator / len(values), 6) if values else None,
    }


def _independent_mean(values: list[float | int]) -> float | None:
    return round(sum(values) / len(values), 6) if values else None


def _independent_aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    buggy = [row for row in rows if row["is_buggy"] is True]
    clean = [row for row in rows if row["is_buggy"] is False]
    terminals = Counter(row["terminal_reason"] for row in rows)
    return {
        "row_count": len(rows),
        "buggy_denominator": len(buggy),
        "clean_denominator": len(clean),
        "bug_discovery": _independent_rate(buggy, "bug_discovery"),
        "first_failure_observed": _independent_rate(buggy, "first_failure_observed"),
        "clean_false_positive": _independent_rate(clean, "clean_false_positive"),
        "location_top1": _independent_rate(buggy, "location_top1"),
        "location_top3": _independent_rate(buggy, "location_top3"),
        "location_mrr": _independent_mean(
            [row["location_reciprocal_rank"] for row in buggy if row["location_reciprocal_rank"] is not None]
        ),
        "location_mrr_denominator": sum(
            row["location_reciprocal_rank"] is not None for row in buggy
        ),
        "cause_top1": _independent_rate(buggy, "cause_top1"),
        "fix_intent_top1": _independent_rate(buggy, "fix_intent_top1"),
        "mean_cost_to_first_failure_with_penalty": _independent_mean(
            [row["cost_to_first_failure_with_penalty"] for row in buggy]
        ),
        "mean_cumulative_cost": _independent_mean([row["cumulative_cost"] for row in rows]),
        "mean_action_count": _independent_mean([row["action_count"] for row in rows]),
        "terminal_reason_counts": {
            reason: terminals.get(reason, 0) for reason in EXPECTED_STOP_PRECEDENCE
        },
    }


def _independent_groups(
    rows: list[dict[str, Any]], field: str, expected_order: tuple[str, ...]
) -> dict[str, Any]:
    return {
        key: _independent_aggregate([row for row in rows if row[field] == key])
        for key in expected_order
    }


def validate_summary(summary: Any) -> dict[str, Any]:
    """Independently replay trajectories, metrics, identities, and schema fail closed."""

    _validate_registry_contract()
    if type(summary) is not dict or tuple(summary) != EXPECTED_TOP_LEVEL_FIELDS:
        raise P2HContractError("summary schema/order drifted")
    expected_scalars = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "analysis_phase": ANALYSIS_PHASE,
        "audit_id": AUDIT_ID,
        "role": ROLE,
        "domain_id": DOMAIN_ID,
        "domain_schema_version": DOMAIN_SCHEMA_VERSION,
        "claim_boundary": EXPECTED_CLAIM_BOUNDARY,
        "support": {
            "input_order": list(INPUT_ORDER),
            "policy_order": list(FORMAL_POLICY_IDS),
            "buggy_inputs": 10,
            "clean_inputs": 5,
            "buggy_rows": 60,
            "clean_rows": 30,
            "total_rows": 90,
            "arms": ["normal_execution"],
        },
        "action_costs": EXPECTED_ACTION_COSTS,
        "settings": FIXED_SETTINGS,
        "false_positive_definition": (
            "clean row with terminal_reason=bug_confidence_threshold or final bug-presence "
            "posterior >= 0.75"
        ),
        "undefined_value": None,
        "tie_rule": "posterior rank uses descending probability then lexical identity",
    }
    for field, expected in expected_scalars.items():
        if summary[field] != expected:
            raise P2HContractError(f"summary contract drifted: {field}")
    expected_validation = validate_outcome_free_contract()
    if summary["outcome_free_validation"] != expected_validation:
        raise P2HContractError("summary outcome-free validation identity drifted")
    expected_freeze = validate_pre_outcome_freeze_identity()
    if summary["pre_outcome_freeze_identity"] != expected_freeze:
        raise P2HContractError("summary pre-outcome freeze identity drifted")
    rows = summary["rows"]
    if type(rows) is not list:
        raise P2HContractError("summary rows must be a list")
    _validate_rows(rows)
    for definition in INPUT_DEFINITIONS:
        subset = [row for row in rows if row["input_id"] == definition["input_id"]]
        if len(subset) != len(FORMAL_POLICY_IDS):
            raise P2HContractError("per-input support drifted")
        for row in subset:
            _validate_row_semantics(row, definition)
    expected_aggregates = {
        "overall": _independent_aggregate(rows),
        "by_policy": _independent_groups(rows, "policy_id", FORMAL_POLICY_IDS),
        "by_input": _independent_groups(rows, "input_id", INPUT_ORDER),
        "by_buggy_cause_family": _independent_groups(
            rows, "cause_family", tuple(EXPECTED_BUGGY_FAMILIES)
        ),
        "by_clean_family": _independent_groups(rows, "clean_family", EXPECTED_CLEAN_FAMILIES),
    }
    if summary["aggregates"] != expected_aggregates:
        raise P2HContractError("summary aggregates/denominators do not independently recompute")
    expected_identities = {
        "manifest_digest": expected_validation["manifest_digest"],
        "dependency_digest": expected_validation["dependency_identity"]["digest"],
        "freeze_identity_digest": canonical_digest(expected_freeze),
        "row_digest": canonical_digest(rows),
        "aggregate_digest": canonical_digest(expected_aggregates),
    }
    if summary["identities"] != expected_identities:
        raise P2HContractError("summary identity digest drifted")
    without_digest = {key: value for key, value in summary.items() if key != "summary_digest"}
    if summary["summary_digest"] != canonical_digest(without_digest):
        raise P2HContractError("summary digest drifted")
    _validate_portable(summary)
    return summary


def build_summary() -> dict[str, Any]:
    """Execute the exact 90 formal-policy trajectories and validate the summary."""

    validation = validate_outcome_free_contract()
    frozen = validate_pre_outcome_freeze_identity()
    implementation_before = current_implementation_identity()
    dependency_before = current_dependency_identity()
    rows: list[dict[str, Any]] = []
    for definition in INPUT_DEFINITIONS:
        modules = _load_modules(
            _source_for(definition), f"p2h_run_{str(definition['input_id']).lower()}"
        )
        for policy_id in FORMAL_POLICY_IDS:
            rows.append(_trajectory_row(definition, _run_policy(definition, policy_id, modules)))
    _validate_rows(rows)
    aggregate = {
        "overall": _aggregate(rows),
        "by_policy": _grouped(rows, "policy_id"),
        "by_input": _grouped(rows, "input_id"),
        "by_buggy_cause_family": _grouped(rows, "cause_family"),
        "by_clean_family": _grouped(rows, "clean_family"),
    }
    result_payload = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "analysis_phase": ANALYSIS_PHASE,
        "audit_id": AUDIT_ID,
        "role": ROLE,
        "domain_id": DOMAIN_ID,
        "domain_schema_version": DOMAIN_SCHEMA_VERSION,
        "claim_boundary": EXPECTED_CLAIM_BOUNDARY,
        "support": {
            "input_order": list(INPUT_ORDER),
            "policy_order": list(FORMAL_POLICY_IDS),
            "buggy_inputs": 10,
            "clean_inputs": 5,
            "buggy_rows": 60,
            "clean_rows": 30,
            "total_rows": 90,
            "arms": ["normal_execution"],
        },
        "action_costs": EXPECTED_ACTION_COSTS,
        "settings": FIXED_SETTINGS,
        "false_positive_definition": (
            "clean row with terminal_reason=bug_confidence_threshold or final bug-presence "
            "posterior >= 0.75"
        ),
        "undefined_value": None,
        "tie_rule": "posterior rank uses descending probability then lexical identity",
        "outcome_free_validation": validation,
        "pre_outcome_freeze_identity": frozen,
        "rows": rows,
        "aggregates": aggregate,
    }
    if current_dependency_identity() != dependency_before:
        raise P2HContractError("accepted dependency identity changed during outcome execution")
    if current_implementation_identity() != implementation_before:
        raise P2HContractError("P2h implementation identity changed during outcome execution")
    identities = {
        "manifest_digest": validation["manifest_digest"],
        "dependency_digest": validation["dependency_identity"]["digest"],
        "freeze_identity_digest": canonical_digest(frozen),
        "row_digest": canonical_digest(rows),
        "aggregate_digest": canonical_digest(aggregate),
    }
    summary = {**result_payload, "identities": identities}
    summary["summary_digest"] = canonical_digest(summary)
    return validate_summary(summary)


def main() -> None:
    from bug_cause_inference.p2h.reports import write_report_pair

    parser = argparse.ArgumentParser(description="Run the frozen P2h replication audit.")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    summary = build_summary()
    json_path, markdown_path = write_report_pair(summary, args.output_dir)
    print(json_path)
    print(markdown_path)
    print(summary["summary_digest"])


if __name__ == "__main__":
    main()
