# P2g Result Interpretation

## Question and Frozen Inputs

P2g answers one fixed-input descriptive question:

> On the exact five accepted P2a frozen benign non-empty-diff clean inputs, for each of the six accepted formal policies, how does the accepted normal execution compare with a paired execution that suppresses only `no_bug_probability_threshold` at every pre-action decision while retaining the same starting state, RNG, execution context, policy, actions, costs, observations, budget, maximum step count, update semantics, and residual stop precedence?

The inputs are exactly `P2A-CLEAN-001` through `P2A-CLEAN-005` in accepted order. They are the five previously frozen P2a clean-stress patches; P2g does not author, add, remove, replace, or reclassify an input.

| Input | Clean family | Changed path | Changed function | Patch SHA-256 |
|---|---|---|---|---|
| `P2A-CLEAN-001` | `boundary_adjacent_valid_behavior` | `checkout/cart.py` | `cart.validate_item` | `c0a1b7d75e313d91ec0653ddd361f926e1f69ad5025e78878e80aa114c8e3caa` |
| `P2A-CLEAN-002` | `optional_input_valid_absence` | `checkout/config.py` | `config.get_region_aliases` | `ef17bf8a5eb330d52e7ef9b122c4b574b01141bf23d15b6bc90fefa25ddd39f1` |
| `P2A-CLEAN-003` | `config_equivalent_normalization` | `checkout/config.py` | `config.get_tax_rate` | `2ab2975d1537a7ea841ca2744515020f12d914b8a88668c967bcd664d64adea9` |
| `P2A-CLEAN-004` | `valid_state_sequence` | `checkout/discounts.py` | `discounts.apply_coupon` | `eb614f960d83f19a7ddccfc4f7162397f008c42dd2e2089cb3c09753c468b65d` |
| `P2A-CLEAN-005` | `nonintuitive_spec_conformance` | `checkout/discounts.py` | `discounts.apply_bogo_discount` | `b78e400beeffcd5a9a9c84bf39c25f3b67a4b2c03eb41605700806b9331c8778` |

Their accepted LF-canonical post-image SHA-256 values, in the same order, are:

```text
240ca5bf56ca093dbd173a8acf0538f00458e0cc2628acaeddb1ace0c57681d1
8f01cb00755d44a5b1b787ae1d268017bce5f8adb7aa2f55bead1e0f68918bd4
be83ce7d182e509888d0807865d8de1f9d6b7279c750f0d6ca83f25413e51780
9b22eccc0e2a838f38b43fee861bbf0d6ab2cb6d6f8121c62cb53009fe1a6046
7c6b8442c9b7d2484f36806993541f48a6448bb29d3c03d5faad888911796804
```

The input-specific clean-validity gate runs 14 accepted oracles across the five patched checkouts and requires `14/14` passes before any policy trajectory. The hidden clean label and oracle results are not policy-visible inputs.

The six policies remain in accepted formal order:

1. `fixed_checklist`
2. `test_first`
3. `coverage_first`
4. `recent_diff_first`
5. `cause_only_p1a_style`
6. `expected_utility_per_cost`

Each input-policy combination has two arms in fixed order: `normal_control` and `target_suppressed_continuation`. Canonical row order is input-major, policy-major, arm-minor. Complete support is 5 inputs, 6 policies, 2 arms, 60 ordered trajectories, and 30 pairs.

The five inputs are hand-authored, same-domain, fixed, and non-iid. The 30 pairs cross those inputs with six policies; they are not 30 independent programs, replicates, or a population sample.

P2g is analysis-only, fixed-input, same-domain, hand-authored, model-internal, paired, non-causal, and non-deployable.

## Paired Execution Contract

Both arms start independently from the same posterior state, RNG state, execution context, settings, catalog, policy identity, and freshly materialized accepted patch. Starting-checkpoint agreement is `30/30`. Normal-control behavior exactly replays the accepted P2a clean outcome for all `30/30` input-policy pairs.

Until the control reaches its terminal target predicate, both arms have exact decision, action, observation, cost, state, RNG, and execution-context prefix agreement; prefix agreement is `30/30`.

The control uses the accepted normal stop/action/update loop. At every pre-action decision, the intervention evaluates but suppresses only `no_bug_probability_threshold`. It retains the accepted residual precedence:

1. `bug_confidence_threshold`
2. `budget_limit`
3. `max_steps`
4. `low_expected_utility`

If a residual stop fires, no action is selected. Otherwise the same frozen policy receives the same policy-visible state, remaining budget, and RNG. Observations, action costs, budget 12, maximum step count 6, update semantics, and the finite non-repeating action catalog remain unchanged. Every later true firing of the target predicate is suppressed and recorded; no non-target predicate is suppressed.

The pair is a deterministic model-internal contrast. It is not randomized or otherwise identified as a causal effect.

## Distinct Axes and Definitions

P2g keeps these axes separate:

- **Terminal reason:** one exclusive terminal from no-bug probability, bug confidence, budget, maximum steps, low utility, or no available actions.
- **False positive:** terminal `bug_confidence_threshold` or final bug-presence posterior at least `0.75`.
- **Execution failure observed:** any executed frozen catalog test or oracle failed.
- **Bug-detected observation:** any accepted observation recorded `bug_detected=true`.
- **Target suppression:** a true target predicate omitted at one intervention decision.
- **Truthful benign diff:** the observation exactly preserves the accepted repository-relative patch path, changed file, changed function, and non-empty excerpt.
- **Action and cost:** ordered selected actions, action count, and cumulative investigation cost.

A budget, maximum-step, or no-available-actions terminal is not a false positive by definition. Zero execution failures and zero bug-detected observations do not by themselves define the false-positive result. Terminal, false-positive, execution-failure, bug-detected, action/cost, suppression, and diff-evidence denominators must not be merged.

## Exact Result

```text
clean validity gate                         14 / 14
ordered trajectories / pairs                60 / 30
normal-control replay                       30 / 30
pair start / prefix agreement               30 / 30; 30 / 30

normal control
  no_bug_probability_threshold terminals    30 / 30 trajectories
  false positives                            0 / 30 trajectories
  execution failures                         0 / 30 trajectories
  bug-detected observations                  0 / 30 trajectories

target-suppressed continuation
  budget_limit terminals                    20 / 30 trajectories
  max_steps terminals                        5 / 30 trajectories
  no_available_actions terminals             5 / 30 trajectories
  false positives                            0 / 30 trajectories
  execution failures                         0 / 30 trajectories
  bug-detected observations                  0 / 30 trajectories

pair false-positive deltas                  all 30 are 0
intervention action counts                  20 at 5 actions / 10 at 6 actions
intervention cumulative costs                5 at 10 / 5 at 11 / 20 at 12
intervention suppression counts             25 at 4 / 5 at 5
truthful benign-diff observations           20 / 20 exact
```

The intervention terminal partition is exclusive and complete: `20 + 5 + 5 = 30`. All 30 paired false-positive deltas are zero, but that is only an exact observation over the fixed 30 input-policy pairs.

The normal controls take two actions in 25 trajectories and three actions in 5 trajectories. Their cumulative costs are 10 at cost 2, 15 at cost 3, and 5 at cost 5. These are separate descriptive execution distributions, not utility or payoff values.

## Truthful Benign-Diff Boundary

Every `inspect_recent_diff` observation uses `evidence_source=p2g_accepted_p2a_patch_identity`. It records only the accepted repository-relative patch path, exact changed path/function, and non-empty portable patch excerpt. All `20/20` executed recent-diff observations have exact path/function/excerpt agreement.

P2g does not use P2f's empty-diff sentinel, generate a local checkout path, expose an absolute/private path, or make the clean label, oracle result, or hidden ground truth policy-visible. P2f's truthful no-patch evidence and P2g's truthful accepted non-empty patch evidence are separate contracts.

## Interpretation Boundary

The `0/30` control and `0/30` intervention false positives are arm-specific fixed-support fractions over five hand-authored inputs crossed with six policies. They are not population clean-safety rates, independent program replication, unseen-clean results, confidence intervals, or external-validity claims.

Repeated target-only suppression does not prove that the target threshold caused an outcome or that the threshold is defective. The result does not establish a policy defect, policy improvement, ranking, deployable recommendation, or production usefulness. Budget, maximum-step, and no-available-actions labels are not causal explanations.

