# Evaluation Summary

## Dataset Diagnostics

- case_count: 50
- initial_top1_accuracy: 0.700000
- initial_top2_accuracy: 1.000000
- initially_wrong_case_count: 15

## Policy Comparison

| policy | mean_cost_to_true_cause_top1 | success_rate_within_budget | brier_score | wrong_stop_rate |
|---|---:|---:|---:|---:|
| random | 2.048200 | 0.895200 | 0.314007 | 0.125520 |
| fixed_checklist | 1.560000 | 0.960000 | 0.214945 | 0.121951 |
| posterior_greedy | 2.080000 | 0.860000 | 0.248211 | 0.140000 |
| cheapest_first | 1.920000 | 0.940000 | 0.310989 | 0.139535 |
| information_gain | 1.740000 | 0.900000 | 0.230180 | 0.106383 |
| information_gain_per_cost | 1.120000 | 0.940000 | 0.276261 | 0.130435 |
| static_posterior | 3.600000 | 0.700000 | 0.392458 | 0.000000 |

## Initially Wrong Cases

| policy | num_runs | mean_cost_to_true_cause_top1 | success_rate_within_budget |
|---|---:|---:|---:|
| random | 1500 | 6.827333 | 0.650667 |
| fixed_checklist | 15 | 5.2 | 0.866667 |
| posterior_greedy | 15 | 6.933333 | 0.533333 |
| cheapest_first | 15 | 6.4 | 0.8 |
| information_gain | 15 | 5.8 | 0.666667 |
| information_gain_per_cost | 15 | 3.733333 | 0.8 |
| static_posterior | 15 | 12.0 | 0.0 |

## Success Checks

- primary_policy: information_gain_per_cost
- fixed_checklist_cost_reduction: 0.282051
- meets_15_percent_fixed_checklist_reduction: True
- posterior_greedy_mean_cost_delta: -0.96
- primary_success_rate_at_least_80_percent: True
- primary_wrong_stop_rate: 0.130435
- primary_wrong_stop_rate_under_10_percent_diagnostic: False

## Notes

- Failure to reach true-cause top-1 within budget is scored with the configured failure cost.
- Wrong stop rate means stopping on a high-confidence but incorrect cause hypothesis.
- The wrong-stop diagnostic threshold is surfaced as a caution signal, not as a hard validity claim.
- These results use synthetic cases and a fixed likelihood table.
