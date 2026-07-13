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
- Minimal GitHub Actions CI workflow for pull requests and pushes to `main`, running pytest and the P1b real-diff validator on Python 3.10.
- Test operations guidance for verification tiers, CI expectations, and Codex sandbox Temp fallback: [`docs/test_operations.md`](test_operations.md).
- Public-release hygiene notes for tracked artifacts, ignored local outputs, CI expectations, known constraints, and public non-claims: [`docs/release_readiness.md`](release_readiness.md).
- P1c1 analysis-only worst-case report over existing P1b variants, policies, settings, and run results.
- P1c1 result interpretation note: [`docs/p1c1_result_interpretation.md`](p1c1_result_interpretation.md).
- P1c2 adversarial bucket selection specification: [`docs/p1c2_adversarial_bucket_selection_spec.md`](p1c2_adversarial_bucket_selection_spec.md).
- P1c3 adversarial bucket selection report integrated into `p1c-evaluate`, adding metric-specific selected buckets and separate clean false-positive stress as analysis-only output.
- P1c4 bounded observation-cost stress specification: [`docs/p1c4_bounded_observation_cost_stress_spec.md`](p1c4_bounded_observation_cost_stress_spec.md).
- P1c5 bounded observation-cost stress report integrated into `p1c-evaluate`, adding policy-visible cost-profile overlays, profile-vs-baseline gaps, and separate clean false-positive cost stress as analysis-only output.
- P1c6 cost-profile bucket-selection diagnostic specification: [`docs/p1c6_cost_profile_bucket_selection_spec.md`](p1c6_cost_profile_bucket_selection_spec.md).
- P1c7 profile-conditioned bucket-selection diagnostic integrated under `observation_cost_stress`, adding profile-specific selected-bucket shifts against the P1c3 baseline as analysis-only output.
- P1c8 bounded observation dropout/delay specification: [`docs/p1c8_bounded_observation_dropout_delay_spec.md`](p1c8_bounded_observation_dropout_delay_spec.md).
- P1c9 bounded observation dropout/delay stress report integrated into `p1c-evaluate` as the analysis-only `observation_dropout_delay_stress` object, using deterministic P1c-only copied-observation perturbation profiles.
- P1c consolidated result interpretation note: [`docs/p1c_result_interpretation.md`](p1c_result_interpretation.md).
- P1c variant label table for the 25 existing P1b variants, grouped into five buggy buckets and one clean false-positive bucket.
- P1c CLI command: `p1c-evaluate`.
- P1d0 reviewed specification for a fixed execution-grounded empirical finite loss game over the existing P1b/P1c scaffold.
- P1d1 analysis-only `headline_primary` report (`p1d1_finite_game_report.v1`) through `p1d1-report`: a six-policy by five-buggy-bucket discovery-loss matrix, restricted-pure security analysis, separate clean stress and secondary matrices, and an explicitly uncomputed mixed solution.
- P1d2 analysis-only `preregistered_candidate_headline_primary` report (`p1d2_preregistered_policy_evaluation.v1`) through `p1d2-report`: the preregistered `state_sequence_guard` candidate appended to the six baseline policies on the same five buckets. The valid directional result is `not_supported`; software acceptance is independently `accepted`.
- P1d3a retrospective analysis-only `retrospective_profile_conditioned_headline_primary` report (`p1d3a_g1_cost_profile_family_report.v1`) through `p1d3a-report`: four separate cost-profile-conditioned 6 by 5 matrices, 30 primary cells per profile and 120 primary cells total.
- P1d3b retrospective analysis-only `retrospective_dropout_delay_profile_conditioned_headline_primary` report (`p1d3b_g1_dropout_delay_profile_family_report.v1`) through `p1d3b-report`: four separate dropout/delay-profile-conditioned 6 by 5 matrices, 30 primary cells per profile and 120 primary cells total.
- P1d3a cost profiles and P1d3b dropout/delay profiles remain separate families. Each profile is fixed externally for its matrix; neither report creates a combined interaction, profile adversary action, or cross-profile optimization result.
- P1b dataset metadata validation for location/action references, dataset counts, category balance, required fields, difficulty labels, and duplicate variant IDs.
- Dataset diagnostics for initial top-1/top-2 accuracy.
- Separate evaluation summary for cases where the initial top-1 hypothesis is wrong.
- Wrong-stop diagnostic for the primary policy.
- CLI output saving with either JSON or Markdown output paths independently, creating parent directories when needed.
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
- Dedicated P1c adversarial-selection CLI command; P1c3 is integrated into the existing `p1c-evaluate` output.
- Dedicated P1c observation-cost stress CLI command; P1c5 is integrated into the existing `p1c-evaluate` output.
- Dedicated P1c profile-conditioned bucket-selection CLI command; P1c7 is integrated into the existing `p1c-evaluate` output.
- Dedicated P1c observation dropout/delay CLI command; P1c9 is integrated into the existing `p1c-evaluate` output.
- Combined cost plus dropout/delay evaluation or report.
- A joint profile-by-bucket game or cross-profile maximum, ranking, winner, or optimization result.
- P1d mixed-solution solver, general Nash-equilibrium result, regret analysis, or weighted discovery-cost loss.
- Additional P1d policy candidates, policy tuning, new variants, relabeling, or dataset expansion beyond the accepted fixed-scaffold studies.

