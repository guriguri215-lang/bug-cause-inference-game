from dataclasses import asdict

from bug_cause_inference.p1b.actions import P1B_ACTION_SPECS
from bug_cause_inference.p1b.dataset import get_variant, load_p1b_variants
from bug_cause_inference.p1b.policies import P1B_POLICIES, run_p1b_investigation
from bug_cause_inference.p1c.evaluation import (
    HEADLINE_KEYS,
    RAW_WORST_CASE_KEYS,
    evaluate_p1c,
    p1c_evaluation_to_markdown,
)
from bug_cause_inference.p1c.labels import BUGGY_PRIMARY_BUCKETS, PRIMARY_BUCKETS


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


def test_p1c_adversarial_bucket_selection_shape_is_present():
    summary = evaluate_p1c(policies=("expected_utility_per_cost",))
    selection = summary["adversarial_bucket_selection"]

    assert selection["analysis_phase"] == "p1c3_adversarial_bucket_selection_report"
    assert selection["selector_model"] == "metric_specific_bucket_selection"
    assert selection["primary_observation_mode"] == "execution_grounded"
    assert selection["source_observation_mode"] == "execution_grounded"
    assert "expected_utility_per_cost" in selection["selected_buckets_by_policy"]
    assert selection["clean_false_positive_stress"]["allowed_bucket_set"] == (
        "clean_false_positive_only"
    )


def test_p1c_observation_cost_stress_shape_is_present_and_separate():
    summary = evaluate_p1c(policies=("expected_utility_per_cost",))
    stress = summary["observation_cost_stress"]

    assert stress is not summary["adversarial_bucket_selection"]
    assert stress["analysis_phase"] == "p1c5_bounded_observation_cost_stress_report"
    assert stress["stress_model"] == "bounded_action_cost_overlay"
    assert stress["cost_visibility"] == "policy_visible_overlay"
    assert stress["primary_observation_mode"] == "execution_grounded"
    assert stress["source_observation_mode"] == "execution_grounded"
    assert stress["base_budget_limit"] == 12
    assert stress["base_failure_cost"] == 14
    assert set(stress["results_by_profile"]) == {
        "trace_access_expensive",
        "sequence_reproduction_expensive",
        "localization_evidence_expensive",
        "targeted_reproduction_expensive",
    }
    assert set(stress["profile_conditioned_bucket_selection_by_profile"]) == set(
        stress["results_by_profile"]
    )


def test_p1c_observation_dropout_delay_stress_shape_is_present_and_separate():
    summary = evaluate_p1c(policies=("expected_utility_per_cost",))
    stress = summary["observation_dropout_delay_stress"]

    assert stress is not summary["adversarial_bucket_selection"]
    assert stress is not summary["observation_cost_stress"]
    assert stress["analysis_phase"] == "p1c9_bounded_observation_dropout_delay_stress_report"
    assert stress["stress_model"] == "bounded_observation_visibility_or_delay_profile"
    assert stress["perturbation_visibility"] == "policy_visible_p1c_only"
    assert stress["primary_observation_mode"] == "execution_grounded"
    assert stress["source_observation_mode"] == "execution_grounded"
    assert stress["baseline_source"] == "unperturbed_p1c_report"
    assert stress["report_role"] == "headline_primary"
    assert stress["source_observation_retained"] is True
    assert stress["visible_observation_is_copy"] is True
    assert set(stress["results_by_profile"]) == {
        "traceback_signal_dropout",
        "recent_diff_signal_delay",
        "coverage_signal_dropout",
        "sequence_reproduction_delay",
    }
    assert "profile_conditioned_bucket_selection_by_profile" in summary["observation_cost_stress"]
    assert "profile_conditioned_bucket_selection_by_profile" not in stress


