from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from bug_cause_inference.p2g import benign_diff_clean_audit as audit
from bug_cause_inference.p2g.reports import p2g_summary_to_json, p2g_summary_to_markdown


ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "src/bug_cause_inference/p2g/artifacts/p2g_accepted_benign_diff_clean_paired_continuation_audit_v1.json"
MARKDOWN_PATH = ROOT / "src/bug_cause_inference/p2g/artifacts/p2g_accepted_benign_diff_clean_paired_continuation_audit_v1.md"


@pytest.fixture(scope="module")
def tracked_summary() -> dict:
    return audit.validate_audit_summary(json.loads(JSON_PATH.read_text(encoding="utf-8")))


def test_frozen_constants_and_exact_five_input_contracts() -> None:
    assert audit.INPUT_IDS == tuple(f"P2A-CLEAN-{index:03d}" for index in range(1, 6))
    assert audit.FORMAL_POLICY_IDS == (
        "fixed_checklist", "test_first", "coverage_first", "recent_diff_first",
        "cause_only_p1a_style", "expected_utility_per_cost",
    )
    assert audit.ARM_IDS == ("normal_control", "target_suppressed_continuation")
    contracts = audit._validate_input_contracts()
    assert [row["input_id"] for row in contracts] == list(audit.INPUT_IDS)
    assert all(row["patch_sha256"] and row["post_image_sha256_lf"] for row in contracts)
    assert all(row["changed_files"] and row["changed_functions"] for row in contracts)


def test_tracked_support_order_pairing_and_clean_gate(tracked_summary) -> None:
    assert tracked_summary["population"] == audit._population()
    assert len(tracked_summary["trajectory_results"]) == 60
    assert len(tracked_summary["pair_results"]) == 30
    aggregate = tracked_summary["aggregate_results"]
    assert aggregate["support"] == {
        "input_count": 5, "policy_count": 6, "arm_count": 2,
        "trajectory_count": 60, "pair_count": 30,
    }
    assert aggregate["pair_start_checkpoint_agreement"] == {"numerator": 30, "denominator": 30}
    assert aggregate["pair_prefix_agreement"] == {"numerator": 30, "denominator": 30}
    assert aggregate["normal_control_replay_gate"]["matched_pair_count"] == 30
    gate = aggregate["clean_validity_gate"]
    assert gate["input_count"] == 5
    assert gate["passed_oracle_count"] == gate["oracle_count"]
    assert all(row["all_pass"] for row in gate["inputs"])


def test_only_target_is_suppressed_and_every_row_is_bounded(tracked_summary) -> None:
    for row in tracked_summary["trajectory_results"]:
        assert len(row["selected_action_ids"]) == len(set(row["selected_action_ids"]))
        assert row["cumulative_cost"] <= 12
        assert row["action_count"] <= 6
        for event in row["decision_events"]:
            suppressed = [item["stop_id"] for item in event["evaluated_stop_predicates"] if item["suppressed"]]
            assert suppressed in ([], [audit.TARGET_STOP_ID])
            if event["residual_stop_result"] is not None:
                assert event["selected_action_id"] is None
    assert all(pair["start_checkpoint_agreement"] for pair in tracked_summary["pair_results"])
    assert all(pair["prefix_agreement_before_control_terminal"] for pair in tracked_summary["pair_results"])


def test_false_positive_and_distinct_axes_are_exact(tracked_summary) -> None:
    by_arm = tracked_summary["aggregate_results"]["by_arm"]
    for arm in audit.ARM_IDS:
        assert by_arm[arm]["false_positive"]["denominator"] == 30
        assert sum(by_arm[arm]["terminal_reason_counts"].values()) == 30
        assert "execution_failure_count" in by_arm[arm]
        assert "bug_detected_observation_count" in by_arm[arm]
    for row in tracked_summary["trajectory_results"]:
        expected = row["terminal_reason"] == "bug_confidence_threshold" or row["final_bug_presence_posterior"] >= 0.75
        assert row["false_positive"] is expected
        assert row["execution_failure_observed"] is False


def test_truthful_nonempty_benign_diff_is_exact(tracked_summary) -> None:
    observations = [
        (row["input_id"], observation)
        for row in tracked_summary["trajectory_results"]
        for observation in row["observations"]
        if observation["action_id"] == "inspect_recent_diff"
    ]
    assert observations
    for input_id, observation in observations:
        contract = audit._input_contract(input_id)
        assert observation["evidence_source"] == "p2g_accepted_p2a_patch_identity"
        assert observation["changed_files"] == contract["changed_files"]
        assert observation["changed_functions"] == contract["changed_functions"]
        assert observation["diff_artifact_path"] == contract["patch_path"]
        assert observation["diff_excerpt"].strip()
        assert not Path(observation["diff_artifact_path"]).is_absolute()
    aggregate = tracked_summary["aggregate_results"]["benign_diff_observations"]
    assert aggregate["path_function_excerpt_agreement_count"] == aggregate["execution_count"]


def test_fresh_replay_is_byte_and_semantically_equal(tmp_path, tracked_summary) -> None:
    expected = audit.implementation_identity()
    assert (
        tracked_summary["pre_outcome_freeze"]["implementation_file_sha256_lf"]
        == audit.HISTORICAL_FIRST_OUTCOME_IMPLEMENTATION_IDENTITY
    )
    fresh = audit.run_benign_diff_clean_audit(
        expected_implementation_identity=expected,
        work_root=tmp_path / "p2g-fresh",
    )
    assert fresh == tracked_summary
    assert p2g_summary_to_json(fresh) == JSON_PATH.read_text(encoding="utf-8")
    assert p2g_summary_to_markdown(fresh) == MARKDOWN_PATH.read_text(encoding="utf-8")


