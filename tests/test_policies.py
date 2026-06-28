from bug_cause_inference.bayes import update, uniform_prior
from bug_cause_inference.policies import ACTIVE_POLICIES, choose_action, run_investigation
from bug_cause_inference.synthetic_cases import generate_synthetic_cases


def test_each_active_policy_selects_an_unexecuted_action():
    case = generate_synthetic_cases()[0]
    posterior = update(uniform_prior(), case.initial_observations)
    executed = ["inspect_error_log"]

    for policy in ACTIVE_POLICIES:
        action = choose_action(policy, posterior, executed, remaining_budget=10)
        assert action is not None
        assert action not in executed


def test_stop_condition_functions():
    case = generate_synthetic_cases()[0]
    result = run_investigation(case, policy="information_gain_per_cost")

    assert result.stop_reason is not None
    assert result.current_step <= 5
    assert result.cumulative_cost <= 10