def test_p1c_dropout_delay_profiles_are_bounded_deterministic_and_spec_mapped():
    summary = evaluate_p1c(policies=("expected_utility_per_cost",))
    profiles = {
        profile["profile_id"]: profile
        for profile in summary["observation_dropout_delay_stress"]["profiles"]
    }

    assert profiles["traceback_signal_dropout"]["perturbation_type"] == "dropout"
    assert profiles["traceback_signal_dropout"]["target_action_ids"] == [
        "inspect_traceback",
        "run_null_missing_tests",
    ]
    assert profiles["traceback_signal_dropout"]["target_observation_families"] == [
        "exception_trace"
    ]
    assert profiles["recent_diff_signal_delay"]["perturbation_type"] == "delay"
    assert profiles["recent_diff_signal_delay"]["target_action_ids"] == ["inspect_recent_diff"]
    assert profiles["recent_diff_signal_delay"]["target_observation_families"] == [
        "recent_diff_signal"
    ]
    assert profiles["recent_diff_signal_delay"]["delay_steps"] == 1
    assert profiles["coverage_signal_dropout"]["perturbation_type"] == "dropout"
    assert profiles["coverage_signal_dropout"]["target_action_ids"] == [
        "inspect_coverage_spectrum"
    ]
    assert profiles["coverage_signal_dropout"]["target_observation_families"] == [
        "coverage_suspicious_location"
    ]
    assert profiles["sequence_reproduction_delay"]["perturbation_type"] == "delay"
    assert profiles["sequence_reproduction_delay"]["target_action_ids"] == [
        "run_state_sequence_tests"
    ]
    assert profiles["sequence_reproduction_delay"]["target_observation_families"] == [
        "state_sequence_counterexample"
    ]
    assert profiles["sequence_reproduction_delay"]["delay_steps"] == 1
    for profile in profiles.values():
        assert profile["bounded"] is True
        assert profile["deterministic"] is True
        assert profile["source_observation_retained"] is True
        assert profile["visible_observation_is_copy"] is True
        assert "deterministic_rule" in profile


def test_p1c_cost_profiles_are_bounded_and_do_not_mutate_default_costs():
    before_costs = {action_id: spec.cost for action_id, spec in P1B_ACTION_SPECS.items()}

    summary = evaluate_p1c(policies=("expected_utility_per_cost",))

    after_costs = {action_id: spec.cost for action_id, spec in P1B_ACTION_SPECS.items()}
    assert after_costs == before_costs
    for profile in summary["observation_cost_stress"]["profiles"]:
        cost_range = profile["cost_range"]
        assert 1 <= cost_range["min"] <= cost_range["max"] <= 8
        assert all(1 <= cost <= 8 for cost in profile["effective_costs_by_action"].values())


def test_p1c_dropout_delay_report_does_not_mutate_p1b_defaults():
    before_specs = {action_id: asdict(spec) for action_id, spec in P1B_ACTION_SPECS.items()}
    variant = get_variant("P1B-BUG-001")
    before_result = run_p1b_investigation(
        variant,
        policy="expected_utility_per_cost",
        observation_mode="execution_grounded",
    ).to_dict()

    evaluate_p1c(policies=("expected_utility_per_cost",))

    after_specs = {action_id: asdict(spec) for action_id, spec in P1B_ACTION_SPECS.items()}
    after_result = run_p1b_investigation(
        variant,
        policy="expected_utility_per_cost",
        observation_mode="execution_grounded",
    ).to_dict()
    assert after_specs == before_specs
    assert after_result == before_result


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


def test_p1c_markdown_includes_p1c3_section_and_scope_notes():
    markdown = p1c_evaluation_to_markdown(evaluate_p1c(policies=("expected_utility_per_cost",)))

    assert "## P1c3 Adversarial Bucket Selection" in markdown
    assert "metric-specific and policy-aware" in markdown
    assert "weighted payoff" in markdown
    assert "regret" in markdown
    assert "minimax" in markdown
    assert "equilibrium" in markdown
    assert "`metadata_synth` remains diagnostic" in markdown
    assert "### Clean False-Positive Stress" in markdown


