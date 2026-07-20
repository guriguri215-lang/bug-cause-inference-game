# P2h Result Interpretation

## Question and Frozen Support

P2h answers one fixed-input descriptive question:

> On a pure deterministic toy task-scheduler domain, fixed before any formal-policy outcome and distinct from checkout/pricing, what descriptive bug-discovery, function-localization, cause/fix-intent-inference, clean-false-positive, action-sequence, cost, and terminal-reason results are observed when the accepted six formal policies run without policy, action, cost, or settings tuning on 10 buggy inputs and 5 benign clean inputs?

The domain is one hand-authored six-file Python task scheduler. Its 15 accepted patches are exactly `P2H-BUG-001` through `P2H-BUG-010`, followed by `P2H-CLEAN-001` through `P2H-CLEAN-005`. Before any policy trajectory is valid, the outcome-free validator checks the exact manifest, domain tree, baseline and patch identities, ordered oracle definitions, and action-to-case mapping. The baseline passes all 25 frozen oracles. Each buggy patch fails its exact designated oracle set, and every clean patch passes `25/25`.

The six policies remain in accepted formal order:

1. `fixed_checklist`
2. `test_first`
3. `coverage_first`
4. `recent_diff_first`
5. `cause_only_p1a_style`
6. `expected_utility_per_cost`

Canonical row order is input-major and policy-minor. Complete support is 15 inputs crossed with 6 policies: 60 buggy rows, 30 clean rows, and 90 rows total. Every row is a normal execution. P2h does not copy P2g's target-suppressed intervention arm.

The 15 patches are hand-authored within one toy domain. The 90 rows are crossed input-policy observations, not 90 independent programs, replications, or draws from a scheduler population.

P2h is analysis-only, fixed-input, hand-authored, deterministic, crossed, non-iid, model-internal, descriptive, non-causal, and non-deployable.

## Frozen Execution Contract

P2h reuses the accepted P1b posterior update, stable seed, action scoring, policy selection, non-repetition, budget feasibility, and stop semantics. The P2h-local adapter fixes a ten-function location universe for the scheduler domain. The policy selector receives only the policy ID, policy-visible state, remaining budget, and RNG; it does not receive input identity, hidden ground truth, expected labels, oracle results, or a precomputed trajectory.

The exact action costs are:

| Action | Cost |
|---|---:|
| `run_smoke_tests` | 1 |
| `run_boundary_tests` | 2 |
| `run_null_missing_tests` | 2 |
| `run_config_matrix_tests` | 3 |
| `run_state_sequence_tests` | 4 |
| `run_property_search` | 5 |
| `inspect_traceback` | 1 |
| `inspect_coverage_spectrum` | 3 |
| `inspect_recent_diff` | 2 |
| `inspect_spec_clause` | 2 |

The fixed settings are budget `12`, maximum steps `6`, failure penalty `14`, bug-presence threshold `0.75`, no-bug probability threshold `0.8`, location top-1 threshold `0.5`, cause top-1 threshold `0.6`, minimum expected utility per cost `0.03`, and RNG seed `0`.

Stop precedence remains:

1. `no_bug_probability_threshold`
2. `bug_confidence_threshold`
3. `budget_limit`
4. `max_steps`
5. `low_expected_utility`
6. `no_available_actions`

Recent-diff observations preserve only scheduler-local repository-relative patch evidence. Coverage observations are derived from the frozen scheduler-local function trace. Absolute checkout paths, user-specific paths, credentials, hidden labels, and oracle outcomes are not policy-visible or serialized.

## Distinct Axes and Definitions

P2h keeps these axes separate:

- **Bug discovery:** a buggy row executes an observation that detects its designated failure.
- **First failure observed:** a buggy row records a first failing observation; its penalized cost uses `14` when no failure is observed.
- **Function localization:** the frozen true function is ranked by final posterior, with descending probability and lexical identity as the tie rule. Top-1, top-3, and reciprocal rank remain separate.
- **Cause inference:** the frozen cause category is final top-1.
- **Fix-intent inference:** the frozen fix-intent category is final top-1.
- **Clean false positive:** a clean row terminates with `bug_confidence_threshold` or has final bug-presence posterior at least `0.75`.
- **Execution failure observed:** independently recomputed from whether any executed trace observation has `failure_found=true`.
- **Bug-detected observation:** independently recomputed from whether any executed trace observation has `bug_detected=true`.
- **No-bug evidence observed:** independently recomputed from whether any executed trace observation has `no_bug_evidence=true`.
- **Recent-diff location signal:** truthful scheduler-local patch identity can update location evidence, but it is not itself an execution failure, bug-detected observation, or no-bug observation. It does not independently define a false positive or terminal.
- **Cost and action count:** cumulative investigation cost and executed action count.
- **Terminal reason:** one exclusive final stop label.

A bug-confidence terminal on a buggy row is not a clean false positive. Execution failure, bug-detected signal, no-bug evidence, recent-diff location signal, discovery, localization, cause, fix, cost, action count, posterior, clean false positive, and terminal labels are independently validated axes and must not be merged into one score.

## Exact Descriptive Result

```text
outcome-free baseline gate                    25 / 25 oracles
ordered support                               15 inputs / 6 policies / 90 rows
buggy / clean rows                            60 / 30

bug discovery                                12 / 60 = 0.200000
first failure observed                       12 / 60 = 0.200000
clean false positive                          0 / 30 = 0.000000
function location top-1                      25 / 60 = 0.416667
function location top-3                      35 / 60 = 0.583333
function location MRR                          0.555192 (denominator 60)
cause top-1                                  16 / 60 = 0.266667
fix-intent top-1                             16 / 60 = 0.266667
mean penalized cost to first failure           11.733333
mean cumulative cost                            3.922222
mean action count                               2.533333

terminal no_bug_probability_threshold         85 / 90
terminal bug_confidence_threshold               4 / 90
terminal budget_limit                           1 / 90
terminal max_steps / low utility / no action    0 / 90 each
```

Per-policy values are descriptive over 10 buggy and 5 clean inputs per policy:

| Policy | Bug discovery | Clean FP | Location top-3 | Cause top-1 | Fix top-1 | Mean cost |
|---|---:|---:|---:|---:|---:|---:|
| `fixed_checklist` | 2/10 | 0/5 | 5/10 | 2/10 | 3/10 | 4.200000 |
| `test_first` | 2/10 | 0/5 | 5/10 | 2/10 | 3/10 | 4.200000 |
| `coverage_first` | 2/10 | 0/5 | 5/10 | 2/10 | 3/10 | 4.133333 |
| `recent_diff_first` | 2/10 | 0/5 | 10/10 | 2/10 | 3/10 | 5.933333 |
| `cause_only_p1a_style` | 2/10 | 0/5 | 5/10 | 4/10 | 2/10 | 2.533333 |
| `expected_utility_per_cost` | 2/10 | 0/5 | 5/10 | 4/10 | 2/10 | 2.533333 |

These values do not define or select a policy winner. A higher value on one fixed descriptive axis does not establish superiority, utility, or a production recommendation.

## Interpretation Boundary

P2h adds one domain distinct from checkout/pricing, but it remains one hand-authored toy program. It is not an independently authored program replication, random domain sample, unseen production workload, or benchmark-population estimate. The exact fractions have no confidence interval or significance claim.

The results do not establish policy ranking or superiority, checkout-to-scheduler causal transfer, arbitrary-program generalization, scheduler correctness, reliability, security, performance, inference, deployability, release readiness, or production readiness. The deterministic execution is not a randomized or identified causal contrast.

P2a through P2g answer different fixed questions. P2h does not combine their outcomes into a payoff, utility, weighted loss, tradeoff optimum, meta-ranking, threshold recommendation, or general performance score. No new or tuned policy, optimized sequence, branch search, or dynamic-programming result is evaluated here.

## Versioned Artifacts and Digests

The tracked artifacts contain the same validated summary:

- [Versioned JSON artifact](../src/bug_cause_inference/p2h/artifacts/p2h_task_scheduler_second_domain_replication_audit_v1.json) — 2,453,124 bytes; SHA-256 `d3ba265fb42dbf33e1e71ad972a85409386a2537160d7be5c09afc6e5d7d0f47`.
- [Versioned Markdown artifact](../src/bug_cause_inference/p2h/artifacts/p2h_task_scheduler_second_domain_replication_audit_v1.md) — 2,652 bytes; SHA-256 `f693f9079409fc71cb5cc8ac609d0fde47b517161162f0e7baf95cabf58c522f`.

```text
schema                         p2h_task_scheduler_second_domain_replication.v1
domain manifest digest         343746ea65d6649726e116e529c8a0e83d07f7c8d72e76c2074e21f24941304b
dependency digest              c3ca2a00d1729b003a6ac12ba73853cb3d1c86710d0fa29b4aee61e55c19179f
pre-outcome freeze digest      105a0076aaedef34c06f00b1ce43b351a74f07a364e5f23b2e72e41646e09b52
row digest                     f53d6a1d2d74cca3510ca1495814baa096ef4b1e114f22c7797a3cf3aab4ee72
aggregate digest               6befa920087340f33d69ac8912cf4c5e129980b5f2e6a2087e022e01e1a8e531
summary digest                 68a169c60dc25eda886df608560f1698eb5e09f05ed2563f2aef622b49ae3df3
outcome-free validation        06c00f7f46e8d33ec6792eb8d5d06ff259b376b0e781d7d74f9968b6b54fde9d
domain manifest LF identity    33448 bytes / 16bb5876d857e74fd4a8f63f43ab701a60fab018a2c9969d889b11d085227316
```

The JSON artifact is authoritative for the complete per-row trace, per-input, per-family, per-policy, denominator, terminal-partition, and identity details. The artifact is evidence, not its own acceptance decision.

## Historical and Current Implementation Identity

The pre-outcome freeze preserves 28 LF-canonical implementation/domain/test identities with digest:

```text
72e545afd77900b14107f93ece3b95f0289a9cd3ea1504321b2a5fd7da1813ff
```

Independent implementation review identified conformance-validation gaps after the first valid outcome. The correction was test-only in outcome effect: it changed implementation/test validation files, not the accepted execution outcome. The corrective slice added the historical/current identity gate and corrected the AST-based selector-boundary test; trajectory generation and decision replay logic were unchanged. It did not change the frozen domain, inputs, oracles, policies, actions, costs, settings, metrics, denominators, 90 rows, aggregates, serialized JSON/Markdown bytes, or claim boundary. The accepted current 28-file LF-canonical identity has digest:

```text
41937256d429feba4898f23f841415a983335e23ace54133cf0be234475ad2a8
```

Only `task_scheduler_replication.py` and `test_p2h_task_scheduler_replication.py` differ between the historical and current maps. The versioned `pre_outcome_freeze_identity.json` and `post_outcome_current_identity.json` preserve both layers. Current identity must not overwrite or rebind the historical freeze.

Portable identity normalizes CRLF and CR line endings to LF. Exact raw working-tree snapshots separately detect same-run drift within one checkout; raw constants are not cross-platform accepted identities.

## Reproduction and Verification

P2h has no public CLI command. The module runner is a fixed-audit verification surface, not a user-facing product command. Use short, unused workspace-local pytest base directories and do not run the P2a or P2b outcome runners:

```bash
python -B -m pytest tests/test_p2h_task_scheduler_replication.py tests/test_p2h_reports.py -q -p no:cacheprovider --basetemp tmp/ph-t-001
python -B -m pytest tests/test_p1b_actions.py tests/test_p1b_cli.py tests/test_p1b_dataset.py tests/test_p1b_evaluation.py tests/test_p1b_policies.py tests/test_p1b_real_diff.py tests/test_p2a_adequacy.py tests/test_p2a_candidate_oracles.py tests/test_p2a_candidates.py tests/test_p2a_compatibility.py tests/test_p2a_evaluation.py tests/test_p2a_execution.py tests/test_p2a_freeze.py tests/test_p2a_freeze_realization.py tests/test_p2a_reports.py tests/test_p2b_reports.py tests/test_p2b_solvability_ceiling.py tests/test_p2c_reports.py tests/test_p2c_trajectory_audit.py tests/test_p2d_reports.py tests/test_p2d_stop_relaxation_audit.py tests/test_p2e_continuation_audit.py tests/test_p2e_reports.py tests/test_p2f_no_diff_clean_audit.py tests/test_p2f_reports.py tests/test_p2g_benign_diff_clean_audit.py tests/test_p2g_reports.py tests/test_p2h_task_scheduler_replication.py tests/test_p2h_reports.py -q -p no:cacheprovider --basetemp tmp/ph-r-001
python -B -m pytest -q -p no:cacheprovider --basetemp tmp/ph-f-001
python -m bug_cause_inference.p1b.real_diff --validate
```

