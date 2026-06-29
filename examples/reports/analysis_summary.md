# P1a Analysis Summary

## Scope

- This is an analysis-only patch.
- The model, dataset, default thresholds, and main policy are unchanged.
- This report surfaces wrong stops, initially-wrong cases, stop reasons, category failures, and threshold-sweep tradeoffs.
- P1b/P1c features are not implemented here.

## Wrong-Stop Cases

| case_id | true_cause | policy | final_top_hypothesis | final_posterior_probability | top2_hypothesis | top1_top2_margin | cumulative_cost | current_step | stop_reason |
|---|---|---|---|---|---|---|---|---|---|
| BUG-0009 | boundary_condition | cheapest_first | specification_mismatch | 0.819395 | boundary_condition | 0.664717 | 10 | 5 | top_probability_threshold |
| BUG-0033 | race_order_dependence | cheapest_first | configuration_environment | 0.789067 | race_order_dependence | 0.604951 | 1 | 1 | top_probability_threshold |
| BUG-0035 | race_order_dependence | cheapest_first | configuration_environment | 0.789067 | race_order_dependence | 0.604951 | 1 | 1 | top_probability_threshold |
| BUG-0037 | race_order_dependence | cheapest_first | configuration_environment | 0.789067 | race_order_dependence | 0.604951 | 1 | 1 | top_probability_threshold |
| BUG-0039 | race_order_dependence | cheapest_first | configuration_environment | 0.785421 | race_order_dependence | 0.663244 | 3 | 2 | top_probability_threshold |
| BUG-0040 | race_order_dependence | cheapest_first | configuration_environment | 0.894423 | race_order_dependence | 0.852683 | 5 | 3 | top_probability_threshold |
| BUG-0033 | race_order_dependence | fixed_checklist | configuration_environment | 0.789067 | race_order_dependence | 0.604951 | 1 | 1 | top_probability_threshold |
| BUG-0035 | race_order_dependence | fixed_checklist | configuration_environment | 0.789067 | race_order_dependence | 0.604951 | 1 | 1 | top_probability_threshold |
| BUG-0037 | race_order_dependence | fixed_checklist | configuration_environment | 0.789067 | race_order_dependence | 0.604951 | 1 | 1 | top_probability_threshold |
| BUG-0039 | race_order_dependence | fixed_checklist | configuration_environment | 0.821854 | missing_null_handling | 0.682646 | 7 | 4 | top_probability_threshold |
| BUG-0040 | race_order_dependence | fixed_checklist | configuration_environment | 0.810911 | race_order_dependence | 0.703691 | 10 | 5 | top_probability_threshold |
| BUG-0009 | boundary_condition | information_gain | specification_mismatch | 0.885899 | boundary_condition | 0.798706 | 3 | 1 | top_probability_threshold |
| BUG-0010 | boundary_condition | information_gain | missing_null_handling | 0.911762 | boundary_condition | 0.863325 | 5 | 2 | top_probability_threshold |
| BUG-0023 | configuration_environment | information_gain | race_order_dependence | 0.760812 | configuration_environment | 0.530651 | 5 | 1 | top_probability_threshold |
| BUG-0025 | configuration_environment | information_gain | race_order_dependence | 0.760812 | configuration_environment | 0.530651 | 5 | 1 | top_probability_threshold |
| BUG-0027 | configuration_environment | information_gain | race_order_dependence | 0.760812 | configuration_environment | 0.530651 | 5 | 1 | top_probability_threshold |
| BUG-0009 | boundary_condition | information_gain_per_cost | specification_mismatch | 0.768579 | boundary_condition | 0.554248 | 5 | 2 | top_probability_threshold |
| BUG-0010 | boundary_condition | information_gain_per_cost | missing_null_handling | 0.847366 | boundary_condition | 0.764836 | 7 | 3 | top_probability_threshold |
| BUG-0033 | race_order_dependence | information_gain_per_cost | configuration_environment | 0.789067 | race_order_dependence | 0.604951 | 1 | 1 | top_probability_threshold |
| BUG-0035 | race_order_dependence | information_gain_per_cost | configuration_environment | 0.789067 | race_order_dependence | 0.604951 | 1 | 1 | top_probability_threshold |
| BUG-0037 | race_order_dependence | information_gain_per_cost | configuration_environment | 0.789067 | race_order_dependence | 0.604951 | 1 | 1 | top_probability_threshold |
| BUG-0039 | race_order_dependence | information_gain_per_cost | configuration_environment | 0.785421 | race_order_dependence | 0.663244 | 3 | 2 | top_probability_threshold |
| BUG-0004 | boundary_condition | posterior_greedy | specification_mismatch | 0.838897 | boundary_condition | 0.707305 | 3 | 1 | top_probability_threshold |
| BUG-0006 | boundary_condition | posterior_greedy | specification_mismatch | 0.838897 | boundary_condition | 0.707305 | 3 | 1 | top_probability_threshold |
| BUG-0008 | boundary_condition | posterior_greedy | specification_mismatch | 0.838897 | boundary_condition | 0.707305 | 3 | 1 | top_probability_threshold |
| BUG-0009 | boundary_condition | posterior_greedy | specification_mismatch | 0.885899 | boundary_condition | 0.798706 | 3 | 1 | top_probability_threshold |
| BUG-0010 | boundary_condition | posterior_greedy | missing_null_handling | 0.911762 | boundary_condition | 0.863325 | 5 | 2 | top_probability_threshold |
| BUG-0039 | race_order_dependence | posterior_greedy | configuration_environment | 0.785421 | race_order_dependence | 0.663244 | 3 | 2 | top_probability_threshold |
| BUG-0040 | race_order_dependence | posterior_greedy | configuration_environment | 0.801999 | specification_mismatch | 0.707506 | 8 | 4 | top_probability_threshold |
| BUG-0004 | boundary_condition | random | specification_mismatch | 0.838897 | boundary_condition | 0.707305 | 3 | 1 | top_probability_threshold |
| BUG-0006 | boundary_condition | random | specification_mismatch | 0.838897 | boundary_condition | 0.707305 | 3 | 1 | top_probability_threshold |
| BUG-0008 | boundary_condition | random | specification_mismatch | 0.838897 | boundary_condition | 0.707305 | 3 | 1 | top_probability_threshold |
| BUG-0009 | boundary_condition | random | specification_mismatch | 0.885899 | boundary_condition | 0.798706 | 3 | 1 | top_probability_threshold |

