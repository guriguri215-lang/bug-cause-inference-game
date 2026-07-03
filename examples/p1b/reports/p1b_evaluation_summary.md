# P1b Evaluation Comparison

P1b is a small injected-bug benchmark scaffold. It does not generate patches,
handle large repositories, or implement adversarial bug generation.

Phase B compares the frozen `metadata_synth` baseline with `execution_grounded`
observations. Lower execution-grounded scores are diagnostic evidence about
metadata-synth optimism, not a B3 implementation failure.

## Dataset

- total_variants: 25
- buggy_variants: 20
- clean_variants: 5
- primary_policy: expected_utility_per_cost
- observation_mode: both
- compared_observation_modes: metadata_synth, execution_grounded

## Primary Policy Comparison

| metric | metadata_synth | execution_grounded | execution_minus_metadata_delta | metadata_optimism_gap |
|---|---:|---:|---:|---:|
| bug_discovery_rate_within_budget | 0.550000 | 0.400000 | -0.150000 | 0.150000 |
| false_positive_rate_on_clean_cases | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| location_top3_accuracy | 0.600000 | 0.550000 | -0.050000 | 0.050000 |
| cause_top1_accuracy | 0.800000 | 0.500000 | -0.300000 | 0.300000 |
| fix_intent_top1_accuracy | 0.750000 | 0.400000 | -0.350000 | 0.350000 |
| mean_investigation_cost | 2.800000 | 4.760000 | 1.960000 | 1.960000 |
| primary_vs_fixed_mean_cost_delta | 0.421488 | 0.137681 | -0.283807 | 0.283807 |

## Policy Metrics: metadata_synth

| policy | bug_discovery_rate | false_positive_rate | location_top3 | cause_top1 | fix_intent_top1 | mean_cost | mean_buggy_cost |
|---|---:|---:|---:|---:|---:|---:|---:|
| random_action | 0.500000 | 0.000000 | 0.900000 | 0.750000 | 0.650000 | 5.880000 | 6.050000 |
| fixed_checklist | 0.500000 | 0.000000 | 0.500000 | 0.650000 | 0.650000 | 4.840000 | 5.300000 |
| test_first | 0.500000 | 0.000000 | 0.500000 | 0.650000 | 0.650000 | 4.840000 | 5.300000 |
| coverage_first | 0.500000 | 0.000000 | 0.500000 | 0.650000 | 0.650000 | 5.360000 | 5.950000 |
| recent_diff_first | 0.300000 | 0.000000 | 1.000000 | 1.000000 | 1.000000 | 4.600000 | 5.000000 |
| cause_only_p1a_style | 0.550000 | 0.000000 | 0.600000 | 0.800000 | 0.750000 | 2.800000 | 3.000000 |
| expected_utility_per_cost | 0.550000 | 0.000000 | 0.600000 | 0.800000 | 0.750000 | 2.800000 | 3.000000 |

## Policy Metrics: execution_grounded

| policy | bug_discovery_rate | false_positive_rate | location_top3 | cause_top1 | fix_intent_top1 | mean_cost | mean_buggy_cost |
|---|---:|---:|---:|---:|---:|---:|---:|
| random_action | 0.400000 | 0.000000 | 0.550000 | 0.600000 | 0.450000 | 7.120000 | 7.600000 |
| fixed_checklist | 0.350000 | 0.000000 | 0.350000 | 0.350000 | 0.500000 | 5.520000 | 6.150000 |
| test_first | 0.350000 | 0.000000 | 0.350000 | 0.350000 | 0.500000 | 5.520000 | 6.150000 |
| coverage_first | 0.350000 | 0.000000 | 0.350000 | 0.350000 | 0.500000 | 5.360000 | 5.950000 |
| recent_diff_first | 0.350000 | 0.000000 | 0.350000 | 0.300000 | 0.500000 | 6.960000 | 7.450000 |
| cause_only_p1a_style | 0.400000 | 0.000000 | 0.500000 | 0.500000 | 0.400000 | 4.680000 | 5.350000 |
| expected_utility_per_cost | 0.400000 | 0.000000 | 0.550000 | 0.500000 | 0.400000 | 4.760000 | 5.450000 |

## Notes

- `execution_minus_metadata_delta` is `execution_grounded_value - metadata_synth_value`.
- `metadata_optimism_gap` is positive when `metadata_synth` made the primary policy look better than execution-grounded evidence. For lower-is-better metrics such as false-positive rate and mean cost, it is `execution_grounded_value - metadata_synth_value`; otherwise it is `metadata_synth_value - execution_grounded_value`.
- Failure cost for undiscovered buggy variants is `14`.
- Location metrics use function-level targets; line-span hints are secondary only.
- Execution-grounded mode builds test-action observations from checkout test results, exceptions, and traced checkout functions, not from variant cause/location/fix-intent labels.
- `inspect_coverage_spectrum` computes function-level Ochiai suspicion from cached passing/failing execution results.
- `inspect_recent_diff` remains a synthetic prior in Phase B; real git commit/diff artifacts are deferred to Phase C.
- All policies share the same stopping rules, so the comparison is primarily about action ordering.
- `run_property_search` uses deterministic enumerated cases, not randomized Hypothesis-style generation.
