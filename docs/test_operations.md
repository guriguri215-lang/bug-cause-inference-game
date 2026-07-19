# Test Operations

Status: operational guidance for local verification and CI. This document does not change runtime behavior, test scope, metrics, policies, action costs, datasets, or report semantics.

## Scope

Use this note to keep evaluation and test runs consistent across local development, Codex sessions, and CI.

This note does not:

- skip, xfail, or narrow CLI/file-output tests that use `tmp_path`;
- hardcode user-specific temporary directories;
- weaken GitHub Actions verification;
- change P1b or P1c runtime behavior, metrics, policies, thresholds, scores, datasets, real-diff artifacts, or observation semantics.
- change accepted P2a/P2b/P2c/P2d/P2e inputs, artifacts, results, catalog cases, action costs, settings, policy outcomes, or intervention semantics.

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

Relevant P2a/P2b/P2c/P2d/P2e regression for the complete accepted-input boundary:

```bash
python -B -m pytest tests/test_p2a_adequacy.py tests/test_p2a_candidate_oracles.py tests/test_p2a_candidates.py tests/test_p2a_compatibility.py tests/test_p2a_evaluation.py tests/test_p2a_execution.py tests/test_p2a_freeze.py tests/test_p2a_freeze_realization.py tests/test_p2a_reports.py tests/test_p2b_reports.py tests/test_p2b_solvability_ceiling.py tests/test_p2c_reports.py tests/test_p2c_trajectory_audit.py tests/test_p2d_reports.py tests/test_p2d_stop_relaxation_audit.py tests/test_p2e_continuation_audit.py tests/test_p2e_reports.py -q -p no:cacheprovider
```

This regression covers the P2a candidate, compatibility, execution, freeze, evaluation, and report layers plus the P2b, P2c, P2d, and P2e diagnostics. P2e closeout uses it as read-only non-regression evidence; it does not invoke the P2a or P2b outcome runners.

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

The full suite includes P2b, P2c, P2d, and P2e. On Linux, the tracked LF artifacts and accepted identities must match the same portable LF-canonical hashes used on Windows. A platform-specific raw working-tree hash is not an accepted portable artifact identity.

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
