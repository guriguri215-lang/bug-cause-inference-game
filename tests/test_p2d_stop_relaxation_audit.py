from __future__ import annotations

from copy import deepcopy
import hashlib
import json

import pytest

from bug_cause_inference.p1b.models import P1BSettings, uniform_distribution
from bug_cause_inference.p1b import policies as p1b_policies
from bug_cause_inference.p1b.dataset import LOCATION_CANDIDATES
from bug_cause_inference.p1b.models import (
    P1B_CAUSE_CATEGORIES,
    P1B_FIX_INTENT_CATEGORIES,
)
from bug_cause_inference.p2d import stop_relaxation_audit as audit


@pytest.fixture(scope="module")
def audit_run() -> tuple[dict, list[dict]]:
    events: list[dict] = []
    summary = audit.run_stop_relaxation_audit(event_log=events)
    assert summary["validation_status"]["status"] == audit.VALID_STATUS
    return summary, events


@pytest.fixture(scope="module")
def summary(audit_run) -> dict:
    return audit_run[0]


def test_identity_contract_is_exact_and_independently_recomputable() -> None:
    rows = audit._identity_rows()
    assert len(rows) == 50
    assert len({row["identity"] for row in rows}) == 50
    canonical = json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode()
    assert hashlib.sha256(canonical).hexdigest() == audit.IDENTITY_CONTRACT_DIGEST
    assert audit.identity_contract_digest(rows) == audit.IDENTITY_CONTRACT_DIGEST
    changed = deepcopy(rows)
    changed[-1]["identity"] = "changed"
    assert audit.identity_contract_digest(changed) != audit.IDENTITY_CONTRACT_DIGEST


def test_implementation_snapshot_covers_source_serializer_and_tests() -> None:
    assert audit._P2D_IMPLEMENTATION_PATHS == (
        "src/bug_cause_inference/p2d/__init__.py",
        "src/bug_cause_inference/p2d/stop_relaxation_audit.py",
        "src/bug_cause_inference/p2d/reports.py",
        "tests/test_p2d_stop_relaxation_audit.py",
        "tests/test_p2d_reports.py",
    )


def test_exact_population_eligibility_and_first_intervention(audit_run) -> None:
    summary, events = audit_run
    rows = summary["pair_results"]
    assert len(rows) == 60
    assert [row["pair_index"] for row in rows] == list(range(1, 61))
    candidates = [row for row in rows if row["intervention_candidate"]]
    assert len(candidates) == 52
    assert len(rows) - len(candidates) == 8
    assert (
        candidates[0]["pair_index"],
        candidates[0]["variant_id"],
        candidates[0]["policy_id"],
    ) == (5, "P2A-BUG-001", "cause_only_p1a_style")
    assert [item["event"] for item in events] == [
        "p2d_specification_frozen",
        "p2d_specification_review_accepted",
        "p2d_identity_preflight_passed",
        "p2d_original_replay_started",
        "p2d_first_intervention_candidate_started",
        "p2d_all_pairs_completed",
        "p2d_summary_validated",
    ]


def test_original_replay_and_terminal_reconstruction_match_p2c(summary) -> None:
    assert all(
        row["p2c_source_row_sha256"] == row["replayed_p2c_row_sha256"]
        for row in summary["pair_results"]
    )
    assert all(
        row["terminal_state_reconstruction_agreement"]
        for row in summary["pair_results"]
    )
    assert all(
        all(row["input_identity_checks"].values()) for row in summary["pair_results"]
    )
    assert all(
        all(row["row_consistency_checks"].values()) for row in summary["pair_results"]
    )


def test_candidate_partition_and_action_horizon_are_exact(summary) -> None:
    candidates = [
        row for row in summary["pair_results"] if row["intervention_candidate"]
    ]
    alternate = [
        row
        for row in candidates
        if row["intervention"]["outcome_class"] == "alternate_stop_before_action"
    ]
    reached = [
        row
        for row in candidates
        if row["intervention"]["outcome_class"] == "action_decision_reached"
    ]
    assert len(alternate) + len(reached) == 52
    assert all(row["intervention"]["action_execution"] is None for row in alternate)
    for row in reached:
        action = row["intervention"]["action_execution"]
        assert action["executed_action_count"] == 1
        assert action["second_action_execution_count"] == 0
        assert action["horizon_status"] in (
            "normal_stop_after_action",
            "one_step_horizon_reached",
        )


