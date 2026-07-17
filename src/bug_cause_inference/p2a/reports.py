"""Deterministic serializers for the validated P2a-B report summary."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bug_cause_inference.p2a.adequacy import (
    ANALYSIS_PHASE,
    REPORT_SCHEMA_VERSION,
    canonical_digest,
    validate_portable_value,
)
from bug_cause_inference.p2a.evaluation import (
    BUGGY_IDENTITIES,
    CLEAN_IDENTITIES,
    FORMAL_POLICY_IDS,
    INVALID_STATUS,
    P2AEvaluationError,
    VALID_STATUS,
    validate_canonical_gate_identity,
    validate_lovo_contract,
)


_TOP_LEVEL_FIELDS = (
    "schema_version",
    "analysis_phase",
    "benchmark_id",
    "report_role",
    "observation_mode",
    "legacy_benchmark_identity",
    "dataset_identity",
    "adapter_identity",
    "action_test_catalog_identity",
    "freeze_identity",
    "validation_status",
    "dataset_summary",
    "cohort_definitions",
    "formal_strategy_ids",
    "excluded_policy_ids",
    "fixed_settings",
    "bucket_ids",
    "bucket_support_by_cohort",
    "clean_family_support_by_cohort",
    "reference_distribution_by_cohort",
    "primary_buggy_results_by_cohort",
    "clean_results_by_cohort",
    "secondary_metric_results_by_cohort",
    "sensitivity",
    "software_acceptance",
    "limitations",
    "non_claims",
    "notes",
)


class P2AReportError(ValueError):
    """Raised when a report summary cannot be serialized safely."""


def validate_report_summary(summary: Any) -> dict[str, Any]:
    """Validate exact schema, portable values, identity order, and result status."""

    if type(summary) is not dict or tuple(summary) != _TOP_LEVEL_FIELDS:
        raise P2AReportError("report summary has missing, unknown, or reordered top-level fields")
    validate_portable_value(summary, "summary")
    if summary["schema_version"] != REPORT_SCHEMA_VERSION:
        raise P2AReportError("report schema version drifted")
    if summary["analysis_phase"] != ANALYSIS_PHASE:
        raise P2AReportError("report analysis phase drifted")
    status = summary["validation_status"].get("status")
    if status not in {VALID_STATUS, INVALID_STATUS}:
        raise P2AReportError("report validation status is unknown")
    if tuple(summary["formal_strategy_ids"]) != FORMAL_POLICY_IDS:
        raise P2AReportError("formal six policy identity/order drifted")
    if status == VALID_STATUS:
        try:
            validate_canonical_gate_identity(summary["freeze_identity"])
            validate_lovo_contract(summary["sensitivity"])
        except P2AEvaluationError as exc:
            raise P2AReportError(str(exc)) from exc
        if tuple(summary["primary_buggy_results_by_cohort"]) != BUGGY_IDENTITIES:
            raise P2AReportError("buggy four-identity order drifted")
        if tuple(summary["clean_results_by_cohort"]) != CLEAN_IDENTITIES:
            raise P2AReportError("clean four-identity order drifted")
        combined_buggy = summary["primary_buggy_results_by_cohort"][BUGGY_IDENTITIES[3]]
        combined_clean = summary["clean_results_by_cohort"][CLEAN_IDENTITIES[3]]
        if combined_buggy["arithmetic_sources"] != [BUGGY_IDENTITIES[1], BUGGY_IDENTITIES[2]]:
            raise P2AReportError("combined buggy arithmetic source is invalid")
        if combined_clean["arithmetic_sources"] != [CLEAN_IDENTITIES[1], CLEAN_IDENTITIES[2]]:
            raise P2AReportError("combined clean arithmetic source is invalid")
        if summary["software_acceptance"] != {
            "status": "implementation_conformant_pending_independent_review",
            "accepted_result": False,
            "performance_pattern_required_for_acceptance": False,
        }:
            raise P2AReportError("implementation report software status drifted or self-accepted")
    else:
        result_fields = (
            "primary_buggy_results_by_cohort",
            "clean_results_by_cohort",
            "secondary_metric_results_by_cohort",
            "sensitivity",
        )
        if any(summary[field] for field in result_fields):
            raise P2AReportError("invalid report contains a partial result")
        if summary["software_acceptance"] != {
            "status": INVALID_STATUS,
            "accepted": False,
        }:
            raise P2AReportError("invalid report contains software acceptance")
    return summary


def p2a_summary_to_json(summary: dict[str, Any]) -> str:
    """Serialize one validated summary as stable UTF-8 JSON text."""

    value = validate_report_summary(summary)
    return json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"


def _fmt_fraction(value: dict[str, Any]) -> str:
    return f"{value['numerator']}/{value['denominator']} ({value['decimal']})"


def p2a_summary_to_markdown(summary: dict[str, Any]) -> str:
    """Serialize the same validated summary as readable Markdown plus exact JSON."""

    value = validate_report_summary(summary)
    status = value["validation_status"]["status"]
    lines = [
        "# P2a Versioned Same-Domain Evaluation Report",
        "",
        f"- Schema: `{value['schema_version']}`",
        f"- Analysis phase: `{value['analysis_phase']}`",
        f"- Validation status: `{status}`",
        f"- Summary digest: `{canonical_digest(value)}`",
    ]
    if status == VALID_STATUS:
        lines.extend(
            [
                "",
                "## Evidence Roles",
                "",
                "Expansion-only buggy discovery rate/loss is primary. Combined versioned buggy evidence is descriptive and is computed from P2a replay plus expansion only. Accepted P1d1 reference rows are immutable context and are not an arithmetic input.",
                "",
                "## Expansion-Only Primary",
                "",
                "| policy | worst-bucket loss | worst buckets | uniform-bucket reference average |",
                "|---|---:|---|---:|",
            ]
        )
        primary = value["primary_buggy_results_by_cohort"][BUGGY_IDENTITIES[2]]["restricted_pure_result"]
        for policy in FORMAL_POLICY_IDS:
            row = primary["by_policy"][policy]
            lines.append(
                f"| `{policy}` | {_fmt_fraction(row['worst_bucket_loss'])} | "
                f"{', '.join(row['worst_bucket_ids'])} | {_fmt_fraction(row['reference_average_loss'])} |"
            )
        lines.extend(
            [
                "",
                "## Limitations and Non-Claims",
                "",
                *[f"- {item}" for item in value["limitations"]],
                *[f"- {item}" for item in value["non_claims"]],
            ]
        )
    else:
        lines.extend(
            [
                "",
                "## Invalid / Inconclusive",
                "",
                value["validation_status"]["reason"],
                "",
                "No partial matrix, performance claim, software acceptance, or accepted result is emitted.",
            ]
        )
    lines.extend(
        [
            "",
            "## Exact Validated Summary",
            "",
            "The JSON block below is the complete source summary used for both serializers.",
            "",
            "```json",
            json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False),
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def summary_from_markdown(markdown: str) -> dict[str, Any]:
    """Extract the exact source summary from a generated Markdown report."""

    marker = "## Exact Validated Summary\n\nThe JSON block below is the complete source summary used for both serializers.\n\n```json\n"
    if marker not in markdown or not markdown.endswith("```\n"):
        raise P2AReportError("Markdown does not contain the exact validated summary")
    payload = markdown.split(marker, 1)[1][:-4]
    value = json.loads(payload)
    return validate_report_summary(value)


def save_p2a_report(
    summary: dict[str, Any],
    *,
    json_path: str | Path,
    markdown_path: str | Path,
) -> dict[str, str]:
    """Write deterministic JSON and Markdown outputs from one validated summary."""

    json_text = p2a_summary_to_json(summary)
    markdown_text = p2a_summary_to_markdown(summary)
    if summary_from_markdown(markdown_text) != json.loads(json_text):
        raise P2AReportError("JSON and Markdown semantic agreement failed")
    json_target = Path(json_path)
    markdown_target = Path(markdown_path)
    json_target.parent.mkdir(parents=True, exist_ok=True)
    markdown_target.parent.mkdir(parents=True, exist_ok=True)
    json_target.write_text(json_text, encoding="utf-8", newline="\n")
    markdown_target.write_text(markdown_text, encoding="utf-8", newline="\n")
    return {
        "summary_digest": canonical_digest(summary),
        "json_sha256": __import__("hashlib").sha256(json_text.encode("utf-8")).hexdigest(),
        "markdown_sha256": __import__("hashlib").sha256(markdown_text.encode("utf-8")).hexdigest(),
    }
