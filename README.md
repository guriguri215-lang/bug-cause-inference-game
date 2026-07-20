# Bug Cause Inference Game

A Bayesian active bug investigation prototype that recommends the next investigation action under limited debugging budget.

P1a works on synthetic observed-bug cases. It updates posterior probabilities over cause categories, compares investigation policies, and emits a `DecisionReport` whose primary output is `recommended_next_action`.

P1b adds a small injected-bug checkout/pricing benchmark scaffold. It evaluates whether budget-aware policies can discover failures, rank function-level locations, infer coarse cause categories, and predict fix-intent categories on 20 buggy variants and 5 clean variants.

P1b currently has two observation modes. `metadata_synth` is the frozen Phase A/B baseline that synthesizes evidence from variant metadata, while `execution_grounded` builds observations from checkout test results, exceptions, traced checkout functions, coverage-spectrum suspicion, and Phase C real-diff artifacts for `inspect_recent_diff`. `p1b-evaluate --observation-mode both` runs both modes on the same dataset and policies so the report can show how much the metadata-synth baseline was optimistic.

P2a is a frozen, versioned same-domain evidence expansion of the small checkout/pricing benchmark. It adds 10 buggy and 5 clean hand-authored variants, keeps accepted legacy references separate from P2a replay and expansion results, and reports only descriptive evidence for the fixed cohort and six deterministic policies. See [`docs/p2a_result_interpretation.md`](docs/p2a_result_interpretation.md) and the versioned [JSON](src/bug_cause_inference/p2a/artifacts/evaluation/p2a_benchmark_evidence_expansion_v1.json) and [Markdown](src/bug_cause_inference/p2a/artifacts/evaluation/p2a_benchmark_evidence_expansion_v1.md) evidence artifacts.

P2b adds a fixed-catalog solvability ceiling diagnostic over the accepted P2a inputs. Across 240 case evaluations, all 10 buggy variants have at least one direct catalog detector within the fixed budget; their minimum detecting costs are `2,2,2,2,3,3,4,4,2,2`. The saved six-policy ceiling gaps are `4/5,4/5,4/5,4/5,1,1` in formal policy order. This is an analysis-only, ground-truth-informed, non-deployable result for the fixed catalog and cohort. It does not show that the six policies solve every variant, establish production readiness, or provide a general solvability bound. See [`docs/p2b_result_interpretation.md`](docs/p2b_result_interpretation.md).

P2c is the merged frozen-policy trajectory audit over the same accepted inputs. Across the fixed `10 × 6 = 60` pairs, direct detectors were selected and discoveries observed in `8/60`; detectors were not selected in `52/60`, and all `52/52` unselected terminal rows still had a detector within the recorded remaining budget. Stops were `58` no-bug probability thresholds and `2` budget limits. Selection, recorded budget feasibility, and termination are overlapping non-causal axes. The result is analysis-only, fixed-input, ground-truth-informed, and non-deployable. Terminal feasibility does not mean a policy could select an action after stopping, identify a causal budget failure, or reveal a production policy defect. See [`docs/p2c_result_interpretation.md`](docs/p2c_result_interpretation.md).

P2d is the merged one-step stop-relaxation audit over those same 60 accepted pairs. It retains `52` preregistered intervention candidates and `8` not-applicable rows. Suppressing only the terminal no-bug-probability predicate once produced `0/52` residual alternate stops and `52/52` one-action decisions: `11/52` selected a direct detector, `11/52` observations detected the bug, and post-action outcomes were `41/52` no-bug threshold stops plus `11/52` one-step horizons. This is analysis-only, fixed-input, ground-truth-informed, model-internal, one-step, non-causal, and non-deployable evidence. Exactly-one suppression does not establish stop causality, policy improvement or ranking, multi-step reachability, or a production recommendation. See [`docs/p2d_result_interpretation.md`](docs/p2d_result_interpretation.md).

