"""Deterministic JSON and Markdown serializers for the P2f audit."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bug_cause_inference.p2f.no_diff_clean_audit import (
    P2FAuditError,
    record_artifacts_serialized,
    validate_audit_summary,
)


_SUMMARY_BEGIN = "<!-- P2F_VALIDATED_SUMMARY_BEGIN -->"
_SUMMARY_END = "<!-- P2F_VALIDATED_SUMMARY_END -->"


def p2f_summary_to_json(summary: dict[str, Any]) -> str:
    """Serialize a validated P2f summary as canonical, LF-terminated JSON."""

    validate_audit_summary(summary)
    return json.dumps(
        summary,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        indent=2,
    ) + "\n"


def p2f_summary_to_markdown(summary: dict[str, Any]) -> str:
    """Serialize the same validated P2f summary as review-friendly Markdown."""

    validate_audit_summary(summary)
    by_arm = summary["aggregate_results"]["by_arm"]
    control = by_arm["normal_control"]
    intervention = by_arm["target_suppressed_continuation"]
    lines = [
        "# P2f Canonical No-Diff Clean Paired Continuation Audit",
        "",
        (
            "This is an analysis-only, fixed-input, clean-boundary, "
            "model-internal, paired, non-causal, and non-deployable audit."
        ),
        "",
        "Validation status: `valid`.",
        "",
        "## Frozen Population and Pairing",
        "",
        "- Input: exactly one canonical baseline with no applied patch.",
        "- Population: `1` input × `6` accepted formal policies × `2` paired arms = `12` trajectories and `6` pairs.",
        "- Control: the accepted normal stop/action/update loop.",
        "- Intervention: suppress only `no_bug_probability_threshold` at every pre-action decision.",
        "- Baseline gate: all `29/29` accepted execution tests passed before trajectories ran.",
        "",
        "## Descriptive Fixed-Input Outcome",
        "",
        f"- Control false positives: `{control['false_positive_count']}/6` policies.",
        f"- Intervention false positives: `{intervention['false_positive_count']}/6` policies.",
        "- Every pair has an identical start checkpoint and an exact prefix before the control terminal.",
        "- Empty recent-diff evidence contains no changed file, function, patch, or artifact path.",
        "",
        (
            "This result does not establish stop causality, a policy defect or "
            "ranking, deployable improvement, safety, inference, "
            "generalization, or production readiness."
        ),
        "",
        "## Canonical Validated Summary",
        "",
        _SUMMARY_BEGIN,
        "```json",
        json.dumps(
            summary,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            indent=2,
        ),
        "```",
        _SUMMARY_END,
        "",
    ]
    return "\n".join(lines)


def summary_from_markdown(markdown: str) -> dict[str, Any]:
    """Recover and validate the exact embedded P2f summary."""

    if markdown.count(_SUMMARY_BEGIN) != 1 or markdown.count(_SUMMARY_END) != 1:
        raise P2FAuditError("Markdown must contain one canonical summary block")
    body = markdown.split(_SUMMARY_BEGIN, 1)[1].split(_SUMMARY_END, 1)[0]
    if body.count("```json") != 1 or body.count("```") != 2:
        raise P2FAuditError("Markdown canonical summary fence is malformed")
    payload = body.split("```json", 1)[1].split("```", 1)[0].strip()
    try:
        summary = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise P2FAuditError("Markdown canonical summary is invalid JSON") from exc
    return validate_audit_summary(summary)


def save_p2f_report(
    summary: dict[str, Any],
    *,
    json_path: Path,
    markdown_path: Path,
    event_log: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Write both canonical formats, then record successful serialization."""

    json_text = p2f_summary_to_json(summary)
    markdown_text = p2f_summary_to_markdown(summary)
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
