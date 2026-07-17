# P2a Result Interpretation

## Evidence Question and Accepted Scope

P2a asks a deliberately narrow evidence question: after candidate diversity and ground truth were reviewed without observing candidate-policy outcomes, what bucket-level discovery-loss pattern and separate clean-cohort behavior are observed when the existing six deterministic policies are applied to a frozen, versioned, same-domain checkout/pricing expansion?

This is a benchmark evidence expansion, not a policy-improvement study. The accepted result is descriptive evidence for the frozen hand-authored cohort and fixed evaluation contract only. Expansion-only buggy evidence is primary. The combined P2a-derived cohort is descriptive context.

The formal policy order is:

1. `fixed_checklist`
2. `test_first`
3. `coverage_first`
4. `recent_diff_first`
5. `cause_only_p1a_style`
6. `expected_utility_per_cost`

## Dataset and Four-Identity Separation

The immutable legacy benchmark contains 20 buggy and 5 clean variants. The P2a expansion adds 10 buggy and 5 clean variants in the same checkout/pricing domain. The combined P2a-derived cohort therefore contains 30 buggy and 10 clean variants.

Buggy evidence is reported as four separate identities:

- `accepted_legacy_reference_buggy`: the immutable accepted P1d1 reference context.
- `p2a_replayed_legacy_buggy`: the 20 legacy buggy variants evaluated with the frozen P2a adapter and action-test catalog.
- `expansion_only_buggy`: the 10 frozen expansion buggy variants; this is the primary P2a result.
- `combined_versioned_buggy`: P2a-replayed legacy outcomes plus expansion outcomes; this is descriptive.

Clean evidence uses the corresponding four identities:

- `accepted_legacy_reference_clean`
- `p2a_replayed_legacy_clean`
- `expansion_only_clean`
- `combined_versioned_clean`

The combined identities use P2a replay plus expansion only. Accepted-reference rows are context and are not arithmetic inputs to the combined results. Differences between an accepted legacy reference and a P2a replay are catalog/context deltas, not expansion effects.

## Expansion-Only Primary and Combined Descriptive Evidence

The primary discovery metric is bucket-level loss: one minus the within-bucket discovery rate. The five bucket cells use the stable bucket order `boundary_precision`, `missing_optional_input`, `config_normalization`, `state_sequence`, and `spec_semantics`. The reference average gives each bucket exact weight `1/5`, then weights variants uniformly within each bucket. It is not a variant-pooled average.

The combined result is shown to describe the versioned P2a cohort, not to replace the expansion-only primary evidence or the accepted legacy reference.

## Exact Observed Result

| Policies in formal order | Expansion-only buggy loss vector | Expansion-only reference average | Combined buggy loss vector | Combined reference average |
|---|---|---:|---|---:|
| `fixed_checklist`, `test_first`, `coverage_first`, `recent_diff_first` | `[0, 1, 1, 1, 1]` | `4/5` | `[1/2, 1, 1, 1, 1]` | `9/10` |
| `cause_only_p1a_style`, `expected_utility_per_cost` | `[1, 1, 1, 1, 1]` | `1` | `[1, 1, 1, 1, 1]` | `1` |

Every policy has worst-bucket loss `1` in both the expansion-only and combined buggy cohorts. The restricted-pure empirical result is therefore a six-policy tie with security loss `1`. This is an exact description of the fixed six-policy matrices, not evidence of policy superiority and not a general minimax result.

## Clean Safety Stratum

The expansion clean cohort is reported separately from buggy matrices, reference averages, and restricted-pure calculations. For each of the six policies:

- false positives: `0/5`;
- no-bug stops: `5/5`.

Mean investigation costs, in formal policy order, are `3, 3, 3, 5, 2, 2`. The zero false-positive observation applies only to these five included clean variants; it is not an estimate for unseen clean programs or a production safety claim.

## LOVO Interpretation

Leave-one-variant-out (LOVO) analysis uses saved frozen per-variant outcomes and exact arithmetic. It does not rerun policies. Buggy LOVO covers 10 expansion variants under two projections each, for 20 projections. Clean LOVO covers 5 expansion variants under two projections each, for 10 projections.

LOVO is descriptive influence analysis only. It is not a confidence interval, bootstrap, significance test, sampling-uncertainty estimate, new dataset identity, or new accepted result.

## Acceptance Separation

Three acceptances are separate:

- **Software acceptance:** the P2a adapter/catalog boundary, candidate and freeze tooling, versioned evaluation/report implementation, and corrective gate/LOVO implementation passed their independent implementation reviews.
- **Dataset acceptance:** the 10-buggy/5-clean expansion and its manifests, patches, contracts, and official freeze identity were accepted as the official frozen dataset.
- **Result acceptance:** the exact observations above were accepted only as descriptive evidence for that frozen cohort and fixed six-policy evaluation.

Software acceptance does not imply a favorable performance result. Dataset acceptance does not imply representativeness. Result acceptance does not imply policy superiority, generalization, statistical significance, production readiness, or a game-theoretic guarantee. The versioned artifact retains its implementation-time provenance; subsequent independent review and policy-management decisions provide the external acceptance record.

## Limitations and Explicit Non-Claims

- The variants are hand-authored and stratified within the same checkout/pricing domain.
- The evidence is non-iid.
- Location evaluation is function-level only.
- The real-diff artifacts are synthetic baseline-plus-patch artifacts, not real repository histories.
- There is no second-domain or unseen-variant generalization evidence.
- There is no confidence-interval, bootstrap, statistical-significance, or inferential claim.
- There is no production performance or production safety claim.
- There is no general minimax, Nash-equilibrium, regret, weighted-loss, mixed-strategy, or policy-superiority claim.
- The clean zero applies only to the included clean cohort.
- Accepted-reference versus P2a-replay differences are catalog/context deltas, not expansion effects.
- The fixed legacy fix-intent posterior label space does not contain the expansion authoring labels.

## Versioned Artifacts

The two artifacts contain the same validated summary:

- [Versioned JSON artifact](../src/bug_cause_inference/p2a/artifacts/evaluation/p2a_benchmark_evidence_expansion_v1.json) — 1,699,240 bytes; SHA-256 `d7e69fa62513f5bbae22d570e39b841401f5110b6cd1e45701c53393eb0ef3df`.
- [Versioned Markdown artifact](../src/bug_cause_inference/p2a/artifacts/evaluation/p2a_benchmark_evidence_expansion_v1.md) — 1,701,581 bytes; SHA-256 `017c5e3d9281e59e0b115a825a5f0e08f90a5e15a1e331514296adf443a2808a`.

The canonical validated-summary digest is `3dea5aaf38e1d9a46fd1a9ed973cb02c3fabf7ec933f2bb1c6df4f97446a9629`. These large versioned files are intentional evidence artifacts.
