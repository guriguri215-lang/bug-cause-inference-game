"""Build the retrospective P1d3b dropout/delay profile-family report.

P1d3b is an analysis-only adapter over already-observed public P1c9 output.
It does not alter or reimplement P1c9 matching, transformation, release, or
stop semantics, and it does not invoke the P1d2 or P1d3a evaluators.
"""

from __future__ import annotations

import hashlib
import json
import math
from copy import deepcopy
from dataclasses import asdict
from fractions import Fraction
from functools import lru_cache
from typing import Any

from bug_cause_inference.p1b.actions import P1B_ACTION_SPECS, P1B_ACTIONS
from bug_cause_inference.p1b.models import P1BSettings
from bug_cause_inference.p1b.policies import P1B_POLICIES, STATE_SEQUENCE_GUARD_POLICY_ID
from bug_cause_inference.p1c.evaluation import P1C9_DROPOUT_DELAY_PROFILES, evaluate_p1c
from bug_cause_inference.p1d.evaluation import (
    P1D1_BUCKET_IDS,
    P1D1_FORMAL_STRATEGY_IDS,
    build_p1d1_summary,
    p1d1_summary_to_json,
    p1d1_summary_to_markdown,
)
from bug_cause_inference.p1d import p1d2_evaluation, p1d3a_evaluation


P1D3B_SCHEMA_VERSION = "p1d3b_g1_dropout_delay_profile_family_report.v1"
P1D3B_ANALYSIS_PHASE = "p1d3b_g1_dropout_delay_profile_family_report"
P1D3B_GAME_FAMILY_ID = "p1d3b_g1_dropout_delay_profile_conditioned_execution_grounded_v1"
P1D3B_FORMAL_STRATEGY_IDS = P1D1_FORMAL_STRATEGY_IDS
P1D3B_BUCKET_IDS = P1D1_BUCKET_IDS
P1D3B_PROFILE_IDS = tuple(p["profile_id"] for p in P1C9_DROPOUT_DELAY_PROFILES)
P1D3B_SECONDARY_METRIC_IDS = (
    "cost_to_first_failure",
    "location_top3_loss",
    "cause_top1_loss",
    "fix_intent_top1_loss",
    "wrong_cause_high_confidence_rate",
    "mean_investigation_cost",
)

_BENCHMARK_ID = "p1b_injected_bug_benchmark"
_REPORT_ROLE = "retrospective_dropout_delay_profile_conditioned_headline_primary"
_MODE = "execution_grounded"
_P1D1_JSON_HASH = "d1e86525240485b615f61b6261ea239a57b7a7148bdee4a5857452cc84169bac"
_P1D1_MARKDOWN_HASH = "9611e6cd8d3086a0b498a89278695f75c07ccdc9f840b6b3d00b14b0234f1dad"
_PROJECTION_ID = "p1d3b_p1c9_public_source_projection.v1"
_EXPECTED_SOURCE_PROJECTION_SHA256 = (
    "a35d09cf5108d1567e68ec27ba572274a711c29a5446eb4ba6f251907e8c2ec6"
)
_PROJECTION_FIELDS = (
    "analysis_phase", "stress_model", "perturbation_visibility",
    "primary_observation_mode", "source_observation_mode", "baseline_source",
    "report_role", "source_observation_retained", "visible_observation_is_copy",
    "release_timing_rule", "profiles", "baseline_aggregate_metrics_by_policy",
    "baseline_bucket_metrics_by_policy", "results_by_profile",
    "profile_vs_baseline_gap_by_policy", "recovery_diagnostics_by_policy",
    "clean_false_positive_stress_by_policy",
)
_STRESS_KEYS = (*_PROJECTION_FIELDS, "diagnostic_reports_by_observation_mode", "notes")
_PROFILE_RESULT_KEYS = (
    "profile", "aggregate_metrics_by_policy", "bucket_metrics_by_policy",
    "raw_variant_worst_cases_by_policy", "profile_vs_baseline_gap_by_policy",
    "recovery_diagnostics_by_policy", "clean_false_positive_stress_by_policy",
)
_AGGREGATE_KEYS = (
    "bug_discovery_rate_within_budget", "cost_to_first_failure",
    "location_top3_accuracy", "cause_top1_accuracy", "fix_intent_top1_accuracy",
    "wrong_cause_high_confidence_rate", "false_positive_rate_on_clean_cases",
    "mean_investigation_cost",
)
_BUCKET_METRIC_KEYS = (
    "variant_count", "buggy_variant_count", "clean_variant_count",
    "bucket_bug_discovery_rate", "bucket_cost_to_first_failure",
    "bucket_location_top3_accuracy", "bucket_cause_top1_accuracy",
    "bucket_fix_intent_top1_accuracy", "bucket_wrong_cause_high_confidence_rate",
    "bucket_false_positive_rate", "bucket_mean_investigation_cost",
)
_RAW_KEYS = (
    "missed_bug_variant_ids", "max_first_failure_cost_variant_ids",
    "location_top3_miss_variant_ids", "cause_top1_miss_variant_ids",
    "fix_intent_top1_miss_variant_ids", "wrong_cause_high_confidence_variant_ids",
    "false_positive_clean_variant_ids",
)
_RECOVERY_FIXED_KEYS = (
    "source_observation_count", "perturbed_observation_count", "perturbed_run_count",
    "perturbed_buggy_run_count", "recovered_after_missing_observation_count",
    "dropout_applied_count", "delayed_payload_count", "delayed_payload_released_count",
    "delayed_payload_stop_before_release_count", "recovery_rate_after_missing_observation",
    "delayed_evidence_released_rate", "stop_before_delayed_evidence_rate",
    "source_actions_with_perturbation",
)
_CLEAN_FIXED_KEYS = (
    "metric", "direction", "allowed_bucket_set", "allowed_bucket_ids",
    "selected_bucket_ids", "false_positive_rate_on_clean_cases",
    "clean_bucket_false_positive_rate", "clean_bucket_mean_investigation_cost",
    "clean_no_bug_stop_rate", "diagnostic_variant_ids",
)
_CLEAN_IDENTITY_KEYS = (
    "false_positive_rate_on_clean_cases", "clean_bucket_false_positive_rate",
    "clean_bucket_mean_investigation_cost", "clean_no_bug_stop_rate",
    "diagnostic_variant_ids",
)
_EXPECTED_SUPPORT = {
    "boundary_precision": ("P1B-BUG-001", "P1B-BUG-002", "P1B-BUG-003", "P1B-BUG-004"),
    "missing_optional_input": ("P1B-BUG-005", "P1B-BUG-006", "P1B-BUG-007", "P1B-BUG-008"),
    "config_normalization": ("P1B-BUG-009", "P1B-BUG-010", "P1B-BUG-011", "P1B-BUG-012"),
    "state_sequence": ("P1B-BUG-013", "P1B-BUG-014", "P1B-BUG-015", "P1B-BUG-016"),
    "spec_semantics": ("P1B-BUG-017", "P1B-BUG-018", "P1B-BUG-019", "P1B-BUG-020"),
}
_CLEAN_SUPPORT = (
    "P1B-CLEAN-021", "P1B-CLEAN-022", "P1B-CLEAN-023",
    "P1B-CLEAN-024", "P1B-CLEAN-025",
)
_EXPECTED_ACTION_SPECS = {
    "run_smoke_tests": (1, "test_failure", ("specification_mismatch", "missing_null_handling"), 0.45, 0.25),
    "run_boundary_tests": (2, "boundary_counterexample", ("boundary_condition",), 0.70, 0.45),
    "run_null_missing_tests": (2, "exception_trace", ("missing_null_handling",), 0.70, 0.55),
    "run_config_matrix_tests": (3, "config_counterexample", ("configuration_environment",), 0.70, 0.45),
    "run_state_sequence_tests": (4, "state_sequence_counterexample", ("state_order_dependence",), 0.75, 0.55),
    "run_property_search": (5, "property_counterexample", ("boundary_condition", "state_order_dependence", "specification_mismatch"), 0.65, 0.35),
    "inspect_traceback": (1, "exception_trace", ("missing_null_handling", "configuration_environment"), 0.30, 0.70),
    "inspect_coverage_spectrum": (3, "coverage_suspicious_location", (), 0.15, 0.85),
    "inspect_recent_diff": (2, "recent_diff_signal", ("configuration_environment", "state_order_dependence", "boundary_condition"), 0.20, 0.55),
    "inspect_spec_clause": (2, "spec_clause_mismatch", ("specification_mismatch", "boundary_condition", "configuration_environment"), 0.45, 0.50),
}
_EXPECTED_SETTINGS = asdict(P1BSettings())
_SECONDARY = {
    "cost_to_first_failure": ("bucket_cost_to_first_failure", "identity"),
    "location_top3_loss": ("bucket_location_top3_accuracy", "one_minus"),
    "cause_top1_loss": ("bucket_cause_top1_accuracy", "one_minus"),
    "fix_intent_top1_loss": ("bucket_fix_intent_top1_accuracy", "one_minus"),
    "wrong_cause_high_confidence_rate": ("bucket_wrong_cause_high_confidence_rate", "identity"),
    "mean_investigation_cost": ("bucket_mean_investigation_cost", "identity"),
}
_CHECK_IDS = (
    "p1d1_identity", "p1d2_immutable_context", "p1d3a_immutable_separate_context",
    "p1c9_source_contract", "p1c9_duplicate_exact_equality",
    "p1c9_canonical_public_projection", "exact_six_source", "dataset_and_support",
    "g0_comparability", "primary_cell_evidence", "secondary_aggregate_sources",
    "recovery_aggregate_sources", "clean_source_boundary", "cross_phase_invariance",
)
_TOP_KEYS = (
    "schema_version", "analysis_phase", "game_family_id", "benchmark_id",
    "report_role", "observation_mode", "retrospective_analysis", "public_boundary",
    "g0_reference_identity", "p1d2_immutable_context", "p1d3a_immutable_separate_context",
    "validation_status", "dataset_summary", "fixed_settings",
    "default_action_specifications", "formal_strategy_ids", "excluded_policy_ids",
    "diagnostic_only_policy_ids", "bucket_ids", "bucket_support", "clean_support",
    "dropout_delay_profile_ids", "dropout_delay_profiles", "information_structure",
    "loss_definition", "reference_distribution", "results_by_profile", "mixed_solution",
    "combined_interaction", "software_acceptance", "limitations", "non_claims", "notes",
)

