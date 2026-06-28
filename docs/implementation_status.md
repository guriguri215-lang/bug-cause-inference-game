# Implementation Status

## Implemented

- Evaluation interpretation notes: [`docs/p1a_evaluation_notes.md`](p1a_evaluation_notes.md).
- Synthetic dataset generator for 50 cases using seed `20260627`.
- Five cause categories and eight fixed investigation actions.
- Fixed observation likelihood table and Naive Bayes posterior update.
- Policies: `random`, `fixed_checklist`, `posterior_greedy`, `cheapest_first`, `information_gain`, `information_gain_per_cost`, and `static_posterior`.
- JSON and Markdown `DecisionReport` generation.
- Policy comparison and evaluation metrics.
- Dataset diagnostics for initial top-1/top-2 accuracy.
- Separate evaluation summary for cases where the initial top-1 hypothesis is wrong.
- Wrong-stop diagnostic for the primary policy.
- CLI output saving with either JSON or Markdown output paths independently.
- Per-step trace logging for executed investigation actions.
- CLI commands for case generation, report generation, and evaluation.
- Pytest coverage for the core MVP requirements.

## Not Implemented

- Real-code bug discovery.
- Source-code fault localization.
- Automated patch generation.
- LLM-based free-form debugging.
- AI agent review battles.
- Adversarial or worst-case bug generation.
- Regret-based or bandit policy learning.
- Web UI.
- Real project bug history ingestion.

## Deferred To Future Work

- `oracle_policy` or `dynamic_programming_upper_bound` as an upper-bound comparison.
- Learned or calibrated likelihood tables.
- Noisy, missing, or probabilistic observations.
- Case-specific investigation costs.
- Real-code fault localization and injected-bug programs for P1b.
- Adversarial or worst-case bug models for P1c.

## Known Limitations

- The model does not identify code locations.
- The model does not generate patches.
- Recommendations depend on a synthetic likelihood table.
- Expected information gain is a P1a heuristic score, not a fully coherent action-conditioned generative observation model.
- The current generated dataset is relatively informative before investigation: initial top-1 accuracy is 70%, and initial top-2 accuracy is 100%.
- The current primary policy has a non-trivial wrong-stop rate, so the evaluation surfaces it as a diagnostic.
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
```

## Latest Test Result

Passed on 2026-06-28 after follow-up fixes:

```bash
.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
```

Result: 11 passed.

Latest generated evaluation summary:

- `information_gain_per_cost` mean `cost_to_true_cause_top1`: 1.12
- `fixed_checklist` mean `cost_to_true_cause_top1`: 1.56
- Fixed-checklist cost reduction: 28.2051%
- Primary success rate within budget: 94%
- Dataset initial top-1 accuracy: 70%
- Dataset initial top-2 accuracy: 100%
- Primary wrong-stop rate: 13.0435%
- The first-MVP success check against `fixed_checklist` is currently met on the synthetic dataset.

See [`p1a_evaluation_notes.md`](p1a_evaluation_notes.md) for the current interpretation and limitations of these results.
