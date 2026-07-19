# P2f Result Interpretation

## Question and Frozen Inputs

P2f answers one fixed-input descriptive question:

> On one exact canonical P1b baseline with no patch, for each of the six accepted deterministic policies, how does the accepted normal execution compare with a paired execution that suppresses only `no_bug_probability_threshold` at every pre-action firing while retaining the same starting state, RNG, execution context, policy, observations, costs, budget, maximum step count, update semantics, and residual stop precedence?

The only input is `P2F-NODIFF-001`, an isolated copy of the exact unpatched `p1b_checkout_clean_v1` baseline. P2f does not create or apply an empty patch, benign patch, manifest variant, changed-file entry, changed-function entry, diff path, or diff excerpt. The baseline validity gate runs the exact accepted 29-case catalog before trajectories and requires `29/29` passes.

The six policies remain in accepted formal order:

1. `fixed_checklist`
2. `test_first`
3. `coverage_first`
4. `recent_diff_first`
5. `cause_only_p1a_style`
6. `expected_utility_per_cost`

Each policy has two arms in fixed order: `normal_control` and `target_suppressed_continuation`. The complete support is one independent program, 12 ordered trajectories, and 6 paired policy comparisons. The 12 trajectories are not 12 independent programs, replicates, or a population sample.

P2f is analysis-only, fixed-input, model-internal, paired, non-causal, and non-deployable.

## Paired Execution Contract

Both arms start from the same state, RNG state, execution context, settings, catalog, policy identity, and fresh baseline copy. Starting-checkpoint agreement is `6/6`. Until the control reaches its terminal target predicate, both arms have exact decision, action, observation, cost, state, RNG, and execution-context prefix agreement; prefix agreement is `6/6`.

The control uses the accepted normal stop/action/update loop. At every pre-action decision, the intervention evaluates but suppresses only `no_bug_probability_threshold`. It retains the accepted residual precedence:

1. `bug_confidence_threshold`
2. `budget_limit`
3. `max_steps`
4. `low_expected_utility`

If no residual stop fires, the intervention calls the same frozen policy with the same policy-visible state, remaining budget, and RNG. Observations, action costs, budget 12, maximum step count 6, update semantics, and the finite non-repeating action catalog remain unchanged. Every later firing of the target predicate is suppressed and recorded; no non-target predicate is suppressed.

The pair is a deterministic model-internal contrast. It is not randomized or otherwise identified as a causal effect.

## Distinct Axes and Definitions

P2f keeps these axes separate:

- **Terminal reason:** one exclusive terminal from no-bug probability, bug confidence, budget, maximum steps, low utility, or no available actions.
- **False positive:** terminal `bug_confidence_threshold` or final bug-presence posterior at least `0.75`.
- **Execution failure observed:** any executed canonical baseline test or oracle failed.
- **Bug-detected observation:** any accepted observation recorded `bug_detected=true`.
- **Target suppression:** a true target predicate omitted at one intervention decision.
- **Truthful recent diff:** the no-patch observation has null path, empty changed files/functions, and empty excerpt.

A budget, maximum-step, or no-available-actions terminal is not a false positive by definition. Zero execution failures and zero bug-detected observations do not by themselves define the false-positive result. These denominators must not be merged.

## Exact Result

```text
baseline validity gate                       29 / 29
ordered trajectories / pairs                 12 / 6
pair start / prefix agreement                 6 / 6

normal control
  no_bug_probability_threshold terminals      6 / 6 policies
  false positives                             0 / 6 policies
  execution failures                          0 / 6 policies
  bug-detected observations                    0 / 6 policies

target-suppressed continuation
  budget_limit terminals                       4 / 6 policies
  max_steps terminals                          1 / 6 policies
  no_available_actions terminals               1 / 6 policies
  false positives                              0 / 6 policies
  execution failures                           0 / 6 policies
  bug-detected observations                     0 / 6 policies

pair false-positive deltas                    all 6 are 0
suppression counts                            [4, 4, 4, 4, 4, 5]
truthful empty recent-diff executions          4 / 4 exact
```

