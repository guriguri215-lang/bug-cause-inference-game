from __future__ import annotations

import json
from copy import deepcopy

import pytest

from bug_cause_inference.p2h.reports import render_json, render_markdown, write_report_pair
from bug_cause_inference.p2h.task_scheduler_replication import (
    AUDIT_ID,
    P2HContractError,
    build_summary,
    canonical_digest,
    validate_summary,
)


def test_json_and_markdown_are_deterministic_and_share_one_summary(tmp_path) -> None:
    first = build_summary()
    second = build_summary()
    assert first == second
    assert render_json(first) == render_json(second)
    assert render_markdown(first) == render_markdown(second)
    json_path, markdown_path = write_report_pair(first, tmp_path / "first")
    other_json, other_markdown = write_report_pair(second, tmp_path / "second")
    assert json_path.read_bytes() == other_json.read_bytes()
    assert markdown_path.read_bytes() == other_markdown.read_bytes()
    reloaded = json.loads(json_path.read_text(encoding="utf-8"))
    assert reloaded == first
    assert validate_summary(reloaded) is reloaded
    assert json_path.name == f"{AUDIT_ID}.json"
    assert markdown_path.name == f"{AUDIT_ID}.md"


def test_summary_digest_excludes_only_its_own_field() -> None:
    summary = build_summary()
    without_digest = {key: value for key, value in summary.items() if key != "summary_digest"}
    assert summary["summary_digest"] == canonical_digest(without_digest)


def test_markdown_contains_authoritative_boundaries_metrics_and_digests() -> None:
    summary = build_summary()
    markdown = render_markdown(summary)
    for phrase in (
        "analysis-only",
        "fixed-input",
        "non-IID",
        "non-causal",
        "non-deployable",
        "does not establish policy superiority",
        "Bug discovery",
        "Clean false positive",
        "Function location top-3",
        summary["identities"]["row_digest"],
        summary["summary_digest"],
    ):
        assert phrase in markdown


def test_serializers_reject_an_unvalidated_summary() -> None:
    summary = build_summary()
    changed = deepcopy(summary)
    changed["aggregates"]["overall"]["clean_denominator"] = 29
    with pytest.raises(P2HContractError, match="aggregates"):
        render_json(changed)
    with pytest.raises(P2HContractError, match="aggregates"):
        render_markdown(changed)
