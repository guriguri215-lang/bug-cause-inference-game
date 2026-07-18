from __future__ import annotations

import hashlib
import json
import random
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from bug_cause_inference.p1b import execution as p1b_execution
from bug_cause_inference.p1b import policies as p1b_policies
from bug_cause_inference.p1b.dataset import LOCATION_CANDIDATES
from bug_cause_inference.p1b.models import (
    P1B_CAUSE_CATEGORIES,
    P1B_FIX_INTENT_CATEGORIES,
    P1BSettings,
    uniform_distribution,
)
from bug_cause_inference.p2a import evaluation as p2a_evaluation
from bug_cause_inference.p2e import continuation_audit as audit


ARTIFACT_ROOT = Path(__file__).parents[1] / "src/bug_cause_inference/p2e/artifacts"
JSON_PATH = (
    ARTIFACT_ROOT / "p2e_bounded_threshold_relaxation_continuation_audit_v1.json"
)
P2D_ROOT = Path(__file__).parents[1] / "src/bug_cause_inference/p2d/artifacts"


@pytest.fixture(scope="module")
def tracked_summary() -> dict:
    summary = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    return audit.validate_audit_summary(summary)


def _state(
    *,
    bug_presence: float = 0.5,
    cost: int = 0,
    step: int = 0,
    detected: bool = False,
    executed: list[str] | None = None,
) -> p1b_policies._State:
    return p1b_policies._State(
        bug_presence=bug_presence,
        cause_posterior=uniform_distribution(P1B_CAUSE_CATEGORIES),
        location_posterior=uniform_distribution(LOCATION_CANDIDATES),
        fix_intent_posterior=uniform_distribution(P1B_FIX_INTENT_CATEGORIES),
        executed_actions=list(executed or []),
        cumulative_cost=cost,
        current_step=step,
        bug_detected=detected,
        execution_context=p1b_execution.P1BExecutionContext(),
    )


def test_frozen_constants_and_identity_contract() -> None:
    rows = audit._identity_rows()
    assert len(rows) == 57
    assert len({row["identity"] for row in rows}) == 57
    assert audit.identity_contract_digest(rows) == audit.IDENTITY_CONTRACT_DIGEST
    assert audit.IDENTITY_CONTRACT_DIGEST == (
        "10151569d670f0ada06ae167df1d82f4c77ce66c086c778a299b50ce61e4add5"
    )
    assert audit.SPECIFICATION_SHA256 == (
        "d3edfed2db20aacc390eacb4c0c377139015334d1f6547096f0ac33620249af9"
    )
    assert audit.SPECIFICATION_REVIEW_RECORD_SHA256 == (
        "f98f8b1fad8dc652ed9b487a5b48011bfac61bbb2b7bb159f8022257dcc2aa82"
    )
    assert audit.FROZEN_IMPLEMENTATION_FILE_SHA256_LF[
        "src/bug_cause_inference/p2e/continuation_audit.py"
    ] == "15b2e7525399e609de95a13c9ce4e747c38acef88f8cf937ff7e6764dc7f9ca9"
    assert audit.FROZEN_IMPLEMENTATION_FILE_SHA256_RAW == (
        audit.FROZEN_IMPLEMENTATION_FILE_SHA256_LF
    )
    assert audit._expected_input_identity()["implementation_file_sha256_lf"] == (
        audit.FROZEN_IMPLEMENTATION_FILE_SHA256_LF
    )
    assert audit._expected_freeze()["implementation_file_sha256_raw"] == (
        audit.FROZEN_IMPLEMENTATION_FILE_SHA256_RAW
    )
    assert audit._implementation_identity() != (
        audit.FROZEN_IMPLEMENTATION_FILE_SHA256_LF
    )


def test_accepted_identity_and_same_run_raw_drift_fail_closed(monkeypatch) -> None:
    rows, raw_hashes = audit._fresh_identity_snapshot()
    inputs = {
        "identity_rows": rows,
        "raw_hashes": raw_hashes,
        "implementation_identity": audit._implementation_identity(),
        "implementation_raw_hashes": audit._implementation_raw_snapshot(),
    }
    audit._assert_same_run_identities(inputs)

    raw_drift = deepcopy(inputs)
    first_path = next(iter(raw_drift["implementation_raw_hashes"]))
    raw_drift["implementation_raw_hashes"][first_path] = "0" * 64
    with pytest.raises(audit.P2EContinuationAuditError, match="raw bytes changed"):
        audit._assert_same_run_identities(raw_drift)

    original_hash_file = audit._hash_file
    first_identity_path = audit._repository_path(rows[0]["path"])

    def identity_drift(path):
        portable, raw = original_hash_file(path)
        if path == first_identity_path:
            portable = "0" * 64
        return portable, raw

    monkeypatch.setattr(audit, "_hash_file", identity_drift)
    with pytest.raises(audit.P2EContinuationAuditError, match="accepted input drifted"):
        audit._fresh_identity_snapshot()


