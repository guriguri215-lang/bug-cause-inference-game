"""Deterministic JSON and Markdown serializers for the P2g audit."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bug_cause_inference.p2g.benign_diff_clean_audit import (
    P2GAuditError,
    record_artifacts_serialized,
    validate_audit_summary,
)


_SUMMARY_BEGIN = "<!-- P2G_VALIDATED_SUMMARY_BEGIN -->"
_SUMMARY_END = "<!-- P2G_VALIDATED_SUMMARY_END -->"


def p2g_summary_to_json(summary: dict[str, Any]) -> str:
    validate_audit_summary(summary)
    return json.dumps(summary, ensure_ascii=False, allow_nan=False, sort_keys=True, indent=2) + "\n"


def p2g_summary_to_markdown(summary: dict[str, Any]) -> str:
    validate_audit_summary(summary)
    by_arm = summary["aggregate_results"]["by_arm"]
    control = by_arm["normal_control"]
    intervention = by_arm["target_suppressed_continuation"]
    lines = [
        "# P2g Accepted Benign-Diff Clean Paired Continuation Audit",
        "",
        "This is an analysis-only, fixed-input, same-domain, hand-authored, model-internal, paired, non-causal, and non-deployable audit.",
        "",
        "Validation status: `valid`.",
        "",
        "## Frozen Support and Pairing",
        "",
        "- Inputs: exactly five accepted P2a benign non-empty-diff clean patches.",
        "- Support: `5` inputs × `6` accepted formal policies × `2` arms = `60` trajectories and `30` pairs.",
        "- Control: the accepted normal stop/action/update loop.",
        "- Intervention: suppress only `no_bug_probability_threshold` at every pre-action decision.",
        "- All input-specific clean oracles passed before policy trajectories ran.",
        "",
        "## Descriptive Fixed-Input Outcome",
        "",
        f"- Control false positives: `{control['false_positive']['numerator']}/30` trajectories.",
        f"- Intervention false positives: `{intervention['false_positive']['numerator']}/30` trajectories.",
        "- All `30/30` pairs have identical starts and exact prefixes before the control terminal.",
        "- Executed recent-diff actions use the accepted non-empty repository-relative patch evidence.",
        "",
        "This result is not a population safety rate, causal effect, policy ranking, deployable improvement, generalization result, or production recommendation.",
        "",
        "## Canonical Validated Summary",
        "",
        _SUMMARY_BEGIN,
        "```json",
        json.dumps(summary, ensure_ascii=False, allow_nan=False, sort_keys=True, indent=2),
        "```",
        _SUMMARY_END,
        "",
    ]
    return "\n".join(lines)


def summary_from_markdown(markdown: str) -> dict[str, Any]:
    if markdown.count(_SUMMARY_BEGIN) != 1 or markdown.count(_SUMMARY_END) != 1:
        raise P2GAuditError("Markdown must contain one canonical summary block")
    body = markdown.split(_SUMMARY_BEGIN, 1)[1].split(_SUMMARY_END, 1)[0]
    if body.count("```json") != 1 or body.count("```") != 2:
        raise P2GAuditError("Markdown canonical summary fence is malformed")
    payload = body.split("```json", 1)[1].split("```", 1)[0].strip()
    try:
        summary = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise P2GAuditError("Markdown canonical summary is invalid JSON") from exc
    return validate_audit_summary(summary)


def save_p2g_report(
    summary: dict[str, Any], *, json_path: Path, markdown_path: Path,
    event_log: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    json_text = p2g_summary_to_json(summary)
    markdown_text = p2g_summary_to_markdown(summary)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json_text, encoding="utf-8", newline="\n")
    markdown_path.write_text(markdown_text, encoding="utf-8", newline="\n")
    if event_log is not None:
        record_artifacts_serialized(event_log)
    return {"json_bytes": len(json_text.encode()), "markdown_bytes": len(markdown_text.encode())}
