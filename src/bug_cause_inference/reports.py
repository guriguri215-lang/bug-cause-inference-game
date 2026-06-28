"""DecisionReport JSON and Markdown rendering."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bug_cause_inference.bayes import rank_hypotheses, uniform_prior, update
from bug_cause_inference.likelihoods import ACTION_SPECS
from bug_cause_inference.models import HypothesisScore, Observation, SimulationResult, StopSettings, SyntheticCase
from bug_cause_inference.policies import PRIMARY_POLICY, check_stop, choose_action, score_actions

KNOWN_LIMITS = [
    "This report does not identify a code location.",
    "This report does not propose or generate a patch.",
    "The recommendation depends on the synthetic likelihood table.",
]


def top_hypotheses(posterior: dict[str, float], limit: int = 5) -> list[HypothesisScore]:
    return [
        HypothesisScore(rank=index, hypothesis=cause, posterior_probability=round(probability, 6))
        for index, (cause, probability) in enumerate(rank_hypotheses(posterior)[:limit], start=1)
    ]


def observation_influence_trace(observations: list[Observation]) -> list[dict[str, Any]]:
    if not observations:
        return []
    full = update(uniform_prior(), observations)
    full_top = rank_hypotheses(full)[0][0]
    trace = []
    for index, observation in enumerate(observations):
        reduced = [item for item_index, item in enumerate(observations) if item_index != index]
        reduced_posterior = update(uniform_prior(), reduced) if reduced else uniform_prior()
        reduced_top, reduced_probability = rank_hypotheses(reduced_posterior)[0]
        full_probability_for_top = full[full_top]
        reduced_probability_for_full_top = reduced_posterior[full_top]
        trace.append(
            {
                "observation_index": index,
                "evidence_id": observation.evidence_id,
                "type": observation.type,
                "top_with_all_evidence": full_top,
                "top_without_this_evidence": reduced_top,
                "top_changed": reduced_top != full_top,
                "full_top_probability_delta": round(full_probability_for_top - reduced_probability_for_full_top, 6),
                "top_without_probability": round(reduced_probability, 6),
            }
        )
    return sorted(trace, key=lambda item: (-abs(item["full_top_probability_delta"]), item["evidence_id"]))


def counterfactual_notes(observations: list[Observation], recommended_action: str | None) -> list[str]:
    influence = observation_influence_trace(observations)
    notes: list[str] = []
    seen_evidence: set[str] = set()
    unique_influence = []
    for item in influence:
        if item["evidence_id"] in seen_evidence:
            continue
        seen_evidence.add(item["evidence_id"])
        unique_influence.append(item)
    for item in unique_influence[:2]:
        if item["top_changed"]:
            notes.append(
                f"Without `{item['evidence_id']}`, the top hypothesis would shift to "
                f"`{item['top_without_this_evidence']}`."
            )
        else:
            notes.append(
                f"Removing `{item['evidence_id']}` changes the current top hypothesis probability by "
                f"{item['full_top_probability_delta']:.3f}."
            )
    if recommended_action is not None:
        notes.append(
            f"The recommended action `{recommended_action}` is selected to reduce uncertainty among the current top causes."
        )
    return notes


def _why_action(report_policy: str, posterior: dict[str, float], action_scores: list[dict[str, Any]], action: str | None) -> str:
    ranked = rank_hypotheses(posterior)
    if action is None:
        return "No next action is recommended because a stopping condition was reached."
    matching = next(item for item in action_scores if item["action"] == action)
    top_names = ", ".join(cause for cause, _ in ranked[:2])
    return (
        f"Policy `{report_policy}` selected `{action}` because it has expected information gain per cost "
        f"{matching['expected_information_gain_per_cost']:.3f} at cost {matching['cost']}, "
        f"while the current leading hypotheses are {top_names}."
    )


def build_decision_report(
    case: SyntheticCase,
    result: SimulationResult | None = None,
    policy: str = PRIMARY_POLICY,
    settings: StopSettings | None = None,
) -> dict[str, Any]:
    settings = settings or StopSettings()
    if result is None:
        observations = list(case.initial_observations)
        posterior = update(uniform_prior(), observations)
        executed_actions: list[str] = []
        cumulative_cost = 0
        current_step = 0
        stop_reason = check_stop(posterior, cumulative_cost, current_step, executed_actions, settings)
        trace = []
    else:
        observations = result.observations
        posterior = result.posterior
        executed_actions = result.executed_actions
        cumulative_cost = result.cumulative_cost
        current_step = result.current_step
        stop_reason = result.stop_reason
        trace = [item.to_dict() for item in result.trace]
        policy = result.policy

    remaining_budget = settings.budget_limit - cumulative_cost
    action_scores = score_actions(posterior, executed_actions, remaining_budget)
    if stop_reason is None and policy != "static_posterior":
        recommended_action = choose_action(policy, posterior, executed_actions, remaining_budget=remaining_budget)
    else:
        recommended_action = None

    selected_score = next((item for item in action_scores if item["action"] == recommended_action), None)
    report = {
        "case_id": case.case_id,
        "current_step": current_step,
        "stop_or_continue": "stop" if recommended_action is None else "continue",
        "stop_reason": stop_reason if recommended_action is None else None,
        "recommended_next_action": recommended_action,
        "expected_cost": ACTION_SPECS[recommended_action].cost if recommended_action is not None else None,
        "expected_information_gain_per_cost": (
            selected_score["expected_information_gain_per_cost"] if selected_score is not None else None
        ),
        "current_top_hypotheses": [item.to_dict() for item in top_hypotheses(posterior)],
        "why_this_action": _why_action(policy, posterior, action_scores, recommended_action),
        "counterfactual_notes": counterfactual_notes(observations, recommended_action),
        "known_limits": KNOWN_LIMITS,
        "policy": policy,
        "cumulative_cost": cumulative_cost,
        "observed_evidence_ids": [item.evidence_id for item in observations],
        "executed_actions": list(executed_actions),
        "action_scores": action_scores,
        "observation_influence_trace": observation_influence_trace(observations),
        "trace": trace,
    }
    return report


def report_to_json(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=2) + "\n"


def report_to_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# DecisionReport: {report['case_id']}",
        "",
        "## Summary",
        "",
        f"- case_id: {report['case_id']}",
        f"- current_step: {report['current_step']}",
        f"- stop_or_continue: {report['stop_or_continue']}",
        f"- stop_reason: {report['stop_reason']}",
        f"- recommended_next_action: {report['recommended_next_action']}",
        f"- expected_cost: {report['expected_cost']}",
        f"- expected_information_gain_per_cost: {report['expected_information_gain_per_cost']}",
        "",
        "## Current Hypotheses",
        "",
        "| rank | hypothesis | posterior_probability |",
        "|---:|---|---:|",
    ]
    for item in report["current_top_hypotheses"]:
        lines.append(f"| {item['rank']} | {item['hypothesis']} | {item['posterior_probability']:.6f} |")
    lines.extend(
        [
            "",
            "## Why This Action",
            "",
            report["why_this_action"],
            "",
            "## Counterfactual Notes",
            "",
        ]
    )
    lines.extend(f"- {note}" for note in report["counterfactual_notes"])
    lines.extend(
        [
            "",
            "## Known Limits",
            "",
        ]
    )
    lines.extend(f"- {limit}" for limit in report["known_limits"])
    return "\n".join(lines) + "\n"


def save_report(report: dict[str, Any], json_path: str | Path, markdown_path: str | Path) -> None:
    Path(json_path).write_text(report_to_json(report), encoding="utf-8")
    Path(markdown_path).write_text(report_to_markdown(report), encoding="utf-8")
