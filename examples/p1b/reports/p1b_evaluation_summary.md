# P1b Evaluation Summary

P1b is a small injected-bug benchmark scaffold. It does not generate patches,
handle large repositories, or implement adversarial bug generation.

## Dataset

- total_variants: 25
- buggy_variants: 20
- clean_variants: 5
- primary_policy: expected_utility_per_cost

## Policy Metrics

| policy | bug_discovery_rate | false_positive_rate | location_top3 | cause_top1 | fix_intent_top1 | mean_cost |
|---|---:|---:|---:|---:|---:|---:|
| random_action | 0.500000 | 0.000000 | 0.900000 | 0.750000 | 0.650000 | 5.880000 |
| fixed_checklist | 0.500000 | 0.000000 | 0.500000 | 0.650000 | 0.650000 | 4.840000 |
| test_first | 0.500000 | 0.000000 | 0.500000 | 0.650000 | 0.650000 | 4.840000 |
| coverage_first | 0.500000 | 0.000000 | 0.500000 | 0.650000 | 0.650000 | 5.360000 |
| recent_diff_first | 0.300000 | 0.000000 | 1.000000 | 1.000000 | 1.000000 | 4.600000 |
| cause_only_p1a_style | 0.550000 | 0.000000 | 0.600000 | 0.800000 | 0.750000 | 2.800000 |
| expected_utility_per_cost | 0.550000 | 0.000000 | 0.600000 | 0.800000 | 0.750000 | 2.800000 |

## Success Checks

- primary_policy: expected_utility_per_cost
- primary_vs_fixed_mean_cost_delta: 0.421488
- primary_bug_discovery_rate_at_least_75_percent: False
- primary_clean_false_positive_rate_at_most_20_percent: True
- primary_location_top3_at_least_65_percent: False
- primary_cause_top1_at_least_60_percent: True

## Notes

- Failure cost for undiscovered buggy variants is `budget_limit + 2`.
- Location metrics use function-level targets; line-span hints are secondary only.
- `inspect_recent_diff` uses synthetic metadata, not real git commits or diffs.
- `run_property_search` uses deterministic enumerated cases, not randomized Hypothesis-style generation.
