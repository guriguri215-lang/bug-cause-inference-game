"""Preregistered P1d2 state-sequence-guard evaluation and serializers."""

from __future__ import annotations

import hashlib
import inspect
import json
from copy import deepcopy
from dataclasses import fields
from fractions import Fraction
from statistics import mean
from typing import Any

from bug_cause_inference.p1b.actions import P1B_ACTION_SPECS, action_specs_to_dict
from bug_cause_inference.p1b.dataset import load_p1b_variants
from bug_cause_inference.p1b.models import P1BSettings, P1BVariant, rank_distribution
from bug_cause_inference.p1b import policies as p1b_policies
from bug_cause_inference.p1c.labels import BUGGY_PRIMARY_BUCKETS, load_p1c_variant_labels
from bug_cause_inference.p1d.evaluation import (
    P1D1_BUCKET_IDS,
    P1D1_DIAGNOSTIC_ONLY_POLICY_IDS,
    P1D1_FORMAL_STRATEGY_IDS,
    build_p1d1_summary,
    p1d1_summary_to_json,
    p1d1_summary_to_markdown,
)


P1D2_CANDIDATE_STRATEGY_ID = p1b_policies.STATE_SEQUENCE_GUARD_POLICY_ID
P1D2_FORMAL_STRATEGY_IDS = P1D1_FORMAL_STRATEGY_IDS + (P1D2_CANDIDATE_STRATEGY_ID,)
P1D2_BUCKET_IDS = P1D1_BUCKET_IDS

P1D2_SCHEMA_VERSION = "p1d2_preregistered_policy_evaluation.v1"
P1D2_ANALYSIS_PHASE = "p1d2_preregistered_policy_evaluation"
P1D2_GAME_ID = "p1d2_g0_default_execution_grounded_state_sequence_guard_v1"
P1D2_BENCHMARK_ID = "p1b_injected_bug_benchmark"
P1D2_CANDIDATE_SPECIFICATION_ID = (
    "p1d2_state_sequence_guard_preregistered_2026-07-11"
)

_P1D1_JSON_SHA256 = "d1e86525240485b615f61b6261ea239a57b7a7148bdee4a5857452cc84169bac"
_P1D1_MARKDOWN_SHA256 = "9611e6cd8d3086a0b498a89278695f75c07ccdc9f840b6b3d00b14b0234f1dad"
_P1D1_SCHEMA_VERSION = "p1d1_finite_game_report.v1"
_P1D1_ANALYSIS_PHASE = "p1d1_finite_game_report"
_P1D1_GAME_ID = "p1d0_g0_default_execution_grounded_v1"
_BASELINE_SECURITY_LOSS = Fraction(1, 1)
_EXPECTED_BASELINE_ROWS = {
    policy: (Fraction(0), Fraction(3, 4), Fraction(1), Fraction(1), Fraction(1, 2))
    for policy in P1D1_FORMAL_STRATEGY_IDS[:4]
}
_EXPECTED_BASELINE_ROWS.update(
    {
        policy: (Fraction(3, 4), Fraction(0), Fraction(3, 4), Fraction(1), Fraction(1, 2))
        for policy in P1D1_FORMAL_STRATEGY_IDS[4:]
    }
)

_EXPECTED_ACTION_SPECS = (
    ("run_smoke_tests", 1, "test_failure", ("specification_mismatch", "missing_null_handling"), 0.45, 0.25),
    ("run_boundary_tests", 2, "boundary_counterexample", ("boundary_condition",), 0.70, 0.45),
    ("run_null_missing_tests", 2, "exception_trace", ("missing_null_handling",), 0.70, 0.55),
    ("run_config_matrix_tests", 3, "config_counterexample", ("configuration_environment",), 0.70, 0.45),
    ("run_state_sequence_tests", 4, "state_sequence_counterexample", ("state_order_dependence",), 0.75, 0.55),
    ("run_property_search", 5, "property_counterexample", ("boundary_condition", "state_order_dependence", "specification_mismatch"), 0.65, 0.35),
    ("inspect_traceback", 1, "exception_trace", ("missing_null_handling", "configuration_environment"), 0.30, 0.70),
    ("inspect_coverage_spectrum", 3, "coverage_suspicious_location", (), 0.15, 0.85),
    ("inspect_recent_diff", 2, "recent_diff_signal", ("configuration_environment", "state_order_dependence", "boundary_condition"), 0.20, 0.55),
    ("inspect_spec_clause", 2, "spec_clause_mismatch", ("specification_mismatch", "boundary_condition", "configuration_environment"), 0.45, 0.50),
)

_SECONDARY_METRIC_IDS = (
    "cost_to_first_failure",
    "location_top3_loss",
    "cause_top1_loss",
    "fix_intent_top1_loss",
    "wrong_cause_high_confidence_rate",
    "mean_investigation_cost",
)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _fraction_from_cell(cell: dict[str, Any]) -> Fraction:
    return Fraction(
        cell["variant_denominator"] - cell["discovered_numerator"],
        cell["variant_denominator"],
    )


def _action_specifications() -> list[dict[str, Any]]:
    specs = action_specs_to_dict()
    return [
        {
            "action_id": action_id,
            "cost": specs[action_id]["cost"],
            "observation_type": specs[action_id]["observation_type"],
            "strong_causes": list(specs[action_id]["strong_causes"]),
            "discovery_power": specs[action_id]["discovery_power"],
            "location_power": specs[action_id]["location_power"],
        }
        for action_id in P1B_ACTION_SPECS
    ]