_P1D2_IMMUTABLE_CONTEXT = {
    "candidate_policy_id": "state_sequence_guard",
    "candidate_discovery_loss_row": [0.75, 0.0, 0.75, 1.0, 0.5],
    "candidate_worst_bucket_discovery_loss": 1.0,
    "candidate_worst_bucket_ids": ["state_sequence"],
    "expanded_restricted_pure_security_loss": 1.0,
    "expanded_restricted_pure_security_policies": [
        *P1D3B_FORMAL_STRATEGY_IDS, "state_sequence_guard",
    ],
    "hypothesis_outcome": "not_supported",
    "software_acceptance": "accepted",
}
_P1D3A_COST_PROFILE_IDS = (
    "trace_access_expensive", "sequence_reproduction_expensive",
    "localization_evidence_expensive", "targeted_reproduction_expensive",
)
_P1D3A_IMMUTABLE_CONTEXT = {
    "commit": "a7cc8143780e4d3b6d99d04d2d87e09e40fdd62d",
    "schema_version": "p1d3a_g1_cost_profile_family_report.v1",
    "analysis_phase": "p1d3a_g1_cost_profile_family_report",
    "game_family_id": "p1d3a_g1_cost_profile_conditioned_execution_grounded_v1",
    "report_role": "retrospective_profile_conditioned_headline_primary",
    "reviewed_json_sha256": "e60b07a3ff95df2fb97006f86a3dd8081151565466e12638f9742748495dcb71",
    "reviewed_markdown_sha256": "1367f81d6ebb7322e74ae8bf65f20cecc2475f52c3864d0122807c678af2368a",
    "accepted_clean_projection_sha256": "9f81d7ec7eb30d9b5c2499614891a115b82b3906d86c4d815335bb65657a7774",
    "profile_count": 4,
    "primary_cell_count": 120,
    "restricted_pure_security_loss_by_profile": {
        profile: 1.0 for profile in _P1D3A_COST_PROFILE_IDS
    },
    "restricted_pure_security_policies_by_profile": {
        profile: list(P1D3B_FORMAL_STRATEGY_IDS)
        for profile in _P1D3A_COST_PROFILE_IDS
    },
    "separation_rule": "immutable_separate_not_invoked_or_copied",
}


def _expected_p1d2_immutable_context() -> dict[str, Any]:
    """Return an independent fixed sentinel for the accepted P1d2 projection."""

    return {
        "candidate_policy_id": "state_sequence_guard",
        "candidate_discovery_loss_row": [0.75, 0.0, 0.75, 1.0, 0.5],
        "candidate_worst_bucket_discovery_loss": 1.0,
        "candidate_worst_bucket_ids": ["state_sequence"],
        "expanded_restricted_pure_security_loss": 1.0,
        "expanded_restricted_pure_security_policies": [
            "fixed_checklist",
            "test_first",
            "coverage_first",
            "recent_diff_first",
            "cause_only_p1a_style",
            "expected_utility_per_cost",
            "state_sequence_guard",
        ],
        "hypothesis_outcome": "not_supported",
        "software_acceptance": "accepted",
    }


def _expected_p1d3a_immutable_context() -> dict[str, Any]:
    """Return an independent fixed sentinel for the accepted P1d3a projection."""

    profile_ids = (
        "trace_access_expensive",
        "sequence_reproduction_expensive",
        "localization_evidence_expensive",
        "targeted_reproduction_expensive",
    )
    policies = [
        "fixed_checklist",
        "test_first",
        "coverage_first",
        "recent_diff_first",
        "cause_only_p1a_style",
        "expected_utility_per_cost",
    ]
    return {
        "commit": "a7cc8143780e4d3b6d99d04d2d87e09e40fdd62d",
        "schema_version": "p1d3a_g1_cost_profile_family_report.v1",
        "analysis_phase": "p1d3a_g1_cost_profile_family_report",
        "game_family_id": "p1d3a_g1_cost_profile_conditioned_execution_grounded_v1",
        "report_role": "retrospective_profile_conditioned_headline_primary",
        "reviewed_json_sha256": (
            "e60b07a3ff95df2fb97006f86a3dd8081151565466e12638f9742748495dcb71"
        ),
        "reviewed_markdown_sha256": (
            "1367f81d6ebb7322e74ae8bf65f20cecc2475f52c3864d0122807c678af2368a"
        ),
        "accepted_clean_projection_sha256": (
            "9f81d7ec7eb30d9b5c2499614891a115b82b3906d86c4d815335bb65657a7774"
        ),
        "profile_count": 4,
        "primary_cell_count": 120,
        "restricted_pure_security_loss_by_profile": {
            profile_id: 1.0 for profile_id in profile_ids
        },
        "restricted_pure_security_policies_by_profile": {
            profile_id: list(policies) for profile_id in profile_ids
        },
        "separation_rule": "immutable_separate_not_invoked_or_copied",
    }


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _ordered_exact(left: Any, right: Any) -> bool:
    """Compare recursively, including container type, key order, and scalar type."""

    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return list(left) == list(right) and all(
            _ordered_exact(left[key], right[key]) for key in left
        )
    if isinstance(left, (list, tuple)):
        return len(left) == len(right) and all(
            _ordered_exact(a, b) for a, b in zip(left, right, strict=True)
        )
    return left == right


def _require_keys(value: Any, keys: tuple[str, ...], label: str) -> None:
    if not isinstance(value, dict) or tuple(value) != keys:
        raise ValueError(f"{label} fields are missing, extra, or reordered.")


def _ordered_subset(value: Any, support: tuple[str, ...]) -> bool:
    return (
        isinstance(value, list)
        and len(value) == len(set(value))
        and value == [item for item in support if item in set(value)]
    )


def _finite_number(value: Any) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(value)
    )


def _projection(stress: dict[str, Any]) -> dict[str, Any]:
    _require_keys(stress, _STRESS_KEYS, "P1c9 stress")
    return {key: deepcopy(stress[key]) for key in _PROJECTION_FIELDS}


def _projection_bytes(projection: dict[str, Any]) -> bytes:
    _require_keys(projection, _PROJECTION_FIELDS, "P1c9 public projection")
    return json.dumps(
        projection, ensure_ascii=False, separators=(",", ":"),
        sort_keys=False, allow_nan=False,
    ).encode("utf-8")


def build_p1d3b_source() -> dict[str, Any]:
    """Call P1c explicitly with the exact six formal execution-grounded policies."""

    return evaluate_p1c(
        policies=P1D3B_FORMAL_STRATEGY_IDS,
        observation_mode="execution_grounded",
    )