def test_p1c_markdown_includes_p1c5_section_and_non_claim_notes():
    markdown = p1c_evaluation_to_markdown(evaluate_p1c(policies=("expected_utility_per_cost",)))

    assert "## P1c5 Observation-Cost Stress" in markdown
    assert "bounded action-cost overlay" in markdown
    assert "policy-visible" in markdown
    assert "Profile-Vs-Baseline Gaps" in markdown
    assert "Profile-Conditioned Bucket Selection" in markdown
    assert "Profile-Conditioned Clean False-Positive Stress" in markdown
    assert "Clean False-Positive Cost Stress" in markdown
    assert "Scope/Non-Claim Notes" in markdown
    assert "separate slice from P1c3" in markdown
    assert "does not replace top-level `adversarial_bucket_selection`" in markdown
    assert "does not introduce a single weighted payoff" in markdown
    assert "formal payoff model" in markdown


def test_p1c_markdown_includes_p1c9_section_and_scope_notes():
    markdown = p1c_evaluation_to_markdown(evaluate_p1c(policies=("expected_utility_per_cost",)))

    assert "## P1c9 Observation Dropout/Delay Stress" in markdown
    assert "bounded observation dropout/delay report" in markdown
    assert "source observations are retained" in markdown
    assert "policy-facing visible observations are copied" in markdown
    assert "Profile-Vs-Baseline Gaps" in markdown
    assert "Recovery Diagnostics" in markdown
    assert "Clean False-Positive Dropout/Delay Stress" in markdown
    assert "separate from P1c3 adversarial_bucket_selection" in markdown
    assert "P1c7 profile_conditioned_bucket_selection_by_profile remains nested" in markdown
    assert "does not introduce a single weighted payoff" in markdown
    assert "formal payoff model" in markdown


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


def test_p1c_adversarial_bucket_selection_uses_metric_specific_rules():
    summary = evaluate_p1c(
        policies=("expected_utility_per_cost",),
        observation_mode="execution_grounded",
    )
    selected = summary["adversarial_bucket_selection"]["selected_buckets_by_policy"][
        "expected_utility_per_cost"
    ]

    for metric_name in (
        "bucket_bug_discovery_rate",
        "bucket_location_top3_accuracy",
        "bucket_cause_top1_accuracy",
        "bucket_fix_intent_top1_accuracy",
    ):
        row = selected[metric_name]
        assert row["allowed_bucket_set"] == "buggy_primary_buckets"
        assert "clean_false_positive" not in row["allowed_bucket_ids"]
        assert row["selected_bucket_ids"] == ["state_sequence"]
        assert row["selected_value"] == 0.0
        assert row["diagnostic_variant_ids"] == [
            "P1B-BUG-013",
            "P1B-BUG-014",
            "P1B-BUG-015",
            "P1B-BUG-016",
        ]

    mean_cost = selected["bucket_mean_investigation_cost"]
    assert mean_cost["allowed_bucket_set"] == "all_primary_buckets"
    assert mean_cost["selected_bucket_ids"] == ["missing_optional_input"]
    assert mean_cost["selected_value"] == 9.75
    assert mean_cost["selected_bucket_types"] == {"missing_optional_input": "buggy"}


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


def test_p1c_clean_false_positive_stress_is_reported_separately():
    summary = evaluate_p1c(
        policies=("expected_utility_per_cost",),
        observation_mode="execution_grounded",
    )
    stress = summary["adversarial_bucket_selection"]["clean_false_positive_stress"]
    row = stress["by_policy"]["expected_utility_per_cost"]

    assert stress["allowed_bucket_set"] == "clean_false_positive_only"
    assert stress["selected_bucket_ids"] == ["clean_false_positive"]
    assert row["allowed_bucket_set"] == "clean_false_positive_only"
    assert row["selected_value"] == 0.0
    assert row["diagnostic_variant_ids"] == []
    assert "not triggered" in row["note"]


