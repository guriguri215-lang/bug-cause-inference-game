"""Evaluation metrics for the P1b injected-bug benchmark."""

from __future__ import annotations

import json
from statistics import mean
from typing import Any

from bug_cause_inference.p1b.dataset import load_p1b_variants
from bug_cause_inference.p1b.models import P1B_CAUSE_CATEGORIES, P1BRunResult, P1BSettings, P1BVariant, rank_distribution
from bug_cause_inference.p1b.policies import P1B_POLICIES, P1B_PRIMARY_POLICY, run_p1b_investigation


def _rank(distribution: dict[str, float]) -> list[str]:
    return [label for label, _ in rank_distribution(distribution)]


def _safe_rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 6) if denominator else 0.0


def _location_rank(variant: P1BVariant, result: P1BRunResult) -> int | None:
    target = variant.target_location
    if target is None:
        return None
    ranked = _rank(result.location_posterior)
    if target not in ranked:
        return None
    return ranked.index(target) + 1


def _cause_brier_score(variants: list[P1BVariant], results: list[P1BRunResult]) -> float:
    lookup = {variant.variant_id: variant for variant in variants}
    total = 0.0
    count = 0
    for result in results:
        variant = lookup[result.variant_id]
        if not variant.is_buggy or variant.true_cause_category is None:
            continue
        for cause in P1B_CAUSE_CATEGORIES:
            expected = 1.0 if cause == variant.true_cause_category else 0.0
            total += (result.cause_posterior.get(cause, 0.0) - expected) ** 2
        count += 1
    return round(total / count, 6) if count else 0.0


def _policy_metrics(
    variants: list[P1BVariant],
    results: list[P1BRunResult],
    settings: P1BSettings,
) -> dict[str, Any]:
    variant_lookup = {variant.variant_id: variant for variant in variants}
    buggy_results = [result for result in results if result.is_buggy]
    clean_results = [result for result in results if not result.is_buggy]
    buggy_count = len(buggy_results)
    clean_count = len(clean_results)

    # The current loop only selects actions that fit the remaining budget; keep
    # this predicate so the metric contract stays explicit if that loop changes.
    discovered = [
        result
        for result in buggy_results
        if result.bug_detected and result.cumulative_cost <= settings.budget_limit
    ]
    first_failure_costs = [
        result.first_failure_cost if result.first_failure_cost is not None else settings.failure_cost
        for result in buggy_results
    ]
    false_positives = [
        result
        for result in clean_results
        if result.stop_reason == "bug_confidence_threshold"
        or result.bug_presence_posterior >= settings.bug_presence_threshold
    ]
    # The over-budget branch is defensive under today's remaining-budget action
    # filter, but preserves the false-negative definition for future stop logic.
    false_negatives = [
        result
        for result in buggy_results
        if not result.bug_detected
        or result.stop_reason == "no_bug_probability_threshold"
        or result.cumulative_cost > settings.budget_limit
    ]

    location_ranks: list[int] = []
    cause_top1 = 0
    cause_top2 = 0
    fix_top1 = 0
    fix_top3 = 0
    wrong_cause_high_confidence = 0
    for result in buggy_results:
        variant = variant_lookup[result.variant_id]
        location_rank = _location_rank(variant, result)
        if location_rank is not None:
            location_ranks.append(location_rank)
        cause_rank = _rank(result.cause_posterior)
        if variant.true_cause_category in cause_rank[:1]:
            cause_top1 += 1
        if variant.true_cause_category in cause_rank[:2]:
            cause_top2 += 1
        cause_top = rank_distribution(result.cause_posterior)[0]
        if cause_top[1] >= settings.cause_top1_threshold and cause_top[0] != variant.true_cause_category:
            wrong_cause_high_confidence += 1
        fix_rank = _rank(result.fix_intent_posterior)
        if variant.fix_intent_category in fix_rank[:1]:
            fix_top1 += 1
        if variant.fix_intent_category in fix_rank[:3]:
            fix_top3 += 1

    return {
        "num_variants": len(results),
        "buggy_variants": buggy_count,
        "clean_variants": clean_count,
        "bug_discovery_rate_within_budget": _safe_rate(len(discovered), buggy_count),
        "cost_to_first_failure": round(mean(first_failure_costs), 6) if first_failure_costs else 0.0,
        "reproduction_success_rate": _safe_rate(
            sum(1 for result in buggy_results if result.reproduction_input is not None),
            buggy_count,
        ),
        "false_positive_rate_on_clean_cases": _safe_rate(len(false_positives), clean_count),
        "false_negative_rate_on_buggy_cases": _safe_rate(len(false_negatives), buggy_count),
        "location_top1_accuracy": _safe_rate(sum(1 for rank in location_ranks if rank == 1), buggy_count),
        "location_top3_accuracy": _safe_rate(sum(1 for rank in location_ranks if rank <= 3), buggy_count),
        "location_mrr": round(mean(1.0 / rank for rank in location_ranks), 6) if location_ranks else 0.0,
        "cause_top1_accuracy": _safe_rate(cause_top1, buggy_count),
        "cause_top2_accuracy": _safe_rate(cause_top2, buggy_count),
        "cost_to_true_cause_top1": round(
            mean(result.cost_to_true_cause_top1 or settings.failure_cost for result in buggy_results),
            6,
        )
        if buggy_results
        else 0.0,
        "wrong_cause_high_confidence_rate": _safe_rate(wrong_cause_high_confidence, buggy_count),
        "fix_intent_top1_accuracy": _safe_rate(fix_top1, buggy_count),
        "fix_intent_top3_accuracy": _safe_rate(fix_top3, buggy_count),
        "mean_investigation_cost": round(mean(result.cumulative_cost for result in results), 6),
        "mean_investigation_cost_buggy_only": round(mean(result.cumulative_cost for result in buggy_results), 6)
        if buggy_results
        else 0.0,
        "cause_brier_score": _cause_brier_score(variants, results),
        "stop_reason_counts": {
            reason: sum(1 for result in results if result.stop_reason == reason)
            for reason in sorted({result.stop_reason for result in results})
        },
    }


