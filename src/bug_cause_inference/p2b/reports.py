"""Deterministic serializers for the P2b solvability ceiling diagnostic."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bug_cause_inference.p2b.solvability_ceiling import (
    INVALID_STATUS,
    P2BDiagnosticError,
    record_artifacts_serialized,
    validate_diagnostic_summary,
)


_SUMMARY_BEGIN = "<!-- P2B_VALIDATED_SUMMARY_BEGIN -->"
_SUMMARY_END = "<!-- P2B_VALIDATED_SUMMARY_END -->"


def p2b_summary_to_json(summary: dict[str, Any]) -> str:
    """Serialize one validated summary as stable newline-terminated JSON."""

    validate_diagnostic_summary(summary)
    return json.dumps(
        summary,
        ensure_ascii=False,
        allow_nan=False,
        indent=2,
    ) + "\n"


def _rate_text(rate: dict[str, Any]) -> str:
    if rate["decimal"] is None:
        return f"undefined ({rate['undefined_reason']})"
    return f"{rate['numerator']}/{rate['denominator']} ({rate['decimal']})"


def p2b_summary_to_markdown(summary: dict[str, Any]) -> str:
    """Serialize the same validated summary as audit-friendly Markdown."""

    validate_diagnostic_summary(summary)
    status = summary["validation_status"]["status"]
    lines = [
        "# P2b Fixed-Catalog Solvability Ceiling",
        "",
        "This is an analysis-only, ground-truth-informed, non-deployable diagnostic over the accepted fixed P2a catalog and cohort.",
        "",
        f"Validation status: `{status}`.",
        "",
    ]
    if status == INVALID_STATUS:
        lines.extend(
            [
                "No partial reachability, ceiling, policy comparison, or performance claim is valid.",
                "",
                "Reason codes: " + ", ".join(f"`{item}`" for item in summary["reason_codes"]),
                "",
            ]
        )
    else:
        overall = summary["overall_diagnostic"]
        lines.extend(
            [
                "## Fixed Inputs",
                "",
                "- Buggy support: `10` accepted P2a variants.",
                "- Frozen catalog: `24` cases applied to every buggy variant (`240` case evaluations).",
                "- Fixed budget: `12`; formal policies: `6`.",
                "- Saved accepted P2a policy outcomes were reused; policy and compatibility runners were not executed.",
                "",
                "## Overall Diagnostic",
                "",
                f"- Catalog reachability: {_rate_text(overall['catalog_reachability_rate'])}.",
                f"- Ground-truth-informed ceiling discovery: {_rate_text(overall['ceiling_discovery_rate'])}.",
                f"- Ceiling discovery loss: {_rate_text(overall['ceiling_discovery_loss'])}.",
                "",
                "## Variant Diagnostics",
                "",
                "| Variant | Bucket | Detecting actions | Minimum cost | Budget feasible |",
                "|---|---|---|---:|---|",
            ]
        )
        for row in summary["variant_diagnostics"]:
            actions = ", ".join(f"`{item}`" for item in row["detecting_action_ids"]) or "none"
            minimum = row["minimum_detecting_cost"]
            lines.append(
                f"| `{row['variant_id']}` | `{row['bucket_id']}` | {actions} | "
                f"{minimum if minimum is not None else 'undefined'} | "
                f"`{str(row['budget_feasible']).lower()}` |"
            )
        lines.extend(
            [
                "",
                "## Policy Comparison Boundary",
                "",
                "`catalog_reachable_policy_missed` means only that a direct, one-step, budget-feasible frozen-catalog certificate exists while the saved fixed-policy trajectory missed. It is a selection/order/stop trajectory limitation under this fixed contract, not a causal policy-inferiority or implementation-defect claim.",
                "",
                "The ceiling is not a seventh formal policy, deployable strategy, general upper bound, policy winner, minimax/Nash/regret result, or evidence of unseen-variant, second-domain, production, causal, or inferential performance.",
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
        raise P2BDiagnosticError("Markdown must contain one canonical summary block")
    body = markdown.split(_SUMMARY_BEGIN, 1)[1].split(_SUMMARY_END, 1)[0]
    if body.count("```json") != 1 or body.count("```") != 2:
        raise P2BDiagnosticError("Markdown canonical summary fence is malformed")
    payload = body.split("```json", 1)[1].split("```", 1)[0].strip()
    try:
        summary = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise P2BDiagnosticError("Markdown canonical summary is invalid JSON") from exc
    return validate_diagnostic_summary(summary)


def save_p2b_report(
    summary: dict[str, Any],
    *,
    json_path: Path,
    markdown_path: Path,
    event_log: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Write both deterministic formats from one validated summary."""

    json_text = p2b_summary_to_json(summary)
    markdown_text = p2b_summary_to_markdown(summary)
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