The intervention terminal partition is exclusive and complete: `4 + 1 + 1 = 6`. All six paired false-positive deltas are zero, but that is only an exact observation across six frozen policies on one program.

## Truthful Empty-Diff Boundary

P2f's `inspect_recent_diff` observation describes the unpatched baseline directly. It has:

```text
diff_artifact_path   null
changed_files        []
changed_functions    []
diff_excerpt         ""
bug_detected         false
failure_found        false
no_bug_evidence      false
```

The four executions of this action have `4/4` exact empty-field agreement. `no_bug_evidence=false` preserves the accepted observation/update boundary: the hidden clean label and absence of a patch do not become a direct posterior update. P2f does not weaken P2a's non-empty-diff input validation and does not manufacture a patch to enter the P2a population.

## Interpretation Boundary

The `0/6` control and `0/6` intervention false positives are policy-support fractions for one exact program. They are not a clean safety rate, population estimate, unseen-clean result, confidence interval, or external-validity claim.

Repeated target-only suppression does not prove that the target threshold caused an outcome or that the threshold is defective. The result does not establish a policy defect, policy improvement, ranking, deployable recommendation, or production usefulness. Budget, maximum-step, and no-available-actions labels are not causal explanations.

P2e and P2f answer different questions. P2e is a bounded buggy-side continuation from accepted P2d states; P2f is a paired clean-side observation on one unpatched baseline. Their outcomes are not combined into a payoff, utility, weighted loss, benefit-cost score, or causal effect. No new or tuned policy, optimized sequence, branch search, or dynamic-programming result is evaluated here.

## Versioned Artifacts and Digests

The tracked artifacts contain the same validated summary:

- [Versioned JSON artifact](../src/bug_cause_inference/p2f/artifacts/p2f_canonical_no_diff_clean_paired_continuation_audit_v1.json) — 920,661 bytes; SHA-256 `f0ffbddb24cd500144ea0b52958b3ae51d81e2b895ff8b89faf3da504a871000`.
- [Versioned Markdown artifact](../src/bug_cause_inference/p2f/artifacts/p2f_canonical_no_diff_clean_paired_continuation_audit_v1.md) — 921,896 bytes; SHA-256 `a93019bb2422278d8efe1b9fdbb1453ba0829b6d0388ff77b172e5ca21c1410a`.

```text
65-file accepted-input contract  aca567fb7048aac2b6349a6383ec0aa601ceedde504724e4c75ddbf1e8729d0a
canonical summary digest         36d5ae198b4e9f873dedd4d13ac9ce467cde373fc8a7bf4ec6a30f32b360dfad
trajectory-results digest        13726d00369e9483e7d395aca8a282c6abd64fde017a954de44f8b32067b7c09
pair-results digest              71e3b09994cfbf46ac27ff3fc5a47d4824bbfeabc8d820fab2d821c59c7365bf
aggregate-results digest         ec03765df1854a9e78fe769e691d731754bca260c5f45434b3aa9b894dacc2c6
```

The 65-file contract rehashes the accepted P1b–P2e input boundary. A mismatch is invalidity, not a new P2f outcome.

## Historical and Final Implementation Identity

The artifact preserves the historical five-file identity frozen before the first outcome:

```text
src/bug_cause_inference/p2f/__init__.py                 f04b73866e041663a582a3447987096b8bb57ccf55eb35544ef9a3caef13de37
src/bug_cause_inference/p2f/no_diff_clean_audit.py       d9f20ce7b7160771ab24df5585b3a854f0d523decef68f58e6d7e68e609e3ddc
src/bug_cause_inference/p2f/reports.py                   aef7abf588ac1c68436a9e08cd30514474ee244069164c5ddfa998b1699836c5
tests/test_p2f_no_diff_clean_audit.py                    3958740a6beda8421caf0b02665685791ca8abf21478725d1da843a033b54a5a
tests/test_p2f_reports.py                                711160041d1f56bf514cfec2799e758694068b30aa6ec0c78a9916bcc9003f53
```

The final merged current LF-canonical identities are a separate gate:

