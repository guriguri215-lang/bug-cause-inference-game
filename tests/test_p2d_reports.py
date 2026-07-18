from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from bug_cause_inference.p2d import reports
from bug_cause_inference.p2d import stop_relaxation_audit as audit


ARTIFACT_ROOT = Path(__file__).parents[1] / "src/bug_cause_inference/p2d/artifacts"
JSON_PATH = ARTIFACT_ROOT / "p2d_one_step_stop_relaxation_audit_v1.json"
MARKDOWN_PATH = ARTIFACT_ROOT / "p2d_one_step_stop_relaxation_audit_v1.md"


@pytest.fixture(scope="module")
def tracked_summary() -> dict:
    summary = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    return audit.validate_audit_summary(summary)


def test_tracked_artifacts_are_deterministic_and_semantically_equal(tracked_summary) -> None:
    json_text = reports.p2d_summary_to_json(tracked_summary)
    markdown_text = reports.p2d_summary_to_markdown(tracked_summary)
    assert JSON_PATH.read_bytes() == json_text.encode()
    assert MARKDOWN_PATH.read_bytes() == markdown_text.encode()
    assert reports.summary_from_markdown(markdown_text) == tracked_summary
    assert json_text.endswith("\n") and markdown_text.endswith("\n")
    assert tracked_summary["input_identity"]["implementation_file_sha256_lf"] == (
        audit._implementation_identity()
    )


def test_artifact_identity_is_stable(tracked_summary) -> None:
    first_json = reports.p2d_summary_to_json(tracked_summary).encode()
    second_json = reports.p2d_summary_to_json(tracked_summary).encode()
    first_markdown = reports.p2d_summary_to_markdown(tracked_summary).encode()
    second_markdown = reports.p2d_summary_to_markdown(tracked_summary).encode()
    assert first_json == second_json
    assert first_markdown == second_markdown
    assert hashlib.sha256(first_json).hexdigest() == hashlib.sha256(
        JSON_PATH.read_bytes()
    ).hexdigest()
    assert hashlib.sha256(first_markdown).hexdigest() == hashlib.sha256(
        MARKDOWN_PATH.read_bytes()
    ).hexdigest()


def test_markdown_states_one_step_noncausal_boundary(tracked_summary) -> None:
    markdown = reports.p2d_summary_to_markdown(tracked_summary)
    for phrase in (
        "analysis-only",
        "model-internal",
        "one-step",
        "non-causal",
        "non-deployable",
        "does not establish stop causality",
        "multi-step reachability",
    ):
        assert phrase in markdown


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
        reports.save_p2d_report(
            tracked_summary,
            json_path=tmp_path / "audit.json",
            markdown_path=tmp_path / "audit.md",
            event_log=events,
        )
    assert events == []