P2e is the merged bounded continuation audit over the same 60 accepted pairs. It retains `41/60` P2d post-action threshold rows as continuation candidates, `11/60` accepted P2d direct-detector endpoints, and `8/60` not-applicable rows. Suppressing only `no_bug_probability_threshold` at every later pre-action decision produced the candidate terminal partition `21/41` detector, `0/41` bug confidence, `8/41` budget, `4/41` maximum step, `0/41` low utility, and `8/41` no available actions. Direct-detector selection and observation detection are separate axes and both equal `21/41` here. This evidence is analysis-only, fixed-input, ground-truth-informed, model-internal, bounded-sequence, non-causal, and non-deployable. Repeated target-only suppression does not establish stop causality, a threshold defect, policy improvement or ranking, sequence optimality, or a production recommendation. See [`docs/p2e_result_interpretation.md`](docs/p2e_result_interpretation.md).

P2f is the merged paired clean-boundary audit over one exact unpatched canonical P1b baseline. The six accepted deterministic policies each have a normal control and an arm that suppresses only `no_bug_probability_threshold` at every pre-action firing, for 12 trajectories and 6 pairs after a `29/29` baseline gate. Control false positives are `0/6`; intervention false positives are `0/6`, with terminals `4/6` budget, `1/6` maximum step, and `1/6` no available actions. Suppression counts are `[4, 4, 4, 4, 4, 5]`, and all four recent-diff executions truthfully preserve empty path/file/function/excerpt fields. This is analysis-only, fixed-input, model-internal, paired, non-causal, and non-deployable evidence—not a clean safety rate, threshold or policy improvement, combined P2e/P2f payoff, or production result. See [`docs/p2f_result_interpretation.md`](docs/p2f_result_interpretation.md).

P2g is the merged paired benign-diff clean-boundary audit over the exact five accepted P2a clean patches. It crosses those five hand-authored same-domain inputs with the six accepted formal policies and two arms, for 60 trajectories and 30 pairs after a `14/14` input-specific clean-oracle gate. Normal-control replay, pair starts, and pre-target prefixes agree `30/30`; control and target-suppressed-continuation false positives are separately `0/30` and `0/30`. Intervention terminals are `20/30` budget, `5/30` maximum step, and `5/30` no available actions; action counts are 20 at five and 10 at six, costs are 5 at 10, 5 at 11, and 20 at 12, suppression counts are 25 at four and 5 at five, and all `20/20` recent-diff observations preserve the accepted non-empty repository-relative patch evidence. This fixed crossed non-iid support is analysis-only, model-internal, paired, non-causal, and non-deployable—not a population clean-safety rate, threshold or policy defect/improvement, ranking, combined P2e/P2f/P2g payoff, generalization result, or production recommendation. See [`docs/p2g_result_interpretation.md`](docs/p2g_result_interpretation.md).

P2h is the merged normal-execution replication in one pure deterministic toy task-scheduler domain, distinct from checkout/pricing and frozen before any formal-policy outcome. It crosses 10 buggy and 5 benign clean hand-authored inputs with the six accepted formal policies for 90 ordered rows after a 25-oracle outcome-free gate. The fixed-support results are bug discovery `12/60`, function localization top-1 `25/60` and top-3 `35/60`, cause and fix-intent top-1 `16/60` each, and clean false positives `0/30`; terminals are 85 no-bug thresholds, 4 bug-confidence thresholds, and 1 budget limit. This single-domain crossed non-iid evidence is analysis-only, descriptive, non-causal, and non-deployable—not independent program replication, a policy ranking, a population estimate, checkout-to-scheduler transfer, combined P2a–P2h payoff, inference, generalization, release readiness, or production evidence. See [`docs/p2h_result_interpretation.md`](docs/p2h_result_interpretation.md).

See [`docs/p1a_evaluation_notes.md`](docs/p1a_evaluation_notes.md) for the current evaluation interpretation.

## What This Project Is

