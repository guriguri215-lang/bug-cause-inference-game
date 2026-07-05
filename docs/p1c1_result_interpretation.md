# P1c1 Result Interpretation

P1c1 adds an analysis-only worst-case report over the existing P1b injected-bug benchmark. This note interprets that report before any P1c2 specification work. It is not a replacement for the generated JSON or Markdown report; it is a short reading memo for deciding which stress direction should come next.

## Scope

This note reads the P1c1 `execution_grounded` report as the primary result. That mode uses the P1b execution-derived observations, including checkout test results, exceptions, traced checkout functions, function-level coverage suspicion, and Phase C real-diff artifacts for `inspect_recent_diff`.

`metadata_synth` is used only as a diagnostic comparison. It remains a metadata-dependent baseline and should not be treated as the headline robustness result.

No implementation logic, P1b policies, thresholds, scores, action costs, variants, datasets, or real-diff artifacts are changed by this note.

## Reading Guide

The most useful P1c1 fields for interpretation are:

- `bucket_metrics`: shows which primary bucket is weak for each metric.
- `headline_worst_case_summary`: identifies the worst bucket per policy and metric.
- `raw_variant_worst_cases`: lists the concrete variant IDs behind the bucket failures.
- `average_vs_worst_gap`: shows where a policy looks acceptable on average but collapses on its hardest bucket.

The clean bucket should be read separately. `clean_false_positive` has meaningful false-positive and clean-cost metrics, while buggy-only metrics are intentionally `n/a`.

## Main Fragility Patterns

The strongest primary pattern is that `state_sequence` is the hardest execution-grounded bucket for the current primary policy, `expected_utility_per_cost`. Its bucket discovery, location top-3, cause top-1, and fix-intent top-1 rates are all `0.0`, and its penalized first-failure cost is `14`.

`config_normalization` is the second major weak bucket. For `expected_utility_per_cost`, discovery is only `0.25`, location top-3 is `0.25`, cause top-1 is `0.25`, and fix-intent top-1 is `0.25`. For checklist-like policies, `config_normalization` is often tied with `state_sequence` as a zero-discovery bucket.

`missing_optional_input` is the most favorable bucket for `expected_utility_per_cost`: discovery, location top-3, cause top-1, and fix-intent top-1 are all `1.0`. However, it is also the max mean-cost bucket for that policy at `9.75`, so it is not simply cheap success.

`boundary_precision` splits policies. Checklist, test-first, coverage-first, and recent-diff-first all discover this bucket at `1.0`, while `expected_utility_per_cost` discovers only `0.25`. The raw misses for the primary policy are `P1B-BUG-002`, `P1B-BUG-003`, and `P1B-BUG-004`, which suggests that exact-threshold and rounding-like cases can be missed when early evidence points away from a bug.

Clean false positives are not the current fragility driver. Every evaluated execution-grounded policy has `clean_false_positive_rate = 0.0`, and the primary policy has no `false_positive_clean_variant_ids`.

No execution-grounded policy has wrong-cause high-confidence variants in this report. The weakness is mostly missed discovery, late/penalized first failure, and poor localization/cause/fix-intent ranking in specific buckets, not confident wrong-cause stopping.

## Policy-Level Observations

| policy | average discovery | worst discovery bucket | key interpretation |
|---|---:|---|---|
| `random_action` | `0.40` | `boundary_precision`, `config_normalization` at `0.0` | Stochastic exploration sometimes reaches missing-input and spec cases, but it is unreliable and has the highest average first-failure cost. |
| `fixed_checklist` | `0.35` | `config_normalization`, `state_sequence` at `0.0` | Strong on boundary precision, weak when the relevant evidence is not on its early checklist path. |
| `test_first` | `0.35` | `config_normalization`, `state_sequence` at `0.0` | Same worst-case profile as fixed checklist in this report. |
| `coverage_first` | `0.35` | `config_normalization`, `state_sequence` at `0.0` | Similar to checklist/test-first, with slightly lower average mean cost but the same zero-discovery buckets. |
| `recent_diff_first` | `0.35` | `config_normalization`, `state_sequence` at `0.0` | Preserves location top-3 at `1.0` across all buggy buckets, but discovery, cause, and fix-intent still collapse in the hardest buckets. |
| `cause_only_p1a_style` | `0.40` | `state_sequence` at `0.0` | Looks competitive on average and avoids the config zero-discovery bucket, but still collapses on state-sequence cases. |
| `expected_utility_per_cost` | `0.40` | `state_sequence` at `0.0` | Current primary policy ties the best average discovery rate and average first-failure cost, but its hardest bucket is still a complete miss. |

`expected_utility_per_cost` is therefore not dominated by the simple baselines on average, but it is clearly brittle under bucket-level selection. Its average-versus-worst gaps are especially visible for location top-3 (`0.55`), cause top-1 (`0.55`), first-failure cost (`5.05`), and mean investigation cost (`5.11`).

`recent_diff_first` is the clearest example of a policy that can look excellent on one metric while failing on others. It has no location top-3 gap because its location top-3 accuracy is `1.0` even in the worst bucket, but it still has zero-discovery buckets and cause/fix-intent gaps.

## Candidate P1c2 Stress Directions

| candidate | support from P1c1 | main risk | priority |
|---|---|---|---|
| Adversarial bucket selection | Directly supported. P1c1 already shows that choosing `state_sequence` or `config_normalization` changes the policy ranking and exposes zero-discovery buckets. | Could become too close to the existing P1c1 report unless P1c2 specifies the chooser, allowed buckets, and decision rule clearly. | First |
| Bounded observation-cost stress | Supported by large mean-cost and first-failure-cost gaps, especially `expected_utility_per_cost` on `missing_optional_input` and `state_sequence`. | Requires specifying cost profiles without tuning P1b policy logic or implying a new payoff model. | Second |
| Observation dropout or delay | Supported indirectly by state-sequence misses and early no-bug stops, where decisive sequential evidence may not be reached. | More invasive than bucket selection because it perturbs observation availability and could drift toward a new execution harness. | Third |

Recommended next step: make P1c2 a specification-only design for adversarial bucket selection first. It is the closest continuation of the P1c1 evidence, can reuse existing variants and metrics, and keeps P1c2 from prematurely changing observation generation or policy scoring. A bounded observation-cost stress can be the next candidate after the bucket-selection rules are explicit.

## Non-Claims / Limitations

This note does not claim real-world debugging accuracy, production fault localization, automated repair, or a formal game-theoretic guarantee.

The report covers only 25 existing P1b variants. Each buggy bucket has four variants, so bucket-level results are useful as diagnostic signals but should not be generalized beyond this scaffold.

The results do not prove that a policy is globally robust or non-robust. They show which policies and buckets should be stress-specified next inside the current P1b/P1c boundary.

The `metadata_synth` diagnostic comparison is useful for seeing how metadata-derived evidence can make some metrics look better, such as higher cause or fix-intent accuracy in several buckets for `expected_utility_per_cost`. It should remain diagnostic because it depends on synthesized metadata rather than execution-grounded observations.