## Initially-Wrong Cases

| case_id | true_cause | initial_top_hypothesis | initial_top_probability | policy | final_top_hypothesis | final_top_probability | cost_to_true_cause_top1 | success_within_budget | stop_reason |
|---|---|---|---|---|---|---|---|---|---|
| BUG-0004 | boundary_condition | specification_mismatch | 0.528497 | cheapest_first | specification_mismatch | 0.748761 | 7 | True | budget_limit |
| BUG-0004 | boundary_condition | specification_mismatch | 0.528497 | fixed_checklist | boundary_condition | 0.664835 | 5 | True | budget_limit |
| BUG-0004 | boundary_condition | specification_mismatch | 0.528497 | information_gain | specification_mismatch | 0.721167 | 2 | True | low_expected_information_gain |
| BUG-0004 | boundary_condition | specification_mismatch | 0.528497 | information_gain_per_cost | specification_mismatch | 0.721167 | 2 | True | low_expected_information_gain |
| BUG-0004 | boundary_condition | specification_mismatch | 0.528497 | posterior_greedy | specification_mismatch | 0.838897 | 12 | False | top_probability_threshold |
| BUG-0004 | boundary_condition | specification_mismatch | 0.528497 | random | specification_mismatch | 0.838897 | 12 | False | top_probability_threshold |
| BUG-0004 | boundary_condition | specification_mismatch | 0.528497 | static_posterior | specification_mismatch | 0.528497 | 12 | False | static_posterior_no_investigation |
| BUG-0006 | boundary_condition | specification_mismatch | 0.528497 | cheapest_first | specification_mismatch | 0.748761 | 7 | True | budget_limit |
| BUG-0006 | boundary_condition | specification_mismatch | 0.528497 | fixed_checklist | boundary_condition | 0.664835 | 5 | True | budget_limit |
| BUG-0006 | boundary_condition | specification_mismatch | 0.528497 | information_gain | specification_mismatch | 0.721167 | 2 | True | low_expected_information_gain |
| BUG-0006 | boundary_condition | specification_mismatch | 0.528497 | information_gain_per_cost | specification_mismatch | 0.721167 | 2 | True | low_expected_information_gain |
| BUG-0006 | boundary_condition | specification_mismatch | 0.528497 | posterior_greedy | specification_mismatch | 0.838897 | 12 | False | top_probability_threshold |
| BUG-0006 | boundary_condition | specification_mismatch | 0.528497 | random | specification_mismatch | 0.838897 | 12 | False | top_probability_threshold |
| BUG-0006 | boundary_condition | specification_mismatch | 0.528497 | static_posterior | specification_mismatch | 0.528497 | 12 | False | static_posterior_no_investigation |
| BUG-0008 | boundary_condition | specification_mismatch | 0.528497 | cheapest_first | specification_mismatch | 0.748761 | 7 | True | budget_limit |
| BUG-0008 | boundary_condition | specification_mismatch | 0.528497 | fixed_checklist | boundary_condition | 0.664835 | 5 | True | budget_limit |
| BUG-0008 | boundary_condition | specification_mismatch | 0.528497 | information_gain | specification_mismatch | 0.721167 | 2 | True | low_expected_information_gain |
| BUG-0008 | boundary_condition | specification_mismatch | 0.528497 | information_gain_per_cost | specification_mismatch | 0.721167 | 2 | True | low_expected_information_gain |
| BUG-0008 | boundary_condition | specification_mismatch | 0.528497 | posterior_greedy | specification_mismatch | 0.838897 | 12 | False | top_probability_threshold |
| BUG-0008 | boundary_condition | specification_mismatch | 0.528497 | random | specification_mismatch | 0.838897 | 12 | False | top_probability_threshold |
| BUG-0008 | boundary_condition | specification_mismatch | 0.528497 | static_posterior | specification_mismatch | 0.528497 | 12 | False | static_posterior_no_investigation |
| BUG-0009 | boundary_condition | specification_mismatch | 0.621951 | cheapest_first | specification_mismatch | 0.819395 | 12 | False | top_probability_threshold |
| BUG-0009 | boundary_condition | specification_mismatch | 0.621951 | fixed_checklist | boundary_condition | 0.556895 | 10 | True | budget_limit |
| BUG-0009 | boundary_condition | specification_mismatch | 0.621951 | information_gain | specification_mismatch | 0.885899 | 12 | False | top_probability_threshold |
| BUG-0009 | boundary_condition | specification_mismatch | 0.621951 | information_gain_per_cost | specification_mismatch | 0.768579 | 2 | True | top_probability_threshold |
| BUG-0009 | boundary_condition | specification_mismatch | 0.621951 | posterior_greedy | specification_mismatch | 0.885899 | 12 | False | top_probability_threshold |
| BUG-0009 | boundary_condition | specification_mismatch | 0.621951 | random | specification_mismatch | 0.885899 | 12 | False | top_probability_threshold |
| BUG-0009 | boundary_condition | specification_mismatch | 0.621951 | static_posterior | specification_mismatch | 0.621951 | 12 | False | static_posterior_no_investigation |
| BUG-0010 | boundary_condition | missing_null_handling | 0.421053 | cheapest_first | boundary_condition | 0.390478 | 7 | True | budget_limit |
| BUG-0010 | boundary_condition | missing_null_handling | 0.421053 | fixed_checklist | boundary_condition | 0.683075 | 5 | True | budget_limit |
| BUG-0010 | boundary_condition | missing_null_handling | 0.421053 | information_gain | missing_null_handling | 0.911762 | 12 | False | top_probability_threshold |
| BUG-0010 | boundary_condition | missing_null_handling | 0.421053 | information_gain_per_cost | missing_null_handling | 0.847366 | 12 | False | top_probability_threshold |
| BUG-0010 | boundary_condition | missing_null_handling | 0.421053 | posterior_greedy | missing_null_handling | 0.911762 | 12 | False | top_probability_threshold |
| BUG-0010 | boundary_condition | missing_null_handling | 0.421053 | random | specification_mismatch | 0.591085 | 12 | False | budget_limit |
| BUG-0010 | boundary_condition | missing_null_handling | 0.421053 | static_posterior | missing_null_handling | 0.421053 | 12 | False | static_posterior_no_investigation |
| BUG-0020 | missing_null_handling | configuration_environment | 0.493151 | cheapest_first | missing_null_handling | 0.868943 | 1 | True | top_probability_threshold |
| BUG-0020 | missing_null_handling | configuration_environment | 0.493151 | fixed_checklist | missing_null_handling | 0.921643 | 1 | True | top_probability_threshold |
| BUG-0020 | missing_null_handling | configuration_environment | 0.493151 | information_gain | missing_null_handling | 0.868943 | 3 | True | top_probability_threshold |
| BUG-0020 | missing_null_handling | configuration_environment | 0.493151 | information_gain_per_cost | missing_null_handling | 0.921643 | 1 | True | top_probability_threshold |
| BUG-0020 | missing_null_handling | configuration_environment | 0.493151 | posterior_greedy | missing_null_handling | 0.868943 | 3 | True | top_probability_threshold |
| BUG-0020 | missing_null_handling | configuration_environment | 0.493151 | random | missing_null_handling | 0.663658 | 3 | True | budget_limit |
| BUG-0020 | missing_null_handling | configuration_environment | 0.493151 | static_posterior | configuration_environment | 0.493151 | 12 | False | static_posterior_no_investigation |
| BUG-0023 | configuration_environment | race_order_dependence | 0.51073 | cheapest_first | configuration_environment | 0.789067 | 1 | True | top_probability_threshold |
| BUG-0023 | configuration_environment | race_order_dependence | 0.51073 | fixed_checklist | configuration_environment | 0.789067 | 1 | True | top_probability_threshold |
| BUG-0023 | configuration_environment | race_order_dependence | 0.51073 | information_gain | race_order_dependence | 0.760812 | 12 | False | top_probability_threshold |
| BUG-0023 | configuration_environment | race_order_dependence | 0.51073 | information_gain_per_cost | configuration_environment | 0.789067 | 1 | True | top_probability_threshold |
| BUG-0023 | configuration_environment | race_order_dependence | 0.51073 | posterior_greedy | configuration_environment | 0.902081 | 3 | True | top_probability_threshold |
| BUG-0023 | configuration_environment | race_order_dependence | 0.51073 | random | configuration_environment | 0.678225 | 3 | True | budget_limit |
| BUG-0023 | configuration_environment | race_order_dependence | 0.51073 | static_posterior | race_order_dependence | 0.51073 | 12 | False | static_posterior_no_investigation |
| BUG-0025 | configuration_environment | race_order_dependence | 0.51073 | cheapest_first | configuration_environment | 0.789067 | 1 | True | top_probability_threshold |
| BUG-0025 | configuration_environment | race_order_dependence | 0.51073 | fixed_checklist | configuration_environment | 0.789067 | 1 | True | top_probability_threshold |
| BUG-0025 | configuration_environment | race_order_dependence | 0.51073 | information_gain | race_order_dependence | 0.760812 | 12 | False | top_probability_threshold |
| BUG-0025 | configuration_environment | race_order_dependence | 0.51073 | information_gain_per_cost | configuration_environment | 0.789067 | 1 | True | top_probability_threshold |
| BUG-0025 | configuration_environment | race_order_dependence | 0.51073 | posterior_greedy | configuration_environment | 0.902081 | 3 | True | top_probability_threshold |
| BUG-0025 | configuration_environment | race_order_dependence | 0.51073 | random | configuration_environment | 0.678225 | 3 | True | budget_limit |
| BUG-0025 | configuration_environment | race_order_dependence | 0.51073 | static_posterior | race_order_dependence | 0.51073 | 12 | False | static_posterior_no_investigation |
| BUG-0027 | configuration_environment | race_order_dependence | 0.51073 | cheapest_first | configuration_environment | 0.789067 | 1 | True | top_probability_threshold |
| BUG-0027 | configuration_environment | race_order_dependence | 0.51073 | fixed_checklist | configuration_environment | 0.789067 | 1 | True | top_probability_threshold |
| BUG-0027 | configuration_environment | race_order_dependence | 0.51073 | information_gain | race_order_dependence | 0.760812 | 12 | False | top_probability_threshold |
| BUG-0027 | configuration_environment | race_order_dependence | 0.51073 | information_gain_per_cost | configuration_environment | 0.789067 | 1 | True | top_probability_threshold |
| BUG-0027 | configuration_environment | race_order_dependence | 0.51073 | posterior_greedy | configuration_environment | 0.902081 | 3 | True | top_probability_threshold |
| BUG-0027 | configuration_environment | race_order_dependence | 0.51073 | random | configuration_environment | 0.678225 | 3 | True | budget_limit |
| BUG-0027 | configuration_environment | race_order_dependence | 0.51073 | static_posterior | race_order_dependence | 0.51073 | 12 | False | static_posterior_no_investigation |
| BUG-0039 | race_order_dependence | missing_null_handling | 0.354167 | cheapest_first | configuration_environment | 0.785421 | 12 | False | top_probability_threshold |
| BUG-0039 | race_order_dependence | missing_null_handling | 0.354167 | fixed_checklist | configuration_environment | 0.821854 | 12 | False | top_probability_threshold |
| BUG-0039 | race_order_dependence | missing_null_handling | 0.354167 | information_gain | race_order_dependence | 0.933853 | 5 | True | top_probability_threshold |
| BUG-0039 | race_order_dependence | missing_null_handling | 0.354167 | information_gain_per_cost | configuration_environment | 0.785421 | 12 | False | top_probability_threshold |
| BUG-0039 | race_order_dependence | missing_null_handling | 0.354167 | posterior_greedy | configuration_environment | 0.785421 | 12 | False | top_probability_threshold |
| BUG-0039 | race_order_dependence | missing_null_handling | 0.354167 | random | missing_null_handling | 0.351378 | 8 | True | budget_limit |
| BUG-0039 | race_order_dependence | missing_null_handling | 0.354167 | static_posterior | missing_null_handling | 0.354167 | 12 | False | static_posterior_no_investigation |
| BUG-0040 | race_order_dependence | specification_mismatch | 0.286765 | cheapest_first | configuration_environment | 0.894423 | 12 | False | top_probability_threshold |
| BUG-0040 | race_order_dependence | specification_mismatch | 0.286765 | fixed_checklist | configuration_environment | 0.810911 | 12 | False | top_probability_threshold |
| BUG-0040 | race_order_dependence | specification_mismatch | 0.286765 | information_gain | race_order_dependence | 0.922283 | 5 | True | top_probability_threshold |
| BUG-0040 | race_order_dependence | specification_mismatch | 0.286765 | information_gain_per_cost | specification_mismatch | 0.498035 | 12 | False | low_expected_information_gain |
| BUG-0040 | race_order_dependence | specification_mismatch | 0.286765 | posterior_greedy | configuration_environment | 0.801999 | 12 | False | top_probability_threshold |
| BUG-0040 | race_order_dependence | specification_mismatch | 0.286765 | random | specification_mismatch | 0.376532 | 12 | False | budget_limit |
| BUG-0040 | race_order_dependence | specification_mismatch | 0.286765 | static_posterior | specification_mismatch | 0.286765 | 12 | False | static_posterior_no_investigation |
| BUG-0044 | specification_mismatch | boundary_condition | 0.613115 | cheapest_first | specification_mismatch | 0.901419 | 7 | True | top_probability_threshold |
| BUG-0044 | specification_mismatch | boundary_condition | 0.613115 | fixed_checklist | specification_mismatch | 0.568097 | 5 | True | budget_limit |
| BUG-0044 | specification_mismatch | boundary_condition | 0.613115 | information_gain | specification_mismatch | 0.872233 | 2 | True | top_probability_threshold |
| BUG-0044 | specification_mismatch | boundary_condition | 0.613115 | information_gain_per_cost | specification_mismatch | 0.8943 | 2 | True | top_probability_threshold |
| BUG-0044 | specification_mismatch | boundary_condition | 0.613115 | posterior_greedy | specification_mismatch | 0.872233 | 2 | True | top_probability_threshold |
| BUG-0044 | specification_mismatch | boundary_condition | 0.613115 | random | specification_mismatch | 0.656686 | 3 | True | budget_limit |
| BUG-0044 | specification_mismatch | boundary_condition | 0.613115 | static_posterior | boundary_condition | 0.613115 | 12 | False | static_posterior_no_investigation |
| BUG-0046 | specification_mismatch | boundary_condition | 0.613115 | cheapest_first | specification_mismatch | 0.901419 | 7 | True | top_probability_threshold |
| BUG-0046 | specification_mismatch | boundary_condition | 0.613115 | fixed_checklist | specification_mismatch | 0.568097 | 5 | True | budget_limit |
| BUG-0046 | specification_mismatch | boundary_condition | 0.613115 | information_gain | specification_mismatch | 0.872233 | 2 | True | top_probability_threshold |
| BUG-0046 | specification_mismatch | boundary_condition | 0.613115 | information_gain_per_cost | specification_mismatch | 0.8943 | 2 | True | top_probability_threshold |
| BUG-0046 | specification_mismatch | boundary_condition | 0.613115 | posterior_greedy | specification_mismatch | 0.872233 | 2 | True | top_probability_threshold |
| BUG-0046 | specification_mismatch | boundary_condition | 0.613115 | random | specification_mismatch | 0.656686 | 3 | True | budget_limit |
| BUG-0046 | specification_mismatch | boundary_condition | 0.613115 | static_posterior | boundary_condition | 0.613115 | 12 | False | static_posterior_no_investigation |
| BUG-0048 | specification_mismatch | boundary_condition | 0.613115 | cheapest_first | specification_mismatch | 0.901419 | 7 | True | top_probability_threshold |
| BUG-0048 | specification_mismatch | boundary_condition | 0.613115 | fixed_checklist | specification_mismatch | 0.568097 | 5 | True | budget_limit |
| BUG-0048 | specification_mismatch | boundary_condition | 0.613115 | information_gain | specification_mismatch | 0.872233 | 2 | True | top_probability_threshold |
| BUG-0048 | specification_mismatch | boundary_condition | 0.613115 | information_gain_per_cost | specification_mismatch | 0.8943 | 2 | True | top_probability_threshold |
| BUG-0048 | specification_mismatch | boundary_condition | 0.613115 | posterior_greedy | specification_mismatch | 0.872233 | 2 | True | top_probability_threshold |
| BUG-0048 | specification_mismatch | boundary_condition | 0.613115 | random | specification_mismatch | 0.656686 | 3 | True | budget_limit |
| BUG-0048 | specification_mismatch | boundary_condition | 0.613115 | static_posterior | boundary_condition | 0.613115 | 12 | False | static_posterior_no_investigation |
| BUG-0050 | specification_mismatch | boundary_condition | 0.613115 | cheapest_first | specification_mismatch | 0.901419 | 7 | True | top_probability_threshold |
| BUG-0050 | specification_mismatch | boundary_condition | 0.613115 | fixed_checklist | specification_mismatch | 0.568097 | 5 | True | budget_limit |
| BUG-0050 | specification_mismatch | boundary_condition | 0.613115 | information_gain | specification_mismatch | 0.872233 | 2 | True | top_probability_threshold |
| BUG-0050 | specification_mismatch | boundary_condition | 0.613115 | information_gain_per_cost | specification_mismatch | 0.8943 | 2 | True | top_probability_threshold |
| BUG-0050 | specification_mismatch | boundary_condition | 0.613115 | posterior_greedy | specification_mismatch | 0.872233 | 2 | True | top_probability_threshold |
| BUG-0050 | specification_mismatch | boundary_condition | 0.613115 | random | specification_mismatch | 0.656686 | 3 | True | budget_limit |
| BUG-0050 | specification_mismatch | boundary_condition | 0.613115 | static_posterior | boundary_condition | 0.613115 | 12 | False | static_posterior_no_investigation |

