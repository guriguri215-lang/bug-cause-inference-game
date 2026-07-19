# P2e Result Interpretation

## Question and Frozen Inputs

P2e answers one fixed-input descriptive question:

> Among the 41 accepted P2d rows whose non-detector action returned to the no-bug-probability threshold, what terminal outcome is observed when only that threshold predicate is suppressed at every later pre-action decision while retaining the accepted state, RNG, execution context, same frozen policy, observations, costs, budget, max-step, and update semantics?

The inputs are the accepted P2a runner, expansion-only buggy cohort, settings, seed, actions, costs, observations, and six formal policies; the accepted P2b detector mapping; the accepted P2c trajectories; and the accepted P2d replay, classifications, and post-action starting states. P2e changes none of those inputs. It is an analysis-only, fixed-input, ground-truth-informed, model-internal, bounded-sequence, non-causal, and non-deployable audit.

The full ordered support remains 10 variants by 6 policies, or 60 pairs. Variants are ordered `P2A-BUG-001` through `P2A-BUG-010`; within each variant, policies are ordered:

1. `fixed_checklist`
2. `test_first`
3. `coverage_first`
4. `recent_diff_first`
5. `cause_only_p1a_style`
6. `expected_utility_per_cost`

All 60 accepted P2d rows remain in the denominator:

- `continuation_candidate`: 41 rows whose accepted P2d non-detector action returned to `no_bug_probability_threshold`;
- `p2d_direct_detector_endpoint`: 11 rows whose P2d action selected the direct detector and detected the bug;
- `p2d_not_applicable`: 8 rows that were not eligible for the accepted P2d intervention.

The 11 P2d endpoints and 8 not-applicable rows are not silently removed from overall support. The cohort is hand-authored, same-domain, fixed, and non-iid. It is not a sample that supports population inference.

## Replay, Checkpoints, and Repeated Target-Only Suppression

For every pair, P2e replays the accepted P2d result and requires exact identity, row, classification, and outcome agreement. Agreement is `60/60`. Before any continuation starts, it reconstructs all 41 candidate checkpoints and requires exact state, RNG-state, and execution-context digests. Checkpoint agreement is `41/41`.

For each candidate, execution resumes from the retained mutable state, RNG, and execution context produced by that accepted replay. P2e does not recreate a new policy state, reseed the RNG, alter the accepted observations, or change action costs, budget, maximum steps, or update semantics.

At every later pre-action decision, P2e suppresses only `no_bug_probability_threshold`. The remaining accepted predicates keep their precedence:

1. `bug_confidence_threshold`
2. `budget_limit`
3. `max_steps`
4. `low_expected_utility`

If a residual predicate fires, no action is selected. Otherwise the same frozen policy receives only its normal policy-visible arguments: policy ID, retained state, remaining budget, and retained RNG. Variant identity, bucket, P2b detector mapping, and ground truth are not selector inputs. The P2b mapping is applied after selection only as a ground-truth-informed audit label.

Selected actions use the accepted observation and portable state-update semantics. A direct-detector observation terminates immediately. Otherwise P2e continues to the next decision under the same contract. Actions cannot repeat. Budget 12, maximum step 6, and the finite non-repeating action catalog guarantee termination. This is a bounded continuation, not an optimized or unbounded sequence search, a dynamic-programming ceiling, or an optimality computation.

## Distinct Axes

P2e keeps these axes separate:

- **Classification:** candidate, accepted P2d direct-detector endpoint, or accepted P2d not applicable.
- **Decision stop evaluation:** whether a non-target accepted stop fires while only the target threshold is omitted.
- **Action selection:** which action the same frozen policy selects if no residual stop fires.
- **Observation detection:** whether the accepted observation from that selected action records the bug as detected.
- **Continuation termination:** one exclusive terminal reason: detector, bug confidence, budget, maximum steps, low utility, or no available actions.

Detector selection and observation detection are separately stored fields and aggregates. They happen to both equal `21/41` in this fixed result; that equality does not merge their definitions.

## Exact Overall Result

```text
ordered support / accepted P2d replay       60 / 60
continuation candidates                     41 / 60
P2d direct-detector endpoints               11 / 60
P2d not applicable                           8 / 60
direct_detector_observed                    21 / 41 candidates
bug_confidence_threshold                     0 / 41
budget_limit                                 8 / 41
max_steps                                    4 / 41
low_expected_utility                         0 / 41
no_available_actions                         8 / 41
direct detector selected                    21 / 41
observation detected                        21 / 41
```

The terminal reasons are exclusive and complete: `21 + 0 + 8 + 4 + 0 + 8 = 41`.