def test_accepted_p2d_artifact_bytes_are_unchanged() -> None:
    json_path = P2D_ROOT / "p2d_one_step_stop_relaxation_audit_v1.json"
    markdown_path = P2D_ROOT / "p2d_one_step_stop_relaxation_audit_v1.md"
    assert hashlib.sha256(json_path.read_bytes()).hexdigest() == (
        audit.EXPECTED_P2D_JSON_SHA256
    )
    assert hashlib.sha256(markdown_path.read_bytes()).hexdigest() == (
        audit.EXPECTED_P2D_MARKDOWN_SHA256
    )


def test_classification_truth_table_and_candidate_indices() -> None:
    source = json.loads(audit._P2D_JSON_PATH.read_text(encoding="utf-8"))
    classes = [audit._classification(row) for row in source["pair_results"]]
    assert {item: classes.count(item) for item in audit.CLASSIFICATION_IDS} == {
        "continuation_candidate": 41,
        "p2d_direct_detector_endpoint": 11,
        "p2d_not_applicable": 8,
    }
    assert tuple(
        index
        for index, item in enumerate(classes, start=1)
        if item == "continuation_candidate"
    ) == audit.CONTINUATION_CANDIDATE_INDICES
    assert audit.CONTINUATION_CANDIDATE_INDICES[0] == 5


def test_rng_and_context_checkpoints_are_deep_and_ordered() -> None:
    first = random.Random(123)
    second = random.Random(123)
    assert audit.rng_state_digest(first) == audit.rng_state_digest(second)
    first.random()
    assert audit.rng_state_digest(first) != audit.rng_state_digest(second)

    left = p1b_execution.P1BExecutionContext()
    right = p1b_execution.P1BExecutionContext()
    left.record("run_smoke_tests", [{"passed": True, "test_id": "a"}])
    right.record("run_smoke_tests", [{"test_id": "a", "passed": True}])
    assert audit.execution_context_digest(left) == audit.execution_context_digest(right)
    right.record("inspect_traceback", [{"test_id": "b", "passed": False}])
    assert audit.execution_context_digest(left) != audit.execution_context_digest(right)


def test_residual_stop_precedence_is_accepted_order() -> None:
    settings = P1BSettings(**p2a_evaluation._FIXED_SETTINGS)
    state = _state(bug_presence=1.0, cost=12, step=6, detected=True)
    state.cause_posterior = {key: float(index == 0) for index, key in enumerate(P1B_CAUSE_CATEGORIES)}
    state.location_posterior = {key: float(index == 0) for index, key in enumerate(LOCATION_CANDIDATES)}
    rows, result = audit._residual_stop_evaluation(state, settings, [])
    assert [row["stop_id"] for row in rows] == list(audit.RESIDUAL_STOP_IDS)
    assert [row["fired"] for row in rows[:3]] == [True, True, True]
    assert result == "bug_confidence_threshold"


@pytest.mark.parametrize(
    ("state", "scores", "expected"),
    [
        (
            _state(bug_presence=1.0, detected=True),
            [{"expected_utility_per_cost": 1.0}],
            "bug_confidence_threshold",
        ),
        (_state(cost=12), [], "budget_limit"),
        (_state(step=6), [], "max_steps"),
        (_state(), [{"expected_utility_per_cost": 0.0}], "low_expected_utility"),
        (_state(), [{"expected_utility_per_cost": 1.0}], None),
    ],
)
def test_each_residual_predicate_and_no_stop_fixture(state, scores, expected) -> None:
    if expected == "bug_confidence_threshold":
        state.cause_posterior = {
            key: float(index == 0)
            for index, key in enumerate(P1B_CAUSE_CATEGORIES)
        }
        state.location_posterior = {
            key: float(index == 0) for index, key in enumerate(LOCATION_CANDIDATES)
        }
    settings = P1BSettings(**p2a_evaluation._FIXED_SETTINGS)
    rows, result = audit._residual_stop_evaluation(state, settings, scores)
    assert result == expected
    fired = [row["stop_id"] for row in rows if row["fired"]]
    assert fired == ([] if expected is None else [expected])


