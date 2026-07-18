from __future__ import annotations

from copy import deepcopy
import hashlib
import json

import pytest

from bug_cause_inference.p2c import trajectory_audit as audit


@pytest.fixture(scope="module")
def summary() -> dict:
    result = audit.run_trajectory_audit()
    assert result["validation_status"]["status"] == audit.VALID_STATUS
    return result


def test_identity_contract_is_exact_and_independently_recomputable() -> None:
    rows = audit._identity_rows()
    assert len(rows) == 43
    assert audit.identity_contract_digest(rows) == audit.IDENTITY_CONTRACT_DIGEST
    canonical = json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode()
    assert hashlib.sha256(canonical).hexdigest() == audit.IDENTITY_CONTRACT_DIGEST
    changed = deepcopy(rows)
    changed[-1]["identity"] = "changed"
    assert audit.identity_contract_digest(changed) != audit.IDENTITY_CONTRACT_DIGEST
    reordered = deepcopy(rows)
    reordered[-2:] = reversed(reordered[-2:])
    assert audit.identity_contract_digest(reordered) != audit.IDENTITY_CONTRACT_DIGEST


def test_exact_population_replay_and_p2b_mapping(summary) -> None:
    rows = summary["pair_trajectories"]
    assert len(rows) == 60
    assert [row["pair_index"] for row in rows] == list(range(1, 61))
    assert all(row["accepted_replay_agreement"] for row in rows)
    assert all(all(row["consistency_checks"].values()) for row in rows)
    minima = {
        row["variant_id"]: row["minimum_detecting_cost"]
        for row in rows
    }
    assert [minima[variant] for variant in audit.BUGGY_VARIANT_IDS] == [
        2, 2, 2, 2, 3, 3, 4, 4, 2, 2
    ]


def test_reduced_trace_and_terminal_reconstruction_are_exact(summary) -> None:
    for row in summary["pair_trajectories"]:
        assert row["step_count"] == len(row["pre_action_states"])
        assert row["executed_action_ids"] == [
            step["selected_action_id"] for step in row["pre_action_states"]
        ]
        assert row["pair_trace_digest"] == audit.canonical_trace_digest(
            row["pre_action_states"]
        )
        assert row["stop_reason"] in audit.STOP_REASON_IDS
        assert row["initial_feasible_direct_detector_ids"]


def test_aggregate_axes_are_independently_recomputed(summary) -> None:
    assert summary["aggregate_axes"] == audit.derive_aggregate_axes(
        summary["pair_trajectories"]
    )
    assert summary["aggregate_axes"]["overall"]["support_pair_count"] == 60
    for item in summary["aggregate_axes"]["by_policy"]:
        assert item["axes"]["support_pair_count"] == 10
        assert len(item["axes"]["selection_terminal_budget_stop_crosstab"]) == 24
    for item in summary["aggregate_axes"]["by_variant"]:
        assert item["axes"]["support_pair_count"] == 6
    for item in summary["aggregate_axes"]["by_bucket"]:
        assert item["axes"]["support_pair_count"] == 12


@pytest.mark.parametrize("mutation", ["pair_order", "trace", "aggregate", "consistency"])
def test_pair_and_aggregate_mutations_fail_closed(summary, mutation) -> None:
    changed = deepcopy(summary)
    if mutation == "pair_order":
        changed["pair_trajectories"][:2] = reversed(changed["pair_trajectories"][:2])
    elif mutation == "trace":
        changed["pair_trajectories"][0]["pre_action_states"][0]["remaining_budget_before"] -= 1
    elif mutation == "aggregate":
        changed["aggregate_axes"]["overall"]["support_pair_count"] = 59
    else:
        changed["pair_trajectories"][0]["consistency_checks"][
            "accepted_p2a_outcome_matches_replay"
        ] = False
    with pytest.raises(audit.P2CTrajectoryAuditError):
        audit.validate_audit_summary(changed)