Additional-action and additional-cost distributions include zero cells across their accepted domains:

```text
additional actions   0:0 / 1:11 / 2:24 / 3:6 / 4:0 / 5:0 / 6:0
additional cost      0:0 / 1:0 / 2:5 / 3:6 / 4:4 / 5:0 / 6:6 / 7:20 /
                     8:0 / 9:0 / 10:0 / 11:0 / 12:0
```

Detector-feasibility categories are also a separate descriptive axis:

| Category | Count |
|---|---:|
| Initially infeasible | 0 |
| Initially feasible and selected as direct detector | 21 |
| Initially feasible and became infeasible before selection | 20 |
| Initially feasible through a non-detector termination | 0 |

The selected-action distribution, including zero cells in accepted catalog order, is:

| Action | Count |
|---|---:|
| `run_smoke_tests` | 0 |
| `run_boundary_tests` | 6 |
| `run_null_missing_tests` | 13 |
| `run_config_matrix_tests` | 18 |
| `run_state_sequence_tests` | 12 |
| `run_property_search` | 8 |
| `inspect_traceback` | 0 |
| `inspect_coverage_spectrum` | 0 |
| `inspect_recent_diff` | 6 |
| `inspect_spec_clause` | 14 |

The counts sum to 77 selected actions across the 41 continuations.

## Result by Policy

Terminal columns are candidate-only. `Endpoint` and `NA` retain the complete 10-row policy support.

| Policy | Support | Candidate | Endpoint | NA | Detector | Budget | Max step | No action | Selected | Detected |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `fixed_checklist` | 10 | 6 | 2 | 2 | 4 | 2 | 0 | 0 | 4 | 4 |
| `test_first` | 10 | 6 | 2 | 2 | 4 | 2 | 0 | 0 | 4 | 4 |
| `coverage_first` | 10 | 6 | 2 | 2 | 4 | 2 | 0 | 0 | 4 | 4 |
| `recent_diff_first` | 10 | 5 | 3 | 2 | 3 | 2 | 0 | 0 | 3 | 3 |
| `cause_only_p1a_style` | 10 | 10 | 0 | 0 | 2 | 0 | 0 | 8 | 2 | 2 |
| `expected_utility_per_cost` | 10 | 8 | 2 | 0 | 4 | 0 | 4 | 0 | 4 | 4 |

Bug-confidence and low-utility terminal counts are zero for every policy. These are descriptive counts, not policy scores, rankings, or improvement estimates.

## Result by Variant

| Variant | Support | Candidate | Endpoint | NA | Detector | Budget | Max step | No action | Selected | Detected |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `P2A-BUG-001` | 6 | 2 | 0 | 4 | 1 | 0 | 0 | 1 | 1 | 1 |
| `P2A-BUG-002` | 6 | 2 | 0 | 4 | 1 | 0 | 0 | 1 | 1 | 1 |
| `P2A-BUG-003` | 6 | 3 | 3 | 0 | 2 | 0 | 0 | 1 | 2 | 2 |
| `P2A-BUG-004` | 6 | 2 | 4 | 0 | 1 | 0 | 0 | 1 | 1 | 1 |
| `P2A-BUG-005` | 6 | 5 | 1 | 0 | 3 | 0 | 1 | 1 | 3 | 3 |
| `P2A-BUG-006` | 6 | 5 | 1 | 0 | 3 | 0 | 1 | 1 | 3 | 3 |
| `P2A-BUG-007` | 6 | 6 | 0 | 0 | 3 | 1 | 1 | 1 | 3 | 3 |
| `P2A-BUG-008` | 6 | 6 | 0 | 0 | 3 | 1 | 1 | 1 | 3 | 3 |
| `P2A-BUG-009` | 6 | 5 | 1 | 0 | 2 | 3 | 0 | 0 | 2 | 2 |
| `P2A-BUG-010` | 6 | 5 | 1 | 0 | 2 | 3 | 0 | 0 | 2 | 2 |

Bug-confidence and low-utility terminal counts are zero for every variant.

## Result by Bucket

| Bucket | Support | Candidate | Endpoint | NA | Detector | Budget | Max step | No action | Selected | Detected |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `boundary_precision` | 12 | 4 | 0 | 8 | 2 | 0 | 0 | 2 | 2 | 2 |
| `missing_optional_input` | 12 | 5 | 7 | 0 | 3 | 0 | 0 | 2 | 3 | 3 |
| `config_normalization` | 12 | 10 | 2 | 0 | 6 | 0 | 2 | 2 | 6 | 6 |
| `state_sequence` | 12 | 12 | 0 | 0 | 6 | 2 | 2 | 2 | 6 | 6 |
| `spec_semantics` | 12 | 10 | 2 | 0 | 4 | 6 | 0 | 0 | 4 | 4 |