def _validate_runtime_contract() -> None:
    if P1D3B_FORMAL_STRATEGY_IDS != (
        "fixed_checklist", "test_first", "coverage_first", "recent_diff_first",
        "cause_only_p1a_style", "expected_utility_per_cost",
    ):
        raise ValueError("P1d3b formal policy order drifted.")
    if tuple(P1B_POLICIES) != ("random_action", *P1D3B_FORMAL_STRATEGY_IDS):
        raise ValueError("P1b policy registry drifted.")
    if STATE_SEQUENCE_GUARD_POLICY_ID != "state_sequence_guard":
        raise ValueError("P1d2 candidate identity drifted.")
    if not _ordered_exact(
        _P1D2_IMMUTABLE_CONTEXT, _expected_p1d2_immutable_context()
    ):
        raise ValueError("Accepted P1d2 immutable projection drifted.")
    if not _ordered_exact(
        _P1D3A_IMMUTABLE_CONTEXT, _expected_p1d3a_immutable_context()
    ):
        raise ValueError("Accepted P1d3a immutable projection drifted.")
    p1d2_identity = (
        p1d2_evaluation.P1D2_SCHEMA_VERSION,
        p1d2_evaluation.P1D2_ANALYSIS_PHASE,
        p1d2_evaluation.P1D2_GAME_ID,
        p1d2_evaluation.P1D2_BENCHMARK_ID,
        p1d2_evaluation.P1D2_CANDIDATE_STRATEGY_ID,
        p1d2_evaluation.P1D2_FORMAL_STRATEGY_IDS,
        p1d2_evaluation.P1D2_BUCKET_IDS,
    )
    if p1d2_identity != (
        "p1d2_preregistered_policy_evaluation.v1",
        "p1d2_preregistered_policy_evaluation",
        "p1d2_g0_default_execution_grounded_state_sequence_guard_v1",
        _BENCHMARK_ID,
        "state_sequence_guard",
        (
            "fixed_checklist", "test_first", "coverage_first", "recent_diff_first",
            "cause_only_p1a_style", "expected_utility_per_cost",
            "state_sequence_guard",
        ),
        (
            "boundary_precision", "missing_optional_input", "config_normalization",
            "state_sequence", "spec_semantics",
        ),
    ):
        raise ValueError("P1d2 immutable module contract drifted.")
    p1d3a_identity = (
        p1d3a_evaluation.P1D3A_SCHEMA_VERSION,
        p1d3a_evaluation.P1D3A_ANALYSIS_PHASE,
        p1d3a_evaluation.P1D3A_GAME_FAMILY_ID,
        p1d3a_evaluation.P1D3A_FORMAL_STRATEGY_IDS,
        p1d3a_evaluation.P1D3A_BUCKET_IDS,
        p1d3a_evaluation.P1D3A_COST_PROFILE_IDS,
    )
    if p1d3a_identity != (
        "p1d3a_g1_cost_profile_family_report.v1",
        "p1d3a_g1_cost_profile_family_report",
        "p1d3a_g1_cost_profile_conditioned_execution_grounded_v1",
        (
            "fixed_checklist", "test_first", "coverage_first", "recent_diff_first",
            "cause_only_p1a_style", "expected_utility_per_cost",
        ),
        (
            "boundary_precision", "missing_optional_input", "config_normalization",
            "state_sequence", "spec_semantics",
        ),
        (
            "trace_access_expensive", "sequence_reproduction_expensive",
            "localization_evidence_expensive", "targeted_reproduction_expensive",
        ),
    ):
        raise ValueError("P1d3a immutable module contract drifted.")
    if tuple(P1B_ACTIONS) != tuple(_EXPECTED_ACTION_SPECS):
        raise ValueError("P1b action order drifted.")
    observed = {
        key: (spec.cost, spec.observation_type, spec.strong_causes,
              spec.discovery_power, spec.location_power)
        for key, spec in P1B_ACTION_SPECS.items()
    }
    if not _ordered_exact(observed, _EXPECTED_ACTION_SPECS):
        raise ValueError("P1b default action specifications drifted.")
    if not _ordered_exact(asdict(P1BSettings()), _EXPECTED_SETTINGS):
        raise ValueError("P1b default settings drifted.")
    if P1D3B_PROFILE_IDS != (
        "traceback_signal_dropout", "recent_diff_signal_delay",
        "coverage_signal_dropout", "sequence_reproduction_delay",
    ):
        raise ValueError("P1c9 runtime profile order drifted.")
    runtime_keys = (
        "profile_id", "perturbation_type", "target_action_ids",
        "target_observation_families", "delay_steps", "bounded",
        "deterministic_rule", "expected_diagnostic_signal",
    )
    for profile in P1C9_DROPOUT_DELAY_PROFILES:
        _require_keys(profile, runtime_keys, f"P1c9 runtime profile {profile.get('profile_id')}")
        if (
            profile["perturbation_type"] not in ("dropout", "delay")
            or profile["bounded"] is not True
            or (profile["delay_steps"] is None) != (profile["perturbation_type"] == "dropout")
            or (profile["perturbation_type"] == "delay" and profile["delay_steps"] != 1)
        ):
            raise ValueError(f"P1c9 runtime profile semantics drifted for {profile['profile_id']}.")


def _validate_g0(source: dict[str, Any]) -> dict[str, Any]:
    g0 = build_p1d1_summary(source)
    if _sha256_bytes(p1d1_summary_to_json(g0).encode()) != _P1D1_JSON_HASH:
        raise ValueError("Accepted P1d1 JSON identity drifted.")
    if _sha256_bytes(p1d1_summary_to_markdown(g0).encode()) != _P1D1_MARKDOWN_HASH:
        raise ValueError("Accepted P1d1 Markdown identity drifted.")
    if (
        g0.get("schema_version"), g0.get("analysis_phase"), g0.get("game_id"),
        g0.get("report_role"),
    ) != (
        "p1d1_finite_game_report.v1", "p1d1_finite_game_report",
        "p1d0_g0_default_execution_grounded_v1", "headline_primary",
    ):
        raise ValueError("Accepted P1d1 identity drifted.")
    solution = g0["restricted_pure_solution"]
    if solution["restricted_pure_security_loss"] != 1.0 or tuple(
        solution["restricted_pure_security_policies"]
    ) != P1D3B_FORMAL_STRATEGY_IDS:
        raise ValueError("Accepted P1d1 solution drifted.")
    return g0


def _validate_profile(profile: dict[str, Any], runtime: dict[str, Any]) -> None:
    kind = runtime["perturbation_type"]
    keys = (
        "profile_id", "perturbation_type", "target_action_ids",
        "target_observation_families", "bounded", "deterministic",
        "deterministic_rule", "source_observation_retained",
        "visible_observation_is_copy", "expected_diagnostic_signal",
    ) + (("delay_steps",) if kind == "delay" else ())
    _require_keys(profile, keys, f"P1c9 profile {runtime['profile_id']}")
    expected = {
        "profile_id": runtime["profile_id"],
        "perturbation_type": kind,
        "target_action_ids": list(runtime["target_action_ids"]),
        "target_observation_families": list(runtime["target_observation_families"]),
        "bounded": runtime["bounded"],
        "deterministic": True,
        "deterministic_rule": runtime["deterministic_rule"],
        "source_observation_retained": True,
        "visible_observation_is_copy": True,
        "expected_diagnostic_signal": runtime["expected_diagnostic_signal"],
    }
    if kind == "delay":
        expected["delay_steps"] = runtime["delay_steps"]
    if not _ordered_exact(profile, expected):
        raise ValueError(f"P1c9 profile metadata drifted for {runtime['profile_id']}.")


def _validate_dataset(source: dict[str, Any]) -> None:
    dataset = source.get("dataset")
    _require_keys(dataset, ("total_variants", "buggy_variants", "clean_variants", "bucket_sizes"), "P1c dataset")
    if (dataset["total_variants"], dataset["buggy_variants"], dataset["clean_variants"]) != (25, 20, 5):
        raise ValueError("P1c dataset counts drifted.")
    buckets = dataset["bucket_sizes"]
    if tuple(buckets) != (*P1D3B_BUCKET_IDS, "clean_false_positive"):
        raise ValueError("P1c dataset bucket order drifted.")
    for bucket, support in _EXPECTED_SUPPORT.items():
        expected = {"variant_count": 4, "buggy_variants": 4, "clean_variants": 0, "variant_ids": list(support)}
        if not _ordered_exact(buckets[bucket], expected):
            raise ValueError(f"P1c support drifted for {bucket}.")
    expected_clean = {"variant_count": 5, "buggy_variants": 0, "clean_variants": 5, "variant_ids": list(_CLEAN_SUPPORT)}
    if not _ordered_exact(buckets["clean_false_positive"], expected_clean):
        raise ValueError("P1c clean support drifted.")


def _validate_recovery(row: dict[str, Any], profile_id: str, policy: str, kind: str) -> None:
    note_keys = tuple(row)[len(_RECOVERY_FIXED_KEYS):]
    if note_keys not in ((), ("note",), ("delayed_evidence_note",)):
        raise ValueError(f"P1c9 recovery fields drifted for {profile_id}/{policy}.")
    if tuple(row)[:len(_RECOVERY_FIXED_KEYS)] != _RECOVERY_FIXED_KEYS:
        raise ValueError(f"P1c9 recovery order drifted for {profile_id}/{policy}.")
    for key in _RECOVERY_FIXED_KEYS[:9]:
        if isinstance(row[key], bool) or not isinstance(row[key], int) or row[key] < 0:
            raise ValueError(f"P1c9 recovery count domain invalid for {profile_id}/{policy}.")
    if row["source_observation_count"] < row["perturbed_observation_count"]:
        raise ValueError(f"P1c9 recovery source count invalid for {profile_id}/{policy}.")
    denominators = (
        ("recovery_rate_after_missing_observation", "recovered_after_missing_observation_count", "perturbed_buggy_run_count"),
        ("delayed_evidence_released_rate", "delayed_payload_released_count", "delayed_payload_count"),
        ("stop_before_delayed_evidence_rate", "delayed_payload_stop_before_release_count", "delayed_payload_count"),
    )
    for rate, numerator, denominator in denominators:
        expected = None if row[denominator] == 0 else round(row[numerator] / row[denominator], 6)
        if type(row[rate]) is not type(expected) or row[rate] != expected:
            raise ValueError(f"P1c9 recovery arithmetic invalid for {profile_id}/{policy}/{rate}.")
    if kind == "delay" and row["delayed_payload_released_count"] + row["delayed_payload_stop_before_release_count"] != row["delayed_payload_count"]:
        raise ValueError(f"P1c9 delay partition invalid for {profile_id}/{policy}.")
    if kind == "dropout" and (
        row["dropout_applied_count"] != row["perturbed_observation_count"]
        or row["delayed_payload_count"] != 0
    ):
        raise ValueError(f"P1c9 dropout arithmetic invalid for {profile_id}/{policy}.")


