import json

from bug_cause_inference.cli import main


def test_p1c_evaluate_cli_writes_json_and_markdown(tmp_path):
    json_path = tmp_path / "nested" / "reports" / "p1c_summary.json"
    markdown_path = tmp_path / "nested" / "reports" / "p1c_summary.md"

    main(
        [
            "p1c-evaluate",
            "--policies",
            "expected_utility_per_cost",
            "--json-output",
            str(json_path),
            "--markdown-output",
            str(markdown_path),
        ]
    )

    assert json_path.exists()
    assert markdown_path.exists()

    summary = json.loads(json_path.read_text(encoding="utf-8"))
    markdown = markdown_path.read_text(encoding="utf-8")

    assert summary["observation_mode"] == "execution_grounded"
    assert "bucket_metrics" in summary
    assert "headline_worst_case_summary" in summary
    assert "raw_variant_worst_cases" in summary
    assert "average_vs_worst_gap" in summary
    assert summary["adversarial_bucket_selection"]["selector_model"] == (
        "metric_specific_bucket_selection"
    )
    assert summary["observation_cost_stress"]["stress_model"] == "bounded_action_cost_overlay"
    assert summary["observation_cost_stress"]["cost_visibility"] == "policy_visible_overlay"
    assert summary["observation_cost_stress"]["primary_observation_mode"] == "execution_grounded"
    assert "profile_conditioned_bucket_selection_by_profile" in summary["observation_cost_stress"]
    assert summary["observation_dropout_delay_stress"]["stress_model"] == (
        "bounded_observation_visibility_or_delay_profile"
    )
    assert summary["observation_dropout_delay_stress"]["perturbation_visibility"] == (
        "policy_visible_p1c_only"
    )
    assert summary["observation_dropout_delay_stress"]["primary_observation_mode"] == (
        "execution_grounded"
    )
    assert set(summary["observation_dropout_delay_stress"]["results_by_profile"]) == {
        "traceback_signal_dropout",
        "recent_diff_signal_delay",
        "coverage_signal_dropout",
        "sequence_reproduction_delay",
    }
    assert "# P1c1 Worst-Case Analysis Report" in markdown
    assert "## P1c3 Adversarial Bucket Selection" in markdown
    assert "## P1c5 Observation-Cost Stress" in markdown
    assert "## P1c9 Observation Dropout/Delay Stress" in markdown
    assert "### Profile-Conditioned Bucket Selection" in markdown
    assert "Scope/Non-Claim Notes" in markdown
    assert "### Clean False-Positive Stress" in markdown
    assert "### Profile-Conditioned Clean False-Positive Stress" in markdown
    assert "### Clean False-Positive Cost Stress" in markdown
    assert "### Recovery Diagnostics" in markdown
    assert "### Clean False-Positive Dropout/Delay Stress" in markdown
    assert "analysis-only" in markdown
    assert "execution_grounded" in markdown
