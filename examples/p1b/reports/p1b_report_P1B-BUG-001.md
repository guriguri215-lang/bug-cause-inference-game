# P1b Report: P1B-BUG-001

## Summary

- policy: expected_utility_per_cost
- observation_mode: metadata_synth
- is_buggy: True
- stop_reason: bug_confidence_threshold
- bug_detected: True
- reproduction_input: Cart subtotal 10000, region domestic, no coupon.
- cumulative_cost: 6
- current_step: 4
- true_cause_category: boundary_condition
- target_location: shipping.free_shipping_eligible
- fix_intent_category: change_comparison

## Location Ranking

| rank | location | probability |
|---:|---|---:|
| 1 | shipping.free_shipping_eligible | 0.999572 |
| 2 | cart.cart_subtotal | 0.000037 |
| 3 | config.get_shipping_threshold | 0.000037 |
| 4 | cart.add_item | 0.000017 |
| 5 | cart.calculate_tax | 0.000017 |

## Cause Posterior

| rank | cause | probability |
|---:|---|---:|
| 1 | boundary_condition | 0.972339 |
| 2 | configuration_environment | 0.006915 |
| 3 | missing_null_handling | 0.006915 |
| 4 | specification_mismatch | 0.006915 |
| 5 | state_order_dependence | 0.006915 |

## Fix-Intent Prediction

| rank | fix_intent | probability |
|---:|---|---:|
| 1 | change_comparison | 0.988198 |
| 2 | add_missing_value_guard | 0.001311 |
| 3 | add_spec_exception_rule | 0.001311 |
| 4 | align_calculation_order_with_spec | 0.001311 |
| 5 | align_selection_rule_with_spec | 0.001311 |

## Executed Actions

- inspect_traceback
- run_smoke_tests
- inspect_recent_diff
- inspect_spec_clause

## Known Limits

- P1b is a small injected-bug benchmark scaffold, not a real-code production debugger.
- P1b ranks function-level locations; line spans are explanatory hints only.
- P1b predicts fix-intent categories but does not generate patches.
- P1b uses synthetic recent-diff metadata and structured coverage-like observations.
