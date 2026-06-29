"""Command line interface for generating cases, reports, and evaluations."""

from __future__ import annotations

import argparse
from pathlib import Path

from bug_cause_inference.analysis import analysis_to_json, analysis_to_markdown, build_analysis_summary
from bug_cause_inference.evaluation import evaluate_policies, evaluation_to_json, evaluation_to_markdown
from bug_cause_inference.likelihoods import validate_likelihood_table
from bug_cause_inference.policies import POLICIES, PRIMARY_POLICY, run_investigation
from bug_cause_inference.reports import build_decision_report, report_to_json, report_to_markdown
from bug_cause_inference.synthetic_cases import DEFAULT_SEED, generate_synthetic_cases, load_cases, save_cases


def _load_or_generate(path: str | None, seed: int):
    if path:
        return load_cases(path)
    return generate_synthetic_cases(seed)


def command_generate_cases(args: argparse.Namespace) -> None:
    validate_likelihood_table()
    cases = generate_synthetic_cases(args.seed)
    save_cases(cases, args.output)
    print(f"Wrote {len(cases)} synthetic cases to {args.output}")


def command_report(args: argparse.Namespace) -> None:
    validate_likelihood_table()
    cases = _load_or_generate(args.cases, args.seed)
    case = next((item for item in cases if item.case_id == args.case_id), None)
    if case is None:
        raise SystemExit(f"Case {args.case_id!r} not found.")
    result = run_investigation(case, policy=args.policy, rng_seed=args.rng_seed) if args.simulate_to_stop else None
    report = build_decision_report(case, result=result, policy=args.policy)
    if args.json_output:
        args.json_output.write_text(report_to_json(report), encoding="utf-8")
    if args.markdown_output:
        args.markdown_output.write_text(report_to_markdown(report), encoding="utf-8")
    if args.json_output or args.markdown_output:
        return
    if args.format == "json":
        print(report_to_json(report), end="")
    else:
        print(report_to_markdown(report), end="")


def command_evaluate(args: argparse.Namespace) -> None:
    validate_likelihood_table()
    cases = _load_or_generate(args.cases, args.seed)
    policies = tuple(args.policies) if args.policies else POLICIES
    summary = evaluate_policies(cases, policies=policies, random_repeats=args.random_repeats)
    if args.json_output:
        args.json_output.write_text(evaluation_to_json(summary), encoding="utf-8")
    if args.markdown_output:
        args.markdown_output.write_text(evaluation_to_markdown(summary), encoding="utf-8")
    if args.json_output or args.markdown_output:
        return
    if args.format == "json":
        print(evaluation_to_json(summary), end="")
    else:
        print(evaluation_to_markdown(summary), end="")


def command_analyze(args: argparse.Namespace) -> None:
    validate_likelihood_table()
    cases = _load_or_generate(args.cases, args.seed)
    policies = tuple(args.policies) if args.policies else None
    summary = build_analysis_summary(cases, policies=policies) if policies else build_analysis_summary(cases)
    if args.json_output:
        args.json_output.write_text(analysis_to_json(summary), encoding="utf-8")
    if args.markdown_output:
        args.markdown_output.write_text(analysis_to_markdown(summary), encoding="utf-8")
    if args.json_output or args.markdown_output:
        return
    if args.format == "json":
        print(analysis_to_json(summary), end="")
    else:
        print(analysis_to_markdown(summary), end="")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bug-cause-inference",
        description="Bayesian active bug investigation prototype for synthetic cases.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate-cases", help="Generate the fixed synthetic dataset.")
    generate.add_argument("--seed", type=int, default=DEFAULT_SEED)
    generate.add_argument("--output", type=Path, default=Path("examples/cases/synthetic_cases.json"))
    generate.set_defaults(func=command_generate_cases)

    report = subparsers.add_parser("report", help="Generate one DecisionReport.")
    report.add_argument("--cases", default=None, help="Path to synthetic_cases.json. If omitted, cases are generated.")
    report.add_argument("--case-id", default="BUG-0001")
    report.add_argument("--policy", choices=POLICIES, default=PRIMARY_POLICY)
    report.add_argument("--seed", type=int, default=DEFAULT_SEED)
    report.add_argument("--rng-seed", type=int, default=0)
    report.add_argument("--format", choices=("json", "markdown"), default="markdown")
    report.add_argument("--json-output", type=Path, default=None)
    report.add_argument("--markdown-output", type=Path, default=None)
    report.add_argument(
        "--simulate-to-stop",
        action="store_true",
        help="Run the selected policy until a stop condition before building the report.",
    )
    report.set_defaults(func=command_report)

    evaluate = subparsers.add_parser("evaluate", help="Compare policies on the synthetic dataset.")
    evaluate.add_argument("--cases", default=None, help="Path to synthetic_cases.json. If omitted, cases are generated.")
    evaluate.add_argument("--seed", type=int, default=DEFAULT_SEED)
    evaluate.add_argument("--policies", nargs="*", choices=POLICIES)
    evaluate.add_argument("--random-repeats", type=int, default=100)
    evaluate.add_argument("--format", choices=("json", "markdown"), default="markdown")
    evaluate.add_argument("--json-output", type=Path, default=None)
    evaluate.add_argument("--markdown-output", type=Path, default=None)
    evaluate.set_defaults(func=command_evaluate)

    analyze = subparsers.add_parser("analyze", help="Generate analysis-only diagnostics for P1a.")
    analyze.add_argument("--cases", default=None, help="Path to synthetic_cases.json. If omitted, cases are generated.")
    analyze.add_argument("--seed", type=int, default=DEFAULT_SEED)
    analyze.add_argument("--policies", nargs="*", choices=POLICIES)
    analyze.add_argument("--format", choices=("json", "markdown"), default="markdown")
    analyze.add_argument("--json-output", type=Path, default=None)
    analyze.add_argument("--markdown-output", type=Path, default=None)
    analyze.set_defaults(func=command_analyze)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