def test_p1c_observation_cost_clean_false_positive_stress_stays_separate():
    summary = evaluate_p1c(
        policies=("expected_utility_per_cost",),
        observation_mode="execution_grounded",
    )
    stress = summary["observation_cost_stress"]

    for profile_id, rows_by_policy in stress["clean_false_positive_stress_by_policy"].items():
        row = rows_by_policy["expected_utility_per_cost"]
        assert row["allowed_bucket_set"] == "clean_false_positive_only"
        assert row["selected_bucket_ids"] == ["clean_false_positive"]
        assert row["false_positive_rate_on_clean_cases"] == 0.0
        assert row["diagnostic_variant_ids"] == []

        clean_metrics = stress["results_by_profile"][profile_id]["bucket_metrics_by_policy"][
            "expected_utility_per_cost"
        ]["clean_false_positive"]
        assert clean_metrics["bucket_bug_discovery_rate"] is None
        assert clean_metrics["bucket_location_top3_accuracy"] is None
        assert clean_metrics["bucket_cause_top1_accuracy"] is None
        assert clean_metrics["bucket_false_positive_rate"] == 0.0


def test_p1c_observation_dropout_delay_clean_false_positive_stress_stays_separate():
    summary = evaluate_p1c(
        policies=("expected_utility_per_cost",),
        observation_mode="execution_grounded",
    )
    stress = summary["observation_dropout_delay_stress"]

    for profile_id, rows_by_policy in stress["clean_false_positive_stress_by_policy"].items():
        row = rows_by_policy["expected_utility_per_cost"]
        assert row["allowed_bucket_set"] == "clean_false_positive_only"
        assert row["selected_bucket_ids"] == ["clean_false_positive"]
        assert row["false_positive_rate_on_clean_cases"] == 0.0
        assert row["diagnostic_variant_ids"] == []
        assert "not triggered" in row["note"]

        clean_metrics = stress["results_by_profile"][profile_id]["bucket_metrics_by_policy"][
            "expected_utility_per_cost"
        ]["clean_false_positive"]
        for metric_name in (
            "bucket_bug_discovery_rate",
            "bucket_cost_to_first_failure",
            "bucket_location_top3_accuracy",
            "bucket_cause_top1_accuracy",
            "bucket_fix_intent_top1_accuracy",
            "bucket_wrong_cause_high_confidence_rate",
        ):
            assert clean_metrics[metric_name] is None
        for bucket in BUGGY_PRIMARY_BUCKETS:
            bucket_metrics = stress["results_by_profile"][profile_id]["bucket_metrics_by_policy"][
                "expected_utility_per_cost"
            ][bucket]
            assert bucket_metrics["bucket_false_positive_rate"] is None


def test_p1c_observation_dropout_delay_recovery_diagnostics_are_auditable():
    summary = evaluate_p1c(policies=("expected_utility_per_cost",))
    stress = summary["observation_dropout_delay_stress"]
    diagnostics = stress["recovery_diagnostics_by_policy"]

    for profile_id, rows_by_policy in diagnostics.items():
        row = rows_by_policy["expected_utility_per_cost"]
        assert "source_observation_count" in row
        assert "perturbed_observation_count" in row
        assert "dropout_applied_count" in row
        assert "delayed_payload_count" in row
        assert "delayed_payload_released_count" in row
        assert "delayed_payload_stop_before_release_count" in row
        assert "recovery_rate_after_missing_observation" in row
        assert "delayed_evidence_released_rate" in row
        assert "stop_before_delayed_evidence_rate" in row
        assert row["source_observation_count"] >= row["perturbed_observation_count"]
        if profile_id.endswith("_dropout"):
            assert row["dropout_applied_count"] == row["perturbed_observation_count"]
            assert row["delayed_payload_count"] == 0
            assert row["delayed_evidence_released_rate"] is None
        if profile_id.endswith("_delay") and row["delayed_payload_count"] == 0:
            assert row["delayed_evidence_released_rate"] is None


