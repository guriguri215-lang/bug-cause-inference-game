"""Deterministic JSON and Markdown reports for the P2h audit."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bug_cause_inference.p2h.task_scheduler_replication import (
    AUDIT_ID,
    FORMAL_POLICY_IDS,
    validate_summary,
)


def render_json(summary: dict[str, Any]) -> str:
    validate_summary(summary)
    return json.dumps(summary, ensure_ascii=False, allow_nan=False, indent=2) + "\n"


def _rate(metric: dict[str, Any]) -> str:
    rate = "undefined" if metric["rate"] is None else f"{metric['rate']:.6f}"
    return f"{metric['successes']}/{metric['denominator']} ({rate})"


def render_markdown(summary: dict[str, Any]) -> str:
    validate_summary(summary)
    overall = summary["aggregates"]["overall"]
    lines = [
        "# P2h task-scheduler second-domain replication audit",
        "",
        "## Boundary",
        "",
        "This is an analysis-only, fixed-input, hand-authored, non-IID, non-causal, "
        "non-deployable observation in one toy task-scheduler domain. It does not establish "
        "policy superiority, population generalization, or production scheduler properties.",
        "",
        "## Frozen support",
        "",
        "- Inputs: 10 buggy and 5 benign clean inputs.",
        "- Policies: six accepted formal policies in their accepted order.",
        "- Actions: ten accepted action IDs with accepted costs and semantics.",
        "- Trajectories: 60 buggy plus 30 clean rows, normal execution only.",
        "",
        "## Descriptive result",
        "",
        f"- Bug discovery: {_rate(overall['bug_discovery'])}",
        f"- First failure observed: {_rate(overall['first_failure_observed'])}",
        f"- Clean false positive: {_rate(overall['clean_false_positive'])}",
        f"- Function location top-1: {_rate(overall['location_top1'])}",
        f"- Function location top-3: {_rate(overall['location_top3'])}",
        f"- Function location MRR: {overall['location_mrr']} "
        f"(denominator {overall['location_mrr_denominator']})",
        f"- Cause top-1: {_rate(overall['cause_top1'])}",
        f"- Fix-intent top-1: {_rate(overall['fix_intent_top1'])}",
        f"- Mean penalized cost to first failure: {overall['mean_cost_to_first_failure_with_penalty']}",
        f"- Mean cumulative cost: {overall['mean_cumulative_cost']}",
        "",
        "## Per-policy description",
        "",
        "| Policy | Bug discovery | Clean FP | Location top-3 | Cause top-1 | Fix top-1 | Mean cost |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for policy in FORMAL_POLICY_IDS:
        item = summary["aggregates"]["by_policy"][policy]
        lines.append(
            f"| `{policy}` | {_rate(item['bug_discovery'])} | "
            f"{_rate(item['clean_false_positive'])} | {_rate(item['location_top3'])} | "
            f"{_rate(item['cause_top1'])} | {_rate(item['fix_intent_top1'])} | "
            f"{item['mean_cumulative_cost']} |"
        )
    lines.extend(
        [
            "",
            "## Identity",
            "",
            f"- Schema: `{summary['schema_version']}`",
            f"- Domain manifest: `{summary['identities']['manifest_digest']}`",
            f"- Accepted dependency identity: `{summary['identities']['dependency_digest']}`",
            f"- Pre-outcome freeze identity: `{summary['identities']['freeze_identity_digest']}`",
            f"- Row digest: `{summary['identities']['row_digest']}`",
            f"- Aggregate digest: `{summary['identities']['aggregate_digest']}`",
            f"- Summary digest: `{summary['summary_digest']}`",
            "",
            "The JSON artifact is authoritative for per-input, per-family, per-policy, raw trace, "
            "denominator, terminal-partition, and identity details.",
            "",
        ]
    )
    return "\n".join(lines)


def write_report_pair(summary: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    validate_summary(summary)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{AUDIT_ID}.json"
    markdown_path = output_dir / f"{AUDIT_ID}.md"
    json_path.write_text(render_json(summary), encoding="utf-8", newline="\n")
    markdown_path.write_text(render_markdown(summary), encoding="utf-8", newline="\n")
    return json_path, markdown_path
