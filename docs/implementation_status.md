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
- P2a-only patch-grounded adapter and frozen action-test catalog, including accepted exact legacy compatibility evidence for all 150 ordered legacy policy/variant pairs.
- P2a candidate authoring and adequacy/freeze tooling for a hand-authored same-domain expansion of 10 buggy and 5 clean checkout/pricing variants.
- P2a official freeze realization with versioned candidate, patch, artifact-manifest, and freeze-bundle evidence.
- P2a-B versioned evaluation and deterministic JSON/Markdown reporting with separate accepted-reference, P2a-replay, expansion-only, and combined identities for both buggy and clean evidence.
- P2a-B corrective fail-closed gate validation and saved-outcome-only LOVO reporting: 20 buggy and 10 clean descriptive influence projections without policy reruns.
- P2a result interpretation note: [`docs/p2a_result_interpretation.md`](p2a_result_interpretation.md).
- P2b fixed-catalog solvability ceiling source, tests, and versioned JSON/Markdown artifacts, merged by PR #28 after the cross-platform identity correction.
- P2b exact descriptive diagnostic: 240 case evaluations, catalog reachability `10/10`, one-step budget feasibility `10/10`, minimum costs `2,2,2,2,3,3,4,4,2,2`, and saved-policy ceiling gaps `4/5,4/5,4/5,4/5,1,1`.
- P2b software conformance, versioned artifact identity, descriptive result, and public documentation were accepted as four separate decisions; the documentation decision followed independent documentation review and required verification.
- P2b result interpretation note: [`docs/p2b_result_interpretation.md`](p2b_result_interpretation.md).
- P2c frozen-policy trajectory audit source, tests, and versioned JSON/Markdown evidence, merged by PR #30 for the accepted expansion-only `10 × 6 = 60` trajectories.
- P2c exact descriptive result: accepted P2a replay and P2b mapping agreement `60/60`, direct detector selected/discovered `8/60`, not selected `52/60`, unselected terminal detector feasible `52/52`, and stops `58` no-bug probability threshold / `2` budget limit.
- P2c software conformance final audit, versioned artifact identity, descriptive result, and public documentation were accepted as four separate decisions; the documentation decision followed independent documentation review, required verification, and status-closure re-review.
- P2c result interpretation note: [`docs/p2c_result_interpretation.md`](p2c_result_interpretation.md).
- P2d one-step stop-relaxation audit source, tests, and versioned JSON/Markdown evidence, merged by PR #32 over the same accepted 60 pairs. The 52 preregistered candidates suppress only the terminal no-bug-probability predicate once and execute at most one frozen-policy action; the remaining 8 rows stay in overall support as not applicable.
- P2d implementation evidence observes 0 alternate residual stops, 52 action decisions, 11 direct-detector selections, 11 detected observations, and post-action outcomes of 41 no-bug threshold stops plus 11 one-step horizons. These fixed-input observations are model-internal, non-causal, and non-deployable.
- P2d final merged-tree software conformance, versioned artifact identity, descriptive result, and public documentation are accepted as four separate decisions; the documentation decision followed independent documentation review, required verification, and status-closure re-review.
- P2d result interpretation note: [`docs/p2d_result_interpretation.md`](p2d_result_interpretation.md).
- P2e bounded threshold-relaxation continuation audit source, tests, and versioned JSON/Markdown evidence, merged by PR #34 over the same accepted 60 pairs. The 41 P2d post-action threshold rows suppress only that threshold at every later decision while retaining the accepted policy, state, RNG, execution context, costs, budget, max-step, observation, and update contracts; 11 P2d detector endpoints and 8 P2d not-applicable rows remain in overall support.
- P2e implementation evidence observes 21 direct-detector endpoints, 8 budget stops, 4 max-step stops, and 8 no-available-action terminations among the 41 continuation candidates. Direct-detector selection and observation detection are recorded separately and are both `21/41` in this fixed artifact.
- P2e final merged-tree software conformance, versioned artifact identity, descriptive result, and public documentation are accepted as four separate decisions. The documentation decision followed independent documentation review and required verification.
- P2e result interpretation note: [`docs/p2e_result_interpretation.md`](p2e_result_interpretation.md).
- P2f canonical no-diff clean paired continuation audit candidate source, tests, and versioned JSON/Markdown evidence over one exact unpatched P1b baseline. It compares the six accepted policies under the normal control and repeated suppression of only `no_bug_probability_threshold`, yielding 12 trajectories and 6 pairs without manufacturing diff evidence.
- P2f candidate evidence records control false positives `0/6` and target-suppressed continuation false positives `0/6`; intervention terminals are 4 budget limits, 1 max-step limit, and 1 no-available-action stop. These are fixed-input descriptive observations pending independent implementation acceptance, not a safety rate, causal effect, policy improvement, or deployable result.
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
- A public P2a CLI command. The accepted P2a evidence is published as versioned repository artifacts, not through a reporting command.
- A second P2a domain, unseen-variant evaluation, inferential analysis, confidence intervals, bootstrap analysis, or significance testing.
- P2a policy tuning, new policies, combined profiles, weighted or mixed solutions, Nash analysis, regret analysis, or a general minimax result.
- A public P2b CLI command, deployable P2b policy, multi-step sequence ceiling, dynamic-programming result, or general solvability bound.
- A new or tuned policy, optimized/unbounded P2c/P2d/P2e/P2f sequence search or DP analysis, a second domain, additional clean inputs, inferential analysis, or production-readiness claim.

