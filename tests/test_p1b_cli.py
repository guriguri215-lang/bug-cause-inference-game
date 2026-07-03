import json

from bug_cause_inference.cli import main


def test_p1b_report_cli_generates_json_and_markdown(tmp_path):
    json_path = tmp_path / "p1b_report.json"
    markdown_path = tmp_path / "p1b_report.md"

    main(
        [
            "p1b-report",
            "--variant-id",
            "P1B-BUG-001",
            "--json-output",
            str(json_path),
            "--markdown-output",
            str(markdown_path),
        ]
    )

    report = json.loads(json_path.read_text(encoding="utf-8"))
    assert report["variant"]["variant_id"] == "P1B-BUG-001"
    assert "location_ranking" in report
    assert "fix_intent_prediction" in report
    assert "P1b Report" in markdown_path.read_text(encoding="utf-8")


def test_p1b_evaluate_cli_outputs_major_metrics(tmp_path):
    json_path = tmp_path / "p1b_eval.json"

    main(["p1b-evaluate", "--policies", "expected_utility_per_cost", "--json-output", str(json_path)])

    summary = json.loads(json_path.read_text(encoding="utf-8"))
    assert summary["observation_mode"] == "metadata_synth"
    metrics = summary["policies"]["expected_utility_per_cost"]
    assert "bug_discovery_rate_within_budget" in metrics
    assert "location_top3_accuracy" in metrics
    assert "fix_intent_top1_accuracy" in metrics


def test_p1b_evaluate_cli_accepts_execution_grounded_mode(tmp_path):
    json_path = tmp_path / "p1b_eval_execution.json"

    main(
        [
            "p1b-evaluate",
            "--policies",
            "expected_utility_per_cost",
            "--observation-mode",
            "execution_grounded",
            "--json-output",
            str(json_path),
        ]
    )

    summary = json.loads(json_path.read_text(encoding="utf-8"))
    assert summary["observation_mode"] == "execution_grounded"
    assert summary["policies"]["expected_utility_per_cost"]["num_variants"] == 25


def test_p1b_list_variants_cli_can_save_dataset(tmp_path):
    output = tmp_path / "variants.json"

    main(["p1b-list-variants", "--output", str(output), "--json-output", str(tmp_path / "list.json")])

    variants = json.loads(output.read_text(encoding="utf-8"))
    assert len(variants) == 25