## Deferred To Future Work

- `oracle_policy` or `dynamic_programming_upper_bound` as an upper-bound comparison.
- Learned or calibrated likelihood tables.
- Noisy, missing, or probabilistic observations.
- Case-specific investigation costs.
- Larger real-code fault localization beyond the small P1b injected-bug scaffold.
- Adversarial or worst-case bug models for P1c.
- A separately reviewed design for any future combined cost plus dropout/delay interaction.
- Any benchmark expansion, new policy/variant study, uncertainty analysis, or cross-profile optimization requires a separate specification and review.

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
- Codex sandbox pytest runs can hit Windows Temp-directory permission errors for `tmp_path` tests. Treat that as a local execution constraint when the same command passes with normal permissions; see [`docs/test_operations.md`](test_operations.md).
- P1c1 is analysis-only. It does not add variants, alter P1b execution logic, tune policies, or provide a formal game-theoretic guarantee.
- P1c2 is specification-only. It defines metric-specific bucket selection but does not implement a report, change P1b/P1c1 behavior, or introduce a weighted payoff, regret, minimax, or equilibrium model.
- P1c3 implements the P1c2 bucket-selection report as an analysis-only addition to P1c1 output. It selects buckets per policy and metric, keeps clean false-positive stress separate, and does not introduce a weighted payoff, regret, minimax, equilibrium, or formal game-theoretic guarantee.
- P1c4 is specification-only. It defines bounded action-cost overlays for future P1c-only observation-cost stress reporting, keeps P1b default costs unchanged, keeps P1c3 bucket selection separate, and does not introduce a weighted payoff, regret, minimax, equilibrium, or formal payoff model.
- P1c5 implements the P1c4 bounded observation-cost stress report as an analysis-only addition to P1c1 output. It uses a P1c-only policy-visible cost overlay, keeps `P1B_ACTION_SPECS` and default P1b behavior unchanged, keeps `observation_cost_stress` separate from `adversarial_bucket_selection`, keeps clean false-positive stress separate from buggy metrics, and does not introduce a weighted payoff, regret, minimax, equilibrium, or formal payoff model.
- P1c6 is specification-only. It defines a future profile-conditioned bucket-selection diagnostic derived from existing P1c5 profile bucket metrics, keeps the P1c3 baseline selection and P1c5 cost-stress objects separate, recommends nesting the diagnostic under `observation_cost_stress`, and does not introduce a weighted payoff, regret, minimax, equilibrium, or formal payoff model.
- P1c7 implements the P1c6 profile-conditioned bucket-selection diagnostic as an analysis-only nested addition under `observation_cost_stress`. It keeps the P1c3 baseline selected-bucket report unchanged, derives profile-selected buckets from existing P1c5 profile bucket metrics, keeps clean false-positive stress separate from buggy metrics, and does not introduce a weighted payoff, regret, minimax, equilibrium, or formal payoff model.
- P1c8 is specification-only. It defines deterministic, reproducible, bounded future observation dropout/delay profiles as P1c-only copied-observation perturbations, keeps P1b default observations, execution traces, real-diff artifacts, P1c3 bucket selection, P1c5 cost stress, and P1c7 nested diagnostics unchanged, and does not introduce a weighted payoff, regret, minimax, equilibrium, or formal payoff model.
- P1c9 implements the P1c8 bounded observation dropout/delay report candidate as an analysis-only `observation_dropout_delay_stress` addition to `p1c-evaluate`. It applies deterministic P1c-only copied-observation dropout/delay profiles, retains source observations, keeps clean false-positive stress separate from buggy metrics, leaves P1b defaults unchanged, and does not introduce a weighted payoff, regret, minimax, equilibrium, or formal payoff model.
- P1d1 and P1d2 are analysis-only evaluations on the fixed execution-grounded P1b scaffold. P1d2 is in-sample and exploratory; `not_supported` is the research result, not a software rejection.
- P1d3a and P1d3b retrospectively re-express already-observed P1c outcomes as separate profile-conditioned finite empirical matrix families. Profile-specific changes or their absence are not causal evidence and do not establish unseen-variant, unseen-profile, arbitrary-program, or real-world generalization.
- P1d restricted-pure results are qualified to the fixed policies, buckets, variants, settings, and externally fixed profiles. No P1d mixed solution, general Nash equilibrium, regret guarantee, general minimax-optimal debugger, joint profile-by-bucket robustness, or combined cost-plus-dropout/delay robustness is implemented or claimed.
- The synthetic cases are useful for policy comparison, not for claiming real-world debugging accuracy.
- The current expected information gain calculation uses action-specific candidate evidence sets derived from the fixed likelihood table.