def test_p1c_profile_conditioned_bucket_selection_matches_p1c3_baseline():
    summary = evaluate_p1c(
        policies=("expected_utility_per_cost",),
        observation_mode="execution_grounded",
    )
    baseline = summary["adversarial_bucket_selection"]["selected_buckets_by_policy"][
        "expected_utility_per_cost"
    ]
    profile_reports = summary["observation_cost_stress"][
        "profile_conditioned_bucket_selection_by_profile"
    ]

    assert set(profile_reports) == {
        "trace_access_expensive",
        "sequence_reproduction_expensive",
        "localization_evidence_expensive",
        "targeted_reproduction_expensive",
    }
    for profile_id, report in profile_reports.items():
        assert report["analysis_phase"] == "p1c7_profile_conditioned_bucket_selection_report"
        assert report["selector_model"] == (
            "profile_conditioned_metric_specific_bucket_selection"
        )
        assert report["source_profile_id"] == profile_id
        assert report["baseline_selection_source"] == "adversarial_bucket_selection"
        assert report["primary_observation_mode"] == "execution_grounded"
        assert report["source_observation_mode"] == "execution_grounded"

        selected = report["selected_buckets_by_policy"]["expected_utility_per_cost"]
        for metric_name, baseline_row in baseline.items():
            row = selected[metric_name]
            assert row["baseline_selected_bucket_ids"] == baseline_row["selected_bucket_ids"]
            assert row["baseline_selected_value"] == baseline_row["selected_value"]
            assert isinstance(row["bucket_shifted_from_baseline"], bool)


def test_p1c_profile_conditioned_selection_keeps_bucket_sets_separate():
    summary = evaluate_p1c(
        policies=("expected_utility_per_cost",),
        observation_mode="execution_grounded",
    )
    report = summary["observation_cost_stress"]["profile_conditioned_bucket_selection_by_profile"][
        "trace_access_expensive"
    ]
    selected = report["selected_buckets_by_policy"]["expected_utility_per_cost"]

    for metric_name in (
        "bucket_bug_discovery_rate",
        "bucket_cost_to_first_failure",
        "bucket_location_top3_accuracy",
        "bucket_cause_top1_accuracy",
        "bucket_fix_intent_top1_accuracy",
        "bucket_wrong_cause_high_confidence_rate",
    ):
        row = selected[metric_name]
        assert row["allowed_bucket_set"] == "buggy_primary_buckets"
        assert tuple(row["allowed_bucket_ids"]) == BUGGY_PRIMARY_BUCKETS
        assert "clean_false_positive" not in row["profile_selected_bucket_ids"]

    mean_cost = selected["bucket_mean_investigation_cost"]
    assert mean_cost["allowed_bucket_set"] == "all_primary_buckets"
    assert tuple(mean_cost["allowed_bucket_ids"]) == PRIMARY_BUCKETS
    assert "profile_selected_bucket_types" in mean_cost
    assert set(mean_cost["profile_selected_bucket_types"].values()) <= {"buggy", "clean"}

    clean = report["clean_false_positive_stress"]
    clean_row = clean["by_policy"]["expected_utility_per_cost"]
    assert clean["allowed_bucket_set"] == "clean_false_positive_only"
    assert clean["selected_bucket_ids"] == ["clean_false_positive"]
    assert clean_row["baseline_false_positive_rate"] == 0.0
    assert clean_row["profile_false_positive_rate"] == 0.0
    assert clean_row["profile_vs_baseline_gap"] == 0.0
    assert clean_row["diagnostic_variant_ids"] == []
    assert "not triggered" in clean_row["note"]


def test_p1c_profile_conditioned_gap_uses_metric_direction():
    summary = evaluate_p1c(
        policies=("expected_utility_per_cost",),
        observation_mode="execution_grounded",
    )
    report = summary["observation_cost_stress"]["profile_conditioned_bucket_selection_by_profile"][
        "trace_access_expensive"
    ]
    selected = report["selected_buckets_by_policy"]["expected_utility_per_cost"]

    discovery = selected["bucket_bug_discovery_rate"]
    assert discovery["direction"] == "higher_is_better"
    assert discovery["profile_vs_baseline_selected_value_gap"] == round(
        discovery["baseline_selected_value"] - discovery["profile_selected_value"],
        6,
    )

    mean_cost = selected["bucket_mean_investigation_cost"]
    assert mean_cost["direction"] == "lower_is_better"
    assert mean_cost["profile_vs_baseline_selected_value_gap"] == round(
        mean_cost["profile_selected_value"] - mean_cost["baseline_selected_value"],
        6,
    )


