"""Reproducible synthetic bug cases for the first MVP."""

from __future__ import annotations

import json
import random
from pathlib import Path

from bug_cause_inference.likelihoods import ACTION_SPECS, CAUSES
from bug_cause_inference.models import ActionOutcome, Observation, SyntheticCase

DEFAULT_SEED = 20260627

DIFFICULTIES: tuple[str, ...] = (
    "easy",
    "easy",
    "medium",
    "medium",
    "medium",
    "medium",
    "medium",
    "medium",
    "hard",
    "hard",
)

PRIMARY_EVIDENCE: dict[str, tuple[str, ...]] = {
    "boundary_condition": ("empty_or_edge_input_failure", "boundary_probe_fails"),
    "missing_null_handling": ("null_reference_error", "missing_key_or_uninitialized"),
    "configuration_environment": ("single_environment_failure", "config_or_dependency_mismatch"),
    "race_order_dependence": ("intermittent_failure", "order_or_cache_sensitive"),
    "specification_mismatch": ("acceptance_criteria_conflict", "recent_contract_or_validation_diff"),
}

DISTRACTOR_EVIDENCE: dict[str, tuple[str, ...]] = {
    "boundary_condition": ("recent_contract_or_validation_diff", "acceptance_criteria_conflict"),
    "missing_null_handling": ("trace_points_to_config_loader", "recent_contract_or_validation_diff"),
    "configuration_environment": ("intermittent_failure", "null_reference_error"),
    "race_order_dependence": ("single_environment_failure", "instrumentation_shows_stale_state"),
    "specification_mismatch": ("empty_or_edge_input_failure", "boundary_probe_fails"),
}

ACTION_EVIDENCE_BY_CAUSE: dict[str, dict[str, str]] = {
    "boundary_condition": {
        "inspect_error_log": "missing_key_or_uninitialized",
        "run_boundary_tests": "boundary_probe_fails",
        "compare_environment": "single_environment_failure",
        "inspect_recent_diff": "recent_contract_or_validation_diff",
        "run_reproduction_matrix": "empty_or_edge_input_failure",
        "add_instrumentation": "missing_key_or_uninitialized",
        "check_spec_acceptance": "acceptance_criteria_conflict",
        "run_concurrency_stress": "order_or_cache_sensitive",
    },
    "missing_null_handling": {
        "inspect_error_log": "null_reference_error",
        "run_boundary_tests": "empty_or_edge_input_failure",
        "compare_environment": "trace_points_to_config_loader",
        "inspect_recent_diff": "missing_key_or_uninitialized",
        "run_reproduction_matrix": "empty_or_edge_input_failure",
        "add_instrumentation": "missing_key_or_uninitialized",
        "check_spec_acceptance": "recent_contract_or_validation_diff",
        "run_concurrency_stress": "order_or_cache_sensitive",
    },
    "configuration_environment": {
        "inspect_error_log": "trace_points_to_config_loader",
        "run_boundary_tests": "empty_or_edge_input_failure",
        "compare_environment": "config_or_dependency_mismatch",
        "inspect_recent_diff": "trace_points_to_config_loader",
        "run_reproduction_matrix": "single_environment_failure",
        "add_instrumentation": "trace_points_to_config_loader",
        "check_spec_acceptance": "recent_contract_or_validation_diff",
        "run_concurrency_stress": "intermittent_failure",
    },
    "race_order_dependence": {
        "inspect_error_log": "trace_points_to_config_loader",
        "run_boundary_tests": "empty_or_edge_input_failure",
        "compare_environment": "single_environment_failure",
        "inspect_recent_diff": "trace_points_to_config_loader",
        "run_reproduction_matrix": "intermittent_failure",
        "add_instrumentation": "instrumentation_shows_stale_state",
        "check_spec_acceptance": "recent_contract_or_validation_diff",
        "run_concurrency_stress": "order_or_cache_sensitive",
    },
    "specification_mismatch": {
        "inspect_error_log": "missing_key_or_uninitialized",
        "run_boundary_tests": "acceptance_criteria_conflict",
        "compare_environment": "single_environment_failure",
        "inspect_recent_diff": "recent_contract_or_validation_diff",
        "run_reproduction_matrix": "empty_or_edge_input_failure",
        "add_instrumentation": "missing_key_or_uninitialized",
        "check_spec_acceptance": "acceptance_criteria_conflict",
        "run_concurrency_stress": "intermittent_failure",
    },
}