def _validate_candidate_contract() -> dict[str, Any]:
    observed_specs = tuple(
        (
            action_id,
            spec.cost,
            spec.observation_type,
            spec.strong_causes,
            spec.discovery_power,
            spec.location_power,
        )
        for action_id, spec in P1B_ACTION_SPECS.items()
    )
    history_fields = tuple(field.name for field in fields(p1b_policies._StateSequenceGuardHistory))
    expected_history_fields = (
        "bug_presence_posterior",
        "cause_posterior",
        "location_posterior",
        "fix_intent_posterior",
        "executed_action_ids",
        "cumulative_cost",
        "current_step",
        "bug_detected",
    )
    selector_parameters = tuple(
        inspect.signature(p1b_policies._choose_state_sequence_guard).parameters
    )
    settings = P1BSettings()
    checks = {
        "action_specifications_exact": observed_specs == _EXPECTED_ACTION_SPECS,
        "target_action_present": "run_state_sequence_tests" in P1B_ACTION_SPECS,
        "target_action_cost_is_reserve": P1B_ACTION_SPECS.get(
            "run_state_sequence_tests"
        ).cost
        == 4
        if "run_state_sequence_tests" in P1B_ACTION_SPECS
        else False,
        "candidate_absent_from_p1b_policies": P1D2_CANDIDATE_STRATEGY_ID
        not in p1b_policies.P1B_POLICIES,
        "p1b_primary_policy_unchanged": p1b_policies.P1B_PRIMARY_POLICY
        == "expected_utility_per_cost",
        "selector_interface_exact": selector_parameters == ("history", "remaining_budget"),
        "policy_visible_projection_exact": history_fields == expected_history_fields,
        "execution_context_excluded": "execution_context" not in history_fields,
        "fixed_settings_exact": (
            settings.budget_limit,
            settings.max_steps,
            settings.failure_cost,
            settings.bug_presence_threshold,
            settings.no_bug_probability_threshold,
            settings.location_top1_threshold,
            settings.cause_top1_threshold,
            settings.min_expected_utility_per_cost,
            settings.rng_seed,
        )
        == (12, 6, 14, 0.75, 0.80, 0.50, 0.60, 0.03, 0),
    }
    return {
        "status": "valid" if all(checks.values()) else "invalid",
        "checks": checks,
        "hidden_information_policy_input": False if all(checks.values()) else None,
    }


def validate_p1d1_baseline(summary: dict[str, Any]) -> dict[str, Any]:
    """Validate the accepted P1d1 identity, hashes, rows, support, and solution."""

    try:
        observed_json_hash: str | None = _sha256(p1d1_summary_to_json(summary))
    except (KeyError, TypeError, ValueError):
        observed_json_hash = None
    try:
        observed_markdown_hash: str | None = _sha256(
            p1d1_summary_to_markdown(summary)
        )
    except (KeyError, TypeError, ValueError):
        observed_markdown_hash = None
    checks: dict[str, bool] = {
        "schema_version": summary.get("schema_version") == _P1D1_SCHEMA_VERSION,
        "analysis_phase": summary.get("analysis_phase") == _P1D1_ANALYSIS_PHASE,
        "game_id": summary.get("game_id") == _P1D1_GAME_ID,
        "json_serializer_hash": observed_json_hash == _P1D1_JSON_SHA256,
        "markdown_serializer_hash": observed_markdown_hash == _P1D1_MARKDOWN_SHA256,
        "formal_strategy_ids": tuple(summary.get("formal_strategy_ids", ()))
        == P1D1_FORMAL_STRATEGY_IDS,
        "bucket_ids": tuple(summary.get("bucket_ids", ())) == P1D1_BUCKET_IDS,
    }
    matrix = summary.get("g0_discovery_loss_matrix", {}).get("cells_by_policy", {})
    dataset = summary.get("dataset_summary", {})
    membership = dataset.get("bucket_membership", {})
    rows_exact = True
    support_exact = True
    for policy in P1D1_FORMAL_STRATEGY_IDS:
        cells = matrix.get(policy, {})
        observed_row: list[Fraction] = []
        for bucket in P1D1_BUCKET_IDS:
            cell = cells.get(bucket)
            if not isinstance(cell, dict):
                rows_exact = False
                support_exact = False
                continue
            try:
                observed_row.append(_fraction_from_cell(cell))
            except (KeyError, TypeError, ZeroDivisionError):
                rows_exact = False
            expected_support = membership.get(bucket)
            if (
                cell.get("variant_denominator") != 4
                or cell.get("diagnostic_variant_ids") != expected_support
                or sorted(
                    cell.get("discovered_variant_ids", [])
                    + cell.get("missed_variant_ids", [])
                )
                != sorted(expected_support or [])
            ):
                support_exact = False
        if tuple(observed_row) != _EXPECTED_BASELINE_ROWS[policy]:
            rows_exact = False
    solution = summary.get("restricted_pure_solution", {})
    checks.update(
        {
            "accepted_primary_rows": rows_exact,
            "uniform_four_variant_support": support_exact,
            "restricted_pure_security_loss": solution.get(
                "restricted_pure_security_loss"
            )
            == 1.0,
            "restricted_pure_six_policy_tie": tuple(
                solution.get("restricted_pure_security_policies", ())
            )
            == P1D1_FORMAL_STRATEGY_IDS,
        }
    )
    return {
        "status": "valid" if all(checks.values()) else "invalid",
        "checks": checks,
        "accepted_hashes": {
            "json_sha256": _P1D1_JSON_SHA256,
            "markdown_sha256": _P1D1_MARKDOWN_SHA256,
        },
        "observed_hashes": {
            "json_sha256": observed_json_hash,
            "markdown_sha256": observed_markdown_hash,
        },
        "candidate_interpretation_permitted": all(checks.values()),
    }


