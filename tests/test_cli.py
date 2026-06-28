import json

from bug_cause_inference.cli import main
from bug_cause_inference.synthetic_cases import generate_synthetic_cases, save_cases


def test_report_cli_supports_json_only_output(tmp_path):
    cases_path = tmp_path / "cases.json"
    json_path = tmp_path / "report.json"
    save_cases(generate_synthetic_cases(), cases_path)

    main(
        [
            "report",
            "--cases",
            str(cases_path),
            "--case-id",
            "BUG-0001",
            "--json-output",
            str(json_path),
        ]
    )

    assert json_path.exists()
    report = json.loads(json_path.read_text(encoding="utf-8"))
    assert report["case_id"] == "BUG-0001"
    assert "recommended_next_action" in report


def test_evaluate_cli_supports_markdown_only_output(tmp_path):
    cases_path = tmp_path / "cases.json"
    markdown_path = tmp_path / "evaluation.md"
    save_cases(generate_synthetic_cases(), cases_path)

    main(
        [
            "evaluate",
            "--cases",
            str(cases_path),
            "--policies",
            "information_gain_per_cost",
            "--random-repeats",
            "1",
            "--markdown-output",
            str(markdown_path),
        ]
    )

    assert markdown_path.exists()
    markdown = markdown_path.read_text(encoding="utf-8")
    assert "Dataset Diagnostics" in markdown
    assert "information_gain_per_cost" in markdown
