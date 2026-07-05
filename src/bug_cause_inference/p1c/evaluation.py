"""Analysis-only P1c worst-case reports over existing P1b runs."""

from __future__ import annotations

import json
from statistics import mean
from typing import Any

from bug_cause_inference.p1b.actions import P1B_OBSERVATION_MODES
from bug_cause_inference.p1b.dataset import load_p1b_variants
from bug_cause_inference.p1b.models import P1BRunResult, P1BSettings, P1BVariant, rank_distribution
from bug_cause_inference.p1b.policies import P1B_POLICIES, P1B_PRIMARY_POLICY, run_p1b_investigation
from bug_cause_inference.p1c.labels import (
    BUGGY_PRIMARY_BUCKETS,
    PRIMARY_BUCKETS,
    bucket_size_summary,
    load_p1c_variant_labels,
    p1c_variant_labels_to_dict,
)


P1C_COMPARISON_OBSERVATION_MODE = "both"
P1C_OBSERVATION_MODES = P1B_OBSERVATION_MODES + (P1C_COMPARISON_OBSERVATION_MODE,)
P1C_DEFAULT_OBSERVATION_MODE = "execution_grounded"

HEADLINE_KEYS = (
    "min_bucket_bug_discovery_rate",
    "max_bucket_cost_to_first_failure",
    "min_bucket_location_top3_accuracy",
    "min_bucket_cause_top1_accuracy",
    "min_bucket_fix_intent_top1_accuracy",
    "max_bucket_wrong_cause_high_confidence_rate",
    "clean_false_positive_rate",
    "max_bucket_mean_investigation_cost",
)

RAW_WORST_CASE_KEYS = (
    "missed_bug_variant_ids",
    "max_first_failure_cost_variant_ids",
    "location_top3_miss_variant_ids",
    "cause_top1_miss_variant_ids",
    "fix_intent_top1_miss_variant_ids",
    "wrong_cause_high_confidence_variant_ids",
    "false_positive_clean_variant_ids",
)


def _settings_to_dict(settings: P1BSettings) -> dict[str, Any]:
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


def _dataset_to_dict(variants: list[P1BVariant]) -> dict[str, Any]:
    return {
        "total_variants": len(variants),
        "buggy_variants": sum(1 for variant in variants if variant.is_buggy),
        "clean_variants": sum(1 for variant in variants if not variant.is_buggy),
        "bucket_sizes": bucket_size_summary(variants),
    }


def _rank(distribution: dict[str, float]) -> list[str]:
    return [label for label, _ in rank_distribution(distribution)]


def _rank_position(distribution: dict[str, float], target: str | None) -> int | None:
    if target is None:
        return None
    ranked = _rank(distribution)
    if target not in ranked:
        return None
    return ranked.index(target) + 1


