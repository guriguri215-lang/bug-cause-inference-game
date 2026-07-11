import json
import argparse

from bug_cause_inference import cli
from bug_cause_inference.p1b.policies import P1B_POLICIES, P1B_PRIMARY_POLICY


def test_p1d2_report_cli_writes_both_outputs_from_one_mocked_summary(
    tmp_path,
    monkeypatch,
):
    summary = {"schema_version": "p1d2_test", "sentinel": 17}
    seen = []
    monkeypatch.setattr(cli, "build_p1d2_summary", lambda: summary)

    def to_json(value):
        seen.append(value)
        return json.dumps(value, indent=2) + "\n"

    def to_markdown(value):
        seen.append(value)
        return "# P1d2 Test\n\n17\n"

    monkeypatch.setattr(cli, "p1d2_summary_to_json", to_json)
    monkeypatch.setattr(cli, "p1d2_summary_to_markdown", to_markdown)
    json_path = tmp_path / "nested" / "p1d2" / "report.json"
    markdown_path = tmp_path / "nested" / "p1d2" / "report.md"

    cli.main(
        [
            "p1d2-report",
            "--format",
            "json",
            "--json-output",
            str(json_path),
            "--markdown-output",
            str(markdown_path),
        ]
    )

    assert json.loads(json_path.read_text(encoding="utf-8")) == summary
    assert markdown_path.read_text(encoding="utf-8") == "# P1d2 Test\n\n17\n"
    assert seen == [summary, summary]


def test_p1d2_report_cli_prints_selected_format(capsys, monkeypatch):
    summary = {"schema_version": "p1d2_test", "sentinel": 23}
    monkeypatch.setattr(cli, "build_p1d2_summary", lambda: summary)
    monkeypatch.setattr(
        cli,
        "p1d2_summary_to_json",
        lambda value: json.dumps(value) + "\n",
    )
    monkeypatch.setattr(
        cli,
        "p1d2_summary_to_markdown",
        lambda value: "# P1d2 Markdown\n",
    )

    cli.main(["p1d2-report", "--format", "json"])

    assert json.loads(capsys.readouterr().out) == summary


def test_existing_p1b_p1c_cli_choices_and_defaults_exclude_candidate():
    parser = cli.build_parser()
    subparsers = next(
        action
        for action in parser._actions
        if isinstance(action, argparse._SubParsersAction)
    )
    p1b_report = subparsers.choices["p1b-report"]
    policy_action = next(
        action for action in p1b_report._actions if action.dest == "policy"
    )
    assert tuple(policy_action.choices) == P1B_POLICIES
    assert policy_action.default == P1B_PRIMARY_POLICY

    for command in ("p1b-evaluate", "p1c-evaluate"):
        subparser = subparsers.choices[command]
        policies_action = next(
            action for action in subparser._actions if action.dest == "policies"
        )
        assert tuple(policies_action.choices) == P1B_POLICIES
        assert "state_sequence_guard" not in policies_action.choices