Bug-confidence and low-utility terminal counts are zero for every bucket.

## Interpretation Boundary

Repeated target-only suppression changes a model-internal decision predicate. It is not a randomized or otherwise identified causal contrast. The result does not prove that the threshold caused an original miss or that the threshold is defective.

The `21/41` direct-detector selections and `21/41` detected observations do not establish that a policy should be changed, that any policy is defective, or that continuing after a production stop would be safe or useful. They do not rank the six policies, estimate a deployable improvement, or establish sequence optimality.

The 8 budget, 4 maximum-step, and 8 no-available-action endpoints are terminal labels under this exact retained execution. They are not mutually exclusive causal explanations for original misses. They do not show detector impossibility, individual miss causation, an unbounded-search result, or a general upper bound.

P2b mapping and bucket/variant labels are ground-truth-informed audit provenance. They are unavailable to the selector. P2c trajectories, P2d starting states, and accepted observation semantics provide the replay provenance; P2e does not reinterpret them as policy-visible ground truth.

## Versioned Artifacts and Identity

The tracked artifacts contain the same validated summary:

- [Versioned JSON artifact](../src/bug_cause_inference/p2e/artifacts/p2e_bounded_threshold_relaxation_continuation_audit_v1.json) — 464,656 bytes; SHA-256 `28af62b91f2a25ee4cb8f7aa4cef8186d6976863ae1fd8f0ac17f1d067befb61`.
- [Versioned Markdown artifact](../src/bug_cause_inference/p2e/artifacts/p2e_bounded_threshold_relaxation_continuation_audit_v1.md) — 465,827 bytes; SHA-256 `a99e72e4334d76a74a5fb6c5a1e8b7c9d13975758d14238f178348c0fa135174`.

Validated identities:

```text
canonical validated-summary digest  e7dd83d7579274b19eb9a4af4940b7a26d40c52fcc9da6c44d0f83453220945d
pair-results digest                  cf6497bdea1c60dc176bab98e96e22a7e162feefc5953c9174948b47d82c4789
aggregate-results digest             349ac974d3ea4bc1bd690d44876129404b2d138f060a90a7693dbb4917cb982a
57-file accepted-input contract      10151569d670f0ada06ae167df1d82f4c77ce66c086c778a299b50ce61e4add5
```

Portable accepted identities use SHA-256 after CRLF-to-LF normalization. Parsed-input caching and same-run pre/post drift detection separately use exact raw working-tree bytes.

P2e has a two-layer implementation-identity boundary. The artifact preserves the historical five-file identities frozen before the first outcome:

```text
src/bug_cause_inference/p2e/__init__.py                 bed9dc32d78fd419c34929a425d09800e53b536792dec16bac8c2eec398b98ff
src/bug_cause_inference/p2e/continuation_audit.py       15b2e7525399e609de95a13c9ce4e747c38acef88f8cf937ff7e6764dc7f9ca9
src/bug_cause_inference/p2e/reports.py                  48477174f16ad1caeaedfe5c5b165bb6c45a0c743592faaa46ea2dc2d1eb7566
tests/test_p2e_continuation_audit.py                    17775c3ca167a6a8dbc1e340b6b4192640f2766a4c17c4befeca11a411aab1a9
tests/test_p2e_reports.py                               81af3c35c5be84ba8c33d8ee0e54922ba4e521696e666904d6d98615a74c9b4c
```

Independent implementation review then added fail-closed identity and negative/runtime coverage without changing the 60 rows, aggregates, artifact bytes, or canonical result. The final merged current identities are:

```text
src/bug_cause_inference/p2e/__init__.py                 bed9dc32d78fd419c34929a425d09800e53b536792dec16bac8c2eec398b98ff
src/bug_cause_inference/p2e/continuation_audit.py       ffada38b510ed782e819751dbbc3ec9ec6e0cd2b4204a9be873f1c412f007947
src/bug_cause_inference/p2e/reports.py                  48477174f16ad1caeaedfe5c5b165bb6c45a0c743592faaa46ea2dc2d1eb7566
tests/test_p2e_continuation_audit.py                    8e539426ed28a8b8d7c5ba9a8636731a7e843425b853f2161899ba73252f93b0
tests/test_p2e_reports.py                               db658f234edef11ebf43a125e46eb2c657b06a7e44ea633631fe5d1c8067ee67
```

