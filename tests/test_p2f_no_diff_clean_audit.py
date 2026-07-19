from __future__ import annotations

import json
import shutil
from copy import deepcopy
from pathlib import Path

import pytest

from bug_cause_inference.p2f import no_diff_clean_audit as audit


ARTIFACT_ROOT = Path(__file__).parents[1] / "src/bug_cause_inference/p2f/artifacts"
JSON_PATH = ARTIFACT_ROOT / "p2f_canonical_no_diff_clean_paired_continuation_audit_v1.json"


@pytest.fixture(scope="module")
def tracked_summary() -> dict:
    return audit.validate_audit_summary(json.loads(JSON_PATH.read_text(encoding="utf-8")))


def _refresh_summary_digest(summary: dict) -> None:
    summary["aggregate_results"]["digests"]["canonical_summary_digest"] = (
        audit._summary_digest(summary)
    )


def _rebuild_derived(summary: dict) -> None:
    for row in summary["trajectory_results"]:
        row["trajectory_digest"] = audit._trajectory_digest(row)
    cloned = deepcopy(summary["trajectory_results"])
    pairs = [
        audit._finish_pair(cloned[index], cloned[index + 1])
        for index in range(0, 12, 2)
    ]
    gate = summary["aggregate_results"]["baseline_validity_gate"]
    summary["pair_results"] = pairs
    summary["aggregate_results"] = audit.derive_aggregate_results(
        summary["trajectory_results"], pairs, gate
    )
    _refresh_summary_digest(summary)


def _event(summary: dict, kind: str) -> dict:
    if kind == "ordinary_selected":
        return next(
            event
            for row in summary["trajectory_results"]
            if row["arm_id"] == audit.ARM_IDS[1]
            for event in row["decision_events"]
            if event["selected_action_id"] is not None
            and event["target_predicate_value"] is False
        )
    if kind == "target_suppressed_selected":
        return next(
            event
            for row in summary["trajectory_results"]
            if row["arm_id"] == audit.ARM_IDS[1]
            for event in row["decision_events"]
            if event["selected_action_id"] is not None
            and event["target_suppressed"] is True
        )
    if kind == "control_target_terminal":
        return next(
            row["decision_events"][-1]
            for row in summary["trajectory_results"]
            if row["arm_id"] == audit.ARM_IDS[0]
        )
    if kind == "residual_terminal":
        return next(
            row["decision_events"][-1]
            for row in summary["trajectory_results"]
            if row["terminal_reason"] in audit.RESIDUAL_STOP_IDS
        )
    if kind == "no_available_actions":
        return next(
            row["decision_events"][-1]
            for row in summary["trajectory_results"]
            if row["terminal_reason"] == "no_available_actions"
        )
    raise AssertionError(kind)


def test_frozen_constants_and_exact_input_identity_contract() -> None:
    rows, _ = audit._fresh_identity_snapshot()
    assert len(rows) == 65
    assert len({row["identity"] for row in rows}) == 65
    assert audit._canonical_digest(rows) == audit.INPUT_IDENTITY_CONTRACT_DIGEST
    assert audit.INPUT_IDENTITY_CONTRACT_DIGEST == (
        "aca567fb7048aac2b6349a6383ec0aa601ceedde504724e4c75ddbf1e8729d0a"
    )
    assert audit.BASELINE_CASE_IDS == tuple(audit.p1b_execution.TEST_CASES)
    assert audit._canonical_digest(list(audit.BASELINE_CASE_IDS)) == (
        audit.BASELINE_CASE_ID_DIGEST
    )
    assert len(audit.BASELINE_CASE_IDS) == 29
    assert audit.FORMAL_POLICY_IDS == (
        "fixed_checklist",
        "test_first",
        "coverage_first",
        "recent_diff_first",
        "cause_only_p1a_style",
        "expected_utility_per_cost",
    )
    assert audit.implementation_identity() != audit.FROZEN_IMPLEMENTATION_FILE_SHA256_LF


def test_manifest_and_no_diff_observation_are_truthful() -> None:
    audit._validate_manifest()
    observation = audit._truthful_no_diff_observation().to_dict()
    assert observation["changed_files"] == []
    assert observation["changed_functions"] == []
    assert observation["diff_artifact_path"] is None
    assert observation["diff_excerpt"] == ""
    assert observation["bug_detected"] is False
    assert observation["failure_found"] is False
    assert observation["no_bug_evidence"] is False
    assert observation["evidence_source"] == "p2f_truthful_no_diff"


