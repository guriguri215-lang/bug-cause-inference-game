"""Deterministic JSON and Markdown serializers for the P2c trajectory audit."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bug_cause_inference.p2c.trajectory_audit import (
    INVALID_STATUS,
    P2CTrajectoryAuditError,
    record_artifacts_serialized,
    validate_audit_summary,
)


_SUMMARY_BEGIN = "<!-- P2C_VALIDATED_SUMMARY_BEGIN -->"
_SUMMARY_END = "<!-- P2C_VALIDATED_SUMMARY_END -->"


def p2c_summary_to_json(summary: dict[str, Any]) -> str:
    """Serialize a validated audit as stable newline-terminated JSON."""

    validate_audit_summary(summary)
    return json.dumps(
        summary,
        ensure_ascii=False,
        allow_nan=False,
        indent=2,
    ) + "\n"


def _rate_text(value: dict[str, Any]) -> str:
    if value["decimal"] is None:
        return f"undefined ({value['undefined_reason']})"
    return f"{value['fraction']} ({value['decimal']})"


def p2c_summary_to_markdown(summary: dict[str, Any]) -> str:
    """Serialize the same validated audit as review-friendly Markdown."""

    validate_audit_summary(summary)
    status = summary["validation_status"]["status"]
    lines = [
        "# P2c Frozen-Policy Trajectory Miss Audit",
        "",
        "This is an analysis-only, fixed-input, descriptive, non-causal, and non-deployable audit of the accepted formal six policies.",
        "",
        f"Validation status: `{status}`.",
        "",
    ]
    if status == INVALID_STATUS:
        lines.extend(
            [
                "No partial trajectory, aggregate, policy-performance, or acceptance claim is valid.",
                "",
                "Reason codes: " + ", ".join(f"`{item}`" for item in summary["reason_codes"]),
                "",
            ]
        )
    else:
        overall = summary["aggregate_axes"]["overall"]
        lines.extend(
            [
                "## Frozen Population",
                "",
                "- Population: `10` expansion-only buggy variants × `6` accepted formal policies = `60` trajectories.",
                "- Runner, seed, settings, catalog, policies, and variant-level module-context lifetime are unchanged.",
                "- Accepted P2a discovery rows and P2b detector mapping are exact validation anchors.",
                "",
                "## Overlapping Descriptive Axes",
                "",
                f"- Direct detector selected: {_rate_text(overall['detector_selected_count'])}.",
                f"- Direct detector not selected: {_rate_text(overall['detector_not_selected_count'])}.",
                f"- Unselected detector still budget-feasible at terminal state: {_rate_text(overall['detector_not_selected_terminal_feasible_count'])}.",
                f"- Replayed discoveries: {_rate_text(overall['replayed_discovered_count'])}.",
                "",
                "Selection, recorded budget feasibility, and termination overlap. They are not mutually exclusive causal explanations.",
                "",
                "## Policy Summary",
                "",
                "| Policy | Support | Detector selected | Unselected terminal-feasible | Replayed discovered |",
                "|---|---:|---:|---:|---:|",
            ]
        )
        for item in summary["aggregate_axes"]["by_policy"]:
            axes = item["axes"]
            lines.append(
                f"| `{item['policy_id']}` | {axes['support_pair_count']} | "
                f"{axes['detector_selected_count']['numerator']} | "
                f"{axes['detector_not_selected_terminal_feasible_count']['numerator']} | "
                f"{axes['replayed_discovered_count']['numerator']} |"
            )
        lines.extend(
            [
                "",
                "This audit does not rank policies, identify causal policy defects, add a policy, compute a counterfactual or DP ceiling, or establish inference, generalization, or production readiness.",
                "",
            ]
        )
    canonical = json.dumps(
        summary,
        ensure_ascii=False,
        allow_nan=False,
        indent=2,
    )
    lines.extend(
        [
            "## Canonical Validated Summary",
            "",
            _SUMMARY_BEGIN,
            "```json",
            canonical,
            "```",
            _SUMMARY_END,
            "",
        ]
    )
    return "\n".join(lines)


def summary_from_markdown(markdown: str) -> dict[str, Any]:
    """Recover and validate the exact embedded summary."""

    if markdown.count(_SUMMARY_BEGIN) != 1 or markdown.count(_SUMMARY_END) != 1:
        raise P2CTrajectoryAuditError("Markdown must contain one canonical summary block")
    body = markdown.split(_SUMMARY_BEGIN, 1)[1].split(_SUMMARY_END, 1)[0]
    if body.count("```json") != 1 or body.count("```") != 2:
        raise P2CTrajectoryAuditError("Markdown canonical summary fence is malformed")
    payload = body.split("```json", 1)[1].split("```", 1)[0].strip()
    try:
        summary = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise P2CTrajectoryAuditError("Markdown canonical summary is invalid JSON") from exc
    return validate_audit_summary(summary)


def save_p2c_report(
    summary: dict[str, Any],
    *,
    json_path: Path,
    markdown_path: Path,
    event_log: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Write both formats and record serialization only after both succeed."""

    json_text = p2c_summary_to_json(summary)
    markdown_text = p2c_summary_to_markdown(summary)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json_text, encoding="utf-8", newline="\n")
    markdown_path.write_text(markdown_text, encoding="utf-8", newline="\n")
    if event_log is not None:
        record_artifacts_serialized(event_log)
    return {
        "json_bytes": len(json_text.encode("utf-8")),
        "markdown_bytes": len(markdown_text.encode("utf-8")),
    }
