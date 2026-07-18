"""Deterministic JSON and Markdown serializers for the P2e audit."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bug_cause_inference.p2e.continuation_audit import (
    INVALID_STATUS,
    P2EContinuationAuditError,
    record_artifacts_serialized,
    validate_audit_summary,
)


_SUMMARY_BEGIN = "<!-- P2E_VALIDATED_SUMMARY_BEGIN -->"
_SUMMARY_END = "<!-- P2E_VALIDATED_SUMMARY_END -->"


def p2e_summary_to_json(summary: dict[str, Any]) -> str:
    """Serialize a validated P2e audit as newline-terminated JSON."""

    validate_audit_summary(summary)
    return json.dumps(
        summary,
        ensure_ascii=False,
        allow_nan=False,
        indent=2,
    ) + "\n"


def _ratio_text(value: dict[str, Any]) -> str:
    if value["decimal"] is None:
        return f"undefined ({value['undefined_reason']})"
    return f"{value['fraction']} ({value['decimal']})"


def p2e_summary_to_markdown(summary: dict[str, Any]) -> str:
    """Serialize the same validated P2e audit as review-friendly Markdown."""

    validate_audit_summary(summary)
    status = summary["validation_status"]["status"]
    lines = [
        "# P2e Bounded Threshold-Relaxation Continuation Audit",
        "",
        "This is an analysis-only, fixed-input, ground-truth-informed, model-internal, bounded-sequence, non-causal, and non-deployable audit.",
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
        partition = overall["classification_counts"]
        terminal = overall["candidate_terminal_reason_counts"]
        lines.extend(
            [
                "## Frozen Population and Continuation",
                "",
                "- Population: `10` variants × `6` accepted formal policies = `60` ordered pairs.",
                f"- Continuation candidates: `{partition['continuation_candidate']}`; P2d detector endpoints: `{partition['p2d_direct_detector_endpoint']}`; P2d not applicable: `{partition['p2d_not_applicable']}`.",
                "- Only `no_bug_probability_threshold` is suppressed at every later pre-action decision.",
                "- The same retained policy state, RNG, execution context, costs, budget, and max-step contract are preserved.",
                "",
                "## Descriptive Bounded Outcome",
                "",
                f"- Direct detector observed endpoints: `{terminal['direct_detector_observed']}`.",
                "- Direct detector selected among continuation candidates: "
                + _ratio_text(overall["direct_detector_selected_candidate_ratio"])
                + ".",
                "- Observation detection is recorded separately from detector selection: "
                + _ratio_text(overall["observation_detected_candidate_ratio"])
                + ".",
                "",
                "This result does not establish stop causality, a policy defect or ranking, deployable improvement, sequence optimality, inference, generalization, or production readiness.",
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
    """Recover and validate the exact embedded P2e summary."""

    if markdown.count(_SUMMARY_BEGIN) != 1 or markdown.count(_SUMMARY_END) != 1:
        raise P2EContinuationAuditError(
            "Markdown must contain one canonical summary block"
        )
    body = markdown.split(_SUMMARY_BEGIN, 1)[1].split(_SUMMARY_END, 1)[0]
    if body.count("```json") != 1 or body.count("```") != 2:
        raise P2EContinuationAuditError("Markdown canonical summary fence is malformed")
    payload = body.split("```json", 1)[1].split("```", 1)[0].strip()
    try:
        summary = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise P2EContinuationAuditError(
            "Markdown canonical summary is invalid JSON"
        ) from exc
    return validate_audit_summary(summary)


def save_p2e_report(
    summary: dict[str, Any],
    *,
    json_path: Path,
    markdown_path: Path,
    event_log: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Write both formats and record serialization after both succeed."""

    json_text = p2e_summary_to_json(summary)
    markdown_text = p2e_summary_to_markdown(summary)
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
