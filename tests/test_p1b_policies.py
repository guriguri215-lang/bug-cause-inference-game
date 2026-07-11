import inspect
import pytest

from bug_cause_inference.p1b.actions import P1B_ACTIONS
from bug_cause_inference.p1b.dataset import get_variant
from bug_cause_inference.p1b.models import P1BSettings, uniform_distribution
from bug_cause_inference.p1b import policies
from bug_cause_inference.p1b.policies import (
    P1B_POLICIES,
    P1B_PRIMARY_POLICY,
    STATE_SEQUENCE_GUARD_POLICY_ID,
    run_p1b_investigation,
)


def test_p1b_each_policy_executes_known_actions_without_repeats():
    variant = get_variant("P1B-BUG-001")

    for policy in P1B_POLICIES:
        result = run_p1b_investigation(variant, policy=policy, settings=P1BSettings())
        assert result.executed_actions
        assert len(result.executed_actions) == len(set(result.executed_actions))
        assert set(result.executed_actions) <= set(P1B_ACTIONS)
        assert result.cumulative_cost <= P1BSettings().budget_limit


def test_p1b_stop_condition_runs():
    variant = get_variant("P1B-CLEAN-021")
    result = run_p1b_investigation(variant, policy="fixed_checklist", settings=P1BSettings())

    assert result.stop_reason is not None
    assert result.current_step <= P1BSettings().max_steps


def _history(
    *,
    executed=(),
    remaining_budget=12,
    current_step=0,
    bug_detected=False,
):
    state = policies._State(
        bug_presence=0.5,
        cause_posterior=uniform_distribution(("a", "b")),
        location_posterior=uniform_distribution(("x", "y")),
        fix_intent_posterior=uniform_distribution(("f", "g")),
        executed_actions=list(executed),
        cumulative_cost=12 - remaining_budget,
        current_step=current_step,
        bug_detected=bug_detected,
    )
    return policies._state_sequence_guard_history(state)


def test_state_sequence_guard_is_p1d2_only_and_has_hidden_information_safe_interface():
    assert STATE_SEQUENCE_GUARD_POLICY_ID not in P1B_POLICIES
    assert P1B_PRIMARY_POLICY == "expected_utility_per_cost"
    assert tuple(inspect.signature(policies._choose_state_sequence_guard).parameters) == (
        "history",
        "remaining_budget",
    )
    assert "execution_context" not in policies._StateSequenceGuardHistory.__dataclass_fields__
    assert not {
        "variant_id",
        "bucket_id",
        "ground_truth",
        "report",
    } & set(policies._StateSequenceGuardHistory.__dataclass_fields__)


def test_state_sequence_guard_preserves_reserve_and_forces_target_at_exact_boundaries(
    monkeypatch,
):
    target = "run_state_sequence_tests"
    selected = policies._choose_state_sequence_guard(_history(), 12)
    if selected != target:
        assert policies.P1B_ACTION_SPECS[selected].cost <= 8

    assert policies._choose_state_sequence_guard(_history(remaining_budget=4), 4) == target
    monkeypatch.setattr(
        policies,
        "score_actions",
        lambda state, budget: [
            {"action": "run_smoke_tests", "cost": 1},
            {"action": target, "cost": 4},
        ],
    )
    assert policies._choose_state_sequence_guard(_history(current_step=4), 12) == (
        "run_smoke_tests"
    )
    assert policies._choose_state_sequence_guard(_history(current_step=5), 12) == target


def test_state_sequence_guard_candidate_pool_uses_existing_rank_and_release_fallback(monkeypatch):
    ranked = [
        {"action": "run_state_sequence_tests", "cost": 4},
        {"action": "run_smoke_tests", "cost": 1},
    ]
    monkeypatch.setattr(policies, "score_actions", lambda state, budget: ranked)
    assert policies._choose_state_sequence_guard(_history(), 12) == "run_state_sequence_tests"

    fallback_ranked = [
        {"action": "inspect_traceback", "cost": 1},
        {"action": "run_state_sequence_tests", "cost": 4},
    ]
    monkeypatch.setattr(policies, "score_actions", lambda state, budget: fallback_ranked)
    assert (
        policies._choose_state_sequence_guard(_history(bug_detected=True), 12)
        == "inspect_traceback"
    )
    assert (
        policies._choose_state_sequence_guard(
            _history(executed=("run_state_sequence_tests",)), 12
        )
        == "inspect_traceback"
    )

    unaffordable_ranked = [{"action": "inspect_traceback", "cost": 1}]
    monkeypatch.setattr(policies, "score_actions", lambda state, budget: unaffordable_ranked)
    assert (
        policies._choose_state_sequence_guard(_history(remaining_budget=3), 3)
        == "inspect_traceback"
    )


