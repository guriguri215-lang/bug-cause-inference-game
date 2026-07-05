from bug_cause_inference.p1b.dataset import load_p1b_variants
from bug_cause_inference.p1b.policies import P1B_POLICIES
from bug_cause_inference.p1c.evaluation import (
    HEADLINE_KEYS,
    RAW_WORST_CASE_KEYS,
    evaluate_p1c,
    p1c_evaluation_to_markdown,
)
from bug_cause_inference.p1c.labels import BUGGY_PRIMARY_BUCKETS


def test_p1c_default_evaluation_uses_execution_grounded_and_all_policies():
    summary = evaluate_p1c()

    assert summary["analysis_phase"] == "p1c1_analysis_only_worst_case_report"
    assert summary["observation_mode"] == "execution_grounded"
    assert tuple(summary["policies_evaluated"]) == P1B_POLICIES


def test_p1c_headline_summary_contains_required_keys():
    summary = evaluate_p1c(policies=("expected_utility_per_cost",))
    headline = summary["headline_worst_case_summary"]["expected_utility_per_cost"]

    assert set(HEADLINE_KEYS) <= set(headline)
    for key in HEADLINE_KEYS:
        assert "value" in headline[key]
        assert "bucket_ids" in headline[key]


def test_p1c_raw_worst_case_lists_are_present_and_use_valid_variant_ids():
    summary = evaluate_p1c(policies=("expected_utility_per_cost",))
    valid_ids = {variant.variant_id for variant in load_p1b_variants()}
    raw = summary["raw_variant_worst_cases"]["expected_utility_per_cost"]

    assert set(RAW_WORST_CASE_KEYS) <= set(raw)
    for key in RAW_WORST_CASE_KEYS:
        assert set(raw[key]) <= valid_ids


def test_p1c_markdown_states_analysis_scope_and_primary_mode():
    markdown = p1c_evaluation_to_markdown(evaluate_p1c(policies=("expected_utility_per_cost",)))

    assert "P1c" in markdown
    assert "analysis-only" in markdown
    assert "execution_grounded" in markdown
    assert "does not add new variants" in markdown
    assert "does not" in markdown
    assert "formal game-theoretic guarantee" in markdown
    assert "minimax-optimal" not in markdown


def test_p1c_execution_grounded_bucket_metrics_remain_arithmetic_grounded():
    summary = evaluate_p1c(
        policies=("expected_utility_per_cost",),
        observation_mode="execution_grounded",
    )
    metrics = summary["bucket_metrics"]["expected_utility_per_cost"]

    assert metrics["boundary_precision"]["bucket_bug_discovery_rate"] == 0.25
    assert metrics["boundary_precision"]["bucket_cost_to_first_failure"] == 11
    assert metrics["boundary_precision"]["bucket_location_top3_accuracy"] == 0.75
    assert metrics["boundary_precision"]["bucket_cause_top1_accuracy"] == 1.0
    assert metrics["boundary_precision"]["bucket_fix_intent_top1_accuracy"] == 0.25
    assert metrics["boundary_precision"]["bucket_mean_investigation_cost"] == 4.25

    assert metrics["missing_optional_input"]["bucket_bug_discovery_rate"] == 1.0
    assert metrics["missing_optional_input"]["bucket_cost_to_first_failure"] == 1
    assert metrics["missing_optional_input"]["bucket_mean_investigation_cost"] == 9.75

    assert metrics["state_sequence"]["bucket_bug_discovery_rate"] == 0.0
    assert metrics["state_sequence"]["bucket_cost_to_first_failure"] == 14
    assert metrics["state_sequence"]["bucket_location_top3_accuracy"] == 0.0
    assert metrics["state_sequence"]["bucket_cause_top1_accuracy"] == 0.0
    assert metrics["state_sequence"]["bucket_fix_intent_top1_accuracy"] == 0.0


def test_p1c_average_vs_worst_gap_uses_metric_direction():
    summary = evaluate_p1c(
        policies=("expected_utility_per_cost",),
        observation_mode="execution_grounded",
    )
    gap = summary["average_vs_worst_gap"]["expected_utility_per_cost"]

    discovery = gap["bucket_bug_discovery_rate"]
    assert discovery["direction"] == "higher_is_better"
    assert discovery["average_metric"] == 0.4
    assert discovery["worst_bucket_metric"] == 0.0
    assert discovery["gap"] == round(
        discovery["average_metric"] - discovery["worst_bucket_metric"],
        6,
    )

    failure_cost = gap["bucket_cost_to_first_failure"]
    assert failure_cost["direction"] == "lower_is_better"
    assert failure_cost["average_metric"] == 8.95
    assert failure_cost["worst_bucket_metric"] == 14
    assert failure_cost["gap"] == round(
        failure_cost["worst_bucket_metric"] - failure_cost["average_metric"],
        6,
    )

    mean_cost = gap["bucket_mean_investigation_cost"]
    assert mean_cost["direction"] == "lower_is_better"
    assert mean_cost["average_metric"] == 4.64
    assert mean_cost["worst_bucket_metric"] == 9.75
    assert mean_cost["gap"] == round(mean_cost["worst_bucket_metric"] - mean_cost["average_metric"], 6)


def test_p1c_clean_false_positive_bucket_keeps_buggy_metrics_na():
    summary = evaluate_p1c(
        policies=("expected_utility_per_cost",),
        observation_mode="execution_grounded",
    )
    metrics = summary["bucket_metrics"]["expected_utility_per_cost"]
    clean_metrics = metrics["clean_false_positive"]

    for metric_name in (
        "bucket_bug_discovery_rate",
        "bucket_cost_to_first_failure",
        "bucket_location_top3_accuracy",
        "bucket_cause_top1_accuracy",
        "bucket_fix_intent_top1_accuracy",
        "bucket_wrong_cause_high_confidence_rate",
    ):
        assert clean_metrics[metric_name] is None
    assert clean_metrics["bucket_false_positive_rate"] == 0.0
    assert clean_metrics["bucket_mean_investigation_cost"] == 2

    for bucket in BUGGY_PRIMARY_BUCKETS:
        assert metrics[bucket]["bucket_false_positive_rate"] is None


def test_p1c_both_mode_keeps_execution_grounded_as_primary_report():
    summary = evaluate_p1c(
        policies=("expected_utility_per_cost",),
        observation_mode="both",
    )

    assert summary["observation_mode"] == "both"
    assert summary["primary_observation_mode"] == "execution_grounded"
    assert summary["compared_observation_modes"] == ["execution_grounded", "metadata_synth"]
    assert set(summary["diagnostic_reports_by_observation_mode"]) == {
        "execution_grounded",
        "metadata_synth",
    }

    diagnostics = summary["diagnostic_reports_by_observation_mode"]
    assert summary["bucket_metrics"] == diagnostics["execution_grounded"]["bucket_metrics"]
    assert summary["headline_worst_case_summary"] == diagnostics["execution_grounded"][
        "headline_worst_case_summary"
    ]
    assert diagnostics["metadata_synth"]["observation_mode"] == "metadata_synth"
