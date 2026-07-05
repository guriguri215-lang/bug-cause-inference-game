# P1c0 Specification: Difficulty Labels And Worst-Case Metrics

Status: specification only. No code or dataset changes are included in this step.

P1c0 defines how a first P1c analysis report should label existing P1b variants and compute worst-case robustness metrics. It intentionally stays inside the current 25-variant injected checkout/pricing benchmark. It does not add new injected bugs, randomized input generation, patch generation, LLM agents, or a formal game-theoretic guarantee.

## Scope

P1c0 should use:

- The existing P1b variants from `load_p1b_variants()`.
- The existing P1b policies from `P1B_POLICIES`.
- The existing P1b settings from `P1BSettings`.
- The existing `execution_grounded` observation mode as the primary evaluation mode.
- The existing `metadata_synth` mode only as an optional diagnostic comparison.

P1c0 should not change:

- P1b variant source code.
- P1b real-diff artifacts.
- P1b policies, thresholds, costs, or scoring.
- P1b generated examples.
- README public claims.

## Policy Set

The first P1c0 report should compare the existing P1b policy set:

| policy | P1c0 role |
|---|---|
| `random_action` | seeded stochastic reference |
| `fixed_checklist` | deterministic checklist baseline |
| `test_first` | broad test-action baseline |
| `coverage_first` | localization-oriented baseline after discovery |
| `recent_diff_first` | diff-prior baseline |
| `cause_only_p1a_style` | cause-inference-biased baseline |
| `expected_utility_per_cost` | current P1b primary policy |

No new policy should be introduced in P1c0.

## Primary Buckets

Primary buckets are coarse and deliberately reuse the existing P1b structure. The goal is robustness reporting, not a new benchmark taxonomy.

| bucket | variants | purpose |
|---|---|---|
| `boundary_precision` | `P1B-BUG-001` to `P1B-BUG-004` | Tests exact thresholds, upper bounds, and rounding edge cases. |
| `missing_optional_input` | `P1B-BUG-005` to `P1B-BUG-008` | Tests absent values, missing keys, and optional fields. |
| `config_normalization` | `P1B-BUG-009` to `P1B-BUG-012` | Tests missing config defaults, aliases, flags, and type normalization. |
| `state_sequence` | `P1B-BUG-013` to `P1B-BUG-016` | Tests operation order, idempotence, stale state, and reservation transitions. |
| `spec_semantics` | `P1B-BUG-017` to `P1B-BUG-020` | Tests calculation order, selection rules, and documented exception rules. |
| `clean_false_positive` | `P1B-CLEAN-021` to `P1B-CLEAN-025` | Tests whether policies over-report bugs on clean but confusing cases. |

The first implementation should compute bucket metrics only for these six buckets. Finer labels may be emitted as metadata, but they should not be used as headline metrics until the benchmark is larger.

## Variant Labels

Each variant gets one primary bucket and zero or more stress labels. Stress labels are explanatory only in P1c0.