## Stop Reason Summary

| policy | stop_reason | count | rate | wrong_stop_count | wrong_stop_rate_within_reason |
|---|---|---|---|---|---|
| cheapest_first | budget_limit | 7 | 0.14 | 0 | 0.0 |
| cheapest_first | top_probability_threshold | 43 | 0.86 | 6 | 0.139535 |
| fixed_checklist | budget_limit | 9 | 0.18 | 0 | 0.0 |
| fixed_checklist | top_probability_threshold | 41 | 0.82 | 5 | 0.121951 |
| information_gain | low_expected_information_gain | 3 | 0.06 | 0 | 0.0 |
| information_gain | top_probability_threshold | 47 | 0.94 | 5 | 0.106383 |
| information_gain_per_cost | low_expected_information_gain | 4 | 0.08 | 0 | 0.0 |
| information_gain_per_cost | top_probability_threshold | 46 | 0.92 | 6 | 0.130435 |
| posterior_greedy | top_probability_threshold | 50 | 1.0 | 7 | 0.14 |
| random | budget_limit | 24 | 0.48 | 0 | 0.0 |
| random | low_expected_information_gain | 3 | 0.06 | 0 | 0.0 |
| random | top_probability_threshold | 23 | 0.46 | 4 | 0.173913 |
| static_posterior | static_posterior_no_investigation | 50 | 1.0 | 0 | 0.0 |

