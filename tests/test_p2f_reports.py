from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from bug_cause_inference.p2f import no_diff_clean_audit as audit
from bug_cause_inference.p2f import reports


ARTIFACT_ROOT = Path(__file__).parents[1] / "src/bug_cause_inference/p2f/artifacts"
JSON_PATH = ARTIFACT_ROOT / "p2f_canonical_no_diff_clean_paired_continuation_audit_v1.json"
MARKDOWN_PATH = ARTIFACT_ROOT / "p2f_canonical_no_diff_clean_paired_continuation_audit_v1.md"


@pytest.fixture(scope="module")
def tracked_summary() -> dict:
    return audit.validate_audit_summary(json.loads(JSON_PATH.read_text(encoding="utf-8")))


def test_tracked_formats_are_deterministic_and_semantically_equal(tracked_summary) -> None:
    json_text = reports.p2f_summary_to_json(tracked_summary)
    markdown_text = reports.p2f_summary_to_markdown(tracked_summary)
    assert JSON_PATH.read_bytes() == json_text.encode()
    assert MARKDOWN_PATH.read_bytes() == markdown_text.encode()
    assert reports.summary_from_markdown(markdown_text) == tracked_summary
    assert json_text.endswith("\n") and markdown_text.endswith("\n")
    assert json_text == reports.p2f_summary_to_json(tracked_summary)
    assert markdown_text == reports.p2f_summary_to_markdown(tracked_summary)


def test_artifact_hashes_match_canonical_serialization(tracked_summary) -> None:
    json_bytes = reports.p2f_summary_to_json(tracked_summary).encode()
    markdown_bytes = reports.p2f_summary_to_markdown(tracked_summary).encode()
    assert hashlib.sha256(json_bytes).hexdigest() == hashlib.sha256(
        JSON_PATH.read_bytes()
    ).hexdigest()
    assert hashlib.sha256(markdown_bytes).hexdigest() == hashlib.sha256(
        MARKDOWN_PATH.read_bytes()
    ).hexdigest()


def test_markdown_states_exact_claim_boundary(tracked_summary) -> None:
    markdown = reports.p2f_summary_to_markdown(tracked_summary)
    for phrase in (
        "analysis-only",
        "fixed-input",
        "model-internal",
        "paired",
        "non-causal",
        "non-deployable",
        "does not establish stop causality",
        "generalization",
        "production readiness",
    ):
        assert phrase in markdown


def test_markdown_rejects_missing_duplicate_and_malformed_blocks(tracked_summary) -> None:
    markdown = reports.p2f_summary_to_markdown(tracked_summary)
    with pytest.raises(audit.P2FAuditError):
        reports.summary_from_markdown(markdown.replace(reports._SUMMARY_BEGIN, ""))
    with pytest.raises(audit.P2FAuditError):
        reports.summary_from_markdown(markdown + markdown)
    with pytest.raises(audit.P2FAuditError):
        reports.summary_from_markdown(markdown.replace("```json", "```text", 1))


def test_save_records_serialization_only_after_both_writes(
    tmp_path, tracked_summary, monkeypatch
) -> None:
    events: list[dict] = []
    original = Path.write_text
    call_count = 0

    def fail_second(self, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise OSError("synthetic second write failure")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", fail_second)
    with pytest.raises(OSError):
        reports.save_p2f_report(
            tracked_summary,
            json_path=tmp_path / "audit.json",
            markdown_path=tmp_path / "audit.md",
            event_log=events,
        )
    assert events == []


def test_successful_save_is_exact_and_event_is_last(tmp_path, tracked_summary) -> None:
    events: list[dict] = []
    json_path = tmp_path / "audit.json"
    markdown_path = tmp_path / "audit.md"
    sizes = reports.save_p2f_report(
        tracked_summary,
        json_path=json_path,
        markdown_path=markdown_path,
        event_log=events,
    )
    assert sizes == {
        "json_bytes": len(json_path.read_bytes()),
        "markdown_bytes": len(markdown_path.read_bytes()),
    }
    assert events == [{"event": "p2f_artifacts_serialized"}]
