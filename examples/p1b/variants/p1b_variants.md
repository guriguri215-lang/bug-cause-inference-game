# P1b Variants

| variant_id | is_buggy | cause_or_area | target_location | primary_action | difficulty |
|---|---:|---|---|---|---|
| P1B-BUG-001 | true | boundary_condition | shipping.free_shipping_eligible | run_boundary_tests | easy |
| P1B-BUG-002 | true | boundary_condition | discounts.coupon_is_eligible | run_boundary_tests | easy |
| P1B-BUG-003 | true | boundary_condition | cart.add_item | run_boundary_tests | medium |
| P1B-BUG-004 | true | boundary_condition | cart.calculate_tax | run_boundary_tests | hard |
| P1B-BUG-005 | true | missing_null_handling | discounts.apply_coupon | run_null_missing_tests | easy |
| P1B-BUG-006 | true | missing_null_handling | shipping.resolve_region_rate | run_null_missing_tests | easy |
| P1B-BUG-007 | true | missing_null_handling | cart.cart_subtotal | run_null_missing_tests | medium |
| P1B-BUG-008 | true | missing_null_handling | inventory.reserve_stock | run_null_missing_tests | medium |
| P1B-BUG-009 | true | configuration_environment | config.get_tax_rate | run_config_matrix_tests | medium |
| P1B-BUG-010 | true | configuration_environment | config.get_feature_flag | run_config_matrix_tests | medium |
| P1B-BUG-011 | true | configuration_environment | shipping.resolve_region_rate | run_config_matrix_tests | hard |
| P1B-BUG-012 | true | configuration_environment | config.load_config | run_config_matrix_tests | hard |
| P1B-BUG-013 | true | state_order_dependence | inventory.cancel_reservation | run_state_sequence_tests | easy |
| P1B-BUG-014 | true | state_order_dependence | discounts.apply_coupon | run_state_sequence_tests | medium |
| P1B-BUG-015 | true | state_order_dependence | inventory.sync_after_cart_update | run_state_sequence_tests | hard |
| P1B-BUG-016 | true | state_order_dependence | cart.checkout_quote | run_state_sequence_tests | hard |
| P1B-BUG-017 | true | specification_mismatch | cart.calculate_total | inspect_spec_clause | medium |
| P1B-BUG-018 | true | specification_mismatch | discounts.apply_bogo_discount | inspect_spec_clause | medium |
| P1B-BUG-019 | true | specification_mismatch | shipping.calculate_shipping | inspect_spec_clause | easy |
| P1B-BUG-020 | true | specification_mismatch | inventory.reserve_stock | inspect_spec_clause | hard |
| P1B-CLEAN-021 | false | Free-shipping and threshold pricing. |  |  |  |
| P1B-CLEAN-022 | false | Missing coupon and optional coupon fields. |  |  |  |
| P1B-CLEAN-023 | false | Conservative default feature flags. |  |  |  |
| P1B-CLEAN-024 | false | Inventory reserve/cancel/reserve state sequence. |  |  |  |
| P1B-CLEAN-025 | false | Tax, discount, and rounding interaction. |  |  |  |