def test_state_sequence_guard_uses_rounded_score_cost_action_id_order_and_entropy_guards():
    state = policies._State(
        bug_presence=0.5,
        cause_posterior=uniform_distribution(("a", "b")),
        location_posterior=uniform_distribution(("x", "y")),
        fix_intent_posterior=uniform_distribution(("f", "g")),
        executed_actions=[],
        cumulative_cost=0,
        current_step=0,
        bug_detected=False,
    )
    scores = policies.score_actions(state, 12)
    assert scores == sorted(
        scores,
        key=lambda item: (
            -item["expected_utility_per_cost"],
            item["cost"],
            item["action"],
        ),
    )
    assert policies._entropy({}) == 0.0
    assert policies._entropy({"only": 1.0}) == 0.0


@pytest.mark.parametrize(
    "reason",
    [
        "no_bug_probability_threshold",
        "bug_confidence_threshold",
        "budget_limit",
        "max_steps",
        "low_expected_utility",
    ],
)
def test_common_stop_precedes_state_sequence_guard_selector(monkeypatch, reason):
    monkeypatch.setattr(policies, "_check_stop", lambda state, settings, best_score: reason)

    def fail_selector(*args, **kwargs):
        raise AssertionError("selector must not run after a common stop")

    monkeypatch.setattr(policies, "_choose_state_sequence_guard", fail_selector)
    result = run_p1b_investigation(
        get_variant("P1B-BUG-001"),
        policy=STATE_SEQUENCE_GUARD_POLICY_ID,
        settings=P1BSettings(),
    )
    assert result.stop_reason == reason
    assert result.executed_actions == []


def test_low_expected_utility_uses_all_feasible_scores_before_reserve_filter(monkeypatch):
    monkeypatch.setattr(
        policies,
        "score_actions",
        lambda state, budget: [
            {
                "action": "run_property_search",
                "cost": 5,
                "expected_utility_per_cost": 0.02,
            }
        ],
    )

    def fail_selector(*args, **kwargs):
        raise AssertionError("reserve-filtered selection must not precede low-utility stop")

    monkeypatch.setattr(policies, "_choose_state_sequence_guard", fail_selector)
    result = run_p1b_investigation(
        get_variant("P1B-BUG-001"),
        policy=STATE_SEQUENCE_GUARD_POLICY_ID,
        settings=P1BSettings(min_expected_utility_per_cost=0.03),
    )
    assert result.stop_reason == "low_expected_utility"


def test_state_sequence_guard_nonterminal_run_returns_only_feasible_unique_actions():
    result = run_p1b_investigation(
        get_variant("P1B-BUG-013"),
        policy=STATE_SEQUENCE_GUARD_POLICY_ID,
        settings=P1BSettings(),
        observation_mode="execution_grounded",
    )
    assert result.executed_actions
    assert len(result.executed_actions) == len(set(result.executed_actions))
    assert set(result.executed_actions) <= set(P1B_ACTIONS)
    assert result.cumulative_cost <= 12


def test_existing_six_deterministic_policy_representative_traces_are_unchanged():
    expected = {
        "fixed_checklist": [
            "run_smoke_tests",
            "run_boundary_tests",
            "run_null_missing_tests",
            "run_config_matrix_tests",
            "run_state_sequence_tests",
        ],
        "test_first": [
            "run_smoke_tests",
            "run_boundary_tests",
            "run_null_missing_tests",
            "run_config_matrix_tests",
            "run_state_sequence_tests",
        ],
        "coverage_first": [
            "run_smoke_tests",
            "inspect_coverage_spectrum",
            "run_boundary_tests",
            "run_null_missing_tests",
            "run_config_matrix_tests",
            "inspect_traceback",
        ],
        "recent_diff_first": [
            "inspect_recent_diff",
            "run_smoke_tests",
            "run_boundary_tests",
            "run_config_matrix_tests",
            "run_null_missing_tests",
            "inspect_spec_clause",
        ],
        "cause_only_p1a_style": [
            "inspect_traceback",
            "run_smoke_tests",
            "inspect_spec_clause",
            "inspect_recent_diff",
            "run_boundary_tests",
            "run_null_missing_tests",
        ],
        "expected_utility_per_cost": [
            "inspect_traceback",
            "run_smoke_tests",
            "inspect_spec_clause",
            "inspect_recent_diff",
            "run_boundary_tests",
            "inspect_coverage_spectrum",
        ],
    }
    variant = get_variant("P1B-BUG-001")
    for policy, expected_actions in expected.items():
        result = run_p1b_investigation(
            variant,
            policy=policy,
            settings=P1BSettings(),
            observation_mode="execution_grounded",
        )
        assert result.executed_actions == expected_actions