For two isolated fresh P2h runs, choose two new ignored directories and never target the tracked artifact paths:

```bash
python -B -m bug_cause_inference.p2h.task_scheduler_replication --output-dir tmp/p2h-closeout-fresh-a
python -B -m bug_cause_inference.p2h.task_scheduler_replication --output-dir tmp/p2h-closeout-fresh-b
```

Compare both generated pairs byte-for-byte and semantically with the tracked pair. Required checks include:

- exact 15-input and 6-policy order, 90 rows, 60 buggy rows, and 30 clean rows;
- outcome-free 25-oracle baseline, exact buggy designated failures, and all five clean `25/25` passes;
- exact action costs, settings, policy-visible selector boundary, decision/action/observation/update replay, and terminal partition;
- truthful scheduler-local recent-diff and coverage evidence;
- exact JSON/Markdown bytes, summary/row/aggregate/manifest/dependency/freeze/validation digests;
- historical 28-file identity and separate current 28-file identity;
- raw implementation and dependency pre/post snapshots remain unchanged within each run;
- accepted P1b–P2g source, tests, artifacts, identities, results, and public claims remain unchanged.

Use new suffixes when the example paths already exist. A fresh P2h replay is fixed-input verification only and must not be followed by input, oracle, action, cost, settings, policy, metric, denominator, result, or claim tuning.

## Acceptance and Provenance

The controlling implementation was merged by [PR #40](https://github.com/guriguri215-lang/bug-cause-inference-game/pull/40):

```text
final accepted head   1490bb52aeedbc9ca075f3daa2f6e64783be6e67
merge commit          55316cb29c3a0b87037c0bf5df829e0b127ebced
accepted/merge tree   62db4def9a9ffadb341a7925d1d7bb4660bfdf13
PR CI                 29710983703 (run #79, success)
post-merge main CI    29720182121 (run #80, success)
```

Acceptance decisions remain separate:

- P2h software conformance final audit: accepted after independent final merged-tree review.
- P2h versioned artifact identity: accepted.
- P2h descriptive result: accepted only for the exact fixed support above.
- P2h public documentation: accepted after independent documentation review, required verification, and same-reviewer status-closure re-review.

The artifact remains non-self-accepting. External acceptance and review records provide these decisions. The documentation-closeout verification passed P2h targeted `30` tests, the P1b–P2h relevant regression `1014` tests, the full repository suite `2150` tests, P1b real-diff validation `25/25`, and two isolated P2h fresh runs with exact tracked JSON/Markdown bytes and semantics. Both authoritative fresh runs preserved 32 raw implementation/dependency paths and matched all digests plus the historical/current 28-file identity gates.

This closeout accepts and publishes research evidence; it does not accept release readiness. A separate release-readiness audit and PR are required before a tag or GitHub Release. Packaging and production-readiness decisions also remain separate future work.

## Limitations and Deferred Questions

- Only one hand-authored toy task-scheduler domain and 15 fixed patches are observed; there are no independent program replicates.
- The 90 crossed rows and exact fractions are not population rates, inferential estimates, confidence intervals, or causal effects.
- Per-policy descriptions do not establish a winner, superiority, a deployable recommendation, or checkout-to-scheduler transfer.
- P2h does not establish scheduler correctness, reliability, security, performance, release readiness, or production readiness.
- No combined P2a–P2h payoff, utility, weighted loss, tradeoff optimum, or meta-ranking is defined.
- Additional domains, independently authored programs, unseen inputs, inference, new or tuned policies, optimized sequence/DP work, and production evaluation require separate pre-outcome specifications and reviews.
