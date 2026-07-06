# P1c Result Interpretation

Status: reporting-only interpretation note. No code, CLI, runtime behavior, metric, dataset, policy, threshold, score, action cost, observation profile, or variant changes are included in this document.

This note consolidates how to read the current P1c1, P1c3, P1c5, P1c7, and P1c9 reports together. It should be read as an interpretation layer over the generated `p1c-evaluate` output, not as a new benchmark definition or a new stress model.

## Scope And Non-Claims

P1c remains an analysis-only robustness report over the existing 25-variant P1b injected checkout/pricing scaffold. The current reports reuse existing P1b variants, policies, settings, observations, execution traces, real-diff artifacts, labels, and metric definitions.

This note does not claim:

- real-world debugging accuracy,
- production source-code fault localization,
- automated bug discovery,
- automated repair,
- an LLM agent benchmark,
- real repository history coverage,
- a minimax-optimal policy or game-theoretic guarantee,
- a weighted payoff, regret, equilibrium, formal payoff, or single weighted utility model.

The primary reading uses `execution_grounded`. `metadata_synth` is diagnostic only because it is metadata-dependent and can make some metrics look better than execution-derived evidence.

## How To Read The Reports Together

P1c1 is the baseline robustness report. It groups the existing P1b outcomes into P1c0 buckets and reports per-bucket metrics, raw variant worst cases, headline worst-case summaries, and average-versus-worst gaps. It answers: "Where does a policy look weaker than its average result suggests?"

P1c3 adds metric-specific selected buckets. It takes the existing P1c1 bucket metrics and selects the hardest bucket per policy and metric. It answers: "If the report highlights only the weakest bucket for each metric, which bucket is selected?" Clean false-positive stress is separate and uses only the clean bucket.

P1c5 adds bounded observation-cost stress. It reruns the existing policies inside a P1c-only policy-visible cost-overlay path and reports profile-vs-baseline metric gaps. It answers: "What changes when a small documented set of observation actions becomes more expensive, without mutating P1b default costs?"

P1c7 is nested under P1c5. It selects the hardest bucket inside each cost profile and compares that selection with the P1c3 default-cost selection. It answers: "Did the cost profile change where the weakness appears, even if aggregate metrics changed only a little?"

P1c9 adds bounded observation dropout/delay stress. It keeps source observations intact and perturbs only policy-facing copied observations inside a P1c-only analysis path. It answers: "What changes when a small documented evidence family is hidden or delayed without changing the underlying P1b action result?"

These reports should not be collapsed into one score. The useful signal is metric-specific: discovery, first-failure cost, localization, cause, fix-intent, false-positive, and mean-cost results can point to different weaknesses.

## Current Primary-Policy Snapshot

For the current primary policy, `expected_utility_per_cost`, the execution-grounded aggregate reading is:

| metric | value |
|---|---:|
| `bug_discovery_rate_within_budget` | `0.40` |
| `cost_to_first_failure` | `8.95` |
| `location_top3_accuracy` | `0.55` |
| `cause_top1_accuracy` | `0.55` |
| `fix_intent_top1_accuracy` | `0.40` |
| `mean_investigation_cost` | `4.64` |

These averages are useful only with the bucket view beside them. P1c1 and P1c3 show that the aggregate hides sharply different bucket behavior.

## Key Current Weaknesses

`state_sequence` is the primary brittle bucket. For `expected_utility_per_cost`, discovery, location top-3, cause top-1, and fix-intent top-1 are all `0.0`, and first-failure cost is `14`. P1c3 selects `state_sequence` for discovery, first-failure cost, location, cause, and fix-intent.

`config_normalization` is the next broad weak bucket. For the same policy, discovery, location top-3, cause top-1, and fix-intent top-1 are all `0.25`, with first-failure cost `10.75`. It is weaker than the aggregate, but it does not replace `state_sequence` as the main selected bucket under default costs.

`missing_optional_input` is a high-cost success bucket. It has `1.0` discovery, location top-3, cause top-1, and fix-intent top-1 for the primary policy, with first-failure cost `1`. However, it is selected for mean investigation cost at `9.75`, so the interpretation is "successful but expensive", not "globally easy."

