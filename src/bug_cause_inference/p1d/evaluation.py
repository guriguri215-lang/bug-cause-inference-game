"""Build the P1d1 analysis-only report from existing P1c outcomes."""

from __future__ import annotations

import json
from fractions import Fraction
from typing import Any

from bug_cause_inference.p1c.evaluation import evaluate_p1c
from bug_cause_inference.p1c.labels import BUGGY_PRIMARY_BUCKETS


P1D1_FORMAL_STRATEGY_IDS = (
    "fixed_checklist",
    "test_first",
    "coverage_first",
    "recent_diff_first",
    "cause_only_p1a_style",
    "expected_utility_per_cost",
)
P1D1_DIAGNOSTIC_ONLY_POLICY_IDS = ("random_action",)
P1D1_BUCKET_IDS = BUGGY_PRIMARY_BUCKETS
_P1D1_FIXED_BUCKET_MEMBERSHIP = {
    "boundary_precision": (
        "P1B-BUG-001",
        "P1B-BUG-002",
        "P1B-BUG-003",
        "P1B-BUG-004",
    ),
    "missing_optional_input": (
        "P1B-BUG-005",
        "P1B-BUG-006",
        "P1B-BUG-007",
        "P1B-BUG-008",
    ),
    "config_normalization": (
        "P1B-BUG-009",
        "P1B-BUG-010",
        "P1B-BUG-011",
        "P1B-BUG-012",
    ),
    "state_sequence": (
        "P1B-BUG-013",
        "P1B-BUG-014",
        "P1B-BUG-015",
        "P1B-BUG-016",
    ),
    "spec_semantics": (
        "P1B-BUG-017",
        "P1B-BUG-018",
        "P1B-BUG-019",
        "P1B-BUG-020",
    ),
    "clean_false_positive": (
        "P1B-CLEAN-021",
        "P1B-CLEAN-022",
        "P1B-CLEAN-023",
        "P1B-CLEAN-024",
        "P1B-CLEAN-025",
    ),
}
_P1D1_FIXED_VARIANT_IDS = tuple(
    variant_id
    for variant_ids in _P1D1_FIXED_BUCKET_MEMBERSHIP.values()
    for variant_id in variant_ids
)
_P1D1_FIXED_BUCKET_BY_VARIANT = {
    variant_id: bucket
    for bucket, variant_ids in _P1D1_FIXED_BUCKET_MEMBERSHIP.items()
    for variant_id in variant_ids
}
_EXPECTED_SETTINGS = {
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

_SECONDARY_METRICS: dict[str, dict[str, str]] = {
    "cost_to_first_failure": {
        "source": "bucket_cost_to_first_failure",
        "transform": "identity",
        "definition": "Mean existing penalized first-failure cost; a missed buggy variant contributes failure_cost=14.",
    },
    "location_top3_loss": {
        "source": "bucket_location_top3_accuracy",
        "transform": "one_minus",
        "definition": "1 - bucket_location_top3_accuracy.",
    },
    "cause_top1_loss": {
        "source": "bucket_cause_top1_accuracy",
        "transform": "one_minus",
        "definition": "1 - bucket_cause_top1_accuracy.",
    },
    "fix_intent_top1_loss": {
        "source": "bucket_fix_intent_top1_accuracy",
        "transform": "one_minus",
        "definition": "1 - bucket_fix_intent_top1_accuracy.",
    },
    "wrong_cause_high_confidence_rate": {
        "source": "bucket_wrong_cause_high_confidence_rate",
        "transform": "identity",
        "definition": "Existing bucket wrong-cause high-confidence rate.",
    },
    "mean_investigation_cost": {
        "source": "bucket_mean_investigation_cost",
        "transform": "identity",
        "definition": "Existing bucket mean investigation cost.",
    },
}


def _decimal(value: Fraction) -> float:
    return float(value)


def _validate_p1c_source(summary: dict[str, Any]) -> None:
    if summary.get("observation_mode") != "execution_grounded":
        raise ValueError("P1d1 requires an execution_grounded P1c source summary.")
    available_policies = set(summary.get("policies_evaluated", []))
    missing_policies = [
        policy for policy in P1D1_FORMAL_STRATEGY_IDS if policy not in available_policies
    ]
    if missing_policies:
        raise ValueError(f"P1c source summary is missing formal policies: {missing_policies}")
    dataset = summary.get("dataset", {})
    bucket_sizes = dataset.get("bucket_sizes", {})
    expected_bucket_keys = set(_P1D1_FIXED_BUCKET_MEMBERSHIP)
    observed_bucket_keys = set(bucket_sizes)
    if observed_bucket_keys != expected_bucket_keys:
        raise ValueError(
            "P1c source dataset bucket_sizes must use the fixed bucket key set; "
            f"missing={sorted(expected_bucket_keys - observed_bucket_keys)}, "
            f"extra={sorted(observed_bucket_keys - expected_bucket_keys, key=str)}"
        )
    observed_membership: dict[str, list[str]] = {}
    buckets_by_variant: dict[str, list[str]] = {}
    for bucket in _P1D1_FIXED_BUCKET_MEMBERSHIP:
        variant_ids = bucket_sizes.get(bucket, {}).get("variant_ids")
        if not isinstance(variant_ids, list):
            raise ValueError(f"P1c source dataset bucket {bucket!r} must provide variant_ids.")
        observed_membership[bucket] = variant_ids
        for variant_id in variant_ids:
            buckets_by_variant.setdefault(variant_id, []).append(bucket)

    cross_bucket_duplicates = {
        variant_id: buckets
        for variant_id, buckets in buckets_by_variant.items()
        if len(set(buckets)) > 1
    }
    if cross_bucket_duplicates:
        raise ValueError(
            "P1c source dataset membership repeats variants across buckets: "
            f"{cross_bucket_duplicates}"
        )

    observed_ids = [
        variant_id
        for bucket in _P1D1_FIXED_BUCKET_MEMBERSHIP
        for variant_id in observed_membership[bucket]
    ]
    duplicate_ids = sorted(
        variant_id for variant_id in set(observed_ids) if observed_ids.count(variant_id) > 1
    )
    expected_id_set = set(_P1D1_FIXED_VARIANT_IDS)
    observed_id_set = set(observed_ids)
    missing_ids = sorted(expected_id_set - observed_id_set)
    extra_ids = sorted(observed_id_set - expected_id_set, key=str)
    if duplicate_ids or missing_ids or extra_ids or len(observed_ids) != len(
        _P1D1_FIXED_VARIANT_IDS
    ):
        raise ValueError(
            "P1c source dataset membership must contain the fixed 25 variants exactly once; "
            f"duplicates={duplicate_ids}, missing={missing_ids}, extra={extra_ids}"
        )

    for bucket, expected_ids in _P1D1_FIXED_BUCKET_MEMBERSHIP.items():
        if observed_membership[bucket] != list(expected_ids):
            raise ValueError(
                f"P1c source dataset bucket {bucket!r} has incorrect variant membership or order."
            )

    invalid_buckets = [
        bucket
        for bucket in P1D1_BUCKET_IDS
        if bucket_sizes.get(bucket, {}).get("variant_count") != 4
    ]
    if invalid_buckets:
        raise ValueError(
            "P1d1 requires four existing variants in every buggy bucket; "
            f"invalid buckets: {invalid_buckets}"
        )
    observed_counts = (
        dataset.get("total_variants"),
        dataset.get("buggy_variants"),
        dataset.get("clean_variants"),
    )
    if observed_counts != (25, 20, 5):
        raise ValueError(
            "P1d1 requires the fixed 25-variant P1b scaffold (20 buggy, 5 clean); "
            f"observed counts: {observed_counts}"
        )
    source_settings = summary.get("settings", {})
    changed_settings = {
        key: source_settings.get(key)
        for key, expected in _EXPECTED_SETTINGS.items()
        if source_settings.get(key) != expected
    }
    if changed_settings:
        raise ValueError(f"P1d1 requires the fixed P1b settings; changed values: {changed_settings}")

    labels = summary.get("variant_labels", {})
    label_ids = set(labels)
    if label_ids != expected_id_set:
        raise ValueError(
            "P1c source variant_labels must exactly cover the fixed variants; "
            f"missing={sorted(expected_id_set - label_ids)}, "
            f"extra={sorted(label_ids - expected_id_set, key=str)}"
        )
    for variant_id in _P1D1_FIXED_VARIANT_IDS:
        label = labels[variant_id]
        if label.get("variant_id") != variant_id:
            raise ValueError(f"P1c source label key and variant_id disagree for {variant_id}.")
        expected_bucket = _P1D1_FIXED_BUCKET_BY_VARIANT[variant_id]
        if label.get("primary_bucket") != expected_bucket:
            raise ValueError(
                f"P1c source label for {variant_id} must use bucket {expected_bucket!r}."
            )

    per_variant_outcomes = summary.get("per_variant_outcomes", {})
    for policy in P1D1_FORMAL_STRATEGY_IDS:
        outcomes = per_variant_outcomes.get(policy)
        if not isinstance(outcomes, list):
            raise ValueError(f"P1c source outcomes for policy {policy!r} must be a list.")
        outcome_ids = [outcome.get("variant_id") for outcome in outcomes]
        outcome_id_set = set(outcome_ids)
        duplicate_outcome_ids = sorted(
            (variant_id for variant_id in outcome_id_set if outcome_ids.count(variant_id) > 1),
            key=str,
        )
        missing_outcome_ids = sorted(expected_id_set - outcome_id_set)
        extra_outcome_ids = sorted(outcome_id_set - expected_id_set, key=str)
        if (
            len(outcomes) != len(_P1D1_FIXED_VARIANT_IDS)
            or duplicate_outcome_ids
            or missing_outcome_ids
            or extra_outcome_ids
        ):
            raise ValueError(
                f"P1c source outcomes for policy {policy!r} must contain each fixed variant "
                f"exactly once; duplicates={duplicate_outcome_ids}, "
                f"missing={missing_outcome_ids}, extra={extra_outcome_ids}"
            )
        for outcome in outcomes:
            variant_id = outcome["variant_id"]
            expected_bucket = _P1D1_FIXED_BUCKET_BY_VARIANT[variant_id]
            if outcome.get("primary_bucket") != expected_bucket:
                raise ValueError(
                    f"P1c source outcome for {variant_id} under {policy!r} must use "
                    f"bucket {expected_bucket!r}."
                )
            expected_is_buggy = expected_bucket != "clean_false_positive"
            if outcome.get("is_buggy") is not expected_is_buggy:
                raise ValueError(
                    f"P1c source outcome for {variant_id} under {policy!r} has incorrect "
                    "is_buggy semantics."
                )

    bucket_metrics = summary.get("bucket_metrics", {})
    for policy in P1D1_FORMAL_STRATEGY_IDS:
        policy_metrics = bucket_metrics.get(policy, {})
        missing_metric_buckets = [
            bucket
            for bucket in _P1D1_FIXED_BUCKET_MEMBERSHIP
            if bucket not in policy_metrics
        ]
        if missing_metric_buckets:
            raise ValueError(
                f"P1c source bucket_metrics for policy {policy!r} are missing buckets: "
                f"{missing_metric_buckets}"
            )
        for bucket in _P1D1_FIXED_BUCKET_MEMBERSHIP:
            expected_counts = (
                (5, 0, 5) if bucket == "clean_false_positive" else (4, 4, 0)
            )
            metrics = policy_metrics[bucket]
            observed_metric_counts = (
                metrics.get("variant_count"),
                metrics.get("buggy_variant_count"),
                metrics.get("clean_variant_count"),
            )
            if observed_metric_counts != expected_counts:
                raise ValueError(
                    f"P1c source bucket_metrics for policy {policy!r}, bucket {bucket!r} "
                    f"have incorrect support counts: {observed_metric_counts}"
                )


def _dataset_summary(source: dict[str, Any]) -> dict[str, Any]:
    source_dataset = source["dataset"]
    bucket_membership = {
        bucket: list(source_dataset["bucket_sizes"][bucket]["variant_ids"])
        for bucket in (*P1D1_BUCKET_IDS, "clean_false_positive")
    }
    all_variant_ids = [
        variant_id
        for bucket in (*P1D1_BUCKET_IDS, "clean_false_positive")
        for variant_id in bucket_membership[bucket]
    ]
    return {
        "total_variant_count": source_dataset["total_variants"],
        "buggy_variant_count": source_dataset["buggy_variants"],
        "clean_variant_count": source_dataset["clean_variants"],
        "all_variant_ids": all_variant_ids,
        "bucket_membership": bucket_membership,
        "bucket_sizes": {
            bucket: len(variant_ids) for bucket, variant_ids in bucket_membership.items()
        },
        "buggy_bucket_count": len(P1D1_BUCKET_IDS),
        "uniform_variant_support_within_buggy_bucket": True,
    }


def _fixed_settings(source: dict[str, Any]) -> dict[str, Any]:
    settings = dict(source["settings"])
    settings["seed_contract"] = {
        "rng_seed": settings["rng_seed"],
        "deterministic_policy_effect": "rng_seed does not change the six formal deterministic policy mappings",
        "random_action_stable_seed": (
            "rng_seed + sum((i + 1) * ord(variant_id[i]) for i in range(len(variant_id)))"
        ),
        "random_action_status": "diagnostic_only_not_computed",
    }
    return settings


def _matrix(source: dict[str, Any], dataset: dict[str, Any]) -> dict[str, Any]:
    cells_by_policy: dict[str, dict[str, dict[str, Any]]] = {}
    for policy in P1D1_FORMAL_STRATEGY_IDS:
        outcomes_by_id = {
            outcome["variant_id"]: outcome for outcome in source["per_variant_outcomes"][policy]
        }
        policy_cells: dict[str, dict[str, Any]] = {}
        for bucket in P1D1_BUCKET_IDS:
            support = list(dataset["bucket_membership"][bucket])
            discovered = [
                variant_id
                for variant_id in support
                if outcomes_by_id[variant_id]["discovered_within_budget"]
            ]
            missed = [variant_id for variant_id in support if variant_id not in discovered]
            numerator = len(discovered)
            denominator = len(support)
            rate = Fraction(numerator, denominator)
            loss = Fraction(denominator - numerator, denominator)
            policy_cells[bucket] = {
                "policy_id": policy,
                "bucket_id": bucket,
                "discovered_numerator": numerator,
                "variant_denominator": denominator,
                "discovery_rate": _decimal(rate),
                "discovery_loss": _decimal(loss),
                "diagnostic_variant_ids": support,
                "discovered_variant_ids": discovered,
                "missed_variant_ids": missed,
            }
        cells_by_policy[policy] = policy_cells
    return {
        "direction": "lower_is_better",
        "row_policy_ids": list(P1D1_FORMAL_STRATEGY_IDS),
        "column_bucket_ids": list(P1D1_BUCKET_IDS),
        "empirical_support": "uniform over the four existing variants in each buggy bucket",
        "raw_variant_role": "support_and_diagnostic_evidence_only",
        "cells_by_policy": cells_by_policy,
    }


def _restricted_pure_solution(matrix: dict[str, Any]) -> dict[str, Any]:
    rows: dict[str, dict[str, Any]] = {}
    exact_worst_by_policy: dict[str, Fraction] = {}
    for policy in P1D1_FORMAL_STRATEGY_IDS:
        cells = matrix["cells_by_policy"][policy]
        exact_losses = {
            bucket: Fraction(
                cells[bucket]["variant_denominator"]
                - cells[bucket]["discovered_numerator"],
                cells[bucket]["variant_denominator"],
            )
            for bucket in P1D1_BUCKET_IDS
        }
        worst = max(exact_losses.values())
        reference_average = sum(exact_losses.values(), start=Fraction(0, 1)) / len(
            P1D1_BUCKET_IDS
        )
        exact_worst_by_policy[policy] = worst
        rows[policy] = {
            "worst_bucket_loss": _decimal(worst),
            "worst_bucket_ids": [
                bucket for bucket in P1D1_BUCKET_IDS if exact_losses[bucket] == worst
            ],
            "reference_average_loss": _decimal(reference_average),
            "average_to_worst_gap": _decimal(worst - reference_average),
        }
    security_loss = min(exact_worst_by_policy.values())
    return {
        "by_policy": rows,
        "restricted_pure_security_loss": _decimal(security_loss),
        "restricted_pure_security_policies": [
            policy
            for policy in P1D1_FORMAL_STRATEGY_IDS
            if exact_worst_by_policy[policy] == security_loss
        ],
        "tie_rule": (
            "Decide ties from exact numerator/denominator values before display rounding; "
            "emit bucket and policy ties in their declared stable orders."
        ),
        "rounding_rule": (
            "Empirical cells and restricted-pure decisions use exact rational counts; "
            "JSON numbers are exact finite decimals for the current four-variant cells."
        ),
    }


def _clean_stress(source: dict[str, Any], dataset: dict[str, Any]) -> dict[str, Any]:
    clean_ids = list(dataset["bucket_membership"]["clean_false_positive"])
    rows: dict[str, dict[str, Any]] = {}
    for policy in P1D1_FORMAL_STRATEGY_IDS:
        outcomes_by_id = {
            outcome["variant_id"]: outcome for outcome in source["per_variant_outcomes"][policy]
        }
        clean_outcomes = [outcomes_by_id[variant_id] for variant_id in clean_ids]
        false_positive_ids = [
            outcome["variant_id"] for outcome in clean_outcomes if outcome["false_positive"]
        ]
        denominator = len(clean_outcomes)
        numerator = len(false_positive_ids)
        mean_cost = sum(outcome["clean_investigation_cost"] for outcome in clean_outcomes) / denominator
        no_bug_count = sum(1 for outcome in clean_outcomes if outcome["clean_no_bug_stop"])
        row: dict[str, Any] = {
            "false_positive_numerator": numerator,
            "clean_variant_denominator": denominator,
            "clean_false_positive_rate": _decimal(Fraction(numerator, denominator)),
            "clean_mean_investigation_cost": round(mean_cost, 6),
            "clean_no_bug_stop_rate": _decimal(Fraction(no_bug_count, denominator)),
            "false_positive_clean_variant_ids": false_positive_ids,
        }
        if numerator == 0:
            row["note"] = (
                "Clean false positives were not triggered in the current five clean variants."
            )
        rows[policy] = row
    return {
        "formal_game_membership": "excluded",
        "clean_bucket_id": "clean_false_positive",
        "clean_variant_ids": clean_ids,
        "by_policy": rows,
        "risk_note": (
            "This separate current-five-variant stress does not establish that false-positive risk is solved."
        ),
    }


def _secondary_matrices(source: dict[str, Any]) -> dict[str, Any]:
    matrices: dict[str, Any] = {}
    for metric_id, spec in _SECONDARY_METRICS.items():
        values_by_policy: dict[str, dict[str, float | int]] = {}
        for policy in P1D1_FORMAL_STRATEGY_IDS:
            policy_values: dict[str, float | int] = {}
            for bucket in P1D1_BUCKET_IDS:
                value = source["bucket_metrics"][policy][bucket][spec["source"]]
                if spec["transform"] == "one_minus":
                    value = round(1.0 - value, 6)
                policy_values[bucket] = value
            values_by_policy[policy] = policy_values
        matrix: dict[str, Any] = {
            "direction": "lower_is_better",
            "definition": spec["definition"],
            "source_p1c_metric": spec["source"],
            "used_in_restricted_pure_solution": False,
            "row_policy_ids": list(P1D1_FORMAL_STRATEGY_IDS),
            "column_bucket_ids": list(P1D1_BUCKET_IDS),
            "values_by_policy": values_by_policy,
        }
        if metric_id == "cost_to_first_failure":
            matrix.update(
                {
                    "failure_cost": source["settings"]["failure_cost"],
                    "missed_buggy_variant_penalty": source["settings"]["failure_cost"],
                    "source_per_variant_field": "first_failure_cost_penalized",
                }
            )
        matrices[metric_id] = matrix
    return matrices


def build_p1d1_summary(p1c_summary: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build one P1d1 report from the existing execution-grounded P1c data path."""

    source = (
        p1c_summary
        if p1c_summary is not None
        else evaluate_p1c(
            policies=P1D1_FORMAL_STRATEGY_IDS,
            observation_mode="execution_grounded",
        )
    )
    _validate_p1c_source(source)
    dataset = _dataset_summary(source)
    matrix = _matrix(source, dataset)
    return {
        "schema_version": "p1d1_finite_game_report.v1",
        "analysis_phase": "p1d1_finite_game_report",
        "game_id": "p1d0_g0_default_execution_grounded_v1",
        "benchmark_id": "p1b_injected_bug_benchmark",
        "report_role": "headline_primary",
        "observation_mode": "execution_grounded",
        "dataset_summary": dataset,
        "fixed_settings": _fixed_settings(source),
        "formal_strategy_ids": list(P1D1_FORMAL_STRATEGY_IDS),
        "diagnostic_only_policy_ids": list(P1D1_DIAGNOSTIC_ONLY_POLICY_IDS),
        "bucket_ids": list(P1D1_BUCKET_IDS),
        "loss_definition": {
            "metric_id": "discovery_loss",
            "direction": "lower_is_better",
            "formula": "1 - discovered_variant_count / variant_denominator",
            "formal_primary_and_solution_matrix_only": True,
            "within_bucket_support": "uniform_empirical_four_variant_support",
        },
        "reference_distribution": {
            "distribution_id": "q0_uniform_over_buggy_buckets",
            "bucket_probabilities": {
                bucket: 1.0 / len(P1D1_BUCKET_IDS) for bucket in P1D1_BUCKET_IDS
            },
            "meaning": "uniform over the five buggy bucket actions, not over raw adversary variants",
        },
        "g0_discovery_loss_matrix": matrix,
        "restricted_pure_solution": _restricted_pure_solution(matrix),
        "mixed_solution": {
            "computed": False,
            "reason": "mixed minimax solver not included in this P1d1 slice",
        },
        "clean_false_positive_stress": _clean_stress(source, dataset),
        "secondary_metric_matrices": _secondary_matrices(source),
        "diagnostic_reports": {},
        "non_claims": [
            "P1d1 does not claim a production debugger or production fault-localization engine.",
            "P1d1 does not claim automated bug discovery, automated repair, or patch correctness.",
            "P1d1 does not claim arbitrary-program or real-world debugging accuracy.",
            "P1d1 does not claim a generally minimax-optimal debugger or a general Nash equilibrium.",
            "P1d1 does not claim a regret-optimal policy or robustness beyond the fixed empirical scaffold.",
        ],
        "notes": [
            "P1a is a Bayesian active bug-cause investigation prototype for synthetic observed-bug cases.",
            "P1b is a small injected checkout/pricing benchmark scaffold with 20 buggy variants and 5 clean variants.",
            "P1b location metrics are function-level only, and its real-diff artifacts are not real repository histories.",
            "P1c and P1d1 are analysis-only reporting over the existing scaffold.",
            "Raw variant IDs are support and diagnostic evidence, not adversary actions or within-bucket worst-case choices.",
            "random_action is diagnostic-only and is not computed in this minimum P1d1 report.",
            "metadata_synth is not computed; any future inclusion must remain a separate diagnostic report because of metadata dependence and optimism risk.",
            "Secondary metrics remain separate and do not enter the discovery-loss solution computation.",
        ],
    }


def p1d1_summary_to_json(summary: dict[str, Any]) -> str:
    """Serialize a P1d1 summary as stable, human-readable JSON."""

    return json.dumps(summary, indent=2) + "\n"


def _format_number(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def _format_ids(values: list[str]) -> str:
    return ", ".join(values) if values else "none"


def p1d1_summary_to_markdown(summary: dict[str, Any]) -> str:
    """Serialize a P1d1 summary as an auditable Markdown report."""

    dataset = summary["dataset_summary"]
    settings = summary["fixed_settings"]
    matrix = summary["g0_discovery_loss_matrix"]
    solution = summary["restricted_pure_solution"]
    lines = [
        "# P1d1 Analysis-Only Finite-Game Report",
        "",
        "P1d1 is an analysis-only reporting layer over existing P1b/P1c execution-grounded outcomes.",
        "The formal primary matrix contains only discovery loss for six existing deterministic policies and five existing buggy buckets.",
        "",
        "## Report IDs And Role",
        "",
        f"- schema_version: {summary['schema_version']}",
        f"- analysis_phase: {summary['analysis_phase']}",
        f"- game_id: {summary['game_id']}",
        f"- benchmark_id: {summary['benchmark_id']}",
        f"- report_role: {summary['report_role']}",
        f"- observation_mode: {summary['observation_mode']}",
        "",
        "## Dataset And Stable Bucket Support",
        "",
        f"- total variants: {dataset['total_variant_count']}",
        f"- buggy variants: {dataset['buggy_variant_count']}",
        f"- clean variants: {dataset['clean_variant_count']}",
        "",
        "| bucket | size | stable variant support |",
        "|---|---:|---|",
    ]
    for bucket in (*summary["bucket_ids"], "clean_false_positive"):
        lines.append(
            f"| {bucket} | {dataset['bucket_sizes'][bucket]} | "
            f"{_format_ids(dataset['bucket_membership'][bucket])} |"
        )

    lines.extend(
        [
            "",
            "## Fixed Settings",
            "",
            "| setting | value |",
            "|---|---:|",
        ]
    )
    for key in (
        "budget_limit",
        "max_steps",
        "failure_cost",
        "bug_presence_threshold",
        "no_bug_probability_threshold",
        "location_top1_threshold",
        "cause_top1_threshold",
        "min_expected_utility_per_cost",
        "rng_seed",
    ):
        lines.append(f"| {key} | {_format_number(settings[key])} |")
    lines.extend(
        [
            "",
            f"- random_action stable-seed contract: `{settings['seed_contract']['random_action_stable_seed']}`",
            "- The seed does not change the six formal deterministic policy mappings.",
            "",
            "## Strategy And Bucket Sets",
            "",
            f"- formal_strategy_ids: {_format_ids(summary['formal_strategy_ids'])}",
            f"- diagnostic_only_policy_ids: {_format_ids(summary['diagnostic_only_policy_ids'])}",
            f"- formal buggy bucket_ids: {_format_ids(summary['bucket_ids'])}",
            "- `random_action` is excluded from the formal matrix, restricted-pure computation, and mixed candidate set.",
            "- Raw variants are uniform cell support and audit evidence, not adversary actions or within-bucket choices.",
            "",
            "## G0 Discovery-Loss Matrix",
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
            "### Cell Numerator/Denominator Evidence",
            "",
            "| policy | bucket | discovered | support | rate | loss | diagnostic variants | discovered variants | missed variants |",
            "|---|---|---:|---:|---:|---:|---|---|---|",
        ]
    )
    for policy in summary["formal_strategy_ids"]:
        for bucket in summary["bucket_ids"]:
            cell = matrix["cells_by_policy"][policy][bucket]
            lines.append(
                f"| {policy} | {bucket} | {cell['discovered_numerator']} | "
                f"{cell['variant_denominator']} | {_format_number(cell['discovery_rate'])} | "
                f"{_format_number(cell['discovery_loss'])} | "
                f"{_format_ids(cell['diagnostic_variant_ids'])} | "
                f"{_format_ids(cell['discovered_variant_ids'])} | "
                f"{_format_ids(cell['missed_variant_ids'])} |"
            )

    lines.extend(
        [
            "",
            "## Restricted Pure Result And Reference Gap",
            "",
            "| policy | worst bucket loss | tied worst buckets | reference average loss | average-to-worst gap |",
            "|---|---:|---|---:|---:|",
        ]
    )
    for policy in summary["formal_strategy_ids"]:
        row = solution["by_policy"][policy]
        lines.append(
            f"| {policy} | {_format_number(row['worst_bucket_loss'])} | "
            f"{_format_ids(row['worst_bucket_ids'])} | "
            f"{_format_number(row['reference_average_loss'])} | "
            f"{_format_number(row['average_to_worst_gap'])} |"
        )
    lines.extend(
        [
            "",
            f"- restricted_pure_security_loss: {_format_number(solution['restricted_pure_security_loss'])}",
            f"- restricted_pure_security_policies: {_format_ids(solution['restricted_pure_security_policies'])}",
            "- q0: uniform probability 1/5 on each formal buggy bucket.",
            f"- tie rule: {solution['tie_rule']}",
            f"- rounding rule: {solution['rounding_rule']}",
            "",
            "## Clean False-Positive Stress",
            "",
            "This stress is separate from the formal buggy matrix and restricted-pure result.",
            "",
            "| policy | false positives | clean variants | rate | mean cost | no-bug stop rate | false-positive variant IDs |",
            "|---|---:|---:|---:|---:|---:|---|",
        ]
    )
    clean = summary["clean_false_positive_stress"]
    for policy in summary["formal_strategy_ids"]:
        row = clean["by_policy"][policy]
        lines.append(
            f"| {policy} | {row['false_positive_numerator']} | "
            f"{row['clean_variant_denominator']} | "
            f"{_format_number(row['clean_false_positive_rate'])} | "
            f"{_format_number(row['clean_mean_investigation_cost'])} | "
            f"{_format_number(row['clean_no_bug_stop_rate'])} | "
            f"{_format_ids(row['false_positive_clean_variant_ids'])} |"
        )
    if all(
        row["false_positive_numerator"] == 0 for row in clean["by_policy"].values()
    ):
        lines.append(
            "\nClean false positives were not triggered in the current five clean variants."
        )
    lines.extend(["", f"- {clean['risk_note']}", "", "## Secondary Metric Matrices", ""])
    lines.append(
        "Secondary matrices are lower-is-better, remain separate from discovery loss, and are not used in the restricted-pure computation."
    )
    for metric_id, secondary in summary["secondary_metric_matrices"].items():
        lines.extend(
            [
                "",
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
        if metric_id == "cost_to_first_failure":
            lines.append(
                f"\nA missed buggy variant contributes the existing penalized `failure_cost={secondary['failure_cost']}`."
            )

    mixed = summary["mixed_solution"]
    lines.extend(
        [
            "",
            "## Mixed Solution",
            "",
            f"Mixed solution: not computed ({mixed['reason']}).",
            "",
            "## Diagnostic Reports",
            "",
            "No optional random_action or metadata_synth diagnostic report is computed in this minimum slice.",
            "",
            "## Scope, Limitations, And Non-Claims",
            "",
        ]
    )
    lines.extend(f"- {note}" for note in summary["notes"])
    lines.extend(f"- {claim}" for claim in summary["non_claims"])
    return "\n".join(lines) + "\n"
