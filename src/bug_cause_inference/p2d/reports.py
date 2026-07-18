"""Deterministic JSON and Markdown serializers for the P2d audit."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bug_cause_inference.p2d.stop_relaxation_audit import (
    INVALID_STATUS,
    P2DStopRelaxationAuditError,
    record_artifacts_serialized,
    validate_audit_summary,
)


_SUMMARY_BEGIN = "<!-- P2D_VALIDATED_SUMMARY_BEGIN -->"
_SUMMARY_END = "<!-- P2D_VALIDATED_SUMMARY_END -->"


def p2d_summary_to_json(summary: dict[str, Any]) -> str:
    """Serialize a validated P2d audit as newline-terminated JSON."""

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


def p2d_summary_to_markdown(summary: dict[str, Any]) -> str:
    """Serialize the same validated P2d audit as review-friendly Markdown."""

    validate_audit_summary(summary)
    status = summary["validation_status"]["status"]
    lines = [
        "# P2d One-Step Stop-Relaxation Audit",
        "",
        "This is an analysis-only, fixed-input, ground-truth-informed, model-internal, one-step, non-causal, and non-deployable audit.",
        "",
        f"Validation status: `{status}`.",
        "",
    ]
    if status == INVALID_STATUS:
        lines.extend(
            [
                "No partial row, aggregate, policy-performance, causal, deployment, or acceptance claim is valid.",
                "",
                "Reason codes: "
                + ", ".join(f"`{item}`" for item in summary["reason_codes"]),
                "",
            ]
        )
    else:
        overall = summary["aggregate_results"]["overall"]
        partition = overall["outcome_class_counts"]
        lines.extend(
            [
                "## Frozen Population and Intervention",
                "",
                "- Population: `10` variants × `6` accepted formal policies = `60` ordered pairs.",
                "- Intervention candidates: `52`; not applicable: `8`.",
                "- Only the terminal `no_bug_probability_threshold` predicate is suppressed once.",
                "- A candidate executes zero or one counterfactual action and never a second action.",
                "",
                "## Immediate Outcome",
                "",
                f"- Alternate stop before action: `{partition['alternate_stop_before_action']}`.",
                f"- Action decision reached: `{partition['action_decision_reached']}`.",
                "- Counterfactual direct detector selected among all candidates: "
                + _rate_text(overall["direct_detector_selected_candidate_ratio"])
                + ".",
                "- Counterfactual direct detector selected among action decisions reached: "
                + _rate_text(overall["direct_detector_selected_action_reached_ratio"])
                + ".",
                "- Observation detection is recorded separately from detector selection.",
                "",
                "This one-step result does not establish stop causality, a policy defect or ranking, deployable improvement, multi-step reachability, sequence/DP optimality, inference, generalization, or production readiness.",
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
    """Recover and validate the exact embedded P2d summary."""

    if markdown.count(_SUMMARY_BEGIN) != 1 or markdown.count(_SUMMARY_END) != 1:
        raise P2DStopRelaxationAuditError(
            "Markdown must contain one canonical summary block"
        )
    body = markdown.split(_SUMMARY_BEGIN, 1)[1].split(_SUMMARY_END, 1)[0]
    if body.count("```json") != 1 or body.count("```") != 2:
        raise P2DStopRelaxationAuditError("Markdown canonical summary fence is malformed")
    payload = body.split("```json", 1)[1].split("```", 1)[0].strip()
    try:
        summary = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise P2DStopRelaxationAuditError(
            "Markdown canonical summary is invalid JSON"
        ) from exc
    return validate_audit_summary(summary)


def save_p2d_report(
    summary: dict[str, Any],
    *,
    json_path: Path,
    markdown_path: Path,
    event_log: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Write both formats and record serialization after both succeed."""

    json_text = p2d_summary_to_json(summary)
    markdown_text = p2d_summary_to_markdown(summary)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json_text, encoding="utf-8", newline="\n")
    markdown_path.write_text(markdown_text, encoding="utf-8", newline="\n")
    if event_log is not None:
        record_artifacts_serialized(event_log)
    return {
        "json_bytes": len(json_text.encode()),
        "markdown_bytes": len(markdown_text.encode()),
    }