P2e, P2f, and P2g answer different questions. P2e is a bounded buggy-side continuation, P2f is a paired no-diff clean observation on one exact unpatched program, and P2g is a paired benign-diff clean observation over five accepted patches. Their outcomes are not combined into a payoff, utility, weighted loss, benefit-cost score, tradeoff optimum, or causal effect. No new or tuned policy, optimized sequence, branch search, or dynamic-programming result is evaluated here.

## Versioned Artifacts and Digests

The tracked artifacts contain the same validated summary:

- [Versioned JSON artifact](../src/bug_cause_inference/p2g/artifacts/p2g_accepted_benign_diff_clean_paired_continuation_audit_v1.json) — 3,370,390 bytes; SHA-256 `b37a6d3af44714d5cd2dcb0bc6afd4b93b43898bbdd9d75d747f8a6125a48ab0`.
- [Versioned Markdown artifact](../src/bug_cause_inference/p2g/artifacts/p2g_accepted_benign_diff_clean_paired_continuation_audit_v1.md) — 3,371,629 bytes; SHA-256 `a01cfac29acb9a43afec7b1764ff8d926cc654327dd0e6eb95266afa58c367ec`.

```text
input-contract digest          ca53689e46ea7b12cbb7c42e199bfef487bf82058303cdc1024634dc1b6cc387
dependency-contract digest     c6c2576d575e14e1e4358bfb96df3c33b3ffa01c0edd46748793b427259c07e5
canonical summary digest       1eb05962a96a3783484c0ef77e7b2fccd9f223d9663cb08a42d6787c3d1e3e2b
trajectory-results digest      3d7079c77a9d9d3598172d3938356b3c83367311acdde5faef386636407bf1a2
pair-results digest            8bec24f367f498cbe5d6cc6f8c81539fdf2a34fafa82dc49e300abf9de23ae26
aggregate-results digest       22062f67d818ef26b5f9641f36ac3cb9a526b7dee3a57a6d934f7364dd1edd0c
```

The dependency contract rehashes the accepted P1b–P2f input boundary used by P2g. A mismatch is invalidity, not a new P2g outcome.

## Historical and Final Implementation Identity

The artifact preserves the historical five-file identity frozen before the first valid outcome:

```text
src/bug_cause_inference/p2g/__init__.py                         cd9678425da62a0e2d9db430479569640a0ab4bf58ffae7f513c48381cb8cbcd
src/bug_cause_inference/p2g/benign_diff_clean_audit.py          5fcd01726d67f4518d61690dc5383a5456cd06cf2cec69aa1c6a2fff7c7a6fb9
src/bug_cause_inference/p2g/reports.py                          b4c29bba4859868ac60dfed044ba90424daa8498e2a1249d542ddce6afac0001
tests/test_p2g_benign_diff_clean_audit.py                       681bfe12886745df3b5e85ad676f1f1b72cb6f5224589f7355fcfcdb4887575a
tests/test_p2g_reports.py                                       0c05ca91ab2b94bb3f0060d8147b6a5ea690e1a8f16c1e6f7deb032faf5e16be
```

The final merged current LF-canonical identities are a separate gate:

```text
src/bug_cause_inference/p2g/__init__.py                    64 / cd9678425da62a0e2d9db430479569640a0ab4bf58ffae7f513c48381cb8cbcd
src/bug_cause_inference/p2g/benign_diff_clean_audit.py   61100 / c700a7ac5515d9c83874d88b5b071846fed7f97e567c8c06fdb0ff1c74116d11
src/bug_cause_inference/p2g/reports.py                    4030 / b4c29bba4859868ac60dfed044ba90424daa8498e2a1249d542ddce6afac0001
tests/test_p2g_benign_diff_clean_audit.py                11136 / 4746ac55aaf1bece7d5eaf79d3c6c2a1aa8869eaeff6adcf72be9805a295ff3b
tests/test_p2g_reports.py                                 3400 / 0c05ca91ab2b94bb3f0060d8147b6a5ea690e1a8f16c1e6f7deb032faf5e16be
```

Portable identity normalizes CRLF and CR line endings to LF. Exact raw working-tree snapshots separately detect same-run drift within one checkout; raw constants are not cross-platform accepted identities.