Clean false positives are not currently triggered. The current five clean variants have `false_positive_rate_on_clean_cases = 0.0` in the baseline selected-bucket report and in the current cost/dropout/delay stress profiles. This means the current clean variants do not expose false positives; it does not show that false-positive risk is solved beyond this scaffold.

## P1c5 And P1c7 Interpretation

Among the current cost profiles, `trace_access_expensive` is the most informative for the primary policy. It produces positive gaps for discovery (`0.10`), first-failure cost (`1.35`), location top-3 (`0.15`), cause top-1 (`0.10`), and mean cost (`0.04`). Its fix-intent gap is `-0.05`, so the effect is not uniformly worse across every metric.

P1c7 shows that `trace_access_expensive` broadens several selected-bucket weaknesses from `state_sequence` alone to `config_normalization` plus `state_sequence`. That matters because it says the profile changes where the weakest metric-specific bucket appears, not just how large the aggregate gap is.

The other cost profiles show smaller or no selected-bucket shifts for the primary policy:

- `sequence_reproduction_expensive` keeps the same selected buckets as the default-cost baseline for the main selected metrics.
- `localization_evidence_expensive` keeps the same selected buckets for the main selected metrics, with a small location aggregate gap and lower mean cost in the current run.
- `targeted_reproduction_expensive` keeps the same selected buckets for the main selected metrics and has only a small mean-cost gap.

The cost-stress reading therefore supports keeping `trace_access_expensive` in mind, but it does not by itself justify adding a new combined stress model before the existing results are documented.

## P1c9 Interpretation

`traceback_signal_dropout` produces small primary-policy degradation in cause top-1 (`0.05` gap), fix-intent top-1 (`0.05` gap), and mean investigation cost (`0.20` gap). It does not change discovery, first-failure cost, or location top-3 in the current primary-policy execution-grounded aggregate.

`recent_diff_signal_delay` mainly affects mean investigation cost for the primary policy (`0.12` gap). In the current primary-policy execution-grounded run, delayed payloads are released `8/8`, so the delay is observable but not producing a broader aggregate failure.

`coverage_signal_dropout` does not currently expose a primary-policy aggregate weakness. The current gaps are `0.0` across the headline primary-policy metrics.

`sequence_reproduction_delay` does not currently expose an urgent new primary-policy aggregate weakness. Its primary-policy perturbed observation count is `0`, and all primary-policy aggregate gaps are `0.0` in the current execution-grounded run.

The P1c9 implementation restricts `sequence_reproduction_delay` matching to failure-bearing `run_state_sequence_tests` source observations. Pass or no-bug state-sequence observations are not converted into delayed failure placeholders.

Clean false positives are not triggered in the current dropout/delay profiles.

## Why Combined Cost Plus Dropout/Delay Should Wait

A combined cost plus dropout/delay interaction is a plausible future design candidate, but it should wait for a later design review.

Reasons:

- The current reports already include multiple objects with different boundaries: P1c3 selected buckets, P1c5 cost stress, P1c7 nested profile-conditioned selection, and P1c9 dropout/delay stress.
- The main current weakness is readable without a combined model: `state_sequence` is the primary brittle bucket, `config_normalization` is the next broad weak bucket, and `missing_optional_input` is high-cost but successful.
- P1c9 does not currently show an urgent primary-policy follow-up signal. `traceback_signal_dropout` and `recent_diff_signal_delay` produce small, metric-specific changes; `coverage_signal_dropout` and `sequence_reproduction_delay` do not expose new primary aggregate weakness.
- Combining stress dimensions now would increase report surface area and public-boundary risk before the existing reports have a stable interpretation.
- Any combined interaction would need a separate specification to preserve P1b defaults, P1c metric semantics, clean false-positive separation, and the no weighted-payoff boundary.

The recommended next action is a design review after this consolidation note, not immediate implementation of a combined interaction specification.

## Recommended Next Action

Treat the current P1c expansion as paused after P1c9. Use this interpretation note as the handoff artifact for deciding whether the next work should be:

- a small documentation/README boundary review,
- a focused design review for a future combined interaction specification,
- or a non-P1c stabilization task such as evaluation harness cleanup.

Do not add a new P1c stress model until that review explicitly confirms the scope, object boundary, metric-specific reporting shape, clean false-positive handling, and public non-claims.
