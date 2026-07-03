# Implementation Status

## Implemented

- Evaluation interpretation notes: [`docs/p1a_evaluation_notes.md`](p1a_evaluation_notes.md).
- Synthetic dataset generator for 50 cases using seed `20260627`.
- Five cause categories and eight fixed investigation actions.
- Fixed observation likelihood table and Naive Bayes posterior update.
- Policies: `random`, `fixed_checklist`, `posterior_greedy`, `cheapest_first`, `information_gain`, `information_gain_per_cost`, and `static_posterior`.
- JSON and Markdown `DecisionReport` generation.
- Policy comparison and evaluation metrics.
- Analysis-only diagnostics for wrong stops, initially-wrong cases, stop reasons, category failures, and threshold sweeps.
- Clarified analysis metrics for wrong-stop denominators and initially-wrong final correctness.
- P1b injected-bug benchmark scaffold for a small checkout/pricing program.
- P1b dataset metadata with 20 buggy variants and 5 clean variants.
- P1b executable checkout/pricing helper modules with variant-specific injected behavior.
- P1b investigation actions, function-level location ranking, cause posterior updates, and fix-intent category prediction.
- P1b policies: `random_action`, `fixed_checklist`, `test_first`, `coverage_first`, `recent_diff_first`, `cause_only_p1a_style`, and `expected_utility_per_cost`.
- P1b JSON and Markdown report/evaluation output.
- P1b CLI commands: `p1b-list-variants`, `p1b-report`, and `p1b-evaluate`.
- P1b dataset metadata validation for location/action references, dataset counts, category balance, required fields, difficulty labels, and duplicate variant IDs.
- Dataset diagnostics for initial top-1/top-2 accuracy.
- Separate evaluation summary for cases where the initial top-1 hypothesis is wrong.
- Wrong-stop diagnostic for the primary policy.
- CLI output saving with either JSON or Markdown output paths independently.
- Per-step trace logging for executed investigation actions.
- CLI commands for case generation, report generation, and evaluation.
- Pytest coverage for the core MVP requirements.

## Not Implemented

- Real-code bug discovery.
- Production source-code fault localization.
- Automated patch generation.
- LLM-based free-form debugging.
- AI agent review battles.
- Adversarial or worst-case bug generation.
- Regret-based or bandit policy learning.
- Web UI.
- Real project bug history ingestion.
- Model or dataset changes in the analysis-only patch.
- Real git commit/diff artifacts for each P1b variant.
- Randomized Hypothesis-style property generation for P1b.

## Deferred To Future Work

- `oracle_policy` or `dynamic_programming_upper_bound` as an upper-bound comparison.
- Learned or calibrated likelihood tables.
- Noisy, missing, or probabilistic observations.
- Case-specific investigation costs.
- Larger real-code fault localization beyond the small P1b injected-bug scaffold.
- Adversarial or worst-case bug models for P1c.

## Known Limitations

- P1a does not identify code locations; P1b only ranks function-level locations inside the small injected-bug scaffold.
- The model does not generate patches.
- Recommendations depend on a synthetic likelihood table.
- Expected information gain is a P1a heuristic score, not a fully coherent action-conditioned generative observation model.
- The current generated dataset is relatively informative before investigation: initial top-1 accuracy is 70%, and initial top-2 accuracy is 100%.
- The current primary policy has a non-trivial wrong-stop rate, so the evaluation surfaces it as a diagnostic.
- The analysis report visualizes failure modes but does not improve model behavior.
- Analysis report policy runs use one diagnostic run per policy and case; `random` uses `rng_seed=0` and is not the repeated-random average used by `evaluate`.
- Category-level wrong-stop diagnostics distinguish confidence-stop denominator rates from per-case rates.
- Threshold-sweep `wrong_stop_rate` keeps the existing evaluation denominator: wrong stops divided by confidence stops.
- P1b is a small injected-bug scaffold, not a production debugger.
- P1b location evaluation is function-level; `line_span_hint` is secondary.
- P1b uses synthetic recent-diff metadata and structured coverage-like observations.
- P1b observations are synthesized from ground-truth variant metadata via discovery-action matching; they are not derived from executing the checkout code, except for two exception probes (`P1B-BUG-007`, `P1B-BUG-012`). Location, cause, and fix-intent metrics therefore measure action-selection efficiency on this scaffold, not real fault-localization ability.
- P1b predicts fix-intent categories but does not generate patches.
- The synthetic cases are useful for policy comparison, not for claiming real-world debugging accuracy.
- The current expected information gain calculation uses action-specific candidate evidence sets derived from the fixed likelihood table.

