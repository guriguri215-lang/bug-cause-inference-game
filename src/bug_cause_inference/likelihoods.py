"""Fixed hypotheses, actions, and observation likelihoods for P1a."""

from __future__ import annotations

from bug_cause_inference.models import ActionSpec

CAUSES: tuple[str, ...] = (
    "boundary_condition",
    "missing_null_handling",
    "configuration_environment",
    "race_order_dependence",
    "specification_mismatch",
)

EVIDENCE_LIKELIHOODS: dict[str, dict[str, float]] = {
    "empty_or_edge_input_failure": {
        "boundary_condition": 0.80,
        "missing_null_handling": 0.35,
        "configuration_environment": 0.10,
        "race_order_dependence": 0.10,
        "specification_mismatch": 0.45,
    },
    "boundary_probe_fails": {
        "boundary_condition": 0.85,
        "missing_null_handling": 0.25,
        "configuration_environment": 0.10,
        "race_order_dependence": 0.10,
        "specification_mismatch": 0.30,
    },
    "null_reference_error": {
        "boundary_condition": 0.10,
        "missing_null_handling": 0.85,
        "configuration_environment": 0.15,
        "race_order_dependence": 0.10,
        "specification_mismatch": 0.15,
    },
    "missing_key_or_uninitialized": {
        "boundary_condition": 0.20,
        "missing_null_handling": 0.80,
        "configuration_environment": 0.20,
        "race_order_dependence": 0.10,
        "specification_mismatch": 0.25,
    },
    "single_environment_failure": {
        "boundary_condition": 0.10,
        "missing_null_handling": 0.10,
        "configuration_environment": 0.85,
        "race_order_dependence": 0.35,
        "specification_mismatch": 0.10,
    },
    "config_or_dependency_mismatch": {
        "boundary_condition": 0.10,
        "missing_null_handling": 0.15,
        "configuration_environment": 0.90,
        "race_order_dependence": 0.20,
        "specification_mismatch": 0.10,
    },
    "intermittent_failure": {
        "boundary_condition": 0.10,
        "missing_null_handling": 0.10,
        "configuration_environment": 0.30,
        "race_order_dependence": 0.85,
        "specification_mismatch": 0.10,
    },
    "order_or_cache_sensitive": {
        "boundary_condition": 0.15,
        "missing_null_handling": 0.15,
        "configuration_environment": 0.20,
        "race_order_dependence": 0.85,
        "specification_mismatch": 0.15,
    },
    "acceptance_criteria_conflict": {
        "boundary_condition": 0.20,
        "missing_null_handling": 0.15,
        "configuration_environment": 0.10,
        "race_order_dependence": 0.10,
        "specification_mismatch": 0.85,
    },
    "recent_contract_or_validation_diff": {
        "boundary_condition": 0.55,
        "missing_null_handling": 0.30,
        "configuration_environment": 0.15,
        "race_order_dependence": 0.10,
        "specification_mismatch": 0.65,
    },
    "trace_points_to_config_loader": {
        "boundary_condition": 0.10,
        "missing_null_handling": 0.35,
        "configuration_environment": 0.75,
        "race_order_dependence": 0.15,
        "specification_mismatch": 0.20,
    },
    "instrumentation_shows_stale_state": {
        "boundary_condition": 0.10,
        "missing_null_handling": 0.20,
        "configuration_environment": 0.20,
        "race_order_dependence": 0.90,
        "specification_mismatch": 0.10,
    },
}

ACTION_SPECS: dict[str, ActionSpec] = {
    "inspect_error_log": ActionSpec(
        action_id="inspect_error_log",
        label="Inspect error log",
        cost=1,
        observation_type="error_log",
        target_hypotheses=("missing_null_handling", "configuration_environment"),
    ),
    "run_boundary_tests": ActionSpec(
        action_id="run_boundary_tests",
        label="Run boundary tests",
        cost=2,
        observation_type="boundary_result",
        target_hypotheses=("boundary_condition",),
    ),
    "compare_environment": ActionSpec(
        action_id="compare_environment",
        label="Compare environment",
        cost=2,
        observation_type="environment_diff",
        target_hypotheses=("configuration_environment",),
    ),
    "inspect_recent_diff": ActionSpec(
        action_id="inspect_recent_diff",
        label="Inspect recent diff",
        cost=2,
        observation_type="recent_diff",
        target_hypotheses=(
            "boundary_condition",
            "missing_null_handling",
            "configuration_environment",
            "specification_mismatch",
        ),
    ),
    "run_reproduction_matrix": ActionSpec(
        action_id="run_reproduction_matrix",
        label="Run reproduction matrix",
        cost=3,
        observation_type="reproduction_condition",
        target_hypotheses=("boundary_condition", "configuration_environment", "race_order_dependence"),
    ),
    "add_instrumentation": ActionSpec(
        action_id="add_instrumentation",
        label="Add instrumentation",
        cost=4,
        observation_type="internal_state",
        target_hypotheses=("missing_null_handling", "configuration_environment", "race_order_dependence"),
    ),
    "check_spec_acceptance": ActionSpec(
        action_id="check_spec_acceptance",
        label="Check spec acceptance",
        cost=3,
        observation_type="spec_clue",
        target_hypotheses=("specification_mismatch",),
    ),
    "run_concurrency_stress": ActionSpec(
        action_id="run_concurrency_stress",
        label="Run concurrency stress",
        cost=5,
        observation_type="timing_result",
        target_hypotheses=("race_order_dependence",),
    ),
}