Historical constants describe the pre-outcome event boundary. Verification independently compares the five current LF-canonical hashes with the accepted final merged map above. The runner separately snapshots checkout-specific raw bytes before and after each fresh run to detect same-run drift. A reviewed historical/current difference is not artifact drift, and current hashes must not overwrite or rebind the historical freeze.

Accepted upstream artifacts remain unchanged:

```text
P2a JSON       d7e69fa62513f5bbae22d570e39b841401f5110b6cd1e45701c53393eb0ef3df
P2a Markdown   017c5e3d9281e59e0b115a825a5f0e08f90a5e15a1e331514296adf443a2808a
P2a summary    3dea5aaf38e1d9a46fd1a9ed973cb02c3fabf7ec933f2bb1c6df4f97446a9629
P2b JSON       1bbb71c5627f756f5dba3aba4f5f333f287f2fbacbb805e50118074d08ce928d
P2b Markdown   ad53651027e024febc04708763398112b81f1bf69aea4f104d94c70f4590ac3b
P2b summary    873423a2cd15908300d604a970664152d931a8a306f64c797122851f887702e2
P2c JSON       1ebfb62edd5034fd57ea69e18c3eb647a3a8746946ecb98d80b66fa127d989d7
P2c Markdown   ee9bfda6a7b352ff770fa3025dff4d4feb94e4e36201d256a76de6d569286666
P2c summary    3872257449d76453f6910b56d28f8e4fdf6c7bb7de30410b2d26335143c0392c
P2d JSON       5fb30992bc16666fd3210709b1143e34f62c6f07635fe72962a4a7880c336f93
P2d Markdown   633305a95afbf237c2163ac3b1de634bf9c6e9a696747ec04a58e14a7c015dd4
P2d summary    fab660ba884ec3c1b1bc0ba5348dff168a850cb6e305f9eb708b03c3205e4fc0
```

## Reproduction and Verification

P2e intentionally has no public CLI command. Run the targeted tests, relevant accepted-input regression, full suite, and P1b validator without overwriting tracked artifacts:

```bash
python -B -m pytest tests/test_p2e_continuation_audit.py tests/test_p2e_reports.py -q -p no:cacheprovider
python -B -m pytest tests/test_p2a_adequacy.py tests/test_p2a_candidate_oracles.py tests/test_p2a_candidates.py tests/test_p2a_compatibility.py tests/test_p2a_evaluation.py tests/test_p2a_execution.py tests/test_p2a_freeze.py tests/test_p2a_freeze_realization.py tests/test_p2a_reports.py tests/test_p2b_reports.py tests/test_p2b_solvability_ceiling.py tests/test_p2c_reports.py tests/test_p2c_trajectory_audit.py tests/test_p2d_reports.py tests/test_p2d_stop_relaxation_audit.py tests/test_p2e_continuation_audit.py tests/test_p2e_reports.py -q -p no:cacheprovider
python -B -m pytest -q -p no:cacheprovider
python -m bug_cause_inference.p1b.real_diff --validate
```

For two isolated P2e runs, use temporary output paths and compare them with the tracked pair:

```python
import hashlib
import json
import tempfile
from pathlib import Path

from bug_cause_inference.p2e import continuation_audit as audit
from bug_cause_inference.p2e import reports

root = Path.cwd()
tracked_json = root / "src/bug_cause_inference/p2e/artifacts/p2e_bounded_threshold_relaxation_continuation_audit_v1.json"
tracked_md = root / "src/bug_cause_inference/p2e/artifacts/p2e_bounded_threshold_relaxation_continuation_audit_v1.md"
accepted_current_lf = {
    "src/bug_cause_inference/p2e/__init__.py": "bed9dc32d78fd419c34929a425d09800e53b536792dec16bac8c2eec398b98ff",
    "src/bug_cause_inference/p2e/continuation_audit.py": "ffada38b510ed782e819751dbbc3ec9ec6e0cd2b4204a9be873f1c412f007947",
    "src/bug_cause_inference/p2e/reports.py": "48477174f16ad1caeaedfe5c5b165bb6c45a0c743592faaa46ea2dc2d1eb7566",
    "tests/test_p2e_continuation_audit.py": "8e539426ed28a8b8d7c5ba9a8636731a7e843425b853f2161899ba73252f93b0",
    "tests/test_p2e_reports.py": "db658f234edef11ebf43a125e46eb2c657b06a7e44ea633631fe5d1c8067ee67",
}

def lf_sha256(path):
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()

assert {
    path: lf_sha256(root / path) for path in accepted_current_lf
} == accepted_current_lf

with tempfile.TemporaryDirectory(prefix="p2e-verify-") as work:
    outputs = []
    for label in ("a", "b"):
        out = Path(work) / label
        raw_before = audit._implementation_raw_snapshot()
        summary = audit.run_continuation_audit()
        assert audit._implementation_raw_snapshot() == raw_before
        assert summary["validation_status"] == {"status": "valid"}
        reports.save_p2e_report(
            summary,
            json_path=out / "audit.json",
            markdown_path=out / "audit.md",
        )
        outputs.append(out)

    for out in outputs:
        assert out.joinpath("audit.json").read_bytes() == tracked_json.read_bytes()
        assert out.joinpath("audit.md").read_bytes() == tracked_md.read_bytes()

summary = audit.validate_audit_summary(json.loads(tracked_json.read_text(encoding="utf-8")))
assert reports.summary_from_markdown(tracked_md.read_text(encoding="utf-8")) == summary
assert audit._canonical_digest(summary) == "e7dd83d7579274b19eb9a4af4940b7a26d40c52fcc9da6c44d0f83453220945d"
assert audit._canonical_digest(summary["pair_results"]) == "cf6497bdea1c60dc176bab98e96e22a7e162feefc5953c9174948b47d82c4789"
assert audit._canonical_digest(summary["aggregate_results"]) == "349ac974d3ea4bc1bd690d44876129404b2d138f060a90a7693dbb4917cb982a"
assert audit._canonical_digest(audit._identity_rows()) == audit.IDENTITY_CONTRACT_DIGEST
assert audit._implementation_identity() == accepted_current_lf
assert audit.FROZEN_IMPLEMENTATION_FILE_SHA256_LF != accepted_current_lf
```

