# P2b Result Interpretation

## Question and Frozen Inputs

P2b asks a narrow diagnostic question: with the accepted P2a dataset, 24-case action-test catalog, action costs, budget, settings, saved six-policy outcomes, and variant membership held fixed, which included buggy variants have at least one direct failure-producing catalog action, and is the least-cost direct detector within the fixed budget?

The diagnostic evaluates the same 24 frozen catalog cases against each of the 10 accepted P2a buggy variants, for 240 case evaluations. It reuses the accepted expansion-only six-policy outcomes without rerunning policies. The 5 accepted clean variants remain identity-checked inputs but are not part of the P2b primary support.

P2b does not change or regenerate P2a source, candidate patches, manifests, freeze data, evaluation artifacts, catalog cases, action costs, policies, settings, or outcomes.

## Definitions

For an included buggy variant, **static catalog reachability** means that at least one frozen catalog case fails when applied to that variant and maps to a direct detecting action. Context-only evidence, patch location metadata, or an action with no directly assigned failed case does not make a variant reachable.

The **budget-feasible ceiling** uses the full variant identity and ground truth to choose the least-cost direct detecting action at step 1. The action is feasible when its cost is within the accepted budget of 12 and the initial common-stop contract does not fire. This selector is intentionally non-deployable because a real policy does not know the hidden variant identity or detecting-action set.

The ceiling is one-step only. It does not search multi-step sequences or run dynamic programming. A saved-policy miss on a reachable, budget-feasible variant is described only as a selection/order/stop trajectory limitation under this fixed contract.

## Exact Result

```text
case evaluations                     240
catalog-reachable variants           10 / 10
budget-feasible variants             10 / 10
catalog-unreachable variants          0 / 10
canonical summary digest             873423a2cd15908300d604a970664152d931a8a306f64c797122851f887702e2
```

The deterministic variant order and independently recomputable direct-detection result are:

| Variant | Direct detecting actions | Minimum cost | Budget feasible |
|---|---|---:|---|
| `P2A-BUG-001` | `run_boundary_tests` | 2 | yes |
| `P2A-BUG-002` | `run_boundary_tests` | 2 | yes |
| `P2A-BUG-003` | `run_null_missing_tests` | 2 | yes |
| `P2A-BUG-004` | `run_null_missing_tests`, `run_config_matrix_tests` | 2 | yes |
| `P2A-BUG-005` | `run_config_matrix_tests` | 3 | yes |
| `P2A-BUG-006` | `run_config_matrix_tests` | 3 | yes |
| `P2A-BUG-007` | `run_state_sequence_tests` | 4 | yes |
| `P2A-BUG-008` | `run_state_sequence_tests` | 4 | yes |
| `P2A-BUG-009` | `inspect_spec_clause` | 2 | yes |
| `P2A-BUG-010` | `inspect_spec_clause` | 2 | yes |

The saved-policy comparison, in the accepted formal policy order, is:

| Policy | Saved discoveries | One-step ceiling | Ceiling gap |
|---|---:|---:|---:|
| `fixed_checklist` | 2/10 | 10/10 | 4/5 |
| `test_first` | 2/10 | 10/10 | 4/5 |
| `coverage_first` | 2/10 | 10/10 | 4/5 |
| `recent_diff_first` | 2/10 | 10/10 | 4/5 |
| `cause_only_p1a_style` | 0/10 | 10/10 | 1 |
| `expected_utility_per_cost` | 0/10 | 10/10 | 1 |

The result separates two questions that the accepted P2a policy matrices did not separate:

- **Catalog limitation:** no direct failure-producing case exists in the frozen catalog for the variant.
- **Saved-policy trajectory limitation:** a direct, budget-feasible catalog certificate exists, but the saved policy trajectory did not discover the variant.

All 10 included variants fall into the second category for at least one saved policy. This does not identify whether action selection, ordering, accumulated cost, or stopping was the specific cause of an individual policy miss.

## Versioned Artifacts and Identity

The two tracked artifacts contain the same validated summary:

- [Versioned JSON artifact](../src/bug_cause_inference/p2b/artifacts/p2b_fixed_catalog_solvability_ceiling_v1.json) — 144,393 bytes; SHA-256 `1bbb71c5627f756f5dba3aba4f5f333f287f2fbacbb805e50118074d08ce928d`.
- [Versioned Markdown artifact](../src/bug_cause_inference/p2b/artifacts/p2b_fixed_catalog_solvability_ceiling_v1.md) — 146,660 bytes; SHA-256 `ad53651027e024febc04708763398112b81f1bf69aea4f104d94c70f4590ac3b`.

The canonical validated-summary digest is `873423a2cd15908300d604a970664152d931a8a306f64c797122851f887702e2`.

Accepted file identities use SHA-256 after CRLF-to-LF normalization. That makes the accepted identity portable between Windows CRLF and Linux LF checkouts. The parsed-input cache key and fresh pre/post execution drift boundary separately use exact raw working-tree bytes. Portable acceptance identity and raw-byte drift detection serve different purposes and must not be substituted for each other.

The final merged implementation checks 39 accepted identities, including all 15 P2a candidate patches and 6 canonical baseline source files, before and after the 240 case evaluations.

## Reproduction and Verification

P2b intentionally has no public reporting CLI. Use the tracked artifacts and repository tests as the public verification surface:

```bash
python -m pytest tests/test_p2b_solvability_ceiling.py tests/test_p2b_reports.py -q -p no:cacheprovider
python -B -m pytest -q -p no:cacheprovider
python -m bug_cause_inference.p1b.real_diff --validate
```

The targeted tests verify the 240-case execution contract, exact aggregate and per-variant result, identity gates, CRLF/LF portability, raw-byte drift detection, deterministic JSON/Markdown bytes, semantic agreement, invalid-result fail-closed behavior, and accepted P2a non-regression.

## Acceptance and Provenance

The controlling implementation was merged by [PR #28](https://github.com/guriguri215-lang/bug-cause-inference-game/pull/28):

```text
final accepted head   7dc0e8852deb0f892e55b3d5f7648ff575eff62f
merge commit          eb33abd5edb801163fbe503a7c918fa0b2e1677a
CI run                29626436257 (run #50, success)
```

The final head includes the cross-platform identity correction: LF-canonical hashes define portable accepted identity, while raw working-tree hashes protect the cache and execution drift boundary.

Acceptance decisions remain separate:

- P2b software conformance final audit: accepted.
- P2b versioned artifact identity: accepted.
- P2b descriptive result: accepted for the exact fixed-catalog observations above.
- P2b public documentation: accepted after independent documentation review and required verification in this documentation slice.

The artifact's embedded acceptance fields remain non-self-accepting implementation-time records. External review and policy-management records, rather than artifact self-assertion, provide the acceptance decisions.

Accepted P2a remains unchanged. Its JSON SHA-256 is `d7e69fa62513f5bbae22d570e39b841401f5110b6cd1e45701c53393eb0ef3df`, its Markdown SHA-256 is `017c5e3d9281e59e0b115a825a5f0e08f90a5e15a1e331514296adf443a2808a`, and its canonical summary digest is `3dea5aaf38e1d9a46fd1a9ed973cb02c3fabf7ec933f2bb1c6df4f97446a9629`.

## Limitations and Non-Claims

- The cohort is hand-authored, stratified, same-domain, fixed, and non-iid.
- The result covers 10 included buggy variants and the accepted 24-case catalog only.
- The ceiling uses hidden variant ground truth unavailable to deployable policies.
- The one-step ceiling ignores multi-step context-dependent evidence and is not a sequence or DP result.
- The result does not establish an oracle policy, optimal deployable policy, seventh formal policy, policy winner, or policy superiority.
- The result is not a general upper bound or general solvability result.
- A reachable saved-policy miss is not proof of a software defect or causal policy inferiority.
- There is no second-domain, unseen-variant, arbitrary-program, production-performance, or production-safety claim.
- There is no confidence interval, bootstrap, significance, causal, inferential, minimax, Nash, regret, weighted-loss, or mixed-strategy claim.
- Clean false-positive behavior is outside the P2b primary diagnostic and remains covered by the separate accepted P2a clean stratum.

## Deferred Questions

The following require separate pre-outcome specifications and reviews:

- multi-step sequence or dynamic-programming diagnostics;
- a deployable candidate policy or policy-tuning study;
- no-diff clean stress or a second benchmark domain;
- combined cost plus dropout/delay analysis;
- inferential uncertainty or external-validity studies.
