from __future__ import annotations

import inspect
from collections import Counter
from copy import deepcopy

import pytest

from bug_cause_inference.p1b import policies as p1b_policies
from bug_cause_inference.p1b.actions import P1B_ACTION_SPECS
from bug_cause_inference.p1b.models import P1BSettings
from bug_cause_inference.p2h import task_scheduler_replication as p2h
from bug_cause_inference.p2h.domain_definition import (
    ACTION_CASE_MAPPING,
    ACTION_ORDER,
    INPUT_DEFINITIONS,
    INPUT_ORDER,
    ORACLE_CASES,
    build_manifest,
)


@pytest.fixture(scope="module")
def summary() -> dict:
    return p2h.build_summary()


def test_frozen_input_strata_and_order_are_exact() -> None:
    assert tuple(item["input_id"] for item in INPUT_DEFINITIONS) == INPUT_ORDER
    assert INPUT_ORDER == tuple(
        [f"P2H-BUG-{index:03d}" for index in range(1, 11)]
        + [f"P2H-CLEAN-{index:03d}" for index in range(1, 6)]
    )
    buggy = [item for item in INPUT_DEFINITIONS if item["is_buggy"]]
    clean = [item for item in INPUT_DEFINITIONS if not item["is_buggy"]]
    assert Counter(item["cause_family"] for item in buggy) == p2h.EXPECTED_BUGGY_FAMILIES
    assert tuple(item["clean_family"] for item in clean) == p2h.EXPECTED_CLEAN_FAMILIES
    assert all(item["replacement_before"] != item["replacement_after"] for item in INPUT_DEFINITIONS)


def test_accepted_policy_action_cost_and_settings_contract_is_unchanged() -> None:
    assert p2h.FORMAL_POLICY_IDS == p2h.EXPECTED_FORMAL_POLICY_IDS
    assert p2h.FORMAL_POLICY_IDS == tuple(p1b_policies.P1B_POLICIES[1:])
    assert tuple(P1B_ACTION_SPECS) == ACTION_ORDER
    assert {key: P1B_ACTION_SPECS[key].cost for key in ACTION_ORDER} == p2h.EXPECTED_ACTION_COSTS
    assert vars(P1BSettings()) == p2h.FIXED_SETTINGS


def test_manifest_oracle_and_action_case_identities_are_exact() -> None:
    manifest = build_manifest()
    assert manifest["input_order"] == list(INPUT_ORDER)
    assert manifest["action_order"] == list(ACTION_ORDER)
    assert manifest["oracle_order"] == [case["oracle_id"] for case in ORACLE_CASES]
    assert manifest["action_case_mapping"] == ACTION_CASE_MAPPING
    assert set(ACTION_CASE_MAPPING) == set(ACTION_ORDER)
    assert all(ACTION_CASE_MAPPING[action] for action in ACTION_ORDER)


def test_outcome_free_baseline_patch_and_oracle_validation() -> None:
    validation = p2h.validate_outcome_free_contract()
    assert validation["baseline_oracle_count"] == 25
    assert len(validation["input_validation"]) == 15
    for definition, row in zip(INPUT_DEFINITIONS, validation["input_validation"], strict=True):
        assert row["input_id"] == definition["input_id"]
        assert row["failed_oracle_ids"] == definition["expected_failing_oracle_ids"]
        if definition["is_buggy"]:
            assert row["failed_oracle_ids"]
        else:
            assert row["failed_oracle_ids"] == []
            assert row["passed_oracle_count"] == 25


def test_policy_selector_has_no_ground_truth_or_oracle_parameter() -> None:
    assert tuple(inspect.signature(p2h._select_policy_action).parameters) == (
        "policy_id",
        "state",
        "remaining_budget",
        "rng",
    )
    source = inspect.getsource(p2h._select_policy_action)
    for forbidden in ("definition", "input_id", "is_buggy", "oracle", "cause_family", "target_function"):
        assert forbidden not in source


def test_recent_diff_evidence_is_truthful_for_buggy_and_clean_inputs() -> None:
    for definition in INPUT_DEFINITIONS:
        observation = p2h._recent_diff_observation(definition)
        assert observation.changed_files == [definition["target_path"]]
        assert observation.changed_functions == [definition["target_function"]]
        assert observation.diff_artifact_path == f"patches/{definition['input_id']}.patch"
        assert observation.diff_excerpt
        assert observation.diff_excerpt.startswith("--- a/")
        assert observation.location_scores == {
            definition["target_function"]: p2h.p1b_execution.RECENT_DIFF_LOCATION_WEIGHT
        }
        assert not observation.bug_detected
        assert not observation.no_bug_evidence


