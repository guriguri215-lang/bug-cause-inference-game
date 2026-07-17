from __future__ import annotations

import json
import hashlib
from copy import deepcopy
from pathlib import Path

import pytest

from bug_cause_inference.p2a import evaluation, reports
from bug_cause_inference.p2a.adequacy import canonical_digest


@pytest.fixture(scope="module")
def summary():
    gate = evaluation._canonical_gate_identity()
    patch = pytest.MonkeyPatch()
    patch.setattr(
        evaluation,
        "validate_pre_outcome_gate",
        lambda **_: deepcopy(gate),
    )
    try:
        legacy, expansion = evaluation.make_synthetic_outcomes()
        value = evaluation.build_versioned_summary(legacy, expansion, gate=gate)
    finally:
        patch.undo()
    assert value["validation_status"]["status"] == "valid"
    return value


def test_json_and_markdown_are_newline_terminated_repeat_byte_deterministic(summary):
    first_json = reports.p2a_summary_to_json(summary)
    second_json = reports.p2a_summary_to_json(summary)
    first_markdown = reports.p2a_summary_to_markdown(summary)
    second_markdown = reports.p2a_summary_to_markdown(summary)
    assert first_json == second_json
    assert first_markdown == second_markdown
    assert first_json.endswith("\n")
    assert first_markdown.endswith("\n")
    assert json.loads(first_json) == summary


def test_markdown_embeds_the_exact_same_validated_summary(summary):
    markdown = reports.p2a_summary_to_markdown(summary)
    assert reports.summary_from_markdown(markdown) == summary
    assert "Expansion-only buggy discovery rate/loss is primary" in markdown
    assert "Accepted P1d1 reference rows are immutable context" in markdown
    assert "LOVO is descriptive influence only" in markdown


def test_save_report_writes_both_formats_from_one_summary(tmp_path, summary):
    json_path = tmp_path / "report.json"
    markdown_path = tmp_path / "report.md"
    first = reports.save_p2a_report(
        summary,
        json_path=json_path,
        markdown_path=markdown_path,
    )
    second = reports.save_p2a_report(
        summary,
        json_path=json_path,
        markdown_path=markdown_path,
    )
    assert first == second
    assert json.loads(json_path.read_text(encoding="utf-8")) == summary
    assert reports.summary_from_markdown(markdown_path.read_text(encoding="utf-8")) == summary


@pytest.mark.parametrize(
    "mutation",
    ["unknown", "path", "nonfinite", "combined_source", "self_accept"],
)
def test_report_validation_rejects_unknown_path_nonfinite_and_contract_drift(
    summary, mutation
):
    value = deepcopy(summary)
    if mutation == "unknown":
        value["unknown"] = True
    elif mutation == "path":
        value["notes"].append("C:/Users/example/private")
    elif mutation == "nonfinite":
        value["fixed_settings"]["budget_limit"] = float("inf")
    elif mutation == "combined_source":
        value["primary_buggy_results_by_cohort"]["combined_versioned_buggy"][
            "arithmetic_sources"
        ] = ["accepted_legacy_reference_buggy", "expansion_only_buggy"]
    else:
        value["software_acceptance"]["accepted_result"] = True
    with pytest.raises((reports.P2AReportError, ValueError)):
        reports.p2a_summary_to_json(value)


@pytest.mark.parametrize(
    "mutation",
    [
        "top_missing",
        "top_unknown",
        "top_reordered",
        "authorization_reordered",
        "contract_digest",
        "compatibility_type",
        "accepted_hash",
    ],
)
def test_valid_summary_embedded_gate_mutation_is_rejected_by_both_serializers(
    summary, mutation
):
    value = deepcopy(summary)
    gate = value["freeze_identity"]
    if mutation == "top_missing":
        gate.pop("official_freeze_digest")
    elif mutation == "top_unknown":
        gate["unknown"] = True
    elif mutation == "top_reordered":
        value["freeze_identity"] = {key: gate[key] for key in reversed(gate)}
    elif mutation == "authorization_reordered":
        authorization = gate["external_authorization_transition"]
        gate["external_authorization_transition"] = {
            key: authorization[key] for key in reversed(authorization)
        }
    elif mutation == "contract_digest":
        gate["contract_digests"]["metric"] = "f" * 64
    elif mutation == "compatibility_type":
        gate["legacy_compatibility"]["matched_pair_count"] = "150"
    else:
        first = next(iter(gate["accepted_four_file_sha256"]))
        gate["accepted_four_file_sha256"][first] = "0" * 64
    with pytest.raises(reports.P2AReportError):
        reports.p2a_summary_to_json(value)
    with pytest.raises(reports.P2AReportError):
        reports.p2a_summary_to_markdown(value)


