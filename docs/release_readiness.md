# Release Readiness Notes

Status: public-release hygiene checklist for the current repository state. This note does not change runtime behavior, test scope, metrics, policies, action costs, datasets, real-diff artifacts, CI coverage, or report semantics.

## Public Boundary

The repository is ready to be reviewed as a small reproducible prototype when the public wording keeps these boundaries:

- P1a is a synthetic Bayesian active bug-cause investigation prototype.
- P1b is a small injected checkout/pricing benchmark scaffold with function-level location metrics.
- P1b real-diff artifacts are clean baseline source plus per-variant unified patches, not real repository histories.
- P1c is analysis-only robustness reporting over the existing P1b scaffold.
- The project does not claim production fault localization, automated repair, LLM agent benchmarking, real-world debugging accuracy, a minimax-optimal policy, or a formal game-theoretic guarantee.

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

Use `tmp/` or `temp/` for local scratch output when possible. Generated checkout trees from `bug_cause_inference.p1b.real_diff` should remain temporary or live under an ignored scratch directory.

## CI And Verification

GitHub Actions is expected to install `requirements.txt` plus the editable package, run the full pytest suite, and validate the P1b real-diff artifacts. Do not weaken CI or skip `tmp_path` tests to work around local sandbox issues.

Recommended pre-release checks:

```bash
python -B -m pytest -q -p no:cacheprovider
python -m bug_cause_inference.p1b.real_diff --validate
python -m bug_cause_inference.cli p1b-evaluate --observation-mode both --format markdown
python -m bug_cause_inference.cli p1c-evaluate --format markdown
git diff --check
git status -sb
```

If a Codex sandbox run hits the known Windows Temp-directory permission issue for pytest `tmp_path` tests, rerun the same command with normal permissions or explicit approval and record both results. Do not change production code, pytest configuration, CI, or test coverage for that local constraint.

## Current Constraints

- P1c9 does not require an immediate follow-up based on the current interpretation note.
- A combined cost plus dropout/delay interaction remains a plausible future design-review topic, not a current implementation target.
- Public release preparation should not modify P1b/P1c runtime behavior, metric semantics, policy thresholds, dataset metadata, or real-diff artifacts.
- Public documentation should keep limitations and non-claims visible rather than broadening README claims.
