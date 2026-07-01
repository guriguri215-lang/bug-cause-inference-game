from bug_cause_inference.p1b.actions import P1B_ACTIONS
from bug_cause_inference.p1b.dataset import get_variant
from bug_cause_inference.p1b.models import P1BSettings
from bug_cause_inference.p1b.policies import P1B_POLICIES, run_p1b_investigation


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

