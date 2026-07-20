# Test Operations

Status: operational guidance for local verification and CI. This document does not change runtime behavior, test scope, metrics, policies, action costs, datasets, or report semantics.

## Scope

Use this note to keep evaluation and test runs consistent across local development, Codex sessions, and CI.

This note does not:

- skip, xfail, or narrow CLI/file-output tests that use `tmp_path`;
- hardcode user-specific temporary directories;
- weaken GitHub Actions verification;
- change P1b or P1c runtime behavior, metrics, policies, thresholds, scores, datasets, real-diff artifacts, or observation semantics.
- change accepted P2a/P2b/P2c/P2d/P2e/P2f/P2g/P2h inputs, artifacts, results, catalog cases, action costs, settings, policy outcomes, execution/intervention semantics, or contracts.

## Verification Tiers

Full repository verification:

```bash
python -B -m pytest -q -p no:cacheprovider
```

Targeted P2b diagnostic and artifact checks:

```bash
python -m pytest tests/test_p2b_solvability_ceiling.py tests/test_p2b_reports.py -q -p no:cacheprovider
```

The targeted P2b command verifies the exact 240-case result, deterministic variant order, minimum costs, saved-policy ceiling gaps, invalid-result handling, 39 accepted input identities, deterministic JSON/Markdown bytes, semantic agreement, and accepted P2a non-regression. It does not rerun saved policies, the P2a evaluation, or compatibility evaluation.

Targeted P2c trajectory and artifact checks:

```bash
python -B -m pytest tests/test_p2c_trajectory_audit.py tests/test_p2c_reports.py -q -p no:cacheprovider
```

The targeted P2c command verifies the 60-pair order and support, exact P2a replay and P2b mapping agreement, selected/feasible/termination aggregates, the 24-row overlap cross-tab, fail-closed trajectory and termination validation, 43 accepted input identities, deterministic JSON/Markdown bytes, semantic agreement, and accepted P2a/P2b non-regression.

Targeted P2d stop-relaxation and artifact checks:

```bash
python -B -m pytest tests/test_p2d_stop_relaxation_audit.py tests/test_p2d_reports.py -q -p no:cacheprovider
```

The targeted P2d command verifies the exact 60-pair order and accepted P2c replay, `52/8` eligibility, exactly-one target suppression, residual-stop precedence, zero-or-one-action horizon, separate selection and observation-detection aggregates, 60 authoritative pair digests, five-file implementation drift protection, 50 accepted input identities, deterministic JSON/Markdown bytes, semantic agreement, Python-portable normalization fixtures, and accepted P2a/P2b/P2c non-regression.

Targeted P2e continuation and artifact checks:

```bash
python -B -m pytest tests/test_p2e_continuation_audit.py tests/test_p2e_reports.py -q -p no:cacheprovider
```

The targeted P2e command verifies the exact 60-pair order and accepted P2d replay; `41/11/8` classification; 41 state/RNG/execution-context checkpoints; every-later-decision target-only suppression; residual-stop precedence; retained state, RNG, execution context, policy, costs, budget, max-step, observations, and updates; separate selection and observation-detection fields; the exclusive `21/0/8/4/0/8` terminal partition; finite non-repeating continuation; 60 authoritative pair digests; five-file historical/current identity separation and raw same-run drift protection; 57 accepted input identities; deterministic JSON/Markdown bytes and semantics; and accepted P1b/P2a/P2b/P2c/P2d non-regression.

Targeted P2f paired clean-boundary and artifact checks:

```bash
python -B -m pytest tests/test_p2f_no_diff_clean_audit.py tests/test_p2f_reports.py -q -p no:cacheprovider --basetemp tmp/pf-t-001
```

The targeted P2f command verifies the exact unpatched baseline and 29-case validity gate; six accepted policies, two arms, 12 trajectories, 6 pairs, starting/prefix agreement; accepted normal control; every-firing target-only suppression; residual precedence and retained state/RNG/context/policy/cost/budget/max-step/update semantics; truthful empty recent-diff fields; separate false-positive, execution-failure, bug-detected, terminal, and suppression axes; the `4/1/1` intervention partition; historical/current five-file identity separation; cross-version arithmetic fixtures; raw same-run drift; 65 accepted input identities; deterministic JSON/Markdown bytes and semantics; and accepted P1b–P2e non-regression.

