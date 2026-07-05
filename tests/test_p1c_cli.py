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
    assert "# P1c1 Worst-Case Analysis Report" in markdown
    assert "analysis-only" in markdown
    assert "execution_grounded" in markdown