def test_coverage_adapter_preserves_accepted_inspection_only_semantics() -> None:
    buggy = INPUT_DEFINITIONS[0]
    modules = p2h._load_modules(p2h._source_for(buggy), "p2h_coverage_test_buggy")
    observation = p2h._run_action("inspect_coverage_spectrum", buggy, modules)
    assert observation.observation_type == "coverage_suspicious_location"
    assert observation.bug_detected
    assert not observation.failure_found
    assert not observation.no_bug_evidence
    assert observation.failed_test_ids == ["coverage.release_equal"]
    assert observation.coverage_suspicion == {"jobs.is_released": 1.0}
    assert observation.location_scores == {"jobs.is_released": 11.0}
    assert observation.coverage_counts["jobs.is_released"] == {
        "failed": 1,
        "passed": 0,
        "total_failed": 1,
    }
    clean = INPUT_DEFINITIONS[-1]
    clean_modules = p2h._load_modules(p2h._source_for(clean), "p2h_coverage_test_clean")
    clean_observation = p2h._run_action("inspect_coverage_spectrum", clean, clean_modules)
    assert not clean_observation.bug_detected
    assert not clean_observation.failure_found
    assert clean_observation.no_bug_evidence
    assert clean_observation.coverage_suspicion == {}
    assert clean_observation.location_scores == {}


def test_manifest_mutation_fails_closed() -> None:
    mutated = deepcopy(build_manifest())
    mutated["inputs"][0]["patch_sha256_lf"] = "0" * 64
    with pytest.raises(p2h.P2HContractError, match="manifest"):
        p2h._validate_manifest_artifacts(mutated)


def test_action_cost_mutation_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    original = P1B_ACTION_SPECS["run_smoke_tests"]
    monkeypatch.setitem(
        P1B_ACTION_SPECS,
        "run_smoke_tests",
        type(original)(
            original.action_id,
            9,
            original.observation_type,
            original.strong_causes,
            original.discovery_power,
            original.location_power,
        ),
    )
    with pytest.raises(p2h.P2HContractError, match="costs"):
        p2h._validate_registry_contract()


def test_action_power_policy_order_and_update_mutations_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = P1B_ACTION_SPECS["run_smoke_tests"]
    monkeypatch.setitem(
        P1B_ACTION_SPECS,
        "run_smoke_tests",
        type(original)(
            original.action_id,
            original.cost,
            original.observation_type,
            original.strong_causes,
            0.99,
            original.location_power,
        ),
    )
    with pytest.raises(p2h.P2HContractError, match="ActionSpec"):
        p2h._validate_registry_contract()
    monkeypatch.undo()
    monkeypatch.setattr(
        p1b_policies,
        "FIXED_CHECKLIST_ORDER",
        tuple(reversed(p1b_policies.FIXED_CHECKLIST_ORDER)),
    )
    with pytest.raises(p2h.P2HContractError, match="ordering"):
        p2h._validate_registry_contract()
    monkeypatch.undo()
    monkeypatch.setattr(p1b_policies, "_update_bug_presence", lambda *_args: 0.5)
    with pytest.raises(p2h.P2HContractError, match="behavior"):
        p2h._validate_registry_contract()


def test_execution_weight_mutation_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(p2h.p1b_execution, "RECENT_DIFF_LOCATION_WEIGHT", 99.0)
    with pytest.raises(p2h.P2HContractError, match="weights"):
        p2h._validate_registry_contract()


def test_pre_outcome_freeze_matches_current_implementation() -> None:
    frozen = p2h.validate_pre_outcome_freeze_identity()
    assert frozen["formal_policy_outcomes_executed_before_freeze"] == 0
    assert frozen["implementation_identity"] == p2h.current_implementation_identity()


def test_exact_90_row_support_and_canonical_order(summary: dict) -> None:
    rows = summary["rows"]
    assert len(rows) == 90
    assert [(row["input_id"], row["policy_id"]) for row in rows] == [
        (input_id, policy) for input_id in INPUT_ORDER for policy in p2h.FORMAL_POLICY_IDS
    ]
    assert sum(row["is_buggy"] for row in rows) == 60
    assert sum(not row["is_buggy"] for row in rows) == 30
    assert summary["support"]["arms"] == ["normal_execution"]


def test_trajectory_budget_actions_trace_and_terminal_partition_recompute(summary: dict) -> None:
    rows = summary["rows"]
    for row in rows:
        assert row["action_count"] == len(row["executed_actions"]) == len(row["trace"])
        assert len(row["executed_actions"]) == len(set(row["executed_actions"]))
        assert row["cumulative_cost"] == sum(
            P1B_ACTION_SPECS[action].cost for action in row["executed_actions"]
        )
        assert row["cumulative_cost"] <= p2h.FIXED_SETTINGS["budget_limit"]
        assert row["action_count"] <= p2h.FIXED_SETTINGS["max_steps"]
        assert row["terminal_reason"] in p2h.EXPECTED_STOP_PRECEDENCE
    terminal_counts = Counter(row["terminal_reason"] for row in rows)
    recorded = summary["aggregates"]["overall"]["terminal_reason_counts"]
    assert sum(recorded.values()) == 90
    assert {key: value for key, value in recorded.items() if value} == dict(terminal_counts)