def test_aggregate_results_are_independently_recomputed(summary) -> None:
    assert summary["aggregate_results"] == audit.derive_aggregate_results(
        summary["pair_results"]
    )
    overall = summary["aggregate_results"]["overall"]
    assert overall["support_pair_count"] == 60
    assert overall["intervention_candidate_count"] == 52
    assert overall["not_applicable_count"] == 8
    assert (
        overall["outcome_class_counts"]["alternate_stop_before_action"]
        + overall["outcome_class_counts"]["action_decision_reached"]
        == 52
    )
    assert (
        overall["action_execution_count"]
        == overall["outcome_class_counts"]["action_decision_reached"]
    )


def _state() -> object:
    return p1b_policies._State(
        bug_presence=0.5,
        cause_posterior=uniform_distribution(P1B_CAUSE_CATEGORIES),
        location_posterior=uniform_distribution(LOCATION_CANDIDATES),
        fix_intent_posterior=uniform_distribution(P1B_FIX_INTENT_CATEGORIES),
        executed_actions=[],
        cumulative_cost=0,
        current_step=0,
        bug_detected=False,
    )


def test_residual_stop_precedence_and_fresh_score_semantics(monkeypatch) -> None:
    settings = P1BSettings(**audit.p2a_evaluation._FIXED_SETTINGS)
    state = _state()
    state.cumulative_cost = settings.budget_limit
    state.current_step = settings.max_steps
    rows, result = audit._residual_stop_evaluation(state, settings)
    assert [item["stop_id"] for item in rows] == list(audit.RESIDUAL_STOP_IDS)
    assert result == "budget_limit"

    state = _state()
    monkeypatch.setattr(
        p1b_policies,
        "score_actions",
        lambda *_: [{"expected_utility_per_cost": 0.0}],
    )
    rows, result = audit._residual_stop_evaluation(state, settings)
    assert result == "low_expected_utility"
    assert rows[-1]["fired"] is True


def test_policy_selector_receives_only_frozen_visible_arguments(monkeypatch) -> None:
    calls: list[tuple] = []
    original = p1b_policies.choose_action

    def spy(policy, state, remaining_budget, rng):
        calls.append((policy, state, remaining_budget, rng))
        return original(policy, state, remaining_budget, rng)

    monkeypatch.setattr(p1b_policies, "choose_action", spy)
    summary = audit.run_stop_relaxation_audit()
    assert summary["validation_status"]["status"] == audit.VALID_STATUS
    assert calls
    assert all(len(call) == 4 for call in calls)
    assert all(call[0] in audit.FORMAL_POLICY_IDS for call in calls)


@pytest.mark.parametrize(
    "mutation",
    [
        "identity",
        "eligibility",
        "not_applicable_payload",
        "suppression_count",
        "residual_order",
        "action_cost",
        "second_action",
        "aggregate",
        "pair_order",
        "bool_type",
    ],
)
def test_contract_mutations_fail_closed(summary, mutation) -> None:
    changed = deepcopy(summary)
    candidate = changed["pair_results"][4]
    if mutation == "identity":
        changed["input_identity"]["p2c_json_sha256"] = "0" * 64
    elif mutation == "eligibility":
        candidate["intervention_candidate"] = False
    elif mutation == "not_applicable_payload":
        changed["pair_results"][0]["intervention"] = deepcopy(candidate["intervention"])
    elif mutation == "suppression_count":
        candidate["intervention"]["suppression_count"] = 2
    elif mutation == "residual_order":
        candidate["intervention"]["residual_stop_predicates"][:2] = reversed(
            candidate["intervention"]["residual_stop_predicates"][:2]
        )
    elif mutation == "action_cost":
        reached = next(
            row
            for row in changed["pair_results"]
            if row["intervention_candidate"]
            and row["intervention"]["outcome_class"] == "action_decision_reached"
        )
        reached["intervention"]["action_execution"]["selected_action_cost"] += 1
    elif mutation == "second_action":
        reached = next(
            row
            for row in changed["pair_results"]
            if row["intervention_candidate"]
            and row["intervention"]["outcome_class"] == "action_decision_reached"
        )
        reached["intervention"]["action_execution"]["second_action_execution_count"] = 1
    elif mutation == "aggregate":
        changed["aggregate_results"]["overall"]["intervention_candidate_count"] = 51
    elif mutation == "pair_order":
        changed["pair_results"][:2] = reversed(changed["pair_results"][:2])
    else:
        candidate["terminal_state_reconstruction_agreement"] = 1
    with pytest.raises(audit.P2DStopRelaxationAuditError):
        audit.validate_audit_summary(changed)


