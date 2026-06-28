"""Policy comparison and evaluation metrics."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from statistics import median
from typing import Any

from bug_cause_inference.bayes import rank_hypotheses, uniform_prior, update
from bug_cause_inference.likelihoods import CAUSES
from bug_cause_inference.models import SimulationResult, StopSettings, SyntheticCase
from bug_cause_inference.policies import POLICIES, PRIMARY_POLICY, run_investigation
from bug_cause_inference.reports import observation_influence_trace


def _initial_posterior(case: SyntheticCase) -> dict[str, float]:
    return update(uniform_prior(), case.initial_observations)


def posterior_at_step(case: SyntheticCase, result: SimulationResult, step: int) -> dict[str, float]:
    if step <= 0 or not result.trace:
        return _initial_posterior(case)
    if step <= len(result.trace):
        return result.trace[step - 1].updated_posterior
    return result.posterior


def cost_to_true_cause_top1(case: SyntheticCase, result: SimulationResult, settings: StopSettings) -> int:
    initial = _initial_posterior(case)
    if rank_hypotheses(initial)[0][0] == case.true_cause:
        return 0
    for trace in result.trace:
        if rank_hypotheses(trace.updated_posterior)[0][0] == case.true_cause:
            if trace.cumulative_cost <= settings.budget_limit:
                return trace.cumulative_cost
    return settings.failure_cost


def success_rate_by_budget(costs: list[int], budget_limit: int) -> dict[str, float]:
    return {
        str(budget): sum(1 for cost in costs if cost <= budget) / len(costs)
        for budget in range(1, budget_limit + 1)
    }


def area_under_budget_curve(curve: dict[str, float]) -> float:
    return sum(curve.values()) / len(curve)


def initial_dataset_diagnostics(cases: list[SyntheticCase]) -> dict[str, Any]:
    """Describe how informative the two initial observations are before actions."""

    top1_hits = 0
    top2_hits = 0
    initially_wrong_case_ids: list[str] = []
    by_category: dict[str, list[bool]] = defaultdict(list)
    for case in cases:
        ranked = rank_hypotheses(_initial_posterior(case))
        top_causes = [cause for cause, _ in ranked]
        top1_correct = top_causes[0] == case.true_cause
        top2_correct = case.true_cause in top_causes[:2]
        top1_hits += int(top1_correct)
        top2_hits += int(top2_correct)
        by_category[case.true_cause].append(top1_correct)
        if not top1_correct:
            initially_wrong_case_ids.append(case.case_id)

    category_summary = {
        cause: {
            "case_count": len(values),
            "initial_top1_accuracy": round(sum(values) / len(values), 6),
            "initially_wrong_case_count": len(values) - sum(values),
        }
        for cause, values in sorted(by_category.items())
    }
    return {
        "case_count": len(cases),
        "initial_top1_accuracy": round(top1_hits / len(cases), 6),
        "initial_top2_accuracy": round(top2_hits / len(cases), 6),
        "initially_wrong_case_count": len(initially_wrong_case_ids),
        "initially_wrong_case_ids": initially_wrong_case_ids,
        "category_summary": category_summary,
    }


def brier_score(results: list[SimulationResult]) -> float:
    total = 0.0
    for result in results:
        for cause in CAUSES:
            expected = 1.0 if cause == result.true_cause else 0.0
            total += (result.posterior[cause] - expected) ** 2
    return total / len(results)


def expected_calibration_error(results: list[SimulationResult], n_bins: int = 5) -> float:
    bins: list[list[tuple[float, float]]] = [[] for _ in range(n_bins)]
    for result in results:
        ranked = rank_hypotheses(result.posterior)
        confidence = ranked[0][1]
        accuracy = 1.0 if ranked[0][0] == result.true_cause else 0.0
        index = min(n_bins - 1, int(confidence * n_bins))
        bins[index].append((confidence, accuracy))

    ece = 0.0
    total = len(results)
    for bucket in bins:
        if not bucket:
            continue
        avg_confidence = sum(item[0] for item in bucket) / len(bucket)
        avg_accuracy = sum(item[1] for item in bucket) / len(bucket)
        ece += (len(bucket) / total) * abs(avg_confidence - avg_accuracy)
    return ece


def top_k_accuracy_by_step(
    cases: list[SyntheticCase],
    results: list[SimulationResult],
    max_steps: int,
    ks: tuple[int, ...] = (1, 2, 3),
) -> dict[str, dict[str, float]]:
    by_step: dict[str, dict[str, float]] = {}
    case_lookup = {case.case_id: case for case in cases}
    for step in range(0, max_steps + 1):
        step_metrics: dict[str, float] = {}
        for k in ks:
            hits = 0
            for result in results:
                case = case_lookup[result.case_id]
                ranked = rank_hypotheses(posterior_at_step(case, result, step))
                if case.true_cause in [cause for cause, _ in ranked[:k]]:
                    hits += 1
            step_metrics[f"top_{k}"] = hits / len(results)
        by_step[str(step)] = step_metrics
    return by_step


def explanation_omission_test(cases: list[SyntheticCase], results: list[SimulationResult]) -> dict[str, float]:
    case_lookup = {case.case_id: case for case in cases}
    tested = 0
    changed = 0
    for result in results:
        observations = result.observations
        if len(observations) < 2:
            continue
        influence = observation_influence_trace(observations)
        if not influence:
            continue
        most_influential = influence[0]["evidence_id"]
        reduced = []
        skipped = False
        for observation in observations:
            if observation.evidence_id == most_influential and not skipped:
                skipped = True
                continue
            reduced.append(observation)
        if not skipped:
            continue
        full_top = rank_hypotheses(result.posterior)[0][0]
        reduced_posterior = update(uniform_prior(), reduced) if reduced else uniform_prior()
        reduced_top = rank_hypotheses(reduced_posterior)[0][0]
        tested += 1
        if full_top != reduced_top:
            changed += 1
        _ = case_lookup[result.case_id]
    return {
        "tested_cases": float(tested),
        "top1_change_rate_when_most_influential_observation_omitted": changed / tested if tested else 0.0,
    }


def explanation_trace_completeness(results: list[SimulationResult]) -> float:
    total_steps = 0
    complete_steps = 0
    for result in results:
        if not result.trace:
            complete_steps += 1
            total_steps += 1
            continue
        for trace in result.trace:
            total_steps += 1
            if (
                trace.selected_action
                and trace.observation.evidence_id
                and trace.prior_posterior
                and trace.updated_posterior
                and trace.cumulative_cost >= trace.action_cost
            ):
                complete_steps += 1
    return complete_steps / total_steps if total_steps else 1.0


def wrong_stop_rate(results: list[SimulationResult]) -> float:
    confidence_stops = [
        result
        for result in results
        if result.stop_reason == "top_probability_threshold"
    ]
    if not confidence_stops:
        return 0.0
    wrong = sum(1 for result in confidence_stops if rank_hypotheses(result.posterior)[0][0] != result.true_cause)
    return wrong / len(confidence_stops)


def _performance_block(
    result_cost_pairs: list[tuple[SimulationResult, int]],
    settings: StopSettings,
) -> dict[str, Any]:
    if not result_cost_pairs:
        return {
            "num_runs": 0,
            "mean_cost_to_true_cause_top1": None,
            "median_cost_to_true_cause_top1": None,
            "success_rate_within_budget": None,
            "success_rate_by_budget": {},
            "area_under_budget_curve": None,
            "category_summary": {},
        }

    costs = [cost for _, cost in result_cost_pairs]
    successes = [cost <= settings.budget_limit for cost in costs]
    by_budget = success_rate_by_budget(costs, settings.budget_limit)
    by_category: dict[str, list[int]] = defaultdict(list)
    for result, cost in result_cost_pairs:
        by_category[result.true_cause].append(cost)

    category_summary = {
        cause: {
            "num_runs": len(values),
            "mean_cost_to_true_cause_top1": round(sum(values) / len(values), 6),
            "success_rate_within_budget": round(
                sum(1 for value in values if value <= settings.budget_limit) / len(values),
                6,
            ),
        }
        for cause, values in sorted(by_category.items())
    }
    return {
        "num_runs": len(result_cost_pairs),
        "mean_cost_to_true_cause_top1": round(sum(costs) / len(costs), 6),
        "median_cost_to_true_cause_top1": round(float(median(costs)), 6),
        "success_rate_within_budget": round(sum(successes) / len(successes), 6),
        "success_rate_by_budget": {key: round(value, 6) for key, value in by_budget.items()},
        "area_under_budget_curve": round(area_under_budget_curve(by_budget), 6),
        "category_summary": category_summary,
    }


def _policy_summary(
    cases: list[SyntheticCase],
    results: list[SimulationResult],
    settings: StopSettings,
) -> dict[str, Any]:
    case_lookup = {case.case_id: case for case in cases}
    costs = [cost_to_true_cause_top1(case_lookup[result.case_id], result, settings) for result in results]
    all_pairs = list(zip(results, costs, strict=True))
    initially_wrong_ids = {
        case.case_id
        for case in cases
        if rank_hypotheses(_initial_posterior(case))[0][0] != case.true_cause
    }
    initially_wrong_pairs = [
        (result, cost)
        for result, cost in all_pairs
        if result.case_id in initially_wrong_ids
    ]

    summary = _performance_block(all_pairs, settings)
    summary.update(
        {
        "top_k_accuracy_by_step": top_k_accuracy_by_step(cases, results, settings.max_steps),
        "brier_score": round(brier_score(results), 6),
        "expected_calibration_error": round(expected_calibration_error(results), 6),
        "explanation_omission_test": explanation_omission_test(cases, results),
        "explanation_trace_completeness": round(explanation_trace_completeness(results), 6),
        "wrong_stop_rate": round(wrong_stop_rate(results), 6),
            "initially_wrong_cases": _performance_block(initially_wrong_pairs, settings),
        }
    )
    return summary


def evaluate_policies(
    cases: list[SyntheticCase],
    policies: tuple[str, ...] = POLICIES,
    settings: StopSettings | None = None,
    random_repeats: int = 100,
) -> dict[str, Any]:
    settings = settings or StopSettings()
    summaries: dict[str, Any] = {}
    for policy in policies:
        results: list[SimulationResult] = []
        repeats = random_repeats if policy == "random" else 1
        for repeat in range(repeats):
            for case in cases:
                results.append(run_investigation(case, policy=policy, settings=settings, rng_seed=repeat))
        summaries[policy] = _policy_summary(cases, results, settings)

    primary = summaries.get(PRIMARY_POLICY)
    fixed = summaries.get("fixed_checklist")
    greedy = summaries.get("posterior_greedy")
    fixed_improvement = None
    if primary and fixed:
        fixed_mean = fixed["mean_cost_to_true_cause_top1"]
        fixed_improvement = (
            (fixed_mean - primary["mean_cost_to_true_cause_top1"]) / fixed_mean
            if fixed_mean
            else 0.0
        )
    greedy_delta = None
    if primary and greedy:
        greedy_delta = primary["mean_cost_to_true_cause_top1"] - greedy["mean_cost_to_true_cause_top1"]
    result = {
        "settings": {
            "budget_limit": settings.budget_limit,
            "max_steps": settings.max_steps,
            "failure_cost": settings.failure_cost,
            "top_probability_threshold": settings.top_probability_threshold,
            "top_margin_threshold": settings.top_margin_threshold,
            "min_expected_ig_per_cost": settings.min_expected_ig_per_cost,
        },
        "dataset_diagnostics": initial_dataset_diagnostics(cases),
        "policies": summaries,
        "success_checks": {
            "primary_policy": PRIMARY_POLICY,
            "fixed_checklist_cost_reduction": round(fixed_improvement, 6)
            if fixed_improvement is not None
            else None,
            "meets_15_percent_fixed_checklist_reduction": fixed_improvement >= 0.15
            if fixed_improvement is not None
            else None,
            "posterior_greedy_mean_cost_delta": round(greedy_delta, 6) if greedy_delta is not None else None,
            "primary_success_rate_at_least_80_percent": primary["success_rate_within_budget"] >= 0.80
            if primary
            else None,
            "primary_wrong_stop_rate": primary["wrong_stop_rate"] if primary else None,
            "primary_wrong_stop_rate_under_10_percent_diagnostic": primary["wrong_stop_rate"] < 0.10
            if primary
            else None,
        },
    }
    return result


def evaluation_to_json(summary: dict[str, Any]) -> str:
    return json.dumps(summary, indent=2) + "\n"


def evaluation_to_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Evaluation Summary",
        "",
        "## Dataset Diagnostics",
        "",
        f"- case_count: {summary['dataset_diagnostics']['case_count']}",
        f"- initial_top1_accuracy: {summary['dataset_diagnostics']['initial_top1_accuracy']:.6f}",
        f"- initial_top2_accuracy: {summary['dataset_diagnostics']['initial_top2_accuracy']:.6f}",
        f"- initially_wrong_case_count: {summary['dataset_diagnostics']['initially_wrong_case_count']}",
        "",
        "## Policy Comparison",
        "",
        "| policy | mean_cost_to_true_cause_top1 | success_rate_within_budget | brier_score | wrong_stop_rate |",
        "|---|---:|---:|---:|---:|",
    ]
    for policy, metrics in summary["policies"].items():
        lines.append(
            f"| {policy} | {metrics['mean_cost_to_true_cause_top1']:.6f} | "
            f"{metrics['success_rate_within_budget']:.6f} | {metrics['brier_score']:.6f} | "
            f"{metrics['wrong_stop_rate']:.6f} |"
        )
    lines.extend(
        [
            "",
            "## Initially Wrong Cases",
            "",
            "| policy | num_runs | mean_cost_to_true_cause_top1 | success_rate_within_budget |",
            "|---|---:|---:|---:|",
        ]
    )
    for policy, metrics in summary["policies"].items():
        wrong = metrics["initially_wrong_cases"]
        lines.append(
            f"| {policy} | {wrong['num_runs']} | {wrong['mean_cost_to_true_cause_top1']} | "
            f"{wrong['success_rate_within_budget']} |"
        )
    lines.extend(
        [
            "",
            "## Success Checks",
            "",
        ]
    )
    for key, value in summary["success_checks"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Failure to reach true-cause top-1 within budget is scored with the configured failure cost.",
            "- Wrong stop rate means stopping on a high-confidence but incorrect cause hypothesis.",
            "- The wrong-stop diagnostic threshold is surfaced as a caution signal, not as a hard validity claim.",
            "- These results use synthetic cases and a fixed likelihood table.",
        ]
    )
    return "\n".join(lines) + "\n"


def save_evaluation(summary: dict[str, Any], json_path: str | Path, markdown_path: str | Path) -> None:
    Path(json_path).write_text(evaluation_to_json(summary), encoding="utf-8")
    Path(markdown_path).write_text(evaluation_to_markdown(summary), encoding="utf-8")