Relevant P2a/P2b/P2c/P2d/P2e/P2f regression for the complete accepted-input boundary:

```bash
python -B -m pytest tests/test_p2a_adequacy.py tests/test_p2a_candidate_oracles.py tests/test_p2a_candidates.py tests/test_p2a_compatibility.py tests/test_p2a_evaluation.py tests/test_p2a_execution.py tests/test_p2a_freeze.py tests/test_p2a_freeze_realization.py tests/test_p2a_reports.py tests/test_p2b_reports.py tests/test_p2b_solvability_ceiling.py tests/test_p2c_reports.py tests/test_p2c_trajectory_audit.py tests/test_p2d_reports.py tests/test_p2d_stop_relaxation_audit.py tests/test_p2e_continuation_audit.py tests/test_p2e_reports.py tests/test_p2f_no_diff_clean_audit.py tests/test_p2f_reports.py -q -p no:cacheprovider --basetemp tmp/pf-r-001
```

This regression covers the P2a candidate, compatibility, execution, freeze, evaluation, and report layers plus the P2b, P2c, P2d, P2e, and P2f diagnostics. P2f closeout uses it as read-only non-regression evidence; it does not invoke the P2a or P2b outcome runners.

Targeted P2g accepted-benign-diff clean paired audit and artifact checks:

```bash
python -B -m pytest tests/test_p2g_benign_diff_clean_audit.py tests/test_p2g_reports.py -q -p no:cacheprovider --basetemp tmp/pg-t-001
```

The targeted P2g command verifies the exact five accepted P2a clean patches and `14/14` oracle gate; six policies, two arms, 60 trajectories, and 30 pairs; starting and pre-target prefix agreement; exact normal-control replay; truthful non-empty repository-relative recent-diff evidence; every-firing target-only suppression and residual precedence; policy/state/RNG/context/action/update replay; separate false-positive, execution-failure, bug-detected, terminal, and suppression axes; historical/current five-file identity separation; fail-closed semantic mutations; and deterministic JSON/Markdown bytes and semantics.

Relevant P2a–P2g regression for the complete accepted-input boundary:

```bash
python -B -m pytest tests/test_p2a_adequacy.py tests/test_p2a_candidate_oracles.py tests/test_p2a_candidates.py tests/test_p2a_compatibility.py tests/test_p2a_evaluation.py tests/test_p2a_execution.py tests/test_p2a_freeze.py tests/test_p2a_freeze_realization.py tests/test_p2a_reports.py tests/test_p2b_reports.py tests/test_p2b_solvability_ceiling.py tests/test_p2c_reports.py tests/test_p2c_trajectory_audit.py tests/test_p2d_reports.py tests/test_p2d_stop_relaxation_audit.py tests/test_p2e_continuation_audit.py tests/test_p2e_reports.py tests/test_p2f_no_diff_clean_audit.py tests/test_p2f_reports.py tests/test_p2g_benign_diff_clean_audit.py tests/test_p2g_reports.py -q -p no:cacheprovider --basetemp tmp/pg-r-001
```

This regression is read-only non-regression evidence for P2a–P2f and verification of the additive P2g diagnostic. It does not invoke the P2a or P2b outcome runners.

Targeted P2h task-scheduler second-domain replication and artifact checks:

```bash
python -B -m pytest tests/test_p2h_task_scheduler_replication.py tests/test_p2h_reports.py -q -p no:cacheprovider --basetemp tmp/ph-t-001
```

The targeted P2h command verifies the exact 15-input and six-policy order; 60 buggy, 30 clean, and 90 total normal-execution rows; the outcome-free 25-oracle baseline and input-specific failure/pass gate; frozen actions, costs, settings, stop precedence, and policy-visible selector boundary; truthful scheduler-local recent-diff and coverage evidence; independent row replay and aggregate recomputation; false-positive, discovery, localization, cause, fix-intent, cost, action-count, and terminal axes; fail-closed schema, identity, private-path, and mutation gates; historical/current 28-file identity separation; and deterministic JSON/Markdown bytes and semantics.