def _validate_source(source: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], str]:
    if source.get("analysis_phase") != "p1c1_analysis_only_worst_case_report" or source.get("observation_mode") != _MODE:
        raise ValueError("P1d3b requires the execution-grounded P1c source.")
    if type(source.get("policies_evaluated")) is not list or tuple(source["policies_evaluated"]) != P1D3B_FORMAL_STRATEGY_IDS:
        raise ValueError("P1d3b source must be the explicit exact-six source in stable order.")
    if not _ordered_exact(source.get("settings"), _EXPECTED_SETTINGS):
        raise ValueError("P1c settings drifted.")
    _validate_dataset(source)
    stress = source.get("observation_dropout_delay_stress")
    _require_keys(stress, _STRESS_KEYS, "P1c9 stress")
    identity = tuple(stress[key] for key in _PROJECTION_FIELDS[:10])
    if identity != (
        "p1c9_bounded_observation_dropout_delay_stress_report",
        "bounded_observation_visibility_or_delay_profile", "policy_visible_p1c_only",
        "execution_grounded", "execution_grounded", "unperturbed_p1c_report",
        "headline_primary", True, True,
        "delay profiles release the named source payload after exactly one later investigation action, before the next stop check, if the run continues",
    ):
        raise ValueError("P1c9 identity or release contract drifted.")
    profiles = stress["profiles"]
    if not isinstance(profiles, list) or len(profiles) != 4:
        raise ValueError("P1c9 profiles are incomplete.")
    for public, runtime in zip(profiles, P1C9_DROPOUT_DELAY_PROFILES, strict=True):
        _validate_profile(public, runtime)
    if tuple(stress["results_by_profile"]) != P1D3B_PROFILE_IDS:
        raise ValueError("P1c9 result profile order drifted.")
    for duplicated in (
        "profile_vs_baseline_gap_by_policy", "recovery_diagnostics_by_policy",
        "clean_false_positive_stress_by_policy",
    ):
        if tuple(stress[duplicated]) != P1D3B_PROFILE_IDS:
            raise ValueError(f"P1c9 duplicate profile order drifted for {duplicated}.")
    if not _ordered_exact(stress["baseline_aggregate_metrics_by_policy"], source.get("aggregate_metrics")):
        raise ValueError("P1c9 baseline aggregate identity drifted.")
    if not _ordered_exact(stress["baseline_bucket_metrics_by_policy"], source.get("bucket_metrics")):
        raise ValueError("P1c9 baseline bucket identity drifted.")
    all_buggy = tuple(item for b in P1D3B_BUCKET_IDS for item in _EXPECTED_SUPPORT[b])
    for profile_id, public_profile in zip(P1D3B_PROFILE_IDS, profiles, strict=True):
        result = stress["results_by_profile"][profile_id]
        _require_keys(result, _PROFILE_RESULT_KEYS, f"P1c9 result {profile_id}")
        if not _ordered_exact(result["profile"], public_profile):
            raise ValueError(f"P1c9 nested profile drifted for {profile_id}.")
        for field in _PROFILE_RESULT_KEYS[1:]:
            if tuple(result[field]) != P1D3B_FORMAL_STRATEGY_IDS:
                raise ValueError(f"P1c9 policy order drifted for {profile_id}/{field}.")
        for duplicate in (
            "profile_vs_baseline_gap_by_policy", "recovery_diagnostics_by_policy",
            "clean_false_positive_stress_by_policy",
        ):
            if not _ordered_exact(stress[duplicate][profile_id], result[duplicate]):
                raise ValueError(f"P1c9 recursive duplicate equality failed for {profile_id}/{duplicate}.")
        for policy in P1D3B_FORMAL_STRATEGY_IDS:
            aggregate = result["aggregate_metrics_by_policy"][policy]
            _require_keys(aggregate, _AGGREGATE_KEYS, f"P1c9 aggregate {profile_id}/{policy}")
            buckets = result["bucket_metrics_by_policy"][policy]
            if tuple(buckets) != (*P1D3B_BUCKET_IDS, "clean_false_positive"):
                raise ValueError(f"P1c9 bucket order drifted for {profile_id}/{policy}.")
            raw = result["raw_variant_worst_cases_by_policy"][policy]
            _require_keys(raw, _RAW_KEYS, f"P1c9 raw evidence {profile_id}/{policy}")
            for field in _RAW_KEYS[:-1]:
                if not _ordered_subset(raw[field], all_buggy):
                    raise ValueError(f"P1c9 raw evidence invalid for {profile_id}/{policy}/{field}.")
            if not _ordered_subset(raw["false_positive_clean_variant_ids"], _CLEAN_SUPPORT):
                raise ValueError(f"P1c9 clean evidence invalid for {profile_id}/{policy}.")
            gap = result["profile_vs_baseline_gap_by_policy"][policy]
            _require_keys(gap, _AGGREGATE_KEYS, f"P1c9 gap {profile_id}/{policy}")
            for metric in _AGGREGATE_KEYS:
                _require_keys(
                    gap[metric], ("direction", "baseline_value", "profile_value", "gap"),
                    f"P1c9 gap leaf {profile_id}/{policy}/{metric}",
                )
            for bucket in P1D3B_BUCKET_IDS:
                metrics = buckets[bucket]
                _require_keys(metrics, _BUCKET_METRIC_KEYS, f"P1c9 bucket metrics {profile_id}/{policy}/{bucket}")
                if (metrics["variant_count"], metrics["buggy_variant_count"], metrics["clean_variant_count"]) != (4, 4, 0):
                    raise ValueError(f"P1c9 buggy support counts drifted for {profile_id}/{policy}/{bucket}.")
                missed = sum(item in set(raw["missed_bug_variant_ids"]) for item in _EXPECTED_SUPPORT[bucket])
                if metrics["bucket_bug_discovery_rate"] != float(Fraction(4 - missed, 4)):
                    raise ValueError(f"P1c9 discovery evidence disagrees for {profile_id}/{policy}/{bucket}.")
                for key in _BUCKET_METRIC_KEYS[3:]:
                    value = metrics[key]
                    if value is not None and not _finite_number(value):
                        raise ValueError(f"P1c9 non-finite metric for {profile_id}/{policy}/{bucket}/{key}.")
            clean = result["clean_false_positive_stress_by_policy"][policy]
            suffix = tuple(clean)[len(_CLEAN_FIXED_KEYS):]
            if tuple(clean)[:len(_CLEAN_FIXED_KEYS)] != _CLEAN_FIXED_KEYS or suffix not in ((), ("note",)):
                raise ValueError(f"P1c9 clean row order drifted for {profile_id}/{policy}.")
            if clean["diagnostic_variant_ids"] != raw["false_positive_clean_variant_ids"]:
                raise ValueError(f"P1c9 clean diagnostic evidence drifted for {profile_id}/{policy}.")
            _validate_recovery(
                result["recovery_diagnostics_by_policy"][policy], profile_id, policy,
                public_profile["perturbation_type"],
            )
    projection = _projection(stress)
    digest = _sha256_bytes(_projection_bytes(projection))
    if digest != _EXPECTED_SOURCE_PROJECTION_SHA256:
        raise ValueError("P1c9 canonical public projection identity drifted.")
    g0 = _validate_g0(source)
    return g0, projection, digest


def _action_specs() -> list[dict[str, Any]]:
    return [
        {
            "action_id": action_id, "cost": spec.cost,
            "observation_type": spec.observation_type,
            "strong_causes": list(spec.strong_causes),
            "discovery_power": spec.discovery_power, "location_power": spec.location_power,
        }
        for action_id, spec in P1B_ACTION_SPECS.items()
    ]


def _identity(path: str, field: str, value: Any, availability: str) -> dict[str, Any]:
    return {
        "source_path": path,
        "source_field": field,
        "source_value": deepcopy(value),
        "evidence_availability": availability,
    }


def _primary_matrix(profile_id: str, result: dict[str, Any]) -> dict[str, Any]:
    cells: dict[str, Any] = {}
    for policy in P1D3B_FORMAL_STRATEGY_IDS:
        missed_all = result["raw_variant_worst_cases_by_policy"][policy]["missed_bug_variant_ids"]
        missed_set = set(missed_all)
        cells[policy] = {}
        for bucket in P1D3B_BUCKET_IDS:
            support = list(_EXPECTED_SUPPORT[bucket])
            missed = [item for item in support if item in missed_set]
            discovered = [item for item in support if item not in missed_set]
            numerator = len(discovered)
            rate = Fraction(numerator, 4)
            path = (
                f"observation_dropout_delay_stress.results_by_profile[{profile_id}]"
                f".raw_variant_worst_cases_by_policy[{policy}]"
            )
            cells[policy][bucket] = {
                "profile_id": profile_id, "policy_id": policy, "bucket_id": bucket,
                "support_variant_ids": support, "discovered_variant_ids": discovered,
                "missed_variant_ids": missed, "discovered_numerator": numerator,
                "variant_denominator": 4, "discovery_rate": float(rate),
                "discovery_loss": float(1 - rate),
                "evidence_source": _identity(
                    path, "missed_bug_variant_ids", missed_all,
                    "public_complete_buggy_missed_variant_ids",
                ),
                "reconstruction_rule": "filter complete missed IDs to canonical support; discovered IDs are the stable support complement",
            }
    return {
        "metric_id": "discovery_loss", "direction": "lower_is_better",
        "row_policy_ids": list(P1D3B_FORMAL_STRATEGY_IDS),
        "column_bucket_ids": list(P1D3B_BUCKET_IDS), "cells_by_policy": cells,
    }