def _rehash_mutated_summary(value: dict) -> None:
    for row in value["trajectory_results"]:
        row["trajectory_digest"] = audit._trajectory_digest(row)
    aggregate = audit.derive_aggregate_results(
        value["trajectory_results"],
        value["pair_results"],
        value["aggregate_results"]["clean_validity_gate"],
    )
    value["aggregate_results"] = aggregate
    aggregate["digests"]["canonical_summary_digest"] = audit._summary_digest(value)


@pytest.mark.parametrize(
    "mutation",
    (
        "later_suppression_missing",
        "spurious_target_suppression",
        "non_target_suppression",
        "stop_precedence",
        "state_checkpoint",
        "rng_checkpoint",
        "context_checkpoint",
        "policy_action",
        "clean_gate_failure",
        "observation_unknown_field",
    ),
)
def test_semantic_decision_mutations_fail_closed(tracked_summary, mutation) -> None:
    value = deepcopy(tracked_summary)
    row = value["trajectory_results"][1]
    events = row["decision_events"]
    action_index = next(index for index, event in enumerate(events) if event["selected_action_id"] is not None)
    final_index = len(events) - 1
    if mutation == "clean_gate_failure":
        gate = value["aggregate_results"]["clean_validity_gate"]
        gate["inputs"][0]["oracle_results"][0]["passed"] = False
        gate["inputs"][0]["all_pass"] = False
        gate["passed_oracle_count"] = 13
    elif mutation == "observation_unknown_field":
        row["observations"][0]["clean_label"] = True
        events[action_index]["observation"]["clean_label"] = True
    elif mutation == "later_suppression_missing":
        event = next(event for event in events if event["suppression_event_index"] == 2)
        event["target_suppressed"] = False
        event["suppression_event_index"] = None
        event["evaluated_stop_predicates"][0]["suppressed"] = False
    elif mutation == "spurious_target_suppression":
        event = events[0]
        assert event["target_predicate_value"] is False
        event["target_suppressed"] = True
        event["suppression_event_index"] = 1
        event["evaluated_stop_predicates"][0]["suppressed"] = True
    elif mutation == "non_target_suppression":
        events[final_index]["evaluated_stop_predicates"][-1]["suppressed"] = True
    elif mutation == "stop_precedence":
        assert events[final_index]["residual_stop_result"] is not None
        events[final_index]["terminal_reason"] = audit.TARGET_STOP_ID
    elif mutation in {"state_checkpoint", "rng_checkpoint", "context_checkpoint"}:
        field = {
            "state_checkpoint": "state_digest_after",
            "rng_checkpoint": "rng_state_digest_after",
            "context_checkpoint": "execution_context_digest_after",
        }[mutation]
        before_field = field.replace("after", "before")
        events[action_index][field] = "0" * 64
        events[action_index + 1][before_field] = "0" * 64
    else:
        event = events[action_index]
        alternative = next(action for action in event["available_action_ids"] if action != event["selected_action_id"])
        event["selected_action_id"] = alternative
        event["selected_action_cost"] = audit.P1B_ACTION_SPECS[alternative].cost
    _rehash_mutated_summary(value)
    with pytest.raises(audit.P2GAuditError):
        audit.validate_audit_summary(value)


@pytest.mark.parametrize(
    "mutation",
    ("input_order", "arm_order", "false_positive", "terminal", "patch_path", "pair_prefix", "self_accept"),
)
def test_contract_mutations_fail_closed(tracked_summary, mutation) -> None:
    value = deepcopy(tracked_summary)
    if mutation == "input_order":
        value["population"]["input_ids"].reverse()
    elif mutation == "arm_order":
        value["population"]["arm_ids"].reverse()
    elif mutation == "false_positive":
        value["trajectory_results"][0]["false_positive"] = not value["trajectory_results"][0]["false_positive"]
    elif mutation == "terminal":
        value["trajectory_results"][0]["terminal_reason"] = "budget_limit"
    elif mutation == "patch_path":
        value["trajectory_results"][0]["observations"][0]["diff_artifact_path"] = "C:/private.patch"
    elif mutation == "pair_prefix":
        value["pair_results"][0]["prefix_agreement_before_control_terminal"] = False
    else:
        value["software_acceptance"]["status"] = "accepted"
    with pytest.raises(audit.P2GAuditError):
        audit.validate_audit_summary(value)


def test_external_implementation_identity_is_required(tmp_path, monkeypatch) -> None:
    current = audit.implementation_identity()
    changed = dict(current)
    changed[audit.IMPLEMENTATION_PATHS[0]] = "0" * 64
    with pytest.raises(audit.P2GAuditError, match="external pre-outcome freeze"):
        audit.run_benign_diff_clean_audit(
            expected_implementation_identity=changed,
            work_root=tmp_path / "bad-freeze",
        )
    monkeypatch.setitem(audit.DEPENDENCY_SHA256_LF, next(iter(audit.DEPENDENCY_SHA256_LF)), "f" * 64)
    with pytest.raises(audit.P2GAuditError, match="dependency identity"):
        audit.dependency_identity()


def test_clean_validity_failure_is_not_a_valid_result(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(audit, "run_oracle", lambda *_args, **_kwargs: type("R", (), {"passed": False})())
    with pytest.raises(audit.P2GAuditError, match="clean validity gate failed"):
        audit._clean_validity_gate(tmp_path / "invalid-clean")
