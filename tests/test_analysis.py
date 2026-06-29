from bug_cause_inference.analysis import (
    TOP_MARGIN_THRESHOLDS,
    TOP_PROBABILITY_THRESHOLDS,
    THRESHOLD_SWEEP_POLICIES,
    analysis_to_markdown,
    build_analysis_summary,
)
from bug_cause_inference.synthetic_cases import generate_synthetic_cases


def test_analysis_summary_contains_required_reports():
    cases = generate_synthetic_cases()
    policies = ("information_gain_per_cost", "fixed_checklist", "posterior_greedy", "information_gain")

    summary = build_analysis_summary(cases, policies=policies)

    assert summary["analysis_scope"]["kind"] == "analysis_only_patch"
    assert summary["analysis_scope"]["model_or_dataset_changed"] is False
    assert "wrong_stop_cases" in summary
    assert "initially_wrong_cases" in summary
    assert "stop_reason_summary" in summary
    assert "category_failure_summary" in summary
    assert "threshold_sweep" in summary
    assert summary["initially_wrong_cases"]
    assert summary["stop_reason_summary"]
    assert summary["category_failure_summary"]


def test_wrong_stop_case_rows_have_expected_fields():
    cases = generate_synthetic_cases()
    summary = build_analysis_summary(cases, policies=("information_gain_per_cost", "fixed_checklist"))

    required = {
        "case_id",
        "true_cause",
        "policy",
        "final_top_hypothesis",
        "final_posterior_probability",
        "top2_hypothesis",
        "top1_top2_margin",
        "cumulative_cost",
        "current_step",
        "stop_reason",
        "executed_actions",
        "observed_evidence_ids",
    }
    assert summary["wrong_stop_cases"]
    assert required <= set(summary["wrong_stop_cases"][0])
    assert all(row["stop_reason"] == "top_probability_threshold" for row in summary["wrong_stop_cases"])


def test_threshold_sweep_shape_and_markdown():
    cases = generate_synthetic_cases()
    summary = build_analysis_summary(cases, policies=("information_gain_per_cost",))

    expected_rows = len(THRESHOLD_SWEEP_POLICIES) * len(TOP_PROBABILITY_THRESHOLDS) * len(TOP_MARGIN_THRESHOLDS)
    assert len(summary["threshold_sweep"]) == expected_rows
    for row in summary["threshold_sweep"]:
        assert 0.0 <= row["success_rate_within_budget"] <= 1.0
        assert 0.0 <= row["wrong_stop_rate"] <= 1.0
        assert 0.0 <= row["initially_wrong_success_rate"] <= 1.0

    markdown = analysis_to_markdown(summary)
    assert "Wrong-Stop Cases" in markdown
    assert "Initially-Wrong Cases" in markdown
    assert "Threshold Sweep" in markdown
