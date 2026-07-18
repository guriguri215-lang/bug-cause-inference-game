# P2d Result Interpretation

## Question and Frozen Inputs

P2d answers one fixed-input descriptive question:

> For each accepted P2c terminal pair that did not select its direct detector but retained a budget-feasible detector and stopped on the no-bug-probability threshold, what happens if only that threshold predicate is suppressed for one terminal decision: does another accepted stop fire immediately, and otherwise what single action does the same frozen policy select and what is the normal post-action stop or one-step horizon?

The inputs are the accepted P2a runner, expansion-only buggy cohort, settings, seed, actions, costs, observations, and six formal policies; the accepted P2b detector mapping; and the accepted P2c trajectories and terminal rows. P2d changes none of them. It is an analysis-only, fixed-input, ground-truth-informed, model-internal, one-step, non-causal, and non-deployable audit.

The full ordered support remains 10 variants by 6 policies, or 60 pairs. Variants are ordered `P2A-BUG-001` through `P2A-BUG-010`; within each variant, policies are ordered:

1. `fixed_checklist`
2. `test_first`
3. `coverage_first`
4. `recent_diff_first`
5. `cause_only_p1a_style`
6. `expected_utility_per_cost`

All 60 accepted P2c terminal rows remain in the denominator. A row is an `intervention_candidate` only when it did not select its direct detector, its terminal direct detector was budget-feasible, and both accepted terminal stop fields equal `no_bug_probability_threshold`. Exactly 52 rows meet this preregistered rule. The other 8 rows remain in the artifact as `not_applicable`; they are not silently removed from overall support.

The cohort is hand-authored, same-domain, fixed, and non-iid. It is not a sample that supports population inference.

## Replay and Exactly-One Intervention

For every pair, P2d first replays the accepted P2c trajectory to its normal terminal state and requires exact row, state, stop, source-identity, P2a-outcome, and P2b-mapping agreement. Agreement is `60/60`.

For each candidate only, the wrapper then suppresses `no_bug_probability_threshold` for exactly one evaluation of the same terminal decision. It does not edit or monkeypatch the accepted runner. The remaining accepted predicates are evaluated with fresh action scores in their accepted precedence:

1. `bug_confidence_threshold`
2. `budget_limit`
3. `max_steps`
4. `low_expected_utility`

If one fires, the row is `alternate_stop_before_action` and no action is selected. Otherwise the row is `action_decision_reached`: the same frozen policy receives only its normal policy-visible arguments and selects one action. That action is executed once with the accepted observation and state-update semantics. The updated state then receives the normal common-stop evaluation. If no common stop fires, P2d records `one_step_horizon_reached` and ends without evaluating or executing a second action.

The P2b detector mapping is applied only after action selection as an audit label. Variant identity, bucket, direct-detector mapping, and ground truth are not policy-visible selector inputs.

## Five Distinct Axes

P2d keeps these axes separate:

- **Eligibility:** whether an accepted P2c row meets the preregistered intervention rule.
- **Residual stop:** whether a non-target accepted stop fires when only the target threshold is omitted.
- **Action selection:** which one action the same frozen policy selects when no residual stop fires.
- **Observation detection:** whether the accepted observation from that selected action records the bug as detected.
- **Post-action outcome:** the normal common stop after the action, or the P2d-only one-step horizon label.

Detector selection and observation detection are separate fields and aggregates. They happen to both equal `11/52` in this fixed result; that equality does not merge their definitions.

## Exact Overall Result

```text
ordered support / accepted P2c replay       60 / 60
intervention candidates                     52 / 60
not applicable                               8 / 60
alternate stop before action                 0 / 52
action decision reached                     52 / 52
action executed                             52 / 52
direct detector selected                    11 / 52 candidates
direct detector selected                    11 / 52 action-reached
observation detected                        11 / 52
post-action no_bug_probability_threshold    41 / 52
post-action one_step_horizon_reached         11 / 52
second action executed                       0 / 52
residual stop reason                         none 52 / 52
```

The selected-action distribution, including zero cells in accepted catalog order, is:

| Action | Count |
|---|---:|
| `run_smoke_tests` | 0 |
| `run_boundary_tests` | 0 |
| `run_null_missing_tests` | 24 |
| `run_config_matrix_tests` | 8 |
| `run_state_sequence_tests` | 0 |
| `run_property_search` | 0 |
| `inspect_traceback` | 0 |
| `inspect_coverage_spectrum` | 0 |
| `inspect_recent_diff` | 10 |
| `inspect_spec_clause` | 10 |

## Result by Policy

| Policy | Support | Candidate | NA | Selected | Detected | Post threshold | Horizon |
|---|---:|---:|---:|---:|---:|---:|---:|
| `fixed_checklist` | 10 | 8 | 2 | 2 | 2 | 6 | 2 |
| `test_first` | 10 | 8 | 2 | 2 | 2 | 6 | 2 |
| `coverage_first` | 10 | 8 | 2 | 2 | 2 | 6 | 2 |
| `recent_diff_first` | 10 | 8 | 2 | 3 | 3 | 5 | 3 |
| `cause_only_p1a_style` | 10 | 10 | 0 | 0 | 0 | 10 | 0 |
| `expected_utility_per_cost` | 10 | 10 | 0 | 2 | 2 | 8 | 2 |

These are descriptive counts, not policy scores, rankings, or improvement estimates.

## Result by Variant

| Variant | Support | Candidate | NA | Selected | Detected | Post threshold | Horizon |
|---|---:|---:|---:|---:|---:|---:|---:|
| `P2A-BUG-001` | 6 | 2 | 4 | 0 | 0 | 2 | 0 |
| `P2A-BUG-002` | 6 | 2 | 4 | 0 | 0 | 2 | 0 |
| `P2A-BUG-003` | 6 | 6 | 0 | 3 | 3 | 3 | 3 |
| `P2A-BUG-004` | 6 | 6 | 0 | 4 | 4 | 2 | 4 |
| `P2A-BUG-005` | 6 | 6 | 0 | 1 | 1 | 5 | 1 |
| `P2A-BUG-006` | 6 | 6 | 0 | 1 | 1 | 5 | 1 |
| `P2A-BUG-007` | 6 | 6 | 0 | 0 | 0 | 6 | 0 |
| `P2A-BUG-008` | 6 | 6 | 0 | 0 | 0 | 6 | 0 |
| `P2A-BUG-009` | 6 | 6 | 0 | 1 | 1 | 5 | 1 |
| `P2A-BUG-010` | 6 | 6 | 0 | 1 | 1 | 5 | 1 |

## Result by Bucket

| Bucket | Support | Candidate | NA | Selected | Detected | Post threshold | Horizon |
|---|---:|---:|---:|---:|---:|---:|---:|
| `boundary_precision` | 12 | 4 | 8 | 0 | 0 | 4 | 0 |
| `missing_optional_input` | 12 | 12 | 0 | 7 | 7 | 5 | 7 |
| `config_normalization` | 12 | 12 | 0 | 2 | 2 | 10 | 2 |
| `state_sequence` | 12 | 12 | 0 | 0 | 0 | 12 | 0 |
| `spec_semantics` | 12 | 12 | 0 | 2 | 2 | 10 | 2 |

## Interpretation Boundary

The absence of residual alternate stops is a statement about the four remaining predicates at these 52 reconstructed terminal decisions. It does not prove that the suppressed threshold caused the original miss. The intervention is model-internal and changes one predicate evaluation; it is not a randomized or otherwise identified causal contrast.

The `11/52` direct-detector selections and `11/52` detected observations do not establish that a policy should be changed, that any policy is defective, or that continuing after a production stop would be safe or useful. They do not rank the six policies or evaluate a deployable improvement.

The 11 `one_step_horizon_reached` rows mean only that no normal common stop fired after the single permitted action. P2d did not score, select, or execute a next action. A horizon row therefore does not show that a detector would be reached next, that it is unreachable, or that the result is a multi-step sequence/DP ceiling, optimality result, or general upper bound.

## Versioned Artifacts and Identity

The tracked artifacts contain the same validated summary:

- [Versioned JSON artifact](../src/bug_cause_inference/p2d/artifacts/p2d_one_step_stop_relaxation_audit_v1.json) — 248,450 bytes; SHA-256 `5fb30992bc16666fd3210709b1143e34f62c6f07635fe72962a4a7880c336f93`.
- [Versioned Markdown artifact](../src/bug_cause_inference/p2d/artifacts/p2d_one_step_stop_relaxation_audit_v1.md) — 249,662 bytes; SHA-256 `633305a95afbf237c2163ac3b1de634bf9c6e9a696747ec04a58e14a7c015dd4`.

The compact canonical validated-summary digest is `fab660ba884ec3c1b1bc0ba5348dff168a850cb6e305f9eb708b03c3205e4fc0`. The 50-file accepted-input identity-contract digest is `7d127bcedb58f59487e16b3ec9c3a300753fe48108ef2d8a676b4c8b059217b8`. All 60 compact canonical pair-result digests are separately anchored and validated.

Portable accepted identities use SHA-256 after CRLF-to-LF normalization. Parsed-input caching and same-run pre/post drift detection separately use exact raw working-tree bytes. The five-file P2d implementation snapshot includes the three source/serializer files and both P2d test files. Portable acceptance identity and raw drift detection serve different purposes and must not be substituted for one another.

Python 3.10.11 and 3.12.13 fresh audits both matched all 60 authoritative pair-result digests. The P2d-only replay/update wrapper uses `math.fsum` to make the accepted prior-times-weight normalization portable across those runtimes without changing accepted upstream source or the frozen rows/results. Python 3.10 generated JSON/Markdown also matched the tracked pair exactly.

Accepted upstream artifacts remain unchanged:

```text
P2a JSON      1699240 / d7e69fa62513f5bbae22d570e39b841401f5110b6cd1e45701c53393eb0ef3df
P2a Markdown  1701581 / 017c5e3d9281e59e0b115a825a5f0e08f90a5e15a1e331514296adf443a2808a
P2a summary             / 3dea5aaf38e1d9a46fd1a9ed973cb02c3fabf7ec933f2bb1c6df4f97446a9629
P2b JSON       144393 / 1bbb71c5627f756f5dba3aba4f5f333f287f2fbacbb805e50118074d08ce928d
P2b Markdown   146660 / ad53651027e024febc04708763398112b81f1bf69aea4f104d94c70f4590ac3b
P2b summary             / 873423a2cd15908300d604a970664152d931a8a306f64c797122851f887702e2
P2c JSON       387424 / 1ebfb62edd5034fd57ea69e18c3eb647a3a8746946ecb98d80b66fa127d989d7
P2c Markdown   389004 / ee9bfda6a7b352ff770fa3025dff4d4feb94e4e36201d256a76de6d569286666
P2c summary             / 3872257449d76453f6910b56d28f8e4fdf6c7bb7de30410b2d26335143c0392c
P2c 43-file contract    / 1a7c59b40dc837b1c2199a6f1fe8fc8016b87400df89eda05c00e28f0b0767bc
```

## Reproduction and Verification

P2d intentionally has no public CLI command. Run the targeted tests, relevant accepted-input regression, full suite, and P1b validator without overwriting tracked artifacts:

```bash
python -B -m pytest tests/test_p2d_stop_relaxation_audit.py tests/test_p2d_reports.py -q -p no:cacheprovider
python -B -m pytest tests/test_p2a_adequacy.py tests/test_p2a_candidate_oracles.py tests/test_p2a_candidates.py tests/test_p2a_compatibility.py tests/test_p2a_evaluation.py tests/test_p2a_execution.py tests/test_p2a_freeze.py tests/test_p2a_freeze_realization.py tests/test_p2a_reports.py tests/test_p2b_reports.py tests/test_p2b_solvability_ceiling.py tests/test_p2c_reports.py tests/test_p2c_trajectory_audit.py -q -p no:cacheprovider
python -B -m pytest -q -p no:cacheprovider
python -m bug_cause_inference.p1b.real_diff --validate
```

For two isolated P2d runs, use temporary output paths and compare them with the tracked pair:

```python
import hashlib
import json
import tempfile
from pathlib import Path

from bug_cause_inference.p2d import reports
from bug_cause_inference.p2d import stop_relaxation_audit as audit

root = Path.cwd()
tracked_json = root / "src/bug_cause_inference/p2d/artifacts/p2d_one_step_stop_relaxation_audit_v1.json"
tracked_md = root / "src/bug_cause_inference/p2d/artifacts/p2d_one_step_stop_relaxation_audit_v1.md"

with tempfile.TemporaryDirectory(prefix="p2d-verify-") as work:
    outputs = []
    for label in ("a", "b"):
        out = Path(work) / label
        summary = audit.run_stop_relaxation_audit()
        reports.save_p2d_report(
            summary,
            json_path=out / "audit.json",
            markdown_path=out / "audit.md",
        )
        outputs.append(out)

    assert outputs[0].joinpath("audit.json").read_bytes() == tracked_json.read_bytes()
    assert outputs[1].joinpath("audit.json").read_bytes() == tracked_json.read_bytes()
    assert outputs[0].joinpath("audit.md").read_bytes() == tracked_md.read_bytes()
    assert outputs[1].joinpath("audit.md").read_bytes() == tracked_md.read_bytes()

summary = json.loads(tracked_json.read_text(encoding="utf-8"))
compact = json.dumps(summary, ensure_ascii=False, separators=(",", ":")).encode()
assert hashlib.sha256(compact).hexdigest() == "fab660ba884ec3c1b1bc0ba5348dff168a850cb6e305f9eb708b03c3205e4fc0"
assert reports.summary_from_markdown(tracked_md.read_text(encoding="utf-8")) == summary
assert audit.identity_contract_digest(audit._identity_rows()) == audit.IDENTITY_CONTRACT_DIGEST
```

Closeout and release verification must not run the P2a or P2b outcome runners. Do not redirect verification output onto either tracked P2d artifact.

## Acceptance and Provenance

The P2d population, eligibility, intervention, schema, metrics, serializer, and claim boundary were frozen before the first outcome. Independent specification review closed its initial findings before execution. Independent implementation review then required fail-closed identity/result anchors and clearer selection/detection status, and separately reviewed the Python portability correction. Those corrections preserved all 60 frozen rows and the descriptive result.

The controlling implementation was merged by [PR #32](https://github.com/guriguri215-lang/bug-cause-inference-game/pull/32):

```text
final accepted head   4a0920c68a1d0c163006dcbb699c1c20127a8a5b
merge commit          7f6de22d77dee5b076fed2546911dca5bbf59530
accepted/merge tree   f6f741f40b5094f97813d076315163e0d5da3ca9
PR CI                 29639158553 (run #61, success)
post-merge main CI    29639555887 (run #62, success)
```

Acceptance decisions remain separate:

- P2d software conformance final audit: accepted after independent final merged-tree review.
- P2d versioned artifact identity: accepted.
- P2d descriptive result: accepted for the exact fixed-input observations above.
- P2d public documentation: accepted after independent documentation review, required verification, and a separate status-closure re-review in this documentation slice.

The artifact's embedded acceptance fields remain non-self-accepting implementation-time records. External acceptance and review records provide the decisions; the artifact does not accept itself.

## Limitations and Non-Claims

- The support is only 60 fixed, hand-authored, same-domain, non-iid policy/variant pairs; 52 are intervention candidates and 8 are not applicable.
- The P2b mapping is ground-truth-informed and unavailable to deployable policies.
- Exactly-one threshold suppression does not establish threshold causality or a stop-rule defect.
- Selection and observation detection are distinct; neither establishes a policy improvement, ranking, recommendation, or production usefulness.
- `one_step_horizon_reached` establishes neither next-step detector reachability nor detector unreachability.
- P2d executes at most one counterfactual action. It is not a multi-step sequence search, dynamic-programming ceiling, optimality result, or general upper bound.
- There is no new or tuned policy, second domain, no-diff clean stress, confidence interval, bootstrap, significance, causal inference, generalization, production-performance, or production-readiness claim.

## Deferred Questions

The following require separate pre-outcome specifications and reviews:

- multi-step sequence or dynamic-programming diagnostics;
- a new or tuned deployable policy study;
- no-diff clean stress or a second benchmark domain;
- inferential uncertainty, external validity, or production-readiness work.
