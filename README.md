# Bug Cause Inference Game

A Bayesian active bug investigation prototype that recommends the next investigation action under limited debugging budget.

This first MVP works only on synthetic observed-bug cases. It updates posterior probabilities over cause categories, compares investigation policies, and emits a `DecisionReport` whose primary output is `recommended_next_action`.

See [`docs/p1a_evaluation_notes.md`](docs/p1a_evaluation_notes.md) for the current evaluation interpretation.

## What This Project Is

- A small Python prototype for cost-aware bug-cause investigation.
- A reproducible synthetic dataset with 50 cases, 5 cause categories, and a fixed seed.
- A Bayesian update loop using a fixed observation likelihood table.
- A policy comparison harness for action-selection strategies.
- A report generator for JSON and Markdown `DecisionReport` outputs.

## What This Project Is Not

- This is not a real-code fault localization engine.
- This is not an automated program repair tool.
- This is not an LLM debugging benchmark.
- This is not yet a full game-theoretic debugging tool.
- It does not discover bugs in source code.
- It does not identify code locations.
- It does not generate patches.
- It does not ingest real project bug histories.

## Installation

Windows setup example:

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python -m pip install -e .
python -m pytest
```

The project uses a `src/` layout. Install it in editable mode before running CLI examples with `python -m bug_cause_inference.cli`.

After the editable install, you can run:

```bash
python -m bug_cause_inference.cli --help
```

## Quick Start

Generate the reproducible synthetic dataset:

```bash
python -m bug_cause_inference.cli generate-cases --output examples/cases/synthetic_cases.json
```

Generate a Markdown `DecisionReport` for one case:

```bash
python -m bug_cause_inference.cli report --cases examples/cases/synthetic_cases.json --case-id BUG-0001 --format markdown
```

Compare policies:

```bash
python -m bug_cause_inference.cli evaluate --cases examples/cases/synthetic_cases.json --format markdown
```

Generate analysis-only diagnostics:

```bash
python -m bug_cause_inference.cli analyze --cases examples/cases/synthetic_cases.json --format markdown
```

## Example Command

```bash
python -m bug_cause_inference.cli report ^
  --cases examples/cases/synthetic_cases.json ^
  --case-id BUG-0001 ^
  --policy information_gain_per_cost ^
  --json-output examples/reports/decision_report_BUG-0001.json ^
  --markdown-output examples/reports/decision_report_BUG-0001.md
```

`--json-output` and `--markdown-output` can also be used independently.

## Example DecisionReport

```json
{
  "case_id": "BUG-0001",
  "current_step": 0,
  "stop_or_continue": "continue",
  "stop_reason": null,
  "recommended_next_action": "run_boundary_tests",
  "expected_cost": 2,
  "expected_information_gain_per_cost": 0.2042,
  "current_top_hypotheses": [
    {
      "rank": 1,
      "hypothesis": "boundary_condition",
      "posterior_probability": 0.737127
    }
  ],
  "known_limits": [
    "This report does not identify a code location.",
    "This report does not propose or generate a patch.",
    "The recommendation depends on the synthetic likelihood table."
  ]
}
```

Exact probabilities depend on the generated case and the investigation trace.

## Evaluation Metrics

The evaluator reports:

- `initial_top1_accuracy`
- `initial_top2_accuracy`
- performance over all synthetic cases
- performance on cases where the initial top-1 hypothesis is wrong
- `cost_to_true_cause_top1`
- `success_rate_within_budget`
- `success_rate_by_budget`
- `area_under_budget_curve`
- `top_k_accuracy_by_step`
- `brier_score`
- `expected_calibration_error`
- `explanation_omission_test`
- `explanation_trace_completeness`
- `wrong_stop_rate`

`wrong_stop_rate` means the model stopped on a high-confidence but incorrect cause hypothesis. It is not about patch correctness.

The evaluation also reports a wrong-stop diagnostic threshold for the primary policy. This is a caution signal, not a claim that the synthetic model is safe for real-world root-cause decisions.

## Analysis Reports

The `analyze` command adds diagnostic reports without changing the model, dataset, default thresholds, or policies. It is an analysis-only companion to the existing evaluation command.

It reports:

- wrong-stop cases and their final posterior state
- initially-wrong cases by policy
- stop-reason distributions
- category-level failure summaries
- a minimal threshold sweep for `information_gain_per_cost` and `fixed_checklist`

Example:

```bash
python -m bug_cause_inference.cli analyze ^
  --cases examples/cases/synthetic_cases.json ^
  --json-output examples/reports/analysis_summary.json ^
  --markdown-output examples/reports/analysis_summary.md
```

## Baselines

Implemented policies:

- `random`
- `fixed_checklist`
- `posterior_greedy`
- `cheapest_first`
- `information_gain`
- `information_gain_per_cost`
- `static_posterior`

The main policy is `information_gain_per_cost`.

## Limitations

- The dataset is synthetic and intentionally small.
- The likelihood table is fixed by hand and is not learned from real project data.
- Observation independence is assumed by the Naive Bayes update.
- Expected information gain is a simple P1a action-ranking heuristic: prediction uses action-specific candidate evidence, while posterior updates use the global synthetic likelihood table. It is not a fully coherent generative observation model.
- Investigation action outcomes are deterministic within each synthetic case.
- The prototype recommends the next investigation action; it does not prove a root cause in a real system.
- There is no web UI, LLM free-form debugging, adversarial bug generation, or regret-based policy learning in this MVP.
- Analysis reports expose current failure modes; they do not improve the model or make real-world accuracy claims.

## Reproducibility Notes

- Synthetic cases use fixed seed `20260627`.
- The first MVP contains 50 cases: 5 cause categories times 10 cases.
- Each case has 2 initial observations and all 8 possible investigation outcomes.
- The current generated dataset has initial top-1 accuracy of 70% and initial top-2 accuracy of 100%, so evaluation reports both all-case and initially-wrong-case performance.
- Generated examples under `examples/` are reproducible from the CLI.

## License

MIT.