@pytest.mark.parametrize(
    "target,mutation",
    [
        ("buggy_policy", "missing"),
        ("buggy_policy", "unknown"),
        ("buggy_policy", "reordered"),
        ("buggy_projection", "missing"),
        ("buggy_projection", "unknown"),
        ("clean", "missing"),
        ("clean", "unknown"),
        ("clean", "reordered"),
    ],
)
def test_lovo_metric_schema_missing_unknown_and_reordered_is_rejected(
    summary, target, mutation
):
    value = deepcopy(summary)
    projection_id = "expansion_only_buggy_minus_v"
    policy = evaluation.FORMAL_POLICY_IDS[0]
    if target == "buggy_policy":
        metrics = value["sensitivity"]["buggy_lovo"]["extremes"][projection_id][
            "policy_metrics"
        ][policy]
    elif target == "buggy_projection":
        metrics = value["sensitivity"]["buggy_lovo"]["extremes"][projection_id][
            "projection_metrics"
        ]
    else:
        metrics = value["sensitivity"]["clean_lovo"]["extremes"][
            "expansion_only_clean_minus_v"
        ][policy]
    if mutation == "missing":
        metrics.pop(next(iter(metrics)))
    elif mutation == "unknown":
        metrics["unknown"] = deepcopy(next(iter(metrics.values())))
    else:
        reordered = {key: metrics[key] for key in reversed(metrics)}
        metrics.clear()
        metrics.update(reordered)
    with pytest.raises(reports.P2AReportError):
        reports.p2a_summary_to_json(value)


def test_invalid_inconclusive_summary_serializes_without_partial_matrix():
    invalid = evaluation._invalid_summary("synthetic incomplete input")
    serialized = reports.p2a_summary_to_json(invalid)
    markdown = reports.p2a_summary_to_markdown(invalid)
    assert json.loads(serialized)["validation_status"]["status"] == "invalid_inconclusive"
    assert "No partial matrix" in markdown
    assert "implementation_conformant" not in serialized
    assert reports.summary_from_markdown(markdown) == invalid


def test_corrected_saved_artifacts_have_exact_identity_semantics_and_repeat_bytes():
    directory = Path("src/bug_cause_inference/p2a/artifacts/evaluation")
    json_bytes = (directory / "p2a_benchmark_evidence_expansion_v1.json").read_bytes()
    markdown_bytes = (directory / "p2a_benchmark_evidence_expansion_v1.md").read_bytes()
    assert len(json_bytes) == 1_699_240
    assert hashlib.sha256(json_bytes).hexdigest() == (
        "d7e69fa62513f5bbae22d570e39b841401f5110b6cd1e45701c53393eb0ef3df"
    )
    assert len(markdown_bytes) == 1_701_581
    assert hashlib.sha256(markdown_bytes).hexdigest() == (
        "017c5e3d9281e59e0b115a825a5f0e08f90a5e15a1e331514296adf443a2808a"
    )
    summary = json.loads(json_bytes)
    assert summary["schema_version"] == "p2a_benchmark_evidence_expansion_report.v1"
    assert summary["analysis_phase"] == "p2a_benchmark_evidence_expansion_report"
    assert summary["validation_status"]["status"] == "valid"
    assert canonical_digest(summary) == (
        "3dea5aaf38e1d9a46fd1a9ed973cb02c3fabf7ec933f2bb1c6df4f97446a9629"
    )
    assert reports.p2a_summary_to_json(summary).encode("utf-8") == json_bytes
    assert reports.p2a_summary_to_markdown(summary).encode("utf-8") == markdown_bytes
    assert reports.summary_from_markdown(markdown_bytes.decode("utf-8")) == summary