ACTION_ORDER: tuple[str, ...] = tuple(ACTION_SPECS.keys())

FIXED_CHECKLIST_ORDER: tuple[str, ...] = (
    "inspect_error_log",
    "inspect_recent_diff",
    "run_boundary_tests",
    "compare_environment",
    "run_reproduction_matrix",
    "check_spec_acceptance",
    "add_instrumentation",
    "run_concurrency_stress",
)

POSTERIOR_GREEDY_ACTIONS: dict[str, tuple[str, ...]] = {
    "boundary_condition": ("run_boundary_tests", "inspect_recent_diff"),
    "missing_null_handling": ("inspect_error_log", "add_instrumentation"),
    "configuration_environment": ("compare_environment", "inspect_error_log"),
    "race_order_dependence": ("run_reproduction_matrix", "run_concurrency_stress"),
    "specification_mismatch": ("check_spec_acceptance", "inspect_recent_diff"),
}

ACTION_CANDIDATE_EVIDENCE: dict[str, tuple[str, ...]] = {
    "inspect_error_log": (
        "null_reference_error",
        "missing_key_or_uninitialized",
        "trace_points_to_config_loader",
        "config_or_dependency_mismatch",
    ),
    "run_boundary_tests": (
        "boundary_probe_fails",
        "empty_or_edge_input_failure",
        "acceptance_criteria_conflict",
    ),
    "compare_environment": (
        "single_environment_failure",
        "config_or_dependency_mismatch",
        "trace_points_to_config_loader",
    ),
    "inspect_recent_diff": (
        "recent_contract_or_validation_diff",
        "missing_key_or_uninitialized",
        "trace_points_to_config_loader",
        "acceptance_criteria_conflict",
    ),
    "run_reproduction_matrix": (
        "intermittent_failure",
        "empty_or_edge_input_failure",
        "single_environment_failure",
        "order_or_cache_sensitive",
    ),
    "add_instrumentation": (
        "instrumentation_shows_stale_state",
        "missing_key_or_uninitialized",
        "trace_points_to_config_loader",
        "order_or_cache_sensitive",
    ),
    "check_spec_acceptance": (
        "acceptance_criteria_conflict",
        "recent_contract_or_validation_diff",
        "empty_or_edge_input_failure",
    ),
    "run_concurrency_stress": (
        "intermittent_failure",
        "order_or_cache_sensitive",
        "instrumentation_shows_stale_state",
    ),
}


def validate_likelihood_table() -> None:
    """Raise ValueError if the fixed likelihood/action tables are incomplete."""

    expected = set(CAUSES)
    for evidence_id, row in EVIDENCE_LIKELIHOODS.items():
        if set(row) != expected:
            missing = expected - set(row)
            extra = set(row) - expected
            raise ValueError(f"Likelihood row {evidence_id!r} has missing={missing} extra={extra}.")
        for cause, value in row.items():
            if not 0.0 < value <= 1.0:
                raise ValueError(f"Likelihood {evidence_id!r}/{cause!r} must be in (0, 1], got {value}.")
    for action_id, candidates in ACTION_CANDIDATE_EVIDENCE.items():
        if action_id not in ACTION_SPECS:
            raise ValueError(f"Candidate evidence references unknown action {action_id!r}.")
        for evidence_id in candidates:
            if evidence_id not in EVIDENCE_LIKELIHOODS:
                raise ValueError(f"Action {action_id!r} references unknown evidence {evidence_id!r}.")


def action_cost(action_id: str) -> int:
    return ACTION_SPECS[action_id].cost