The reviewed correction history is part of the provenance:

1. The first attempt mislabeled Windows raw CRLF post-image hashes as LF-canonical identities. It failed closed before any policy trajectory, pair, or artifact existed. The same specification reviewer recomputed and accepted all five LF-canonical post-image hashes before the first valid outcome.
2. Independent implementation review added full decision replay for available actions, scores, target-only repeated suppression and indices, stop precedence, policy selection, and state/RNG/context projection.
3. The same reviewer then required exact clean-validity and observation-schema validation for five inputs, 14 ordered oracle IDs, `14/14` passes, and patched-checkout digests.
4. The same reviewer accepted both corrective slices with unresolved High/Medium/Low `0/0/0`.

These corrections changed no artifact byte, input, policy, arm, trajectory, pair, terminal, metric, denominator, descriptive result, or claim boundary. Current identities must not overwrite or rebind the historical freeze.

## Reproduction and Verification

P2g has no public CLI command. Use short, unused workspace-local pytest base directories and do not run the P2a or P2b outcome runners:

```bash
python -B -m pytest tests/test_p2g_benign_diff_clean_audit.py tests/test_p2g_reports.py -q -p no:cacheprovider --basetemp tmp/pg-t-001
python -B -m pytest tests/test_p2a_adequacy.py tests/test_p2a_candidate_oracles.py tests/test_p2a_candidates.py tests/test_p2a_compatibility.py tests/test_p2a_evaluation.py tests/test_p2a_execution.py tests/test_p2a_freeze.py tests/test_p2a_freeze_realization.py tests/test_p2a_reports.py tests/test_p2b_reports.py tests/test_p2b_solvability_ceiling.py tests/test_p2c_reports.py tests/test_p2c_trajectory_audit.py tests/test_p2d_reports.py tests/test_p2d_stop_relaxation_audit.py tests/test_p2e_continuation_audit.py tests/test_p2e_reports.py tests/test_p2f_no_diff_clean_audit.py tests/test_p2f_reports.py tests/test_p2g_benign_diff_clean_audit.py tests/test_p2g_reports.py -q -p no:cacheprovider --basetemp tmp/pg-r-001
python -B -m pytest -q -p no:cacheprovider --basetemp tmp/pg-f-001
python -m bug_cause_inference.p1b.real_diff --validate
```

For two isolated fresh P2g runs, use distinct ignored output/work directories and compare both pairs with the tracked artifacts:

```python
import hashlib
import json
from pathlib import Path

from bug_cause_inference.p2g import benign_diff_clean_audit as audit
from bug_cause_inference.p2g import reports

root = Path.cwd()
tracked_json = root / "src/bug_cause_inference/p2g/artifacts/p2g_accepted_benign_diff_clean_paired_continuation_audit_v1.json"
tracked_md = root / "src/bug_cause_inference/p2g/artifacts/p2g_accepted_benign_diff_clean_paired_continuation_audit_v1.md"
accepted_current_lf = {
    "src/bug_cause_inference/p2g/__init__.py": "cd9678425da62a0e2d9db430479569640a0ab4bf58ffae7f513c48381cb8cbcd",
    "src/bug_cause_inference/p2g/benign_diff_clean_audit.py": "c700a7ac5515d9c83874d88b5b071846fed7f97e567c8c06fdb0ff1c74116d11",
    "src/bug_cause_inference/p2g/reports.py": "b4c29bba4859868ac60dfed044ba90424daa8498e2a1249d542ddce6afac0001",
    "tests/test_p2g_benign_diff_clean_audit.py": "4746ac55aaf1bece7d5eaf79d3c6c2a1aa8869eaeff6adcf72be9805a295ff3b",
    "tests/test_p2g_reports.py": "0c05ca91ab2b94bb3f0060d8147b6a5ea690e1a8f16c1e6f7deb032faf5e16be",
}

def lf_sha256(path):
    raw = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(raw).hexdigest()

assert {path: lf_sha256(root / path) for path in accepted_current_lf} == accepted_current_lf

for label in ("a", "b"):
    out = root / f"tmp/p2g-closeout-fresh-{label}"
    raw_before = {
        path: hashlib.sha256((root / path).read_bytes()).hexdigest()
        for path in accepted_current_lf
    }
    dependency_before = audit._raw_dependency_snapshot()
    summary = audit.run_benign_diff_clean_audit(
        expected_implementation_identity=accepted_current_lf,
        work_root=out / "work",
    )
    reports.save_p2g_report(
        summary,
        json_path=out / "audit.json",
        markdown_path=out / "audit.md",
    )
    assert raw_before == {
        path: hashlib.sha256((root / path).read_bytes()).hexdigest()
        for path in accepted_current_lf
    }
    assert dependency_before == audit._raw_dependency_snapshot()
    assert out.joinpath("audit.json").read_bytes() == tracked_json.read_bytes()
    assert out.joinpath("audit.md").read_bytes() == tracked_md.read_bytes()

summary = audit.validate_audit_summary(json.loads(tracked_json.read_text(encoding="utf-8")))
assert reports.summary_from_markdown(tracked_md.read_text(encoding="utf-8")) == summary
assert summary["aggregate_results"]["digests"] == {
    "aggregate_results_digest": "22062f67d818ef26b5f9641f36ac3cb9a526b7dee3a57a6d934f7364dd1edd0c",
    "canonical_summary_digest": "1eb05962a96a3783484c0ef77e7b2fccd9f223d9663cb08a42d6787c3d1e3e2b",
    "dependency_contract_digest": "c6c2576d575e14e1e4358bfb96df3c33b3ffa01c0edd46748793b427259c07e5",
    "input_contract_digest": "ca53689e46ea7b12cbb7c42e199bfef487bf82058303cdc1024634dc1b6cc387",
    "pair_results_digest": "8bec24f367f498cbe5d6cc6f8c81539fdf2a34fafa82dc49e300abf9de23ae26",
    "trajectory_results_digest": "3d7079c77a9d9d3598172d3938356b3c83367311acdde5faef386636407bf1a2",
}
assert summary["pre_outcome_freeze"]["implementation_file_sha256_lf"] == audit.HISTORICAL_FIRST_OUTCOME_IMPLEMENTATION_IDENTITY
assert audit.implementation_identity() == accepted_current_lf
```

Use new short suffixes when the example paths already exist. Never redirect fresh output onto the tracked JSON or Markdown path. A fixed-input P2g fresh replay is verification only and must not be followed by support, result, threshold, policy, arm, denominator, or claim tuning.

## Acceptance and Provenance

The controlling implementation was merged by [PR #38](https://github.com/guriguri215-lang/bug-cause-inference-game/pull/38):

```text
final accepted head   c1053d1f8e7974c086a15b6431c9b79e2bb7cecf
merge commit          ee1dbd8223bdffb38c43e7f40e152f0ed7dc8cc1
accepted/merge tree   200e296329b0dabe885544734a0299f6b6d56b64
PR CI                 29683876292 (run #75, success)
post-merge main CI    29684215286 (run #76, success)
```

Acceptance decisions remain separate:

- P2g software conformance final audit: accepted after independent final merged-tree review.
- P2g versioned artifact identity: accepted.
- P2g descriptive result: accepted only for the exact fixed-input observations above.
- P2g public documentation: accepted after independent documentation review, required verification, and same-reviewer status-closure re-review.

The artifact remains non-self-accepting. External acceptance and review records provide these decisions.

The current documentation-closeout verification passed with P2g targeted `33` tests, the P2a–P2g relevant regression `802` tests, the full repository suite `2120` tests, P1b real-diff validation `25/25`, and two isolated P2g fresh runs reproducing both tracked artifact files byte-for-byte and semantically. The fresh runs also preserved the raw implementation/dependency snapshots and matched all six digests and both historical/current identity gates.

## Limitations and Deferred Questions

- Only five accepted hand-authored same-domain benign-diff clean inputs are observed; there are no independent program replicates.
- The six-policy arm fractions are not population clean-safety or false-positive rates.
- The intervention is model-internal and non-causal, not a deployable policy.
- No P2e/P2f/P2g combined payoff, utility, weighted loss, tradeoff optimum, threshold recommendation, or policy ranking is defined.
- Unseen or additional clean inputs, a second domain, inference, new or tuned policies, optimized sequence/DP work, and production readiness require separate pre-outcome specifications and reviews.