def evaluate_p1b(
    variants: list[P1BVariant] | None = None,
    policies: tuple[str, ...] = P1B_POLICIES,
    settings: P1BSettings | None = None,
) -> dict[str, Any]:
    settings = settings or P1BSettings()
    variants = variants or load_p1b_variants()
    policy_results: dict[str, list[P1BRunResult]] = {}
    policy_metrics: dict[str, Any] = {}
    for policy in policies:
        results = [run_p1b_investigation(variant, policy=policy, settings=settings) for variant in variants]
        policy_results[policy] = results
        policy_metrics[policy] = _policy_metrics(variants, results, settings)

    primary = policy_metrics.get(P1B_PRIMARY_POLICY)
    fixed = policy_metrics.get("fixed_checklist")
    cost_delta = None
    if primary and fixed and fixed["mean_investigation_cost"]:
        cost_delta = (
            fixed["mean_investigation_cost"] - primary["mean_investigation_cost"]
        ) / fixed["mean_investigation_cost"]
    return {
        "benchmark": "p1b_injected_bug_benchmark",
        "settings": {
            "budget_limit": settings.budget_limit,
            "max_steps": settings.max_steps,
            "failure_cost": settings.failure_cost,
            "bug_presence_threshold": settings.bug_presence_threshold,
            "no_bug_probability_threshold": settings.no_bug_probability_threshold,
            "location_top1_threshold": settings.location_top1_threshold,
            "cause_top1_threshold": settings.cause_top1_threshold,
            "min_expected_utility_per_cost": settings.min_expected_utility_per_cost,
            "rng_seed": settings.rng_seed,
        },
        "dataset": {
            "total_variants": len(variants),
            "buggy_variants": sum(1 for variant in variants if variant.is_buggy),
            "clean_variants": sum(1 for variant in variants if not variant.is_buggy),
        },
        "primary_policy": P1B_PRIMARY_POLICY,
        "policies": policy_metrics,
        "success_checks": {
            "primary_policy": P1B_PRIMARY_POLICY,
            "primary_vs_fixed_mean_cost_delta": round(cost_delta, 6) if cost_delta is not None else None,
            "primary_mean_cost_at_least_10_percent_below_fixed_checklist": cost_delta >= 0.10
            if cost_delta is not None
            else None,
            "primary_bug_discovery_rate_at_least_75_percent": primary["bug_discovery_rate_within_budget"] >= 0.75
            if primary
            else None,
            "primary_clean_false_positive_rate_at_most_20_percent": primary["false_positive_rate_on_clean_cases"] <= 0.20
            if primary
            else None,
            "primary_location_top3_at_least_65_percent": primary["location_top3_accuracy"] >= 0.65
            if primary
            else None,
            "primary_cause_top1_at_least_60_percent": primary["cause_top1_accuracy"] >= 0.60
            if primary
            else None,
        },
    }


def p1b_evaluation_to_json(summary: dict[str, Any]) -> str:
    return json.dumps(summary, indent=2) + "\n"


def p1b_evaluation_to_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# P1b Evaluation Summary",
        "",
        "P1b is a small injected-bug benchmark scaffold. It does not generate patches,",
        "handle large repositories, or implement adversarial bug generation.",
        "",
        "## Dataset",
        "",
        f"- total_variants: {summary['dataset']['total_variants']}",
        f"- buggy_variants: {summary['dataset']['buggy_variants']}",
        f"- clean_variants: {summary['dataset']['clean_variants']}",
        f"- primary_policy: {summary['primary_policy']}",
        "",
        "## Policy Metrics",
        "",
        "| policy | bug_discovery_rate | false_positive_rate | location_top3 | cause_top1 | fix_intent_top1 | mean_cost | mean_buggy_cost |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for policy, metrics in summary["policies"].items():
        lines.append(
            f"| {policy} | {metrics['bug_discovery_rate_within_budget']:.6f} | "
            f"{metrics['false_positive_rate_on_clean_cases']:.6f} | "
            f"{metrics['location_top3_accuracy']:.6f} | {metrics['cause_top1_accuracy']:.6f} | "
            f"{metrics['fix_intent_top1_accuracy']:.6f} | {metrics['mean_investigation_cost']:.6f} | "
            f"{metrics['mean_investigation_cost_buggy_only']:.6f} |"
        )
    lines.extend(["", "## Success Checks", ""])
    for key, value in summary["success_checks"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Notes",
            "",
            f"- Failure cost for undiscovered buggy variants is `{summary['settings']['failure_cost']}`.",
            "- Location metrics use function-level targets; line-span hints are secondary only.",
            "- P1b observations are synthesized from ground-truth variant metadata via discovery-action matching; they are not derived from executing the checkout code, except for two exception probes (`P1B-BUG-007`, `P1B-BUG-012`). Location, cause, and fix-intent metrics therefore measure action-selection efficiency on this scaffold, not real fault-localization ability.",
            "- All policies share the same stopping rules, so the comparison is primarily about action ordering.",
            "- The equal-cost/better-localization alternative clause is assessed manually.",
            "- `inspect_recent_diff` uses synthetic metadata, not real git commits or diffs.",
            "- `run_property_search` uses deterministic enumerated cases, not randomized Hypothesis-style generation.",
        ]
    )
    return "\n".join(lines) + "\n"
