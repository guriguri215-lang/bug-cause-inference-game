# Release Readiness Notes

Status: public-release hygiene checklist for the current repository state. This note does not change runtime behavior, test scope, metrics, policies, action costs, datasets, real-diff artifacts, CI coverage, or report semantics.

## Public Boundary

The repository is ready to be reviewed as a small reproducible prototype when the public wording keeps these boundaries:

- P1a is a synthetic Bayesian active bug-cause investigation prototype.
- P1b is a small injected checkout/pricing benchmark scaffold with function-level location metrics.
- P1b real-diff artifacts are clean baseline source plus per-variant unified patches, not real repository histories.
- P1c is analysis-only robustness reporting over the existing P1b scaffold.
- P1d1, P1d2, P1d3a, and P1d3b are dedicated analysis-only reports and CLI commands over the same fixed scaffold.
- P1d3a cost-profile matrices and P1d3b dropout/delay-profile matrices are separate retrospective families. They do not define a combined interaction, joint profile-by-bucket game, or cross-profile winner or ranking.
- The project does not claim production fault localization, automated repair, LLM agent benchmarking, real-world debugging accuracy, general minimax optimality, a general Nash equilibrium, regret optimality, or a game-theoretic guarantee beyond each explicitly fixed empirical matrix.

## Tracked Public Artifacts

The tracked generated artifacts are intentionally small and reproducible:

- `examples/cases/synthetic_cases.json`
- `examples/reports/*.json` and `examples/reports/*.md`
- `examples/p1b/variants/*.json` and `examples/p1b/variants/*.md`
- `examples/p1b/reports/*.json` and `examples/p1b/reports/*.md`
- `src/bug_cause_inference/p1b/artifacts/real_diff/manifest.json`
- `src/bug_cause_inference/p1b/artifacts/real_diff/baseline/checkout/*.py`
- `src/bug_cause_inference/p1b/artifacts/real_diff/patches/*.patch`

These artifacts should not contain private project data, local filesystem paths, credentials, generated full checkout trees, or large benchmark outputs.

## Local Outputs

Local outputs should stay out of commits unless they are deliberately refreshed as curated examples:

- virtual environments and package build output;
- pytest, Python, mypy, ruff, and coverage caches;
- temporary validation work roots;
- generated real-diff checkout trees;
- ad hoc CLI output files created during investigation.
- P1d JSON/Markdown reports created for local review or smoke testing; these are ignored/local outputs, not required tracked release artifacts.

Use `tmp/` or `temp/` for local scratch output when possible. Generated checkout trees from `bug_cause_inference.p1b.real_diff` should remain temporary or live under an ignored scratch directory.

## CI And Verification

GitHub Actions is expected to install `requirements.txt` plus the editable package, run the full pytest suite, and validate the P1b real-diff artifacts. Do not weaken CI or skip `tmp_path` tests to work around local sandbox issues.

Recommended pre-release checks:

```bash
python -B -m pytest -q -p no:cacheprovider
python -m bug_cause_inference.p1b.real_diff --validate
python -m bug_cause_inference.cli p1b-evaluate --observation-mode both --format markdown
python -m bug_cause_inference.cli p1c-evaluate --format markdown
python -m bug_cause_inference.cli p1d1-report --format json
python -m bug_cause_inference.cli p1d1-report --format markdown
python -m bug_cause_inference.cli p1d2-report --format json
python -m bug_cause_inference.cli p1d2-report --format markdown
python -m bug_cause_inference.cli p1d3a-report --format json
python -m bug_cause_inference.cli p1d3a-report --format markdown
python -m bug_cause_inference.cli p1d3b-report --format json
python -m bug_cause_inference.cli p1d3b-report --format markdown
git diff --check
git status -sb
```

Before a public release, complete the full test and real-diff checks above, exercise all four P1d CLI commands in both formats, and complete the package-artifact checks below. A documentation closeout or a previously reviewed local report hash does not replace those release-time checks.

If a Codex sandbox run hits the known Windows Temp-directory permission issue for pytest `tmp_path` tests, rerun the same command with normal permissions or explicit approval and record both results. Do not change production code, pytest configuration, CI, or test coverage for that local constraint.

## Package Artifact Smoke

For a local release-artifact boundary check, build outputs should stay under ignored paths:

```bash
python -m pip wheel . --no-deps -w tmp/wheelhouse
python -m build --sdist --wheel --outdir tmp/dist
```

If a no-isolation build fails because the active environment cannot import `setuptools.build_meta`, treat that as a local build-tool constraint. Do not add build backends or build frontends to runtime requirements only for this smoke; use build isolation or a temporary build environment instead.

Before publishing or tagging, inspect the built wheel and verify that it:

- includes `bug_cause_inference/p1b/artifacts/real_diff/manifest.json`;
- includes the six baseline checkout Python files under `bug_cause_inference/p1b/artifacts/real_diff/baseline/checkout/`;
- includes the 25 real-diff patch files under `bug_cause_inference/p1b/artifacts/real_diff/patches/`;
- excludes generated checkout trees, `tmp/`, `temp/`, `.venv/`, pytest caches, local outputs, `examples/`, and `tests/`.

Also confirm that package metadata builds without setuptools license deprecation warnings: `pyproject.toml` should use the SPDX license expression `MIT`, include `LICENSE` as a license file, and avoid deprecated license classifiers.

The source distribution may include source and test files, but it should still exclude local scratch output, generated checkout trees, virtual environments, and build/cache directories.

Install the wheel into a temporary environment under `tmp/` and run at least:

```bash
python -m bug_cause_inference.cli --help
python -m bug_cause_inference.p1b.real_diff --validate
```

## Current Constraints

- P1c9 does not require an immediate follow-up based on the current interpretation note.
- A combined cost plus dropout/delay interaction remains a plausible future design-review topic, not a current implementation target.
- P1d3a and P1d3b release wording must preserve their separate-family boundary and their retrospective, fixed-scaffold, non-causal, and non-generalization limitations.
- Local reviewed P1d report files and hashes are not tracked-artifact requirements; source, serializers, tests, and reproducible CLI behavior are the release boundary.
- Public release preparation should not modify P1b/P1c runtime behavior, metric semantics, policy thresholds, dataset metadata, or real-diff artifacts.
- Public documentation should keep limitations and non-claims visible rather than broadening README claims.