def test_tracked_population_pairing_and_clean_gate(tracked_summary) -> None:
    assert tracked_summary["population"] == {
        "input_ids": [audit.INPUT_ID],
        "baseline_id": audit.BASELINE_ID,
        "policy_ids": list(audit.FORMAL_POLICY_IDS),
        "arm_ids": list(audit.ARM_IDS),
        "order": "input_major_policy_major_arm_minor",
        "trajectory_count": 12,
        "pair_count": 6,
        "independent_program_count": 1,
    }
    assert len(tracked_summary["trajectory_results"]) == 12
    assert len(tracked_summary["pair_results"]) == 6
    assert tracked_summary["aggregate_results"]["baseline_validity_gate"] == {
        "catalog_case_count": 29,
        "executed_case_count": 29,
        "passed_case_count": 29,
        "failed_case_count": 0,
        "ordered_case_id_digest": audit.BASELINE_CASE_ID_DIGEST,
        "baseline_copy_digest": audit._canonical_digest(audit._baseline_rows()),
    }
    assert all(pair["start_checkpoint_agreement"] for pair in tracked_summary["pair_results"])
    assert all(
        pair["prefix_agreement_before_control_terminal"]
        for pair in tracked_summary["pair_results"]
    )


def test_only_target_is_suppressed_and_every_row_is_bounded(tracked_summary) -> None:
    for row in tracked_summary["trajectory_results"]:
        assert row["action_count"] <= 6
        assert row["cumulative_cost"] <= 12
        assert len(row["selected_action_ids"]) == len(set(row["selected_action_ids"]))
        for event in row["decision_events"]:
            predicates = event["evaluated_stop_predicates"]
            assert [item["stop_id"] for item in predicates] == [
                audit.TARGET_STOP_ID,
                *audit.RESIDUAL_STOP_IDS,
            ]
            assert all(
                not item["suppressed"]
                for item in predicates
                if item["stop_id"] != audit.TARGET_STOP_ID
            )
            assert event["target_suppressed"] == predicates[0]["suppressed"]


def test_false_positive_definition_is_exact(tracked_summary) -> None:
    for row in tracked_summary["trajectory_results"]:
        expected = (
            row["terminal_reason"] == "bug_confidence_threshold"
            or row["final_bug_presence_posterior"] >= 0.75
        )
        assert row["false_positive"] is expected
        assert row["execution_failure_observed"] is False


def test_fresh_replay_is_byte_semantically_equal(tmp_path, tracked_summary) -> None:
    fresh = audit.run_no_diff_clean_audit(
        expected_implementation_identity=tracked_summary["pre_outcome_freeze"][
            "implementation_file_sha256_lf"
        ],
        work_root=tmp_path / "fresh",
    )
    assert fresh == tracked_summary


@pytest.mark.parametrize(
    "mutation",
    [
        "identity",
        "fake_diff",
        "pair_prefix",
        "residual_suppression",
        "self_acceptance",
        "trajectory_digest",
    ],
)
def test_contract_mutations_fail_closed(tracked_summary, mutation) -> None:
    changed = deepcopy(tracked_summary)
    if mutation == "identity":
        changed["input_identity"]["identity_contract_digest"] = "0" * 64
    elif mutation == "fake_diff":
        row = next(
            row
            for row in changed["trajectory_results"]
            if any(obs["action_id"] == "inspect_recent_diff" for obs in row["observations"])
        )
        observation = next(
            obs for obs in row["observations"] if obs["action_id"] == "inspect_recent_diff"
        )
        observation["diff_excerpt"] = "synthetic patch"
    elif mutation == "pair_prefix":
        changed["pair_results"][0]["prefix_agreement_before_control_terminal"] = False
    elif mutation == "residual_suppression":
        event = changed["trajectory_results"][1]["decision_events"][0]
        event["evaluated_stop_predicates"][1]["suppressed"] = True
    elif mutation == "self_acceptance":
        changed["software_acceptance"]["status"] = "accepted"
    else:
        changed["trajectory_results"][0]["trajectory_digest"] = "f" * 64
    _refresh_summary_digest(changed)
    with pytest.raises(audit.P2FAuditError):
        audit.validate_audit_summary(changed)


def test_freeze_identity_drift_fails_before_execution(tmp_path, tracked_summary) -> None:
    expected = dict(
        tracked_summary["pre_outcome_freeze"]["implementation_file_sha256_lf"]
    )
    expected[next(iter(expected))] = "0" * 64
    with pytest.raises(audit.P2FAuditError, match="external pre-outcome freeze"):
        audit.run_no_diff_clean_audit(
            expected_implementation_identity=expected,
            work_root=tmp_path / "must-not-run",
        )


