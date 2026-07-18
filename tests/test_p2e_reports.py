from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from bug_cause_inference.p2e import continuation_audit as audit
from bug_cause_inference.p2e import reports


ARTIFACT_ROOT = Path(__file__).parents[1] / "src/bug_cause_inference/p2e/artifacts"
JSON_PATH = (
    ARTIFACT_ROOT / "p2e_bounded_threshold_relaxation_continuation_audit_v1.json"
)
MARKDOWN_PATH = (
    ARTIFACT_ROOT / "p2e_bounded_threshold_relaxation_continuation_audit_v1.md"
)


@pytest.fixture(scope="module")
def tracked_summary() -> dict:
    summary = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    return audit.validate_audit_summary(summary)


def test_tracked_artifacts_are_deterministic_and_semantically_equal(
    tracked_summary,
) -> None:
    json_text = reports.p2e_summary_to_json(tracked_summary)
    markdown_text = reports.p2e_summary_to_markdown(tracked_summary)
    assert JSON_PATH.read_bytes() == json_text.encode()
    assert MARKDOWN_PATH.read_bytes() == markdown_text.encode()
    assert reports.summary_from_markdown(markdown_text) == tracked_summary
    assert json_text.endswith("\n") and markdown_text.endswith("\n")
    assert tracked_summary["input_identity"]["implementation_file_sha256_lf"] == (
        audit.FROZEN_IMPLEMENTATION_FILE_SHA256_LF
    )
    assert tracked_summary["pre_outcome_freeze"][
        "implementation_file_sha256_raw"
    ] == audit.FROZEN_IMPLEMENTATION_FILE_SHA256_RAW
    assert audit._implementation_identity() != (
        audit.FROZEN_IMPLEMENTATION_FILE_SHA256_LF
    )


def test_artifact_identity_is_stable(tracked_summary) -> None:
    first_json = reports.p2e_summary_to_json(tracked_summary).encode()
    second_json = reports.p2e_summary_to_json(tracked_summary).encode()
    first_markdown = reports.p2e_summary_to_markdown(tracked_summary).encode()
    second_markdown = reports.p2e_summary_to_markdown(tracked_summary).encode()
    assert first_json == second_json
    assert first_markdown == second_markdown
    assert hashlib.sha256(first_json).hexdigest() == hashlib.sha256(
        JSON_PATH.read_bytes()
    ).hexdigest()
    assert hashlib.sha256(first_markdown).hexdigest() == hashlib.sha256(
        MARKDOWN_PATH.read_bytes()
    ).hexdigest()


def test_markdown_states_bounded_noncausal_boundary(tracked_summary) -> None:
    markdown = reports.p2e_summary_to_markdown(tracked_summary)
    for phrase in (
        "analysis-only",
        "model-internal",
        "bounded-sequence",
        "non-causal",
        "non-deployable",
        "does not establish stop causality",
        "sequence optimality",
    ):
        assert phrase in markdown


def test_markdown_rejects_missing_duplicate_and_malformed_blocks(
    tracked_summary,
) -> None:
    markdown = reports.p2e_summary_to_markdown(tracked_summary)
    with pytest.raises(audit.P2EContinuationAuditError):
        reports.summary_from_markdown(markdown.replace(reports._SUMMARY_BEGIN, ""))
    with pytest.raises(audit.P2EContinuationAuditError):
        reports.summary_from_markdown(markdown + markdown)
    with pytest.raises(audit.P2EContinuationAuditError):
        reports.summary_from_markdown(markdown.replace("```json", "```text", 1))


def test_save_records_event_only_after_both_writes(
    tmp_path, tracked_summary, monkeypatch
) -> None:
    events: list[dict] = []
    original = Path.write_text
    calls = 0

    def fail_second(self, *args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("synthetic second write failure")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", fail_second)
    with pytest.raises(OSError):
        reports.save_p2e_report(
            tracked_summary,
            json_path=tmp_path / "audit.json",
            markdown_path=tmp_path / "audit.md",
            event_log=events,
        )
    assert events == []


def test_successful_save_records_serialization_last(tmp_path, tracked_summary) -> None:
    events: list[dict] = []
    sizes = reports.save_p2e_report(
        tracked_summary,
        json_path=tmp_path / "audit.json",
        markdown_path=tmp_path / "audit.md",
        event_log=events,
    )
    assert sizes["json_bytes"] > 0 and sizes["markdown_bytes"] > 0
    assert events == [{"event": "p2e_artifacts_serialized"}]
