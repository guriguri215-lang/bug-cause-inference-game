from bug_cause_inference.evaluation import evaluate_policies
from bug_cause_inference.policies import PRIMARY_POLICY
from bug_cause_inference.synthetic_cases import generate_synthetic_cases


REQUIRED_POLICY_METRICS = {
    "num_runs",
    "mean_cost_to_true_cause_top1",
    "median_cost_to_true_cause_top1",
    "success_rate_within_budget",
    "success_rate_by_budget",
    "area_under_budget_curve",
    "top_k_accuracy_by_step",
    "brier_score",
    "expected_calibration_error",
    "explanation_omission_test",
    "explanation_trace_completeness",
    "wrong_stop_rate",
    "category_summary",
    "initially_wrong_cases",
}


def _assert_rate(value):
    assert 0.0 <= value <= 1.0


def test_evaluation_metrics_run():
    cases = generate_synthetic_cases()
    policies = ("fixed_checklist", "information_gain_per_cost", "static_posterior", "random")
    summary = evaluate_policies(
        cases,
        policies=policies,
        random_repeats=2,
    )

    assert set(summary["policies"]) == set(policies)
    assert summary["success_checks"]["primary_policy"] == PRIMARY_POLICY
    assert "dataset_diagnostics" in summary
    _assert_rate(summary["dataset_diagnostics"]["initial_top1_accuracy"])
    _assert_rate(summary["dataset_diagnostics"]["initial_top2_accuracy"])

    primary = summary["policies"][PRIMARY_POLICY]
    assert REQUIRED_POLICY_METRICS <= set(primary)
    _assert_rate(primary["success_rate_within_budget"])
    _assert_rate(primary["area_under_budget_curve"])
    _assert_rate(primary["expected_calibration_error"])
    _assert_rate(primary["explanation_trace_completeness"])
    _assert_rate(primary["wrong_stop_rate"])

    for value in primary["success_rate_by_budget"].values():
        _assert_rate(value)
    for step_metrics in primary["top_k_accuracy_by_step"].values():
        for value in step_metrics.values():
            _assert_rate(value)
    for category in primary["category_summary"].values():
        _assert_rate(category["success_rate_within_budget"])
    wrong_cases = primary["initially_wrong_cases"]
    assert wrong_cases["num_runs"] > 0
    _assert_rate(wrong_cases["success_rate_within_budget"])

    success_checks = summary["success_checks"]
    assert isinstance(success_checks["meets_15_percent_fixed_checklist_reduction"], bool)
    assert isinstance(success_checks["primary_success_rate_at_least_80_percent"], bool)
    assert isinstance(success_checks["primary_wrong_stop_rate_under_10_percent_diagnostic"], bool)
    _assert_rate(success_checks["primary_wrong_stop_rate"])