def test_p1c_observation_cost_report_avoids_formal_payoff_fields():
    summary = evaluate_p1c(policies=("expected_utility_per_cost",))
    stress_text = str(summary["observation_cost_stress"])

    for forbidden_key in (
        "'weighted_payoff'",
        "'regret'",
        "'minimax'",
        "'equilibrium'",
        "'formal_payoff'",
    ):
        assert forbidden_key not in stress_text
    assert "does not introduce a single weighted payoff" in " ".join(
        summary["observation_cost_stress"]["notes"]
    )


def test_p1c_observation_dropout_delay_report_avoids_formal_payoff_fields():
    summary = evaluate_p1c(policies=("expected_utility_per_cost",))
    stress_text = str(summary["observation_dropout_delay_stress"])

    for forbidden_key in (
        "'weighted_payoff'",
        "'regret'",
        "'minimax'",
        "'equilibrium'",
        "'formal_payoff'",
    ):
        assert forbidden_key not in stress_text
    assert "does not introduce a single weighted payoff" in " ".join(
        summary["observation_dropout_delay_stress"]["notes"]
    )


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
    assert summary["adversarial_bucket_selection"] == diagnostics["execution_grounded"][
        "adversarial_bucket_selection"
    ]
    assert summary["adversarial_bucket_selection"]["source_observation_mode"] == "execution_grounded"
    assert diagnostics["metadata_synth"]["observation_mode"] == "metadata_synth"


def test_p1c_both_mode_keeps_observation_cost_execution_grounded_primary():
    summary = evaluate_p1c(
        policies=("expected_utility_per_cost",),
        observation_mode="both",
    )
    stress = summary["observation_cost_stress"]
    diagnostics = summary["diagnostic_reports_by_observation_mode"]

    assert stress == diagnostics["execution_grounded"]["observation_cost_stress"]
    assert stress["primary_observation_mode"] == "execution_grounded"
    assert stress["source_observation_mode"] == "execution_grounded"
    assert stress["report_role"] == "headline_primary"
    assert diagnostics["metadata_synth"]["observation_cost_stress"]["report_role"] == "diagnostic"
    assert diagnostics["metadata_synth"]["observation_cost_stress"]["source_observation_mode"] == (
        "metadata_synth"
    )
    assert stress["profile_conditioned_bucket_selection_by_profile"] == diagnostics[
        "execution_grounded"
    ]["observation_cost_stress"]["profile_conditioned_bucket_selection_by_profile"]
    metadata_profile_reports = diagnostics["metadata_synth"]["observation_cost_stress"][
        "profile_conditioned_bucket_selection_by_profile"
    ]
    for report in metadata_profile_reports.values():
        assert report["report_role"] == "diagnostic"
        assert report["source_observation_mode"] == "metadata_synth"


def test_p1c_both_mode_keeps_observation_dropout_delay_execution_grounded_primary():
    summary = evaluate_p1c(
        policies=("expected_utility_per_cost",),
        observation_mode="both",
    )
    stress = summary["observation_dropout_delay_stress"]
    diagnostics = summary["diagnostic_reports_by_observation_mode"]

    assert stress == diagnostics["execution_grounded"]["observation_dropout_delay_stress"]
    assert stress["primary_observation_mode"] == "execution_grounded"
    assert stress["source_observation_mode"] == "execution_grounded"
    assert stress["report_role"] == "headline_primary"
    metadata_stress = diagnostics["metadata_synth"]["observation_dropout_delay_stress"]
    assert metadata_stress["report_role"] == "diagnostic"
    assert metadata_stress["source_observation_mode"] == "metadata_synth"
    assert "metadata_synth" not in stress["diagnostic_reports_by_observation_mode"]