def test_repeated_target_only_suppression_retains_objects_and_nonrepeat(
    monkeypatch,
) -> None:
    state = _state(
        cost=2,
        step=2,
        executed=["inspect_traceback", "run_smoke_tests"],
    )
    rng = random.Random(73)
    context = state.execution_context
    planned = iter(["inspect_recent_diff", "inspect_spec_clause", None])
    calls: list[tuple] = []

    def choose(*args):
        calls.append(args)
        return next(planned)

    def execute(*, state, action_id, **kwargs):
        cost = audit.P1B_ACTION_SPECS[action_id].cost
        state.executed_actions.append(action_id)
        state.cumulative_cost += cost
        state.current_step += 1
        return SimpleNamespace(cost=cost, bug_detected=False)

    monkeypatch.setattr(p1b_policies, "choose_action", choose)
    monkeypatch.setattr(p1b_policies, "score_actions", lambda state, remaining: [])
    monkeypatch.setattr(
        audit,
        "_residual_stop_evaluation",
        lambda state, settings, scores: (
            [{"stop_id": item, "fired": False} for item in audit.RESIDUAL_STOP_IDS],
            None,
        ),
    )
    monkeypatch.setattr(audit, "_execute_action", execute)
    monkeypatch.setattr(audit, "_post_action_stop", lambda state, settings: audit.TARGET_STOP_ID)
    result = audit._run_continuation(
        variant=SimpleNamespace(variant_id="P2A-BUG-001"),
        policy_id="fixed_checklist",
        state=state,
        rng=rng,
        detector_ids=["run_boundary_tests"],
        modules={},
        cases_by_action={},
        candidate_artifact={},
    )
    assert [item["selected_action_id"] for item in result["decisions"]] == [
        "inspect_recent_diff",
        "inspect_spec_clause",
        None,
    ]
    assert all(item["suppressed_stop_id"] == audit.TARGET_STOP_ID for item in result["decisions"])
    assert [item["post_action_common_stop_result"] for item in result["decisions"][:2]] == [
        audit.TARGET_STOP_ID,
        audit.TARGET_STOP_ID,
    ]
    assert result["terminal_reason"] == "no_available_actions"
    assert result["additional_action_count"] == 2
    assert len(set(state.executed_actions)) == len(state.executed_actions)
    assert all(args[1] is state and args[3] is rng for args in calls)
    assert state.execution_context is context


@pytest.mark.parametrize(("action_id", "cost"), [("run_boundary_tests", 2), ("inspect_recent_diff", 2)])
def test_mapping_observation_contradiction_fails_closed(
    monkeypatch, action_id, cost
) -> None:
    state = _state(cost=2, step=2)
    monkeypatch.setattr(p1b_policies, "choose_action", lambda *args: action_id)
    monkeypatch.setattr(p1b_policies, "score_actions", lambda state, remaining: [])
    monkeypatch.setattr(
        audit,
        "_residual_stop_evaluation",
        lambda state, settings, scores: (
            [{"stop_id": item, "fired": False} for item in audit.RESIDUAL_STOP_IDS],
            None,
        ),
    )

    def contradictory(*, state, action_id, **kwargs):
        state.executed_actions.append(action_id)
        state.cumulative_cost += cost
        state.current_step += 1
        return SimpleNamespace(
            cost=cost,
            bug_detected=action_id != "run_boundary_tests",
        )

    monkeypatch.setattr(audit, "_execute_action", contradictory)
    with pytest.raises(
        audit.P2EContinuationAuditError,
        match="mapping and accepted observation disagree",
    ):
        audit._run_continuation(
            variant=SimpleNamespace(variant_id="P2A-BUG-001"),
            policy_id="fixed_checklist",
            state=state,
            rng=random.Random(0),
            detector_ids=["run_boundary_tests"],
            modules={},
            cases_by_action={},
            candidate_artifact={},
        )


@pytest.mark.parametrize("mode", ["unknown", "repeated", "over_budget"])
def test_invalid_selector_output_fails_closed(monkeypatch, mode) -> None:
    executed = ["inspect_traceback"] if mode == "repeated" else []
    state = _state(cost=11 if mode == "over_budget" else 2, step=2, executed=executed)
    if mode == "unknown":
        action_id = "not_an_accepted_action"
        pattern = "unavailable action"
    elif mode == "repeated":
        action_id = "inspect_traceback"
        pattern = "unavailable action"
    else:
        action_id = max(
            audit.ACTION_IDS, key=lambda item: audit.P1B_ACTION_SPECS[item].cost
        )
        assert audit.P1B_ACTION_SPECS[action_id].cost > 1
        pattern = "over-budget action"
    monkeypatch.setattr(p1b_policies, "choose_action", lambda *args: action_id)
    monkeypatch.setattr(p1b_policies, "score_actions", lambda state, remaining: [])
    monkeypatch.setattr(
        audit,
        "_residual_stop_evaluation",
        lambda state, settings, scores: (
            [{"stop_id": item, "fired": False} for item in audit.RESIDUAL_STOP_IDS],
            None,
        ),
    )
    with pytest.raises(audit.P2EContinuationAuditError, match=pattern):
        audit._run_continuation(
            variant=SimpleNamespace(variant_id="P2A-BUG-001"),
            policy_id="fixed_checklist",
            state=state,
            rng=random.Random(0),
            detector_ids=["run_boundary_tests"],
            modules={},
            cases_by_action={},
            candidate_artifact={},
        )