EVIDENCE_TEXT: dict[str, str] = {
    "empty_or_edge_input_failure": "An edge input or empty input scenario fails while common inputs pass.",
    "boundary_probe_fails": "Targeted zero, one, max, or off-by-one probes reproduce the failure.",
    "null_reference_error": "The error log contains a null reference or None-like access failure.",
    "missing_key_or_uninitialized": "The failing path reads a missing key, unset field, or default that was never initialized.",
    "single_environment_failure": "The issue reproduces in one environment but not in a comparable baseline.",
    "config_or_dependency_mismatch": "A configuration flag, dependency version, or path differs between passing and failing runs.",
    "intermittent_failure": "The failure is intermittent and changes with repeated runs.",
    "order_or_cache_sensitive": "The failure depends on cache state, call order, or prior initialization.",
    "acceptance_criteria_conflict": "The observed behavior conflicts with an acceptance criterion or product rule.",
    "recent_contract_or_validation_diff": "A recent change touched validation, contracts, or input interpretation.",
    "trace_points_to_config_loader": "The stack trace or log points toward configuration loading or environment setup.",
    "instrumentation_shows_stale_state": "Instrumentation shows stale shared state or a value from a prior operation.",
}

EVIDENCE_TYPE: dict[str, str] = {
    "empty_or_edge_input_failure": "failing_test",
    "boundary_probe_fails": "boundary_result",
    "null_reference_error": "error_log",
    "missing_key_or_uninitialized": "error_log",
    "single_environment_failure": "environment_diff",
    "config_or_dependency_mismatch": "environment_diff",
    "intermittent_failure": "reproduction_condition",
    "order_or_cache_sensitive": "timing_result",
    "acceptance_criteria_conflict": "spec_clue",
    "recent_contract_or_validation_diff": "recent_diff",
    "trace_points_to_config_loader": "stack_trace",
    "instrumentation_shows_stale_state": "internal_state",
}


def _observation(evidence_id: str, case_id: str, context: str) -> Observation:
    return Observation(
        type=EVIDENCE_TYPE[evidence_id],
        evidence_id=evidence_id,
        value=f"{EVIDENCE_TEXT[evidence_id]} Context: {case_id} {context}.",
    )


def _initial_evidence(true_cause: str, difficulty: str, variation: int, rng: random.Random) -> tuple[str, str]:
    primary = PRIMARY_EVIDENCE[true_cause][variation % 2]
    if difficulty == "easy":
        secondary = PRIMARY_EVIDENCE[true_cause][(variation + 1) % 2]
    elif difficulty == "medium":
        secondary = DISTRACTOR_EVIDENCE[true_cause][variation % 2]
    elif true_cause == "specification_mismatch":
        secondary = DISTRACTOR_EVIDENCE[true_cause][variation % 2]
    else:
        other_cause = rng.choice([cause for cause in CAUSES if cause != true_cause])
        secondary = PRIMARY_EVIDENCE[other_cause][variation % 2]
    return primary, secondary


def generate_synthetic_cases(seed: int = DEFAULT_SEED) -> list[SyntheticCase]:
    """Generate 50 cases: five causes times ten cases, with a fixed seed."""

    rng = random.Random(seed)
    cases: list[SyntheticCase] = []
    case_number = 1
    for cause in CAUSES:
        for index, difficulty in enumerate(DIFFICULTIES):
            case_id = f"BUG-{case_number:04d}"
            template_side = "A" if index % 2 == 0 else "B"
            template_id = f"{cause}_{template_side}_{index % 5}"
            initial_ids = _initial_evidence(cause, difficulty, index, rng)
            initial_observations = tuple(
                _observation(evidence_id, case_id, f"initial observation {position}")
                for position, evidence_id in enumerate(initial_ids, start=1)
            )
            outcomes = []
            for action_id, spec in ACTION_SPECS.items():
                evidence_id = ACTION_EVIDENCE_BY_CAUSE[cause][action_id]
                outcomes.append(
                    ActionOutcome(
                        action=action_id,
                        cost=spec.cost,
                        observation_if_run=_observation(evidence_id, case_id, f"after {action_id}"),
                    )
                )
            cases.append(
                SyntheticCase(
                    case_id=case_id,
                    true_cause=cause,
                    difficulty=difficulty,
                    template_id=template_id,
                    seed=seed,
                    initial_observations=initial_observations,
                    available_investigations=tuple(outcomes),
                )
            )
            case_number += 1
    return cases


def save_cases(cases: list[SyntheticCase], path: str | Path) -> None:
    output = [case.to_dict() for case in cases]
    Path(path).write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")


def load_cases(path: str | Path) -> list[SyntheticCase]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [SyntheticCase.from_dict(item) for item in data]
