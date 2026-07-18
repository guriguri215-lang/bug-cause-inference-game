# Test Operations

Status: operational guidance for local verification and CI. This document does not change runtime behavior, test scope, metrics, policies, action costs, datasets, or report semantics.

## Scope

Use this note to keep evaluation and test runs consistent across local development, Codex sessions, and CI.

This note does not:

- skip, xfail, or narrow CLI/file-output tests that use `tmp_path`;
- hardcode user-specific temporary directories;
- weaken GitHub Actions verification;
- change P1b or P1c runtime behavior, metrics, policies, thresholds, scores, datasets, real-diff artifacts, or observation semantics.
- change accepted P2a/P2b inputs, artifacts, results, catalog cases, action costs, settings, or policy outcomes.

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

The full suite includes P2b. On Linux, the tracked LF artifacts and accepted identities must match the same portable LF-canonical hashes used on Windows. A platform-specific raw working-tree hash is not an accepted portable artifact identity.

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
