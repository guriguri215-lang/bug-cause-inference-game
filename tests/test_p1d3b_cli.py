from __future__ import annotations

import json

from bug_cause_inference import cli


def _summary():
    return {"sentinel": "summary"}


def test_p1d3b_cli_stdout_json(monkeypatch, capsys):
    monkeypatch.setattr(cli, "build_p1d3b_summary", _summary)
    monkeypatch.setattr(cli, "p1d3b_summary_to_json", lambda value: json.dumps(value) + "\n")
    monkeypatch.setattr(cli, "p1d3b_summary_to_markdown", lambda value: "# sentinel\n")
    cli.main(["p1d3b-report", "--format", "json"])
    assert capsys.readouterr().out == '{"sentinel": "summary"}\n'


def test_p1d3b_cli_stdout_markdown(monkeypatch, capsys):
    monkeypatch.setattr(cli, "build_p1d3b_summary", _summary)
    monkeypatch.setattr(cli, "p1d3b_summary_to_json", lambda value: "{}\n")
    monkeypatch.setattr(cli, "p1d3b_summary_to_markdown", lambda value: "# sentinel\n")
    cli.main(["p1d3b-report"])
    assert capsys.readouterr().out == "# sentinel\n"


def test_p1d3b_cli_dual_output_creates_parents(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(cli, "build_p1d3b_summary", _summary)
    monkeypatch.setattr(cli, "p1d3b_summary_to_json", lambda value: "{}\n")
    monkeypatch.setattr(cli, "p1d3b_summary_to_markdown", lambda value: "# sentinel\n")
    json_path = tmp_path / "nested" / "report.json"
    markdown_path = tmp_path / "other" / "report.md"
    cli.main([
        "p1d3b-report", "--format", "json", "--json-output", str(json_path),
        "--markdown-output", str(markdown_path),
    ])
    assert json_path.read_text(encoding="utf-8") == "{}\n"
    assert markdown_path.read_text(encoding="utf-8") == "# sentinel\n"
    assert capsys.readouterr().out == ""


def test_p1d3b_cli_has_no_source_policy_or_profile_override():
    parser = cli.build_parser()
    args = parser.parse_args(["p1d3b-report"])
    assert vars(args) == {
        "command": "p1d3b-report", "format": "markdown", "json_output": None,
        "markdown_output": None, "func": cli.command_p1d3b_report,
    }