@pytest.mark.parametrize(
    "mutation",
    [
        "p2a_identity",
        "specification_identity",
        "raw_pre_post",
        "detector_mapping",
        "pair_boolean_type",
        "acceptance_boolean_type",
        "terminal_feasibility",
        "executed_action_history",
    ],
)
def test_frozen_subcontract_mutations_fail_closed(summary, mutation) -> None:
    changed = deepcopy(summary)
    row = changed["pair_trajectories"][0]
    if mutation == "p2a_identity":
        changed["input_identity"]["p2a_json_sha256"] = "0" * 64
    elif mutation == "specification_identity":
        changed["pre_outcome_freeze"]["specification_sha256"] = "0" * 64
    elif mutation == "raw_pre_post":
        changed["execution_boundary"]["raw_identity_pre_post_match"] = False
    elif mutation == "detector_mapping":
        row["direct_detecting_action_ids"] = ["run_null_missing_tests"]
        row["minimum_detecting_cost"] = 2
    elif mutation == "pair_boolean_type":
        row["accepted_replay_agreement"] = 1
    elif mutation == "acceptance_boolean_type":
        changed["software_acceptance"]["accepted"] = 0
    elif mutation == "terminal_feasibility":
        row = changed["pair_trajectories"][4]
        row["terminal_feasible_direct_detector_ids"] = []
        row["terminal_direct_detector_budget_feasible"] = False
    else:
        row["pre_action_states"][1]["executed_action_ids_before"] = []
        row["pair_trace_digest"] = audit.canonical_trace_digest(
            row["pre_action_states"]
        )
    with pytest.raises(audit.P2CTrajectoryAuditError):
        audit.validate_audit_summary(changed)


@pytest.mark.parametrize("mutation", ["detection_trace", "termination"])
def test_coordinated_semantic_mutations_fail_closed(summary, mutation) -> None:
    changed = deepcopy(summary)
    row = changed["pair_trajectories"][4]
    if mutation == "detection_trace":
        row["pre_action_states"][0]["observation_bug_detected"] = True
        row["pair_trace_digest"] = audit.canonical_trace_digest(
            row["pre_action_states"]
        )
    else:
        row["stop_reason"] = "budget_limit"
        row["terminal_common_stop_result"] = "budget_limit"
        changed["aggregate_axes"] = audit.derive_aggregate_axes(
            changed["pair_trajectories"]
        )
    with pytest.raises(audit.P2CTrajectoryAuditError):
        audit.validate_audit_summary(changed)


@pytest.mark.parametrize(
    ("value", "message"),
    [
        (float("nan"), "non-finite"),
        (float("inf"), "non-finite"),
        (r"C:\\private\\trace", "private absolute path"),
        (r"\\server\\share\\trace", "private absolute path"),
        ("/tmp/private-trace", "private absolute path"),
        ("file:///tmp/trace", "private absolute path"),
    ],
)
def test_nonfinite_and_private_paths_fail_closed(summary, value, message) -> None:
    changed = deepcopy(summary)
    changed["notes"].append(value)
    with pytest.raises(audit.P2CTrajectoryAuditError, match=message):
        audit.validate_audit_summary(changed)


def test_invalid_summary_has_no_partial_claims() -> None:
    invalid = audit._invalid_summary("SyntheticFailure")
    assert invalid["validation_status"]["status"] == audit.INVALID_STATUS
    for forbidden in ("pair_trajectories", "aggregate_axes", "pre_outcome_freeze"):
        assert forbidden not in invalid
    assert all(
        invalid[field]["accepted"] is False
        for field in (
            "software_acceptance",
            "artifact_identity_acceptance",
            "result_acceptance",
            "documentation_acceptance",
        )
    )


def test_budget_feasibility_is_not_terminal_selectability() -> None:
    detectors = ["run_boundary_tests"]
    assert audit._feasible_detectors(detectors, [], 2) == detectors
    assert audit._feasible_detectors(detectors, [], 1) == []
    assert audit._feasible_detectors(detectors, detectors, 12) == []
