from bug_cause_inference.p1b.evaluation import evaluate_p1b
from bug_cause_inference.p1b.policies import P1B_PRIMARY_POLICY


REQUIRED_P1B_METRICS = {
    "bug_discovery_rate_within_budget",
    "cost_to_first_failure",
    "reproduction_success_rate",
    "false_positive_rate_on_clean_cases",
    "false_negative_rate_on_buggy_cases",
    "location_top1_accuracy",
    "location_top3_accuracy",
    "location_mrr",
    "cause_top1_accuracy",
    "cause_top2_accuracy",
    "cost_to_true_cause_top1",
    "wrong_cause_high_confidence_rate",
    "fix_intent_top1_accuracy",
    "fix_intent_top3_accuracy",
    "mean_investigation_cost",
    "cause_brier_score",
}


def test_p1b_evaluation_outputs_required_metrics():
    summary = evaluate_p1b(policies=("fixed_checklist", "expected_utility_per_cost"))

    assert summary["dataset"] == {"total_variants": 25, "buggy_variants": 20, "clean_variants": 5}
    assert summary["primary_policy"] == P1B_PRIMARY_POLICY
    primary = summary["policies"][P1B_PRIMARY_POLICY]
    assert REQUIRED_P1B_METRICS <= set(primary)
    for key in REQUIRED_P1B_METRICS:
        assert primary[key] >= 0
    assert "primary_bug_discovery_rate_at_least_75_percent" in summary["success_checks"]