- A small Python prototype for cost-aware bug-cause investigation.
- A reproducible synthetic dataset with 50 cases, 5 cause categories, and a fixed seed.
- A Bayesian update loop using a fixed observation likelihood table.
- A policy comparison harness for action-selection strategies.
- A report generator for JSON and Markdown `DecisionReport` outputs.
- A P1b small injected-bug benchmark scaffold for checkout/pricing variants.
- Analysis-only P1c robustness reports and P1d fixed empirical finite-game reports over that scaffold.
- A frozen P2a same-domain benchmark expansion with versioned candidate, freeze, evaluation, and report evidence.
- A P2b fixed-catalog diagnostic with versioned JSON/Markdown evidence and explicit artifact/result acceptance boundaries.
- A P2c frozen-policy trajectory audit with versioned evidence and separate software, artifact, result, and documentation acceptance decisions.
- A P2d exactly-one-threshold-suppression audit with a zero-or-one-action horizon and separate software, artifact, result, and documentation acceptance decisions.
- A P2e every-later-decision target-only continuation audit with finite budget, step, and non-repeating-action bounds and separate software, artifact, result, and documentation acceptance decisions.
- A P2f canonical unpatched-clean paired audit with truthful empty-diff evidence and separate software, artifact, result, and documentation acceptance decisions.
- A P2g accepted-benign-diff clean paired audit with truthful non-empty patch evidence and separate software, artifact, result, and documentation acceptance decisions.
- A P2h fixed task-scheduler second-domain replication with 90 normal-execution rows and separate software, artifact, result, and documentation acceptance decisions.

## What This Project Is Not

- This is not a production fault-localization engine.
- This is not an automated program repair tool.
- This is not an LLM debugging benchmark.
- This is not a fuzzing or property-based testing framework.
- This is not a general or production game-theoretic debugging system.
- P1a does not discover bugs or identify source-code locations.
- P1b uses a small injected checkout/pricing benchmark scaffold; it does not claim real-world debugging accuracy.
- P1b only ranks function-level locations inside that scaffold.
- P1b real-diff artifacts are not real repository histories.
- P1b predicts fix-intent categories but does not generate patches.
- P2a does not establish unseen-variant or second-domain generalization, statistical significance, production performance, general minimax or Nash results, regret guarantees, or policy superiority.
- P2b catalog reachability is not a seventh policy, deployable strategy, general upper bound, or production-readiness claim.
- P2c does not rank policies, assign mutually exclusive causal miss reasons, add or tune a policy, compute a counterfactual or DP ceiling, or establish generalization or production readiness.
- P2d does not establish threshold causality, a policy defect or improvement, a second action, multi-step or DP reachability, deployability, generalization, or production readiness.
- P2e does not establish threshold causality or defect, policy ranking or improvement, sequence optimality, an unbounded or DP ceiling, deployability, generalization, or production readiness.
- P2f does not establish a clean safety rate, causal effect, threshold or policy defect, policy improvement or ranking, a P2e/P2f combined payoff, deployability, generalization, or production readiness.
- P2g does not establish a population clean-safety rate, causal effect, threshold or policy defect, policy improvement or ranking, a P2e/P2f/P2g combined payoff, deployability, generalization, inference, or production readiness.
- P2h does not establish independent program replication, a domain-population estimate, policy superiority or ranking, causal transfer, a combined P2a–P2h payoff, arbitrary-program generalization, inference, release readiness, or production readiness.

## Related Work

This project is closest to probabilistic debugging, Bayesian fault diagnosis, and active diagnosis. Those areas study how to rank likely diagnoses from observations and how to choose the next test or observation under limited cost. P1a adopts that framing at a deliberately small scale: it ranks coarse bug-cause categories rather than source-code locations, and it recommends the next investigation action rather than generating a patch.

The project also touches fault localization and spectrum-based fault localization, but P1a is not a source-location engine. P1b adds a small injected-bug checkout/pricing benchmark with function-level location metrics, execution-derived observations, and real-diff artifacts, while keeping the scope far below production fault-localization systems or large bug benchmarks such as Defects4J.