Relevant P1b–P2h regression for the complete accepted-input boundary:

```bash
python -B -m pytest tests/test_p1b_actions.py tests/test_p1b_cli.py tests/test_p1b_dataset.py tests/test_p1b_evaluation.py tests/test_p1b_policies.py tests/test_p1b_real_diff.py tests/test_p2a_adequacy.py tests/test_p2a_candidate_oracles.py tests/test_p2a_candidates.py tests/test_p2a_compatibility.py tests/test_p2a_evaluation.py tests/test_p2a_execution.py tests/test_p2a_freeze.py tests/test_p2a_freeze_realization.py tests/test_p2a_reports.py tests/test_p2b_reports.py tests/test_p2b_solvability_ceiling.py tests/test_p2c_reports.py tests/test_p2c_trajectory_audit.py tests/test_p2d_reports.py tests/test_p2d_stop_relaxation_audit.py tests/test_p2e_continuation_audit.py tests/test_p2e_reports.py tests/test_p2f_no_diff_clean_audit.py tests/test_p2f_reports.py tests/test_p2g_benign_diff_clean_audit.py tests/test_p2g_reports.py tests/test_p2h_task_scheduler_replication.py tests/test_p2h_reports.py -q -p no:cacheprovider --basetemp tmp/ph-r-001
```

This regression verifies the accepted P1b boundary and P2a–P2g non-regression together with the additive P2h diagnostic. It does not invoke the P2a or P2b outcome runners.

Targeted P1b/P1c CLI and real-diff checks:

```bash
python -B -m pytest tests/test_cli.py tests/test_p1b_cli.py tests/test_p1c_cli.py tests/test_p1b_real_diff.py -q -p no:cacheprovider
python -m bug_cause_inference.p1b.real_diff --validate
```

Targeted P1c report checks:

```bash
python -B -m pytest tests/test_p1c_labels.py tests/test_p1c_evaluation.py tests/test_p1c_cli.py -q -p no:cacheprovider
python -m bug_cause_inference.cli p1c-evaluate --format json
python -m bug_cause_inference.cli p1c-evaluate --format markdown
```

Targeted P1d report checks:

```bash
python -m pytest tests/test_p1d1_evaluation.py tests/test_p1d1_cli.py -q
python -m pytest tests/test_p1d2_evaluation.py tests/test_p1d2_cli.py -q
python -m pytest tests/test_p1d3a_evaluation.py tests/test_p1d3a_cli.py -q
python -m pytest tests/test_p1d3b_evaluation.py tests/test_p1d3b_cli.py -q
```

P1d JSON/Markdown CLI smoke checks:

```bash
python -m bug_cause_inference.cli p1d1-report --format json
python -m bug_cause_inference.cli p1d1-report --format markdown
python -m bug_cause_inference.cli p1d2-report --format json
python -m bug_cause_inference.cli p1d2-report --format markdown
python -m bug_cause_inference.cli p1d3a-report --format json
python -m bug_cause_inference.cli p1d3a-report --format markdown
python -m bug_cause_inference.cli p1d3b-report --format json
python -m bug_cause_inference.cli p1d3b-report --format markdown
```

Representative smoke checks for generated outputs:

```bash
python -m bug_cause_inference.cli p1b-evaluate --observation-mode both --format markdown
python -m bug_cause_inference.cli p1c-evaluate --observation-mode execution_grounded --format markdown
python -m bug_cause_inference.cli p1c-evaluate --observation-mode both --policies expected_utility_per_cost --format json
```

## CI Expectations

`.github/workflows/ci.yml` is expected to run on Ubuntu with Python 3.10, install `requirements.txt` plus the editable package, run the full pytest suite, and validate P1b real-diff artifacts.

CI should keep the full pytest command and real-diff validator unless there is a clear repository-side problem. Do not reduce CI coverage just to avoid local sandbox issues or speed up verification.

The full suite includes P2b, P2c, P2d, P2e, P2f, P2g, and P2h. On Linux, the tracked LF artifacts and accepted identities must match the same portable LF-canonical hashes used on Windows. A platform-specific raw working-tree hash is not an accepted portable artifact identity.

## P2b Artifact and Portability Checks

P2b separates two identity purposes:

- **Portable accepted identity:** SHA-256 after CRLF-to-LF normalization. This must match across Windows CRLF and Linux LF checkouts.
- **Raw working-tree identity:** SHA-256 of exact local bytes. This keys parsed-input caching and detects fresh pre/post execution drift within one checkout.

The P2b report tests require exact tracked bytes and hashes:

```text
JSON      144393 bytes / 1bbb71c5627f756f5dba3aba4f5f333f287f2fbacbb805e50118074d08ce928d
Markdown  146660 bytes / ad53651027e024febc04708763398112b81f1bf69aea4f104d94c70f4590ac3b
summary                 / 873423a2cd15908300d604a970664152d931a8a306f64c797122851f887702e2
```

The generated JSON and Markdown must repeat byte-for-byte and recover the same validated summary. Accepted P2a identity checks must remain unchanged. Do not regenerate accepted P2a or P2b artifacts merely to accommodate checkout line endings; investigate whether the portable identity or raw drift boundary is being applied incorrectly.

## P2c Artifact, Fresh-Run, and Portability Checks

P2c uses the same separation between LF-canonical portable identity and exact raw working-tree drift detection. Its accepted identities are:

```text
JSON      387424 bytes / 1ebfb62edd5034fd57ea69e18c3eb647a3a8746946ecb98d80b66fa127d989d7
Markdown  389004 bytes / ee9bfda6a7b352ff770fa3025dff4d4feb94e4e36201d256a76de6d569286666
summary                 / 3872257449d76453f6910b56d28f8e4fdf6c7bb7de30410b2d26335143c0392c
43-file contract        / 1a7c59b40dc837b1c2199a6f1fe8fc8016b87400df89eda05c00e28f0b0767bc
```

