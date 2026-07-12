"""Build the retrospective P1d3a G1 cost-profile family report.

P1d3a is an analysis-only adapter over the existing execution-grounded P1c
cost-profile outcomes. It does not alter P1b or P1c runtime semantics.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import asdict
from fractions import Fraction
from typing import Any

from bug_cause_inference.p1b.actions import P1B_ACTION_SPECS, P1B_ACTIONS
from bug_cause_inference.p1b.models import P1BSettings
from bug_cause_inference.p1b.policies import P1B_POLICIES, STATE_SEQUENCE_GUARD_POLICY_ID
from bug_cause_inference.p1c.evaluation import P1C5_COST_PROFILES, evaluate_p1c
from bug_cause_inference.p1d.evaluation import (
    P1D1_BUCKET_IDS,
    P1D1_FORMAL_STRATEGY_IDS,
    build_p1d1_summary,
    p1d1_summary_to_json,
    p1d1_summary_to_markdown,
)


P1D3A_SCHEMA_VERSION = "p1d3a_g1_cost_profile_family_report.v1"
P1D3A_ANALYSIS_PHASE = "p1d3a_g1_cost_profile_family_report"
P1D3A_GAME_FAMILY_ID = "p1d3a_g1_cost_profile_conditioned_execution_grounded_v1"
P1D3A_FORMAL_STRATEGY_IDS = P1D1_FORMAL_STRATEGY_IDS
P1D3A_BUCKET_IDS = P1D1_BUCKET_IDS
P1D3A_COST_PROFILE_IDS = tuple(profile["profile_id"] for profile in P1C5_COST_PROFILES)
P1D3A_SECONDARY_METRIC_IDS = (
    "cost_to_first_failure",
    "location_top3_loss",
    "cause_top1_loss",
    "fix_intent_top1_loss",
    "wrong_cause_high_confidence_rate",
    "mean_investigation_cost",
)

_EXPECTED_P1D1_JSON_SHA256 = "d1e86525240485b615f61b6261ea239a57b7a7148bdee4a5857452cc84169bac"
_EXPECTED_P1D1_MARKDOWN_SHA256 = "9611e6cd8d3086a0b498a89278695f75c07ccdc9f840b6b3d00b14b0234f1dad"
_EXPECTED_BUCKET_SUPPORT = {
    "boundary_precision": ("P1B-BUG-001", "P1B-BUG-002", "P1B-BUG-003", "P1B-BUG-004"),
    "missing_optional_input": ("P1B-BUG-005", "P1B-BUG-006", "P1B-BUG-007", "P1B-BUG-008"),
    "config_normalization": ("P1B-BUG-009", "P1B-BUG-010", "P1B-BUG-011", "P1B-BUG-012"),
    "state_sequence": ("P1B-BUG-013", "P1B-BUG-014", "P1B-BUG-015", "P1B-BUG-016"),
    "spec_semantics": ("P1B-BUG-017", "P1B-BUG-018", "P1B-BUG-019", "P1B-BUG-020"),
}
_EXPECTED_CLEAN_SUPPORT = (
    "P1B-CLEAN-021", "P1B-CLEAN-022", "P1B-CLEAN-023", "P1B-CLEAN-024", "P1B-CLEAN-025"
)
_EXPECTED_DATASET_BUCKET_IDS = (*P1D3A_BUCKET_IDS, "clean_false_positive")
_EXPECTED_DATASET_BUCKET_FIELDS = (
    "variant_count", "buggy_variants", "clean_variants", "variant_ids",
)
_EXPECTED_OVERLAYS = {
    "trace_access_expensive": {"inspect_traceback": 4, "run_null_missing_tests": 5},
    "sequence_reproduction_expensive": {"run_state_sequence_tests": 8, "run_property_search": 7},
    "localization_evidence_expensive": {
        "inspect_coverage_spectrum": 6, "inspect_recent_diff": 5, "inspect_spec_clause": 4
    },
    "targeted_reproduction_expensive": {
        "run_boundary_tests": 4, "run_config_matrix_tests": 5,
        "run_state_sequence_tests": 7, "run_property_search": 8,
    },
}
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
_EXPECTED_BENCHMARK_ID = "p1b_injected_bug_benchmark"
_EXPECTED_REPORT_ROLE = "retrospective_profile_conditioned_headline_primary"
_EXPECTED_OBSERVATION_MODE = "execution_grounded"
_EXPECTED_RAW_EVIDENCE_KEYS = (
    "missed_bug_variant_ids",
    "max_first_failure_cost_variant_ids",
    "location_top3_miss_variant_ids",
    "cause_top1_miss_variant_ids",
    "fix_intent_top1_miss_variant_ids",
    "wrong_cause_high_confidence_variant_ids",
    "false_positive_clean_variant_ids",
)
_EXPECTED_BUCKET_METRIC_KEYS = (
    "variant_count",
    "buggy_variant_count",
    "clean_variant_count",
    "bucket_bug_discovery_rate",
    "bucket_cost_to_first_failure",
    "bucket_location_top3_accuracy",
    "bucket_cause_top1_accuracy",
    "bucket_fix_intent_top1_accuracy",
    "bucket_wrong_cause_high_confidence_rate",
    "bucket_false_positive_rate",
    "bucket_mean_investigation_cost",
)
_EXPECTED_AGGREGATE_METRIC_KEYS = (
    "bug_discovery_rate_within_budget",
    "cost_to_first_failure",
    "location_top3_accuracy",
    "cause_top1_accuracy",
    "fix_intent_top1_accuracy",
    "wrong_cause_high_confidence_rate",
    "false_positive_rate_on_clean_cases",
    "mean_investigation_cost",
)
_EXPECTED_CLEAN_ROW_KEYS = (
    "metric",
    "direction",
    "allowed_bucket_set",
    "allowed_bucket_ids",
    "selected_bucket_ids",
    "false_positive_rate_on_clean_cases",
    "clean_bucket_false_positive_rate",
    "clean_bucket_mean_investigation_cost",
    "clean_no_bug_stop_rate",
    "diagnostic_variant_ids",
)
_PRIMARY_EVIDENCE_SOURCE = (
    "P1c raw_variant_worst_cases_by_policy.missed_bug_variant_ids"
)
_PRIMARY_RECONSTRUCTION_RULE = (
    "stable bucket support minus missed IDs; discovered and missed are disjoint and exhaustive"
)
_CLEAN_SOURCE_IDENTITY_KEYS = (
    "clean_false_positive_rate", "clean_mean_investigation_cost",
    "clean_no_bug_stop_rate",
)
_CLEAN_SOURCE_FIELD_KEYS = (
    "report_field", "source_path", "source_field", "source_value",
    "evidence_availability",
)
_EXPECTED_CLEAN_PROJECTION_SHA256 = (
    "9f81d7ec7eb30d9b5c2499614891a115b82b3906d86c4d815335bb65657a7774"
)
_RAW_RATE_EVIDENCE = {
    "bucket_bug_discovery_rate": ("missed_bug_variant_ids", "miss"),
    "bucket_location_top3_accuracy": ("location_top3_miss_variant_ids", "miss"),
    "bucket_cause_top1_accuracy": ("cause_top1_miss_variant_ids", "miss"),
    "bucket_fix_intent_top1_accuracy": ("fix_intent_top1_miss_variant_ids", "miss"),
    "bucket_wrong_cause_high_confidence_rate": (
        "wrong_cause_high_confidence_variant_ids", "hit"
    ),
}
_EXPECTED_RETROSPECTIVE_ANALYSIS = {
    "retrospective": True,
    "source": "already-observed P1c bounded observation-cost outcomes",
    "new_hypothesis_or_candidate_evaluation": False,
}
_EXPECTED_G0_REFERENCE_IDENTITY = {
    "schema_version": "p1d1_finite_game_report.v1",
    "analysis_phase": "p1d1_finite_game_report",
    "game_id": "p1d0_g0_default_execution_grounded_v1",
    "json_sha256": _EXPECTED_P1D1_JSON_SHA256,
    "markdown_sha256": _EXPECTED_P1D1_MARKDOWN_SHA256,
    "restricted_pure_security_loss": 1.0,
    "restricted_pure_security_policies": list(P1D3A_FORMAL_STRATEGY_IDS),
}
_EXPECTED_P1D2_CONTEXT = {
    "candidate_policy_id": "state_sequence_guard",
    "candidate_discovery_loss_row": [0.75, 0.0, 0.75, 1.0, 0.5],
    "candidate_worst_bucket_discovery_loss": 1.0,
    "candidate_worst_bucket_ids": ["state_sequence"],
    "expanded_restricted_pure_security_loss": 1.0,
    "expanded_restricted_pure_security_policies": [
        *P1D3A_FORMAL_STRATEGY_IDS, "state_sequence_guard"
    ],
    "hypothesis_outcome": "not_supported",
    "software_acceptance": "accepted",
    "p1d3a_evaluation_membership": "excluded",
}
_EXPECTED_VALIDATION_STATUS = {
    "status": "valid",
    "preflight_completed_before_results": True,
    "p1d1_hash_sentinels_valid": True,
    "p1c_cost_family_contract_valid": True,
    "dataset_and_outcomes_complete": True,
    "primary_cell_count": 120,
}
_EXPECTED_INFORMATION_STRUCTURE = {
    "profile_role": "externally_fixed_not_an_adversary_action",
    "policy_commitment": "before_bucket_realization",
    "adversary_action": "one_of_five_buggy_buckets_within_the_fixed_profile",
    "raw_variant_role": "uniform_empirical_support_and_evidence_only",
    "family_shape": "four_separate_6_by_5_matrices_not_a_joint_profile_by_bucket_game",
}
_EXPECTED_LOSS_DEFINITION = {
    "metric_id": "discovery_loss",
    "direction": "lower_is_better",
    "formula": "1 - discovered_numerator / 4",
    "allowed_cell_values": [0.0, 0.25, 0.5, 0.75, 1.0],
    "sole_primary_and_solution_metric": True,
}
_EXPECTED_REFERENCE_DISTRIBUTION = {
    "distribution_id": "q0_uniform_over_five_buggy_buckets",
    "bucket_probabilities": {bucket: 0.2 for bucket in P1D3A_BUCKET_IDS},
    "used_for": "descriptive per-policy reference averages within each fixed profile",
}
_EXPECTED_LIMITATIONS = [
    "The empirical family is limited to the fixed P1b scaffold, exact policies, buckets, variants, and cost profiles.",
    "A profile-specific empirical weakness is not causal proof or unseen-generalization evidence.",
    "Clean stress covers only five current clean variants; P1b location metrics are function-level only.",
]
_EXPECTED_NON_CLAIMS = [
    "P1d3a does not claim production debugging, repair or patch correctness, real-world accuracy, or arbitrary-program generalization.",
    "P1d3a does not claim statistical significance, general minimax, Nash, or regret optimality.",
    "P1d3a does not claim robustness outside the fixed scaffold, joint profile-by-bucket robustness, combined cost-drop robustness, or cross-profile optimality.",
    "P1b real-diff artifacts are not real repository histories.",
]
_EXPECTED_NOTES = [
    "P1a is a Bayesian active bug-cause investigation prototype for synthetic observed-bug cases.",
    "P1b is a small injected checkout/pricing benchmark scaffold with 20 buggy variants and 5 clean variants.",
    "P1c, P1d1, P1d2, and P1d3a are analysis-only work over the fixed scaffold.",
    "P1d3a formalizes already-observed P1c cost-profile outcomes and does not rerun P1d2.",
    "Secondary and clean metrics remain separate from the discovery-loss solution.",
]
_EXPECTED_TOP_LEVEL_KEYS = (
    "schema_version", "analysis_phase", "game_family_id", "benchmark_id", "report_role",
    "observation_mode", "retrospective_analysis", "g0_reference_identity",
    "p1d2_immutable_context", "validation_status", "dataset_summary", "fixed_settings",
    "default_action_specifications", "formal_strategy_ids", "excluded_policy_ids",
    "diagnostic_only_policy_ids", "bucket_ids", "bucket_support", "cost_profile_ids",
    "cost_profiles", "information_structure", "loss_definition", "reference_distribution",
    "results_by_profile", "mixed_solution", "software_acceptance", "limitations",
    "non_claims", "notes",
)
_SECONDARY_SOURCES = {
    "cost_to_first_failure": ("bucket_cost_to_first_failure", "identity"),
    "location_top3_loss": ("bucket_location_top3_accuracy", "one_minus"),
    "cause_top1_loss": ("bucket_cause_top1_accuracy", "one_minus"),
    "fix_intent_top1_loss": ("bucket_fix_intent_top1_accuracy", "one_minus"),
    "wrong_cause_high_confidence_rate": ("bucket_wrong_cause_high_confidence_rate", "identity"),
    "mean_investigation_cost": ("bucket_mean_investigation_cost", "identity"),
}
_EXPECTED_G0_LOSS_ROWS = {
    policy: ([0.0, 0.75, 1.0, 1.0, 0.5] if index < 4 else [0.75, 0.0, 0.75, 1.0, 0.5])
    for index, policy in enumerate(P1D3A_FORMAL_STRATEGY_IDS)
}


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _expected_dataset_buckets() -> dict[str, dict[str, Any]]:
    buckets = {
        bucket: {
            "variant_count": 4,
            "buggy_variants": 4,
            "clean_variants": 0,
            "variant_ids": list(_EXPECTED_BUCKET_SUPPORT[bucket]),
        }
        for bucket in P1D3A_BUCKET_IDS
    }
    buckets["clean_false_positive"] = {
        "variant_count": 5,
        "buggy_variants": 0,
        "clean_variants": 5,
        "variant_ids": list(_EXPECTED_CLEAN_SUPPORT),
    }
    return buckets


def _clean_source_identity(
    profile_id: str,
    policy: str,
    *,
    clean_false_positive_rate: float,
    clean_mean_investigation_cost: int | float,
    clean_no_bug_stop_rate: float,
) -> dict[str, dict[str, Any]]:
    prefix = (
        f"P1c observation_cost_stress.results_by_profile.{profile_id}"
    )
    return {
        "clean_false_positive_rate": {
            "report_field": "clean_false_positive_rate",
            "source_path": (
                f"{prefix}.bucket_metrics_by_policy.{policy}.clean_false_positive."
                "bucket_false_positive_rate"
            ),
            "source_field": "bucket_false_positive_rate",
            "source_value": clean_false_positive_rate,
            "evidence_availability": "exact_from_false_positive_clean_variant_ids",
        },
        "clean_mean_investigation_cost": {
            "report_field": "clean_mean_investigation_cost",
            "source_path": (
                f"{prefix}.bucket_metrics_by_policy.{policy}.clean_false_positive."
                "bucket_mean_investigation_cost"
            ),
            "source_field": "bucket_mean_investigation_cost",
            "source_value": clean_mean_investigation_cost,
            "evidence_availability": "not_exposed_by_p1c",
        },
        "clean_no_bug_stop_rate": {
            "report_field": "clean_no_bug_stop_rate",
            "source_path": (
                f"{prefix}.clean_false_positive_stress_by_policy.{policy}."
                "clean_no_bug_stop_rate"
            ),
            "source_field": "clean_no_bug_stop_rate",
            "source_value": clean_no_bug_stop_rate,
            "evidence_availability": "not_exposed_by_p1c",
        },
    }


def _clean_projection_from_source(stress: dict[str, Any]) -> dict[str, Any]:
    projection: dict[str, Any] = {}
    results = stress["results_by_profile"]
    for profile_id in P1D3A_COST_PROFILE_IDS:
        projection[profile_id] = {}
        profile = results[profile_id]
        for policy in P1D3A_FORMAL_STRATEGY_IDS:
            raw = profile["raw_variant_worst_cases_by_policy"][policy]
            bucket = profile["bucket_metrics_by_policy"][policy]["clean_false_positive"]
            clean = profile["clean_false_positive_stress_by_policy"][policy]
            projection[profile_id][policy] = {
                "false_positive_ids": list(raw["false_positive_clean_variant_ids"]),
                "clean_false_positive_rate": bucket["bucket_false_positive_rate"],
                "clean_mean_investigation_cost": bucket["bucket_mean_investigation_cost"],
                "clean_no_bug_stop_rate": clean["clean_no_bug_stop_rate"],
            }
    return projection


def _clean_projection_from_summary(summary: dict[str, Any]) -> dict[str, Any]:
    projection: dict[str, Any] = {}
    results = summary["results_by_profile"]
    for profile_id in P1D3A_COST_PROFILE_IDS:
        projection[profile_id] = {}
        rows = results[profile_id]["clean_false_positive_stress"]["by_policy"]
        for policy in P1D3A_FORMAL_STRATEGY_IDS:
            row = rows[policy]
            projection[profile_id][policy] = {
                "false_positive_ids": list(row["false_positive_clean_variant_ids"]),
                "clean_false_positive_rate": row["clean_false_positive_rate"],
                "clean_mean_investigation_cost": row["clean_mean_investigation_cost"],
                "clean_no_bug_stop_rate": row["clean_no_bug_stop_rate"],
            }
    return projection


def _clean_projection_sha256(projection: dict[str, Any]) -> str:
    canonical = json.dumps(projection, ensure_ascii=False, separators=(",", ":"))
    return _sha256(canonical)


def _action_specifications() -> list[dict[str, Any]]:
    return [
        {
            "action_id": action_id,
            "default_cost": spec.cost,
            "observation_type": spec.observation_type,
            "strong_causes": list(spec.strong_causes),
            "discovery_power": spec.discovery_power,
            "location_power": spec.location_power,
        }
        for action_id, spec in P1B_ACTION_SPECS.items()
    ]


def _default_costs() -> dict[str, int]:
    return {action_id: values[0] for action_id, values in _EXPECTED_ACTION_SPECS.items()}


def _expected_effective_costs(profile_id: str) -> dict[str, int]:
    effective = _default_costs()
    effective.update(_EXPECTED_OVERLAYS[profile_id])
    return effective


def _ordered_subset(value: Any, support: tuple[str, ...] | list[str]) -> bool:
    return (
        isinstance(value, list)
        and len(value) == len(set(value))
        and value == [item for item in support if item in set(value)]
    )


def _is_fraction_step(
    value: Any,
    denominator: int,
    *,
    minimum: int | float,
    maximum: int | float,
) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    if not minimum <= value <= maximum:
        return False
    scaled = Fraction(str(value)) * denominator
    return scaled.denominator == 1


def _rounded_mean(values: list[int | float]) -> float:
    return round(sum(values) / len(values), 6)


def _expected_dataset_summary() -> dict[str, Any]:
    return {
        "total_variant_count": 25,
        "buggy_variant_count": 20,
        "clean_variant_count": 5,
        "buggy_variant_ids": [
            item for bucket in P1D3A_BUCKET_IDS for item in _EXPECTED_BUCKET_SUPPORT[bucket]
        ],
        "clean_variant_ids": list(_EXPECTED_CLEAN_SUPPORT),
        "buggy_bucket_count": 5,
        "uniform_variant_support_within_buggy_bucket": True,
    }


def _validate_profile_specification(profile: dict[str, Any], profile_id: str) -> None:
    if tuple(profile) != (
        "profile_id", "overlay", "effective_costs_by_action", "cost_range",
        "unchanged_actions_use_default", "budget_limit", "failure_cost", "stress_rationale",
    ):
        raise ValueError(f"P1c profile fields drifted for {profile_id}.")
    if profile.get("profile_id") != profile_id:
        raise ValueError(f"P1c profile identity drifted for {profile_id}.")
    overlay = profile.get("overlay", {})
    if tuple(overlay) != tuple(_EXPECTED_OVERLAYS[profile_id]):
        raise ValueError(f"P1c overlay order drifted for {profile_id}.")
    if overlay != _EXPECTED_OVERLAYS[profile_id]:
        raise ValueError(f"P1c overlay drifted for {profile_id}.")
    expected_effective = _expected_effective_costs(profile_id)
    effective = profile.get("effective_costs_by_action", {})
    if tuple(effective) != tuple(_EXPECTED_ACTION_SPECS):
        raise ValueError(f"P1c effective-cost order drifted for {profile_id}.")
    if effective != expected_effective:
        raise ValueError(f"P1c effective costs drifted for {profile_id}.")
    if profile.get("unchanged_actions_use_default") is not True:
        raise ValueError(f"P1c default-cost fallback drifted for {profile_id}.")
    if profile.get("budget_limit") != 12 or profile.get("failure_cost") != 14:
        raise ValueError(f"P1c settings drifted for {profile_id}.")
    if profile.get("cost_range") != {
        "min": min(expected_effective.values()),
        "max": max(expected_effective.values()),
    }:
        raise ValueError(f"P1c effective cost range drifted for {profile_id}.")
    expected_rationale = next(
        item["stress_rationale"]
        for item in P1C5_COST_PROFILES
        if item["profile_id"] == profile_id
    )
    if profile.get("stress_rationale") != expected_rationale:
        raise ValueError(f"P1c profile rationale drifted for {profile_id}.")
    if any(
        isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 8
        for value in expected_effective.values()
    ):
        raise ValueError(f"P1c effective cost domain is invalid for {profile_id}.")


def _expected_clean_source_row(
    *,
    false_positive_ids: list[str],
    clean_false_positive_rate: float,
    clean_mean_cost: int | float,
    clean_no_bug_stop_rate: float,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "metric": "false_positive_rate_on_clean_cases",
        "direction": "lower_is_better",
        "allowed_bucket_set": "clean_false_positive_only",
        "allowed_bucket_ids": ["clean_false_positive"],
        "selected_bucket_ids": ["clean_false_positive"],
        "false_positive_rate_on_clean_cases": clean_false_positive_rate,
        "clean_bucket_false_positive_rate": clean_false_positive_rate,
        "clean_bucket_mean_investigation_cost": clean_mean_cost,
        "clean_no_bug_stop_rate": clean_no_bug_stop_rate,
        "diagnostic_variant_ids": false_positive_ids,
    }
    if not false_positive_ids:
        row["note"] = "Clean false positives are not triggered in the current cost profile."
    return row


def _validate_runtime_contract() -> None:
    if P1D3A_FORMAL_STRATEGY_IDS != (
        "fixed_checklist", "test_first", "coverage_first", "recent_diff_first",
        "cause_only_p1a_style", "expected_utility_per_cost",
    ):
        raise ValueError("P1d3a formal policy order drifted.")
    if tuple(P1B_POLICIES) != ("random_action", *P1D3A_FORMAL_STRATEGY_IDS):
        raise ValueError("P1b policy registry drifted from the expected diagnostic-plus-six order.")
    if STATE_SEQUENCE_GUARD_POLICY_ID != "state_sequence_guard":
        raise ValueError("P1d2 candidate identity drifted.")
    if tuple(P1B_ACTIONS) != tuple(_EXPECTED_ACTION_SPECS):
        raise ValueError("P1b action order drifted.")
    observed_specs = {
        action_id: (
            spec.cost, spec.observation_type, spec.strong_causes,
            spec.discovery_power, spec.location_power,
        )
        for action_id, spec in P1B_ACTION_SPECS.items()
    }
    if observed_specs != _EXPECTED_ACTION_SPECS:
        raise ValueError("P1b action specifications drifted.")
    if asdict(P1BSettings()) != _EXPECTED_SETTINGS:
        raise ValueError("P1b default settings drifted.")
    if tuple(profile.get("profile_id") for profile in P1C5_COST_PROFILES) != tuple(
        _EXPECTED_OVERLAYS
    ):
        raise ValueError("P1c runtime cost profile IDs or order drifted.")
    for profile in P1C5_COST_PROFILES:
        profile_id = profile.get("profile_id")
        if tuple(profile) != ("profile_id", "overlay", "stress_rationale"):
            raise ValueError(f"P1c runtime profile fields drifted for {profile_id}.")
        overlay = profile.get("overlay", {})
        if tuple(overlay) != tuple(_EXPECTED_OVERLAYS[profile_id]):
            raise ValueError(f"P1c runtime overlay order drifted for {profile_id}.")
        if overlay != _EXPECTED_OVERLAYS[profile_id]:
            raise ValueError(f"P1c runtime overlay values drifted for {profile_id}.")


def build_p1d3a_source() -> dict[str, Any]:
    """Evaluate the existing P1c path with the exact six formal policies."""

    return evaluate_p1c(
        policies=P1D3A_FORMAL_STRATEGY_IDS,
        observation_mode="execution_grounded",
    )


def _validate_g0_reference(source: dict[str, Any]) -> dict[str, Any]:
    g0 = build_p1d1_summary(source)
    json_hash = _sha256(p1d1_summary_to_json(g0))
    markdown_hash = _sha256(p1d1_summary_to_markdown(g0))
    if json_hash != _EXPECTED_P1D1_JSON_SHA256 or markdown_hash != _EXPECTED_P1D1_MARKDOWN_SHA256:
        raise ValueError("Accepted P1d1 JSON or Markdown hash sentinel drifted.")
    if g0["schema_version"] != "p1d1_finite_game_report.v1" or g0["analysis_phase"] != "p1d1_finite_game_report":
        raise ValueError("Accepted P1d1 schema identity drifted.")
    if g0["game_id"] != "p1d0_g0_default_execution_grounded_v1" or g0["report_role"] != "headline_primary":
        raise ValueError("Accepted P1d1 game identity or report role drifted.")
    solution = g0["restricted_pure_solution"]
    if solution["restricted_pure_security_loss"] != 1.0 or tuple(solution["restricted_pure_security_policies"]) != P1D3A_FORMAL_STRATEGY_IDS:
        raise ValueError("Accepted P1d1 restricted-pure result drifted.")
    if tuple(g0["secondary_metric_matrices"]) != P1D3A_SECONDARY_METRIC_IDS:
        raise ValueError("Accepted P1d1 secondary metric order drifted.")
    return g0


def _validate_p1c_cost_source(source: dict[str, Any]) -> None:
    if source.get("analysis_phase") != "p1c1_analysis_only_worst_case_report" or source.get("observation_mode") != "execution_grounded":
        raise ValueError("P1d3a requires the execution-grounded P1c source.")
    if tuple(source.get("policies_evaluated", ())) != P1D3A_FORMAL_STRATEGY_IDS:
        raise ValueError("P1d3a source must contain exactly the six formal policies in stable order.")
    stress = source.get("observation_cost_stress", {})
    expected_identity = (
        "p1c5_bounded_observation_cost_stress_report", "bounded_action_cost_overlay",
        "policy_visible_overlay", "execution_grounded", "execution_grounded", "headline_primary",
    )
    observed_identity = tuple(stress.get(key) for key in (
        "analysis_phase", "stress_model", "cost_visibility", "primary_observation_mode",
        "source_observation_mode", "report_role",
    ))
    if observed_identity != expected_identity:
        raise ValueError("P1c cost-family identity drifted.")
    if stress.get("base_budget_limit") != 12 or stress.get("base_failure_cost") != 14:
        raise ValueError("P1c cost-family budget or failure cost drifted.")
    if stress.get("cost_constraints") != {
        "integer_costs": True,
        "min_effective_cost": 1,
        "max_effective_cost": 8,
        "default_budget_limit_unchanged": True,
        "default_failure_cost_unchanged": True,
    }:
        raise ValueError("P1c cost-family constraints drifted.")
    if source.get("settings") != _EXPECTED_SETTINGS:
        raise ValueError("P1c source settings drifted.")
    dataset = source.get("dataset", {})
    if tuple(dataset) != (
        "total_variants", "buggy_variants", "clean_variants", "bucket_sizes"
    ):
        raise ValueError("P1c dataset fields drifted.")
    if (
        dataset.get("total_variants"), dataset.get("buggy_variants"),
        dataset.get("clean_variants"),
    ) != (25, 20, 5):
        raise ValueError("P1c dataset counts drifted.")
    bucket_sizes = dataset.get("bucket_sizes", {})
    if tuple(bucket_sizes) != _EXPECTED_DATASET_BUCKET_IDS:
        raise ValueError("P1c dataset bucket order or membership drifted.")
    expected_dataset_buckets = _expected_dataset_buckets()
    for bucket_id in _EXPECTED_DATASET_BUCKET_IDS:
        bucket = bucket_sizes.get(bucket_id, {})
        if tuple(bucket) != _EXPECTED_DATASET_BUCKET_FIELDS:
            raise ValueError(f"P1c dataset bucket fields drifted for {bucket_id}.")
        if bucket != expected_dataset_buckets[bucket_id]:
            raise ValueError(f"P1c dataset bucket support drifted for {bucket_id}.")
    profiles = stress.get("profiles")
    if not isinstance(profiles, list) or [p.get("profile_id") for p in profiles] != list(P1D3A_COST_PROFILE_IDS):
        raise ValueError("P1c cost profiles are missing, extra, duplicated, or reordered.")
    for profile in profiles:
        profile_id = profile["profile_id"]
        _validate_profile_specification(profile, profile_id)

    baseline_aggregates = stress.get("baseline_aggregate_metrics_by_policy", {})
    baseline_buckets = stress.get("baseline_bucket_metrics_by_policy", {})
    if baseline_aggregates != source.get("aggregate_metrics"):
        raise ValueError("P1c cost-family baseline aggregate metrics drifted from its source.")
    if baseline_buckets != source.get("bucket_metrics"):
        raise ValueError("P1c cost-family baseline bucket metrics drifted from its source.")

    results = stress.get("results_by_profile", {})
    if tuple(results) != P1D3A_COST_PROFILE_IDS:
        raise ValueError("P1c profile result order or membership drifted.")
    expected_bucket_order = (*P1D3A_BUCKET_IDS, "clean_false_positive")
    all_buggy = [variant_id for bucket in P1D3A_BUCKET_IDS for variant_id in _EXPECTED_BUCKET_SUPPORT[bucket]]
    all_buggy_tuple = tuple(all_buggy)
    gap_directions = {
        "bug_discovery_rate_within_budget": "higher_is_better",
        "cost_to_first_failure": "lower_is_better",
        "location_top3_accuracy": "higher_is_better",
        "cause_top1_accuracy": "higher_is_better",
        "fix_intent_top1_accuracy": "higher_is_better",
        "wrong_cause_high_confidence_rate": "lower_is_better",
        "false_positive_rate_on_clean_cases": "lower_is_better",
        "mean_investigation_cost": "lower_is_better",
    }
    for profile_id in P1D3A_COST_PROFILE_IDS:
        profile_result = results[profile_id]
        for field in (
            "aggregate_metrics_by_policy", "bucket_metrics_by_policy",
            "raw_variant_worst_cases_by_policy", "profile_vs_baseline_gap_by_policy",
            "clean_false_positive_stress_by_policy",
        ):
            if tuple(profile_result.get(field, {})) != P1D3A_FORMAL_STRATEGY_IDS:
                raise ValueError(f"P1c {field} policy order or membership drifted for {profile_id}.")
        for policy in P1D3A_FORMAL_STRATEGY_IDS:
            aggregate = profile_result["aggregate_metrics_by_policy"][policy]
            if tuple(aggregate) != _EXPECTED_AGGREGATE_METRIC_KEYS:
                raise ValueError(f"P1c aggregate metric order or membership drifted for {profile_id}/{policy}.")
            bucket_metrics = profile_result["bucket_metrics_by_policy"][policy]
            if tuple(bucket_metrics) != expected_bucket_order:
                raise ValueError(f"P1c bucket order or membership drifted for {profile_id}/{policy}.")
            raw = profile_result["raw_variant_worst_cases_by_policy"][policy]
            if tuple(raw) != _EXPECTED_RAW_EVIDENCE_KEYS:
                raise ValueError(f"P1c raw secondary evidence is missing, extra, or reordered for {profile_id}/{policy}.")
            for raw_field in _EXPECTED_RAW_EVIDENCE_KEYS[:-1]:
                if not _ordered_subset(raw.get(raw_field), all_buggy_tuple):
                    raise ValueError(f"P1c raw evidence {raw_field} is invalid for {profile_id}/{policy}.")
            if not raw["max_first_failure_cost_variant_ids"]:
                raise ValueError(f"P1c first-failure maximum evidence is empty for {profile_id}/{policy}.")
            if (
                raw["missed_bug_variant_ids"]
                and raw["max_first_failure_cost_variant_ids"]
                != raw["missed_bug_variant_ids"]
            ):
                raise ValueError(
                    f"P1c first-failure penalty evidence disagrees for {profile_id}/{policy}."
                )
            if not _ordered_subset(raw.get("false_positive_clean_variant_ids"), _EXPECTED_CLEAN_SUPPORT):
                raise ValueError(f"P1c raw clean evidence is invalid for {profile_id}/{policy}.")
            for bucket in P1D3A_BUCKET_IDS:
                metrics = bucket_metrics[bucket]
                if tuple(metrics) != _EXPECTED_BUCKET_METRIC_KEYS:
                    raise ValueError(f"P1c bucket metric fields drifted for {profile_id}/{policy}/{bucket}.")
                if (metrics.get("variant_count"), metrics.get("buggy_variant_count"), metrics.get("clean_variant_count")) != (4, 4, 0):
                    raise ValueError(f"P1c buggy support counts drifted for {profile_id}/{policy}/{bucket}.")
                support = _EXPECTED_BUCKET_SUPPORT[bucket]
                for source_field, (raw_field, evidence_kind) in _RAW_RATE_EVIDENCE.items():
                    evidence_count = sum(item in set(raw[raw_field]) for item in support)
                    numerator = 4 - evidence_count if evidence_kind == "miss" else evidence_count
                    if metrics.get(source_field) != float(Fraction(numerator, 4)):
                        raise ValueError(
                            f"P1c {source_field} evidence arithmetic disagrees for "
                            f"{profile_id}/{policy}/{bucket}."
                        )
                if metrics.get("bucket_false_positive_rate") is not None:
                    raise ValueError(f"P1c buggy false-positive metric is invalid for {profile_id}/{policy}/{bucket}.")
                if not _is_fraction_step(
                    metrics.get("bucket_cost_to_first_failure"), 4, minimum=0, maximum=14
                ):
                    raise ValueError(f"P1c first-failure mean/domain drifted for {profile_id}/{policy}/{bucket}.")
                if not _is_fraction_step(
                    metrics.get("bucket_mean_investigation_cost"), 4, minimum=0, maximum=12
                ):
                    raise ValueError(f"P1c investigation-cost mean/domain drifted for {profile_id}/{policy}/{bucket}.")

            clean_metrics = bucket_metrics["clean_false_positive"]
            if tuple(clean_metrics) != _EXPECTED_BUCKET_METRIC_KEYS:
                raise ValueError(f"P1c clean bucket metric fields drifted for {profile_id}/{policy}.")
            if (
                clean_metrics.get("variant_count"),
                clean_metrics.get("buggy_variant_count"),
                clean_metrics.get("clean_variant_count"),
            ) != (5, 0, 5):
                raise ValueError(f"P1c clean support counts drifted for {profile_id}/{policy}.")
            for field in (
                "bucket_bug_discovery_rate", "bucket_cost_to_first_failure",
                "bucket_location_top3_accuracy", "bucket_cause_top1_accuracy",
                "bucket_fix_intent_top1_accuracy", "bucket_wrong_cause_high_confidence_rate",
            ):
                if clean_metrics.get(field) is not None:
                    raise ValueError(f"P1c clean-only field {field} has invalid buggy data for {profile_id}/{policy}.")
            false_positive_ids = raw["false_positive_clean_variant_ids"]
            clean_fp_rate = float(Fraction(len(false_positive_ids), 5))
            if clean_metrics.get("bucket_false_positive_rate") != clean_fp_rate:
                raise ValueError(f"P1c clean false-positive arithmetic disagrees for {profile_id}/{policy}.")
            if not _is_fraction_step(
                clean_metrics.get("bucket_mean_investigation_cost"), 5, minimum=0, maximum=12
            ):
                raise ValueError(f"P1c clean mean-cost domain drifted for {profile_id}/{policy}.")

            buggy_metric_to_aggregate = {
                "bucket_bug_discovery_rate": "bug_discovery_rate_within_budget",
                "bucket_cost_to_first_failure": "cost_to_first_failure",
                "bucket_location_top3_accuracy": "location_top3_accuracy",
                "bucket_cause_top1_accuracy": "cause_top1_accuracy",
                "bucket_fix_intent_top1_accuracy": "fix_intent_top1_accuracy",
                "bucket_wrong_cause_high_confidence_rate": "wrong_cause_high_confidence_rate",
            }
            for bucket_field, aggregate_field in buggy_metric_to_aggregate.items():
                expected_aggregate = _rounded_mean([
                    bucket_metrics[bucket][bucket_field] for bucket in P1D3A_BUCKET_IDS
                ])
                if aggregate.get(aggregate_field) != expected_aggregate:
                    raise ValueError(f"P1c aggregate {aggregate_field} arithmetic drifted for {profile_id}/{policy}.")
            if aggregate.get("false_positive_rate_on_clean_cases") != clean_fp_rate:
                raise ValueError(f"P1c aggregate clean rate arithmetic drifted for {profile_id}/{policy}.")
            expected_mean_cost = round(
                (
                    sum(
                        bucket_metrics[bucket]["bucket_mean_investigation_cost"] * 4
                        for bucket in P1D3A_BUCKET_IDS
                    )
                    + clean_metrics["bucket_mean_investigation_cost"] * 5
                ) / 25,
                6,
            )
            if aggregate.get("mean_investigation_cost") != expected_mean_cost:
                raise ValueError(f"P1c aggregate investigation-cost arithmetic drifted for {profile_id}/{policy}.")

            clean = profile_result["clean_false_positive_stress_by_policy"][policy]
            if not _is_fraction_step(clean.get("clean_no_bug_stop_rate"), 5, minimum=0, maximum=1):
                raise ValueError(f"P1c clean no-bug stop rate/domain drifted for {profile_id}/{policy}.")
            expected_clean = _expected_clean_source_row(
                false_positive_ids=false_positive_ids,
                clean_false_positive_rate=clean_fp_rate,
                clean_mean_cost=clean_metrics["bucket_mean_investigation_cost"],
                clean_no_bug_stop_rate=clean["clean_no_bug_stop_rate"],
            )
            if clean != expected_clean:
                raise ValueError(f"P1c clean evidence or arithmetic drifted for {profile_id}/{policy}.")

            gap = profile_result["profile_vs_baseline_gap_by_policy"][policy]
            if tuple(gap) != _EXPECTED_AGGREGATE_METRIC_KEYS:
                raise ValueError(f"P1c profile-gap metric order drifted for {profile_id}/{policy}.")
            expected_gap: dict[str, Any] = {}
            for metric, direction in gap_directions.items():
                baseline_value = baseline_aggregates[policy][metric]
                profile_value = aggregate[metric]
                difference = (
                    baseline_value - profile_value
                    if direction == "higher_is_better"
                    else profile_value - baseline_value
                )
                expected_gap[metric] = {
                    "direction": direction,
                    "baseline_value": baseline_value,
                    "profile_value": profile_value,
                    "gap": round(difference, 6),
                }
            if gap != expected_gap:
                raise ValueError(f"P1c profile-gap arithmetic drifted for {profile_id}/{policy}.")

        if stress.get("profile_vs_baseline_gap_by_policy", {}).get(profile_id) != profile_result["profile_vs_baseline_gap_by_policy"]:
            raise ValueError(f"P1c duplicated profile-gap evidence drifted for {profile_id}.")
        if stress.get("clean_false_positive_stress_by_policy", {}).get(profile_id) != profile_result["clean_false_positive_stress_by_policy"]:
            raise ValueError(f"P1c duplicated clean evidence drifted for {profile_id}.")
    if _clean_projection_sha256(_clean_projection_from_source(stress)) != (
        _EXPECTED_CLEAN_PROJECTION_SHA256
    ):
        raise ValueError("P1c accepted clean outcome identity drifted.")


def _dataset_summary(source: dict[str, Any]) -> dict[str, Any]:
    dataset = source["dataset"]
    buckets = dataset["bucket_sizes"]
    return {
        "total_variant_count": dataset["total_variants"],
        "buggy_variant_count": dataset["buggy_variants"],
        "clean_variant_count": dataset["clean_variants"],
        "buggy_variant_ids": [
            item for bucket in P1D3A_BUCKET_IDS for item in buckets[bucket]["variant_ids"]
        ],
        "clean_variant_ids": list(buckets["clean_false_positive"]["variant_ids"]),
        "buggy_bucket_count": 5,
        "uniform_variant_support_within_buggy_bucket": True,
    }


def _primary_matrix(profile_id: str, profile_result: dict[str, Any]) -> dict[str, Any]:
    cells_by_policy: dict[str, dict[str, Any]] = {}
    for policy in P1D3A_FORMAL_STRATEGY_IDS:
        missed_all = set(profile_result["raw_variant_worst_cases_by_policy"][policy]["missed_bug_variant_ids"])
        policy_cells: dict[str, Any] = {}
        for bucket in P1D3A_BUCKET_IDS:
            support = list(_EXPECTED_BUCKET_SUPPORT[bucket])
            missed = [item for item in support if item in missed_all]
            discovered = [item for item in support if item not in missed_all]
            numerator = len(discovered)
            rate = Fraction(numerator, 4)
            policy_cells[bucket] = {
                "profile_id": profile_id,
                "policy_id": policy,
                "bucket_id": bucket,
                "discovered_numerator": numerator,
                "variant_denominator": 4,
                "discovery_rate": float(rate),
                "discovery_loss": float(1 - rate),
                "support_variant_ids": support,
                "discovered_variant_ids": discovered,
                "missed_variant_ids": missed,
                "evidence_source": _PRIMARY_EVIDENCE_SOURCE,
                "reconstruction_rule": _PRIMARY_RECONSTRUCTION_RULE,
            }
        cells_by_policy[policy] = policy_cells
    return {
        "metric_id": "discovery_loss",
        "direction": "lower_is_better",
        "row_policy_ids": list(P1D3A_FORMAL_STRATEGY_IDS),
        "column_bucket_ids": list(P1D3A_BUCKET_IDS),
        "cell_count": 30,
        "cells_by_policy": cells_by_policy,
    }


def _solution(matrix: dict[str, Any]) -> dict[str, Any]:
    rows: dict[str, Any] = {}
    worst_by_policy: dict[str, Fraction] = {}
    for policy in P1D3A_FORMAL_STRATEGY_IDS:
        cells = matrix["cells_by_policy"][policy]
        losses = {
            bucket: Fraction(4 - cells[bucket]["discovered_numerator"], 4)
            for bucket in P1D3A_BUCKET_IDS
        }
        worst = max(losses.values())
        average = sum(losses.values(), start=Fraction()) / 5
        worst_by_policy[policy] = worst
        rows[policy] = {
            "worst_bucket_loss": float(worst),
            "worst_bucket_ids": [bucket for bucket in P1D3A_BUCKET_IDS if losses[bucket] == worst],
            "reference_average_loss": float(average),
            "average_to_worst_gap": float(worst - average),
        }
    security_loss = min(worst_by_policy.values())
    return {
        "qualification": "profile-conditioned restricted-pure security loss among the six fixed deterministic policies",
        "by_policy": rows,
        "restricted_pure_security_loss": float(security_loss),
        "restricted_pure_security_policies": [
            policy for policy in P1D3A_FORMAL_STRATEGY_IDS if worst_by_policy[policy] == security_loss
        ],
        "tie_rule": "Use exact rational counts before display rounding and retain stable policy and bucket order.",
    }


def _g0_comparison(matrix: dict[str, Any], solution: dict[str, Any], g0: dict[str, Any]) -> dict[str, Any]:
    g0_matrix = g0["g0_discovery_loss_matrix"]["cells_by_policy"]
    g0_solution = g0["restricted_pure_solution"]["by_policy"]
    cell_deltas: dict[str, Any] = {}
    policy_deltas: dict[str, Any] = {}
    for policy in P1D3A_FORMAL_STRATEGY_IDS:
        cell_deltas[policy] = {
            bucket: matrix["cells_by_policy"][policy][bucket]["discovery_loss"] - g0_matrix[policy][bucket]["discovery_loss"]
            for bucket in P1D3A_BUCKET_IDS
        }
        policy_deltas[policy] = {
            "reference_average_delta": solution["by_policy"][policy]["reference_average_loss"] - g0_solution[policy]["reference_average_loss"],
            "worst_bucket_loss_delta": solution["by_policy"][policy]["worst_bucket_loss"] - g0_solution[policy]["worst_bucket_loss"],
            "g0_worst_bucket_ids": list(g0_solution[policy]["worst_bucket_ids"]),
            "profile_worst_bucket_ids": list(solution["by_policy"][policy]["worst_bucket_ids"]),
        }
    return {
        "comparison_scope": "same_policy_descriptive_discovery_loss_only",
        "positive_delta_meaning": "higher discovery loss under the fixed cost profile",
        "cell_delta_by_policy": cell_deltas,
        "aggregate_delta_by_policy": policy_deltas,
    }


def _clean_stress(profile_id: str, profile_result: dict[str, Any]) -> dict[str, Any]:
    rows: dict[str, Any] = {}
    for policy in P1D3A_FORMAL_STRATEGY_IDS:
        source = profile_result["clean_false_positive_stress_by_policy"][policy]
        ids = list(source["diagnostic_variant_ids"])
        rows[policy] = {
            "false_positive_numerator": len(ids),
            "clean_variant_denominator": 5,
            "clean_false_positive_rate": source["false_positive_rate_on_clean_cases"],
            "clean_mean_investigation_cost": source["clean_bucket_mean_investigation_cost"],
            "clean_no_bug_stop_rate": source["clean_no_bug_stop_rate"],
            "false_positive_clean_variant_ids": ids,
            "clean_source_identity": _clean_source_identity(
                profile_id,
                policy,
                clean_false_positive_rate=source["false_positive_rate_on_clean_cases"],
                clean_mean_investigation_cost=source[
                    "clean_bucket_mean_investigation_cost"
                ],
                clean_no_bug_stop_rate=source["clean_no_bug_stop_rate"],
            ),
        }
    return {
        "formal_game_membership": "excluded",
        "clean_variant_ids": list(_EXPECTED_CLEAN_SUPPORT),
        "by_policy": rows,
        "risk_note": "Results cover only the current five clean variants and do not establish broader false-positive safety.",
    }


def _secondary_matrices(profile_result: dict[str, Any]) -> dict[str, Any]:
    matrices: dict[str, Any] = {}
    bucket_metrics = profile_result["bucket_metrics_by_policy"]
    raw_evidence = profile_result["raw_variant_worst_cases_by_policy"]
    for metric_id, (source_field, transform) in _SECONDARY_SOURCES.items():
        values: dict[str, Any] = {}
        source_values: dict[str, Any] = {}
        for policy in P1D3A_FORMAL_STRATEGY_IDS:
            values[policy] = {}
            source_values[policy] = {}
            for bucket in P1D3A_BUCKET_IDS:
                source_value = bucket_metrics[policy][bucket][source_field]
                value = source_value
                if transform == "one_minus":
                    value = 1.0 - value
                source_values[policy][bucket] = source_value
                values[policy][bucket] = value
        matrix: dict[str, Any] = {
            "direction": "lower_is_better",
            "source_p1c_metric": source_field,
            "transform": transform,
            "used_in_restricted_pure_solution": False,
            "row_policy_ids": list(P1D3A_FORMAL_STRATEGY_IDS),
            "column_bucket_ids": list(P1D3A_BUCKET_IDS),
            "source_values_by_policy": source_values,
            "values_by_policy": values,
        }
        if source_field in _RAW_RATE_EVIDENCE:
            raw_field, evidence_kind = _RAW_RATE_EVIDENCE[source_field]
            matrix["raw_variant_evidence_field"] = raw_field
            matrix["raw_variant_evidence_kind"] = evidence_kind
            matrix["raw_variant_evidence_by_policy"] = {
                policy: {
                    bucket: [
                        item
                        for item in _EXPECTED_BUCKET_SUPPORT[bucket]
                        if item in set(raw_evidence[policy][raw_field])
                    ]
                    for bucket in P1D3A_BUCKET_IDS
                }
                for policy in P1D3A_FORMAL_STRATEGY_IDS
            }
        else:
            matrix["raw_variant_evidence_field"] = None
            matrix["raw_variant_evidence_kind"] = "not_exposed_by_p1c"
            matrix["raw_variant_evidence_by_policy"] = {}
        if metric_id == "cost_to_first_failure":
            matrix.update({"failure_cost": 14, "missed_buggy_variant_penalty": 14})
        matrices[metric_id] = matrix
    return matrices


def build_p1d3a_summary(p1c_summary: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build a validated P1d3a report, failing closed before partial output."""

    _validate_runtime_contract()
    source = p1c_summary if p1c_summary is not None else build_p1d3a_source()
    g0 = _validate_g0_reference(source)
    _validate_p1c_cost_source(source)
    stress = source["observation_cost_stress"]
    profile_specs = {profile["profile_id"]: profile for profile in stress["profiles"]}
    results_by_profile: dict[str, Any] = {}
    for profile_id in P1D3A_COST_PROFILE_IDS:
        source_result = stress["results_by_profile"][profile_id]
        matrix = _primary_matrix(profile_id, source_result)
        solution = _solution(matrix)
        results_by_profile[profile_id] = {
            "profile_id": profile_id,
            "effective_costs_by_action": dict(profile_specs[profile_id]["effective_costs_by_action"]),
            "primary_discovery_loss_matrix": matrix,
            "restricted_pure_solution": solution,
            "g0_same_policy_comparison": _g0_comparison(matrix, solution, g0),
            "clean_false_positive_stress": _clean_stress(profile_id, source_result),
            "secondary_metric_matrices": _secondary_matrices(source_result),
            "validation_status": {"status": "valid", "cell_count": 30},
        }

    summary = {
        "schema_version": P1D3A_SCHEMA_VERSION,
        "analysis_phase": P1D3A_ANALYSIS_PHASE,
        "game_family_id": P1D3A_GAME_FAMILY_ID,
        "benchmark_id": _EXPECTED_BENCHMARK_ID,
        "report_role": _EXPECTED_REPORT_ROLE,
        "observation_mode": _EXPECTED_OBSERVATION_MODE,
        "retrospective_analysis": dict(_EXPECTED_RETROSPECTIVE_ANALYSIS),
        "g0_reference_identity": deepcopy(_EXPECTED_G0_REFERENCE_IDENTITY),
        "p1d2_immutable_context": deepcopy(_EXPECTED_P1D2_CONTEXT),
        "validation_status": dict(_EXPECTED_VALIDATION_STATUS),
        "dataset_summary": _dataset_summary(source),
        "fixed_settings": dict(source["settings"]),
        "default_action_specifications": _action_specifications(),
        "formal_strategy_ids": list(P1D3A_FORMAL_STRATEGY_IDS),
        "excluded_policy_ids": ["state_sequence_guard"],
        "diagnostic_only_policy_ids": ["random_action"],
        "bucket_ids": list(P1D3A_BUCKET_IDS),
        "bucket_support": {bucket: list(ids) for bucket, ids in _EXPECTED_BUCKET_SUPPORT.items()},
        "cost_profile_ids": list(P1D3A_COST_PROFILE_IDS),
        "cost_profiles": [dict(profile) for profile in stress["profiles"]],
        "information_structure": dict(_EXPECTED_INFORMATION_STRUCTURE),
        "loss_definition": deepcopy(_EXPECTED_LOSS_DEFINITION),
        "reference_distribution": deepcopy(_EXPECTED_REFERENCE_DISTRIBUTION),
        "results_by_profile": results_by_profile,
        "mixed_solution": {"computed": False, "reason": "mixed solver is outside the P1d3a initial slice"},
        "software_acceptance": {
            "status": "accepted",
            "basis": "all exact preflight, completeness, arithmetic, and serialization contracts are satisfied",
            "independent_of_profile_performance": True,
        },
        "limitations": list(_EXPECTED_LIMITATIONS),
        "non_claims": list(_EXPECTED_NON_CLAIMS),
        "notes": list(_EXPECTED_NOTES),
    }
    validate_p1d3a_summary(summary)
    return summary