def test_coordinated_alternate_stop_mutation_fails_authoritative_digest(
    summary,
) -> None:
    changed = deepcopy(summary)
    intervention = changed["pair_results"][4]["intervention"]
    intervention["residual_stop_predicates"][1]["fired"] = True
    intervention["residual_stop_result"] = "budget_limit"
    intervention["outcome_class"] = "alternate_stop_before_action"
    intervention["action_execution"] = None
    changed["aggregate_results"] = audit.derive_aggregate_results(
        changed["pair_results"]
    )
    with pytest.raises(audit.P2DStopRelaxationAuditError, match="authoritative digest"):
        audit.validate_audit_summary(changed)


def test_coordinated_already_executed_action_mutation_fails_authoritative_digest(
    summary,
) -> None:
    changed = deepcopy(summary)
    row = changed["pair_results"][4]
    action = row["intervention"]["action_execution"]
    action["selected_action_id"] = "inspect_traceback"
    action["selected_action_cost"] = audit.P1B_ACTION_SPECS["inspect_traceback"].cost
    action["selected_action_is_direct_detector"] = False
    action["observation_bug_detected"] = False
    action["post_action_cumulative_cost"] = (
        row["original_terminal"]["terminal_cumulative_cost"]
        + action["selected_action_cost"]
    )
    changed["aggregate_results"] = audit.derive_aggregate_results(
        changed["pair_results"]
    )
    with pytest.raises(audit.P2DStopRelaxationAuditError, match="authoritative digest"):
        audit.validate_audit_summary(changed)


def test_implementation_raw_drift_during_execution_fails_closed(monkeypatch) -> None:
    original_snapshot = audit._implementation_raw_snapshot()
    calls = 0

    def drifting_snapshot() -> dict[str, str]:
        nonlocal calls
        calls += 1
        if calls == 1:
            return original_snapshot
        changed = dict(original_snapshot)
        changed["tests/test_p2d_reports.py"] = "0" * 64
        return changed

    monkeypatch.setattr(audit, "_implementation_raw_snapshot", drifting_snapshot)
    result = audit.run_stop_relaxation_audit()
    assert result["validation_status"]["status"] == audit.INVALID_STATUS
    assert result["reason_codes"] == ["intervention_contract_error"]


@pytest.mark.parametrize(
    ("value", "message"),
    [
        (float("nan"), "non-finite"),
        (float("inf"), "non-finite"),
        (r"C:\private\trace", "private absolute path"),
        (r"\\server\share\trace", "private absolute path"),
        ("/tmp/private-trace", "private absolute path"),
        ("file:///tmp/trace", "private absolute path"),
    ],
)
def test_nonfinite_and_private_paths_fail_closed(summary, value, message) -> None:
    changed = deepcopy(summary)
    changed["notes"].append(value)
    with pytest.raises(audit.P2DStopRelaxationAuditError, match=message):
        audit.validate_audit_summary(changed)


def test_zero_support_reason_is_exact() -> None:
    ratio = audit._ratio(0, 0, zero_reason="no_action_decision_reached_support")
    assert ratio == {
        "numerator": 0,
        "denominator": 0,
        "fraction": None,
        "decimal": None,
        "undefined_reason": "no_action_decision_reached_support",
    }


def test_invalid_summary_has_no_partial_claims() -> None:
    invalid = audit._invalid_summary("population_eligibility_error")
    assert invalid["validation_status"]["status"] == audit.INVALID_STATUS
    for forbidden in ("pair_results", "aggregate_results", "pre_outcome_freeze"):
        assert forbidden not in invalid
    assert invalid["reason_codes"] == ["population_eligibility_error"]
    assert all(
        invalid[field]["accepted"] is False
        for field in (
            "software_acceptance",
            "artifact_identity_acceptance",
            "result_acceptance",
            "documentation_acceptance",
        )
    )