Run two P2c audits into isolated temporary directories and compare both candidate pairs with the tracked files. The complete portable example is in [`docs/p2c_result_interpretation.md`](p2c_result_interpretation.md#reproduction-and-verification). The required safety properties are:

1. Create fresh temporary output directories; never use the tracked artifact paths as output arguments.
2. Run `run_trajectory_audit()` twice and serialize each result with `save_p2c_report()`.
3. Compare each candidate JSON and Markdown file byte-for-byte with the tracked pair.
4. Recover and validate the same summary from JSON and Markdown.
5. Recompute the compact summary digest and 43-file identity-contract digest.
6. Confirm the accepted P2a/P2b bytes, hashes, and semantic digests remain unchanged.

Do not overwrite or regenerate the tracked P2c artifacts during verification. Do not run the P2a or P2b outcome runners as part of P2c closeout. P2c fresh replay is permitted because it is the audit under verification; it must remain fixed-input and must not be followed by metric, catalog, policy, or claim tuning.

## P2d Artifact, Fresh-Run, and Portability Checks

P2d retains the portable LF-canonical identity/raw same-run drift separation and adds 60 authoritative pair-result digests. Its accepted identities are:

```text
JSON      248450 bytes / 5fb30992bc16666fd3210709b1143e34f62c6f07635fe72962a4a7880c336f93
Markdown  249662 bytes / 633305a95afbf237c2163ac3b1de634bf9c6e9a696747ec04a58e14a7c015dd4
summary                 / fab660ba884ec3c1b1bc0ba5348dff168a850cb6e305f9eb708b03c3205e4fc0
50-file contract        / 7d127bcedb58f59487e16b3ec9c3a300753fe48108ef2d8a676b4c8b059217b8
```

Run two P2d audits into isolated temporary directories and compare both output pairs with the tracked files. The complete safe example is in [`docs/p2d_result_interpretation.md`](p2d_result_interpretation.md#reproduction-and-verification). Required checks are:

- both fresh JSON files equal the tracked JSON byte-for-byte;
- both fresh Markdown files equal the tracked Markdown byte-for-byte;
- JSON and Markdown recover the same validated summary;
- the compact canonical digest and 50-file identity contract match exactly;
- all 60 authoritative pair digests, 60 accepted P2c replays, and row consistency checks match;
- accepted P2a/P2b/P2c artifact identities and results remain unchanged;
- the five-file implementation raw snapshot is unchanged before and after each run.

Python 3.10 and 3.12 must produce the same accepted rows and artifacts. P2d's reviewed `math.fsum` normalization is confined to the P2d replay/update wrapper; do not modify accepted upstream update semantics to accommodate a platform. Portable identity normalizes CRLF to LF, while raw drift uses exact checkout bytes.

Do not overwrite or regenerate tracked P2d artifacts during verification. Do not run the P2a or P2b outcome runners as part of P2d closeout. A fixed-input P2d fresh replay is permitted, but it must not be followed by metric, catalog, policy, eligibility, intervention, or claim tuning.

## P2e Artifact, Fresh-Run, and Identity Checks

P2e preserves the historical five-file pre-outcome identity. Verification separately compares the current five-file LF-canonical hashes with the accepted final merged map, while the runner compares checkout-specific raw snapshots before and after each run. Its accepted artifact identities are:

```text
JSON      464656 bytes / 28af62b91f2a25ee4cb8f7aa4cef8186d6976863ae1fd8f0ac17f1d067befb61
Markdown  465827 bytes / a99e72e4334d76a74a5fb6c5a1e8b7c9d13975758d14238f178348c0fa135174
summary                 / e7dd83d7579274b19eb9a4af4940b7a26d40c52fcc9da6c44d0f83453220945d
pair results            / cf6497bdea1c60dc176bab98e96e22a7e162feefc5953c9174948b47d82c4789
aggregates              / 349ac974d3ea4bc1bd690d44876129404b2d138f060a90a7693dbb4917cb982a
57-file contract        / 10151569d670f0ada06ae167df1d82f4c77ce66c086c778a299b50ce61e4add5
```

Run two P2e audits into isolated temporary directories and compare both output pairs with the tracked files. The complete safe example is in [`docs/p2e_result_interpretation.md`](p2e_result_interpretation.md#reproduction-and-verification). Required checks are:

- both fresh JSON files equal the tracked JSON byte-for-byte;
- both fresh Markdown files equal the tracked Markdown byte-for-byte;
- JSON and Markdown recover the same validated summary;
- canonical, pair-results, aggregate-results, and 57-file digests match exactly;
- the artifact's historical pre-outcome implementation identity matches the frozen constants;
- the five current LF-canonical hashes equal the accepted final merged values documented in [`docs/p2e_result_interpretation.md`](p2e_result_interpretation.md#versioned-artifacts-and-identity);
- the checkout-specific current implementation raw snapshot is unchanged before and after each fresh run;
- all 60 authoritative rows and 60 accepted P2d replays match;
- all 41 state/RNG/execution-context starting checkpoints match;
- `41/11/8`, the exclusive `21/0/8/4/0/8` terminal partition, separate `21/41` selection and detection, selected-action, additional action/cost, and feasibility aggregates recompute exactly;
- accepted P1b/P2a/P2b/P2c/P2d source, tests, artifacts, identities, and results remain unchanged.

Portable identity normalizes CRLF to LF. Exact raw bytes detect same-run drift within one checkout. The reviewed difference between historical freeze identities and final current identities is expected and must not be treated as drift or used to rebind the historical freeze.

Do not overwrite or regenerate tracked P2e artifacts during verification. Do not run the P2a or P2b outcome runners as part of P2e closeout. A fixed-input P2e fresh replay is permitted, but it must not be followed by metric, catalog, policy, classification, result, or claim tuning.

## P2f Artifact, Fresh-Run, and Identity Checks

P2f preserves the historical five-file pre-outcome identity and separately gates the final merged five-file LF-canonical identity. Each runner invocation also compares checkout-specific raw snapshots before and after execution. Accepted artifact identities are:

```text
JSON         920661 bytes / f0ffbddb24cd500144ea0b52958b3ae51d81e2b895ff8b89faf3da504a871000
Markdown     921896 bytes / a93019bb2422278d8efe1b9fdbb1453ba0829b6d0388ff77b172e5ca21c1410a
summary                   / 36d5ae198b4e9f873dedd4d13ac9ce467cde373fc8a7bf4ec6a30f32b360dfad
trajectories              / 13726d00369e9483e7d395aca8a282c6abd64fde017a954de44f8b32067b7c09
pairs                     / 71e3b09994cfbf46ac27ff3fc5a47d4824bbfeabc8d820fab2d821c59c7365bf
aggregates                / ec03765df1854a9e78fe769e691d731754bca260c5f45434b3aa9b894dacc2c6
65-file contract          / aca567fb7048aac2b6349a6383ec0aa601ceedde504724e4c75ddbf1e8729d0a
```

Run two P2f audits into isolated temporary directories and compare both output pairs with the tracked files. The complete safe example and accepted final current identity map are in [`docs/p2f_result_interpretation.md`](p2f_result_interpretation.md#reproduction-and-verification). Required checks are:

- both fresh JSON and Markdown files equal the tracked pair byte-for-byte;
- JSON and Markdown recover the same validated summary;
- summary, trajectory, pair, aggregate, and 65-file digests match exactly;
- the artifact's historical pre-outcome implementation identity matches the frozen constants;
- the five current LF-canonical hashes equal the accepted final merged map;
- checkout-specific raw snapshots are unchanged before and after both runs;
- the unpatched baseline gate passes `29/29` with no fabricated diff evidence;
- ordered support is exactly 12 trajectories / 6 pairs / one program;
- pair start and prefix agreement are `6/6`;
- control/intervention false positives remain `0/6` and `0/6` as separate policy-support fractions;
- the intervention terminal partition is exactly 4 budget / 1 max-step / 1 no-available-actions;
- suppression counts are `[4,4,4,4,4,5]` and four recent-diff observations have exact empty fields;
- execution-failure and bug-detected-observation axes remain zero in both arms;
- accepted P1b–P2e source, tests, artifacts, identities, and results remain unchanged.

Portable identity normalizes CRLF and CR to LF. Historical Windows raw sizes are provenance metadata, not Linux runner-local sizes. Exact raw bytes detect same-run drift within one checkout. The P2f-local `math.fsum` correction keeps accepted checkpoints stable on Python 3.10 and 3.12 without changing P1b–P2e.

Use a new short basetemp suffix for each P2f pytest command. On Windows, a long basetemp can combine with the copied baseline namespace and ignored `__pycache__` filenames to exceed the legacy path-length boundary; that filesystem error is not a P2f assertion result.

Do not overwrite or regenerate tracked P2f artifacts during closeout or release verification. Do not run the P2a or P2b outcome runners. A fixed-input P2f fresh replay is verification only and must not be followed by metric, threshold, policy, denominator, result, or claim tuning.

## P2g Artifact, Fresh-Run, and Identity Checks

P2g preserves the historical five-file pre-outcome identity and separately gates the accepted current corrective five-file LF-canonical identity. Accepted artifact identities are:

```text
JSON        3370390 bytes / b37a6d3af44714d5cd2dcb0bc6afd4b93b43898bbdd9d75d747f8a6125a48ab0
Markdown    3371629 bytes / a01cfac29acb9a43afec7b1764ff8d926cc654327dd0e6eb95266afa58c367ec
summary                   / 1eb05962a96a3783484c0ef77e7b2fccd9f223d9663cb08a42d6787c3d1e3e2b
trajectories              / 3d7079c77a9d9d3598172d3938356b3c83367311acdde5faef386636407bf1a2
pairs                     / 8bec24f367f498cbe5d6cc6f8c81539fdf2a34fafa82dc49e300abf9de23ae26
aggregates                / 22062f67d818ef26b5f9641f36ac3cb9a526b7dee3a57a6d934f7364dd1edd0c
input contract            / ca53689e46ea7b12cbb7c42e199bfef487bf82058303cdc1024634dc1b6cc387
dependency contract       / c6c2576d575e14e1e4358bfb96df3c33b3ffa01c0edd46748793b427259c07e5
```

The accepted current LF-canonical five-file identity is:

```text
src/bug_cause_inference/p2g/__init__.py                    64 / cd9678425da62a0e2d9db430479569640a0ab4bf58ffae7f513c48381cb8cbcd
src/bug_cause_inference/p2g/benign_diff_clean_audit.py   61100 / c700a7ac5515d9c83874d88b5b071846fed7f97e567c8c06fdb0ff1c74116d11
src/bug_cause_inference/p2g/reports.py                    4030 / b4c29bba4859868ac60dfed044ba90424daa8498e2a1249d542ddce6afac0001
tests/test_p2g_benign_diff_clean_audit.py                11136 / 4746ac55aaf1bece7d5eaf79d3c6c2a1aa8869eaeff6adcf72be9805a295ff3b
tests/test_p2g_reports.py                                 3400 / 0c05ca91ab2b94bb3f0060d8147b6a5ea690e1a8f16c1e6f7deb032faf5e16be
```

The artifact's historical first-outcome map is not rebound by the reviewed current implementation corrections. Portable identity uses LF-canonical bytes; raw identity detects drift only within one checkout and run. The complete safe two-run example and correction provenance are in [`docs/p2g_result_interpretation.md`](p2g_result_interpretation.md#reproduction-and-verification).

Run two P2g audits into distinct ignored workspace-local directories and compare both serialized output pairs with the tracked files byte-for-byte and semantically. Required checks are:

- exact ordered support of 5 inputs / 6 policies / 2 arms / 60 trajectories / 30 pairs;
- clean-validity gate `14/14`, normal-control replay `30/30`, and pair start/prefix agreement `30/30`;
- control/intervention false positives `0/30` and `0/30` as separate fixed-support fractions;
- intervention terminals exactly 20 budget / 5 max-step / 5 no-available-actions;
- truthful benign-diff observations `20/20`, with zero execution failures and zero bug-detected observations in both arms;
- summary, trajectory, pair, aggregate, input-contract, and dependency-contract digests match exactly;
- the artifact historical first-outcome identity remains unchanged while the current five-file map is checked separately;
- accepted P1b–P2f source, tests, artifacts, identities, results, and public claims remain unchanged.

Do not overwrite the tracked P2g artifacts during verification. Do not run the P2a or P2b outcome runners. P2g fresh replay is fixed-input verification only and must not be followed by support, metric, threshold, policy, arm, denominator, result, or claim tuning.

The 2026-07-19 documentation-closeout checkpoint passed P2g targeted `33` tests, the P2a–P2g relevant regression `802` tests, the full repository suite `2120` tests, P1b real-diff validation `25/25`, and two isolated exact fresh P2g artifact runs. Both fresh runs preserved raw implementation/dependency snapshots and matched the tracked JSON/Markdown bytes, semantics, six digests, historical identity, and accepted current identity. These are verification results, not new outcome evidence.

## P2h Artifact, Fresh-Run, and Identity Checks

P2h preserves the historical 28-file pre-outcome identity and separately gates the accepted current corrective 28-file LF-canonical identity. Accepted artifact identities are:

```text
JSON                       2453124 bytes / d3ba265fb42dbf33e1e71ad972a85409386a2537160d7be5c09afc6e5d7d0f47
Markdown                      2652 bytes / f693f9079409fc71cb5cc8ac609d0fde47b517161162f0e7baf95cabf58c522f
summary                                  / 68a169c60dc25eda886df608560f1698eb5e09f05ed2563f2aef622b49ae3df3
rows                                     / f53d6a1d2d74cca3510ca1495814baa096ef4b1e114f22c7797a3cf3aab4ee72
aggregates                               / 6befa920087340f33d69ac8912cf4c5e129980b5f2e6a2087e022e01e1a8e531
manifest                                 / 343746ea65d6649726e116e529c8a0e83d07f7c8d72e76c2074e21f24941304b
dependency                               / c3ca2a00d1729b003a6ac12ba73853cb3d1c86710d0fa29b4aee61e55c19179f
freeze                                   / 105a0076aaedef34c06f00b1ce43b351a74f07a364e5f23b2e72e41646e09b52
outcome-free validation                  / 06c00f7f46e8d33ec6792eb8d5d06ff259b376b0e781d7d74f9968b6b54fde9d
historical implementation                / 72e545afd77900b14107f93ece3b95f0289a9cd3ea1504321b2a5fd7da1813ff
current implementation                   / 41937256d429feba4898f23f841415a983335e23ace54133cf0be234475ad2a8
domain manifest LF             33448 bytes / 16bb5876d857e74fd4a8f63f43ab701a60fab018a2c9969d889b11d085227316
```

The artifact's historical map is not rebound by the reviewed implementation/test correction. Portable identity uses LF-canonical bytes; raw identity detects drift only within one checkout and run. The complete contract and safe commands are in [`docs/p2h_result_interpretation.md`](p2h_result_interpretation.md#reproduction-and-verification).

Run two P2h audits into distinct ignored workspace-local directories:

```bash
python -B -m bug_cause_inference.p2h.task_scheduler_replication --output-dir tmp/p2h-closeout-fresh-a
python -B -m bug_cause_inference.p2h.task_scheduler_replication --output-dir tmp/p2h-closeout-fresh-b
```

Compare both serialized pairs with the tracked files byte-for-byte and semantically. Required checks are:

- exact ordered support of 15 inputs / 6 policies / 90 normal-execution rows;
- 25-oracle baseline, exact input-specific failure sets, and clean passes `5/5` at `25/25` each;
- exact action costs, settings, selector boundary, decision/action/observation/update semantics, and terminal partition;
- bug discovery `12/60`, first failure `12/60`, clean false positives `0/30`, location top-1/top-3 `25/60` and `35/60`, cause/fix `16/60` each;
- truthful scheduler-local recent-diff and coverage observations;
- summary, row, aggregate, manifest, dependency, freeze, and outcome-free-validation digests match exactly;
- artifact historical 28-file identity remains unchanged while the current 28-file map is checked separately;
- raw implementation and dependency snapshots remain identical before/after each run;
- accepted P1b–P2g source, tests, artifacts, identities, results, and public claims remain unchanged.

Do not overwrite or regenerate the tracked P2h artifacts during verification. Do not run the P2a or P2b outcome runners. P2h fresh replay is fixed-input verification only and must not be followed by input, oracle, action, cost, setting, policy, metric, denominator, result, or claim tuning.

The 2026-07-20 documentation-closeout checkpoint passed P2h targeted `30` tests in `18.22s`, the P1b–P2h relevant regression `1014` tests in `278.67s`, the full repository suite `2150` tests in `378.59s`, P1b real-diff validation `25/25`, and two isolated exact fresh P2h artifact runs. Both authoritative fresh runs preserved all 32 raw implementation/dependency paths and matched the tracked JSON/Markdown bytes, validated semantics, seven result/contract digests, historical 28-file identity, accepted current 28-file identity, 25-oracle gate, and 90-row support. These are verification results, not new outcome evidence.

## `tmp_path` Tests

CLI/file-output tests and P1b real-diff generation tests use pytest's `tmp_path` fixture intentionally. These tests verify that output paths, nested parent creation, generated checkout trees, and validation work roots behave correctly without writing into committed example or artifact directories.

Do not replace these tests with fixed repository paths, skips, or xfails to work around local temporary-directory permission failures.

## Codex Sandbox Temp Constraint

Some Codex sandbox runs on Windows have failed while pytest was creating or cleaning the user temp root, for example:

```text
PermissionError: C:\Users\gurig\AppData\Local\Temp\pytest-of-gurig
```

Treat this as a local execution-environment constraint when the same pytest command passes with normal permissions.

Operational rule:

- Do not change production code, pytest configuration, CI, or `tmp_path` tests to work around the sandbox Temp permission failure.
- Rerun the same pytest command with normal permissions or explicit approval.
- If normal Temp remains inaccessible, create the ignored parent `tmp/pytest/` if needed and rerun the unchanged command with a unique workspace-local base such as `--basetemp tmp/pytest/<unique-run-id>`. Use a fresh path for each rerun and record the original Temp failure separately from the fallback result.
- Record both the sandbox failure and the normal-permission rerun result.
- If the same command fails with normal permissions, treat it as a repository or test failure and investigate normally.

## Ruff Result Separation

Run narrow lint checks against changed supported files and run `python -m ruff check .` as a separate repository-wide check. Markdown paths may be unsupported or outside the configured Ruff file set; an unsupported Markdown invocation is not a passed Python changed-file lint check.

The accepted P1d3b baseline recorded three pre-existing repository-wide `F401` failures. Reconfirm and report them separately from any new failure. This baseline is not permission to suppress, expand, or ignore lint debt, and documentation-only work must not edit unrelated prior-phase Python files merely to make the repository-wide command green.