## Category Failure Summary

| policy | true_cause | num_cases | mean_cost_to_true_cause_top1 | success_rate_within_budget | wrong_stop_rate | initially_wrong_success_rate |
|---|---|---|---|---|---|---|
| cheapest_first | boundary_condition | 10 | 4 | 0.9 | 0.333333 | 0.8 |
| cheapest_first | configuration_environment | 10 | 0.3 | 1.0 | 0.0 | 1.0 |
| cheapest_first | missing_null_handling | 10 | 0.1 | 1.0 | 0.0 | 1.0 |
| cheapest_first | race_order_dependence | 10 | 2.4 | 0.8 | 0.5 | 0.0 |
| cheapest_first | specification_mismatch | 10 | 2.8 | 1.0 | 0.0 | 1.0 |
| fixed_checklist | boundary_condition | 10 | 3 | 1.0 | 0.0 | 1.0 |
| fixed_checklist | configuration_environment | 10 | 0.3 | 1.0 | 0.0 | 1.0 |
| fixed_checklist | missing_null_handling | 10 | 0.1 | 1.0 | 0.0 | 1.0 |
| fixed_checklist | race_order_dependence | 10 | 2.4 | 0.8 | 0.5 | 0.0 |
| fixed_checklist | specification_mismatch | 10 | 2 | 1.0 | 0.0 | 1.0 |
| information_gain | boundary_condition | 10 | 3 | 0.8 | 0.285714 | 0.6 |
| information_gain | configuration_environment | 10 | 3.6 | 0.7 | 0.3 | 0.0 |
| information_gain | missing_null_handling | 10 | 0.3 | 1.0 | 0.0 | 1.0 |
| information_gain | race_order_dependence | 10 | 1 | 1.0 | 0.0 | 1.0 |
| information_gain | specification_mismatch | 10 | 0.8 | 1.0 | 0.0 | 1.0 |
| information_gain_per_cost | boundary_condition | 10 | 2 | 0.9 | 0.285714 | 0.8 |
| information_gain_per_cost | configuration_environment | 10 | 0.3 | 1.0 | 0.0 | 1.0 |
| information_gain_per_cost | missing_null_handling | 10 | 0.1 | 1.0 | 0.0 | 1.0 |
| information_gain_per_cost | race_order_dependence | 10 | 2.4 | 0.8 | 0.444444 | 0.0 |
| information_gain_per_cost | specification_mismatch | 10 | 0.8 | 1.0 | 0.0 | 1.0 |
| posterior_greedy | boundary_condition | 10 | 6 | 0.5 | 0.5 | 0.0 |
| posterior_greedy | configuration_environment | 10 | 0.9 | 1.0 | 0.0 | 1.0 |
| posterior_greedy | missing_null_handling | 10 | 0.3 | 1.0 | 0.0 | 1.0 |
| posterior_greedy | race_order_dependence | 10 | 2.4 | 0.8 | 0.2 | 0.0 |
| posterior_greedy | specification_mismatch | 10 | 0.8 | 1.0 | 0.0 | 1.0 |
| random | boundary_condition | 10 | 6 | 0.5 | 1.0 | 0.0 |
| random | configuration_environment | 10 | 0.9 | 1.0 | 0.0 | 1.0 |
| random | missing_null_handling | 10 | 0.3 | 1.0 | 0.0 | 1.0 |
| random | race_order_dependence | 10 | 2 | 0.9 | 0.0 | 0.5 |
| random | specification_mismatch | 10 | 1.2 | 1.0 | 0.0 | 1.0 |
| static_posterior | boundary_condition | 10 | 6 | 0.5 | 0.0 | 0.0 |
| static_posterior | configuration_environment | 10 | 3.6 | 0.7 | 0.0 | 0.0 |
| static_posterior | missing_null_handling | 10 | 1.2 | 0.9 | 0.0 | 0.0 |
| static_posterior | race_order_dependence | 10 | 2.4 | 0.8 | 0.0 | 0.0 |
| static_posterior | specification_mismatch | 10 | 4.8 | 0.6 | 0.0 | 0.0 |

