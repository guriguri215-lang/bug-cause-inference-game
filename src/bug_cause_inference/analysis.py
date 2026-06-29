"""Analysis-only reports for P1a evaluation diagnostics."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

from bug_cause_inference.bayes import rank_hypotheses, uniform_prior, update
from bug_cause_inference.evaluation import cost_to_true_cause_top1
from bug_cause_inference.models import SimulationResult, StopSettings, SyntheticCase
from bug_cause_inference.policies import POLICIES, run_investigation

ANALYSIS_POLICIES: tuple[str, ...] = POLICIES
THRESHOLD_SWEEP_POLICIES: tuple[str, ...] = ("information_gain_per_cost", "fixed_checklist")
TOP_PROBABILITY_THRESHOLDS: tuple[float, ...] = (0.70, 0.75, 0.80, 0.85, 0.90)
TOP_MARGIN_THRESHOLDS: tuple[float, ...] = (0.10, 0.15, 0.20, 0.25)


def _initial_posterior(case: SyntheticCase) -> dict[str, float]:
    return update(uniform_prior(), case.initial_observations)


def _ranked_summary(posterior: dict[str, float]) -> dict[str, Any]:
    ranked = rank_hypotheses(posterior)
    top_hypothesis, top_probability = ranked[0]
    second_hypothesis, second_probability = ranked[1]
    return {
        "top_hypothesis": top_hypothesis,
        "top_probability": round(top_probability, 6),
        "top2_hypothesis": second_hypothesis,
        "top2_probability": round(second_probability, 6),
        "top_margin": round(top_probability - second_probability, 6),
    }


def _is_wrong_stop(result: SimulationResult) -> bool:
    return (
        result.stop_reason == "top_probability_threshold"
        and rank_hypotheses(result.posterior)[0][0] != result.true_cause
    )


def _wrong_stop_rate(results: list[SimulationResult]) -> float:
    confidence_stops = [
        result
        for result in results
        if result.stop_reason == "top_probability_threshold"
    ]
    if not confidence_stops:
        return 0.0
    return sum(_is_wrong_stop(result) for result in confidence_stops) / len(confidence_stops)


def _success(cost: int, settings: StopSettings) -> bool:
    return cost <= settings.budget_limit


def _run_policy_grid(
    cases: list[SyntheticCase],
    policies: tuple[str, ...],
    settings: StopSettings,
) -> list[tuple[SyntheticCase, SimulationResult, int]]:
    rows: list[tuple[SyntheticCase, SimulationResult, int]] = []
    case_by_id = {case.case_id: case for case in cases}
    for policy in policies:
        for case in cases:
            result = run_investigation(case, policy=policy, settings=settings, rng_seed=0)
            rows.append((case_by_id[result.case_id], result, cost_to_true_cause_top1(case, result, settings)))
    return rows


def wrong_stop_case_report(
    runs: list[tuple[SyntheticCase, SimulationResult, int]],
) -> list[dict[str, Any]]:
    report = []
    for case, result, _ in runs:
        if not _is_wrong_stop(result):
            continue
        ranked = _ranked_summary(result.posterior)
        report.append(
            {
                "case_id": case.case_id,
                "true_cause": case.true_cause,
                "policy": result.policy,
                "final_top_hypothesis": ranked["top_hypothesis"],
                "final_posterior_probability": ranked["top_probability"],
                "top2_hypothesis": ranked["top2_hypothesis"],
                "top1_top2_margin": ranked["top_margin"],
                "cumulative_cost": result.cumulative_cost,
                "current_step": result.current_step,
                "stop_reason": result.stop_reason,
                "executed_actions": result.executed_actions,
                "observed_evidence_ids": [observation.evidence_id for observation in result.observations],
            }
        )
    return sorted(report, key=lambda item: (item["policy"], item["case_id"]))


def initially_wrong_failure_report(
    cases: list[SyntheticCase],
    runs: list[tuple[SyntheticCase, SimulationResult, int]],
    settings: StopSettings,
) -> list[dict[str, Any]]:
    initial_by_case: dict[str, dict[str, Any]] = {}
    for case in cases:
        ranked = rank_hypotheses(_initial_posterior(case))
        if ranked[0][0] == case.true_cause:
            continue
        initial_by_case[case.case_id] = {
            "initial_top_hypothesis": ranked[0][0],
            "initial_top_probability": round(ranked[0][1], 6),
        }

    rows = []
    for case, result, cost in runs:
        if case.case_id not in initial_by_case:
            continue
        final = _ranked_summary(result.posterior)
        rows.append(
            {
                "case_id": case.case_id,
                "true_cause": case.true_cause,
                "initial_top_hypothesis": initial_by_case[case.case_id]["initial_top_hypothesis"],
                "initial_top_probability": initial_by_case[case.case_id]["initial_top_probability"],
                "policy": result.policy,
                "final_top_hypothesis": final["top_hypothesis"],
                "final_top_probability": final["top_probability"],
                "cost_to_true_cause_top1": cost,
                "success_within_budget": _success(cost, settings),
                "stop_reason": result.stop_reason,
                "executed_actions": result.executed_actions,
            }
        )
    return sorted(rows, key=lambda item: (item["case_id"], item["policy"]))


def stop_reason_summary(
    runs: list[tuple[SyntheticCase, SimulationResult, int]],
) -> list[dict[str, Any]]:
    by_policy: dict[str, list[SimulationResult]] = defaultdict(list)
    for _, result, _ in runs:
        by_policy[result.policy].append(result)

    rows = []
    for policy, results in sorted(by_policy.items()):
        counts = Counter(result.stop_reason for result in results)
        wrong_counts = Counter(result.stop_reason for result in results if _is_wrong_stop(result))
        for reason, count in sorted(counts.items()):
            wrong_count = wrong_counts[reason]
            rows.append(
                {
                    "policy": policy,
                    "stop_reason": reason,
                    "count": count,
                    "rate": round(count / len(results), 6),
                    "wrong_stop_count": wrong_count,
                    "wrong_stop_rate_within_reason": round(wrong_count / count, 6) if count else 0.0,
                }
            )
    return rows


def category_failure_summary(
    cases: list[SyntheticCase],
    runs: list[tuple[SyntheticCase, SimulationResult, int]],
    settings: StopSettings,
) -> list[dict[str, Any]]:
    initially_wrong_ids = {
        case.case_id
        for case in cases
        if rank_hypotheses(_initial_posterior(case))[0][0] != case.true_cause
    }
    grouped: dict[tuple[str, str], list[tuple[SyntheticCase, SimulationResult, int]]] = defaultdict(list)
    for row in runs:
        case, result, _ = row
        grouped[(result.policy, case.true_cause)].append(row)

    rows = []
    for (policy, true_cause), items in sorted(grouped.items()):
        costs = [cost for _, _, cost in items]
        successes = [_success(cost, settings) for cost in costs]
        results = [result for _, result, _ in items]
        initially_wrong_items = [item for item in items if item[0].case_id in initially_wrong_ids]
        initially_wrong_successes = [
            _success(cost, settings)
            for _, _, cost in initially_wrong_items
        ]
        rows.append(
            {
                "policy": policy,
                "true_cause": true_cause,
                "num_cases": len(items),
                "mean_cost_to_true_cause_top1": round(mean(costs), 6),
                "success_rate_within_budget": round(sum(successes) / len(successes), 6),
                "wrong_stop_rate": round(_wrong_stop_rate(results), 6),
                "initially_wrong_success_rate": round(
                    sum(initially_wrong_successes) / len(initially_wrong_successes),
                    6,
                )
                if initially_wrong_successes
                else None,
            }
        )
    return rows


def threshold_sweep(
    cases: list[SyntheticCase],
) -> list[dict[str, Any]]:
    rows = []
    initially_wrong_ids = {
        case.case_id
        for case in cases
        if rank_hypotheses(_initial_posterior(case))[0][0] != case.true_cause
    }
    for policy in THRESHOLD_SWEEP_POLICIES:
        for top_probability_threshold in TOP_PROBABILITY_THRESHOLDS:
            for top_margin_threshold in TOP_MARGIN_THRESHOLDS:
                settings = StopSettings(
                    top_probability_threshold=top_probability_threshold,
                    top_margin_threshold=top_margin_threshold,
                    budget_limit=10,
                    max_steps=5,
                    min_expected_ig_per_cost=0.03,
                )
                results = [
                    run_investigation(case, policy=policy, settings=settings, rng_seed=0)
                    for case in cases
                ]
                cost_rows = [
                    (case, result, cost_to_true_cause_top1(case, result, settings))
                    for case, result in zip(cases, results, strict=True)
                ]
                costs = [cost for _, _, cost in cost_rows]
                initially_wrong_costs = [
                    cost
                    for case, _, cost in cost_rows
                    if case.case_id in initially_wrong_ids
                ]
                rows.append(
                    {
                        "policy": policy,
                        "top_probability_threshold": top_probability_threshold,
                        "top_margin_threshold": top_margin_threshold,
                        "mean_cost_to_true_cause_top1": round(mean(costs), 6),
                        "success_rate_within_budget": round(
                            sum(_success(cost, settings) for cost in costs) / len(costs),
                            6,
                        ),
                        "wrong_stop_rate": round(_wrong_stop_rate(results), 6),
                        "initially_wrong_success_rate": round(
                            sum(_success(cost, settings) for cost in initially_wrong_costs)
                            / len(initially_wrong_costs),
                            6,
                        ),
                        "initially_wrong_mean_cost": round(mean(initially_wrong_costs), 6),
                    }
                )
    return rows


def build_analysis_summary(
    cases: list[SyntheticCase],
    policies: tuple[str, ...] = ANALYSIS_POLICIES,
    settings: StopSettings | None = None,
) -> dict[str, Any]:
    settings = settings or StopSettings()
    runs = _run_policy_grid(cases, policies, settings)
    return {
        "analysis_scope": {
            "kind": "analysis_only_patch",
            "model_or_dataset_changed": False,
            "default_stop_thresholds_changed": False,
            "notes": [
                "This report analyzes existing P1a behavior without tuning the dataset or policies.",
                "It does not add real-code bug discovery, code localization, patch generation, adversarial modeling, or regret/bandit learning.",
            ],
        },
        "settings": {
            "budget_limit": settings.budget_limit,
            "max_steps": settings.max_steps,
            "failure_cost": settings.failure_cost,
            "top_probability_threshold": settings.top_probability_threshold,
            "top_margin_threshold": settings.top_margin_threshold,
            "min_expected_ig_per_cost": settings.min_expected_ig_per_cost,
        },
        "policies": list(policies),
        "wrong_stop_cases": wrong_stop_case_report(runs),
        "initially_wrong_cases": initially_wrong_failure_report(cases, runs, settings),
        "stop_reason_summary": stop_reason_summary(runs),
        "category_failure_summary": category_failure_summary(cases, runs, settings),
        "threshold_sweep": threshold_sweep(cases),
    }


def analysis_to_json(summary: dict[str, Any]) -> str:
    return json.dumps(summary, indent=2) + "\n"


def _markdown_table(headers: list[str], rows: list[dict[str, Any]]) -> list[str]:
    lines = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(header, "")) for header in headers) + " |")
    return lines


def analysis_to_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# P1a Analysis Summary",
        "",
        "## Scope",
        "",
        "- This is an analysis-only patch.",
        "- The model, dataset, default thresholds, and main policy are unchanged.",
        "- This report surfaces wrong stops, initially-wrong cases, stop reasons, category failures, and threshold-sweep tradeoffs.",
        "- P1b/P1c features are not implemented here.",
        "",
        "## Wrong-Stop Cases",
        "",
    ]
    wrong_stop_headers = [
        "case_id",
        "true_cause",
        "policy",
        "final_top_hypothesis",
        "final_posterior_probability",
        "top2_hypothesis",
        "top1_top2_margin",
        "cumulative_cost",
        "current_step",
        "stop_reason",
    ]
    lines.extend(_markdown_table(wrong_stop_headers, summary["wrong_stop_cases"]))
    lines.extend(
        [
            "",
            "## Initially-Wrong Cases",
            "",
        ]
    )
    initial_headers = [
        "case_id",
        "true_cause",
        "initial_top_hypothesis",
        "initial_top_probability",
        "policy",
        "final_top_hypothesis",
        "final_top_probability",
        "cost_to_true_cause_top1",
        "success_within_budget",
        "stop_reason",
    ]
    lines.extend(_markdown_table(initial_headers, summary["initially_wrong_cases"]))
    lines.extend(
        [
            "",
            "## Stop Reason Summary",
            "",
        ]
    )
    stop_headers = [
        "policy",
        "stop_reason",
        "count",
        "rate",
        "wrong_stop_count",
        "wrong_stop_rate_within_reason",
    ]
    lines.extend(_markdown_table(stop_headers, summary["stop_reason_summary"]))
    lines.extend(
        [
            "",
            "## Category Failure Summary",
            "",
        ]
    )
    category_headers = [
        "policy",
        "true_cause",
        "num_cases",
        "mean_cost_to_true_cause_top1",
        "success_rate_within_budget",
        "wrong_stop_rate",
        "initially_wrong_success_rate",
    ]
    lines.extend(_markdown_table(category_headers, summary["category_failure_summary"]))
    lines.extend(
        [
            "",
            "## Threshold Sweep",
            "",
        ]
    )
    sweep_headers = [
        "policy",
        "top_probability_threshold",
        "top_margin_threshold",
        "mean_cost_to_true_cause_top1",
        "success_rate_within_budget",
        "wrong_stop_rate",
        "initially_wrong_success_rate",
        "initially_wrong_mean_cost",
    ]
    lines.extend(_markdown_table(sweep_headers, summary["threshold_sweep"]))
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Wrong stop means a high-confidence stop on an incorrect top hypothesis.",
            "- The threshold sweep is diagnostic only and does not change default thresholds.",
            "- These results remain synthetic and should not be interpreted as real-world debugging accuracy.",
        ]
    )
    return "\n".join(lines) + "\n"


def save_analysis(summary: dict[str, Any], json_path: str | Path | None, markdown_path: str | Path | None) -> None:
    if json_path is not None:
        Path(json_path).write_text(analysis_to_json(summary), encoding="utf-8")
    if markdown_path is not None:
        Path(markdown_path).write_text(analysis_to_markdown(summary), encoding="utf-8")