def _rank_position(distribution: dict[str, float], target: str | None) -> int | None:
    if target is None:
        return None
    ranked = [label for label, _ in rank_distribution(distribution)]
    return ranked.index(target) + 1 if target in ranked else None


def _candidate_variant_outcome(
    variant: P1BVariant,
    primary_bucket: str,
    settings: P1BSettings,
) -> dict[str, Any]:
    result = p1b_policies.run_p1b_investigation(
        variant,
        policy=P1D2_CANDIDATE_STRATEGY_ID,
        settings=settings,
        observation_mode="execution_grounded",
    )
    base: dict[str, Any] = {
        "variant_id": variant.variant_id,
        "policy": P1D2_CANDIDATE_STRATEGY_ID,
        "primary_bucket": primary_bucket,
        "is_buggy": variant.is_buggy,
        "stop_reason": result.stop_reason,
        "bug_presence_posterior": round(result.bug_presence_posterior, 6),
        "executed_action_ids": list(result.executed_actions),
    }
    if not variant.is_buggy:
        base.update(
            {
                "false_positive": result.stop_reason == "bug_confidence_threshold"
                or result.bug_presence_posterior >= settings.bug_presence_threshold,
                "clean_no_bug_stop": result.stop_reason
                == "no_bug_probability_threshold",
                "clean_investigation_cost": result.cumulative_cost,
            }
        )
        return base

    location_rank = _rank_position(result.location_posterior, variant.target_location)
    cause_rank = [label for label, _ in rank_distribution(result.cause_posterior)]
    fix_rank = [label for label, _ in rank_distribution(result.fix_intent_posterior)]
    cause_top = rank_distribution(result.cause_posterior)[0]
    base.update(
        {
            "discovered_within_budget": result.bug_detected
            and result.cumulative_cost <= settings.budget_limit,
            "first_failure_cost_penalized": result.first_failure_cost
            if result.first_failure_cost is not None
            else settings.failure_cost,
            "location_top3_hit": location_rank is not None and location_rank <= 3,
            "cause_top1_hit": variant.true_cause_category in cause_rank[:1],
            "fix_intent_top1_hit": variant.fix_intent_category in fix_rank[:1],
            "wrong_cause_high_confidence": cause_top[1]
            >= settings.cause_top1_threshold
            and cause_top[0] != variant.true_cause_category,
            "investigation_cost": result.cumulative_cost,
        }
    )
    return base


def _run_candidate_once() -> list[dict[str, Any]]:
    variants = load_p1b_variants()
    labels = load_p1c_variant_labels(variants)
    settings = P1BSettings()
    return [
        _candidate_variant_outcome(
            variant,
            labels[variant.variant_id].primary_bucket,
            settings,
        )
        for variant in variants
    ]


def _validate_candidate_outcomes(
    outcomes: list[dict[str, Any]],
    dataset: dict[str, Any],
) -> dict[str, Any]:
    expected_ids = dataset["all_variant_ids"]
    observed_ids = [outcome.get("variant_id") for outcome in outcomes]
    by_id = {outcome.get("variant_id"): outcome for outcome in outcomes}
    support_exact = observed_ids == expected_ids and len(by_id) == len(expected_ids)
    required_fields = True
    for bucket, variant_ids in dataset["bucket_membership"].items():
        is_buggy = bucket != "clean_false_positive"
        for variant_id in variant_ids:
            outcome = by_id.get(variant_id, {})
            base_fields = {
                "variant_id",
                "policy",
                "primary_bucket",
                "is_buggy",
                "stop_reason",
                "bug_presence_posterior",
                "executed_action_ids",
            }
            metric_fields = (
                {
                    "discovered_within_budget",
                    "first_failure_cost_penalized",
                    "location_top3_hit",
                    "cause_top1_hit",
                    "fix_intent_top1_hit",
                    "wrong_cause_high_confidence",
                    "investigation_cost",
                }
                if is_buggy
                else {
                    "false_positive",
                    "clean_no_bug_stop",
                    "clean_investigation_cost",
                }
            )
            if (
                not base_fields | metric_fields <= set(outcome)
                or outcome.get("primary_bucket") != bucket
                or outcome.get("is_buggy") is not is_buggy
                or outcome.get("policy") != P1D2_CANDIDATE_STRATEGY_ID
                or len(outcome.get("executed_action_ids", []))
                != len(set(outcome.get("executed_action_ids", [])))
            ):
                required_fields = False
    checks = {
        "stable_exact_25_variant_support": support_exact,
        "required_metric_fields_and_labels": required_fields,
    }
    return {"status": "valid" if all(checks.values()) else "invalid", "checks": checks}