| variant_id | primary_bucket | existing_difficulty | stress_labels | rationale |
|---|---|---|---|---|
| `P1B-BUG-001` | `boundary_precision` | easy | `exact_threshold`, `shipping_boundary` | Threshold equality should be caught by boundary tests. |
| `P1B-BUG-002` | `boundary_precision` | easy | `exact_threshold`, `coupon_boundary` | Minimum-spend equality should be caught by boundary tests. |
| `P1B-BUG-003` | `boundary_precision` | medium | `upper_boundary`, `input_validation` | Upper bound is valid but may look like validation failure. |
| `P1B-BUG-004` | `boundary_precision` | hard | `rounding_precision`, `small_numeric_delta` | One-yen rounding errors are easy to miss or mis-rank. |
| `P1B-BUG-005` | `missing_optional_input` | easy | `missing_optional_value`, `exception_trace` | Missing coupon produces a direct exception signal. |
| `P1B-BUG-006` | `missing_optional_input` | easy | `missing_payload_key`, `default_fallback` | Missing region should fall back to domestic defaults. |
| `P1B-BUG-007` | `missing_optional_input` | medium | `missing_collection`, `exception_trace` | `items=None` resembles an empty-cart edge case. |
| `P1B-BUG-008` | `missing_optional_input` | medium | `missing_record_field`, `inventory_only` | Missing `reserved` is local to inventory data shape. |
| `P1B-BUG-009` | `config_normalization` | medium | `missing_config_default`, `stale_default` | Absent tax config falls back to a stale value. |
| `P1B-BUG-010` | `config_normalization` | medium | `missing_feature_flag`, `semantic_default` | Conservative feature-flag default is reversed. |
| `P1B-BUG-011` | `config_normalization` | hard | `alias_normalization`, `region_edge_case` | Alias handling can be confused with normal region behavior. |
| `P1B-BUG-012` | `config_normalization` | hard | `type_normalization`, `exception_trace` | String override causes a type error during comparison. |
| `P1B-BUG-013` | `state_sequence` | easy | `state_reversal`, `single_sequence` | Cancel should reverse reservation state. |
| `P1B-BUG-014` | `state_sequence` | medium | `idempotence`, `repeated_operation` | Repeated coupon application creates duplicate state. |
| `P1B-BUG-015` | `state_sequence` | hard | `stale_reservation`, `coverage_ambiguity` | Cart removal and inventory sync interact across functions. |
| `P1B-BUG-016` | `state_sequence` | hard | `stale_quote`, `cross_module_state` | Quote state can become stale across cart, shipping, and discounts. |
| `P1B-BUG-017` | `spec_semantics` | medium | `calculation_order`, `tax_discount_order` | Spec says discount before tax. |
| `P1B-BUG-018` | `spec_semantics` | medium | `selection_rule`, `bogo_semantics` | BOGO chooses the wrong eligible item. |
| `P1B-BUG-019` | `spec_semantics` | easy | `spec_exception`, `digital_only_shipping` | Digital-only carts should bypass shipping. |
| `P1B-BUG-020` | `spec_semantics` | hard | `spec_exception`, `state_spec_overlap` | Preorder behavior can look like stock-state failure. |
| `P1B-CLEAN-021` | `clean_false_positive` | n/a | `clean_boundary`, `recent_diff_distractor` | Boundary and recent-diff signals are present but correct. |
| `P1B-CLEAN-022` | `clean_false_positive` | n/a | `clean_null_missing`, `near_buggy_area` | Null/missing behavior is correct in a module with buggy neighbors. |
| `P1B-CLEAN-023` | `clean_false_positive` | n/a | `clean_config`, `documented_behavior_change` | Config differences may look like environment bugs. |
| `P1B-CLEAN-024` | `clean_false_positive` | n/a | `clean_state_sequence`, `trace_noise` | Multi-step traces are noisy but invariant-preserving. |
| `P1B-CLEAN-025` | `clean_false_positive` | n/a | `clean_rounding`, `intermediate_numeric_noise` | Intermediate rounding values are confusing but final totals are correct. |

## Per-Variant Outcomes

P1c0 should derive outcomes from existing `P1BRunResult` fields.

For buggy variants:

- `discovered_within_budget`: `bug_detected` and `cumulative_cost <= settings.budget_limit`.
- `first_failure_cost_penalized`: `first_failure_cost` if present, otherwise `settings.failure_cost`.
- `location_top1_hit`: target function rank is 1.
- `location_top3_hit`: target function rank is at most 3.
- `cause_top1_hit`: true cause category is ranked first.
- `cause_top2_hit`: true cause category is ranked in the top 2.
- `fix_intent_top1_hit`: true fix-intent category is ranked first.
- `fix_intent_top3_hit`: true fix-intent category is ranked in the top 3.
- `wrong_cause_high_confidence`: top cause probability is at least `settings.cause_top1_threshold` and the top cause is wrong.
- `investigation_cost`: `cumulative_cost`.

For clean variants:

- `false_positive`: stop reason is `bug_confidence_threshold` or final bug-presence posterior is at least `settings.bug_presence_threshold`.
- `clean_no_bug_stop`: stop reason is `no_bug_probability_threshold`.
- `clean_investigation_cost`: `cumulative_cost`.

## Worst-Case Metrics

P1c0 should report worst-case metrics at three levels: raw variant, primary bucket, and average-versus-worst gap.

### Raw Variant Worst Cases

For each policy:

- `missed_bug_variant_ids`: buggy variants where `discovered_within_budget` is false.
- `max_first_failure_cost_variant_ids`: buggy variants with the largest `first_failure_cost_penalized`.
- `location_top3_miss_variant_ids`: buggy variants where `location_top3_hit` is false.
- `cause_top1_miss_variant_ids`: buggy variants where `cause_top1_hit` is false.
- `fix_intent_top1_miss_variant_ids`: buggy variants where `fix_intent_top1_hit` is false.
- `wrong_cause_high_confidence_variant_ids`: buggy variants where `wrong_cause_high_confidence` is true.
- `false_positive_clean_variant_ids`: clean variants where `false_positive` is true.

Variant ID lists should be treated as diagnostic evidence, not as broad benchmark claims.

### Bucket Metrics

For each policy and bucket:

- `bucket_bug_discovery_rate`: buggy-only; omit or mark `n/a` for `clean_false_positive`.
- `bucket_cost_to_first_failure`: mean penalized first-failure cost for buggy variants.
- `bucket_location_top3_accuracy`: buggy-only.
- `bucket_cause_top1_accuracy`: buggy-only.
- `bucket_fix_intent_top1_accuracy`: buggy-only.
- `bucket_wrong_cause_high_confidence_rate`: buggy-only.
- `bucket_false_positive_rate`: clean-only; only meaningful for `clean_false_positive`.
- `bucket_mean_investigation_cost`: all variants in the bucket.

### Headline Worst-Case Summary

For each policy:

- `min_bucket_bug_discovery_rate`: minimum `bucket_bug_discovery_rate` over the five buggy buckets.
- `max_bucket_cost_to_first_failure`: maximum `bucket_cost_to_first_failure` over the five buggy buckets.
- `min_bucket_location_top3_accuracy`: minimum `bucket_location_top3_accuracy` over the five buggy buckets.
- `min_bucket_cause_top1_accuracy`: minimum `bucket_cause_top1_accuracy` over the five buggy buckets.
- `min_bucket_fix_intent_top1_accuracy`: minimum `bucket_fix_intent_top1_accuracy` over the five buggy buckets.
- `max_bucket_wrong_cause_high_confidence_rate`: maximum `bucket_wrong_cause_high_confidence_rate` over the five buggy buckets.
- `clean_false_positive_rate`: `bucket_false_positive_rate` for the `clean_false_positive` bucket.
- `max_bucket_mean_investigation_cost`: maximum `bucket_mean_investigation_cost` over all six buckets.

## Average-Versus-Worst Gap

P1c0 should show how much worse the hardest bucket is than the average P1b evaluation.

For higher-is-better rates:

```text
average_vs_worst_gap = average_metric - min_bucket_metric
```

For lower-is-better cost or error metrics:

```text
average_vs_worst_gap = max_bucket_metric - average_metric
```

The report should avoid a single weighted utility score in P1c0. Metric-specific gaps are more transparent and less likely to imply a formal payoff model.

## Observation Mode Contract

Primary P1c0 reporting should use `execution_grounded`.

`metadata_synth` may be reported in a secondary comparison section to show how a metadata-derived baseline behaves under the same bucket definitions. It should not be used as the headline robustness claim because it is intentionally optimistic and metadata-dependent.

## Stop Rules

Stop and return to design review if any P1c0 implementation would require:

- Adding new variants.
- Generating or committing source trees.
- Adding randomized fuzzing or property-based search.
- Changing policy scoring, thresholds, or action costs.
- Introducing a new adversarial policy.
- Using real repository histories.
- Generating patches.
- Introducing LLM agent evaluation.
- Claiming a minimax, equilibrium, regret, or game-theoretic guarantee.
- Reporting a headline metric that depends on fewer than three variants unless it is clearly marked as diagnostic.

## Acceptance Criteria

The P1c0 specification is ready for an implementation prompt when:

- The variant label table covers all 25 P1b variants.
- Every headline metric can be computed from existing `P1BRunResult` data.
- The primary observation mode is `execution_grounded`.
- `metadata_synth` is optional and clearly marked as diagnostic.
- There is no patch generation, new bug generation, LLM agent evaluation, or formal game-theoretic claim.
- The README boundary remains accurate without requiring immediate edits.

## Next Implementation Candidate

Implement a docs-linked, analysis-only P1c report that runs existing P1b policies on existing P1b variants, groups results by the primary buckets above, and emits JSON/Markdown summaries for worst-case and average-versus-worst metrics.