def test_policy_visibility_is_four_arguments_only(monkeypatch) -> None:
    calls: list[tuple] = []

    def spy(*args):
        calls.append(args)
        return None

    monkeypatch.setattr(p1b_policies, "choose_action", spy)
    monkeypatch.setattr(
        audit,
        "_residual_stop_evaluation",
        lambda state, settings, scores: (
            [{"stop_id": item, "fired": False} for item in audit.RESIDUAL_STOP_IDS],
            None,
        ),
    )
    monkeypatch.setattr(p1b_policies, "score_actions", lambda state, remaining: [])
    state = _state(cost=4, step=3, executed=["inspect_traceback"])
    result = audit._run_continuation(
        variant=SimpleNamespace(variant_id="P2A-BUG-001"),
        policy_id="fixed_checklist",
        state=state,
        rng=random.Random(0),
        detector_ids=["run_boundary_tests"],
        modules={},
        cases_by_action={},
        candidate_artifact={},
    )
    assert len(calls) == 1 and len(calls[0]) == 4
    assert calls[0][0] == "fixed_checklist"
    assert calls[0][1] is state
    assert result["terminal_reason"] == "no_available_actions"


def test_tracked_population_and_separate_acceptance(tracked_summary) -> None:
    assert tracked_summary["population"] == audit._expected_population()
    overall = tracked_summary["aggregate_results"]["overall"]
    assert overall["support_pair_count"] == 60
    assert overall["classification_counts"] == {
        "continuation_candidate": 41,
        "p2d_direct_detector_endpoint": 11,
        "p2d_not_applicable": 8,
    }
    for field in (
        "software_acceptance",
        "artifact_identity_acceptance",
        "result_acceptance",
        "documentation_acceptance",
    ):
        assert tracked_summary[field]["accepted"] is False
        assert tracked_summary[field]["status"] == "pending_separate_acceptance"


def test_candidate_checkpoint_and_payload_separation(tracked_summary) -> None:
    candidate_indices = []
    for row in tracked_summary["pair_results"]:
        if row["classification"] == "continuation_candidate":
            candidate_indices.append(row["pair_index"])
            assert row["continuation"] is not None
            for field in (
                "p2e_start_state_digest",
                "p2e_start_rng_state_digest",
                "p2e_start_execution_context_digest",
            ):
                assert len(row[field]) == 64
        else:
            assert row["continuation"] is None
            assert row["p2e_start_state_digest"] is None
            assert row["p2e_start_rng_state_digest"] is None
            assert row["p2e_start_execution_context_digest"] is None
    assert tuple(candidate_indices) == audit.CONTINUATION_CANDIDATE_INDICES


def test_terminal_partition_mapping_and_no_later_action(tracked_summary) -> None:
    candidates = [
        row for row in tracked_summary["pair_results"] if row["continuation"]
    ]
    assert len(candidates) == 41
    for row in candidates:
        value = row["continuation"]
        assert value["terminal_reason"] in audit.TERMINAL_REASON_IDS
        direct = value["terminal_reason"] == "direct_detector_observed"
        assert value["terminal_outcome"] == (
            "direct_detector_observed" if direct else "terminated_without_direct_detector"
        )
        assert value["direct_detector_selected"] is direct
        assert value["direct_detector_observation_detected"] is direct
        assert value["decisions"][-1]["terminal_after_decision"] is True
        assert all(
            decision["terminal_after_decision"] is False
            for decision in value["decisions"][:-1]
        )


def test_cost_step_action_bounds_and_trace_digests(tracked_summary) -> None:
    for row in tracked_summary["pair_results"]:
        value = row["continuation"]
        if value is None:
            continue
        assert value["additional_action_count"] <= value[
            "maximum_additional_action_count"
        ]
        assert value["final_step"] <= 6
        assert value["final_cumulative_cost"] <= 12
        assert value["final_remaining_budget"] >= 0
        assert value["continuation_trace_digest"] == audit._canonical_digest(
            value["decisions"]
        )
        selected = [
            decision
            for decision in value["decisions"]
            if decision["selected_action_id"] is not None
        ]
        assert len(selected) == value["additional_action_count"]
        assert sum(item["selected_action_cost"] for item in selected) == value[
            "cumulative_additional_cost"
        ]