def _solution(matrix: dict[str, Any]) -> dict[str, Any]:
    rows: dict[str, Any] = {}
    worsts: dict[str, Fraction] = {}
    for policy in P1D3B_FORMAL_STRATEGY_IDS:
        losses = {
            bucket: Fraction(
                4 - matrix["cells_by_policy"][policy][bucket]["discovered_numerator"], 4
            )
            for bucket in P1D3B_BUCKET_IDS
        }
        worst = max(losses.values())
        average = sum(losses.values(), start=Fraction()) / 5
        worsts[policy] = worst
        rows[policy] = {
            "worst_bucket_loss": float(worst),
            "worst_bucket_ids": [b for b in P1D3B_BUCKET_IDS if losses[b] == worst],
            "reference_average_loss": float(average),
            "average_to_worst_gap": float(worst - average),
        }
    security = min(worsts.values())
    return {
        "by_policy": rows,
        "restricted_pure_security_loss": float(security),
        "restricted_pure_security_policies": [p for p in P1D3B_FORMAL_STRATEGY_IDS if worsts[p] == security],
        "tie_rule": "retain all exact rational ties in canonical policy and bucket order",
        "rounding_rule": "compute from exact integer counts and rational values before display rounding",
    }


def _g0_comparison(matrix: dict[str, Any], solution: dict[str, Any], g0: dict[str, Any]) -> dict[str, Any]:
    g0_cells = g0["g0_discovery_loss_matrix"]["cells_by_policy"]
    g0_rows = g0["restricted_pure_solution"]["by_policy"]
    cell: dict[str, Any] = {}
    average: dict[str, float] = {}
    worst: dict[str, float] = {}
    g0_buckets: dict[str, Any] = {}
    profile_buckets: dict[str, Any] = {}
    for policy in P1D3B_FORMAL_STRATEGY_IDS:
        cell[policy] = {
            b: matrix["cells_by_policy"][policy][b]["discovery_loss"] - g0_cells[policy][b]["discovery_loss"]
            for b in P1D3B_BUCKET_IDS
        }
        average[policy] = solution["by_policy"][policy]["reference_average_loss"] - g0_rows[policy]["reference_average_loss"]
        worst[policy] = solution["by_policy"][policy]["worst_bucket_loss"] - g0_rows[policy]["worst_bucket_loss"]
        g0_buckets[policy] = list(g0_rows[policy]["worst_bucket_ids"])
        profile_buckets[policy] = list(solution["by_policy"][policy]["worst_bucket_ids"])
    return {
        "comparison_role": "same_policy_descriptive_metric_specific; positive means higher profile discovery loss",
        "metric_id": "discovery_loss", "cell_deltas_by_policy": cell,
        "reference_average_deltas_by_policy": average,
        "worst_bucket_loss_deltas_by_policy": worst,
        "g0_worst_bucket_ids_by_policy": g0_buckets,
        "profile_worst_bucket_ids_by_policy": profile_buckets,
    }


def _secondary_matrices(profile_id: str, result: dict[str, Any]) -> list[dict[str, Any]]:
    matrices: list[dict[str, Any]] = []
    for metric_id, (source_field, transform) in _SECONDARY.items():
        sources: dict[str, Any] = {}
        values: dict[str, Any] = {}
        for policy in P1D3B_FORMAL_STRATEGY_IDS:
            sources[policy] = {}
            values[policy] = {}
            for bucket in P1D3B_BUCKET_IDS:
                value = result["bucket_metrics_by_policy"][policy][bucket][source_field]
                path = (
                    f"observation_dropout_delay_stress.results_by_profile[{profile_id}]"
                    f".bucket_metrics_by_policy[{policy}][{bucket}]"
                )
                sources[policy][bucket] = _identity(path, source_field, value, "not_exposed_by_p1c9")
                values[policy][bucket] = 1.0 - value if transform == "one_minus" else value
        matrices.append({
            "metric_id": metric_id, "direction": "lower_is_better",
            "source_p1c9_metric": source_field, "transform": transform,
            "used_in_restricted_pure_solution": False,
            "row_policy_ids": list(P1D3B_FORMAL_STRATEGY_IDS),
            "column_bucket_ids": list(P1D3B_BUCKET_IDS),
            "source_values_by_policy": sources, "values_by_policy": values,
            "evidence_boundary": {
                "public_aggregate_value": True,
                "variant_level_values": "not_exposed_by_p1c9",
                "reconstruction_permitted": False,
            },
        })
    return matrices