## Verification Commands

See [`docs/test_operations.md`](test_operations.md) for the verification tiers, CI expectations, and the sandbox Temp fallback rule.

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
python -m bug_cause_inference.cli p1c-evaluate --format markdown
python -m bug_cause_inference.cli p1c-evaluate --observation-mode execution_grounded --json-output examples/p1c/reports/p1c_worst_case_summary.json --markdown-output examples/p1c/reports/p1c_worst_case_summary.md
python -m bug_cause_inference.cli p1c-evaluate --observation-mode both --policies expected_utility_per_cost --format json
python -m pytest tests/test_p1d1_evaluation.py tests/test_p1d1_cli.py -q
python -m pytest tests/test_p1d2_evaluation.py tests/test_p1d2_cli.py -q
python -m pytest tests/test_p1d3a_evaluation.py tests/test_p1d3a_cli.py -q
python -m pytest tests/test_p1d3b_evaluation.py tests/test_p1d3b_cli.py -q
python -m bug_cause_inference.cli p1d1-report --format markdown
python -m bug_cause_inference.cli p1d2-report --format json
python -m bug_cause_inference.cli p1d3a-report --format markdown
python -m bug_cause_inference.cli p1d3b-report --format json
python -m bug_cause_inference.p1b.real_diff --validate
```

## Latest Test Result

P1d closeout verification completed on 2026-07-13 at 22:15 JST. The standard Windows Temp runs hit the documented local permission constraint, and the unchanged suites passed with unique workspace-local base directories:

```bash
.\.venv\Scripts\python.exe -m pytest tests/test_p1d1_evaluation.py tests/test_p1d2_evaluation.py tests/test_p1d3a_evaluation.py tests/test_p1d3a_cli.py tests/test_p1d3b_evaluation.py tests/test_p1d3b_cli.py -q --basetemp tmp/pytest/p1d-closeout-targeted-20260713-02
.\.venv\Scripts\python.exe -m pytest -q --basetemp tmp/pytest/p1d-closeout-full-20260713-01
```

Results: `1080 passed` targeted and `1318 passed` full suite. The standard-Temp attempts produced `1078 passed, 2 errors` and `1300 passed, 18 errors`, respectively; every error was the known `PermissionError` while accessing `C:\Users\gurig\AppData\Local\Temp\pytest-of-gurig`.

The documentation-path Ruff command exited successfully but reported `No Python files found under the given path(s)`, so it is not recorded as a Python changed-file lint pass. Repository-wide Ruff reported only the three pre-existing `F401` findings in `p1b/policies.py`, `p1b/reports.py`, and `p1d/p1d2_evaluation.py`; no file was changed to suppress them.

Older P1a/P1b/P1c checkpoints below remain historical records.

Full pytest last passed on 2026-07-07 after adding the test-operations guidance, with normal permissions:

```bash
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
```

Result: 221 passed.

CLI/file-output and P1b real-diff targeted tests passed on 2026-07-07 with normal permissions:

```bash
.\.venv\Scripts\python.exe -B -m pytest tests\test_cli.py tests\test_p1b_cli.py tests\test_p1c_cli.py tests\test_p1b_real_diff.py -q -p no:cacheprovider
```

Result: 18 passed.

P1c targeted tests passed on 2026-07-07 after the P1c result interpretation and public-boundary status review, with normal permissions:

```bash
.\.venv\Scripts\python.exe -B -m pytest tests\test_p1c_labels.py tests\test_p1c_evaluation.py tests\test_p1c_cli.py -q -p no:cacheprovider
```

Result: 34 passed.

In the Codex sandbox, `tmp_path` commands can report Temp-directory permission errors such as:

```text
PermissionError: C:\Users\gurig\AppData\Local\Temp\pytest-of-gurig
```

- During the test-operations review, the targeted CLI/file-output command hit this sandbox error (`4 passed, 14 errors`) and passed when rerun with normal permissions (`18 passed`).
- `python -m bug_cause_inference.p1b.real_diff --validate` passed for all 25 variants.
- P1c9 CLI Markdown, JSON, and `both` mode JSON checks passed.

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

- Phase B/C capabilities are implemented in the current repository state. The historical local commit IDs below are retained as checkpoint notes from the pre-PR workflow.

- Phase B1 local commit: `6610738` (`feat: add P1b execution-grounded observation harness`).
- Phase B2 local commit: `2669530` (`feat: add P1b coverage spectrum localization`).
- Phase B3 local commit: `6359f07` (`feat: add P1b observation-mode comparison reports`).
- Phase C1 local commit: `cabc086` (`feat: add P1b real diff artifact generator`).
- Phase C2 local commit: `4469213` (`feat: wire P1b real diff observations`).
- Phase C3 refreshed README/status/devlog and regenerated P1b examples around the C2 outputs.
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
