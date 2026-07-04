# P1b Report: P1B-BUG-001

## Summary

- policy: recent_diff_first
- observation_mode: execution_grounded
- is_buggy: True
- stop_reason: budget_limit
- bug_detected: True
- reproduction_input: checkout_quote one physical item at subtotal 10000, domestic address.
- cumulative_cost: 12
- current_step: 6
- true_cause_category: boundary_condition
- target_location: shipping.free_shipping_eligible
- fix_intent_category: change_comparison

## Location Ranking

| rank | location | probability |
|---:|---|---:|
| 1 | shipping.free_shipping_eligible | 0.291629 |
| 2 | config.get_shipping_threshold | 0.072907 |
| 3 | config.load_config | 0.072907 |
| 4 | cart.cart_subtotal | 0.040504 |
| 5 | cart.checkout_quote | 0.040504 |

## Cause Posterior

| rank | cause | probability |
|---:|---|---:|
| 1 | boundary_condition | 0.600000 |
| 2 | specification_mismatch | 0.200000 |
| 3 | configuration_environment | 0.066667 |
| 4 | missing_null_handling | 0.066667 |
| 5 | state_order_dependence | 0.066667 |

## Fix-Intent Prediction

| rank | fix_intent | probability |
|---:|---|---:|
| 1 | change_comparison | 0.409836 |
| 2 | add_missing_value_guard | 0.065574 |
| 3 | add_spec_exception_rule | 0.065574 |
| 4 | align_calculation_order_with_spec | 0.065574 |
| 5 | align_selection_rule_with_spec | 0.065574 |

## Executed Actions

- inspect_recent_diff
- run_smoke_tests
- run_boundary_tests
- run_config_matrix_tests
- run_null_missing_tests
- inspect_spec_clause

## Recent Diff Artifact

| step | patch | changed_files | changed_functions |
|---:|---|---|---|
| 1 | patches/P1B-BUG-001.patch | checkout/shipping.py | shipping.free_shipping_eligible |

### Diff Excerpt: Step 1

```diff
diff --git a/checkout/shipping.py b/checkout/shipping.py
--- a/checkout/shipping.py
+++ b/checkout/shipping.py
@@ -18,7 +18,7 @@ def free_shipping_eligible(subtotal: int, config: dict[str, Any]) -> bool:
     threshold = config_helpers.get_shipping_threshold(config)
-    return subtotal >= threshold
+    return subtotal > threshold
```

## Known Limits

- P1b is a small injected-bug benchmark scaffold, not a real-code production debugger.
- P1b ranks function-level locations; line spans are explanatory hints only.
- P1b predicts fix-intent categories but does not generate patches.
- P1b keeps metadata-synth recent-diff evidence synthetic; execution-grounded mode reads Phase C real-diff artifacts.