def _recovery(profile_id: str, result: dict[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for policy in P1D3B_FORMAL_STRATEGY_IDS:
        source = result["recovery_diagnostics_by_policy"][policy]
        row = deepcopy(source)
        path = (
            f"observation_dropout_delay_stress.results_by_profile[{profile_id}]"
            f".recovery_diagnostics_by_policy[{policy}]"
        )
        row["source_identity_by_field"] = {
            field: _identity(path, field, source[field], "not_exposed_by_p1c9")
            for field in _RECOVERY_FIXED_KEYS
        }
        output[policy] = row
    return output


def _clean(profile_id: str, result: dict[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for policy in P1D3B_FORMAL_STRATEGY_IDS:
        source = result["clean_false_positive_stress_by_policy"][policy]
        row = deepcopy(source)
        path = (
            f"observation_dropout_delay_stress.results_by_profile[{profile_id}]"
            f".clean_false_positive_stress_by_policy[{policy}]"
        )
        row["source_identity_by_field"] = {
            field: _identity(
                path, field, source[field],
                "public_diagnostic_variant_ids"
                if field in (
                    "false_positive_rate_on_clean_cases",
                    "clean_bucket_false_positive_rate", "diagnostic_variant_ids",
                ) else "not_exposed_by_p1c9",
            )
            for field in _CLEAN_IDENTITY_KEYS
        }
        output[policy] = row
    return output


def _p1d3a_context() -> dict[str, Any]:
    return deepcopy(_P1D3A_IMMUTABLE_CONTEXT)


def build_p1d3b_summary(
    p1c_summary: dict[str, Any] | None = None,
    *,
    _validate_against_current_source: bool = True,
) -> dict[str, Any]:
    """Build a fully validated report and fail before constructing partial results."""

    _validate_runtime_contract()
    source = p1c_summary if p1c_summary is not None else build_p1d3b_source()
    g0, source_projection, digest = _validate_source(source)
    stress = source["observation_dropout_delay_stress"]
    results_by_profile: dict[str, Any] = {}
    for profile_id in P1D3B_PROFILE_IDS:
        result = stress["results_by_profile"][profile_id]
        matrix = _primary_matrix(profile_id, result)
        solution = _solution(matrix)
        results_by_profile[profile_id] = {
            "profile_id": profile_id,
            "primary_discovery_loss_matrix": matrix,
            "restricted_pure_solution": solution,
            "g0_same_policy_comparison": _g0_comparison(matrix, solution, g0),
            "secondary_metric_matrices": _secondary_matrices(profile_id, result),
            "recovery_diagnostics_by_policy": _recovery(profile_id, result),
            "clean_false_positive_stress": _clean(profile_id, result),
            "profile_validation_status": {
                "status": "valid", "profile_id": profile_id,
                "primary_cell_count": 30, "secondary_matrix_count": 6,
                "recovery_policy_count": 6, "clean_policy_count": 6, "errors": [],
            },
        }
    settings = dict(source["settings"])
    settings["observation_mode"] = _MODE
    summary = {
        "schema_version": P1D3B_SCHEMA_VERSION,
        "analysis_phase": P1D3B_ANALYSIS_PHASE,
        "game_family_id": P1D3B_GAME_FAMILY_ID,
        "benchmark_id": _BENCHMARK_ID, "report_role": _REPORT_ROLE,
        "observation_mode": _MODE,
        "retrospective_analysis": {
            "mode": "retrospective_analysis_only",
            "source_phase": "p1c9_bounded_observation_dropout_delay_stress_report",
            "source_object_path": "observation_dropout_delay_stress",
            "source_public_projection_id": _PROJECTION_ID,
            "source_public_projection_field_ids": list(_PROJECTION_FIELDS),
            "source_public_projection_sha256": digest,
            "identity_verified_after_report_construction": True,
            "new_evaluation_performed": False,
        },
        "public_boundary": {
            "source_is_public_p1c9_output": True,
            "variant_level_primary_missed_ids_exposed": True,
            "variant_level_secondary_values_exposed": False,
            "variant_level_recovery_values_exposed": False,
            "variant_level_clean_false_positive_ids_exposed": True,
            "variant_level_clean_cost_and_stop_values_exposed": False,
            "missing_evidence_rule": "not_exposed_by_p1c9_do_not_reconstruct",
        },
        "g0_reference_identity": {
            "schema_version": "p1d1_finite_game_report.v1",
            "analysis_phase": "p1d1_finite_game_report",
            "game_id": "p1d0_g0_default_execution_grounded_v1",
            "json_sha256": _P1D1_JSON_HASH, "markdown_sha256": _P1D1_MARKDOWN_HASH,
            "formal_strategy_ids": list(P1D3B_FORMAL_STRATEGY_IDS),
            "bucket_ids": list(P1D3B_BUCKET_IDS),
            "restricted_pure_security_loss": 1.0,
            "restricted_pure_security_policies": list(P1D3B_FORMAL_STRATEGY_IDS),
        },
        "p1d2_immutable_context": deepcopy(_P1D2_IMMUTABLE_CONTEXT),
        "p1d3a_immutable_separate_context": _p1d3a_context(),
        "validation_status": {
            "status": "valid", "classification": "retrospective_source_validated",
            "validated_before_result_construction": True,
            "check_ids": list(_CHECK_IDS), "errors": [],
        },
        "dataset_summary": {
            "benchmark_id": _BENCHMARK_ID, "buggy_variant_count": 20,
            "clean_variant_count": 5, "buggy_bucket_count": 5,
            "variants_per_buggy_bucket": 4, "formal_policy_count": 6,
            "dropout_delay_profile_count": 4,
            "primary_matrix_shape_by_profile": [6, 5],
            "primary_cell_count_by_profile": 30, "primary_cell_count_total": 120,
        },
        "fixed_settings": settings,
        "default_action_specifications": _action_specs(),
        "formal_strategy_ids": list(P1D3B_FORMAL_STRATEGY_IDS),
        "excluded_policy_ids": ["state_sequence_guard"],
        "diagnostic_only_policy_ids": ["random_action"],
        "bucket_ids": list(P1D3B_BUCKET_IDS),
        "bucket_support": {b: list(v) for b, v in _EXPECTED_SUPPORT.items()},
        "clean_support": list(_CLEAN_SUPPORT),
        "dropout_delay_profile_ids": list(P1D3B_PROFILE_IDS),
        "dropout_delay_profiles": deepcopy(stress["profiles"]),
        "information_structure": {
            "profile_timing": "one profile is fixed externally before policy commitment",
            "investigator_commitment": "policy selected before bucket realization",
            "environment_action": "one of five buggy buckets within the fixed profile",
            "raw_variant_role": "uniform empirical support and audit evidence only",
            "policy_visible_information": ["P1c9 visible observations", "released delayed payloads"],
            "source_only_information": ["unreleased source observations", "report-only fields", "post-run aggregates"],
            "profile_is_adversary_action": False, "cross_profile_aggregation": "not_permitted",
        },
        "loss_definition": {
            "metric_id": "discovery_loss", "direction": "lower_is_better",
            "cell_support_size": 4,
            "cell_rate_formula": "discovered_numerator / 4",
            "cell_loss_formula": "1 - discovery_rate",
            "allowed_cell_values": [0, 0.25, 0.5, 0.75, 1],
            "primary_solution_metric": "discovery_loss",
            "secondary_metrics_used_in_solution": [],
        },
        "reference_distribution": {
            "distribution_id": "uniform_over_five_fixed_buggy_buckets",
            "role": "descriptive_reference_only", "bucket_ids": list(P1D3B_BUCKET_IDS),
            "weights_by_bucket": {b: 0.2 for b in P1D3B_BUCKET_IDS},
        },
        "results_by_profile": results_by_profile,
        "mixed_solution": {"computed": False, "status": "not_computed", "reason": "outside_p1d3b_scope"},
        "combined_interaction": {"computed": False, "status": "not_computed", "reason": "requires_separate_future_design_review"},
        "software_acceptance": {
            "status": "accepted", "basis": "contract_and_validation_conformance",
            "performance_independent": True, "validation_required": True,
            "scope": "p1d3b_report_software_only",
        },
        "limitations": [
            "The empirical family is limited to the fixed P1b scaffold, policies, buckets, variants, and profiles.",
            "Profile-specific changes or absence of changes are not causal proof or unseen-generalization evidence.",
            "Clean stress covers only five variants; P1b location metrics are function-level only.",
        ],
        "non_claims": [
            "P1d3b makes no production debugging, repair or patch correctness, real-world accuracy, or arbitrary-program generalization claim.",
            "P1d3b makes no statistical significance or general minimax, Nash, or regret optimality claim.",
            "P1d3b makes no joint, combined cost-plus-dropout, or cross-profile robustness claim.",
            "P1b real-diff artifacts are not real repository histories.",
        ],
        "notes": [
            "P1a is a Bayesian active bug-cause investigation prototype for synthetic observed-bug cases.",
            "P1b is a small injected checkout/pricing benchmark scaffold with 20 buggy variants and 5 clean variants.",
            "P1c, P1d1, P1d2, P1d3a, and P1d3b are analysis-only over the fixed scaffold.",
            "P1d3b is retrospective and reports already-observed P1c9 outcomes.",
        ],
    }
    if _sha256_bytes(_projection_bytes(_projection(stress))) != digest or not _ordered_exact(_projection(stress), source_projection):
        raise ValueError("P1c9 public projection changed during report construction.")
    if _validate_against_current_source:
        validate_p1d3b_summary(summary)
    else:
        _validate_p1d3b_summary_contract(summary)
    return summary


def _validate_p1d3b_summary_contract(summary: dict[str, Any]) -> None:
    """Reject partial, reordered, type-drifted, or out-of-contract reports."""

    _validate_runtime_contract()
    _require_keys(summary, _TOP_KEYS, "P1d3b report")
    if (
        summary.get("schema_version"), summary.get("analysis_phase"),
        summary.get("game_family_id"), summary.get("benchmark_id"),
        summary.get("report_role"), summary.get("observation_mode"),
    ) != (
        P1D3B_SCHEMA_VERSION, P1D3B_ANALYSIS_PHASE, P1D3B_GAME_FAMILY_ID,
        _BENCHMARK_ID, _REPORT_ROLE, _MODE,
    ):
        raise ValueError("P1d3b report identity drifted.")
    expected_object_keys = {
        "retrospective_analysis": (
            "mode", "source_phase", "source_object_path", "source_public_projection_id",
            "source_public_projection_field_ids", "source_public_projection_sha256",
            "identity_verified_after_report_construction", "new_evaluation_performed",
        ),
        "public_boundary": (
            "source_is_public_p1c9_output", "variant_level_primary_missed_ids_exposed",
            "variant_level_secondary_values_exposed", "variant_level_recovery_values_exposed",
            "variant_level_clean_false_positive_ids_exposed",
            "variant_level_clean_cost_and_stop_values_exposed", "missing_evidence_rule",
        ),
        "g0_reference_identity": (
            "schema_version", "analysis_phase", "game_id", "json_sha256",
            "markdown_sha256", "formal_strategy_ids", "bucket_ids",
            "restricted_pure_security_loss", "restricted_pure_security_policies",
        ),
        "p1d2_immutable_context": (
            "candidate_policy_id", "candidate_discovery_loss_row",
            "candidate_worst_bucket_discovery_loss", "candidate_worst_bucket_ids",
            "expanded_restricted_pure_security_loss",
            "expanded_restricted_pure_security_policies", "hypothesis_outcome",
            "software_acceptance",
        ),
        "p1d3a_immutable_separate_context": (
            "commit", "schema_version", "analysis_phase", "game_family_id", "report_role",
            "reviewed_json_sha256", "reviewed_markdown_sha256",
            "accepted_clean_projection_sha256", "profile_count", "primary_cell_count",
            "restricted_pure_security_loss_by_profile",
            "restricted_pure_security_policies_by_profile", "separation_rule",
        ),
        "validation_status": (
            "status", "classification", "validated_before_result_construction",
            "check_ids", "errors",
        ),
        "dataset_summary": (
            "benchmark_id", "buggy_variant_count", "clean_variant_count",
            "buggy_bucket_count", "variants_per_buggy_bucket", "formal_policy_count",
            "dropout_delay_profile_count", "primary_matrix_shape_by_profile",
            "primary_cell_count_by_profile", "primary_cell_count_total",
        ),
        "information_structure": (
            "profile_timing", "investigator_commitment", "environment_action",
            "raw_variant_role", "policy_visible_information", "source_only_information",
            "profile_is_adversary_action", "cross_profile_aggregation",
        ),
        "loss_definition": (
            "metric_id", "direction", "cell_support_size", "cell_rate_formula",
            "cell_loss_formula", "allowed_cell_values", "primary_solution_metric",
            "secondary_metrics_used_in_solution",
        ),
        "reference_distribution": (
            "distribution_id", "role", "bucket_ids", "weights_by_bucket",
        ),
    }
    for field, keys in expected_object_keys.items():
        _require_keys(summary[field], keys, f"P1d3b {field}")
    if summary["retrospective_analysis"]["source_public_projection_field_ids"] != list(_PROJECTION_FIELDS):
        raise ValueError("P1d3b projection field order drifted.")
    if summary["retrospective_analysis"]["source_public_projection_sha256"] != _EXPECTED_SOURCE_PROJECTION_SHA256:
        raise ValueError("P1d3b projection digest drifted.")
    if summary["validation_status"] != {
        "status": "valid", "classification": "retrospective_source_validated",
        "validated_before_result_construction": True,
        "check_ids": list(_CHECK_IDS), "errors": [],
    }:
        raise ValueError("P1d3b validation status drifted.")
    if tuple(summary["bucket_support"]) != P1D3B_BUCKET_IDS or summary["bucket_support"] != {
        bucket: list(support) for bucket, support in _EXPECTED_SUPPORT.items()
    }:
        raise ValueError("P1d3b bucket support drifted.")
    if summary["clean_support"] != list(_CLEAN_SUPPORT):
        raise ValueError("P1d3b clean support drifted.")
    if summary["default_action_specifications"] != _action_specs():
        raise ValueError("P1d3b action specifications drifted.")
    _require_keys(summary["fixed_settings"], (*tuple(_EXPECTED_SETTINGS), "observation_mode"), "P1d3b settings")
    if summary["fixed_settings"] != {**_EXPECTED_SETTINGS, "observation_mode": _MODE}:
        raise ValueError("P1d3b fixed settings drifted.")
    if tuple(summary.get("results_by_profile", {})) != P1D3B_PROFILE_IDS:
        raise ValueError("P1d3b result profile order drifted.")
    if tuple(summary.get("formal_strategy_ids", ())) != P1D3B_FORMAL_STRATEGY_IDS:
        raise ValueError("P1d3b formal strategies drifted.")
    if summary.get("dropout_delay_profile_ids") != list(P1D3B_PROFILE_IDS):
        raise ValueError("P1d3b profile IDs drifted.")
    if summary.get("mixed_solution") != {"computed": False, "status": "not_computed", "reason": "outside_p1d3b_scope"}:
        raise ValueError("P1d3b mixed solution boundary drifted.")
    if summary.get("combined_interaction") != {"computed": False, "status": "not_computed", "reason": "requires_separate_future_design_review"}:
        raise ValueError("P1d3b combined boundary drifted.")
    if summary.get("software_acceptance") != {
        "status": "accepted", "basis": "contract_and_validation_conformance",
        "performance_independent": True, "validation_required": True,
        "scope": "p1d3b_report_software_only",
    }:
        raise ValueError("P1d3b software acceptance drifted.")
    for profile_id in P1D3B_PROFILE_IDS:
        result = summary["results_by_profile"][profile_id]
        _require_keys(result, (
            "profile_id", "primary_discovery_loss_matrix", "restricted_pure_solution",
            "g0_same_policy_comparison", "secondary_metric_matrices",
            "recovery_diagnostics_by_policy", "clean_false_positive_stress",
            "profile_validation_status",
        ), f"P1d3b profile result {profile_id}")
        matrix = result["primary_discovery_loss_matrix"]
        _require_keys(matrix, ("metric_id", "direction", "row_policy_ids", "column_bucket_ids", "cells_by_policy"), f"P1d3b primary matrix {profile_id}")
        if tuple(matrix["cells_by_policy"]) != P1D3B_FORMAL_STRATEGY_IDS:
            raise ValueError(f"P1d3b primary policy order drifted for {profile_id}.")
        count = 0
        for policy in P1D3B_FORMAL_STRATEGY_IDS:
            if tuple(matrix["cells_by_policy"][policy]) != P1D3B_BUCKET_IDS:
                raise ValueError(f"P1d3b primary bucket order drifted for {profile_id}/{policy}.")
            for bucket in P1D3B_BUCKET_IDS:
                cell = matrix["cells_by_policy"][policy][bucket]
                _require_keys(cell, (
                    "profile_id", "policy_id", "bucket_id", "support_variant_ids",
                    "discovered_variant_ids", "missed_variant_ids", "discovered_numerator",
                    "variant_denominator", "discovery_rate", "discovery_loss",
                    "evidence_source", "reconstruction_rule",
                ), f"P1d3b primary cell {profile_id}/{policy}/{bucket}")
                support = list(_EXPECTED_SUPPORT[bucket])
                if cell["support_variant_ids"] != support or sorted(cell["discovered_variant_ids"] + cell["missed_variant_ids"], key=support.index) != support:
                    raise ValueError(f"P1d3b primary partition invalid for {profile_id}/{policy}/{bucket}.")
                if set(cell["discovered_variant_ids"]) & set(cell["missed_variant_ids"]):
                    raise ValueError(f"P1d3b primary partition overlaps for {profile_id}/{policy}/{bucket}.")
                expected_rate = float(Fraction(len(cell["discovered_variant_ids"]), 4))
                if cell["discovered_numerator"] != len(cell["discovered_variant_ids"]) or cell["variant_denominator"] != 4 or cell["discovery_rate"] != expected_rate or cell["discovery_loss"] != 1.0 - expected_rate:
                    raise ValueError(f"P1d3b primary arithmetic invalid for {profile_id}/{policy}/{bucket}.")
                _require_keys(cell["evidence_source"], ("source_path", "source_field", "source_value", "evidence_availability"), "P1d3b primary evidence")
                count += 1
        if count != 30:
            raise ValueError(f"P1d3b primary matrix incomplete for {profile_id}.")
        solution = result["restricted_pure_solution"]
        _require_keys(solution, (
            "by_policy", "restricted_pure_security_loss",
            "restricted_pure_security_policies", "tie_rule", "rounding_rule",
        ), f"P1d3b solution {profile_id}")
        if tuple(solution["by_policy"]) != P1D3B_FORMAL_STRATEGY_IDS:
            raise ValueError(f"P1d3b solution policy order invalid for {profile_id}.")
        for policy in P1D3B_FORMAL_STRATEGY_IDS:
            _require_keys(solution["by_policy"][policy], (
                "worst_bucket_loss", "worst_bucket_ids", "reference_average_loss",
                "average_to_worst_gap",
            ), f"P1d3b solution row {profile_id}/{policy}")
        comparison = result["g0_same_policy_comparison"]
        _require_keys(comparison, (
            "comparison_role", "metric_id", "cell_deltas_by_policy",
            "reference_average_deltas_by_policy", "worst_bucket_loss_deltas_by_policy",
            "g0_worst_bucket_ids_by_policy", "profile_worst_bucket_ids_by_policy",
        ), f"P1d3b G0 comparison {profile_id}")
        secondary = result["secondary_metric_matrices"]
        if (
            not isinstance(secondary, list)
            or not all(isinstance(item, dict) for item in secondary)
            or [item.get("metric_id") for item in secondary]
            != list(P1D3B_SECONDARY_METRIC_IDS)
        ):
            raise ValueError(f"P1d3b secondary metric order invalid for {profile_id}.")
        for item in secondary:
            _require_keys(item, (
                "metric_id", "direction", "source_p1c9_metric", "transform",
                "used_in_restricted_pure_solution", "row_policy_ids", "column_bucket_ids",
                "source_values_by_policy", "values_by_policy", "evidence_boundary",
            ), f"P1d3b secondary matrix {profile_id}/{item.get('metric_id')}")
            source_field = item["source_p1c9_metric"]
            expected_transform = _SECONDARY[item["metric_id"]][1]
            if item["transform"] != expected_transform or item["used_in_restricted_pure_solution"] is not False:
                raise ValueError(f"P1d3b secondary transform invalid for {profile_id}/{item['metric_id']}.")
            if tuple(item["source_values_by_policy"]) != P1D3B_FORMAL_STRATEGY_IDS or tuple(item["values_by_policy"]) != P1D3B_FORMAL_STRATEGY_IDS:
                raise ValueError(f"P1d3b secondary policy order invalid for {profile_id}/{item['metric_id']}.")
            for policy in P1D3B_FORMAL_STRATEGY_IDS:
                if tuple(item["source_values_by_policy"][policy]) != P1D3B_BUCKET_IDS or tuple(item["values_by_policy"][policy]) != P1D3B_BUCKET_IDS:
                    raise ValueError(f"P1d3b secondary bucket order invalid for {profile_id}/{item['metric_id']}/{policy}.")
                for bucket in P1D3B_BUCKET_IDS:
                    identity = item["source_values_by_policy"][policy][bucket]
                    _require_keys(identity, ("source_path", "source_field", "source_value", "evidence_availability"), "P1d3b secondary identity")
                    expected_path = (
                        f"observation_dropout_delay_stress.results_by_profile[{profile_id}]"
                        f".bucket_metrics_by_policy[{policy}][{bucket}]"
                    )
                    if identity["source_path"] != expected_path or identity["source_field"] != source_field or identity["evidence_availability"] != "not_exposed_by_p1c9":
                        raise ValueError(f"P1d3b secondary identity invalid for {profile_id}/{item['metric_id']}/{policy}/{bucket}.")
                    expected_value = 1.0 - identity["source_value"] if expected_transform == "one_minus" else identity["source_value"]
                    if item["values_by_policy"][policy][bucket] != expected_value:
                        raise ValueError(f"P1d3b secondary arithmetic invalid for {profile_id}/{item['metric_id']}/{policy}/{bucket}.")
        if tuple(result["recovery_diagnostics_by_policy"]) != P1D3B_FORMAL_STRATEGY_IDS or tuple(result["clean_false_positive_stress"]) != P1D3B_FORMAL_STRATEGY_IDS:
            raise ValueError(f"P1d3b diagnostic policy order invalid for {profile_id}.")
        for policy, row in result["recovery_diagnostics_by_policy"].items():
            suffix = tuple(row)[len(_RECOVERY_FIXED_KEYS):]
            if suffix not in (("source_identity_by_field",), ("note", "source_identity_by_field"), ("delayed_evidence_note", "source_identity_by_field")) or tuple(row)[:len(_RECOVERY_FIXED_KEYS)] != _RECOVERY_FIXED_KEYS:
                raise ValueError(f"P1d3b recovery row order invalid for {profile_id}/{policy}.")
            identities = row["source_identity_by_field"]
            if tuple(identities) != _RECOVERY_FIXED_KEYS:
                raise ValueError(f"P1d3b recovery identity order invalid for {profile_id}/{policy}.")
            expected_path = f"observation_dropout_delay_stress.results_by_profile[{profile_id}].recovery_diagnostics_by_policy[{policy}]"
            for field, identity in identities.items():
                if identity != _identity(expected_path, field, row[field], "not_exposed_by_p1c9"):
                    raise ValueError(f"P1d3b recovery identity invalid for {profile_id}/{policy}/{field}.")
        for policy, row in result["clean_false_positive_stress"].items():
            suffix = tuple(row)[len(_CLEAN_FIXED_KEYS):]
            if suffix not in (("source_identity_by_field",), ("note", "source_identity_by_field")) or tuple(row)[:len(_CLEAN_FIXED_KEYS)] != _CLEAN_FIXED_KEYS:
                raise ValueError(f"P1d3b clean row order invalid for {profile_id}/{policy}.")
            identities = row["source_identity_by_field"]
            if tuple(identities) != _CLEAN_IDENTITY_KEYS:
                raise ValueError(f"P1d3b clean identity order invalid for {profile_id}/{policy}.")
            expected_path = f"observation_dropout_delay_stress.results_by_profile[{profile_id}].clean_false_positive_stress_by_policy[{policy}]"
            for field, identity in identities.items():
                availability = "public_diagnostic_variant_ids" if field in (
                    "false_positive_rate_on_clean_cases", "clean_bucket_false_positive_rate",
                    "diagnostic_variant_ids",
                ) else "not_exposed_by_p1c9"
                if identity != _identity(expected_path, field, row[field], availability):
                    raise ValueError(f"P1d3b clean identity invalid for {profile_id}/{policy}/{field}.")
        _require_keys(result["profile_validation_status"], (
            "status", "profile_id", "primary_cell_count", "secondary_matrix_count",
            "recovery_policy_count", "clean_policy_count", "errors",
        ), f"P1d3b profile validation {profile_id}")


@lru_cache(maxsize=1)
def _current_canonical_summary() -> dict[str, Any]:
    """Build the immutable in-process canonical report once without recursion."""

    return build_p1d3b_summary(
        build_p1d3b_source(),
        _validate_against_current_source=False,
    )


def validate_p1d3b_summary(summary: dict[str, Any]) -> None:
    """Validate every report value against the current accepted source contract.

    The comparison is recursive, order-sensitive, container-sensitive, and scalar-
    type-sensitive.  Building the canonical comparison report invokes only P1c and
    P1d1; P1d2 and P1d3a are checked through side-effect-free module constants and
    their accepted immutable projections.
    """

    _validate_p1d3b_summary_contract(summary)
    canonical = _current_canonical_summary()
    if not _ordered_exact(summary, canonical):
        raise ValueError(
            "P1d3b report differs from the recursively exact current-source report."
        )


def p1d3b_summary_to_json(summary: dict[str, Any]) -> str:
    """Serialize one fully validated P1d3b summary as deterministic JSON."""

    validate_p1d3b_summary(summary)
    return json.dumps(summary, indent=2, ensure_ascii=False, allow_nan=False) + "\n"


def _fmt(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, float):
        return f"{value:.6f}".rstrip("0").rstrip(".")
    return str(value)


def p1d3b_summary_to_markdown(summary: dict[str, Any]) -> str:
    """Serialize the same validated P1d3b summary as an auditable Markdown report."""

    validate_p1d3b_summary(summary)
    r = summary["retrospective_analysis"]
    lines = [
        "# P1d3b G1 Dropout/Delay Profile Family Report", "",
        "## Scope And Identity", "",
        f"- Schema: `{summary['schema_version']}`",
        f"- Game family: `{summary['game_family_id']}`",
        "- Retrospective only; no new candidate or source evaluation was performed.",
        f"- P1c9 public projection: `{r['source_public_projection_id']}`",
        f"- P1c9 public projection SHA-256: `{r['source_public_projection_sha256']}`", "",
        "The profile is externally fixed and is not an adversary action. Each profile has a separate 6 by 5 matrix; cross-profile aggregation is not permitted.", "",
        "## Public Evidence Boundary", "",
        "Primary missed buggy IDs are public and complete. Secondary and recovery variant values, and clean cost/stop variant values, are not exposed by P1c9 and are not reconstructed.", "",
        "## Immutable Context", "",
        f"- P1d1 JSON SHA-256: `{summary['g0_reference_identity']['json_sha256']}`",
        f"- P1d2 candidate: `{summary['p1d2_immutable_context']['candidate_policy_id']}` (excluded; `{summary['p1d2_immutable_context']['hypothesis_outcome']}`)",
        f"- P1d3a commit: `{summary['p1d3a_immutable_separate_context']['commit']}` (separate and not invoked)", "",
        "## Dropout/Delay Profiles", "",
    ]
    for profile in summary["dropout_delay_profiles"]:
        lines.append(
            f"- `{profile['profile_id']}`: {profile['perturbation_type']}; targets "
            f"{', '.join(profile['target_action_ids'])}; {profile['deterministic_rule']}."
        )
    lines.extend(["", "Delay payloads release after exactly one later investigation action, before the next stop check, only if the run continues.", ""])
    for profile_id, result in summary["results_by_profile"].items():
        lines.extend([f"## Profile: `{profile_id}`", "", "### Primary Discovery-Loss Matrix", ""])
        lines.append("| Policy | " + " | ".join(P1D3B_BUCKET_IDS) + " |")
        lines.append("|---|" + "---:|" * 5)
        cells = result["primary_discovery_loss_matrix"]["cells_by_policy"]
        for policy in P1D3B_FORMAL_STRATEGY_IDS:
            lines.append("| `" + policy + "` | " + " | ".join(_fmt(cells[policy][b]["discovery_loss"]) for b in P1D3B_BUCKET_IDS) + " |")
        lines.extend(["", "### Cell Evidence", ""])
        for policy in P1D3B_FORMAL_STRATEGY_IDS:
            for bucket in P1D3B_BUCKET_IDS:
                c = cells[policy][bucket]
                lines.append(
                    f"- `{policy}` / `{bucket}`: support={c['support_variant_ids']}; "
                    f"discovered={c['discovered_variant_ids']}; missed={c['missed_variant_ids']}; "
                    f"loss={_fmt(c['discovery_loss'])}; source=`{c['evidence_source']['source_path']}.{c['evidence_source']['source_field']}`."
                )
        sol = result["restricted_pure_solution"]
        lines.extend(["", "### Profile-Conditioned Restricted-Pure Solution", "",
            f"Restricted-pure security loss among the six fixed deterministic policies: `{_fmt(sol['restricted_pure_security_loss'])}`.",
            "Tied policies: " + ", ".join(f"`{p}`" for p in sol["restricted_pure_security_policies"]) + ".", "",
            "### Same-Policy G0 Deltas", ""])
        comp = result["g0_same_policy_comparison"]
        for policy in P1D3B_FORMAL_STRATEGY_IDS:
            lines.append(
                f"- `{policy}`: average delta `{_fmt(comp['reference_average_deltas_by_policy'][policy])}`; "
                f"worst-bucket delta `{_fmt(comp['worst_bucket_loss_deltas_by_policy'][policy])}`."
            )
        lines.extend(["", "### Separate Secondary, Recovery, And Clean Results", "",
            "Secondary matrices are aggregate-only and do not enter the discovery-loss solution. Recovery and clean rows preserve P1c9 values and carry per-field source identity; unavailable variant evidence is marked `not_exposed_by_p1c9`.", ""])
    lines.extend([
        "## Validation And Explicitly Uncomputed Work", "",
        f"Validation: `{summary['validation_status']['status']}`; software acceptance: `{summary['software_acceptance']['status']}` (performance-independent).",
        f"Mixed solution: `{summary['mixed_solution']['status']}`. Combined interaction: `{summary['combined_interaction']['status']}`.", "",
        "## Limitations And Non-Claims", "",
        *[f"- {item}" for item in summary["limitations"]],
        *[f"- {item}" for item in summary["non_claims"]], "",
        "## Notes", "", *[f"- {item}" for item in summary["notes"]],
        "", "## Normalized Complete Audit Object", "",
        "The following JSON object is the complete validated report represented by this Markdown document.",
        "", "```json",
        json.dumps(summary, indent=2, ensure_ascii=False, allow_nan=False),
        "```",
    ])
    return "\n".join(lines).rstrip() + "\n"