Mutation testing, fuzzing, property-based testing, automated program repair, and LLM software-engineering agents are adjacent rather than direct targets. They can generate failures, evaluate test suites, or repair code; this project currently focuses on cost-aware investigation and scoped benchmark scaffolding after a failure is observed.

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
python -m bug_cause_inference.cli p1b-report --variant-id P1B-BUG-001 --policy recent_diff_first --observation-mode execution_grounded --format markdown
python -m bug_cause_inference.cli p1b-evaluate --format markdown
python -m bug_cause_inference.cli p1b-evaluate --observation-mode execution_grounded --format markdown
python -m bug_cause_inference.cli p1b-evaluate --observation-mode both --format markdown
python -m bug_cause_inference.p1b.real_diff --validate
```

Generate the P1c analysis-only robustness report over existing P1b runs:

```bash
python -m bug_cause_inference.cli p1c-evaluate --format markdown
python -m bug_cause_inference.cli p1c-evaluate --observation-mode execution_grounded --json-output examples/p1c/reports/p1c_worst_case_summary.json --markdown-output examples/p1c/reports/p1c_worst_case_summary.md
```

See [`docs/p1c_result_interpretation.md`](docs/p1c_result_interpretation.md) for a consolidated reading of the current P1c1/P1c3/P1c5/P1c7/P1c9 reports.

Generate the P1d analysis-only reports over the fixed execution-grounded scaffold:

```bash
python -m bug_cause_inference.cli p1d1-report --format markdown
python -m bug_cause_inference.cli p1d2-report --format json
python -m bug_cause_inference.cli p1d3a-report --format markdown
python -m bug_cause_inference.cli p1d3b-report --format json
python -m bug_cause_inference.cli p1d3b-report --format markdown --json-output tmp/p1d3b/report.json --markdown-output tmp/p1d3b/report.md
```

P1d1 reports the fixed six-policy by five-buggy-bucket discovery-loss matrix and its restricted-pure analysis. P1d2 evaluates the preregistered `state_sequence_guard` candidate; the directional hypothesis result is `not_supported`, separately from the accepted software implementation. P1d3a and P1d3b retrospectively report four separate 6 by 5 matrices for cost profiles and dropout/delay profiles, respectively.

All four P1d report stages are analysis-only work on the fixed P1b scaffold. P1d3a and P1d3b are separate families: there is no combined cost-plus-dropout/delay interaction, joint profile-by-bucket game, cross-profile winner or ranking, weighted loss, mixed solution, Nash result, regret result, or general minimax claim.

P2a has no public CLI command. Its accepted public evidence is the frozen, versioned repository artifact pair linked above. Expansion-only buggy evidence is primary and the combined P2a-derived cohort is descriptive. All six policies have worst-bucket loss `1` on both cohorts, so the restricted-pure empirical result is a six-policy tie; this is not a policy-superiority or general minimax claim.

P2b also has no public CLI command. Its tracked artifact pair is validated through the targeted tests. `Catalog reachable` means that a direct failure-producing case exists somewhere in the frozen catalog for the included variant. It does not mean that a saved policy selected that action, that a deployable policy knows the variant identity, or that multi-step/general solvability has been established.

P2c also has no public CLI command. Its tracked artifact pair and targeted tests preserve the exact 60 trajectories and the three overlapping axes. A detector being budget-feasible at a recorded terminal state is not a claim that the stopped runner may continue or that budget caused the miss.

P2d also has no public CLI command. Its tracked artifact pair and targeted tests preserve the `60`-row support, `52/8` eligibility split, exactly-one suppression, and zero-or-one-action boundary. A one-step horizon is not evidence about the next action or a multi-step ceiling.

P2e also has no public CLI command. Its tracked artifact pair and targeted tests preserve all `60` rows, the `41/11/8` classification, every-later-decision target-only suppression, the `21/0/8/4/0/8` candidate terminal partition, and the finite continuation boundary. Detector selection and observation detection are separate even though both are `21/41`; terminal labels are not causal miss categories or policy recommendations.

P2f also has no public CLI command. Its tracked artifact pair and targeted tests preserve the exact unpatched baseline, `29/29` gate, 12 trajectories, 6 pairs, `6/6` starting and prefix agreement, target-only repeated suppression, and truthful empty-diff boundary. The `0/6` false positives in each arm are policy-support fractions for one program, not population safety estimates or causal effects.

P2g also has no public CLI command. Its tracked artifact pair and targeted tests preserve the exact five accepted benign non-empty-diff clean inputs, `14/14` gate, 60 trajectories, 30 pairs, `30/30` normal replay and starting/prefix agreement, every-firing target-only suppression, and truthful repository-relative patch evidence. The `0/30` false positives in each arm are fixed trajectory-support fractions over five hand-authored same-domain inputs, not independent program replication, population safety estimates, or causal effects.

P2h also has no public CLI command. Its tracked artifact pair and targeted tests preserve the exact 15 task-scheduler inputs, 25-oracle outcome-free gate, six accepted policies, fixed actions/costs/settings, 90 normal-execution rows, truthful scheduler-local diff/coverage evidence, and separate historical/current 28-file identities. The exact fractions describe one hand-authored toy domain; they do not select a policy or estimate behavior on other programs.

## Project Status

For the current implementation state, verification guidance, public-release boundary notes, and consolidated P1c interpretation, see:

- [`docs/implementation_status.md`](docs/implementation_status.md)
- [`docs/test_operations.md`](docs/test_operations.md)
- [`docs/release_readiness.md`](docs/release_readiness.md)
- [`docs/p1c_result_interpretation.md`](docs/p1c_result_interpretation.md)
- [`docs/p2a_result_interpretation.md`](docs/p2a_result_interpretation.md)
- [`docs/p2b_result_interpretation.md`](docs/p2b_result_interpretation.md)
- [`docs/p2c_result_interpretation.md`](docs/p2c_result_interpretation.md)
- [`docs/p2d_result_interpretation.md`](docs/p2d_result_interpretation.md)
- [`docs/p2e_result_interpretation.md`](docs/p2e_result_interpretation.md)
- [`docs/p2f_result_interpretation.md`](docs/p2f_result_interpretation.md)
- [`docs/p2g_result_interpretation.md`](docs/p2g_result_interpretation.md)
- [`docs/p2h_result_interpretation.md`](docs/p2h_result_interpretation.md)

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

With `--observation-mode both`, the P1b evaluator also reports a primary-policy comparison for `metadata_synth` versus `execution_grounded`, including `execution_minus_metadata_delta` and `metadata_optimism_gap`. Positive `metadata_optimism_gap` means the metadata-synth baseline made the primary policy look better than execution-grounded evidence. For lower-is-better metrics such as false-positive rate and mean cost, the gap is `execution_grounded_value - metadata_synth_value`; otherwise it is `metadata_synth_value - execution_grounded_value`.

P1c evaluator reports analysis-only robustness diagnostics, including:

- raw variant worst-case IDs
- bucket-level discovery, cost, localization, cause, fix-intent, wrong-cause, false-positive, and mean-cost metrics
- headline worst-case bucket summaries
- average-versus-worst gaps
- metric-specific selected buckets
- bounded observation-cost stress profiles and profile-conditioned selected-bucket shifts
- bounded observation dropout/delay stress profiles

P1c reporting is analysis-only. Its primary observation mode is `execution_grounded`; `metadata_synth` is only diagnostic when requested.

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
- P1b `metadata_synth` observations are synthesized from ground-truth variant metadata via discovery-action matching. They are kept as a frozen baseline for comparison, not as evidence of real fault-localization ability.
- P1b `execution_grounded` observations are derived from checkout test results, exceptions, traced checkout functions, function-level Ochiai coverage suspicion, and Phase C real-diff artifacts for `inspect_recent_diff`. They still run inside a small injected benchmark scaffold rather than a real project history.
- P1b real-diff artifacts are clean baseline source plus per-variant unified patches. They are not real repository histories, and generated source trees are temporary rather than committed.
- P1b keeps synthetic recent-diff observations only in `metadata_synth`; `execution_grounded` reads the real-diff artifacts and reports changed files, changed functions, and a diff excerpt.
- P1b `run_property_search` uses deterministic enumerated cases, not randomized Hypothesis-style generation.
- P1b predicts fix-intent categories but does not generate patches.
- P1c reports robustness diagnostics over the existing P1b scaffold only; it does not add an adversarial generator, a combined stress model, or a formal game-theoretic guarantee.
- P1d reports are fixed-scaffold analysis only. P1d3a and P1d3b are retrospective, separate profile-conditioned families and do not establish causal effects, unseen-profile or unseen-variant generalization, combined-profile robustness, or production performance.
- P2a variants are hand-authored, stratified, same-domain, and non-iid. The expansion contains 10 buggy and 5 clean checkout/pricing variants, and location evaluation remains function-level.
- P2a real-diff artifacts are synthetic baseline-plus-patch artifacts, not real repository histories. Its LOVO analysis is descriptive influence only, not inferential uncertainty or significance.
- P2a clean false positives were `0/5` for every formal policy only within the included clean cohort. The result does not establish production safety or unseen-clean behavior.
- Accepted-reference versus P2a-replay differences are catalog/context deltas, not expansion effects. The fixed legacy fix-intent posterior label space does not contain the expansion authoring labels.
- P2b is a direct one-step, ground-truth-informed fixed-catalog diagnostic. It ignores multi-step context-dependent evidence, uses variant information unavailable to deployable policies, and does not establish generalization, policy superiority, causal effects, or production performance.
- P2c covers 60 fixed same-domain policy/variant pairs only. Its ground-truth-informed detector mapping is unavailable to deployable policies, its reduced traces exclude full posterior and action-score payloads, and its selection, budget-state, and termination axes are descriptive and overlapping rather than causal.
- P2d covers the same fixed support and only one suppressed predicate evaluation followed by at most one action. Its `11/52` selections and detections and `11/52` horizons do not support causal, policy-performance, multi-step, generalization, deployment, or production claims.
- P2e covers the same fixed support and 41 bounded continuations only. Its repeated target-only suppression, `21/41` selections, `21/41` detections, and `8/4/8` budget/max-step/no-action endpoints do not support causal, policy-performance, optimality, generalization, deployment, or production claims.
- P2f covers one exact unpatched program and six paired policy executions only. Its `0/6` per-arm false positives, `4/1/1` intervention terminals, and repeated target-only suppression do not support clean-safety, causal, policy-performance, generalization, deployment, or production claims.
- P2g covers five accepted hand-authored same-domain non-iid benign-diff clean inputs and 30 paired input-policy executions only. Its `0/30` per-arm false positives, `20/5/5` intervention terminals, and repeated target-only suppression do not support population clean-safety, causal, policy-performance, generalization, inference, deployment, or production claims.
- P2h covers one hand-authored, fixed-input, non-iid toy task-scheduler domain and 90 crossed input-policy rows only. Its `12/60` discovery, `35/60` top-3 localization, `16/60` cause/fix, and `0/30` clean-false-positive results do not support policy ranking, causal transfer, population, inferential, arbitrary-program, scheduler-quality, release, deployment, or production claims.

## Reproducibility Notes

- Synthetic cases use fixed seed `20260627`.
- The first MVP contains 50 cases: 5 cause categories times 10 cases.
- Each case has 2 initial observations and all 8 possible investigation outcomes.
- The current generated dataset has initial top-1 accuracy of 70% and initial top-2 accuracy of 100%, so evaluation reports both all-case and initially-wrong-case performance.
- Generated examples under `examples/` are reproducible from the CLI.
- P1b examples under `examples/p1b/` are generated by `p1b-list-variants`, `p1b-report`, and `p1b-evaluate`. The evaluation summary example uses `--observation-mode both` to show the frozen metadata-synth baseline versus execution-grounded observations after the Phase C real-diff connection.

## License

MIT.