@pytest.mark.parametrize(
    ("kind", "field", "value"),
    [
        ("ordinary_selected", "selection_attempted", False),
        ("ordinary_selected", "terminal_after_decision", True),
        ("target_suppressed_selected", "selection_attempted", False),
        ("target_suppressed_selected", "suppression_event_index", None),
        ("control_target_terminal", "selection_attempted", True),
        ("control_target_terminal", "selected_action_cost", 1),
        ("control_target_terminal", "terminal_reason", "budget_limit"),
        ("residual_terminal", "selection_attempted", True),
        ("residual_terminal", "terminal_reason", "no_available_actions"),
        ("no_available_actions", "selection_attempted", False),
        ("no_available_actions", "selected_action_id", "inspect_recent_diff"),
        ("no_available_actions", "terminal_reason", "budget_limit"),
    ],
)
def test_decision_truth_table_mutations_fail_closed(
    tracked_summary, kind, field, value
) -> None:
    changed = deepcopy(tracked_summary)
    target = _event(changed, kind)
    target[field] = value
    if kind == "ordinary_selected":
        control = changed["trajectory_results"][0]["decision_events"][
            target["decision_index"] - 1
        ]
        control[field] = value
    _rebuild_derived(changed)
    with pytest.raises(audit.P2FAuditError):
        audit.validate_audit_summary(changed)


@pytest.mark.parametrize(
    ("kind", "digest_field"),
    [
        ("control_target_terminal", "state_digest_after"),
        ("residual_terminal", "rng_state_digest_after"),
        ("no_available_actions", "execution_context_digest_after"),
    ],
)
def test_terminal_after_digest_mutations_fail_closed(
    tracked_summary, kind, digest_field
) -> None:
    changed = deepcopy(tracked_summary)
    _event(changed, kind)[digest_field] = "0" * 64
    _rebuild_derived(changed)
    with pytest.raises(audit.P2FAuditError, match="digest|checkpoint|chain|RNG"):
        audit.validate_audit_summary(changed)


@pytest.mark.parametrize(
    ("kind", "payload"),
    [
        ("control_target_terminal", "state"),
        ("residual_terminal", "state"),
        ("control_target_terminal", "rng"),
        ("residual_terminal", "context"),
    ],
)
def test_resigned_terminal_checkpoint_mutations_fail_closed(
    tracked_summary, kind, payload
) -> None:
    changed = deepcopy(tracked_summary)
    event = _event(changed, kind)
    row = next(
        row
        for row in changed["trajectory_results"]
        if event in row["decision_events"]
    )
    if payload == "state":
        cause_id = next(iter(row["final_state"]["cause_posterior"]))
        row["final_state"]["cause_posterior"][cause_id] += 0.01
        resigned = audit._result_digest(row["final_state"])
        event["state_digest_after"] = resigned
        row["final_state_digest"] = resigned
    elif payload == "rng":
        event["rng_state_digest_after"] = "1" * 64
        row["final_rng_state_digest"] = "1" * 64
    else:
        event["execution_context_digest_after"] = "2" * 64
        row["final_execution_context_digest"] = "2" * 64
    _rebuild_derived(changed)
    with pytest.raises(audit.P2FAuditError, match="terminal checkpoint"):
        audit.validate_audit_summary(changed)


@pytest.mark.parametrize("field", ["available_action_ids", "action_scores"])
def test_action_projection_completeness_and_order_fail_closed(
    tracked_summary, field
) -> None:
    changed = deepcopy(tracked_summary)
    event = _event(changed, "ordinary_selected")
    event[field] = list(reversed(event[field]))
    control = changed["trajectory_results"][0]["decision_events"][
        event["decision_index"] - 1
    ]
    control[field] = deepcopy(event[field])
    _rebuild_derived(changed)
    with pytest.raises(audit.P2FAuditError, match="completeness or order"):
        audit.validate_audit_summary(changed)


def test_repeated_target_suppression_omission_fails_closed(tracked_summary) -> None:
    changed = deepcopy(tracked_summary)
    row = next(
        row
        for row in changed["trajectory_results"]
        if row["suppression_count"] >= 5
    )
    event = [
        event for event in row["decision_events"] if event["target_suppressed"]
    ][-1]
    event["target_suppressed"] = False
    event["evaluated_stop_predicates"][0]["suppressed"] = False
    event["suppression_event_index"] = None
    row["suppression_count"] -= 1
    _rebuild_derived(changed)
    with pytest.raises(audit.P2FAuditError, match="suppression"):
        audit.validate_audit_summary(changed)


@pytest.mark.parametrize(
    "identity",
    [
        "p1b_actions_source",
        "p1b_execution_source",
        "p1b_models_source",
        "p1b_policies_source",
        "p2a_evaluation_source",
        "p2e_continuation_source",
        "p2e_json",
        "p1b_real_diff_manifest",
    ],
)
def test_accepted_policy_runtime_and_artifact_identity_drift_fails_closed(
    monkeypatch, identity
) -> None:
    rows = audit._identity_rows()
    target = next(row for row in rows if row["identity"] == identity)
    target_path = audit._repository_path(target["path"])
    original = audit._hash_file

    def drift(path):
        portable, raw = original(path)
        if path == target_path:
            portable = "0" * 64
        return portable, raw

    monkeypatch.setattr(audit, "_hash_file", drift)
    with pytest.raises(audit.P2FAuditError, match="accepted input drifted"):
        audit._fresh_identity_snapshot()


