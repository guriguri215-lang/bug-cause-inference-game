from bug_cause_inference.p1b.evaluation import evaluate_p1b, p1b_evaluation_to_markdown
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
    "mean_investigation_cost_buggy_only",
    "cause_brier_score",
}


def test_p1b_evaluation_outputs_required_metrics():
    summary = evaluate_p1b(policies=("fixed_checklist", "expected_utility_per_cost"))

    assert summary["observation_mode"] == "metadata_synth"
    assert summary["dataset"] == {"total_variants": 25, "buggy_variants": 20, "clean_variants": 5}
    assert summary["primary_policy"] == P1B_PRIMARY_POLICY
    primary = summary["policies"][P1B_PRIMARY_POLICY]
    assert REQUIRED_P1B_METRICS <= set(primary)
    for key in REQUIRED_P1B_METRICS:
        assert primary[key] >= 0
    assert "primary_bug_discovery_rate_at_least_75_percent" in summary["success_checks"]
    assert isinstance(
        summary["success_checks"]["primary_mean_cost_at_least_10_percent_below_fixed_checklist"],
        bool,
    )


def test_p1b_metadata_synth_primary_baseline_values_remain_frozen():
    summary = evaluate_p1b(policies=("fixed_checklist", "expected_utility_per_cost"))

    primary = summary["policies"][P1B_PRIMARY_POLICY]
    assert summary["observation_mode"] == "metadata_synth"
    assert primary["bug_discovery_rate_within_budget"] == 0.55
    assert primary["false_positive_rate_on_clean_cases"] == 0.0
    assert primary["location_top3_accuracy"] == 0.6
    assert primary["cause_top1_accuracy"] == 0.8
    assert primary["fix_intent_top1_accuracy"] == 0.75
    assert primary["mean_investigation_cost"] == 2.8
    assert summary["success_checks"]["primary_vs_fixed_mean_cost_delta"] == 0.421488


def test_p1b_evaluation_accepts_execution_grounded_mode():
    summary = evaluate_p1b(policies=("expected_utility_per_cost",), observation_mode="execution_grounded")

    assert summary["observation_mode"] == "execution_grounded"
    metrics = summary["policies"][P1B_PRIMARY_POLICY]
    assert metrics["num_variants"] == 25
    assert metrics["false_positive_rate_on_clean_cases"] == 0.0


def test_p1b_execution_grounded_primary_c2_values_remain_frozen():
    summary = evaluate_p1b(
        policies=("fixed_checklist", "expected_utility_per_cost"),
        observation_mode="execution_grounded",
    )

    primary = summary["policies"][P1B_PRIMARY_POLICY]
    assert primary["bug_discovery_rate_within_budget"] == 0.4
    assert primary["false_positive_rate_on_clean_cases"] == 0.0
    assert primary["location_top3_accuracy"] == 0.55
    assert primary["cause_top1_accuracy"] == 0.55
    assert primary["fix_intent_top1_accuracy"] == 0.4
    assert primary["mean_investigation_cost"] == 4.64
    assert summary["success_checks"]["primary_vs_fixed_mean_cost_delta"] == 0.15942


def test_p1b_evaluation_both_mode_contains_policy_metrics_and_deltas():
    summary = evaluate_p1b(
        policies=("fixed_checklist", "expected_utility_per_cost"),
        observation_mode="both",
    )

    assert summary["observation_mode"] == "both"
    assert summary["compared_observation_modes"] == ["metadata_synth", "execution_grounded"]
    assert set(summary["policies_by_observation_mode"]) == {"metadata_synth", "execution_grounded"}
    assert P1B_PRIMARY_POLICY in summary["policies_by_observation_mode"]["metadata_synth"]
    assert P1B_PRIMARY_POLICY in summary["policies_by_observation_mode"]["execution_grounded"]

    comparison = summary["primary_policy_comparison"]["metrics"]
    discovery = comparison["bug_discovery_rate_within_budget"]
    assert discovery["metadata_synth_value"] == 0.55
    assert discovery["execution_grounded_value"] == 0.4
    assert discovery["execution_minus_metadata_delta"] == -0.15
    assert discovery["metadata_optimism_gap"] == 0.15

    mean_cost = comparison["mean_investigation_cost"]
    assert mean_cost["metadata_synth_value"] == 2.8
    assert mean_cost["execution_grounded_value"] == 4.64
    assert mean_cost["execution_minus_metadata_delta"] == 1.84
    assert mean_cost["metadata_optimism_gap"] == 1.84

    cost_delta = comparison["primary_vs_fixed_mean_cost_delta"]
    assert cost_delta["metadata_synth_value"] == 0.421488
    assert cost_delta["execution_grounded_value"] == 0.15942
    assert cost_delta["execution_minus_metadata_delta"] == -0.262068
    assert cost_delta["metadata_optimism_gap"] == 0.262068


def test_p1b_both_markdown_includes_comparison_table_and_phase_b_notes():
    summary = evaluate_p1b(
        policies=("fixed_checklist", "expected_utility_per_cost"),
        observation_mode="both",
    )

    markdown = p1b_evaluation_to_markdown(summary)

    assert "# P1b Evaluation Comparison" in markdown
    assert "| metric | metadata_synth | execution_grounded | execution_minus_metadata_delta | metadata_optimism_gap |" in markdown
    assert "recent-diff signals come from" in markdown
    assert "`inspect_recent_diff` reads Phase C real-diff artifacts" in markdown
    assert "changed files, changed functions, and a diff excerpt" in markdown