## Threshold Sweep

| policy | top_probability_threshold | top_margin_threshold | mean_cost_to_true_cause_top1 | success_rate_within_budget | wrong_stop_rate | initially_wrong_success_rate | initially_wrong_mean_cost |
|---|---|---|---|---|---|---|---|
| information_gain_per_cost | 0.7 | 0.1 | 1.12 | 0.94 | 0.183673 | 0.8 | 3.733333 |
| information_gain_per_cost | 0.7 | 0.15 | 1.12 | 0.94 | 0.183673 | 0.8 | 3.733333 |
| information_gain_per_cost | 0.7 | 0.2 | 1.12 | 0.94 | 0.183673 | 0.8 | 3.733333 |
| information_gain_per_cost | 0.7 | 0.25 | 1.12 | 0.94 | 0.183673 | 0.8 | 3.733333 |
| information_gain_per_cost | 0.75 | 0.1 | 1.12 | 0.94 | 0.130435 | 0.8 | 3.733333 |
| information_gain_per_cost | 0.75 | 0.15 | 1.12 | 0.94 | 0.130435 | 0.8 | 3.733333 |
| information_gain_per_cost | 0.75 | 0.2 | 1.12 | 0.94 | 0.130435 | 0.8 | 3.733333 |
| information_gain_per_cost | 0.75 | 0.25 | 1.12 | 0.94 | 0.130435 | 0.8 | 3.733333 |
| information_gain_per_cost | 0.8 | 0.1 | 1.12 | 0.94 | 0.130435 | 0.8 | 3.733333 |
| information_gain_per_cost | 0.8 | 0.15 | 1.12 | 0.94 | 0.130435 | 0.8 | 3.733333 |
| information_gain_per_cost | 0.8 | 0.2 | 1.12 | 0.94 | 0.130435 | 0.8 | 3.733333 |
| information_gain_per_cost | 0.8 | 0.25 | 1.12 | 0.94 | 0.130435 | 0.8 | 3.733333 |
| information_gain_per_cost | 0.85 | 0.1 | 1.12 | 0.94 | 0.090909 | 0.8 | 3.733333 |
| information_gain_per_cost | 0.85 | 0.15 | 1.12 | 0.94 | 0.090909 | 0.8 | 3.733333 |
| information_gain_per_cost | 0.85 | 0.2 | 1.12 | 0.94 | 0.090909 | 0.8 | 3.733333 |
| information_gain_per_cost | 0.85 | 0.25 | 1.12 | 0.94 | 0.090909 | 0.8 | 3.733333 |
| information_gain_per_cost | 0.9 | 0.1 | 1.12 | 0.94 | 0.108108 | 0.8 | 3.733333 |
| information_gain_per_cost | 0.9 | 0.15 | 1.12 | 0.94 | 0.108108 | 0.8 | 3.733333 |
| information_gain_per_cost | 0.9 | 0.2 | 1.12 | 0.94 | 0.108108 | 0.8 | 3.733333 |
| information_gain_per_cost | 0.9 | 0.25 | 1.12 | 0.94 | 0.108108 | 0.8 | 3.733333 |
| fixed_checklist | 0.7 | 0.1 | 1.7 | 0.94 | 0.142857 | 0.8 | 5.666667 |
| fixed_checklist | 0.7 | 0.15 | 1.7 | 0.94 | 0.142857 | 0.8 | 5.666667 |
| fixed_checklist | 0.7 | 0.2 | 1.7 | 0.94 | 0.142857 | 0.8 | 5.666667 |
| fixed_checklist | 0.7 | 0.25 | 1.7 | 0.94 | 0.142857 | 0.8 | 5.666667 |
| fixed_checklist | 0.75 | 0.1 | 1.56 | 0.96 | 0.121951 | 0.866667 | 5.2 |
| fixed_checklist | 0.75 | 0.15 | 1.56 | 0.96 | 0.121951 | 0.866667 | 5.2 |
| fixed_checklist | 0.75 | 0.2 | 1.56 | 0.96 | 0.121951 | 0.866667 | 5.2 |
| fixed_checklist | 0.75 | 0.25 | 1.56 | 0.96 | 0.121951 | 0.866667 | 5.2 |
| fixed_checklist | 0.8 | 0.1 | 1.56 | 0.96 | 0.131579 | 0.866667 | 5.2 |
| fixed_checklist | 0.8 | 0.15 | 1.56 | 0.96 | 0.131579 | 0.866667 | 5.2 |
| fixed_checklist | 0.8 | 0.2 | 1.56 | 0.96 | 0.131579 | 0.866667 | 5.2 |
| fixed_checklist | 0.8 | 0.25 | 1.56 | 0.96 | 0.131579 | 0.866667 | 5.2 |
| fixed_checklist | 0.85 | 0.1 | 1.56 | 0.96 | 0.108108 | 0.866667 | 5.2 |
| fixed_checklist | 0.85 | 0.15 | 1.56 | 0.96 | 0.108108 | 0.866667 | 5.2 |
| fixed_checklist | 0.85 | 0.2 | 1.56 | 0.96 | 0.108108 | 0.866667 | 5.2 |
| fixed_checklist | 0.85 | 0.25 | 1.56 | 0.96 | 0.108108 | 0.866667 | 5.2 |
| fixed_checklist | 0.9 | 0.1 | 1.56 | 0.96 | 0.096774 | 0.866667 | 5.2 |
| fixed_checklist | 0.9 | 0.15 | 1.56 | 0.96 | 0.096774 | 0.866667 | 5.2 |
| fixed_checklist | 0.9 | 0.2 | 1.56 | 0.96 | 0.096774 | 0.866667 | 5.2 |
| fixed_checklist | 0.9 | 0.25 | 1.56 | 0.96 | 0.096774 | 0.866667 | 5.2 |

## Notes

- Wrong stop means a high-confidence stop on an incorrect top hypothesis.
- The threshold sweep is diagnostic only and does not change default thresholds.
- These results remain synthetic and should not be interpreted as real-world debugging accuracy.
