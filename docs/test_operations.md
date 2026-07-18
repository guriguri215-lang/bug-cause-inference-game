# Test Operations

Status: operational guidance for local verification and CI. This document does not change runtime behavior, test scope, metrics, policies, action costs, datasets, or report semantics.

## Scope

Use this note to keep evaluation and test runs consistent across local development, Codex sessions, and CI.

This note does not:

- skip, xfail, or narrow CLI/file-output tests that use `tmp_path`;
- hardcode user-specific temporary directories;
- weaken GitHub Actions verification;
- change P1b or P1c runtime behavior, metrics, policies, thresholds, scores, datasets, real-diff artifacts, or observation semantics.
- change accepted P2a/P2b/P2c inputs, artifacts, results, catalog cases, action costs, settings, or policy outcomes.

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

The full suite includes P2b and P2c. On Linux, the tracked LF artifacts and accepted identities must match the same portable LF-canonical hashes used on Windows. A platform-specific raw working-tree hash is not an accepted portable artifact identity.

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