def _safe_rate(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return round(numerator / denominator, 6)


def _safe_mean(values: list[float | int]) -> float | None:
    if not values:
        return None
    return round(mean(values), 6)


def _variant_outcome(
    variant: P1BVariant,
    result: P1BRunResult,
    settings: P1BSettings,
    primary_bucket: str,
) -> dict[str, Any]:
    base: dict[str, Any] = {
        "variant_id": variant.variant_id,
        "policy": result.policy,
        "primary_bucket": primary_bucket,
        "is_buggy": variant.is_buggy,
        "stop_reason": result.stop_reason,
        "bug_presence_posterior": round(result.bug_presence_posterior, 6),
    }
    if variant.is_buggy:
        location_rank = _rank_position(result.location_posterior, variant.target_location)
        cause_rank = _rank(result.cause_posterior)
        fix_rank = _rank(result.fix_intent_posterior)
        cause_top = rank_distribution(result.cause_posterior)[0]
        first_failure_cost_penalized = (
            result.first_failure_cost if result.first_failure_cost is not None else settings.failure_cost
        )
        base.update(
            {
                "discovered_within_budget": result.bug_detected
                and result.cumulative_cost <= settings.budget_limit,
                "first_failure_cost_penalized": first_failure_cost_penalized,
                "location_top1_hit": location_rank == 1,
                "location_top3_hit": location_rank is not None and location_rank <= 3,
                "cause_top1_hit": variant.true_cause_category in cause_rank[:1],
                "cause_top2_hit": variant.true_cause_category in cause_rank[:2],
                "fix_intent_top1_hit": variant.fix_intent_category in fix_rank[:1],
                "fix_intent_top3_hit": variant.fix_intent_category in fix_rank[:3],
                "wrong_cause_high_confidence": cause_top[1] >= settings.cause_top1_threshold
                and cause_top[0] != variant.true_cause_category,
                "investigation_cost": result.cumulative_cost,
            }
        )
        return base

    base.update(
        {
            "false_positive": result.stop_reason == "bug_confidence_threshold"
            or result.bug_presence_posterior >= settings.bug_presence_threshold,
            "clean_no_bug_stop": result.stop_reason == "no_bug_probability_threshold",
            "clean_investigation_cost": result.cumulative_cost,
        }
    )
    return base


def _bucket_metrics(outcomes: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    metrics: dict[str, dict[str, Any]] = {}
    for bucket in PRIMARY_BUCKETS:
        bucket_outcomes = [outcome for outcome in outcomes if outcome["primary_bucket"] == bucket]
        buggy = [outcome for outcome in bucket_outcomes if outcome["is_buggy"]]
        clean = [outcome for outcome in bucket_outcomes if not outcome["is_buggy"]]
        costs = [
            outcome["investigation_cost"] if outcome["is_buggy"] else outcome["clean_investigation_cost"]
            for outcome in bucket_outcomes
        ]
        metrics[bucket] = {
            "variant_count": len(bucket_outcomes),
            "buggy_variant_count": len(buggy),
            "clean_variant_count": len(clean),
            "bucket_bug_discovery_rate": _safe_rate(
                sum(1 for outcome in buggy if outcome["discovered_within_budget"]),
                len(buggy),
            ),
            "bucket_cost_to_first_failure": _safe_mean(
                [outcome["first_failure_cost_penalized"] for outcome in buggy]
            ),
            "bucket_location_top3_accuracy": _safe_rate(
                sum(1 for outcome in buggy if outcome["location_top3_hit"]),
                len(buggy),
            ),
            "bucket_cause_top1_accuracy": _safe_rate(
                sum(1 for outcome in buggy if outcome["cause_top1_hit"]),
                len(buggy),
            ),
            "bucket_fix_intent_top1_accuracy": _safe_rate(
                sum(1 for outcome in buggy if outcome["fix_intent_top1_hit"]),
                len(buggy),
            ),
            "bucket_wrong_cause_high_confidence_rate": _safe_rate(
                sum(1 for outcome in buggy if outcome["wrong_cause_high_confidence"]),
                len(buggy),
            ),
            "bucket_false_positive_rate": _safe_rate(
                sum(1 for outcome in clean if outcome["false_positive"]),
                len(clean),
            ),
            "bucket_mean_investigation_cost": _safe_mean(costs),
        }
    return metrics


def _value_with_buckets(
    bucket_metrics: dict[str, dict[str, Any]],
    metric: str,
    buckets: tuple[str, ...],
    selector: str,
) -> dict[str, Any]:
    values = {
        bucket: bucket_metrics[bucket][metric]
        for bucket in buckets
        if bucket_metrics[bucket][metric] is not None
    }
    if not values:
        return {"value": None, "bucket_ids": []}
    selected = min(values.values()) if selector == "min" else max(values.values())
    return {
        "value": selected,
        "bucket_ids": sorted(bucket for bucket, value in values.items() if value == selected),
    }


def _headline_worst_case_summary(bucket_metrics: dict[str, dict[str, Any]]) -> dict[str, Any]:
    clean_fp = bucket_metrics["clean_false_positive"]["bucket_false_positive_rate"]
    return {
        "min_bucket_bug_discovery_rate": _value_with_buckets(
            bucket_metrics,
            "bucket_bug_discovery_rate",
            BUGGY_PRIMARY_BUCKETS,
            "min",
        ),
        "max_bucket_cost_to_first_failure": _value_with_buckets(
            bucket_metrics,
            "bucket_cost_to_first_failure",
            BUGGY_PRIMARY_BUCKETS,
            "max",
        ),
        "min_bucket_location_top3_accuracy": _value_with_buckets(
            bucket_metrics,
            "bucket_location_top3_accuracy",
            BUGGY_PRIMARY_BUCKETS,
            "min",
        ),
        "min_bucket_cause_top1_accuracy": _value_with_buckets(
            bucket_metrics,
            "bucket_cause_top1_accuracy",
            BUGGY_PRIMARY_BUCKETS,
            "min",
        ),
        "min_bucket_fix_intent_top1_accuracy": _value_with_buckets(
            bucket_metrics,
            "bucket_fix_intent_top1_accuracy",
            BUGGY_PRIMARY_BUCKETS,
            "min",
        ),
        "max_bucket_wrong_cause_high_confidence_rate": _value_with_buckets(
            bucket_metrics,
            "bucket_wrong_cause_high_confidence_rate",
            BUGGY_PRIMARY_BUCKETS,
            "max",
        ),
        "clean_false_positive_rate": {
            "value": clean_fp,
            "bucket_ids": ["clean_false_positive"] if clean_fp is not None else [],
        },
        "max_bucket_mean_investigation_cost": _value_with_buckets(
            bucket_metrics,
            "bucket_mean_investigation_cost",
            PRIMARY_BUCKETS,
            "max",
        ),
    }


def _raw_variant_worst_cases(outcomes: list[dict[str, Any]]) -> dict[str, list[str]]:
    buggy = [outcome for outcome in outcomes if outcome["is_buggy"]]
    clean = [outcome for outcome in outcomes if not outcome["is_buggy"]]
    max_failure_cost = max((outcome["first_failure_cost_penalized"] for outcome in buggy), default=None)
    return {
        "missed_bug_variant_ids": sorted(
            outcome["variant_id"] for outcome in buggy if not outcome["discovered_within_budget"]
        ),
        "max_first_failure_cost_variant_ids": sorted(
            outcome["variant_id"]
            for outcome in buggy
            if max_failure_cost is not None and outcome["first_failure_cost_penalized"] == max_failure_cost
        ),
        "location_top3_miss_variant_ids": sorted(
            outcome["variant_id"] for outcome in buggy if not outcome["location_top3_hit"]
        ),
        "cause_top1_miss_variant_ids": sorted(
            outcome["variant_id"] for outcome in buggy if not outcome["cause_top1_hit"]
        ),
        "fix_intent_top1_miss_variant_ids": sorted(
            outcome["variant_id"] for outcome in buggy if not outcome["fix_intent_top1_hit"]
        ),
        "wrong_cause_high_confidence_variant_ids": sorted(
            outcome["variant_id"] for outcome in buggy if outcome["wrong_cause_high_confidence"]
        ),
        "false_positive_clean_variant_ids": sorted(
            outcome["variant_id"] for outcome in clean if outcome["false_positive"]
        ),
    }


def _aggregate_metrics(outcomes: list[dict[str, Any]]) -> dict[str, float | None]:
    buggy = [outcome for outcome in outcomes if outcome["is_buggy"]]
    clean = [outcome for outcome in outcomes if not outcome["is_buggy"]]
    costs = [
        outcome["investigation_cost"] if outcome["is_buggy"] else outcome["clean_investigation_cost"]
        for outcome in outcomes
    ]
    return {
        "bug_discovery_rate_within_budget": _safe_rate(
            sum(1 for outcome in buggy if outcome["discovered_within_budget"]),
            len(buggy),
        ),
        "cost_to_first_failure": _safe_mean(
            [outcome["first_failure_cost_penalized"] for outcome in buggy]
        ),
        "location_top3_accuracy": _safe_rate(
            sum(1 for outcome in buggy if outcome["location_top3_hit"]),
            len(buggy),
        ),
        "cause_top1_accuracy": _safe_rate(
            sum(1 for outcome in buggy if outcome["cause_top1_hit"]),
            len(buggy),
        ),
        "fix_intent_top1_accuracy": _safe_rate(
            sum(1 for outcome in buggy if outcome["fix_intent_top1_hit"]),
            len(buggy),
        ),
        "wrong_cause_high_confidence_rate": _safe_rate(
            sum(1 for outcome in buggy if outcome["wrong_cause_high_confidence"]),
            len(buggy),
        ),
        "false_positive_rate_on_clean_cases": _safe_rate(
            sum(1 for outcome in clean if outcome["false_positive"]),
            len(clean),
        ),
        "mean_investigation_cost": _safe_mean(costs),
    }


def _gap_row(
    *,
    direction: str,
    average_metric: float | None,
    worst_bucket_metric: float | None,
) -> dict[str, Any]:
    gap = None
    if average_metric is not None and worst_bucket_metric is not None:
        if direction == "higher_is_better":
            gap = round(average_metric - worst_bucket_metric, 6)
        else:
            gap = round(worst_bucket_metric - average_metric, 6)
    return {
        "direction": direction,
        "average_metric": average_metric,
        "worst_bucket_metric": worst_bucket_metric,
        "gap": gap,
    }


def _average_vs_worst_gap(
    aggregate: dict[str, float | None],
    headline: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    return {
        "bucket_bug_discovery_rate": _gap_row(
            direction="higher_is_better",
            average_metric=aggregate["bug_discovery_rate_within_budget"],
            worst_bucket_metric=headline["min_bucket_bug_discovery_rate"]["value"],
        ),
        "bucket_cost_to_first_failure": _gap_row(
            direction="lower_is_better",
            average_metric=aggregate["cost_to_first_failure"],
            worst_bucket_metric=headline["max_bucket_cost_to_first_failure"]["value"],
        ),
        "bucket_location_top3_accuracy": _gap_row(
            direction="higher_is_better",
            average_metric=aggregate["location_top3_accuracy"],
            worst_bucket_metric=headline["min_bucket_location_top3_accuracy"]["value"],
        ),
        "bucket_cause_top1_accuracy": _gap_row(
            direction="higher_is_better",
            average_metric=aggregate["cause_top1_accuracy"],
            worst_bucket_metric=headline["min_bucket_cause_top1_accuracy"]["value"],
        ),
        "bucket_fix_intent_top1_accuracy": _gap_row(
            direction="higher_is_better",
            average_metric=aggregate["fix_intent_top1_accuracy"],
            worst_bucket_metric=headline["min_bucket_fix_intent_top1_accuracy"]["value"],
        ),
        "bucket_wrong_cause_high_confidence_rate": _gap_row(
            direction="lower_is_better",
            average_metric=aggregate["wrong_cause_high_confidence_rate"],
            worst_bucket_metric=headline["max_bucket_wrong_cause_high_confidence_rate"]["value"],
        ),
        "clean_false_positive_rate": _gap_row(
            direction="lower_is_better",
            average_metric=aggregate["false_positive_rate_on_clean_cases"],
            worst_bucket_metric=headline["clean_false_positive_rate"]["value"],
        ),
        "bucket_mean_investigation_cost": _gap_row(
            direction="lower_is_better",
            average_metric=aggregate["mean_investigation_cost"],
            worst_bucket_metric=headline["max_bucket_mean_investigation_cost"]["value"],
        ),
    }


def _evaluate_single_mode(
    *,
    variants: list[P1BVariant],
    policies: tuple[str, ...],
    settings: P1BSettings,
    observation_mode: str,
) -> dict[str, Any]:
    labels = load_p1c_variant_labels(variants)
    per_variant_outcomes: dict[str, list[dict[str, Any]]] = {}
    bucket_metrics: dict[str, dict[str, Any]] = {}
    headline: dict[str, dict[str, Any]] = {}
    raw_worst: dict[str, dict[str, list[str]]] = {}
    average_vs_worst: dict[str, dict[str, dict[str, Any]]] = {}

    for policy in policies:
        outcomes: list[dict[str, Any]] = []
        for variant in variants:
            result = run_p1b_investigation(
                variant,
                policy=policy,
                settings=settings,
                observation_mode=observation_mode,
            )
            label = labels[variant.variant_id]
            outcomes.append(_variant_outcome(variant, result, settings, label.primary_bucket))
        policy_bucket_metrics = _bucket_metrics(outcomes)
        policy_headline = _headline_worst_case_summary(policy_bucket_metrics)
        per_variant_outcomes[policy] = outcomes
        bucket_metrics[policy] = policy_bucket_metrics
        headline[policy] = policy_headline
        raw_worst[policy] = _raw_variant_worst_cases(outcomes)
        average_vs_worst[policy] = _average_vs_worst_gap(_aggregate_metrics(outcomes), policy_headline)

    return {
        "benchmark": "p1b_injected_bug_benchmark",
        "analysis_phase": "p1c1_analysis_only_worst_case_report",
        "observation_mode": observation_mode,
        "dataset": _dataset_to_dict(variants),
        "settings": _settings_to_dict(settings),
        "primary_policy": P1B_PRIMARY_POLICY,
        "policies_evaluated": list(policies),
        "variant_labels": p1c_variant_labels_to_dict(variants),
        "per_variant_outcomes": per_variant_outcomes,
        "bucket_metrics": bucket_metrics,
        "headline_worst_case_summary": headline,
        "raw_variant_worst_cases": raw_worst,
        "average_vs_worst_gap": average_vs_worst,
        "notes": [
            "P1c1 is an analysis-only report over existing P1b variants, policies, settings, and run results.",
            "execution_grounded is the primary observation mode; metadata_synth is diagnostic when requested.",
            "The report does not add variants, change P1b policy logic, tune thresholds, or alter action costs.",
            "The report does not generate patches, evaluate LLM agents, use real repository histories, or claim a formal game-theoretic guarantee.",
            "Bucket and raw variant worst cases are diagnostic for this 25-variant injected scaffold only.",
        ],
    }


def evaluate_p1c(
    variants: list[P1BVariant] | None = None,
    policies: tuple[str, ...] = P1B_POLICIES,
    settings: P1BSettings | None = None,
    observation_mode: str = P1C_DEFAULT_OBSERVATION_MODE,
) -> dict[str, Any]:
    """Build the P1c1 analysis-only worst-case report."""

    if observation_mode not in P1C_OBSERVATION_MODES:
        raise ValueError(f"Unknown P1c observation mode: {observation_mode}")
    settings = settings or P1BSettings()
    variants = variants or load_p1b_variants()
    if observation_mode != P1C_COMPARISON_OBSERVATION_MODE:
        return _evaluate_single_mode(
            variants=variants,
            policies=policies,
            settings=settings,
            observation_mode=observation_mode,
        )

    execution = _evaluate_single_mode(
        variants=variants,
        policies=policies,
        settings=settings,
        observation_mode="execution_grounded",
    )
    metadata = _evaluate_single_mode(
        variants=variants,
        policies=policies,
        settings=settings,
        observation_mode="metadata_synth",
    )
    combined = dict(execution)
    combined.update(
        {
            "observation_mode": P1C_COMPARISON_OBSERVATION_MODE,
            "primary_observation_mode": "execution_grounded",
            "compared_observation_modes": ["execution_grounded", "metadata_synth"],
            "diagnostic_reports_by_observation_mode": {
                "execution_grounded": execution,
                "metadata_synth": metadata,
            },
        }
    )
    combined["notes"] = list(execution["notes"]) + [
        "Top-level worst-case fields in both mode use execution_grounded as the primary report.",
        "metadata_synth is included only as a diagnostic comparison because it is metadata-dependent.",
    ]
    return combined


def p1c_evaluation_to_json(summary: dict[str, Any]) -> str:
    return json.dumps(summary, indent=2) + "\n"


def _format_value(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def _headline_value(row: dict[str, Any]) -> str:
    value = _format_value(row["value"])
    buckets = ", ".join(row["bucket_ids"])
    return f"{value} ({buckets})" if buckets else value


def _variant_ids(ids: list[str]) -> str:
    return ", ".join(ids) if ids else "none"


def p1c_evaluation_to_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# P1c1 Worst-Case Analysis Report",
        "",
        "P1c1 is an analysis-only robustness report over the existing P1b injected-bug benchmark.",
        "It reuses existing P1b variants, policies, settings, and run results.",
        "It does not add new variants, tune policies, generate patches, or claim a formal game-theoretic guarantee.",
        "",
        "## Dataset",
        "",
        f"- benchmark: {summary['benchmark']}",
        f"- analysis_phase: {summary['analysis_phase']}",
        f"- observation_mode: {summary['observation_mode']}",
        "- primary observation mode: execution_grounded",
        f"- total_variants: {summary['dataset']['total_variants']}",
        f"- buggy_variants: {summary['dataset']['buggy_variants']}",
        f"- clean_variants: {summary['dataset']['clean_variants']}",
        f"- policies_evaluated: {', '.join(summary['policies_evaluated'])}",
        "",
        "## Bucket Definitions",
        "",
        "| bucket | variants | purpose |",
        "|---|---|---|",
    ]
    bucket_purposes = {
        "boundary_precision": "Exact thresholds, upper bounds, and rounding edge cases.",
        "missing_optional_input": "Absent values, missing keys, and optional fields.",
        "config_normalization": "Missing config defaults, aliases, flags, and type normalization.",
        "state_sequence": "Operation order, idempotence, stale state, and reservation transitions.",
        "spec_semantics": "Calculation order, selection rules, and documented exception rules.",
        "clean_false_positive": "Clean but confusing cases used for false-positive stress.",
    }
    for bucket in PRIMARY_BUCKETS:
        variant_ids = summary["dataset"]["bucket_sizes"][bucket]["variant_ids"]
        lines.append(f"| {bucket} | {', '.join(variant_ids)} | {bucket_purposes[bucket]} |")

    lines.extend(
        [
            "",
            "## Headline Worst-Case Summary",
            "",
            "| policy | min_discovery | max_first_failure_cost | min_location_top3 | min_cause_top1 | min_fix_intent_top1 | max_wrong_cause_high_conf | clean_false_positive | max_mean_cost |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for policy in summary["policies_evaluated"]:
        headline = summary["headline_worst_case_summary"][policy]
        lines.append(
            f"| {policy} | "
            f"{_headline_value(headline['min_bucket_bug_discovery_rate'])} | "
            f"{_headline_value(headline['max_bucket_cost_to_first_failure'])} | "
            f"{_headline_value(headline['min_bucket_location_top3_accuracy'])} | "
            f"{_headline_value(headline['min_bucket_cause_top1_accuracy'])} | "
            f"{_headline_value(headline['min_bucket_fix_intent_top1_accuracy'])} | "
            f"{_headline_value(headline['max_bucket_wrong_cause_high_confidence_rate'])} | "
            f"{_headline_value(headline['clean_false_positive_rate'])} | "
            f"{_headline_value(headline['max_bucket_mean_investigation_cost'])} |"
        )

    lines.extend(["", "## Bucket Metrics", ""])
    for policy in summary["policies_evaluated"]:
        lines.extend(
            [
                f"### {policy}",
                "",
                "| bucket | discovery | first_failure_cost | location_top3 | cause_top1 | fix_intent_top1 | wrong_cause_high_conf | false_positive | mean_cost |",
                "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for bucket in PRIMARY_BUCKETS:
            metrics = summary["bucket_metrics"][policy][bucket]
            lines.append(
                f"| {bucket} | {_format_value(metrics['bucket_bug_discovery_rate'])} | "
                f"{_format_value(metrics['bucket_cost_to_first_failure'])} | "
                f"{_format_value(metrics['bucket_location_top3_accuracy'])} | "
                f"{_format_value(metrics['bucket_cause_top1_accuracy'])} | "
                f"{_format_value(metrics['bucket_fix_intent_top1_accuracy'])} | "
                f"{_format_value(metrics['bucket_wrong_cause_high_confidence_rate'])} | "
                f"{_format_value(metrics['bucket_false_positive_rate'])} | "
                f"{_format_value(metrics['bucket_mean_investigation_cost'])} |"
            )
        lines.append("")

    lines.extend(["## Raw Worst-Case Variant IDs", ""])
    for policy in summary["policies_evaluated"]:
        lines.extend([f"### {policy}", ""])
        raw = summary["raw_variant_worst_cases"][policy]
        for key in RAW_WORST_CASE_KEYS:
            lines.append(f"- {key}: {_variant_ids(raw[key])}")
        lines.append("")

    lines.extend(
        [
            "## Average-Versus-Worst Gap",
            "",
            "| policy | metric | direction | average | worst_bucket | gap |",
            "|---|---|---|---:|---:|---:|",
        ]
    )
    for policy in summary["policies_evaluated"]:
        for metric, row in summary["average_vs_worst_gap"][policy].items():
            lines.append(
                f"| {policy} | {metric} | {row['direction']} | "
                f"{_format_value(row['average_metric'])} | "
                f"{_format_value(row['worst_bucket_metric'])} | "
                f"{_format_value(row['gap'])} |"
            )

    lines.extend(["", "## Notes", ""])
    lines.extend(f"- {note}" for note in summary["notes"])
    if summary.get("observation_mode") == P1C_COMPARISON_OBSERVATION_MODE:
        lines.extend(
            [
                "- In `both` mode, top-level tables are the execution_grounded primary report.",
                "- The metadata_synth diagnostic report is present in JSON under `diagnostic_reports_by_observation_mode`.",
            ]
        )
    return "\n".join(lines) + "\n"