def _candidate_bucket_metrics(
    outcomes: list[dict[str, Any]],
    dataset: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    by_id = {outcome["variant_id"]: outcome for outcome in outcomes}
    metrics: dict[str, dict[str, Any]] = {}
    for bucket, variant_ids in dataset["bucket_membership"].items():
        rows = [by_id[variant_id] for variant_id in variant_ids]
        if bucket == "clean_false_positive":
            false_positive_ids = [
                row["variant_id"] for row in rows if row["false_positive"]
            ]
            no_bug_count = sum(1 for row in rows if row["clean_no_bug_stop"])
            metrics[bucket] = {
                "false_positive_numerator": len(false_positive_ids),
                "clean_variant_denominator": len(rows),
                "clean_false_positive_rate": len(false_positive_ids) / len(rows),
                "clean_mean_investigation_cost": round(
                    mean(row["clean_investigation_cost"] for row in rows), 6
                ),
                "clean_no_bug_stop_rate": no_bug_count / len(rows),
                "false_positive_clean_variant_ids": false_positive_ids,
            }
            if not false_positive_ids:
                metrics[bucket]["note"] = (
                    "Clean false positives were not triggered in the current five clean variants."
                )
            continue

        discovered = [
            row["variant_id"] for row in rows if row["discovered_within_budget"]
        ]
        denominator = len(rows)
        numerator = len(discovered)
        metrics[bucket] = {
            "discovered_numerator": numerator,
            "variant_denominator": denominator,
            "discovery_rate": numerator / denominator,
            "discovery_loss": (denominator - numerator) / denominator,
            "diagnostic_variant_ids": list(variant_ids),
            "discovered_variant_ids": discovered,
            "missed_variant_ids": [
                variant_id for variant_id in variant_ids if variant_id not in discovered
            ],
            "cost_to_first_failure": round(
                mean(row["first_failure_cost_penalized"] for row in rows), 6
            ),
            "location_top3_loss": round(
                1 - sum(1 for row in rows if row["location_top3_hit"]) / denominator,
                6,
            ),
            "cause_top1_loss": round(
                1 - sum(1 for row in rows if row["cause_top1_hit"]) / denominator,
                6,
            ),
            "fix_intent_top1_loss": round(
                1 - sum(1 for row in rows if row["fix_intent_top1_hit"]) / denominator,
                6,
            ),
            "wrong_cause_high_confidence_rate": round(
                sum(1 for row in rows if row["wrong_cause_high_confidence"])
                / denominator,
                6,
            ),
            "mean_investigation_cost": round(
                mean(row["investigation_cost"] for row in rows), 6
            ),
        }
    return metrics


def classify_p1d2_outcome(
    *,
    baseline_valid: bool,
    contract_valid: bool,
    candidate_outcomes_valid: bool,
    candidate_worst_loss: Fraction | None,
) -> tuple[str, str]:
    """Return hypothesis and software statuses from preregistered criteria."""

    if (
        not baseline_valid
        or not contract_valid
        or not candidate_outcomes_valid
        or candidate_worst_loss is None
    ):
        return "invalid_inconclusive", "rejected"
    hypothesis = (
        "supported"
        if candidate_worst_loss < _BASELINE_SECURITY_LOSS
        else "not_supported"
    )
    return hypothesis, "accepted"


def _candidate_mapping_contract() -> dict[str, Any]:
    return {
        "policy_visible_history_fields": [
            "executed_action_ids",
            "cumulative_cost",
            "remaining_budget",
            "current_step",
            "bug_detected",
            "bug_presence_posterior",
            "cause_posterior",
            "location_posterior",
            "fix_intent_posterior",
            "stop_state",
        ],
        "hidden_information_excluded": [
            "bucket_id",
            "variant_id",
            "clean_or_buggy_ground_truth",
            "true_cause_location_or_fix_intent",
            "discovery_action_metadata",
            "difficulty_or_stress_labels",
            "report_only_observations_or_diff_fields",
            "post_run_metrics_or_matrix_cells",
            "execution_context",
        ],
        "target_action_id": "run_state_sequence_tests",
        "reserve_amount": 4,
        "fixed_max_steps": 6,
        "common_stop_precedence": [
            "no_bug_probability_threshold",
            "bug_confidence_threshold",
            "budget_limit",
            "max_steps",
            "low_expected_utility",
            "no_available_actions",
        ],
        "low_expected_utility_scope": "all_feasible_actions_before_reserve_filtering",
        "reserve_activation": (
            "not bug_detected and target not executed and target is feasible"
        ),
        "reserve_preserving_non_target": (
            "feasible non-target action cost <= remaining_budget - 4"
        ),
        "forced_target": (
            "reserve-preserving set is empty or current_step >= max_steps - 1"
        ),
        "active_non_forced_selection": (
            "first existing-score-ranked action in reserve-preserving set union target"
        ),
        "release_and_fallback": (
            "when reserve is inactive, return first action in existing score order"
        ),
        "score_order": (
            "ascending lexicographic (-round(expected_utility/action_cost, 6), action_cost, action_id)"
        ),
        "score_components": {
            "normalized_entropy": (
                "0 for an empty or single-label distribution; otherwise entropy(d) / log2(number_of_labels)"
            ),
            "cause_relevance": (
                "sum cause posterior over strong causes; 0.25 when strong_causes is empty"
            ),
            "discovery_utility": (
                "discovery_power * (1 - bug_presence_posterior), multiplied by 0.35 after bug detection"
            ),
            "cause_utility": "normalized cause entropy * cause relevance",
            "location_utility": (
                "normalized location entropy * location_power, multiplied by 1.25 after bug detection"
            ),
            "fix_utility": "normalized fix-intent entropy * 0.20",
            "expected_utility": (
                "discovery_utility + cause_utility + location_utility + fix_utility"
            ),
        },
        "post_result_tuning_allowed": False,
    }


def _fixed_settings() -> dict[str, Any]:
    settings = P1BSettings()
    return {
        "budget_limit": settings.budget_limit,
        "max_steps": settings.max_steps,
        "failure_cost": settings.failure_cost,
        "bug_presence_threshold": settings.bug_presence_threshold,
        "no_bug_probability_threshold": settings.no_bug_probability_threshold,
        "location_top1_threshold": settings.location_top1_threshold,
        "cause_top1_threshold": settings.cause_top1_threshold,
        "min_expected_utility_per_cost": settings.min_expected_utility_per_cost,
        "rng_seed": settings.rng_seed,
    }


def _base_report_fields(
    baseline: dict[str, Any],
    baseline_validation: dict[str, Any],
    contract_validation: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": P1D2_SCHEMA_VERSION,
        "analysis_phase": P1D2_ANALYSIS_PHASE,
        "game_id": P1D2_GAME_ID,
        "benchmark_id": P1D2_BENCHMARK_ID,
        "candidate_specification_id": P1D2_CANDIDATE_SPECIFICATION_ID,
        "report_role": "preregistered_candidate_headline_primary",
        "observation_mode": "execution_grounded",
        "dataset_summary": deepcopy(baseline.get("dataset_summary", {})),
        "fixed_settings": _fixed_settings(),
        "action_specifications": _action_specifications(),
        "baseline_strategy_ids": list(P1D1_FORMAL_STRATEGY_IDS),
        "candidate_strategy_id": P1D2_CANDIDATE_STRATEGY_ID,
        "formal_strategy_ids": list(P1D2_FORMAL_STRATEGY_IDS),
        "diagnostic_only_policy_ids": list(P1D1_DIAGNOSTIC_ONLY_POLICY_IDS),
        "bucket_ids": list(P1D2_BUCKET_IDS),
        "candidate_mapping_contract": _candidate_mapping_contract(),
        "loss_definition": {
            "metric_id": "discovery_loss",
            "direction": "lower_is_better",
            "formula": "1 - discovered_variant_count / 4",
            "formal_primary_and_solution_matrix_only": True,
            "raw_variant_role": "support_and_diagnostic_evidence_only",
        },
        "reference_distribution": {
            "distribution_id": "q0_uniform_over_buggy_buckets",
            "bucket_probabilities": {
                bucket: 1.0 / len(P1D2_BUCKET_IDS) for bucket in P1D2_BUCKET_IDS
            },
            "used_as_hypothesis_criterion": False,
        },
        "baseline_validation": {
            **baseline_validation,
            "candidate_contract_validation": contract_validation,
        },
        "mixed_solution": {
            "computed": False,
            "reason": "mixed minimax solver is outside the P1d2 minimum study",
        },
        "diagnostic_reports": {
            "random_action": {
                "computed": False,
                "role": "diagnostic_only_not_a_formal_row",
            },
            "metadata_synth": {
                "computed": False,
                "role": "diagnostic_only_not_headline",
            },
        },
        "non_claims": [
            "P1d2 does not claim unseen-variant generalization.",
            "P1d2 does not claim production or real-world debugging improvement.",
            "P1d2 does not causally prove that budget reservation is generally effective.",
            "P1d2 does not claim general minimax optimality or a general Nash equilibrium.",
            "P1d2 does not claim regret optimality.",
            "P1d2 does not claim robustness beyond the fixed 20 buggy and 5 clean variants.",
            "P1d2 does not claim statistical significance without a separately reviewed uncertainty design.",
            "P1d2 does not claim automated repair or patch correctness.",
        ],
        "notes": [
            "P1a is a Bayesian active bug-cause investigation prototype for synthetic observed-bug cases.",
            "P1b is a small injected checkout/pricing benchmark scaffold with 20 buggy variants and 5 clean variants.",
            "P1b location metrics are function-level only, and its real-diff artifacts are not real repository histories.",
            "P1c, P1d1, and P1d2 are analysis-only work over the fixed scaffold.",
            "state_sequence_guard was designed after observing the P1d1 weakness and is evaluated on the same scaffold; the evidence is in-sample and exploratory.",
            "A faithful negative result is an accepted research artifact when the preregistered software contract is satisfied.",
        ],
    }


def _invalid_summary(
    baseline: dict[str, Any],
    baseline_validation: dict[str, Any],
    contract_validation: dict[str, Any],
) -> dict[str, Any]:
    summary = _base_report_fields(baseline, baseline_validation, contract_validation)
    summary.update(
        {
            "g0_discovery_loss_matrix": {
                "status": "not_computed",
                "reason": "preflight validation failed before candidate execution",
                "row_policy_ids": list(P1D2_FORMAL_STRATEGY_IDS),
                "column_bucket_ids": list(P1D2_BUCKET_IDS),
                "cells_by_policy": {},
            },
            "restricted_pure_comparison": {
                "computed": False,
                "baseline_restricted_pure_security_loss": 1.0,
                "reason": "candidate interpretation is prohibited after preflight failure",
            },
            "hypothesis_outcome": {
                "status": "invalid_inconclusive",
                "criterion": "candidate_worst_bucket_discovery_loss < 1.0",
                "reason": "baseline or candidate-contract preflight failed",
            },
            "clean_false_positive_stress": {
                "computed": False,
                "formal_game_membership": "excluded",
            },
            "secondary_metric_matrices": {},
            "software_acceptance": {
                "status": "rejected",
                "faithful_negative_result_is_acceptable": True,
                "reason": "preflight contract failure",
            },
        }
    )
    return summary


def _expanded_solution(matrix: dict[str, Any]) -> dict[str, Any]:
    by_policy: dict[str, dict[str, Any]] = {}
    worst_by_policy: dict[str, Fraction] = {}
    for policy in P1D2_FORMAL_STRATEGY_IDS:
        cells = matrix["cells_by_policy"][policy]
        losses = {
            bucket: _fraction_from_cell(cells[bucket]) for bucket in P1D2_BUCKET_IDS
        }
        worst = max(losses.values())
        average = sum(losses.values(), start=Fraction()) / len(P1D2_BUCKET_IDS)
        worst_by_policy[policy] = worst
        by_policy[policy] = {
            "worst_bucket_discovery_loss": float(worst),
            "worst_bucket_ids": [
                bucket for bucket in P1D2_BUCKET_IDS if losses[bucket] == worst
            ],
            "reference_average_loss": float(average),
            "average_to_worst_gap": float(worst - average),
        }
    security_loss = min(worst_by_policy.values())
    candidate_worst = worst_by_policy[P1D2_CANDIDATE_STRATEGY_ID]
    return {
        "baseline_restricted_pure_security_loss": 1.0,
        "candidate_worst_bucket_discovery_loss": float(candidate_worst),
        "candidate_worst_bucket_ids": by_policy[P1D2_CANDIDATE_STRATEGY_ID][
            "worst_bucket_ids"
        ],
        "p1d2_restricted_pure_security_loss": float(security_loss),
        "p1d2_restricted_pure_security_policies": [
            policy
            for policy in P1D2_FORMAL_STRATEGY_IDS
            if worst_by_policy[policy] == security_loss
        ],
        "by_policy": by_policy,
        "tie_rule": "exact rational counts before display rounding; stable policy and bucket order",
        "hypothesis_criterion": "candidate_worst_bucket_discovery_loss < 1.0",
        "average_is_descriptive_only": True,
        "_candidate_worst_fraction": candidate_worst,
    }


def build_p1d2_summary(
    p1d1_summary: dict[str, Any] | None = None,
    candidate_outcomes: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build the separate P1d2 report after fail-closed baseline preflight.

    Supplying candidate_outcomes is intended for deterministic tests and
    read-only reconstruction. The official CLI omits it and executes the fixed
    candidate exactly once after baseline and contract validation succeed.
    """

    baseline = p1d1_summary if p1d1_summary is not None else build_p1d1_summary()
    baseline_validation = validate_p1d1_baseline(baseline)
    contract_validation = _validate_candidate_contract()
    if (
        baseline_validation["status"] != "valid"
        or contract_validation["status"] != "valid"
    ):
        return _invalid_summary(baseline, baseline_validation, contract_validation)

    outcomes = candidate_outcomes if candidate_outcomes is not None else _run_candidate_once()
    dataset = baseline["dataset_summary"]
    outcome_validation = _validate_candidate_outcomes(outcomes, dataset)
    if outcome_validation["status"] != "valid":
        invalid_contract = deepcopy(contract_validation)
        invalid_contract["status"] = "invalid"
        invalid_contract["candidate_outcome_validation"] = outcome_validation
        return _invalid_summary(baseline, baseline_validation, invalid_contract)

    candidate_metrics = _candidate_bucket_metrics(outcomes, dataset)
    matrix = deepcopy(baseline["g0_discovery_loss_matrix"])
    matrix["row_policy_ids"] = list(P1D2_FORMAL_STRATEGY_IDS)
    matrix["cells_by_policy"][P1D2_CANDIDATE_STRATEGY_ID] = {
        bucket: {
            "policy_id": P1D2_CANDIDATE_STRATEGY_ID,
            "bucket_id": bucket,
            **{
                key: candidate_metrics[bucket][key]
                for key in (
                    "discovered_numerator",
                    "variant_denominator",
                    "discovery_rate",
                    "discovery_loss",
                    "diagnostic_variant_ids",
                    "discovered_variant_ids",
                    "missed_variant_ids",
                )
            },
        }
        for bucket in P1D2_BUCKET_IDS
    }
    matrix["formal_cell_count"] = len(P1D2_FORMAL_STRATEGY_IDS) * len(
        P1D2_BUCKET_IDS
    )

    comparison = _expanded_solution(matrix)
    candidate_worst = comparison.pop("_candidate_worst_fraction")
    hypothesis_status, software_status = classify_p1d2_outcome(
        baseline_valid=True,
        contract_valid=True,
        candidate_outcomes_valid=True,
        candidate_worst_loss=candidate_worst,
    )

    clean = deepcopy(baseline["clean_false_positive_stress"])
    clean["by_policy"][P1D2_CANDIDATE_STRATEGY_ID] = candidate_metrics[
        "clean_false_positive"
    ]
    clean["formal_strategy_ids"] = list(P1D2_FORMAL_STRATEGY_IDS)

    secondary = deepcopy(baseline["secondary_metric_matrices"])
    for metric_id in _SECONDARY_METRIC_IDS:
        secondary[metric_id]["row_policy_ids"] = list(P1D2_FORMAL_STRATEGY_IDS)
        secondary[metric_id]["values_by_policy"][P1D2_CANDIDATE_STRATEGY_ID] = {
            bucket: candidate_metrics[bucket][metric_id]
            for bucket in P1D2_BUCKET_IDS
        }

    summary = _base_report_fields(baseline, baseline_validation, contract_validation)
    summary["baseline_validation"].update(
        {
            "candidate_outcome_validation": outcome_validation,
            "candidate_evaluated_only_after_preflight": True,
        }
    )
    summary.update(
        {
            "g0_discovery_loss_matrix": matrix,
            "restricted_pure_comparison": comparison,
            "hypothesis_outcome": {
                "status": hypothesis_status,
                "criterion": "candidate_worst_bucket_discovery_loss < 1.0",
                "baseline_loss": 1.0,
                "candidate_worst_bucket_discovery_loss": float(candidate_worst),
                "decision_uses_exact_values_before_rounding": True,
                "interpretation": (
                    "This fixed candidate strictly reduced empirical worst-bucket discovery loss on the fixed G0 scaffold."
                    if hypothesis_status == "supported"
                    else "The valid fixed candidate did not strictly reduce empirical worst-bucket discovery loss below 1.0."
                ),
            },
            "clean_false_positive_stress": clean,
            "secondary_metric_matrices": secondary,
            "software_acceptance": {
                "status": software_status,
                "faithful_negative_result_is_acceptable": True,
                "research_outcome_independent": True,
                "reason": (
                    "The preregistered mapping, baseline invariance, fixed support, and evaluation contract were validated."
                ),
            },
        }
    )
    return summary


def p1d2_summary_to_json(summary: dict[str, Any]) -> str:
    """Serialize a P1d2 summary as stable, human-readable JSON."""

    return json.dumps(summary, indent=2) + "\n"


def _format_number(value: Any) -> str:
    return f"{value:.6f}" if isinstance(value, float) else str(value)


def _format_ids(values: list[str] | tuple[str, ...]) -> str:
    return ", ".join(values) if values else "none"


def p1d2_summary_to_markdown(summary: dict[str, Any]) -> str:
    """Serialize a P1d2 summary as an auditable Markdown report."""

    validation = summary["baseline_validation"]
    hypothesis = summary["hypothesis_outcome"]
    software = summary["software_acceptance"]
    lines = [
        "# P1d2 Preregistered State-Sequence-Guard Evaluation",
        "",
        "P1d2 is an analysis-only, in-sample exploratory evaluation over the fixed P1b scaffold.",
        "The single candidate was fixed before execution; no post-result tuning or winner selection is permitted.",
        "",
        "## Report IDs And Role",
        "",
        f"- schema_version: {summary['schema_version']}",
        f"- analysis_phase: {summary['analysis_phase']}",
        f"- game_id: {summary['game_id']}",
        f"- benchmark_id: {summary['benchmark_id']}",
        f"- candidate_specification_id: {summary['candidate_specification_id']}",
        f"- observation_mode: {summary['observation_mode']}",
        "",
        "## Preregistered Mapping",
        "",
        f"- candidate: {summary['candidate_strategy_id']}",
        "- target: run_state_sequence_tests; reserve: 4; max_steps: 6.",
        "- Common stop precedes selection; low expected utility uses all feasible actions.",
        "- Reserve is active only before bug detection while the unexecuted target is feasible.",
        "- A non-target action must leave at least 4 budget; the target is forced when no such action exists or current_step >= max_steps - 1.",
        "- Otherwise choose the first action in the existing rounded-score, cost, action-ID order from the target plus reserve-preserving actions.",
        "- When the reserve is inactive, use the first feasible action in the same existing score order.",
        "- Bucket, variant, ground truth, report-only fields, post-run metrics, and execution context are excluded from policy input.",
        "",
        "## Baseline And Contract Preflight",
        "",
        f"- baseline validation: {validation['status']}",
        f"- P1d1 JSON SHA-256: {validation['observed_hashes']['json_sha256']}",
        f"- P1d1 Markdown SHA-256: {validation['observed_hashes']['markdown_sha256']}",
        f"- candidate contract validation: {validation['candidate_contract_validation']['status']}",
        "",
    ]
    if summary["g0_discovery_loss_matrix"].get("status") == "not_computed":
        lines.extend(
            [
                "## Invalid/Inconclusive Result",
                "",
                summary["g0_discovery_loss_matrix"]["reason"],
                "",
                f"- hypothesis_outcome: {hypothesis['status']}",
                f"- software_acceptance: {software['status']}",
            ]
        )
    else:
        dataset = summary["dataset_summary"]
        matrix = summary["g0_discovery_loss_matrix"]
        comparison = summary["restricted_pure_comparison"]
        lines.extend(
            [
                "## Dataset And Stable Support",
                "",
                f"- variants: {dataset['total_variant_count']} total; {dataset['buggy_variant_count']} buggy; {dataset['clean_variant_count']} clean.",
                f"- formal policies: {_format_ids(summary['formal_strategy_ids'])}",
                f"- formal buggy buckets: {_format_ids(summary['bucket_ids'])}",
                "",
                "## 7 x 5 G0 Discovery-Loss Matrix",
                "",
                "`discovery_loss = 1 - discovered_variant_count / 4`; lower is better.",
                "",
                "| policy | " + " | ".join(summary["bucket_ids"]) + " |",
                "|---|" + "---:|" * len(summary["bucket_ids"]),
            ]
        )
        for policy in summary["formal_strategy_ids"]:
            values = [
                _format_number(matrix["cells_by_policy"][policy][bucket]["discovery_loss"])
                for bucket in summary["bucket_ids"]
            ]
            lines.append(f"| {policy} | " + " | ".join(values) + " |")
        lines.extend(
            [
                "",
                "### Exact Cell Evidence",
                "",
                "| policy | bucket | discovered/support | support IDs | discovered IDs | missed IDs |",
                "|---|---|---:|---|---|---|",
            ]
        )
        for policy in summary["formal_strategy_ids"]:
            for bucket in summary["bucket_ids"]:
                cell = matrix["cells_by_policy"][policy][bucket]
                lines.append(
                    f"| {policy} | {bucket} | {cell['discovered_numerator']}/{cell['variant_denominator']} | "
                    f"{_format_ids(cell['diagnostic_variant_ids'])} | {_format_ids(cell['discovered_variant_ids'])} | {_format_ids(cell['missed_variant_ids'])} |"
                )
        lines.extend(
            [
                "",
                "## Restricted-Pure Comparison And Classification",
                "",
                "| policy | worst loss | tied worst buckets | q0 average | average-to-worst gap |",
                "|---|---:|---|---:|---:|",
            ]
        )
        for policy in summary["formal_strategy_ids"]:
            row = comparison["by_policy"][policy]
            lines.append(
                f"| {policy} | {_format_number(row['worst_bucket_discovery_loss'])} | "
                f"{_format_ids(row['worst_bucket_ids'])} | {_format_number(row['reference_average_loss'])} | {_format_number(row['average_to_worst_gap'])} |"
            )
        lines.extend(
            [
                "",
                f"- candidate worst-bucket discovery loss: {_format_number(comparison['candidate_worst_bucket_discovery_loss'])}",
                f"- candidate tied worst buckets: {_format_ids(comparison['candidate_worst_bucket_ids'])}",
                f"- expanded restricted-pure loss: {_format_number(comparison['p1d2_restricted_pure_security_loss'])}",
                f"- expanded tied policies: {_format_ids(comparison['p1d2_restricted_pure_security_policies'])}",
                f"- hypothesis_outcome: {hypothesis['status']}",
                f"- software_acceptance: {software['status']}",
                "- q0 averages are descriptive and do not replace the strict hypothesis criterion.",
                "",
                "## Clean False-Positive Stress",
                "",
                "Clean stress is outside the formal buggy matrix and restricted-pure result.",
                "",
                "| policy | false positives/support | rate | mean cost | no-bug stop rate | false-positive IDs |",
                "|---|---:|---:|---:|---:|---|",
            ]
        )
        clean = summary["clean_false_positive_stress"]
        for policy in summary["formal_strategy_ids"]:
            row = clean["by_policy"][policy]
            lines.append(
                f"| {policy} | {row['false_positive_numerator']}/{row['clean_variant_denominator']} | "
                f"{_format_number(row['clean_false_positive_rate'])} | {_format_number(row['clean_mean_investigation_cost'])} | "
                f"{_format_number(row['clean_no_bug_stop_rate'])} | {_format_ids(row['false_positive_clean_variant_ids'])} |"
            )
        lines.extend(["", "## Six Separate Secondary Matrices", ""])
        for metric_id in _SECONDARY_METRIC_IDS:
            secondary = summary["secondary_metric_matrices"][metric_id]
            lines.extend(
                [
                    f"### {metric_id}",
                    "",
                    secondary["definition"],
                    "",
                    "| policy | " + " | ".join(summary["bucket_ids"]) + " |",
                    "|---|" + "---:|" * len(summary["bucket_ids"]),
                ]
            )
            for policy in summary["formal_strategy_ids"]:
                values = [
                    _format_number(secondary["values_by_policy"][policy][bucket])
                    for bucket in summary["bucket_ids"]
                ]
                lines.append(f"| {policy} | " + " | ".join(values) + " |")
            lines.append("")
        lines.extend(
            [
                "## Diagnostic And Mixed Boundaries",
                "",
                "- random_action: diagnostic-only, not computed, not a formal row.",
                "- metadata_synth: diagnostic-only, not computed, not headline.",
                "- mixed_solution.computed: false.",
                "- No secondary or clean metric enters the discovery-loss solution.",
            ]
        )
    lines.extend(["", "## Scope, Limitations, And Non-Claims", ""])
    lines.extend(f"- {note}" for note in summary["notes"])
    lines.extend(f"- {claim}" for claim in summary["non_claims"])
    return "\n".join(lines) + "\n"
