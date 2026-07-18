from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from bug_cause_inference.p2a.adequacy import canonical_digest
from bug_cause_inference.p2b import reports
from bug_cause_inference.p2b import solvability_ceiling as ceiling


ARTIFACT_DIRECTORY = Path("src/bug_cause_inference/p2b/artifacts")
JSON_PATH = ARTIFACT_DIRECTORY / "p2b_fixed_catalog_solvability_ceiling_v1.json"
MARKDOWN_PATH = ARTIFACT_DIRECTORY / "p2b_fixed_catalog_solvability_ceiling_v1.md"


@pytest.fixture(scope="module")
def tracked_summary():
    return json.loads(JSON_PATH.read_text(encoding="utf-8"))


def test_serializers_are_repeat_byte_deterministic_and_semantically_equal(
    tracked_summary,
) -> None:
    first_json = reports.p2b_summary_to_json(tracked_summary)
    second_json = reports.p2b_summary_to_json(tracked_summary)
    first_markdown = reports.p2b_summary_to_markdown(tracked_summary)
    second_markdown = reports.p2b_summary_to_markdown(tracked_summary)
    assert first_json == second_json
    assert first_markdown == second_markdown
    assert first_json.endswith("\n")
    assert first_markdown.endswith("\n")
    assert json.loads(first_json) == tracked_summary
    assert reports.summary_from_markdown(first_markdown) == tracked_summary


def test_tracked_artifacts_are_exact_and_reproducible(tracked_summary) -> None:
    json_bytes = JSON_PATH.read_bytes()
    markdown_bytes = MARKDOWN_PATH.read_bytes()
    assert len(json_bytes) == 144_276
    assert hashlib.sha256(json_bytes).hexdigest() == (
        "2d2e7aac4a745b87a8387cd25d668c9756202fb04b2a939075c42d366b0a715e"
    )
    assert len(markdown_bytes) == 146_543
    assert hashlib.sha256(markdown_bytes).hexdigest() == (
        "8f8af8b8b547e28f7ec1aa33e3e212fc4b8b9c7c1e736114c72e2afd44e0207a"
    )
    assert canonical_digest(tracked_summary) == (
        "f84bc0e5e6d3e4187ae9a9f7c8b6cb1ecc1c121e541edc57fe814e71fef24d50"
    )
    assert reports.p2b_summary_to_json(tracked_summary).encode("utf-8") == json_bytes
    assert reports.p2b_summary_to_markdown(tracked_summary).encode("utf-8") == markdown_bytes
    assert reports.summary_from_markdown(markdown_bytes.decode("utf-8")) == tracked_summary


def test_markdown_keeps_non_deployable_boundary_visible() -> None:
    markdown = MARKDOWN_PATH.read_text(encoding="utf-8")
    assert "ground-truth-informed, non-deployable" in markdown
    assert "not a seventh formal policy" in markdown
    assert "selection/order/stop trajectory limitation" in markdown
    assert "general upper bound" in markdown


def test_serializers_reject_unknown_nonfinite_path_and_self_acceptance(
    tracked_summary,
) -> None:
    unknown = deepcopy(tracked_summary)
    unknown["unknown"] = True
    with pytest.raises(ceiling.P2BDiagnosticError):
        reports.p2b_summary_to_json(unknown)

    nonfinite = deepcopy(tracked_summary)
    nonfinite["dataset_summary"]["buggy_support_count"] = float("nan")
    with pytest.raises((ValueError, ceiling.P2BDiagnosticError)):
        reports.p2b_summary_to_json(nonfinite)

    local_path = deepcopy(tracked_summary)
    local_path["notes"].append("C:/Users/example/private")
    with pytest.raises((ValueError, ceiling.P2BDiagnosticError)):
        reports.p2b_summary_to_json(local_path)

    self_accept = deepcopy(tracked_summary)
    self_accept["software_acceptance"]["accepted"] = True
    with pytest.raises(ceiling.P2BDiagnosticError):
        reports.p2b_summary_to_json(self_accept)


@pytest.mark.parametrize(
    "path_value",
    [
        "C:/Users/example/private",
        "/home/example/private",
        r"\\server\share\private",
        "file:///tmp/private.json",
        "tmp/pytest-of-example/pytest-1/result.json",
    ],
)
def test_serializers_reject_windows_posix_unc_uri_and_temp_paths(
    tracked_summary, path_value: str
) -> None:
    local_path = deepcopy(tracked_summary)
    local_path["notes"].append(path_value)
    with pytest.raises((ValueError, ceiling.P2BDiagnosticError)):
        reports.p2b_summary_to_json(local_path)


def test_save_records_serialization_only_after_both_artifacts(
    tracked_summary,
) -> None:
    class RecordingPath:
        def __init__(self, name: str) -> None:
            self.name = name
            self.parent = self
            self.text: str | None = None

        def mkdir(self, **kwargs) -> None:
            return None

        def write_text(self, text: str, **kwargs) -> None:
            self.text = text

    events = [
        {"event": "p2b_pre_diagnostic_gate_passed"},
        {"event": "p2b_catalog_case_execution_started"},
        {"event": "p2b_catalog_case_execution_completed"},
        {"event": "p2b_summary_validated"},
    ]
    json_path = RecordingPath("result.json")
    markdown_path = RecordingPath("result.md")
    reports.save_p2b_report(
        tracked_summary,
        json_path=json_path,
        markdown_path=markdown_path,
        event_log=events,
    )
    assert json_path.text is not None and markdown_path.text is not None
    assert [item["event"] for item in events][-1] == "p2b_artifacts_serialized"


def test_failed_second_write_does_not_record_serialization(tracked_summary) -> None:
    class RecordingPath:
        def __init__(self, *, fail: bool = False) -> None:
            self.parent = self
            self.fail = fail

        def mkdir(self, **kwargs) -> None:
            return None

        def write_text(self, text: str, **kwargs) -> None:
            if self.fail:
                raise OSError("synthetic second-write failure")

    events = [{"event": "p2b_summary_validated"}]
    with pytest.raises(OSError, match="second-write"):
        reports.save_p2b_report(
            tracked_summary,
            json_path=RecordingPath(),
            markdown_path=RecordingPath(fail=True),
            event_log=events,
        )
    assert events == [{"event": "p2b_summary_validated"}]


def test_invalid_summary_serializes_without_partial_results() -> None:
    invalid = ceiling.invalid_diagnostic_summary("synthetic_gate_failure")
    json_text = reports.p2b_summary_to_json(invalid)
    markdown = reports.p2b_summary_to_markdown(invalid)
    payload = json.loads(json_text)
    assert "variant_diagnostics" not in payload
    assert "policy_comparison" not in payload
    assert "No partial reachability" in markdown
    assert reports.summary_from_markdown(markdown) == invalid