def test_metrics_and_denominators_recompute_from_rows(summary: dict) -> None:
    rows = summary["rows"]
    buggy = [row for row in rows if row["is_buggy"]]
    clean = [row for row in rows if not row["is_buggy"]]
    overall = summary["aggregates"]["overall"]
    assert overall["buggy_denominator"] == len(buggy) == 60
    assert overall["clean_denominator"] == len(clean) == 30
    for field in (
        "bug_discovery",
        "first_failure_observed",
        "location_top1",
        "location_top3",
        "cause_top1",
        "fix_intent_top1",
    ):
        assert overall[field] == p2h._rate(buggy, field)
    assert overall["clean_false_positive"] == p2h._rate(clean, "clean_false_positive")
    assert summary["identities"]["row_digest"] == p2h.canonical_digest(rows)
    assert summary["identities"]["aggregate_digest"] == p2h.canonical_digest(summary["aggregates"])
    assert p2h.validate_summary(summary) is summary


def test_execution_failure_bug_signal_and_no_bug_evidence_remain_distinct(summary: dict) -> None:
    for row in summary["rows"]:
        observed_failures = any(step["observation"]["failure_found"] for step in row["trace"])
        bug_signals = any(step["observation"]["bug_detected"] for step in row["trace"])
        no_bug_signals = any(step["observation"]["no_bug_evidence"] for step in row["trace"])
        assert row["execution_failure_observed"] == observed_failures
        assert row["bug_detected_observation"] == bug_signals
        assert row["no_bug_evidence_observed"] == no_bug_signals


def test_clean_false_positive_definition_is_recomputable(summary: dict) -> None:
    for row in summary["rows"]:
        if row["is_buggy"]:
            assert row["clean_false_positive"] is None
            continue
        expected = (
            row["terminal_reason"] == "bug_confidence_threshold"
            or row["final_bug_presence_posterior"] >= p2h.FIXED_SETTINGS["bug_presence_threshold"]
        )
        assert row["clean_false_positive"] == expected


def test_summary_has_result_independent_claim_boundary(summary: dict) -> None:
    assert summary["claim_boundary"] == p2h.EXPECTED_CLAIM_BOUNDARY


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda value: value.__setitem__("schema_version", "drift"), "schema_version"),
        (lambda value: value["claim_boundary"].__setitem__("non_causal", False), "claim_boundary"),
        (lambda value: value["rows"][0].__setitem__("bug_discovery", False), "derived field"),
        (
            lambda value: value["aggregates"]["overall"].__setitem__("buggy_denominator", 59),
            "aggregates",
        ),
        (lambda value: value["identities"].__setitem__("row_digest", "0" * 64), "identity"),
        (lambda value: value.__setitem__("summary_digest", "0" * 64), "summary digest"),
    ],
)
def test_summary_mutations_fail_closed(summary: dict, mutation, message: str) -> None:
    changed = deepcopy(summary)
    mutation(changed)
    with pytest.raises(p2h.P2HContractError, match=message):
        p2h.validate_summary(changed)


def test_private_path_mutation_fails_closed(summary: dict) -> None:
    with pytest.raises(p2h.P2HContractError, match="private path"):
        p2h._validate_portable({"path": "C:\\Users\\private\\result.json"})
    changed = deepcopy(summary)
    changed["rows"][0]["trace"][0]["observation"]["summary"] += " C:\\Users\\private"
    changed_without_digest = {key: value for key, value in changed.items() if key != "summary_digest"}
    changed["summary_digest"] = p2h.canonical_digest(changed_without_digest)
    with pytest.raises(p2h.P2HContractError, match="observation"):
        p2h.validate_summary(changed)


def test_hidden_label_in_trace_step_fails_closed(summary: dict) -> None:
    changed = deepcopy(summary)
    changed["rows"][0]["trace"][0]["is_buggy"] = True
    changed["identities"]["row_digest"] = p2h.canonical_digest(changed["rows"])
    changed_without_digest = {key: value for key, value in changed.items() if key != "summary_digest"}
    changed["summary_digest"] = p2h.canonical_digest(changed_without_digest)
    with pytest.raises(p2h.P2HContractError, match="step schema"):
        p2h.validate_summary(changed)
