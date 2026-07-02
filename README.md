# Bug Cause Inference Game

A Bayesian active bug investigation prototype that recommends the next investigation action under limited debugging budget.

P1a works on synthetic observed-bug cases. It updates posterior probabilities over cause categories, compares investigation policies, and emits a `DecisionReport` whose primary output is `recommended_next_action`.

P1b adds a small injected-bug checkout/pricing benchmark scaffold. It evaluates whether budget-aware policies can discover failures, rank function-level locations, infer coarse cause categories, and predict fix-intent categories on 20 buggy variants and 5 clean variants.

See [`docs/p1a_evaluation_notes.md`](docs/p1a_evaluation_notes.md) for the current evaluation interpretation.

## What This Project Is

- A small Python prototype for cost-aware bug-cause investigation.
- A reproducible synthetic dataset with 50 cases, 5 cause categories, and a fixed seed.
- A Bayesian update loop using a fixed observation likelihood table.
- A policy comparison harness for action-selection strategies.
- A report generator for JSON and Markdown `DecisionReport` outputs.
- A P1b small injected-bug benchmark scaffold for checkout/pricing variants.

## What This Project Is Not

- This is not a real-code fault localization engine.
- This is not an automated program repair tool.
- This is not an LLM debugging benchmark.
- This is not yet a full game-theoretic debugging tool.
- It does not discover bugs in source code.
- P1a does not identify code locations; P1b only ranks function-level locations inside a small injected benchmark scaffold.
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

Run the P1b injected-bug benchmark scaffold:

```bash
python -m bug_cause_inference.cli p1b-list-variants
python -m bug_cause_inference.cli p1b-report --variant-id P1B-BUG-001 --format markdown
python -m bug_cause_inference.cli p1b-evaluate --format markdown
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

P1a evaluator reports:

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

P1b evaluator reports:

- `bug_discovery_rate_within_budget`
- `cost_to_first_failure`
- `reproduction_success_rate`
- `false_positive_rate_on_clean_cases`
- `false_negative_rate_on_buggy_cases`
- `location_top1_accuracy`
- `location_top3_accuracy`
- `location_mrr`
- `cause_top1_accuracy`
- `cause_top2_accuracy`
- `cost_to_true_cause_top1`
- `wrong_cause_high_confidence_rate`
- `fix_intent_top1_accuracy`
- `fix_intent_top3_accuracy`
- `mean_investigation_cost`
- `mean_investigation_cost_buggy_only`
- `cause_brier_score`

P1b location metrics are function-level only. Line-span hints are explanatory and secondary.

## Analysis Reports

The `analyze` command adds diagnostic reports without changing the model, dataset, default thresholds, or policies. It is an analysis-only companion to the existing evaluation command.

It reports:

- wrong-stop cases and their final posterior state
- initially-wrong cases by policy
- stop-reason distributions
- category-level failure summaries
- a minimal threshold sweep for `information_gain_per_cost` and `fixed_checklist`

Analysis report policy runs use one diagnostic run per policy and case. The `random` policy uses `rng_seed=0` as a single fixed-seed diagnostic run, so its analysis rows are not the same as the repeated-random averages reported by `evaluate`.

In category summaries, `wrong_stop_rate_within_confidence_stops` is `wrong_stop_count / confidence_stop_count`, while `wrong_stop_rate_per_case` is `wrong_stop_count / num_cases`. In threshold-sweep rows, `wrong_stop_rate` follows the existing evaluation definition: wrong stops divided by confidence stops. In initially-wrong rows, `ever_true_cause_top1_within_budget` means the true cause became top-1 within budget at least once; it does not guarantee that the final top hypothesis is correct.

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

P1b implemented policies:

- `random_action`
- `fixed_checklist`
- `test_first`
- `coverage_first`
- `recent_diff_first`
- `cause_only_p1a_style`
- `expected_utility_per_cost`

The P1b main policy is `expected_utility_per_cost`.

## Limitations

- The dataset is synthetic and intentionally small.
- The likelihood table is fixed by hand and is not learned from real project data.
- Observation independence is assumed by the Naive Bayes update.
- Expected information gain is a simple P1a action-ranking heuristic: prediction uses action-specific candidate evidence, while posterior updates use the global synthetic likelihood table. It is not a fully coherent generative observation model.
- Investigation action outcomes are deterministic within each synthetic case.
- The prototype recommends the next investigation action; it does not prove a root cause in a real system.
- There is no web UI, LLM free-form debugging, adversarial bug generation, or regret-based policy learning in this MVP.
- Analysis reports expose current failure modes; they do not improve the model or make real-world accuracy claims.
- P1b is a small injected-bug scaffold, not a production fault-localization engine.
- P1b uses synthetic recent-diff metadata and structured coverage-like observations.
- P1b observations are synthesized from ground-truth variant metadata via discovery-action matching; they are not derived from executing the checkout code, except for two exception probes (`P1B-BUG-007`, `P1B-BUG-012`). Location, cause, and fix-intent metrics therefore measure action-selection efficiency on this scaffold, not real fault-localization ability.
- P1b `run_property_search` uses deterministic enumerated cases, not randomized Hypothesis-style generation.
- P1b predicts fix-intent categories but does not generate patches.

## Reproducibility Notes

- Synthetic cases use fixed seed `20260627`.
- The first MVP contains 50 cases: 5 cause categories times 10 cases.
- Each case has 2 initial observations and all 8 possible investigation outcomes.
- The current generated dataset has initial top-1 accuracy of 70% and initial top-2 accuracy of 100%, so evaluation reports both all-case and initially-wrong-case performance.
- Generated examples under `examples/` are reproducible from the CLI.
- P1b examples under `examples/p1b/` are generated by `p1b-list-variants`, `p1b-report`, and `p1b-evaluate`.

## License

MIT.
