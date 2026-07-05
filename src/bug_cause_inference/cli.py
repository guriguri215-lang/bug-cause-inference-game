"""Command line interface for generating cases, reports, and evaluations."""

from __future__ import annotations

import argparse
from pathlib import Path

from bug_cause_inference.analysis import analysis_to_json, analysis_to_markdown, build_analysis_summary
from bug_cause_inference.evaluation import evaluate_policies, evaluation_to_json, evaluation_to_markdown
from bug_cause_inference.likelihoods import validate_likelihood_table
from bug_cause_inference.p1b.actions import P1B_OBSERVATION_MODES
from bug_cause_inference.p1b.dataset import get_variant, load_p1b_variants, save_variants
from bug_cause_inference.p1b.evaluation import (
    P1B_EVALUATION_OBSERVATION_MODES,
    evaluate_p1b,
    p1b_evaluation_to_json,
    p1b_evaluation_to_markdown,
)
from bug_cause_inference.p1b.policies import P1B_POLICIES, P1B_PRIMARY_POLICY
from bug_cause_inference.p1b.reports import (
    build_p1b_report,
    p1b_report_to_json,
    p1b_report_to_markdown,
    p1b_variants_to_json,
    p1b_variants_to_markdown,
)
from bug_cause_inference.p1c.evaluation import (
    P1C_DEFAULT_OBSERVATION_MODE,
    P1C_OBSERVATION_MODES,
    evaluate_p1c,
    p1c_evaluation_to_json,
    p1c_evaluation_to_markdown,
)
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


def _write_or_print(
    data_json: str,
    data_markdown: str,
    args: argparse.Namespace,
) -> None:
    if args.json_output:
        args.json_output.write_text(data_json, encoding="utf-8")
    if args.markdown_output:
        args.markdown_output.write_text(data_markdown, encoding="utf-8")
    if args.json_output or args.markdown_output:
        return
    if args.format == "json":
        print(data_json, end="")
    else:
        print(data_markdown, end="")


def command_p1b_list_variants(args: argparse.Namespace) -> None:
    variants = load_p1b_variants()
    if args.output:
        save_variants(args.output, variants)
    _write_or_print(p1b_variants_to_json(variants), p1b_variants_to_markdown(variants), args)


def command_p1b_report(args: argparse.Namespace) -> None:
    variant = get_variant(args.variant_id)
    report = build_p1b_report(variant, policy=args.policy, observation_mode=args.observation_mode)
    _write_or_print(p1b_report_to_json(report), p1b_report_to_markdown(report), args)


def command_p1b_evaluate(args: argparse.Namespace) -> None:
    policies = tuple(args.policies) if args.policies else P1B_POLICIES
    summary = evaluate_p1b(policies=policies, observation_mode=args.observation_mode)
    _write_or_print(p1b_evaluation_to_json(summary), p1b_evaluation_to_markdown(summary), args)


def command_p1c_evaluate(args: argparse.Namespace) -> None:
    policies = tuple(args.policies) if args.policies else P1B_POLICIES
    summary = evaluate_p1c(policies=policies, observation_mode=args.observation_mode)
    _write_or_print(p1c_evaluation_to_json(summary), p1c_evaluation_to_markdown(summary), args)


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

    p1b_list = subparsers.add_parser("p1b-list-variants", help="List P1b injected-bug benchmark variants.")
    p1b_list.add_argument("--format", choices=("json", "markdown"), default="markdown")
    p1b_list.add_argument("--output", type=Path, default=None, help="Optional JSON dataset output path.")
    p1b_list.add_argument("--json-output", type=Path, default=None)
    p1b_list.add_argument("--markdown-output", type=Path, default=None)
    p1b_list.set_defaults(func=command_p1b_list_variants)

    p1b_report = subparsers.add_parser("p1b-report", help="Generate one P1b variant report.")
    p1b_report.add_argument("--variant-id", default="P1B-BUG-001")
    p1b_report.add_argument("--policy", choices=P1B_POLICIES, default=P1B_PRIMARY_POLICY)
    p1b_report.add_argument("--observation-mode", choices=P1B_OBSERVATION_MODES, default="metadata_synth")
    p1b_report.add_argument("--format", choices=("json", "markdown"), default="markdown")
    p1b_report.add_argument("--json-output", type=Path, default=None)
    p1b_report.add_argument("--markdown-output", type=Path, default=None)
    p1b_report.set_defaults(func=command_p1b_report)

    p1b_evaluate = subparsers.add_parser("p1b-evaluate", help="Evaluate P1b policies.")
    p1b_evaluate.add_argument("--policies", nargs="*", choices=P1B_POLICIES)
    p1b_evaluate.add_argument("--observation-mode", choices=P1B_EVALUATION_OBSERVATION_MODES, default="metadata_synth")
    p1b_evaluate.add_argument("--format", choices=("json", "markdown"), default="markdown")
    p1b_evaluate.add_argument("--json-output", type=Path, default=None)
    p1b_evaluate.add_argument("--markdown-output", type=Path, default=None)
    p1b_evaluate.set_defaults(func=command_p1b_evaluate)

    p1c_evaluate = subparsers.add_parser("p1c-evaluate", help="Evaluate P1c worst-case bucket robustness.")
    p1c_evaluate.add_argument("--policies", nargs="*", choices=P1B_POLICIES)
    p1c_evaluate.add_argument("--observation-mode", choices=P1C_OBSERVATION_MODES, default=P1C_DEFAULT_OBSERVATION_MODE)
    p1c_evaluate.add_argument("--format", choices=("json", "markdown"), default="markdown")
    p1c_evaluate.add_argument("--json-output", type=Path, default=None)
    p1c_evaluate.add_argument("--markdown-output", type=Path, default=None)
    p1c_evaluate.set_defaults(func=command_p1c_evaluate)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