def validate_p1d3a_summary(summary: dict[str, Any]) -> None:
    """Reject invalid or partial objects before serialization."""

    _validate_runtime_contract()
    if tuple(summary) != _EXPECTED_TOP_LEVEL_KEYS:
        raise ValueError("P1d3a top-level fields are missing, extra, or reordered.")
    if (
        summary.get("schema_version"), summary.get("analysis_phase"),
        summary.get("game_family_id"), summary.get("benchmark_id"),
        summary.get("report_role"), summary.get("observation_mode"),
    ) != (
        P1D3A_SCHEMA_VERSION, P1D3A_ANALYSIS_PHASE, P1D3A_GAME_FAMILY_ID,
        _EXPECTED_BENCHMARK_ID, _EXPECTED_REPORT_ROLE, _EXPECTED_OBSERVATION_MODE,
    ):
        raise ValueError("P1d3a output identity is invalid.")
    if summary.get("retrospective_analysis") != _EXPECTED_RETROSPECTIVE_ANALYSIS:
        raise ValueError("P1d3a retrospective scope is invalid.")
    if summary.get("g0_reference_identity") != _EXPECTED_G0_REFERENCE_IDENTITY:
        raise ValueError("P1d3a G0 reference identity is invalid.")
    if summary.get("p1d2_immutable_context") != _EXPECTED_P1D2_CONTEXT:
        raise ValueError("P1d3a P1d2 immutable context is invalid.")
    if summary.get("validation_status") != _EXPECTED_VALIDATION_STATUS:
        raise ValueError("P1d3a refuses to serialize an invalid or inconclusive report.")
    dataset_summary = summary.get("dataset_summary", {})
    if tuple(dataset_summary) != tuple(_expected_dataset_summary()):
        raise ValueError("P1d3a dataset summary field order is invalid.")
    if dataset_summary != _expected_dataset_summary():
        raise ValueError("P1d3a dataset summary is invalid.")
    if summary.get("fixed_settings") != _EXPECTED_SETTINGS:
        raise ValueError("P1d3a fixed settings are invalid.")
    if tuple(summary.get("formal_strategy_ids", ())) != P1D3A_FORMAL_STRATEGY_IDS:
        raise ValueError("P1d3a formal strategies are invalid.")
    if summary.get("excluded_policy_ids") != ["state_sequence_guard"]:
        raise ValueError("P1d3a excluded policy context is invalid.")
    if summary.get("diagnostic_only_policy_ids") != ["random_action"]:
        raise ValueError("P1d3a diagnostic-only policy context is invalid.")
    if tuple(summary.get("bucket_ids", ())) != P1D3A_BUCKET_IDS:
        raise ValueError("P1d3a bucket order is invalid.")
    if tuple(summary.get("cost_profile_ids", ())) != P1D3A_COST_PROFILE_IDS:
        raise ValueError("P1d3a profile order is invalid.")
    bucket_support = summary.get("bucket_support", {})
    if tuple(bucket_support) != P1D3A_BUCKET_IDS:
        raise ValueError("P1d3a bucket support order is invalid.")
    if bucket_support != {
        bucket: list(ids) for bucket, ids in _EXPECTED_BUCKET_SUPPORT.items()
    }:
        raise ValueError("P1d3a bucket support is invalid.")
    action_specs = summary.get("default_action_specifications", [])
    expected_action_specs = _action_specifications()
    if (
        not isinstance(action_specs, list)
        or [spec.get("action_id") for spec in action_specs] != list(_EXPECTED_ACTION_SPECS)
        or any(tuple(spec) != tuple(expected) for spec, expected in zip(
            action_specs, expected_action_specs
        ))
    ):
        raise ValueError("P1d3a action specification order is invalid.")
    if action_specs != expected_action_specs:
        raise ValueError("P1d3a action specifications are invalid.")
    if summary.get("information_structure") != _EXPECTED_INFORMATION_STRUCTURE:
        raise ValueError("P1d3a information structure is invalid.")
    if summary.get("loss_definition") != _EXPECTED_LOSS_DEFINITION:
        raise ValueError("P1d3a loss definition is invalid.")
    reference_distribution = summary.get("reference_distribution", {})
    if tuple(reference_distribution) != tuple(_EXPECTED_REFERENCE_DISTRIBUTION):
        raise ValueError("P1d3a reference distribution field order is invalid.")
    if tuple(reference_distribution.get("bucket_probabilities", {})) != P1D3A_BUCKET_IDS:
        raise ValueError("P1d3a reference bucket probability order is invalid.")
    if reference_distribution != _EXPECTED_REFERENCE_DISTRIBUTION:
        raise ValueError("P1d3a reference distribution is invalid.")
    profiles = summary.get("cost_profiles", [])
    if [profile.get("profile_id") for profile in profiles] != list(P1D3A_COST_PROFILE_IDS):
        raise ValueError("P1d3a profile specifications are incomplete or reordered.")
    for profile in profiles:
        _validate_profile_specification(profile, profile["profile_id"])
    results = summary.get("results_by_profile", {})
    if tuple(results) != P1D3A_COST_PROFILE_IDS:
        raise ValueError("P1d3a profile results are incomplete.")
    for profile_id in P1D3A_COST_PROFILE_IDS:
        result = results[profile_id]
        if tuple(result) != (
            "profile_id", "effective_costs_by_action", "primary_discovery_loss_matrix",
            "restricted_pure_solution", "g0_same_policy_comparison",
            "clean_false_positive_stress", "secondary_metric_matrices", "validation_status",
        ):
            raise ValueError(f"P1d3a profile result fields are invalid for {profile_id}.")
        if result.get("profile_id") != profile_id:
            raise ValueError(f"P1d3a profile result identity is invalid for {profile_id}.")
        effective_costs = result.get("effective_costs_by_action", {})
        if tuple(effective_costs) != tuple(_EXPECTED_ACTION_SPECS):
            raise ValueError(f"P1d3a result effective-cost order is invalid for {profile_id}.")
        if effective_costs != _expected_effective_costs(profile_id):
            raise ValueError(f"P1d3a result effective costs are invalid for {profile_id}.")
        if result.get("validation_status") != {"status": "valid", "cell_count": 30}:
            raise ValueError(f"P1d3a profile validation status is invalid for {profile_id}.")
        matrix = result.get("primary_discovery_loss_matrix", {})
        if (
            tuple(matrix) != (
                "metric_id", "direction", "row_policy_ids", "column_bucket_ids",
                "cell_count", "cells_by_policy",
            )
            or matrix.get("metric_id") != "discovery_loss"
            or matrix.get("direction") != "lower_is_better"
            or matrix.get("row_policy_ids") != list(P1D3A_FORMAL_STRATEGY_IDS)
            or matrix.get("column_bucket_ids") != list(P1D3A_BUCKET_IDS)
            or matrix.get("cell_count") != 30
            or tuple(matrix.get("cells_by_policy", {})) != P1D3A_FORMAL_STRATEGY_IDS
        ):
            raise ValueError(f"P1d3a primary matrix is incomplete for {profile_id}.")
        for policy in P1D3A_FORMAL_STRATEGY_IDS:
            cells = matrix["cells_by_policy"][policy]
            if tuple(cells) != P1D3A_BUCKET_IDS:
                raise ValueError(f"P1d3a primary matrix buckets are invalid for {profile_id}/{policy}.")
            for bucket in P1D3A_BUCKET_IDS:
                cell = cells[bucket]
                support = list(_EXPECTED_BUCKET_SUPPORT[bucket])
                discovered = cell.get("discovered_variant_ids")
                missed = cell.get("missed_variant_ids")
                if cell.get("support_variant_ids") != support:
                    raise ValueError(f"P1d3a cell support is invalid for {profile_id}/{policy}/{bucket}.")
                if not isinstance(discovered, list) or not isinstance(missed, list):
                    raise ValueError(f"P1d3a cell evidence is missing for {profile_id}/{policy}/{bucket}.")
                if discovered != [item for item in support if item in set(discovered)]:
                    raise ValueError(f"P1d3a discovered evidence order is invalid for {profile_id}/{policy}/{bucket}.")
                if missed != [item for item in support if item in set(missed)]:
                    raise ValueError(f"P1d3a missed evidence order is invalid for {profile_id}/{policy}/{bucket}.")
                if set(discovered) & set(missed) or set(discovered) | set(missed) != set(support):
                    raise ValueError(f"P1d3a cell evidence is not a partition for {profile_id}/{policy}/{bucket}.")
                numerator = len(discovered)
                if (
                    tuple(cell) != (
                        "profile_id", "policy_id", "bucket_id", "discovered_numerator",
                        "variant_denominator", "discovery_rate", "discovery_loss",
                        "support_variant_ids", "discovered_variant_ids", "missed_variant_ids",
                        "evidence_source", "reconstruction_rule",
                    )
                    or cell.get("profile_id") != profile_id
                    or cell.get("policy_id") != policy
                    or cell.get("bucket_id") != bucket
                    or cell.get("discovered_numerator") != numerator
                    or cell.get("variant_denominator") != 4
                    or cell.get("discovery_rate") != float(Fraction(numerator, 4))
                    or cell.get("discovery_loss") != float(Fraction(4 - numerator, 4))
                    or cell.get("evidence_source")
                    != "P1c raw_variant_worst_cases_by_policy.missed_bug_variant_ids"
                    or cell.get("reconstruction_rule")
                    != "stable bucket support minus missed IDs; discovered and missed are disjoint and exhaustive"
                ):
                    raise ValueError(f"P1d3a cell arithmetic is invalid for {profile_id}/{policy}/{bucket}.")
        expected_solution = _solution(matrix)
        if result.get("restricted_pure_solution") != expected_solution:
            raise ValueError(f"P1d3a restricted-pure solution is invalid for {profile_id}.")
        comparison = result.get("g0_same_policy_comparison", {})
        if (
            tuple(comparison) != (
                "comparison_scope", "positive_delta_meaning", "cell_delta_by_policy",
                "aggregate_delta_by_policy",
            )
            or comparison.get("comparison_scope")
            != "same_policy_descriptive_discovery_loss_only"
            or comparison.get("positive_delta_meaning")
            != "higher discovery loss under the fixed cost profile"
            or tuple(comparison.get("cell_delta_by_policy", {}))
            != P1D3A_FORMAL_STRATEGY_IDS
            or tuple(comparison.get("aggregate_delta_by_policy", {}))
            != P1D3A_FORMAL_STRATEGY_IDS
        ):
            raise ValueError(f"P1d3a G0 comparison scope is invalid for {profile_id}.")
        for policy in P1D3A_FORMAL_STRATEGY_IDS:
            profile_losses = [
                matrix["cells_by_policy"][policy][bucket]["discovery_loss"]
                for bucket in P1D3A_BUCKET_IDS
            ]
            g0_losses = _EXPECTED_G0_LOSS_ROWS[policy]
            expected_cell_deltas = {
                bucket: profile_losses[index] - g0_losses[index]
                for index, bucket in enumerate(P1D3A_BUCKET_IDS)
            }
            if comparison.get("cell_delta_by_policy", {}).get(policy) != expected_cell_deltas:
                raise ValueError(f"P1d3a G0 cell deltas are invalid for {profile_id}/{policy}.")
            g0_average = sum(g0_losses) / 5
            expected_aggregate = {
                "reference_average_delta": expected_solution["by_policy"][policy]["reference_average_loss"] - g0_average,
                "worst_bucket_loss_delta": expected_solution["by_policy"][policy]["worst_bucket_loss"] - max(g0_losses),
                "g0_worst_bucket_ids": [
                    bucket for index, bucket in enumerate(P1D3A_BUCKET_IDS)
                    if g0_losses[index] == max(g0_losses)
                ],
                "profile_worst_bucket_ids": expected_solution["by_policy"][policy]["worst_bucket_ids"],
            }
            if comparison.get("aggregate_delta_by_policy", {}).get(policy) != expected_aggregate:
                raise ValueError(f"P1d3a G0 aggregate deltas are invalid for {profile_id}/{policy}.")
        clean = result.get("clean_false_positive_stress", {})
        if (
            tuple(clean) != (
                "formal_game_membership", "clean_variant_ids", "by_policy", "risk_note"
            )
            or clean.get("formal_game_membership") != "excluded"
            or clean.get("clean_variant_ids") != list(_EXPECTED_CLEAN_SUPPORT)
            or clean.get("risk_note")
            != "Results cover only the current five clean variants and do not establish broader false-positive safety."
        ):
            raise ValueError(f"P1d3a clean support is invalid for {profile_id}.")
        if tuple(clean.get("by_policy", {})) != P1D3A_FORMAL_STRATEGY_IDS:
            raise ValueError(f"P1d3a clean rows are incomplete for {profile_id}.")
        for policy, row in clean["by_policy"].items():
            false_positive_ids = row.get("false_positive_clean_variant_ids")
            if (
                tuple(row) != (
                    "false_positive_numerator", "clean_variant_denominator",
                    "clean_false_positive_rate", "clean_mean_investigation_cost",
                    "clean_no_bug_stop_rate", "false_positive_clean_variant_ids",
                    "clean_source_identity",
                )
                or not isinstance(false_positive_ids, list)
                or false_positive_ids != [item for item in _EXPECTED_CLEAN_SUPPORT if item in set(false_positive_ids)]
                or row.get("false_positive_numerator") != len(false_positive_ids)
                or row.get("clean_variant_denominator") != 5
                or row.get("clean_false_positive_rate") != float(Fraction(len(false_positive_ids), 5))
                or not _is_fraction_step(
                    row.get("clean_mean_investigation_cost"), 5, minimum=0, maximum=12
                )
                or not _is_fraction_step(
                    row.get("clean_no_bug_stop_rate"), 5, minimum=0, maximum=1
                )
            ):
                raise ValueError(f"P1d3a clean evidence is invalid for {profile_id}/{policy}.")
            identity = row.get("clean_source_identity", {})
            if tuple(identity) != _CLEAN_SOURCE_IDENTITY_KEYS:
                raise ValueError(
                    f"P1d3a clean source identity order is invalid for {profile_id}/{policy}."
                )
            if any(
                tuple(identity.get(field, {})) != _CLEAN_SOURCE_FIELD_KEYS
                for field in _CLEAN_SOURCE_IDENTITY_KEYS
            ):
                raise ValueError(
                    f"P1d3a clean source identity fields are invalid for {profile_id}/{policy}."
                )
            expected_identity = _clean_source_identity(
                profile_id,
                policy,
                clean_false_positive_rate=row["clean_false_positive_rate"],
                clean_mean_investigation_cost=row["clean_mean_investigation_cost"],
                clean_no_bug_stop_rate=row["clean_no_bug_stop_rate"],
            )
            if identity != expected_identity:
                raise ValueError(
                    f"P1d3a clean report/source identity is invalid for {profile_id}/{policy}."
                )
        if tuple(result.get("secondary_metric_matrices", {})) != P1D3A_SECONDARY_METRIC_IDS:
            raise ValueError(f"P1d3a secondary matrices are incomplete for {profile_id}.")
        for metric_id, secondary in result["secondary_metric_matrices"].items():
            source_field, transform = _SECONDARY_SOURCES[metric_id]
            expected_secondary_keys = (
                "direction", "source_p1c_metric", "transform",
                "used_in_restricted_pure_solution", "row_policy_ids", "column_bucket_ids",
                "source_values_by_policy", "values_by_policy", "raw_variant_evidence_field",
                "raw_variant_evidence_kind", "raw_variant_evidence_by_policy",
            )
            if metric_id == "cost_to_first_failure":
                expected_secondary_keys += ("failure_cost", "missed_buggy_variant_penalty")
            if (
                tuple(secondary) != expected_secondary_keys
                or secondary.get("direction") != "lower_is_better"
                or secondary.get("source_p1c_metric") != source_field
                or secondary.get("transform") != transform
                or secondary.get("used_in_restricted_pure_solution") is not False
                or secondary.get("row_policy_ids") != list(P1D3A_FORMAL_STRATEGY_IDS)
                or secondary.get("column_bucket_ids") != list(P1D3A_BUCKET_IDS)
                or tuple(secondary.get("source_values_by_policy", {}))
                != P1D3A_FORMAL_STRATEGY_IDS
                or tuple(secondary.get("values_by_policy", {})) != P1D3A_FORMAL_STRATEGY_IDS
            ):
                raise ValueError(f"P1d3a secondary matrix contract is invalid for {profile_id}/{metric_id}.")
            raw_spec = _RAW_RATE_EVIDENCE.get(source_field)
            if raw_spec is None:
                if (
                    secondary.get("raw_variant_evidence_field") is not None
                    or secondary.get("raw_variant_evidence_kind") != "not_exposed_by_p1c"
                    or secondary.get("raw_variant_evidence_by_policy") != {}
                ):
                    raise ValueError(f"P1d3a secondary cost-evidence boundary is invalid for {profile_id}/{metric_id}.")
            else:
                raw_field, evidence_kind = raw_spec
                if (
                    secondary.get("raw_variant_evidence_field") != raw_field
                    or secondary.get("raw_variant_evidence_kind") != evidence_kind
                    or tuple(secondary.get("raw_variant_evidence_by_policy", {}))
                    != P1D3A_FORMAL_STRATEGY_IDS
                ):
                    raise ValueError(f"P1d3a secondary raw-evidence contract is invalid for {profile_id}/{metric_id}.")
            for policy in P1D3A_FORMAL_STRATEGY_IDS:
                source_values = secondary["source_values_by_policy"][policy]
                values = secondary["values_by_policy"][policy]
                if (
                    tuple(source_values) != P1D3A_BUCKET_IDS
                    or tuple(values) != P1D3A_BUCKET_IDS
                ):
                    raise ValueError(f"P1d3a secondary matrix shape is invalid for {profile_id}/{metric_id}/{policy}.")
                if raw_spec is not None:
                    evidence = secondary["raw_variant_evidence_by_policy"].get(policy, {})
                    if tuple(evidence) != P1D3A_BUCKET_IDS:
                        raise ValueError(f"P1d3a secondary evidence shape is invalid for {profile_id}/{metric_id}/{policy}.")
                for bucket in P1D3A_BUCKET_IDS:
                    source_value = source_values[bucket]
                    if raw_spec is not None:
                        ids = evidence[bucket]
                        support = _EXPECTED_BUCKET_SUPPORT[bucket]
                        if not _ordered_subset(ids, support):
                            raise ValueError(f"P1d3a secondary evidence IDs are invalid for {profile_id}/{metric_id}/{policy}/{bucket}.")
                        numerator = 4 - len(ids) if raw_spec[1] == "miss" else len(ids)
                        if source_value != float(Fraction(numerator, 4)):
                            raise ValueError(f"P1d3a secondary source arithmetic is invalid for {profile_id}/{metric_id}/{policy}/{bucket}.")
                    elif metric_id == "cost_to_first_failure":
                        if not _is_fraction_step(source_value, 4, minimum=0, maximum=14):
                            raise ValueError(f"P1d3a first-failure value/domain is invalid for {profile_id}/{policy}/{bucket}.")
                    elif not _is_fraction_step(source_value, 4, minimum=0, maximum=12):
                        raise ValueError(f"P1d3a investigation-cost value/domain is invalid for {profile_id}/{policy}/{bucket}.")
                    expected_value = 1.0 - source_value if transform == "one_minus" else source_value
                    if values[bucket] != expected_value:
                        raise ValueError(f"P1d3a secondary transform/value is invalid for {profile_id}/{metric_id}/{policy}/{bucket}.")
            if metric_id == "cost_to_first_failure":
                if secondary.get("failure_cost") != 14 or secondary.get("missed_buggy_variant_penalty") != 14:
                    raise ValueError(f"P1d3a first-failure penalty is invalid for {profile_id}.")
            elif "failure_cost" in secondary or "missed_buggy_variant_penalty" in secondary:
                raise ValueError(f"P1d3a secondary penalty fields are misplaced for {profile_id}/{metric_id}.")
    if _clean_projection_sha256(_clean_projection_from_summary(summary)) != (
        _EXPECTED_CLEAN_PROJECTION_SHA256
    ):
        raise ValueError("P1d3a accepted clean outcome identity is invalid.")
    if summary.get("mixed_solution") != {
        "computed": False, "reason": "mixed solver is outside the P1d3a initial slice"
    }:
        raise ValueError("P1d3a mixed-solution contract is invalid.")
    if summary.get("software_acceptance") != {
        "status": "accepted",
        "basis": "all exact preflight, completeness, arithmetic, and serialization contracts are satisfied",
        "independent_of_profile_performance": True,
    }:
        raise ValueError("P1d3a software acceptance is invalid.")
    if summary.get("limitations") != _EXPECTED_LIMITATIONS:
        raise ValueError("P1d3a limitations are invalid.")
    if summary.get("non_claims") != _EXPECTED_NON_CLAIMS:
        raise ValueError("P1d3a non-claims are invalid.")
    if summary.get("notes") != _EXPECTED_NOTES:
        raise ValueError("P1d3a public-boundary notes are invalid.")