def test_detector_feasibility_is_monotone(tracked_summary) -> None:
    for row in tracked_summary["pair_results"]:
        value = row["continuation"]
        if value is None:
            continue
        history = [
            decision["direct_detector_budget_feasible"]
            for decision in value["decisions"]
        ]
        assert not any(
            not earlier and later
            for earlier, later in zip(history, history[1:])
        )
        assert value["detector_feasibility_category"] in (
            audit.FEASIBILITY_CATEGORY_IDS
        )


def test_aggregates_recompute_exactly(tracked_summary) -> None:
    assert tracked_summary["aggregate_results"] == audit.derive_aggregate_results(
        tracked_summary["pair_results"]
    )
    overall = tracked_summary["aggregate_results"]["overall"]
    assert sum(overall["candidate_terminal_reason_counts"].values()) == 41
    assert sum(overall["additional_action_count_distribution"].values()) == 41
    assert sum(overall["additional_cost_distribution"].values()) == 41
    assert sum(overall["detector_feasibility_category_counts"].values()) == 41
    assert sum(overall["selected_action_counts"].values()) == sum(
        int(key) * value
        for key, value in overall["additional_action_count_distribution"].items()
    )


@pytest.mark.parametrize(
    ("mutator"),
    [
        lambda value: value["pair_results"][4].__setitem__("pair_index", True),
        lambda value: value["pair_results"][4].__setitem__(
            "classification", "p2d_not_applicable"
        ),
        lambda value: value["pair_results"][4]["continuation"].__setitem__(
            "terminal_outcome", "direct_detector_observed"
        ),
        lambda value: value["pair_results"][4]["continuation"]["decisions"][0].__setitem__(
            "suppressed_stop_id", "budget_limit"
        ),
        lambda value: value["pair_results"][4]["continuation"].__setitem__(
            "initial_feasible_direct_detector_ids", []
        ),
        lambda value: value["pair_results"][4].__setitem__(
            "p2e_start_execution_context_digest", "0" * 64
        ),
        lambda value: value["pair_results"][4]["continuation"].__setitem__(
            "continuation_trace_digest", "0" * 64
        ),
        lambda value: value["aggregate_results"]["overall"][
            "classification_counts"
        ].__setitem__("continuation_candidate", 40),
        lambda value: value.__setitem__("notes", ["C:\\private\\path"]),
        lambda value: value["input_identity"][
            "implementation_file_sha256_lf"
        ].__setitem__(
            "src/bug_cause_inference/p2e/continuation_audit.py", "0" * 64
        ),
    ],
)
def test_validator_rejects_coordinated_contract_mutations(
    tracked_summary, mutator
) -> None:
    mutated = deepcopy(tracked_summary)
    mutator(mutated)
    with pytest.raises(audit.P2EContinuationAuditError):
        audit.validate_audit_summary(mutated)


def test_validator_rejects_missing_extra_reorder_and_nonfinite(tracked_summary) -> None:
    missing = deepcopy(tracked_summary)
    missing.pop("notes")
    extra = deepcopy(tracked_summary)
    extra["extra"] = None
    reordered = {key: tracked_summary[key] for key in reversed(tracked_summary)}
    nonfinite = deepcopy(tracked_summary)
    nonfinite["pair_results"][4]["continuation"]["decisions"][0][
        "cumulative_cost_before"
    ] = float("nan")
    for value in (missing, extra, reordered, nonfinite):
        with pytest.raises(audit.P2EContinuationAuditError):
            audit.validate_audit_summary(value)


def test_invalid_summary_cannot_carry_partial_claims() -> None:
    value = audit._invalid_summary("continuation_contract_error")
    assert value["validation_status"] == {"status": "invalid_inconclusive"}
    assert value["input_identity"] is None
    for forbidden in (
        "pair_results",
        "aggregate_results",
        "population",
        "definitions",
        "limitations",
        "notes",
    ):
        assert forbidden not in value


def test_authoritative_pair_digest_support_is_complete(tracked_summary) -> None:
    assert len(audit._EXPECTED_PAIR_RESULT_DIGESTS) == 60
    assert tuple(
        audit._canonical_digest(row) for row in tracked_summary["pair_results"]
    ) == audit._EXPECTED_PAIR_RESULT_DIGESTS
