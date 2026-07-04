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
- P1b observation modes: `metadata_synth` as the frozen Phase A/B baseline and `execution_grounded` as the execution-derived mode with Phase C real-diff evidence for `inspect_recent_diff`.
- P1b Phase B1 execution-grounded harness using checkout test results, exceptions, and traced checkout functions.
- P1b Phase B2 coverage-spectrum localization with function-level Ochiai suspicion and coverage counts.
- P1b Phase B3 comparison reporting via `p1b-evaluate --observation-mode both`.
- P1b Phase C1 real-diff artifact schema with clean baseline checkout source, per-variant unified patches, and manifest.
- P1b Phase C1 real-diff generator/validator for all 25 variants; generated checkout trees are temporary and not committed.
- P1b Phase C2 `execution_grounded` `inspect_recent_diff` observations backed by Phase C real-diff artifacts.
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
- Real git commit histories for each P1b variant.
- Randomized Hypothesis-style property generation for P1b.
- Bayesian redesign of `bug_presence_posterior`.

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
- P1b `metadata_synth` observations are synthesized from ground-truth variant metadata via discovery-action matching. They are retained as a frozen baseline for comparison, not as evidence of real fault-localization ability.
- P1b `execution_grounded` observations are derived from checkout test results, exceptions, traced checkout functions, function-level Ochiai coverage suspicion, and Phase C real-diff artifacts for `inspect_recent_diff`. They still run inside a small injected benchmark scaffold rather than real project histories.
- P1b `metadata_synth` keeps synthetic recent-diff observations as the frozen baseline; only `execution_grounded` reads real-diff artifacts.
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
python -m bug_cause_inference.cli p1b-evaluate --observation-mode execution_grounded --format markdown
python -m bug_cause_inference.cli p1b-evaluate --observation-mode both --json-output examples/p1b/reports/p1b_evaluation_summary.json --markdown-output examples/p1b/reports/p1b_evaluation_summary.md
python -m bug_cause_inference.p1b.real_diff --validate
```

## Latest Test Result

Passed on 2026-07-04 after the P1b Phase C3 docs/examples refresh:

```bash
.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
```

Result: 187 passed.

In the Codex sandbox, the same command reported Temp-directory permission errors for `tmp_path` tests:

```text
174 passed, 13 errors
PermissionError: C:\Users\gurig\AppData\Local\Temp\pytest-of-gurig
```

The standard command passed when rerun with normal permissions.

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

Latest P1b Phase C status:

- Phase B1 local commit: `6610738` (`feat: add P1b execution-grounded observation harness`).
- Phase B2 local commit: `2669530` (`feat: add P1b coverage spectrum localization`).
- Phase B3 local commit: `6359f07` (`feat: add P1b observation-mode comparison reports`).
- Phase C1 local commit: `cabc086` (`feat: add P1b real diff artifact generator`).
- Phase C2 local commit: `4469213` (`feat: wire P1b real diff observations`).
- Phase C3 refreshed README/status/devlog and regenerated P1b examples around the C2 outputs.
- B1/B2/B3/C1/C2/C3 remain local until the user approves push/PR.
- `p1b-list-variants` generated `examples/p1b/variants/p1b_variants.json` and `.md`.
- `p1b-report --policy recent_diff_first --observation-mode execution_grounded` generated `examples/p1b/reports/p1b_report_P1B-BUG-001.json` and `.md`.
- `p1b-evaluate --observation-mode both` generated `examples/p1b/reports/p1b_evaluation_summary.json` and `.md`.
- P1b/P1c exclusions remain: no patch generation, no large real repositories, no LLM agent battles, no adversarial bug generation, no formal minimax framing.
- P1b Phase C2 connects `execution_grounded` `inspect_recent_diff` to real-diff artifacts; no policy, threshold, or score tuning was introduced.

Latest P1b primary-policy comparison:

| metric | metadata_synth | execution_grounded | execution_minus_metadata_delta | metadata_optimism_gap |
|---|---:|---:|---:|---:|
| bug_discovery_rate_within_budget | 0.55 | 0.40 | -0.15 | 0.15 |
| false_positive_rate_on_clean_cases | 0.00 | 0.00 | 0.00 | 0.00 |
| location_top3_accuracy | 0.60 | 0.55 | -0.05 | 0.05 |
| cause_top1_accuracy | 0.80 | 0.55 | -0.25 | 0.25 |
| fix_intent_top1_accuracy | 0.75 | 0.40 | -0.35 | 0.35 |
| mean_investigation_cost | 2.80 | 4.64 | 1.84 | 1.84 |
| primary_vs_fixed_mean_cost_delta | 0.421488 | 0.159420 | -0.262068 | 0.262068 |

`execution_minus_metadata_delta` is `execution_grounded_value - metadata_synth_value`. Positive `metadata_optimism_gap` means `metadata_synth` made the primary policy look better than execution-grounded evidence. For lower-is-better metrics such as false-positive rate and mean cost, the gap is `execution_grounded_value - metadata_synth_value`; otherwise it is `metadata_synth_value - execution_grounded_value`.
