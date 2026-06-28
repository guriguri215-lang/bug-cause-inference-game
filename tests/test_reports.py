from bug_cause_inference.likelihoods import ACTION_SPECS
from bug_cause_inference.models import StopSettings
from bug_cause_inference.policies import available_actions, run_investigation
from bug_cause_inference.reports import build_decision_report
from bug_cause_inference.synthetic_cases import generate_synthetic_cases


def test_decision_report_json_has_expected_keys():
    case = generate_synthetic_cases()[0]
    result = run_investigation(case, policy="information_gain_per_cost")
    report = build_decision_report(case, result=result)

    expected = {
        "case_id",
        "current_step",
        "stop_or_continue",
        "stop_reason",
        "recommended_next_action",
        "expected_cost",
        "expected_information_gain_per_cost",
        "current_top_hypotheses",
        "why_this_action",
        "counterfactual_notes",
        "known_limits",
    }
    assert expected <= set(report)
    assert "This report does not identify a code location." in report["known_limits"]
    if report["stop_or_continue"] == "stop":
        assert report["recommended_next_action"] is None


def test_decision_report_stop_and_continue_semantics():
    case = generate_synthetic_cases()[0]
    settings = StopSettings()

    continue_report = build_decision_report(case, policy="information_gain_per_cost", settings=settings)
    assert continue_report["stop_or_continue"] == "continue"
    action = continue_report["recommended_next_action"]
    assert action in available_actions([], settings.budget_limit)
    assert ACTION_SPECS[action].cost <= settings.budget_limit

    stop_result = run_investigation(case, policy="information_gain_per_cost", settings=settings)
    stop_report = build_decision_report(case, result=stop_result, settings=settings)
    if stop_report["stop_or_continue"] == "stop":
        assert stop_report["recommended_next_action"] is None
