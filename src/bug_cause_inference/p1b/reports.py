"""JSON and Markdown rendering for P1b reports."""

from __future__ import annotations

import json
from typing import Any

from bug_cause_inference.p1b.dataset import load_p1b_variants
from bug_cause_inference.p1b.models import P1BRunResult, P1BSettings, P1BVariant, rank_distribution
from bug_cause_inference.p1b.policies import P1B_PRIMARY_POLICY, run_p1b_investigation


P1B_KNOWN_LIMITS = [
    "P1b is a small injected-bug benchmark scaffold, not a real-code production debugger.",
    "P1b ranks function-level locations; line spans are explanatory hints only.",
    "P1b predicts fix-intent categories but does not generate patches.",
    "P1b keeps metadata-synth recent-diff evidence synthetic; execution-grounded mode reads Phase C real-diff artifacts.",
]


def _top_items(distribution: dict[str, float], limit: int = 5) -> list[dict[str, Any]]:
    return [
        {"rank": index, "label": label, "probability": round(probability, 6)}
        for index, (label, probability) in enumerate(rank_distribution(distribution)[:limit], start=1)
    ]


def build_p1b_report(
    variant: P1BVariant,
    policy: str = P1B_PRIMARY_POLICY,
    settings: P1BSettings | None = None,
    observation_mode: str = "metadata_synth",
) -> dict[str, Any]:
    settings = settings or P1BSettings()
    result = run_p1b_investigation(variant, policy=policy, settings=settings, observation_mode=observation_mode)
    return {
        "variant": variant.to_dict(),
        "policy": policy,
        "observation_mode": observation_mode,
        "stop_or_continue": "stop",
        "stop_reason": result.stop_reason,
        "recommended_next_action": None,
        "bug_detected": result.bug_detected,
        "reproduction_input": result.reproduction_input,
        "bug_presence_posterior": round(result.bug_presence_posterior, 6),
        "location_ranking": _top_items(result.location_posterior, limit=5),
        "cause_posterior": _top_items(result.cause_posterior, limit=5),
        "fix_intent_prediction": _top_items(result.fix_intent_posterior, limit=5),
        "cumulative_cost": result.cumulative_cost,
        "current_step": result.current_step,
        "executed_actions": list(result.executed_actions),
        "trace": [item.to_dict() for item in result.trace],
        "known_limits": P1B_KNOWN_LIMITS,
    }


def p1b_report_to_json(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=2) + "\n"


def p1b_report_to_markdown(report: dict[str, Any]) -> str:
    variant = report["variant"]
    lines = [
        f"# P1b Report: {variant['variant_id']}",
        "",
        "## Summary",
        "",
        f"- policy: {report['policy']}",
        f"- observation_mode: {report.get('observation_mode', 'metadata_synth')}",
        f"- is_buggy: {variant['is_buggy']}",
        f"- stop_reason: {report['stop_reason']}",
        f"- bug_detected: {report['bug_detected']}",
        f"- reproduction_input: {report['reproduction_input']}",
        f"- cumulative_cost: {report['cumulative_cost']}",
        f"- current_step: {report['current_step']}",
    ]
    if variant["is_buggy"]:
        lines.extend(
            [
                f"- true_cause_category: {variant['true_cause_category']}",
                f"- target_location: {variant['target_module'].removesuffix('.py')}.{variant['target_function']}",
                f"- fix_intent_category: {variant['fix_intent_category']}",
            ]
        )
    else:
        lines.append(f"- covered_spec_area: {variant['covered_spec_area']}")
    lines.extend(
        [
            "",
            "## Location Ranking",
            "",
            "| rank | location | probability |",
            "|---:|---|---:|",
        ]
    )
    for item in report["location_ranking"]:
        lines.append(f"| {item['rank']} | {item['label']} | {item['probability']:.6f} |")
    lines.extend(["", "## Cause Posterior", "", "| rank | cause | probability |", "|---:|---|---:|"])
    for item in report["cause_posterior"]:
        lines.append(f"| {item['rank']} | {item['label']} | {item['probability']:.6f} |")
    lines.extend(["", "## Fix-Intent Prediction", "", "| rank | fix_intent | probability |", "|---:|---|---:|"])
    for item in report["fix_intent_prediction"]:
        lines.append(f"| {item['rank']} | {item['label']} | {item['probability']:.6f} |")
    lines.extend(["", "## Executed Actions", ""])
    lines.extend(f"- {action}" for action in report["executed_actions"])
    coverage_steps = [
        step
        for step in report["trace"]
        if step["selected_action"] == "inspect_coverage_spectrum"
        and step["observation"].get("coverage_suspicion")
    ]
    if coverage_steps:
        lines.extend(
            [
                "",
                "## Coverage Spectrum",
                "",
                "| step | function | ochiai | failed | passed | total_failed |",
                "|---:|---|---:|---:|---:|---:|",
            ]
        )
        for step in coverage_steps:
            observation = step["observation"]
            counts = observation.get("coverage_counts", {})
            ranked = sorted(
                observation["coverage_suspicion"].items(),
                key=lambda item: (-item[1], item[0]),
            )[:5]
            for function, suspicion in ranked:
                values = counts.get(function, {})
                lines.append(
                    f"| {step['step']} | {function} | {suspicion:.6f} | "
                    f"{values.get('failed', 0)} | {values.get('passed', 0)} | "
                    f"{values.get('total_failed', 0)} |"
                )
    recent_diff_steps = [
        step
        for step in report["trace"]
        if step["selected_action"] == "inspect_recent_diff"
        and step["observation"].get("changed_files")
    ]
    if recent_diff_steps:
        lines.extend(
            [
                "",
                "## Recent Diff Artifact",
                "",
                "| step | patch | changed_files | changed_functions |",
                "|---:|---|---|---|",
            ]
        )
        for step in recent_diff_steps:
            observation = step["observation"]
            changed_files = ", ".join(observation.get("changed_files", []))
            changed_functions = ", ".join(observation.get("changed_functions", []))
            lines.append(
                f"| {step['step']} | {observation.get('diff_artifact_path', '')} | "
                f"{changed_files} | {changed_functions} |"
            )
            diff_excerpt = observation.get("diff_excerpt")
            if diff_excerpt:
                lines.extend(["", f"### Diff Excerpt: Step {step['step']}", "", "```diff"])
                lines.extend(diff_excerpt.splitlines())
                lines.append("```")
    lines.extend(["", "## Known Limits", ""])
    lines.extend(f"- {limit}" for limit in report["known_limits"])
    return "\n".join(lines) + "\n"


def p1b_variants_to_json(variants: list[P1BVariant] | None = None) -> str:
    return json.dumps([variant.to_dict() for variant in (variants or load_p1b_variants())], indent=2) + "\n"


def p1b_variants_to_markdown(variants: list[P1BVariant] | None = None) -> str:
    variants = variants or load_p1b_variants()
    lines = [
        "# P1b Variants",
        "",
        "| variant_id | is_buggy | cause_or_area | target_location | primary_action | difficulty |",
        "|---|---:|---|---|---|---|",
    ]
    for variant in variants:
        cause_or_area = variant.true_cause_category if variant.is_buggy else variant.covered_spec_area
        target = variant.target_location or ""
        primary = variant.primary_discovery_action or ""
        difficulty = variant.difficulty or ""
        lines.append(
            f"| {variant.variant_id} | {str(variant.is_buggy).lower()} | {cause_or_area} | "
            f"{target} | {primary} | {difficulty} |"
        )
    return "\n".join(lines) + "\n"