```text
src/bug_cause_inference/p2f/__init__.py                 61 / 64149bfd7700fb03ab026d43567b223d8ff651926778f7bbc85eeb6cd44a0c3c
src/bug_cause_inference/p2f/no_diff_clean_audit.py       65333 / 66d3c70c138fe44873be5cd63140aea157f1753f681cfaa9ed7fc179b7ccf1cc
src/bug_cause_inference/p2f/reports.py                   4557 / aef7abf588ac1c68436a9e08cd30514474ee244069164c5ddfa998b1699836c5
tests/test_p2f_no_diff_clean_audit.py                    19711 / b38696946ffce342d69b8e7fe54c1c56ba37bab72a88c43f7472a4a69abb5df1
tests/test_p2f_reports.py                                4008 / 711160041d1f56bf514cfec2799e758694068b30aa6ec0c78a9916bcc9003f53
```

Portable identity normalizes CRLF and CR line endings to LF. Exact raw working-tree snapshots separately detect same-run drift within one checkout; raw constants are not cross-platform accepted identities.

The reviewed correction history is part of the provenance:

1. Canonical result digests were made independent of JSON object insertion order.
2. `selection_attempted` truth-table enforcement, independent checkpoint replay, and re-signed terminal state/RNG/context mutation closure were added.
3. CI #69 separated historical Windows CRLF `raw_size` metadata from Linux LF portable identity.
4. CI #70 used a P2f-local `math.fsum` total so Python 3.10 and 3.12 produce the same accepted posterior checkpoints.

These corrections changed no artifact byte, action, terminal, metric, support count, or claim boundary. Current identities must not overwrite or rebind the historical freeze.

## Reproduction and Verification

P2f has no public CLI command. Use a fresh workspace-local pytest base directory when needed and do not run the P2a or P2b outcome runners:

```bash
python -B -m pytest tests/test_p2f_no_diff_clean_audit.py tests/test_p2f_reports.py -q -p no:cacheprovider --basetemp tmp/pf-t-001
python -B -m pytest tests/test_p2a_adequacy.py tests/test_p2a_candidate_oracles.py tests/test_p2a_candidates.py tests/test_p2a_compatibility.py tests/test_p2a_evaluation.py tests/test_p2a_execution.py tests/test_p2a_freeze.py tests/test_p2a_freeze_realization.py tests/test_p2a_reports.py tests/test_p2b_reports.py tests/test_p2b_solvability_ceiling.py tests/test_p2c_reports.py tests/test_p2c_trajectory_audit.py tests/test_p2d_reports.py tests/test_p2d_stop_relaxation_audit.py tests/test_p2e_continuation_audit.py tests/test_p2e_reports.py tests/test_p2f_no_diff_clean_audit.py tests/test_p2f_reports.py -q -p no:cacheprovider --basetemp tmp/pf-r-001
python -B -m pytest -q -p no:cacheprovider --basetemp tmp/pf-f-001
python -m bug_cause_inference.p1b.real_diff --validate
```

For two isolated fresh P2f runs, use temporary output paths and compare both pairs with the tracked artifacts:

```python
import hashlib
import json
import tempfile
from pathlib import Path

from bug_cause_inference.p2f import no_diff_clean_audit as audit
from bug_cause_inference.p2f import reports

root = Path.cwd()
tracked_json = root / "src/bug_cause_inference/p2f/artifacts/p2f_canonical_no_diff_clean_paired_continuation_audit_v1.json"
tracked_md = root / "src/bug_cause_inference/p2f/artifacts/p2f_canonical_no_diff_clean_paired_continuation_audit_v1.md"
accepted_current_lf = {
    "src/bug_cause_inference/p2f/__init__.py": "64149bfd7700fb03ab026d43567b223d8ff651926778f7bbc85eeb6cd44a0c3c",
    "src/bug_cause_inference/p2f/no_diff_clean_audit.py": "66d3c70c138fe44873be5cd63140aea157f1753f681cfaa9ed7fc179b7ccf1cc",
    "src/bug_cause_inference/p2f/reports.py": "aef7abf588ac1c68436a9e08cd30514474ee244069164c5ddfa998b1699836c5",
    "tests/test_p2f_no_diff_clean_audit.py": "b38696946ffce342d69b8e7fe54c1c56ba37bab72a88c43f7472a4a69abb5df1",
    "tests/test_p2f_reports.py": "711160041d1f56bf514cfec2799e758694068b30aa6ec0c78a9916bcc9003f53",
}

def lf_sha256(path):
    raw = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(raw).hexdigest()

assert {path: lf_sha256(root / path) for path in accepted_current_lf} == accepted_current_lf

with tempfile.TemporaryDirectory(prefix="p2f-verify-") as work:
    for label in ("a", "b"):
        out = Path(work) / label
        raw_before = audit._implementation_raw_snapshot()
        summary = audit.run_no_diff_clean_audit(
            expected_implementation_identity=audit.FROZEN_IMPLEMENTATION_FILE_SHA256_LF,
            work_root=out / "work",
        )
        assert audit._implementation_raw_snapshot() == raw_before
        reports.save_p2f_report(
            summary,
            json_path=out / "audit.json",
            markdown_path=out / "audit.md",
        )
        assert out.joinpath("audit.json").read_bytes() == tracked_json.read_bytes()
        assert out.joinpath("audit.md").read_bytes() == tracked_md.read_bytes()

summary = audit.validate_audit_summary(json.loads(tracked_json.read_text(encoding="utf-8")))
assert reports.summary_from_markdown(tracked_md.read_text(encoding="utf-8")) == summary
assert summary["aggregate_results"]["digests"] == {
    "aggregate_results_digest": "ec03765df1854a9e78fe769e691d731754bca260c5f45434b3aa9b894dacc2c6",
    "baseline_identity_digest": "fc20aff06e1a5b2afb143edf57b14ff92d9e8eebe6da38c4ec818e8f22458c47",
    "canonical_summary_digest": "36d5ae198b4e9f873dedd4d13ac9ce467cde373fc8a7bf4ec6a30f32b360dfad",
    "input_contract_digest": "aca567fb7048aac2b6349a6383ec0aa601ceedde504724e4c75ddbf1e8729d0a",
    "pair_results_digest": "71e3b09994cfbf46ac27ff3fc5a47d4824bbfeabc8d820fab2d821c59c7365bf",
    "trajectory_results_digest": "13726d00369e9483e7d395aca8a282c6abd64fde017a954de44f8b32067b7c09",
}
assert audit.implementation_identity() == accepted_current_lf
assert audit.FROZEN_IMPLEMENTATION_FILE_SHA256_LF != accepted_current_lf
```

Use an unused short suffix for each basetemp, especially on Windows where the copied baseline's nested paths can otherwise exceed the legacy path-length boundary. Never redirect fresh output onto the tracked JSON or Markdown path. A fixed-input P2f fresh replay is verification only and must not be followed by result, threshold, policy, denominator, or claim tuning.

## Acceptance and Provenance

The controlling implementation was merged by [PR #36](https://github.com/guriguri215-lang/bug-cause-inference-game/pull/36):

```text
final accepted head   7c0f1c0453f154865a233c8ca840e2aba3afbe01
merge commit          ec48e3a03dd98f9c67b7102a33c7f8b169836c47
accepted/merge tree   4bc8e3ec55608860756b24aff948386ad5b0544b
PR CI                 29678029178 (run #71, success)
post-merge main CI    29678419623 (run #72, success)
```

Acceptance decisions remain separate:

- P2f software conformance final audit: accepted after independent final merged-tree review.
- P2f versioned artifact identity: accepted.
- P2f descriptive result: accepted only for the exact fixed-input observations above.
- P2f public documentation: accepted after independent documentation review and required verification in this documentation slice.

The artifact remains non-self-accepting. External acceptance and review records provide these decisions.

## Limitations and Deferred Questions

- Only one exact unpatched program is observed; there are no independent program replicates.
- The six-policy fractions are not population clean-safety or false-positive rates.
- The intervention is model-internal and non-causal, not a deployable policy.
- No P2e/P2f combined payoff, utility, weighted loss, threshold recommendation, or policy ranking is defined.
- Unseen clean inputs, benign-diff expansion, a second domain, inference, optimized sequence/DP work, and production readiness require separate specifications and reviews.