The exact current-map assertion is the portable final merged identity gate. The final inequality is intentional: it verifies that the accepted current identity remains distinct from, rather than rebound into, the historical freeze. The raw snapshot assertion is a separate checkout-specific same-run drift gate; raw constants are not cross-platform portable identities.

Closeout and release verification must not run the P2a or P2b outcome runners. Do not redirect verification output onto either tracked P2e artifact. A fresh P2e replay is permitted only as fixed-input verification; it must not be followed by metric, catalog, policy, eligibility, result, or claim tuning.

## Acceptance and Provenance

The P2e question, population, classification, repeated target-only intervention, schema, metrics, serializer, and claim boundary were frozen before the first outcome. Independent specification review closed its initial findings before execution. Independent implementation review then required the historical/current identity separation and broader fail-closed negative/runtime coverage. Those corrections preserved all frozen rows, aggregates, artifact bytes, and the descriptive result.

The controlling implementation was merged by [PR #34](https://github.com/guriguri215-lang/bug-cause-inference-game/pull/34):

```text
final accepted head   961eeae8df1add0f9a8b4ac443f835f90ea63f9a
merge commit          a53a852d2551d1d6d4330a148f5f90e18c402a1e
accepted/merge tree   37738aacffa950a4e3b18ec07a334b436d9a00b4
PR CI                 29645079577 (run #65, success)
post-merge main CI    29645543353 (run #66, success)
```

Acceptance decisions remain separate:

- P2e software conformance final audit: accepted after independent final merged-tree review.
- P2e versioned artifact identity: accepted.
- P2e descriptive result: accepted for the exact fixed-input observations above.
- P2e public documentation: accepted after independent documentation review and required verification in this documentation slice.

The artifact's embedded acceptance fields remain non-self-accepting implementation-time records. External acceptance and review records provide the decisions; the artifact does not accept itself.

## Limitations and Non-Claims

- The support is only 60 fixed, hand-authored, same-domain, non-iid policy/variant pairs; 41 are continuation candidates, 11 are accepted P2d endpoints, and 8 are not applicable.
- The P2b mapping is ground-truth-informed and unavailable to deployable policies.
- Repeated target-only threshold suppression does not establish threshold causality or a stop-rule defect.
- Selection and observation detection are distinct; neither establishes policy improvement, ranking, recommendation, or production usefulness.
- Budget, maximum-step, and no-action terminal labels are not causal miss categories and do not establish detector impossibility.
- P2e is finite and bounded. It is not an optimized or unbounded sequence search, dynamic-programming ceiling, optimality result, or general upper bound.
- There is no new or tuned policy, second domain, no-diff clean stress, confidence interval, bootstrap, significance, causal inference, generalization, production-performance, or production-readiness claim.

## Deferred Questions

The following require separate pre-outcome specifications and reviews:

- any new diagnostic question beyond the accepted bounded continuation;
- an optimized sequence or dynamic-programming diagnostic;
- a new or tuned deployable policy study;
- no-diff clean stress or a second benchmark domain;
- inferential uncertainty, external validity, or production-readiness work.
