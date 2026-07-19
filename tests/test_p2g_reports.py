from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from bug_cause_inference.p2g import benign_diff_clean_audit as audit
from bug_cause_inference.p2g import reports


ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "src/bug_cause_inference/p2g/artifacts/p2g_accepted_benign_diff_clean_paired_continuation_audit_v1.json"
MARKDOWN_PATH = ROOT / "src/bug_cause_inference/p2g/artifacts/p2g_accepted_benign_diff_clean_paired_continuation_audit_v1.md"


@pytest.fixture(scope="module")
def tracked_summary() -> dict:
    return audit.validate_audit_summary(json.loads(JSON_PATH.read_text(encoding="utf-8")))


def test_tracked_formats_are_deterministic_and_semantically_equal(tracked_summary) -> None:
    assert reports.p2g_summary_to_json(tracked_summary) == JSON_PATH.read_text(encoding="utf-8")
    markdown = reports.p2g_summary_to_markdown(tracked_summary)
    assert markdown == MARKDOWN_PATH.read_text(encoding="utf-8")
    assert reports.summary_from_markdown(markdown) == tracked_summary
    assert reports.p2g_summary_to_json(tracked_summary).endswith("\n")
    assert markdown.endswith("\n")


def test_artifact_hashes_are_stable_and_nonempty(tracked_summary) -> None:
    json_text = reports.p2g_summary_to_json(tracked_summary)
    markdown_text = reports.p2g_summary_to_markdown(tracked_summary)
    assert len(json_text.encode()) > 1000
    assert len(markdown_text.encode()) > len(json_text.encode())
    assert len(hashlib.sha256(json_text.encode()).hexdigest()) == 64
    assert len(hashlib.sha256(markdown_text.encode()).hexdigest()) == 64


def test_markdown_states_exact_claim_boundary(tracked_summary) -> None:
    markdown = reports.p2g_summary_to_markdown(tracked_summary)
    assert "exactly five accepted P2a" in markdown
    assert "`60` trajectories and `30` pairs" in markdown
    assert "not a population safety rate" in markdown
    assert "non-causal" in markdown
    assert "non-deployable" in markdown


@pytest.mark.parametrize("mode", ("missing_begin", "duplicate_begin", "missing_end", "bad_json"))
def test_markdown_rejects_missing_duplicate_and_malformed_blocks(tracked_summary, mode) -> None:
    markdown = reports.p2g_summary_to_markdown(tracked_summary)
    if mode == "missing_begin":
        markdown = markdown.replace(reports._SUMMARY_BEGIN, "")
    elif mode == "duplicate_begin":
        markdown = markdown.replace(reports._SUMMARY_BEGIN, reports._SUMMARY_BEGIN * 2)
    elif mode == "missing_end":
        markdown = markdown.replace(reports._SUMMARY_END, "")
    else:
        markdown = markdown.replace('"schema_version"', 'schema_version', 1)
    with pytest.raises(audit.P2GAuditError):
        reports.summary_from_markdown(markdown)


def test_successful_save_is_exact_and_event_is_last(tmp_path, tracked_summary) -> None:
    events: list[dict] = []
    json_path = tmp_path / "out.json"
    markdown_path = tmp_path / "out.md"
    result = reports.save_p2g_report(
        tracked_summary, json_path=json_path, markdown_path=markdown_path,
        event_log=events,
    )
    assert json_path.read_bytes() == JSON_PATH.read_bytes()
    assert markdown_path.read_bytes() == MARKDOWN_PATH.read_bytes()
    assert result == {"json_bytes": len(json_path.read_bytes()), "markdown_bytes": len(markdown_path.read_bytes())}
    assert events[-1] == {"event": "p2g_artifacts_serialized"}