def p1d3a_summary_to_json(summary: dict[str, Any]) -> str:
    validate_p1d3a_summary(summary)
    return json.dumps(summary, indent=2, ensure_ascii=False) + "\n"


def _fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def _matrix_table(lines: list[str], matrix: dict[str, Any], value_key: str = "discovery_loss") -> None:
    lines.extend([
        "| Policy | " + " | ".join(P1D3A_BUCKET_IDS) + " |",
        "|---|" + "---:|" * len(P1D3A_BUCKET_IDS),
    ])
    for policy in P1D3A_FORMAL_STRATEGY_IDS:
        cells = matrix["cells_by_policy"][policy]
        lines.append("| " + policy + " | " + " | ".join(_fmt(cells[b][value_key]) for b in P1D3A_BUCKET_IDS) + " |")


def p1d3a_summary_to_markdown(summary: dict[str, Any]) -> str:
    validate_p1d3a_summary(summary)
    g0 = summary["g0_reference_identity"]
    p1d2 = summary["p1d2_immutable_context"]
    lines = [
        "# P1d3a G1 Cost-Profile Family Report", "",
        "This retrospective analysis formalizes already-observed P1c cost-profile outcomes. It is analysis-only.", "",
        "## Identity", "",
        f"- Schema: `{summary['schema_version']}`",
        f"- Analysis phase: `{summary['analysis_phase']}`",
        f"- Game family: `{summary['game_family_id']}`",
        f"- Benchmark: `{summary['benchmark_id']}`",
        f"- Report role: `{summary['report_role']}`",
        f"- Observation mode: `{summary['observation_mode']}`", "",
        f"- Retrospective: `{str(summary['retrospective_analysis']['retrospective']).lower()}`; "
        f"new hypothesis/candidate evaluation: "
        f"`{str(summary['retrospective_analysis']['new_hypothesis_or_candidate_evaluation']).lower()}`.",
        f"- Source: {summary['retrospective_analysis']['source']}.", "",
        "## Immutable references", "",
        f"- P1d1 G0: schema=`{g0['schema_version']}`; phase=`{g0['analysis_phase']}`; "
        f"game=`{g0['game_id']}`.",
        f"- P1d1 G0 JSON SHA-256: `{g0['json_sha256']}`",
        f"- P1d1 G0 Markdown SHA-256: `{g0['markdown_sha256']}`",
        f"- P1d1 restricted-pure loss: `{_fmt(g0['restricted_pure_security_loss'])}`; "
        f"policies={','.join(g0['restricted_pure_security_policies'])}.",
        f"- P1d2 candidate: `{p1d2['candidate_policy_id']}`; "
        f"row={p1d2['candidate_discovery_loss_row']}; "
        f"worst={_fmt(p1d2['candidate_worst_bucket_discovery_loss'])}; "
        f"worst buckets={','.join(p1d2['candidate_worst_bucket_ids'])}.",
        f"- P1d2 expanded restricted-pure loss: "
        f"`{_fmt(p1d2['expanded_restricted_pure_security_loss'])}`; "
        f"policies={','.join(p1d2['expanded_restricted_pure_security_policies'])}.",
        f"- P1d2 outcome: `{p1d2['hypothesis_outcome']}`; software "
        f"`{p1d2['software_acceptance']}`; P1d3a membership "
        f"`{p1d2['p1d3a_evaluation_membership']}`.", "",
        "## Fixed contract", "",
        "- Formal policies: " + ", ".join(f"`{item}`" for item in summary["formal_strategy_ids"]),
        "- Diagnostic-only policy: `random_action`.",
        "- Excluded policy: `state_sequence_guard`.",
        "- Buggy buckets: " + ", ".join(f"`{item}`" for item in summary["bucket_ids"]),
        "- Cost profiles: " + ", ".join(f"`{item}`" for item in summary["cost_profile_ids"]),
        "- Primary loss: discovery loss only; secondary and clean metrics do not enter the solution.",
        "- The profile is externally fixed; four separate 6 by 5 matrices are reported.", "",
        "### Fixed settings", "",
    ]
    for key, value in summary["fixed_settings"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "### Information structure", ""])
    for key, value in summary["information_structure"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "### Bucket support", ""])
    for bucket, ids in summary["bucket_support"].items():
        lines.append(f"- `{bucket}`: " + ", ".join(f"`{item}`" for item in ids))
    lines.append(
        "- Clean support (outside the formal matrix): "
        + ", ".join(f"`{item}`" for item in summary["dataset_summary"]["clean_variant_ids"])
    )
    lines.extend(["", "### Default actions and profile overlays", ""])
    for spec in summary["default_action_specifications"]:
        strong_causes = ",".join(spec["strong_causes"]) or "none"
        lines.append(
            f"- `{spec['action_id']}`: default cost={spec['default_cost']}; "
            f"type=`{spec['observation_type']}`; strong causes={strong_causes}; "
            f"discovery power={_fmt(spec['discovery_power'])}; "
            f"location power={_fmt(spec['location_power'])}."
        )
    for profile in summary["cost_profiles"]:
        overlay = ", ".join(f"{key}={value}" for key, value in profile["overlay"].items())
        effective = ", ".join(
            f"{key}={value}" for key, value in profile["effective_costs_by_action"].items()
        )
        lines.append(
            f"- `{profile['profile_id']}`: overlay={overlay}; effective costs={effective}; "
            f"range={profile['cost_range']['min']}..{profile['cost_range']['max']}; "
            f"unchanged actions use default="
            f"`{str(profile['unchanged_actions_use_default']).lower()}`; "
            f"budget={profile['budget_limit']}; failure cost={profile['failure_cost']}."
        )

    for profile_id, result in summary["results_by_profile"].items():
        lines.extend(["", f"## Profile: `{profile_id}`", "", "### Primary discovery-loss matrix", ""])
        lines.append(
            "Effective costs: "
            + ", ".join(
                f"`{action_id}={cost}`"
                for action_id, cost in result["effective_costs_by_action"].items()
            )
        )
        lines.append("")
        matrix = result["primary_discovery_loss_matrix"]
        _matrix_table(lines, matrix)
        lines.extend(["", "### Cell evidence", ""])
        lines.extend([
            f"- This contract applies to every primary cell: evidence_source = `{_PRIMARY_EVIDENCE_SOURCE}`.",
            f"- This contract applies to every primary cell: reconstruction_rule = `{_PRIMARY_RECONSTRUCTION_RULE}`.",
            "- Audit relation: support is partitioned into discovered and missed IDs; "
            "discovery rate = discovered numerator / 4; discovery loss = missed numerator / 4.",
        ])
        for policy in P1D3A_FORMAL_STRATEGY_IDS:
            for bucket in P1D3A_BUCKET_IDS:
                cell = matrix["cells_by_policy"][policy][bucket]
                lines.append(
                    f"- `{policy}` / `{bucket}`: discovered {cell['discovered_numerator']}/4; "
                    f"support={','.join(cell['support_variant_ids'])}; "
                    f"discovered={','.join(cell['discovered_variant_ids']) or 'none'}; "
                    f"missed={','.join(cell['missed_variant_ids']) or 'none'}; "
                    f"rate={_fmt(cell['discovery_rate'])}; "
                    f"loss={_fmt(cell['discovery_loss'])}."
                )
        solution = result["restricted_pure_solution"]
        lines.extend(["", "### Profile-conditioned restricted-pure solution", ""])
        for policy, row in solution["by_policy"].items():
            lines.append(
                f"- `{policy}`: worst={_fmt(row['worst_bucket_loss'])}; "
                f"worst buckets={','.join(row['worst_bucket_ids'])}; "
                f"reference average={_fmt(row['reference_average_loss'])}; "
                f"gap={_fmt(row['average_to_worst_gap'])}."
            )
        lines.append(
            f"- Restricted-pure security loss: {_fmt(solution['restricted_pure_security_loss'])}; "
            f"policies={','.join(solution['restricted_pure_security_policies'])}."
        )
        comparison = result["g0_same_policy_comparison"]
        lines.extend(["", "### Same-policy descriptive G0 deltas", ""])
        for policy in P1D3A_FORMAL_STRATEGY_IDS:
            deltas = comparison["cell_delta_by_policy"][policy]
            aggregate = comparison["aggregate_delta_by_policy"][policy]
            lines.append(
                f"- `{policy}` cells: " + ", ".join(f"{b}={_fmt(deltas[b])}" for b in P1D3A_BUCKET_IDS)
                + f"; average delta={_fmt(aggregate['reference_average_delta'])}; "
                f"worst delta={_fmt(aggregate['worst_bucket_loss_delta'])}; "
                f"G0 worst buckets={','.join(aggregate['g0_worst_bucket_ids'])}; "
                f"profile worst buckets={','.join(aggregate['profile_worst_bucket_ids'])}."
            )
        lines.extend(["", "### Separate clean stress", ""])
        lines.append(
            "Clean support: "
            + ", ".join(
                f"`{item}`" for item in result["clean_false_positive_stress"]["clean_variant_ids"]
            )
        )
        for policy, row in result["clean_false_positive_stress"]["by_policy"].items():
            lines.append(
                f"- `{policy}`: false positives={row['false_positive_numerator']}/5; "
                f"rate={_fmt(row['clean_false_positive_rate'])}; mean cost={_fmt(row['clean_mean_investigation_cost'])}; "
                f"no-bug stop rate={_fmt(row['clean_no_bug_stop_rate'])}; IDs={','.join(row['false_positive_clean_variant_ids']) or 'none'}."
            )
            for field, identity in row["clean_source_identity"].items():
                lines.append(
                    f"  - `{field}` source: path=`{identity['source_path']}`; "
                    f"field=`{identity['source_field']}`; source value="
                    f"`{_fmt(identity['source_value'])}`; report field="
                    f"`{identity['report_field']}`; evidence availability="
                    f"`{identity['evidence_availability']}`."
                )
        lines.extend(["", "### Separate secondary matrices", ""])
        for metric_id, secondary in result["secondary_metric_matrices"].items():
            lines.extend([f"#### `{metric_id}`", ""])
            lines.append(
                f"Source P1c metric: `{secondary['source_p1c_metric']}`; "
                f"transform: `{secondary['transform']}`; direction: "
                f"`{secondary['direction']}`; used in restricted-pure solution: "
                f"`{str(secondary['used_in_restricted_pure_solution']).lower()}`."
            )
            if metric_id == "cost_to_first_failure":
                lines.append(
                    f"Failure cost and missed-variant penalty: "
                    f"`{secondary['failure_cost']}` / "
                    f"`{secondary['missed_buggy_variant_penalty']}`."
                )
            lines.append(
                f"Raw variant evidence field: "
                f"`{secondary['raw_variant_evidence_field']}`; evidence kind: "
                f"`{secondary['raw_variant_evidence_kind']}`."
            )
            lines.append("Each cell is shown as `P1c source value -> reported lower-is-better value`.")
            lines.append("")
            lines.extend([
                "| Policy | " + " | ".join(P1D3A_BUCKET_IDS) + " |",
                "|---|" + "---:|" * len(P1D3A_BUCKET_IDS),
            ])
            for policy in P1D3A_FORMAL_STRATEGY_IDS:
                values = secondary["values_by_policy"][policy]
                source_values = secondary["source_values_by_policy"][policy]
                lines.append(
                    "| " + policy + " | "
                    + " | ".join(
                        f"{_fmt(source_values[b])} -> {_fmt(values[b])}"
                        for b in P1D3A_BUCKET_IDS
                    ) + " |"
                )
            lines.append("")
        lines.append(
            f"Profile validation: `{result['validation_status']['status']}` "
            f"({result['validation_status']['cell_count']} primary cells)."
        )

    lines.extend([
        "", "## Validation and excluded analyses", "",
        "- All P1d1 hash, P1c cost-family, dataset, evidence, arithmetic, and ordering preflights passed before results were built.",
        "- Mixed solution: not computed; mixed solver is outside the P1d3a initial slice.",
        "- No joint profile-by-bucket game, cross-profile ranking, weighted score, G1-drop, or combined cost-drop analysis is included.",
        "", "## Public boundary", "",
    ])
    lines.extend(f"- {item}" for item in summary["notes"])
    lines.extend(["", "## Limitations and non-claims", ""])
    lines.extend(f"- {item}" for item in summary["limitations"])
    lines.extend(f"- {item}" for item in summary["non_claims"])
    lines.extend(["", "## Software acceptance", "", "Software acceptance: **accepted**. It is independent of profile performance.", ""])
    return "\n".join(lines)
