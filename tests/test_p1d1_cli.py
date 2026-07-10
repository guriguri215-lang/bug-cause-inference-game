import json

from bug_cause_inference import cli


def test_p1d1_report_cli_writes_consistent_json_and_markdown(
    tmp_path,
    monkeypatch,
    p1d1_source_and_summary,
):
    _, expected_summary = p1d1_source_and_summary
    json_path = tmp_path / "nested" / "reports" / "p1d1_summary.json"
    markdown_path = tmp_path / "nested" / "reports" / "p1d1_summary.md"
    monkeypatch.setattr(cli, "build_p1d1_summary", lambda: expected_summary)

    cli.main(
        [
            "p1d1-report",
            "--format",
            "json",
            "--json-output",
            str(json_path),
            "--markdown-output",
            str(markdown_path),
        ]
    )

    assert json.loads(json_path.read_text(encoding="utf-8")) == expected_summary
    markdown = markdown_path.read_text(encoding="utf-8")
    assert "# P1d1 Analysis-Only Finite-Game Report" in markdown
    assert str(expected_summary["restricted_pure_solution"]["restricted_pure_security_loss"]) in (
        markdown
    )


def test_p1d1_report_cli_prints_selected_format(
    capsys,
    monkeypatch,
    p1d1_source_and_summary,
):
    _, expected_summary = p1d1_source_and_summary
    monkeypatch.setattr(cli, "build_p1d1_summary", lambda: expected_summary)

    cli.main(["p1d1-report", "--format", "json"])

    printed = json.loads(capsys.readouterr().out)
    assert printed == expected_summary