## Deferred To Future Work

- `oracle_policy` or `dynamic_programming_upper_bound` as an upper-bound comparison.
- Learned or calibrated likelihood tables.
- Noisy, missing, or probabilistic observations.
- Case-specific investigation costs.
- Larger real-code fault localization beyond the small P1b injected-bug scaffold.
- Adversarial or worst-case bug models for P1c.
- A separately reviewed design for any future combined cost plus dropout/delay interaction.
- Any benchmark expansion beyond the accepted P2a same-domain cohort, new policy/variant study, uncertainty analysis, or cross-profile optimization requires a separate specification and review.
- Any P2b follow-up involving a sequence/DP ceiling, deployable policy candidate, second domain, clean stress, or inference requires a separate pre-outcome specification and review.
- Any P2c/P2d/P2e follow-up beyond the accepted bounded P2e continuation contract, including a new or tuned policy, optimized/unbounded sequence or DP analysis, second domain, clean stress, inference, or production readiness, requires a separate pre-outcome specification and review.

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
- P2a is a hand-authored, stratified, same-domain, non-iid evidence expansion. Its location evidence is function-level and its real-diff artifacts are synthetic baseline-plus-patch artifacts rather than real repository histories.
- P2a provides no second-domain or unseen-variant generalization, statistical significance, confidence interval, bootstrap result, production performance, policy-superiority, general minimax, Nash, regret, or mixed-strategy claim.
- Expansion-only and combined P2a buggy evidence both have worst-bucket loss `1` for all six policies, yielding a restricted-pure empirical six-policy tie. This describes only the fixed matrices.
- P2a clean false positives were `0/5` and no-bug stops were `5/5` for every formal policy only in the included five-variant clean expansion cohort.
- P2a LOVO is descriptive influence analysis over saved frozen outcomes, not uncertainty estimation. Accepted-reference versus replay differences are catalog/context deltas, not expansion effects.
- The fixed legacy fix-intent posterior label space does not contain the expansion authoring labels.
- P2b is an analysis-only, ground-truth-informed, non-deployable one-step diagnostic over the fixed P2a cohort and catalog. It does not establish a seventh policy, policy winner, causal policy inferiority, general upper bound, unseen-variant behavior, or production readiness.
- P2b `catalog_reachable_policy_missed` means only a selection/order/stop trajectory limitation under the fixed contract. The one-step ceiling does not identify which trajectory mechanism caused a miss and ignores multi-step context-dependent evidence.
- P2c is an analysis-only, fixed-input, ground-truth-informed, non-deployable audit over 60 same-domain pairs. Selection, recorded budget feasibility, and termination are overlapping descriptive axes, not mutually exclusive causal explanations. Terminal budget feasibility does not imply that an action remains selectable after the runner's stop condition fires or that budget caused a miss.
- P2d is a model-internal one-step counterfactual over the same fixed cohort. Its exactly-once stop suppression and 11/52 direct-detector selections do not establish stop causality, a policy defect or ranking, deployable improvement, multi-step reachability, generalization, or production readiness.
- P2e is a model-internal bounded continuation over 41 fixed P2d post-action states. Repeated target-only suppression and 21/41 direct-detector endpoints do not establish threshold causality or defect, policy ranking or improvement, sequence optimality, deployability, generalization, inference, or production readiness.
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
python -m pytest tests/test_p2b_solvability_ceiling.py tests/test_p2b_reports.py -q -p no:cacheprovider
python -B -m pytest tests/test_p2c_trajectory_audit.py tests/test_p2c_reports.py -q -p no:cacheprovider
python -m bug_cause_inference.cli p1d1-report --format markdown
python -m bug_cause_inference.cli p1d2-report --format json
python -m bug_cause_inference.cli p1d3a-report --format markdown
python -m bug_cause_inference.cli p1d3b-report --format json
python -m bug_cause_inference.p1b.real_diff --validate
```

## Latest Test Result

### Current P2f candidate evidence (acceptance pending)

The current P2f pre-review checkpoint records:

```text
P2f targeted                           56 passed
P2a-P2f relevant regression           767 passed
full repository suite                2085 passed
P1b real-diff validator                25 / 25
isolated fresh artifact runs            2 / 2 exact
ordered support                        12 / 12
paired support                           6 / 6
baseline validity gate                 29 / 29
control threshold terminals              6 / 6
control false positives                   0 / 6
intervention false positives              0 / 6
intervention terminals                 4 budget / 1 max-step / 1 no-action
accepted input identities              65 / 65
```

Candidate versioned artifacts:

- JSON: 920,661 bytes, SHA-256 `f0ffbddb24cd500144ea0b52958b3ae51d81e2b895ff8b89faf3da504a871000`.
- Markdown: 921,896 bytes, SHA-256 `a93019bb2422278d8efe1b9fdbb1453ba0829b6d0388ff77b172e5ca21c1410a`.
- Validated-summary digest: `36d5ae198b4e9f873dedd4d13ac9ce467cde373fc8a7bf4ec6a30f32b360dfad`.
- 65-file identity-contract digest: `aca567fb7048aac2b6349a6383ec0aa601ceedde504724e4c75ddbf1e8729d0a`.

The first outcome followed the accepted specification review and explicit five-file pre-outcome freeze. Post-first-execution corrections made canonical result digests independent of JSON object insertion order and closed two fail-closed decision/checkpoint validation findings; they did not change any policy action, terminal, metric, input, artifact byte, or claim boundary. The distinct independent implementation reviewer accepted software conformance, candidate artifact identity, descriptive result, and documentation boundary with unresolved High/Medium/Low findings `0/0/0`. Targeted, relevant, full-suite, real-diff, and two-run identity verification passed. Final merged-tree acceptance and public closeout remain pending and separate.

### Current P2e accepted implementation, artifact, and result evidence

The current P2e branch checkpoint records:

```text
P2e targeted                           43 passed
P2a-P2e relevant regression           696 passed
full repository suite                2029 passed
P1b real-diff validator                25 / 25
ordered support                        60 / 60
accepted P2d replay agreement          60 / 60
continuation candidates                41 / 60
P2d direct-detector endpoints          11 / 60
P2d not applicable                      8 / 60
P2e terminal reasons                  21 detector / 8 budget / 4 max-step / 8 no-action
accepted input identities              57 / 57
```

Versioned P2e artifacts:

- JSON: 464,656 bytes, SHA-256 `28af62b91f2a25ee4cb8f7aa4cef8186d6976863ae1fd8f0ac17f1d067befb61`.
- Markdown: 465,827 bytes, SHA-256 `a99e72e4334d76a74a5fb6c5a1e8b7c9d13975758d14238f178348c0fa135174`.
- Validated-summary digest: `e7dd83d7579274b19eb9a4af4940b7a26d40c52fcc9da6c44d0f83453220945d`.
- Pair-results digest: `cf6497bdea1c60dc176bab98e96e22a7e162feefc5953c9174948b47d82c4789`.
- Aggregate-results digest: `349ac974d3ea4bc1bd690d44876129404b2d138f060a90a7693dbb4917cb982a`.
- 57-file identity-contract digest: `10151569d670f0ada06ae167df1d82f4c77ce66c086c778a299b50ce61e4add5`.

Two isolated final merged-tree fresh runs and the independent acceptance review match both tracked files byte-for-byte and semantically. The four formal decisions remain separate:

```text
P2e software conformance final audit  accepted
P2e versioned artifact identity       accepted
P2e descriptive result                accepted
P2e public documentation              accepted
```

The historical pre-outcome five-file identity remains embedded in the artifact. The accepted final merged current LF-canonical map is a separate reviewed identity gate; checkout-specific raw pre/post snapshots separately detect same-run drift. Repository-wide Ruff still reports only the three pre-existing `F401` findings in `p1b/policies.py`, `p1b/reports.py`, and `p1d/p1d2_evaluation.py`; all P2e changed Python files pass Ruff. These fixed-input observations do not establish causal attribution, policy ranking or improvement, sequence optimality, generalization, or deployability. Accepted P1b/P2a/P2b/P2c/P2d identities and results remain unchanged.

### Current accepted P2d evidence

The final merged-tree P2d checkpoint records:

```text
P2d targeted                          34 passed
ordered support                       60 / 60
accepted P2c replay agreement         60 / 60
intervention candidates               52 / 60
not applicable                         8 / 60
alternate stop before action           0 / 52
action decision reached               52 / 52
direct detector selected              11 / 52
observation detected                  11 / 52
post-action outcomes                  41 threshold / 11 one-step horizon
accepted input identities             50 / 50
```

Accepted versioned P2d artifacts:

- JSON: 248,450 bytes, SHA-256 `5fb30992bc16666fd3210709b1143e34f62c6f07635fe72962a4a7880c336f93`.
- Markdown: 249,662 bytes, SHA-256 `633305a95afbf237c2163ac3b1de634bf9c6e9a696747ec04a58e14a7c015dd4`.
- Validated-summary digest: `fab660ba884ec3c1b1bc0ba5348dff168a850cb6e305f9eb708b03c3205e4fc0`.
- 50-file identity-contract digest: `7d127bcedb58f59487e16b3ec9c3a300753fe48108ef2d8a676b4c8b059217b8`.

Two isolated fresh runs match both tracked files byte-for-byte and semantically. The four decisions remain separate:

```text
P2d software conformance final audit        accepted
P2d versioned artifact identity             accepted
P2d descriptive result                      accepted
P2d public documentation                    accepted
```

Accepted P2a/P2b/P2c identities and results remain unchanged. This evidence does not establish causal attribution, policy ranking or improvement, multi-step reachability, or deployability.

### Current accepted P2c evidence

The final merged P2c checkpoint records:

```text
P2c targeted                          30 passed
ordered support                       60 / 60
accepted P2a replay agreement         60 / 60
accepted P2b mapping agreement        60 / 60
detector selected/discovered           8 / 60
detector not selected                 52 / 60
unselected terminal feasible          52 / 52
stop reasons                          58 threshold / 2 budget
accepted input identities             43 / 43
```

Current versioned P2c artifacts:

- JSON: 387,424 bytes, SHA-256 `1ebfb62edd5034fd57ea69e18c3eb647a3a8746946ecb98d80b66fa127d989d7`.
- Markdown: 389,004 bytes, SHA-256 `ee9bfda6a7b352ff770fa3025dff4d4feb94e4e36201d256a76de6d569286666`.
- Validated-summary digest: `3872257449d76453f6910b56d28f8e4fdf6c7bb7de30410b2d26335143c0392c`.
- 43-file identity-contract digest: `1a7c59b40dc837b1c2199a6f1fe8fc8016b87400df89eda05c00e28f0b0767bc`.

The four decisions remain separate:

```text
P2c software conformance final audit        accepted
P2c versioned artifact identity             accepted
P2c descriptive result                      accepted
P2c public documentation                    accepted
```

The artifact pair repeats byte-for-byte across two isolated fresh runs and has exact semantic agreement. Accepted P2a/P2b identities remain unchanged. These fixed-input observations do not rank policies or establish causal miss reasons, generalization, or production readiness.

### Current accepted P2b evidence

The final merged P2b checkpoint includes the Windows/Linux portability correction and records:

```text
P2b targeted                 46 passed
case evaluations             240
catalog reachable            10/10
budget feasible              10/10
minimum costs                2,2,2,2,3,3,4,4,2,2
policy ceiling gaps          4/5,4/5,4/5,4/5,1,1
accepted input identities    39/39
```

Current versioned P2b artifacts:

- JSON: 144,393 bytes, SHA-256 `1bbb71c5627f756f5dba3aba4f5f333f287f2fbacbb805e50118074d08ce928d`.
- Markdown: 146,660 bytes, SHA-256 `ad53651027e024febc04708763398112b81f1bf69aea4f104d94c70f4590ac3b`.
- Validated-summary digest: `873423a2cd15908300d604a970664152d931a8a306f64c797122851f887702e2`.

The artifact pair repeats byte-for-byte and has exact semantic agreement. Accepted identities use LF-canonical bytes for cross-platform identity and raw working-tree bytes for cache keys and pre/post drift detection. Accepted P2a source, tests, artifacts, dataset, catalog, settings, and outcomes are unchanged.

### Current accepted P2a implementation evidence

The accepted P2a implementation checkpoint on 2026-07-17 records the following implementation-session verification. These counts are P2a evidence and do not replace or rewrite the historical P1d checkpoint below.

```text
targeted evaluation/report  127 passed
freeze realization           25 passed
candidate                     92 passed
tooling                      235 passed
adapter                       79 passed
full suite                  1876 passed
ruff                         pass
P1b real-diff               25/25
skip / xfail                 0 / 0
```

The accepted saved outcome identity contains 150 ordered legacy policy/variant pairs and 90 ordered expansion pairs. Its canonical outcome snapshot digest is `2a1b09b38de6b2e17943726508ebc1f6728290506165cfa263a78dbb57383755`.

Current versioned evaluation artifacts:

- JSON: 1,699,240 bytes, SHA-256 `d7e69fa62513f5bbae22d570e39b841401f5110b6cd1e45701c53393eb0ef3df`.
- Markdown: 1,701,581 bytes, SHA-256 `017c5e3d9281e59e0b115a825a5f0e08f90a5e15a1e331514296adf443a2808a`.
- Validated-summary digest: `3dea5aaf38e1d9a46fd1a9ed973cb02c3fabf7ec933f2bb1c6df4f97446a9629`.

Current accepted frozen dataset identities:

- Dataset schema: `p2a_same_domain_dataset.v1`; benchmark: `p2a_checkout_pricing_same_domain_expansion_v1`.
- Candidate manifest digest: `97c2d0c0379d69010195a4b7448137e566214d88638b0f7642ee59677389cd47`.
- Artifact manifest digest: `674c3f56fbd2d4148a3e63367e4bba63ed7de634f5a219ec82a79a1c878a9544`.
- Official freeze digest: `d335f3f3a4731ee0f4d9b4648e2085eb9c687b7b2a3065d2b08eb2f65370cd9d`.

Software acceptance, official frozen dataset acceptance, and descriptive result acceptance are separate decisions. Software acceptance covers contract conformance; dataset acceptance covers the frozen 10-buggy/5-clean expansion identity; result acceptance covers only the exact descriptive observations in [`p2a_result_interpretation.md`](p2a_result_interpretation.md).

### Historical P1d closeout checkpoint

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