## Verification Commands

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python -m pip install -e .
python -B -m pytest -q -p no:cacheprovider
python -m bug_cause_inference.cli generate-cases --output examples/cases/synthetic_cases.json
python -m bug_cause_inference.cli report --cases examples/cases/synthetic_cases.json --case-id BUG-0001 --json-output examples/reports/decision_report_BUG-0001.json --markdown-output examples/reports/decision_report_BUG-0001.md
python -m bug_cause_inference.cli evaluate --cases examples/cases/synthetic_cases.json --json-output examples/reports/evaluation_summary.json --markdown-output examples/reports/evaluation_summary.md
python -m bug_cause_inference.cli analyze --cases examples/cases/synthetic_cases.json --json-output examples/reports/analysis_summary.json --markdown-output examples/reports/analysis_summary.md
python -m bug_cause_inference.cli p1b-list-variants --output examples/p1b/variants/p1b_variants.json --markdown-output examples/p1b/variants/p1b_variants.md
python -m bug_cause_inference.cli p1b-report --variant-id P1B-BUG-001 --json-output examples/p1b/reports/p1b_report_P1B-BUG-001.json --markdown-output examples/p1b/reports/p1b_report_P1B-BUG-001.md
python -m bug_cause_inference.cli p1b-evaluate --json-output examples/p1b/reports/p1b_evaluation_summary.json --markdown-output examples/p1b/reports/p1b_evaluation_summary.md
```

## Latest Test Result

Passed on 2026-07-03 after the P1b Phase A quality pass:

```bash
.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
```

Result: 102 passed.

Latest generated evaluation summary:

- `information_gain_per_cost` mean `cost_to_true_cause_top1`: 1.12
- `fixed_checklist` mean `cost_to_true_cause_top1`: 1.56
- Fixed-checklist cost reduction: 28.2051%
- Not worse than `posterior_greedy` overall: true
- At least 3 of 5 categories not worse than `fixed_checklist`: true
- Meets charter success criteria: true
- Primary success rate within budget: 94%
- Dataset initial top-1 accuracy: 70%
- Dataset initial top-2 accuracy: 100%
- Primary wrong-stop rate: 13.0435%
- The first-MVP success check against `fixed_checklist` is currently met on the synthetic dataset.
- The `primary_success_rate_at_least_80_percent` check is a diagnostic default, not a charter success criterion.

See [`p1a_evaluation_notes.md`](p1a_evaluation_notes.md) for the current interpretation and limitations of these results.

Latest P1b initial implementation verification:

- Added P1b scaffold without changing P1a evaluation semantics.
- `.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider`: 31 passed.
- `p1b-list-variants` generated `examples/p1b/variants/p1b_variants.json` and `.md`.
- `p1b-report` generated `examples/p1b/reports/p1b_report_P1B-BUG-001.json` and `.md`.
- `p1b-evaluate` generated `examples/p1b/reports/p1b_evaluation_summary.json` and `.md`.
- P1b/P1c exclusions remain: no patch generation, no large real repositories, no LLM agent battles, no adversarial bug generation, no formal minimax framing.

Latest P1b Phase A evaluation snapshot:

- Primary policy: `expected_utility_per_cost`
- Primary bug discovery rate within budget: 0.55
- Primary clean false-positive rate: 0.0
- Primary location top-3 accuracy: 0.60
- Primary cause top-1 accuracy: 0.80
- Primary mean investigation cost: 2.80
- Primary buggy-only mean investigation cost: 3.00
- Primary vs fixed mean cost delta: 42.1488%
- Primary mean cost at least 10% below fixed checklist: true
- The equal-cost/better-localization alternative clause is assessed manually.