def test_baseline_missing_extra_and_hash_drift_fail_closed(tmp_path) -> None:
    root = tmp_path / "checkout"
    shutil.copytree(audit._BASELINE_ROOT, root)
    (root / "cart.py").unlink()
    with pytest.raises(audit.P2FAuditError, match="baseline file identity"):
        audit._baseline_rows(root)

    shutil.rmtree(root)
    shutil.copytree(audit._BASELINE_ROOT, root)
    (root / "extra.py").write_text("# extra\n", encoding="utf-8", newline="\n")
    with pytest.raises(audit.P2FAuditError, match="baseline file identity"):
        audit._baseline_rows(root)

    (root / "extra.py").unlink()
    (root / "cart.py").write_text("# drift\n", encoding="utf-8", newline="\n")
    with pytest.raises(audit.P2FAuditError, match="baseline file identity"):
        audit._baseline_rows(root)


@pytest.mark.parametrize("mode", ["reordered", "duplicate"])
def test_inherited_identity_order_and_duplicates_fail_closed(monkeypatch, mode) -> None:
    original = audit.p2e_audit._identity_rows()
    changed = list(reversed(original)) if mode == "reordered" else [*original[:-1], original[0]]
    monkeypatch.setattr(audit.p2e_audit, "_identity_rows", lambda: changed)
    with pytest.raises(audit.P2FAuditError, match="inherited P2e identity"):
        audit._identity_rows()


def test_arm_order_and_paired_start_drift_fail_closed(tracked_summary) -> None:
    arm_changed = deepcopy(tracked_summary)
    arm_changed["trajectory_results"][0]["arm_id"] = audit.ARM_IDS[1]
    arm_changed["trajectory_results"][0]["trajectory_digest"] = audit._trajectory_digest(
        arm_changed["trajectory_results"][0]
    )
    _refresh_summary_digest(arm_changed)
    with pytest.raises(audit.P2FAuditError, match="canonical trajectory order"):
        audit.validate_audit_summary(arm_changed)

    rows = deepcopy(tracked_summary["trajectory_results"][:2])
    rows[1]["initial_rng_state_digest"] = "0" * 64
    with pytest.raises(audit.P2FAuditError, match="paired start checkpoint"):
        audit._finish_pair(rows[0], rows[1])


def test_bounds_false_positive_partition_and_private_path_fail_closed(
    tracked_summary
) -> None:
    bounds = deepcopy(tracked_summary)
    bounds["trajectory_results"][0]["action_count"] = 7
    _refresh_summary_digest(bounds)
    with pytest.raises(audit.P2FAuditError):
        audit.validate_audit_summary(bounds)

    false_positive = deepcopy(tracked_summary)
    false_positive["trajectory_results"][0]["false_positive"] = True
    _rebuild_derived(false_positive)
    with pytest.raises(audit.P2FAuditError, match="false-positive"):
        audit.validate_audit_summary(false_positive)

    partition = deepcopy(tracked_summary)
    partition["aggregate_results"]["false_positive_delta_counts"]["0"] = 5
    _refresh_summary_digest(partition)
    with pytest.raises(audit.P2FAuditError, match="aggregate results"):
        audit.validate_audit_summary(partition)

    private_path = deepcopy(tracked_summary)
    private_path["notes"][1] = "C:\\Users\\private\\secret.txt"
    _refresh_summary_digest(private_path)
    with pytest.raises(Exception, match="notes drifted|absolute local paths"):
        audit.validate_audit_summary(private_path)


def test_baseline_gate_failure_is_not_a_valid_result(tmp_path, monkeypatch) -> None:
    def failed_case(*args, **kwargs):
        return {"test_id": "synthetic", "passed": False}

    monkeypatch.setattr(audit.p2a_execution, "_run_test_case", failed_case)
    with pytest.raises(audit.P2FAuditError, match="baseline validity gate failed"):
        audit._baseline_validity_gate(tmp_path / "failed-gate")


def test_current_implementation_raw_same_run_drift_fails_closed(
    tmp_path, tracked_summary, monkeypatch
) -> None:
    original = audit._implementation_raw_snapshot()
    changed = dict(original)
    changed[next(iter(changed))] = "0" * 64
    snapshots = iter((original, changed))
    monkeypatch.setattr(audit, "_implementation_raw_snapshot", lambda: next(snapshots))
    with pytest.raises(audit.P2FAuditError, match="raw bytes changed"):
        audit.run_no_diff_clean_audit(
            expected_implementation_identity=tracked_summary["pre_outcome_freeze"][
                "implementation_file_sha256_lf"
            ],
            work_root=tmp_path / "raw-drift",
        )
