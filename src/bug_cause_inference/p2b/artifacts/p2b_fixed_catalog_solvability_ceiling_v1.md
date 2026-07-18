# P2b Fixed-Catalog Solvability Ceiling

This is an analysis-only, ground-truth-informed, non-deployable diagnostic over the accepted fixed P2a catalog and cohort.

Validation status: `valid`.

## Fixed Inputs

- Buggy support: `10` accepted P2a variants.
- Frozen catalog: `24` cases applied to every buggy variant (`240` case evaluations).
- Fixed budget: `12`; formal policies: `6`.
- Saved accepted P2a policy outcomes were reused; policy and compatibility runners were not executed.

## Overall Diagnostic

- Catalog reachability: 10/10 (1).
- Ground-truth-informed ceiling discovery: 10/10 (1).
- Ceiling discovery loss: 0/10 (0).

## Variant Diagnostics

| Variant | Bucket | Detecting actions | Minimum cost | Budget feasible |
|---|---|---|---:|---|
| `P2A-BUG-001` | `boundary_precision` | `run_boundary_tests` | 2 | `true` |
| `P2A-BUG-002` | `boundary_precision` | `run_boundary_tests` | 2 | `true` |
| `P2A-BUG-003` | `missing_optional_input` | `run_null_missing_tests` | 2 | `true` |
| `P2A-BUG-004` | `missing_optional_input` | `run_null_missing_tests`, `run_config_matrix_tests` | 2 | `true` |
| `P2A-BUG-005` | `config_normalization` | `run_config_matrix_tests` | 3 | `true` |
| `P2A-BUG-006` | `config_normalization` | `run_config_matrix_tests` | 3 | `true` |
| `P2A-BUG-007` | `state_sequence` | `run_state_sequence_tests` | 4 | `true` |
| `P2A-BUG-008` | `state_sequence` | `run_state_sequence_tests` | 4 | `true` |
| `P2A-BUG-009` | `spec_semantics` | `inspect_spec_clause` | 2 | `true` |
| `P2A-BUG-010` | `spec_semantics` | `inspect_spec_clause` | 2 | `true` |

## Policy Comparison Boundary

`catalog_reachable_policy_missed` means only that a direct, one-step, budget-feasible frozen-catalog certificate exists while the saved fixed-policy trajectory missed. It is a selection/order/stop trajectory limitation under this fixed contract, not a causal policy-inferiority or implementation-defect claim.

The ceiling is not a seventh formal policy, deployable strategy, general upper bound, policy winner, minimax/Nash/regret result, or evidence of unseen-variant, second-domain, production, causal, or inferential performance.

## Canonical Validated Summary

<!-- P2B_VALIDATED_SUMMARY_BEGIN -->
```json
{
  "schema_version": "p2b_fixed_catalog_solvability_ceiling.v1",
  "analysis_phase": "p2b_fixed_catalog_solvability_ceiling",
  "report_role": "analysis_only_ground_truth_informed_non_deployable_diagnostic",
  "validation_status": {
    "status": "valid",
    "reason_codes": []
  },
  "input_identity": {
    "merged_base_commit": "536485d8ea042f4e84be1980ca5f54f343da18f2",
    "accepted_p2a_head": "2a2dcf05f98ab493c757f659c44b2248a3e3491f",
    "dataset_schema_version": "p2a_same_domain_dataset.v1",
    "benchmark_id": "p2a_checkout_pricing_same_domain_expansion_v1",
    "candidate_manifest_digest": "97c2d0c0379d69010195a4b7448137e566214d88638b0f7642ee59677389cd47",
    "artifact_manifest_digest": "674c3f56fbd2d4148a3e63367e4bba63ed7de634f5a219ec82a79a1c878a9544",
    "official_freeze_digest": "d335f3f3a4731ee0f4d9b4648e2085eb9c687b7b2a3065d2b08eb2f65370cd9d",
    "saved_outcome_snapshot_digest": "2a1b09b38de6b2e17943726508ebc1f6728290506165cfa263a78dbb57383755",
    "accepted_p2a_summary_digest": "3dea5aaf38e1d9a46fd1a9ed973cb02c3fabf7ec933f2bb1c6df4f97446a9629",
    "accepted_p2a_json_sha256": "d7e69fa62513f5bbae22d570e39b841401f5110b6cd1e45701c53393eb0ef3df",
    "accepted_p2a_markdown_sha256": "017c5e3d9281e59e0b115a825a5f0e08f90a5e15a1e331514296adf443a2808a",
    "dataset_counts": {
      "total": 15,
      "buggy": 10,
      "clean": 5
    },
    "catalog_case_count": 24,
    "legacy_compatibility": {
      "status": "valid",
      "expected_pair_count": 150,
      "observed_pair_count": 150,
      "matched_pair_count": 150,
      "mismatch_count": 0,
      "runtime_digest": "a7eede0058030e83b1552b71a83aff55596b16b03d05522e61375d32fa67987d",
      "catalog_digest": "a62d0c6a11ae5f57cffa572bd06277d863e52df6a5367235a6a804adc8bc01dd",
      "artifact_digest": "87f5fc00cde1cb8d02f4df7651b98c4e0e75ace833da82e256c29e1f90ad3d8c"
    },
    "accepted_file_sha256": {
      "p1b_actions_source": "dc738b403df5f43f39d3808d6f040548bc971821b71f98f6e629e54da5d6a9e4",
      "p1b_execution_source": "42dcd7f70041d2576c0c18d426ab933053aa5e560add34b9a2f561cb4e6caba1",
      "p1b_dataset_source": "80c22a16dfc6ab5afc368f6b581ba00542e735c815c8f7a65193a3c16aa709f4",
      "p1b_models_source": "5a851b136b99c27f7f63e8d5399c0de89a340f60ec1a3e581d5cece25a22cadb",
      "p1b_policies_source": "879b88693a9ad50c46d5395ee3a9bd7d35aa8520b7f75065414dc642f6aaef09",
      "p1b_real_diff_source": "a9b173e951af3685a58379e4fe05f5b775eb540950efbca2506ebdd19af55d72",
      "p2a_adequacy_source": "bdef79f373a6398fa6756f1b77661b4dbd394d5470ea5ca84b80e0286ea6d400",
      "p2a_candidate_authoring_source": "c5a8f6801901d535c2bbde61603aa4de66c9d6ccc2005c30e13592733ae46701",
      "p2a_candidate_oracles_source": "0361aefc33fd6a5d0be2dc8fc8e79e1ae290886568113f824598ccbe154c1732",
      "p2a_candidates_source": "47e0bfccff06819efc66384d9528be0828ca95943f63498bca1eb6aed68f6351",
      "p2a_freeze_realization_source": "a8c1dea78ad1e592c8823219aa3e074b3284ec48eac722bc7979d993ff04db1b",
      "p2a_evaluation_source": "02db9095416885f865229f13ba52d2c7e1d794fac07b5cc2e1651d6593866785",
      "p2a_reports_source": "51c5b873a5562badbb4bc5653686c4b94f3cd7f7f2d2f03f37482c11f6d16992",
      "p2a_authoring_manifest": "ccf05cd8c4179ee2b84b68dffa1d576e59f717e4fd314a4cccb0136d9ffb7e3b",
      "p2a_artifact_manifest": "ff519a4f5bd7985e0b8f3929fcaa0ded3bd98f742e52bb85d7866f21a2cf1b0d",
      "p2a_official_freeze_bundle": "8a5197288c60329af2667fba8c541edd39ccc068b3ecf6393afdaddf8ebdb5a4",
      "p2a_evaluation_json": "d7e69fa62513f5bbae22d570e39b841401f5110b6cd1e45701c53393eb0ef3df",
      "p2a_evaluation_markdown": "017c5e3d9281e59e0b115a825a5f0e08f90a5e15a1e331514296adf443a2808a",
      "p2a_candidate_patch_bug_001": "fb828c07825746dab12831dc90504b4471894e4d24ae5381425e26a60d56ecb1",
      "p2a_candidate_patch_bug_002": "57168b75361ff6ca8039aa41a0326edc0136758dabb78329f8ddc2eaf3a10cea",
      "p2a_candidate_patch_bug_003": "68cdd7a8b9d5e1f4fac818d16fdcb7d12c999d40e2bd480d4b962449740c4a92",
      "p2a_candidate_patch_bug_004": "62e7bc6bc3f9855299f7413d3530373f13008a6658682285dbb44af2bfe4a2cf",
      "p2a_candidate_patch_bug_005": "8bcbc4fcdccd41ffd92fe27fa25a8f6a0d95a66770832b779c35fa837d62c147",
      "p2a_candidate_patch_bug_006": "095a4ecc21fb5408aceaf62f009e113ccaecff1bd81a2455ab3665bb8ef0cc87",
      "p2a_candidate_patch_bug_007": "85646fa091547497bc12f523a4f6f95d6cda5d07f63ec7b66327cdeda77f2c6f",
      "p2a_candidate_patch_bug_008": "7c11b70025dcfdef22898103a8656f2d8afa6d492403ac24c52c075967cb374c",
      "p2a_candidate_patch_bug_009": "68903ccc686878bdae8b73489596978006c2a422ed6ac17bbbb5d7db88c45030",
      "p2a_candidate_patch_bug_010": "843ec18c88a2fcfd45e8ea7a04c4c5302472b9856cc3fe3a0c5b793672eeffd7",
      "p2a_candidate_patch_clean_001": "c0a1b7d75e313d91ec0653ddd361f926e1f69ad5025e78878e80aa114c8e3caa",
      "p2a_candidate_patch_clean_002": "ef17bf8a5eb330d52e7ef9b122c4b574b01141bf23d15b6bc90fefa25ddd39f1",
      "p2a_candidate_patch_clean_003": "2ab2975d1537a7ea841ca2744515020f12d914b8a88668c967bcd664d64adea9",
      "p2a_candidate_patch_clean_004": "eb614f960d83f19a7ddccfc4f7162397f008c42dd2e2089cb3c09753c468b65d",
      "p2a_candidate_patch_clean_005": "b78e400beeffcd5a9a9c84bf39c25f3b67a4b2c03eb41605700806b9331c8778",
      "p1b_baseline_checkout_init": "51e4a52ecf7e463802375a38d90ab015235d4d43ee11996b261cf73e3869e6a4",
      "p1b_baseline_checkout_cart": "b98ef7ea15d1df98c288f34656f15a5f7a0e156220d1fa8d38e5f9a7f44c8a41",
      "p1b_baseline_checkout_config": "d02a338aa03a432423621873d3ab6426fa089abcb18d65df182e92bb0cb022b0",
      "p1b_baseline_checkout_discounts": "6a31cb3088dfc26f14123ac84860a83f0860f5bbb142bfe725498f5e0d9e3565",
      "p1b_baseline_checkout_inventory": "9440765e4d993bef2f6dd4c60ddb9acc9f60eb5a1d9fc34b34c1b565399a48f2",
      "p1b_baseline_checkout_shipping": "ab3e80ee7a5e92d0150e13681bc9b4c36b4a0027b03d089f198e7a0d00863a7a"
    }
  },
  "execution_boundary": {
    "pre_diagnostic_gate_passed": true,
    "catalog_case_evaluation_count": 240,
    "expected_catalog_case_evaluation_count": 240,
    "policy_outcome_runner_executed": false,
    "compatibility_runner_executed": false,
    "p2a_evaluation_runner_executed": false,
    "first_execution": "P2A-BUG-001::P2A-BUG-001::boundary.quantity_zero_rejected",
    "summary_observed_event_ids": [
      "p2b_pre_diagnostic_gate_passed",
      "p2b_catalog_case_execution_started",
      "p2b_catalog_case_execution_completed"
    ],
    "required_post_summary_event_ids": [
      "p2b_summary_validated",
      "p2b_artifacts_serialized"
    ]
  },
  "dataset_summary": {
    "accepted_total_count": 15,
    "buggy_support_count": 10,
    "clean_identity_only_count": 5,
    "catalog_case_count": 24,
    "saved_policy_outcome_count": 60
  },
  "formal_policy_ids": [
    "fixed_checklist",
    "test_first",
    "coverage_first",
    "recent_diff_first",
    "cause_only_p1a_style",
    "expected_utility_per_cost"
  ],
  "excluded_policy_ids": [
    "random_action",
    "state_sequence_guard"
  ],
  "bucket_ids": [
    "boundary_precision",
    "missing_optional_input",
    "config_normalization",
    "state_sequence",
    "spec_semantics"
  ],
  "action_specs": [
    {
      "action_id": "run_smoke_tests",
      "cost": 1,
      "observation_type": "test_failure",
      "strong_causes": [
        "specification_mismatch",
        "missing_null_handling"
      ],
      "discovery_power": 0.45,
      "location_power": 0.25
    },
    {
      "action_id": "run_boundary_tests",
      "cost": 2,
      "observation_type": "boundary_counterexample",
      "strong_causes": [
        "boundary_condition"
      ],
      "discovery_power": 0.7,
      "location_power": 0.45
    },
    {
      "action_id": "run_null_missing_tests",
      "cost": 2,
      "observation_type": "exception_trace",
      "strong_causes": [
        "missing_null_handling"
      ],
      "discovery_power": 0.7,
      "location_power": 0.55
    },
    {
      "action_id": "run_config_matrix_tests",
      "cost": 3,
      "observation_type": "config_counterexample",
      "strong_causes": [
        "configuration_environment"
      ],
      "discovery_power": 0.7,
      "location_power": 0.45
    },
    {
      "action_id": "run_state_sequence_tests",
      "cost": 4,
      "observation_type": "state_sequence_counterexample",
      "strong_causes": [
        "state_order_dependence"
      ],
      "discovery_power": 0.75,
      "location_power": 0.55
    },
    {
      "action_id": "run_property_search",
      "cost": 5,
      "observation_type": "property_counterexample",
      "strong_causes": [
        "boundary_condition",
        "state_order_dependence",
        "specification_mismatch"
      ],
      "discovery_power": 0.65,
      "location_power": 0.35
    },
    {
      "action_id": "inspect_traceback",
      "cost": 1,
      "observation_type": "exception_trace",
      "strong_causes": [
        "missing_null_handling",
        "configuration_environment"
      ],
      "discovery_power": 0.3,
      "location_power": 0.7
    },
    {
      "action_id": "inspect_coverage_spectrum",
      "cost": 3,
      "observation_type": "coverage_suspicious_location",
      "strong_causes": [],
      "discovery_power": 0.15,
      "location_power": 0.85
    },
    {
      "action_id": "inspect_recent_diff",
      "cost": 2,
      "observation_type": "recent_diff_signal",
      "strong_causes": [
        "configuration_environment",
        "state_order_dependence",
        "boundary_condition"
      ],
      "discovery_power": 0.2,
      "location_power": 0.55
    },
    {
      "action_id": "inspect_spec_clause",
      "cost": 2,
      "observation_type": "spec_clause_mismatch",
      "strong_causes": [
        "specification_mismatch",
        "boundary_condition",
        "configuration_environment"
      ],
      "discovery_power": 0.45,
      "location_power": 0.5
    }
  ],
  "definitions": {
    "catalog_reachability": "at least one failed frozen catalog case mapped to an action",
    "budget_feasible_ceiling": "ground-truth-informed minimum-cost direct detecting action chosen at step one within budget",
    "policy_comparison": "saved accepted expansion-only outcome compared without policy rerun",
    "classification_boundary": "reachable policy miss means selection/order/stop trajectory limitation under the fixed contract"
  },
  "variant_diagnostics": [
    {
      "variant_id": "P2A-BUG-001",
      "bucket_id": "boundary_precision",
      "catalog_case_support_count": 24,
      "catalog_case_results": [
        {
          "case_id": "P2A-BUG-001::boundary.quantity_zero_rejected",
          "candidate_id": "P2A-BUG-001",
          "action_id": "run_boundary_tests",
          "passed": false
        },
        {
          "case_id": "P2A-BUG-002::boundary.quantity_over_max_rejected",
          "candidate_id": "P2A-BUG-002",
          "action_id": "run_boundary_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-003::missing.region_defaults_domestic",
          "candidate_id": "P2A-BUG-003",
          "action_id": "run_null_missing_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-004::missing.tax_rates_absent_us_zero",
          "candidate_id": "P2A-BUG-004",
          "action_id": "run_null_missing_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-005::config.explicit_fractional_tax_rate",
          "candidate_id": "P2A-BUG-005",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-006::config.threshold_override_exact_value",
          "candidate_id": "P2A-BUG-006",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-007::state.over_cancel_clamps_reserved_zero",
          "candidate_id": "P2A-BUG-007",
          "action_id": "run_state_sequence_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-008::state.coupon_preserves_unrelated_state",
          "candidate_id": "P2A-BUG-008",
          "action_id": "run_state_sequence_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-009::spec.unknown_region_uses_domestic_rate",
          "candidate_id": "P2A-BUG-009",
          "action_id": "inspect_spec_clause",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-010::spec.nonstacking_chooses_larger_discount",
          "candidate_id": "P2A-BUG-010",
          "action_id": "inspect_spec_clause",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-001::clean.boundary_max_accepted",
          "candidate_id": "P2A-CLEAN-001",
          "action_id": "run_boundary_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-001::clean.boundary_over_max_rejected",
          "candidate_id": "P2A-CLEAN-001",
          "action_id": "run_boundary_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-002::clean.optional_alias_copy_isolated",
          "candidate_id": "P2A-CLEAN-002",
          "action_id": "run_null_missing_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-002::clean.optional_aliases_absent_empty",
          "candidate_id": "P2A-CLEAN-002",
          "action_id": "run_null_missing_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-003::clean.config_absent_jp_fallback",
          "candidate_id": "P2A-CLEAN-003",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-003::clean.config_absent_us_fallback",
          "candidate_id": "P2A-CLEAN-003",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-003::clean.config_explicit_zero_rate",
          "candidate_id": "P2A-CLEAN-003",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-003::clean.config_present_none_jp_raises",
          "candidate_id": "P2A-CLEAN-003",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-003::clean.config_present_none_us_raises",
          "candidate_id": "P2A-CLEAN-003",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-003::clean.config_string_rate_equivalence",
          "candidate_id": "P2A-CLEAN-003",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-004::clean.state_coupon_idempotent",
          "candidate_id": "P2A-CLEAN-004",
          "action_id": "run_state_sequence_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-004::clean.state_coupon_preserves_session",
          "candidate_id": "P2A-CLEAN-004",
          "action_id": "run_state_sequence_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-005::clean.spec_bogo_ignores_ineligible",
          "candidate_id": "P2A-CLEAN-005",
          "action_id": "inspect_spec_clause",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-005::clean.spec_bogo_selects_cheapest",
          "candidate_id": "P2A-CLEAN-005",
          "action_id": "inspect_spec_clause",
          "passed": true
        }
      ],
      "case_results_digest": "603811e1b7b6adeb7a1210494e8a85492d85aaa134496b48d3f99644bd4d5648",
      "owned_oracle_case_ids": [
        "P2A-BUG-001::boundary.quantity_zero_rejected"
      ],
      "owned_oracle_reachable": true,
      "detecting_action_ids": [
        "run_boundary_tests"
      ],
      "detecting_cases_by_action": {
        "run_smoke_tests": [],
        "run_boundary_tests": [
          "P2A-BUG-001::boundary.quantity_zero_rejected"
        ],
        "run_null_missing_tests": [],
        "run_config_matrix_tests": [],
        "run_state_sequence_tests": [],
        "run_property_search": [],
        "inspect_traceback": [],
        "inspect_coverage_spectrum": [],
        "inspect_recent_diff": [],
        "inspect_spec_clause": []
      },
      "minimum_detecting_cost": 2,
      "minimum_cost_action_ids": [
        "run_boundary_tests"
      ],
      "ceiling_witness_action_id": "run_boundary_tests",
      "initial_common_stop": false,
      "budget_feasible": true,
      "ceiling_discovered": true,
      "saved_policy_outcomes": {
        "fixed_checklist": true,
        "test_first": true,
        "coverage_first": true,
        "recent_diff_first": true,
        "cause_only_p1a_style": false,
        "expected_utility_per_cost": false
      },
      "policy_classifications": {
        "fixed_checklist": "catalog_reachable_policy_discovered",
        "test_first": "catalog_reachable_policy_discovered",
        "coverage_first": "catalog_reachable_policy_discovered",
        "recent_diff_first": "catalog_reachable_policy_discovered",
        "cause_only_p1a_style": "catalog_reachable_policy_missed",
        "expected_utility_per_cost": "catalog_reachable_policy_missed"
      }
    },
    {
      "variant_id": "P2A-BUG-002",
      "bucket_id": "boundary_precision",
      "catalog_case_support_count": 24,
      "catalog_case_results": [
        {
          "case_id": "P2A-BUG-001::boundary.quantity_zero_rejected",
          "candidate_id": "P2A-BUG-001",
          "action_id": "run_boundary_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-002::boundary.quantity_over_max_rejected",
          "candidate_id": "P2A-BUG-002",
          "action_id": "run_boundary_tests",
          "passed": false
        },
        {
          "case_id": "P2A-BUG-003::missing.region_defaults_domestic",
          "candidate_id": "P2A-BUG-003",
          "action_id": "run_null_missing_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-004::missing.tax_rates_absent_us_zero",
          "candidate_id": "P2A-BUG-004",
          "action_id": "run_null_missing_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-005::config.explicit_fractional_tax_rate",
          "candidate_id": "P2A-BUG-005",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-006::config.threshold_override_exact_value",
          "candidate_id": "P2A-BUG-006",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-007::state.over_cancel_clamps_reserved_zero",
          "candidate_id": "P2A-BUG-007",
          "action_id": "run_state_sequence_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-008::state.coupon_preserves_unrelated_state",
          "candidate_id": "P2A-BUG-008",
          "action_id": "run_state_sequence_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-009::spec.unknown_region_uses_domestic_rate",
          "candidate_id": "P2A-BUG-009",
          "action_id": "inspect_spec_clause",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-010::spec.nonstacking_chooses_larger_discount",
          "candidate_id": "P2A-BUG-010",
          "action_id": "inspect_spec_clause",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-001::clean.boundary_max_accepted",
          "candidate_id": "P2A-CLEAN-001",
          "action_id": "run_boundary_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-001::clean.boundary_over_max_rejected",
          "candidate_id": "P2A-CLEAN-001",
          "action_id": "run_boundary_tests",
          "passed": false
        },
        {
          "case_id": "P2A-CLEAN-002::clean.optional_alias_copy_isolated",
          "candidate_id": "P2A-CLEAN-002",
          "action_id": "run_null_missing_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-002::clean.optional_aliases_absent_empty",
          "candidate_id": "P2A-CLEAN-002",
          "action_id": "run_null_missing_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-003::clean.config_absent_jp_fallback",
          "candidate_id": "P2A-CLEAN-003",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-003::clean.config_absent_us_fallback",
          "candidate_id": "P2A-CLEAN-003",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-003::clean.config_explicit_zero_rate",
          "candidate_id": "P2A-CLEAN-003",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-003::clean.config_present_none_jp_raises",
          "candidate_id": "P2A-CLEAN-003",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-003::clean.config_present_none_us_raises",
          "candidate_id": "P2A-CLEAN-003",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-003::clean.config_string_rate_equivalence",
          "candidate_id": "P2A-CLEAN-003",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-004::clean.state_coupon_idempotent",
          "candidate_id": "P2A-CLEAN-004",
          "action_id": "run_state_sequence_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-004::clean.state_coupon_preserves_session",
          "candidate_id": "P2A-CLEAN-004",
          "action_id": "run_state_sequence_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-005::clean.spec_bogo_ignores_ineligible",
          "candidate_id": "P2A-CLEAN-005",
          "action_id": "inspect_spec_clause",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-005::clean.spec_bogo_selects_cheapest",
          "candidate_id": "P2A-CLEAN-005",
          "action_id": "inspect_spec_clause",
          "passed": true
        }
      ],
      "case_results_digest": "a56b3da581bc1a5a4dbfcdeaf980ef5d23687e6448d07fe397eb1ae9a1a9d3bf",
      "owned_oracle_case_ids": [
        "P2A-BUG-002::boundary.quantity_over_max_rejected"
      ],
      "owned_oracle_reachable": true,
      "detecting_action_ids": [
        "run_boundary_tests"
      ],
      "detecting_cases_by_action": {
        "run_smoke_tests": [],
        "run_boundary_tests": [
          "P2A-BUG-002::boundary.quantity_over_max_rejected",
          "P2A-CLEAN-001::clean.boundary_over_max_rejected"
        ],
        "run_null_missing_tests": [],
        "run_config_matrix_tests": [],
        "run_state_sequence_tests": [],
        "run_property_search": [],
        "inspect_traceback": [],
        "inspect_coverage_spectrum": [],
        "inspect_recent_diff": [],
        "inspect_spec_clause": []
      },
      "minimum_detecting_cost": 2,
      "minimum_cost_action_ids": [
        "run_boundary_tests"
      ],
      "ceiling_witness_action_id": "run_boundary_tests",
      "initial_common_stop": false,
      "budget_feasible": true,
      "ceiling_discovered": true,
      "saved_policy_outcomes": {
        "fixed_checklist": true,
        "test_first": true,
        "coverage_first": true,
        "recent_diff_first": true,
        "cause_only_p1a_style": false,
        "expected_utility_per_cost": false
      },
      "policy_classifications": {
        "fixed_checklist": "catalog_reachable_policy_discovered",
        "test_first": "catalog_reachable_policy_discovered",
        "coverage_first": "catalog_reachable_policy_discovered",
        "recent_diff_first": "catalog_reachable_policy_discovered",
        "cause_only_p1a_style": "catalog_reachable_policy_missed",
        "expected_utility_per_cost": "catalog_reachable_policy_missed"
      }
    },
    {
      "variant_id": "P2A-BUG-003",
      "bucket_id": "missing_optional_input",
      "catalog_case_support_count": 24,
      "catalog_case_results": [
        {
          "case_id": "P2A-BUG-001::boundary.quantity_zero_rejected",
          "candidate_id": "P2A-BUG-001",
          "action_id": "run_boundary_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-002::boundary.quantity_over_max_rejected",
          "candidate_id": "P2A-BUG-002",
          "action_id": "run_boundary_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-003::missing.region_defaults_domestic",
          "candidate_id": "P2A-BUG-003",
          "action_id": "run_null_missing_tests",
          "passed": false
        },
        {
          "case_id": "P2A-BUG-004::missing.tax_rates_absent_us_zero",
          "candidate_id": "P2A-BUG-004",
          "action_id": "run_null_missing_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-005::config.explicit_fractional_tax_rate",
          "candidate_id": "P2A-BUG-005",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-006::config.threshold_override_exact_value",
          "candidate_id": "P2A-BUG-006",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-007::state.over_cancel_clamps_reserved_zero",
          "candidate_id": "P2A-BUG-007",
          "action_id": "run_state_sequence_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-008::state.coupon_preserves_unrelated_state",
          "candidate_id": "P2A-BUG-008",
          "action_id": "run_state_sequence_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-009::spec.unknown_region_uses_domestic_rate",
          "candidate_id": "P2A-BUG-009",
          "action_id": "inspect_spec_clause",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-010::spec.nonstacking_chooses_larger_discount",
          "candidate_id": "P2A-BUG-010",
          "action_id": "inspect_spec_clause",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-001::clean.boundary_max_accepted",
          "candidate_id": "P2A-CLEAN-001",
          "action_id": "run_boundary_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-001::clean.boundary_over_max_rejected",
          "candidate_id": "P2A-CLEAN-001",
          "action_id": "run_boundary_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-002::clean.optional_alias_copy_isolated",
          "candidate_id": "P2A-CLEAN-002",
          "action_id": "run_null_missing_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-002::clean.optional_aliases_absent_empty",
          "candidate_id": "P2A-CLEAN-002",
          "action_id": "run_null_missing_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-003::clean.config_absent_jp_fallback",
          "candidate_id": "P2A-CLEAN-003",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-003::clean.config_absent_us_fallback",
          "candidate_id": "P2A-CLEAN-003",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-003::clean.config_explicit_zero_rate",
          "candidate_id": "P2A-CLEAN-003",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-003::clean.config_present_none_jp_raises",
          "candidate_id": "P2A-CLEAN-003",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-003::clean.config_present_none_us_raises",
          "candidate_id": "P2A-CLEAN-003",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-003::clean.config_string_rate_equivalence",
          "candidate_id": "P2A-CLEAN-003",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-004::clean.state_coupon_idempotent",
          "candidate_id": "P2A-CLEAN-004",
          "action_id": "run_state_sequence_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-004::clean.state_coupon_preserves_session",
          "candidate_id": "P2A-CLEAN-004",
          "action_id": "run_state_sequence_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-005::clean.spec_bogo_ignores_ineligible",
          "candidate_id": "P2A-CLEAN-005",
          "action_id": "inspect_spec_clause",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-005::clean.spec_bogo_selects_cheapest",
          "candidate_id": "P2A-CLEAN-005",
          "action_id": "inspect_spec_clause",
          "passed": true
        }
      ],
      "case_results_digest": "07b3e88ce3fb48f91a80d7a6217d305ccc5882a87ca4c47771796749c983eddc",
      "owned_oracle_case_ids": [
        "P2A-BUG-003::missing.region_defaults_domestic"
      ],
      "owned_oracle_reachable": true,
      "detecting_action_ids": [
        "run_null_missing_tests"
      ],
      "detecting_cases_by_action": {
        "run_smoke_tests": [],
        "run_boundary_tests": [],
        "run_null_missing_tests": [
          "P2A-BUG-003::missing.region_defaults_domestic"
        ],
        "run_config_matrix_tests": [],
        "run_state_sequence_tests": [],
        "run_property_search": [],
        "inspect_traceback": [],
        "inspect_coverage_spectrum": [],
        "inspect_recent_diff": [],
        "inspect_spec_clause": []
      },
      "minimum_detecting_cost": 2,
      "minimum_cost_action_ids": [
        "run_null_missing_tests"
      ],
      "ceiling_witness_action_id": "run_null_missing_tests",
      "initial_common_stop": false,
      "budget_feasible": true,
      "ceiling_discovered": true,
      "saved_policy_outcomes": {
        "fixed_checklist": false,
        "test_first": false,
        "coverage_first": false,
        "recent_diff_first": false,
        "cause_only_p1a_style": false,
        "expected_utility_per_cost": false
      },
      "policy_classifications": {
        "fixed_checklist": "catalog_reachable_policy_missed",
        "test_first": "catalog_reachable_policy_missed",
        "coverage_first": "catalog_reachable_policy_missed",
        "recent_diff_first": "catalog_reachable_policy_missed",
        "cause_only_p1a_style": "catalog_reachable_policy_missed",
        "expected_utility_per_cost": "catalog_reachable_policy_missed"
      }
    },
    {
      "variant_id": "P2A-BUG-004",
      "bucket_id": "missing_optional_input",
      "catalog_case_support_count": 24,
      "catalog_case_results": [
        {
          "case_id": "P2A-BUG-001::boundary.quantity_zero_rejected",
          "candidate_id": "P2A-BUG-001",
          "action_id": "run_boundary_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-002::boundary.quantity_over_max_rejected",
          "candidate_id": "P2A-BUG-002",
          "action_id": "run_boundary_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-003::missing.region_defaults_domestic",
          "candidate_id": "P2A-BUG-003",
          "action_id": "run_null_missing_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-004::missing.tax_rates_absent_us_zero",
          "candidate_id": "P2A-BUG-004",
          "action_id": "run_null_missing_tests",
          "passed": false
        },
        {
          "case_id": "P2A-BUG-005::config.explicit_fractional_tax_rate",
          "candidate_id": "P2A-BUG-005",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-006::config.threshold_override_exact_value",
          "candidate_id": "P2A-BUG-006",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-007::state.over_cancel_clamps_reserved_zero",
          "candidate_id": "P2A-BUG-007",
          "action_id": "run_state_sequence_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-008::state.coupon_preserves_unrelated_state",
          "candidate_id": "P2A-BUG-008",
          "action_id": "run_state_sequence_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-009::spec.unknown_region_uses_domestic_rate",
          "candidate_id": "P2A-BUG-009",
          "action_id": "inspect_spec_clause",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-010::spec.nonstacking_chooses_larger_discount",
          "candidate_id": "P2A-BUG-010",
          "action_id": "inspect_spec_clause",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-001::clean.boundary_max_accepted",
          "candidate_id": "P2A-CLEAN-001",
          "action_id": "run_boundary_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-001::clean.boundary_over_max_rejected",
          "candidate_id": "P2A-CLEAN-001",
          "action_id": "run_boundary_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-002::clean.optional_alias_copy_isolated",
          "candidate_id": "P2A-CLEAN-002",
          "action_id": "run_null_missing_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-002::clean.optional_aliases_absent_empty",
          "candidate_id": "P2A-CLEAN-002",
          "action_id": "run_null_missing_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-003::clean.config_absent_jp_fallback",
          "candidate_id": "P2A-CLEAN-003",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-003::clean.config_absent_us_fallback",
          "candidate_id": "P2A-CLEAN-003",
          "action_id": "run_config_matrix_tests",
          "passed": false
        },
        {
          "case_id": "P2A-CLEAN-003::clean.config_explicit_zero_rate",
          "candidate_id": "P2A-CLEAN-003",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-003::clean.config_present_none_jp_raises",
          "candidate_id": "P2A-CLEAN-003",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-003::clean.config_present_none_us_raises",
          "candidate_id": "P2A-CLEAN-003",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-003::clean.config_string_rate_equivalence",
          "candidate_id": "P2A-CLEAN-003",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-004::clean.state_coupon_idempotent",
          "candidate_id": "P2A-CLEAN-004",
          "action_id": "run_state_sequence_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-004::clean.state_coupon_preserves_session",
          "candidate_id": "P2A-CLEAN-004",
          "action_id": "run_state_sequence_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-005::clean.spec_bogo_ignores_ineligible",
          "candidate_id": "P2A-CLEAN-005",
          "action_id": "inspect_spec_clause",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-005::clean.spec_bogo_selects_cheapest",
          "candidate_id": "P2A-CLEAN-005",
          "action_id": "inspect_spec_clause",
          "passed": true
        }
      ],
      "case_results_digest": "cd2bbb9dd3e71e1d275ef4d2d1b78e87475fae481d1edfc44aae583ed1ff531e",
      "owned_oracle_case_ids": [
        "P2A-BUG-004::missing.tax_rates_absent_us_zero"
      ],
      "owned_oracle_reachable": true,
      "detecting_action_ids": [
        "run_null_missing_tests",
        "run_config_matrix_tests"
      ],
      "detecting_cases_by_action": {
        "run_smoke_tests": [],
        "run_boundary_tests": [],
        "run_null_missing_tests": [
          "P2A-BUG-004::missing.tax_rates_absent_us_zero"
        ],
        "run_config_matrix_tests": [
          "P2A-CLEAN-003::clean.config_absent_us_fallback"
        ],
        "run_state_sequence_tests": [],
        "run_property_search": [],
        "inspect_traceback": [],
        "inspect_coverage_spectrum": [],
        "inspect_recent_diff": [],
        "inspect_spec_clause": []
      },
      "minimum_detecting_cost": 2,
      "minimum_cost_action_ids": [
        "run_null_missing_tests"
      ],
      "ceiling_witness_action_id": "run_null_missing_tests",
      "initial_common_stop": false,
      "budget_feasible": true,
      "ceiling_discovered": true,
      "saved_policy_outcomes": {
        "fixed_checklist": false,
        "test_first": false,
        "coverage_first": false,
        "recent_diff_first": false,
        "cause_only_p1a_style": false,
        "expected_utility_per_cost": false
      },
      "policy_classifications": {
        "fixed_checklist": "catalog_reachable_policy_missed",
        "test_first": "catalog_reachable_policy_missed",
        "coverage_first": "catalog_reachable_policy_missed",
        "recent_diff_first": "catalog_reachable_policy_missed",
        "cause_only_p1a_style": "catalog_reachable_policy_missed",
        "expected_utility_per_cost": "catalog_reachable_policy_missed"
      }
    },
    {
      "variant_id": "P2A-BUG-005",
      "bucket_id": "config_normalization",
      "catalog_case_support_count": 24,
      "catalog_case_results": [
        {
          "case_id": "P2A-BUG-001::boundary.quantity_zero_rejected",
          "candidate_id": "P2A-BUG-001",
          "action_id": "run_boundary_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-002::boundary.quantity_over_max_rejected",
          "candidate_id": "P2A-BUG-002",
          "action_id": "run_boundary_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-003::missing.region_defaults_domestic",
          "candidate_id": "P2A-BUG-003",
          "action_id": "run_null_missing_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-004::missing.tax_rates_absent_us_zero",
          "candidate_id": "P2A-BUG-004",
          "action_id": "run_null_missing_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-005::config.explicit_fractional_tax_rate",
          "candidate_id": "P2A-BUG-005",
          "action_id": "run_config_matrix_tests",
          "passed": false
        },
        {
          "case_id": "P2A-BUG-006::config.threshold_override_exact_value",
          "candidate_id": "P2A-BUG-006",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-007::state.over_cancel_clamps_reserved_zero",
          "candidate_id": "P2A-BUG-007",
          "action_id": "run_state_sequence_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-008::state.coupon_preserves_unrelated_state",
          "candidate_id": "P2A-BUG-008",
          "action_id": "run_state_sequence_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-009::spec.unknown_region_uses_domestic_rate",
          "candidate_id": "P2A-BUG-009",
          "action_id": "inspect_spec_clause",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-010::spec.nonstacking_chooses_larger_discount",
          "candidate_id": "P2A-BUG-010",
          "action_id": "inspect_spec_clause",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-001::clean.boundary_max_accepted",
          "candidate_id": "P2A-CLEAN-001",
          "action_id": "run_boundary_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-001::clean.boundary_over_max_rejected",
          "candidate_id": "P2A-CLEAN-001",
          "action_id": "run_boundary_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-002::clean.optional_alias_copy_isolated",
          "candidate_id": "P2A-CLEAN-002",
          "action_id": "run_null_missing_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-002::clean.optional_aliases_absent_empty",
          "candidate_id": "P2A-CLEAN-002",
          "action_id": "run_null_missing_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-003::clean.config_absent_jp_fallback",
          "candidate_id": "P2A-CLEAN-003",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-003::clean.config_absent_us_fallback",
          "candidate_id": "P2A-CLEAN-003",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-003::clean.config_explicit_zero_rate",
          "candidate_id": "P2A-CLEAN-003",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-003::clean.config_present_none_jp_raises",
          "candidate_id": "P2A-CLEAN-003",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-003::clean.config_present_none_us_raises",
          "candidate_id": "P2A-CLEAN-003",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-003::clean.config_string_rate_equivalence",
          "candidate_id": "P2A-CLEAN-003",
          "action_id": "run_config_matrix_tests",
          "passed": false
        },
        {
          "case_id": "P2A-CLEAN-004::clean.state_coupon_idempotent",
          "candidate_id": "P2A-CLEAN-004",
          "action_id": "run_state_sequence_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-004::clean.state_coupon_preserves_session",
          "candidate_id": "P2A-CLEAN-004",
          "action_id": "run_state_sequence_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-005::clean.spec_bogo_ignores_ineligible",
          "candidate_id": "P2A-CLEAN-005",
          "action_id": "inspect_spec_clause",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-005::clean.spec_bogo_selects_cheapest",
          "candidate_id": "P2A-CLEAN-005",
          "action_id": "inspect_spec_clause",
          "passed": true
        }
      ],
      "case_results_digest": "4562f9d93f3a08fd2d7c5b12e366fb9125e4269227f477978554c8086764d811",
      "owned_oracle_case_ids": [
        "P2A-BUG-005::config.explicit_fractional_tax_rate"
      ],
      "owned_oracle_reachable": true,
      "detecting_action_ids": [
        "run_config_matrix_tests"
      ],
      "detecting_cases_by_action": {
        "run_smoke_tests": [],
        "run_boundary_tests": [],
        "run_null_missing_tests": [],
        "run_config_matrix_tests": [
          "P2A-BUG-005::config.explicit_fractional_tax_rate",
          "P2A-CLEAN-003::clean.config_string_rate_equivalence"
        ],
        "run_state_sequence_tests": [],
        "run_property_search": [],
        "inspect_traceback": [],
        "inspect_coverage_spectrum": [],
        "inspect_recent_diff": [],
        "inspect_spec_clause": []
      },
      "minimum_detecting_cost": 3,
      "minimum_cost_action_ids": [
        "run_config_matrix_tests"
      ],
      "ceiling_witness_action_id": "run_config_matrix_tests",
      "initial_common_stop": false,
      "budget_feasible": true,
      "ceiling_discovered": true,
      "saved_policy_outcomes": {
        "fixed_checklist": false,
        "test_first": false,
        "coverage_first": false,
        "recent_diff_first": false,
        "cause_only_p1a_style": false,
        "expected_utility_per_cost": false
      },
      "policy_classifications": {
        "fixed_checklist": "catalog_reachable_policy_missed",
        "test_first": "catalog_reachable_policy_missed",
        "coverage_first": "catalog_reachable_policy_missed",
        "recent_diff_first": "catalog_reachable_policy_missed",
        "cause_only_p1a_style": "catalog_reachable_policy_missed",
        "expected_utility_per_cost": "catalog_reachable_policy_missed"
      }
    },
    {
      "variant_id": "P2A-BUG-006",
      "bucket_id": "config_normalization",
      "catalog_case_support_count": 24,
      "catalog_case_results": [
        {
          "case_id": "P2A-BUG-001::boundary.quantity_zero_rejected",
          "candidate_id": "P2A-BUG-001",
          "action_id": "run_boundary_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-002::boundary.quantity_over_max_rejected",
          "candidate_id": "P2A-BUG-002",
          "action_id": "run_boundary_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-003::missing.region_defaults_domestic",
          "candidate_id": "P2A-BUG-003",
          "action_id": "run_null_missing_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-004::missing.tax_rates_absent_us_zero",
          "candidate_id": "P2A-BUG-004",
          "action_id": "run_null_missing_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-005::config.explicit_fractional_tax_rate",
          "candidate_id": "P2A-BUG-005",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-006::config.threshold_override_exact_value",
          "candidate_id": "P2A-BUG-006",
          "action_id": "run_config_matrix_tests",
          "passed": false
        },
        {
          "case_id": "P2A-BUG-007::state.over_cancel_clamps_reserved_zero",
          "candidate_id": "P2A-BUG-007",
          "action_id": "run_state_sequence_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-008::state.coupon_preserves_unrelated_state",
          "candidate_id": "P2A-BUG-008",
          "action_id": "run_state_sequence_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-009::spec.unknown_region_uses_domestic_rate",
          "candidate_id": "P2A-BUG-009",
          "action_id": "inspect_spec_clause",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-010::spec.nonstacking_chooses_larger_discount",
          "candidate_id": "P2A-BUG-010",
          "action_id": "inspect_spec_clause",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-001::clean.boundary_max_accepted",
          "candidate_id": "P2A-CLEAN-001",
          "action_id": "run_boundary_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-001::clean.boundary_over_max_rejected",
          "candidate_id": "P2A-CLEAN-001",
          "action_id": "run_boundary_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-002::clean.optional_alias_copy_isolated",
          "candidate_id": "P2A-CLEAN-002",
          "action_id": "run_null_missing_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-002::clean.optional_aliases_absent_empty",
          "candidate_id": "P2A-CLEAN-002",
          "action_id": "run_null_missing_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-003::clean.config_absent_jp_fallback",
          "candidate_id": "P2A-CLEAN-003",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-003::clean.config_absent_us_fallback",
          "candidate_id": "P2A-CLEAN-003",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-003::clean.config_explicit_zero_rate",
          "candidate_id": "P2A-CLEAN-003",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-003::clean.config_present_none_jp_raises",
          "candidate_id": "P2A-CLEAN-003",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-003::clean.config_present_none_us_raises",
          "candidate_id": "P2A-CLEAN-003",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-003::clean.config_string_rate_equivalence",
          "candidate_id": "P2A-CLEAN-003",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-004::clean.state_coupon_idempotent",
          "candidate_id": "P2A-CLEAN-004",
          "action_id": "run_state_sequence_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-004::clean.state_coupon_preserves_session",
          "candidate_id": "P2A-CLEAN-004",
          "action_id": "run_state_sequence_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-005::clean.spec_bogo_ignores_ineligible",
          "candidate_id": "P2A-CLEAN-005",
          "action_id": "inspect_spec_clause",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-005::clean.spec_bogo_selects_cheapest",
          "candidate_id": "P2A-CLEAN-005",
          "action_id": "inspect_spec_clause",
          "passed": true
        }
      ],
      "case_results_digest": "62f91403ae373f2d640d8160a29e8083606f3bdd7ef9a5871c294de926c65031",
      "owned_oracle_case_ids": [
        "P2A-BUG-006::config.threshold_override_exact_value"
      ],
      "owned_oracle_reachable": true,
      "detecting_action_ids": [
        "run_config_matrix_tests"
      ],
      "detecting_cases_by_action": {
        "run_smoke_tests": [],
        "run_boundary_tests": [],
        "run_null_missing_tests": [],
        "run_config_matrix_tests": [
          "P2A-BUG-006::config.threshold_override_exact_value"
        ],
        "run_state_sequence_tests": [],
        "run_property_search": [],
        "inspect_traceback": [],
        "inspect_coverage_spectrum": [],
        "inspect_recent_diff": [],
        "inspect_spec_clause": []
      },
      "minimum_detecting_cost": 3,
      "minimum_cost_action_ids": [
        "run_config_matrix_tests"
      ],
      "ceiling_witness_action_id": "run_config_matrix_tests",
      "initial_common_stop": false,
      "budget_feasible": true,
      "ceiling_discovered": true,
      "saved_policy_outcomes": {
        "fixed_checklist": false,
        "test_first": false,
        "coverage_first": false,
        "recent_diff_first": false,
        "cause_only_p1a_style": false,
        "expected_utility_per_cost": false
      },
      "policy_classifications": {
        "fixed_checklist": "catalog_reachable_policy_missed",
        "test_first": "catalog_reachable_policy_missed",
        "coverage_first": "catalog_reachable_policy_missed",
        "recent_diff_first": "catalog_reachable_policy_missed",
        "cause_only_p1a_style": "catalog_reachable_policy_missed",
        "expected_utility_per_cost": "catalog_reachable_policy_missed"
      }
    },
    {
      "variant_id": "P2A-BUG-007",
      "bucket_id": "state_sequence",
      "catalog_case_support_count": 24,
      "catalog_case_results": [
        {
          "case_id": "P2A-BUG-001::boundary.quantity_zero_rejected",
          "candidate_id": "P2A-BUG-001",
          "action_id": "run_boundary_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-002::boundary.quantity_over_max_rejected",
          "candidate_id": "P2A-BUG-002",
          "action_id": "run_boundary_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-003::missing.region_defaults_domestic",
          "candidate_id": "P2A-BUG-003",
          "action_id": "run_null_missing_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-004::missing.tax_rates_absent_us_zero",
          "candidate_id": "P2A-BUG-004",
          "action_id": "run_null_missing_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-005::config.explicit_fractional_tax_rate",
          "candidate_id": "P2A-BUG-005",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-006::config.threshold_override_exact_value",
          "candidate_id": "P2A-BUG-006",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-007::state.over_cancel_clamps_reserved_zero",
          "candidate_id": "P2A-BUG-007",
          "action_id": "run_state_sequence_tests",
          "passed": false
        },
        {
          "case_id": "P2A-BUG-008::state.coupon_preserves_unrelated_state",
          "candidate_id": "P2A-BUG-008",
          "action_id": "run_state_sequence_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-009::spec.unknown_region_uses_domestic_rate",
          "candidate_id": "P2A-BUG-009",
          "action_id": "inspect_spec_clause",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-010::spec.nonstacking_chooses_larger_discount",
          "candidate_id": "P2A-BUG-010",
          "action_id": "inspect_spec_clause",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-001::clean.boundary_max_accepted",
          "candidate_id": "P2A-CLEAN-001",
          "action_id": "run_boundary_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-001::clean.boundary_over_max_rejected",
          "candidate_id": "P2A-CLEAN-001",
          "action_id": "run_boundary_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-002::clean.optional_alias_copy_isolated",
          "candidate_id": "P2A-CLEAN-002",
          "action_id": "run_null_missing_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-002::clean.optional_aliases_absent_empty",
          "candidate_id": "P2A-CLEAN-002",
          "action_id": "run_null_missing_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-003::clean.config_absent_jp_fallback",
          "candidate_id": "P2A-CLEAN-003",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-003::clean.config_absent_us_fallback",
          "candidate_id": "P2A-CLEAN-003",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-003::clean.config_explicit_zero_rate",
          "candidate_id": "P2A-CLEAN-003",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-003::clean.config_present_none_jp_raises",
          "candidate_id": "P2A-CLEAN-003",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-003::clean.config_present_none_us_raises",
          "candidate_id": "P2A-CLEAN-003",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-003::clean.config_string_rate_equivalence",
          "candidate_id": "P2A-CLEAN-003",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-004::clean.state_coupon_idempotent",
          "candidate_id": "P2A-CLEAN-004",
          "action_id": "run_state_sequence_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-004::clean.state_coupon_preserves_session",
          "candidate_id": "P2A-CLEAN-004",
          "action_id": "run_state_sequence_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-005::clean.spec_bogo_ignores_ineligible",
          "candidate_id": "P2A-CLEAN-005",
          "action_id": "inspect_spec_clause",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-005::clean.spec_bogo_selects_cheapest",
          "candidate_id": "P2A-CLEAN-005",
          "action_id": "inspect_spec_clause",
          "passed": true
        }
      ],
      "case_results_digest": "9387166382fc87d8335d4fe20585e92a82d145440d25f1f807ecf18473c3fc4b",
      "owned_oracle_case_ids": [
        "P2A-BUG-007::state.over_cancel_clamps_reserved_zero"
      ],
      "owned_oracle_reachable": true,
      "detecting_action_ids": [
        "run_state_sequence_tests"
      ],
      "detecting_cases_by_action": {
        "run_smoke_tests": [],
        "run_boundary_tests": [],
        "run_null_missing_tests": [],
        "run_config_matrix_tests": [],
        "run_state_sequence_tests": [
          "P2A-BUG-007::state.over_cancel_clamps_reserved_zero"
        ],
        "run_property_search": [],
        "inspect_traceback": [],
        "inspect_coverage_spectrum": [],
        "inspect_recent_diff": [],
        "inspect_spec_clause": []
      },
      "minimum_detecting_cost": 4,
      "minimum_cost_action_ids": [
        "run_state_sequence_tests"
      ],
      "ceiling_witness_action_id": "run_state_sequence_tests",
      "initial_common_stop": false,
      "budget_feasible": true,
      "ceiling_discovered": true,
      "saved_policy_outcomes": {
        "fixed_checklist": false,
        "test_first": false,
        "coverage_first": false,
        "recent_diff_first": false,
        "cause_only_p1a_style": false,
        "expected_utility_per_cost": false
      },
      "policy_classifications": {
        "fixed_checklist": "catalog_reachable_policy_missed",
        "test_first": "catalog_reachable_policy_missed",
        "coverage_first": "catalog_reachable_policy_missed",
        "recent_diff_first": "catalog_reachable_policy_missed",
        "cause_only_p1a_style": "catalog_reachable_policy_missed",
        "expected_utility_per_cost": "catalog_reachable_policy_missed"
      }
    },
    {
      "variant_id": "P2A-BUG-008",
      "bucket_id": "state_sequence",
      "catalog_case_support_count": 24,
      "catalog_case_results": [
        {
          "case_id": "P2A-BUG-001::boundary.quantity_zero_rejected",
          "candidate_id": "P2A-BUG-001",
          "action_id": "run_boundary_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-002::boundary.quantity_over_max_rejected",
          "candidate_id": "P2A-BUG-002",
          "action_id": "run_boundary_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-003::missing.region_defaults_domestic",
          "candidate_id": "P2A-BUG-003",
          "action_id": "run_null_missing_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-004::missing.tax_rates_absent_us_zero",
          "candidate_id": "P2A-BUG-004",
          "action_id": "run_null_missing_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-005::config.explicit_fractional_tax_rate",
          "candidate_id": "P2A-BUG-005",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-006::config.threshold_override_exact_value",
          "candidate_id": "P2A-BUG-006",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-007::state.over_cancel_clamps_reserved_zero",
          "candidate_id": "P2A-BUG-007",
          "action_id": "run_state_sequence_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-008::state.coupon_preserves_unrelated_state",
          "candidate_id": "P2A-BUG-008",
          "action_id": "run_state_sequence_tests",
          "passed": false
        },
        {
          "case_id": "P2A-BUG-009::spec.unknown_region_uses_domestic_rate",
          "candidate_id": "P2A-BUG-009",
          "action_id": "inspect_spec_clause",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-010::spec.nonstacking_chooses_larger_discount",
          "candidate_id": "P2A-BUG-010",
          "action_id": "inspect_spec_clause",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-001::clean.boundary_max_accepted",
          "candidate_id": "P2A-CLEAN-001",
          "action_id": "run_boundary_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-001::clean.boundary_over_max_rejected",
          "candidate_id": "P2A-CLEAN-001",
          "action_id": "run_boundary_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-002::clean.optional_alias_copy_isolated",
          "candidate_id": "P2A-CLEAN-002",
          "action_id": "run_null_missing_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-002::clean.optional_aliases_absent_empty",
          "candidate_id": "P2A-CLEAN-002",
          "action_id": "run_null_missing_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-003::clean.config_absent_jp_fallback",
          "candidate_id": "P2A-CLEAN-003",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-003::clean.config_absent_us_fallback",
          "candidate_id": "P2A-CLEAN-003",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-003::clean.config_explicit_zero_rate",
          "candidate_id": "P2A-CLEAN-003",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-003::clean.config_present_none_jp_raises",
          "candidate_id": "P2A-CLEAN-003",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-003::clean.config_present_none_us_raises",
          "candidate_id": "P2A-CLEAN-003",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-003::clean.config_string_rate_equivalence",
          "candidate_id": "P2A-CLEAN-003",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-004::clean.state_coupon_idempotent",
          "candidate_id": "P2A-CLEAN-004",
          "action_id": "run_state_sequence_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-004::clean.state_coupon_preserves_session",
          "candidate_id": "P2A-CLEAN-004",
          "action_id": "run_state_sequence_tests",
          "passed": false
        },
        {
          "case_id": "P2A-CLEAN-005::clean.spec_bogo_ignores_ineligible",
          "candidate_id": "P2A-CLEAN-005",
          "action_id": "inspect_spec_clause",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-005::clean.spec_bogo_selects_cheapest",
          "candidate_id": "P2A-CLEAN-005",
          "action_id": "inspect_spec_clause",
          "passed": true
        }
      ],
      "case_results_digest": "f48b8418b5cb778ce3a92d5d4436eb968e700f193b6e4c2ce73f9e60627a01db",
      "owned_oracle_case_ids": [
        "P2A-BUG-008::state.coupon_preserves_unrelated_state"
      ],
      "owned_oracle_reachable": true,
      "detecting_action_ids": [
        "run_state_sequence_tests"
      ],
      "detecting_cases_by_action": {
        "run_smoke_tests": [],
        "run_boundary_tests": [],
        "run_null_missing_tests": [],
        "run_config_matrix_tests": [],
        "run_state_sequence_tests": [
          "P2A-BUG-008::state.coupon_preserves_unrelated_state",
          "P2A-CLEAN-004::clean.state_coupon_preserves_session"
        ],
        "run_property_search": [],
        "inspect_traceback": [],
        "inspect_coverage_spectrum": [],
        "inspect_recent_diff": [],
        "inspect_spec_clause": []
      },
      "minimum_detecting_cost": 4,
      "minimum_cost_action_ids": [
        "run_state_sequence_tests"
      ],
      "ceiling_witness_action_id": "run_state_sequence_tests",
      "initial_common_stop": false,
      "budget_feasible": true,
      "ceiling_discovered": true,
      "saved_policy_outcomes": {
        "fixed_checklist": false,
        "test_first": false,
        "coverage_first": false,
        "recent_diff_first": false,
        "cause_only_p1a_style": false,
        "expected_utility_per_cost": false
      },
      "policy_classifications": {
        "fixed_checklist": "catalog_reachable_policy_missed",
        "test_first": "catalog_reachable_policy_missed",
        "coverage_first": "catalog_reachable_policy_missed",
        "recent_diff_first": "catalog_reachable_policy_missed",
        "cause_only_p1a_style": "catalog_reachable_policy_missed",
        "expected_utility_per_cost": "catalog_reachable_policy_missed"
      }
    },
    {
      "variant_id": "P2A-BUG-009",
      "bucket_id": "spec_semantics",
      "catalog_case_support_count": 24,
      "catalog_case_results": [
        {
          "case_id": "P2A-BUG-001::boundary.quantity_zero_rejected",
          "candidate_id": "P2A-BUG-001",
          "action_id": "run_boundary_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-002::boundary.quantity_over_max_rejected",
          "candidate_id": "P2A-BUG-002",
          "action_id": "run_boundary_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-003::missing.region_defaults_domestic",
          "candidate_id": "P2A-BUG-003",
          "action_id": "run_null_missing_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-004::missing.tax_rates_absent_us_zero",
          "candidate_id": "P2A-BUG-004",
          "action_id": "run_null_missing_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-005::config.explicit_fractional_tax_rate",
          "candidate_id": "P2A-BUG-005",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-006::config.threshold_override_exact_value",
          "candidate_id": "P2A-BUG-006",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-007::state.over_cancel_clamps_reserved_zero",
          "candidate_id": "P2A-BUG-007",
          "action_id": "run_state_sequence_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-008::state.coupon_preserves_unrelated_state",
          "candidate_id": "P2A-BUG-008",
          "action_id": "run_state_sequence_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-009::spec.unknown_region_uses_domestic_rate",
          "candidate_id": "P2A-BUG-009",
          "action_id": "inspect_spec_clause",
          "passed": false
        },
        {
          "case_id": "P2A-BUG-010::spec.nonstacking_chooses_larger_discount",
          "candidate_id": "P2A-BUG-010",
          "action_id": "inspect_spec_clause",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-001::clean.boundary_max_accepted",
          "candidate_id": "P2A-CLEAN-001",
          "action_id": "run_boundary_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-001::clean.boundary_over_max_rejected",
          "candidate_id": "P2A-CLEAN-001",
          "action_id": "run_boundary_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-002::clean.optional_alias_copy_isolated",
          "candidate_id": "P2A-CLEAN-002",
          "action_id": "run_null_missing_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-002::clean.optional_aliases_absent_empty",
          "candidate_id": "P2A-CLEAN-002",
          "action_id": "run_null_missing_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-003::clean.config_absent_jp_fallback",
          "candidate_id": "P2A-CLEAN-003",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-003::clean.config_absent_us_fallback",
          "candidate_id": "P2A-CLEAN-003",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-003::clean.config_explicit_zero_rate",
          "candidate_id": "P2A-CLEAN-003",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-003::clean.config_present_none_jp_raises",
          "candidate_id": "P2A-CLEAN-003",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-003::clean.config_present_none_us_raises",
          "candidate_id": "P2A-CLEAN-003",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-003::clean.config_string_rate_equivalence",
          "candidate_id": "P2A-CLEAN-003",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-004::clean.state_coupon_idempotent",
          "candidate_id": "P2A-CLEAN-004",
          "action_id": "run_state_sequence_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-004::clean.state_coupon_preserves_session",
          "candidate_id": "P2A-CLEAN-004",
          "action_id": "run_state_sequence_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-005::clean.spec_bogo_ignores_ineligible",
          "candidate_id": "P2A-CLEAN-005",
          "action_id": "inspect_spec_clause",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-005::clean.spec_bogo_selects_cheapest",
          "candidate_id": "P2A-CLEAN-005",
          "action_id": "inspect_spec_clause",
          "passed": true
        }
      ],
      "case_results_digest": "44a78d412006ede6f1e79115a7cb55e12436a0d0b4d279c0e388fdb67fb79de1",
      "owned_oracle_case_ids": [
        "P2A-BUG-009::spec.unknown_region_uses_domestic_rate"
      ],
      "owned_oracle_reachable": true,
      "detecting_action_ids": [
        "inspect_spec_clause"
      ],
      "detecting_cases_by_action": {
        "run_smoke_tests": [],
        "run_boundary_tests": [],
        "run_null_missing_tests": [],
        "run_config_matrix_tests": [],
        "run_state_sequence_tests": [],
        "run_property_search": [],
        "inspect_traceback": [],
        "inspect_coverage_spectrum": [],
        "inspect_recent_diff": [],
        "inspect_spec_clause": [
          "P2A-BUG-009::spec.unknown_region_uses_domestic_rate"
        ]
      },
      "minimum_detecting_cost": 2,
      "minimum_cost_action_ids": [
        "inspect_spec_clause"
      ],
      "ceiling_witness_action_id": "inspect_spec_clause",
      "initial_common_stop": false,
      "budget_feasible": true,
      "ceiling_discovered": true,
      "saved_policy_outcomes": {
        "fixed_checklist": false,
        "test_first": false,
        "coverage_first": false,
        "recent_diff_first": false,
        "cause_only_p1a_style": false,
        "expected_utility_per_cost": false
      },
      "policy_classifications": {
        "fixed_checklist": "catalog_reachable_policy_missed",
        "test_first": "catalog_reachable_policy_missed",
        "coverage_first": "catalog_reachable_policy_missed",
        "recent_diff_first": "catalog_reachable_policy_missed",
        "cause_only_p1a_style": "catalog_reachable_policy_missed",
        "expected_utility_per_cost": "catalog_reachable_policy_missed"
      }
    },
    {
      "variant_id": "P2A-BUG-010",
      "bucket_id": "spec_semantics",
      "catalog_case_support_count": 24,
      "catalog_case_results": [
        {
          "case_id": "P2A-BUG-001::boundary.quantity_zero_rejected",
          "candidate_id": "P2A-BUG-001",
          "action_id": "run_boundary_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-002::boundary.quantity_over_max_rejected",
          "candidate_id": "P2A-BUG-002",
          "action_id": "run_boundary_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-003::missing.region_defaults_domestic",
          "candidate_id": "P2A-BUG-003",
          "action_id": "run_null_missing_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-004::missing.tax_rates_absent_us_zero",
          "candidate_id": "P2A-BUG-004",
          "action_id": "run_null_missing_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-005::config.explicit_fractional_tax_rate",
          "candidate_id": "P2A-BUG-005",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-006::config.threshold_override_exact_value",
          "candidate_id": "P2A-BUG-006",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-007::state.over_cancel_clamps_reserved_zero",
          "candidate_id": "P2A-BUG-007",
          "action_id": "run_state_sequence_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-008::state.coupon_preserves_unrelated_state",
          "candidate_id": "P2A-BUG-008",
          "action_id": "run_state_sequence_tests",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-009::spec.unknown_region_uses_domestic_rate",
          "candidate_id": "P2A-BUG-009",
          "action_id": "inspect_spec_clause",
          "passed": true
        },
        {
          "case_id": "P2A-BUG-010::spec.nonstacking_chooses_larger_discount",
          "candidate_id": "P2A-BUG-010",
          "action_id": "inspect_spec_clause",
          "passed": false
        },
        {
          "case_id": "P2A-CLEAN-001::clean.boundary_max_accepted",
          "candidate_id": "P2A-CLEAN-001",
          "action_id": "run_boundary_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-001::clean.boundary_over_max_rejected",
          "candidate_id": "P2A-CLEAN-001",
          "action_id": "run_boundary_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-002::clean.optional_alias_copy_isolated",
          "candidate_id": "P2A-CLEAN-002",
          "action_id": "run_null_missing_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-002::clean.optional_aliases_absent_empty",
          "candidate_id": "P2A-CLEAN-002",
          "action_id": "run_null_missing_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-003::clean.config_absent_jp_fallback",
          "candidate_id": "P2A-CLEAN-003",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-003::clean.config_absent_us_fallback",
          "candidate_id": "P2A-CLEAN-003",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-003::clean.config_explicit_zero_rate",
          "candidate_id": "P2A-CLEAN-003",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-003::clean.config_present_none_jp_raises",
          "candidate_id": "P2A-CLEAN-003",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-003::clean.config_present_none_us_raises",
          "candidate_id": "P2A-CLEAN-003",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-003::clean.config_string_rate_equivalence",
          "candidate_id": "P2A-CLEAN-003",
          "action_id": "run_config_matrix_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-004::clean.state_coupon_idempotent",
          "candidate_id": "P2A-CLEAN-004",
          "action_id": "run_state_sequence_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-004::clean.state_coupon_preserves_session",
          "candidate_id": "P2A-CLEAN-004",
          "action_id": "run_state_sequence_tests",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-005::clean.spec_bogo_ignores_ineligible",
          "candidate_id": "P2A-CLEAN-005",
          "action_id": "inspect_spec_clause",
          "passed": true
        },
        {
          "case_id": "P2A-CLEAN-005::clean.spec_bogo_selects_cheapest",
          "candidate_id": "P2A-CLEAN-005",
          "action_id": "inspect_spec_clause",
          "passed": true
        }
      ],
      "case_results_digest": "b80553ca0c6d6617c7612d728f08c213ef8c1f49203bb606e62a7234c062d775",
      "owned_oracle_case_ids": [
        "P2A-BUG-010::spec.nonstacking_chooses_larger_discount"
      ],
      "owned_oracle_reachable": true,
      "detecting_action_ids": [
        "inspect_spec_clause"
      ],
      "detecting_cases_by_action": {
        "run_smoke_tests": [],
        "run_boundary_tests": [],
        "run_null_missing_tests": [],
        "run_config_matrix_tests": [],
        "run_state_sequence_tests": [],
        "run_property_search": [],
        "inspect_traceback": [],
        "inspect_coverage_spectrum": [],
        "inspect_recent_diff": [],
        "inspect_spec_clause": [
          "P2A-BUG-010::spec.nonstacking_chooses_larger_discount"
        ]
      },
      "minimum_detecting_cost": 2,
      "minimum_cost_action_ids": [
        "inspect_spec_clause"
      ],
      "ceiling_witness_action_id": "inspect_spec_clause",
      "initial_common_stop": false,
      "budget_feasible": true,
      "ceiling_discovered": true,
      "saved_policy_outcomes": {
        "fixed_checklist": false,
        "test_first": false,
        "coverage_first": false,
        "recent_diff_first": false,
        "cause_only_p1a_style": false,
        "expected_utility_per_cost": false
      },
      "policy_classifications": {
        "fixed_checklist": "catalog_reachable_policy_missed",
        "test_first": "catalog_reachable_policy_missed",
        "coverage_first": "catalog_reachable_policy_missed",
        "recent_diff_first": "catalog_reachable_policy_missed",
        "cause_only_p1a_style": "catalog_reachable_policy_missed",
        "expected_utility_per_cost": "catalog_reachable_policy_missed"
      }
    }
  ],
  "bucket_diagnostics": {
    "boundary_precision": {
      "support_variant_ids": [
        "P2A-BUG-001",
        "P2A-BUG-002"
      ],
      "catalog_reachable_variant_ids": [
        "P2A-BUG-001",
        "P2A-BUG-002"
      ],
      "catalog_unreachable_variant_ids": [],
      "budget_feasible_variant_ids": [
        "P2A-BUG-001",
        "P2A-BUG-002"
      ],
      "catalog_reachable_not_budget_feasible_variant_ids": [],
      "catalog_reachability_rate": {
        "numerator": 2,
        "denominator": 2,
        "fraction": "1/1",
        "decimal": "1",
        "undefined_reason": null
      },
      "ceiling_discovery_rate": {
        "numerator": 2,
        "denominator": 2,
        "fraction": "1/1",
        "decimal": "1",
        "undefined_reason": null
      },
      "ceiling_discovery_loss": {
        "numerator": 0,
        "denominator": 2,
        "fraction": "0/1",
        "decimal": "0",
        "undefined_reason": null
      },
      "minimum_detecting_cost_by_variant": {
        "P2A-BUG-001": 2,
        "P2A-BUG-002": 2
      }
    },
    "missing_optional_input": {
      "support_variant_ids": [
        "P2A-BUG-003",
        "P2A-BUG-004"
      ],
      "catalog_reachable_variant_ids": [
        "P2A-BUG-003",
        "P2A-BUG-004"
      ],
      "catalog_unreachable_variant_ids": [],
      "budget_feasible_variant_ids": [
        "P2A-BUG-003",
        "P2A-BUG-004"
      ],
      "catalog_reachable_not_budget_feasible_variant_ids": [],
      "catalog_reachability_rate": {
        "numerator": 2,
        "denominator": 2,
        "fraction": "1/1",
        "decimal": "1",
        "undefined_reason": null
      },
      "ceiling_discovery_rate": {
        "numerator": 2,
        "denominator": 2,
        "fraction": "1/1",
        "decimal": "1",
        "undefined_reason": null
      },
      "ceiling_discovery_loss": {
        "numerator": 0,
        "denominator": 2,
        "fraction": "0/1",
        "decimal": "0",
        "undefined_reason": null
      },
      "minimum_detecting_cost_by_variant": {
        "P2A-BUG-003": 2,
        "P2A-BUG-004": 2
      }
    },
    "config_normalization": {
      "support_variant_ids": [
        "P2A-BUG-005",
        "P2A-BUG-006"
      ],
      "catalog_reachable_variant_ids": [
        "P2A-BUG-005",
        "P2A-BUG-006"
      ],
      "catalog_unreachable_variant_ids": [],
      "budget_feasible_variant_ids": [
        "P2A-BUG-005",
        "P2A-BUG-006"
      ],
      "catalog_reachable_not_budget_feasible_variant_ids": [],
      "catalog_reachability_rate": {
        "numerator": 2,
        "denominator": 2,
        "fraction": "1/1",
        "decimal": "1",
        "undefined_reason": null
      },
      "ceiling_discovery_rate": {
        "numerator": 2,
        "denominator": 2,
        "fraction": "1/1",
        "decimal": "1",
        "undefined_reason": null
      },
      "ceiling_discovery_loss": {
        "numerator": 0,
        "denominator": 2,
        "fraction": "0/1",
        "decimal": "0",
        "undefined_reason": null
      },
      "minimum_detecting_cost_by_variant": {
        "P2A-BUG-005": 3,
        "P2A-BUG-006": 3
      }
    },
    "state_sequence": {
      "support_variant_ids": [
        "P2A-BUG-007",
        "P2A-BUG-008"
      ],
      "catalog_reachable_variant_ids": [
        "P2A-BUG-007",
        "P2A-BUG-008"
      ],
      "catalog_unreachable_variant_ids": [],
      "budget_feasible_variant_ids": [
        "P2A-BUG-007",
        "P2A-BUG-008"
      ],
      "catalog_reachable_not_budget_feasible_variant_ids": [],
      "catalog_reachability_rate": {
        "numerator": 2,
        "denominator": 2,
        "fraction": "1/1",
        "decimal": "1",
        "undefined_reason": null
      },
      "ceiling_discovery_rate": {
        "numerator": 2,
        "denominator": 2,
        "fraction": "1/1",
        "decimal": "1",
        "undefined_reason": null
      },
      "ceiling_discovery_loss": {
        "numerator": 0,
        "denominator": 2,
        "fraction": "0/1",
        "decimal": "0",
        "undefined_reason": null
      },
      "minimum_detecting_cost_by_variant": {
        "P2A-BUG-007": 4,
        "P2A-BUG-008": 4
      }
    },
    "spec_semantics": {
      "support_variant_ids": [
        "P2A-BUG-009",
        "P2A-BUG-010"
      ],
      "catalog_reachable_variant_ids": [
        "P2A-BUG-009",
        "P2A-BUG-010"
      ],
      "catalog_unreachable_variant_ids": [],
      "budget_feasible_variant_ids": [
        "P2A-BUG-009",
        "P2A-BUG-010"
      ],
      "catalog_reachable_not_budget_feasible_variant_ids": [],
      "catalog_reachability_rate": {
        "numerator": 2,
        "denominator": 2,
        "fraction": "1/1",
        "decimal": "1",
        "undefined_reason": null
      },
      "ceiling_discovery_rate": {
        "numerator": 2,
        "denominator": 2,
        "fraction": "1/1",
        "decimal": "1",
        "undefined_reason": null
      },
      "ceiling_discovery_loss": {
        "numerator": 0,
        "denominator": 2,
        "fraction": "0/1",
        "decimal": "0",
        "undefined_reason": null
      },
      "minimum_detecting_cost_by_variant": {
        "P2A-BUG-009": 2,
        "P2A-BUG-010": 2
      }
    }
  },
  "policy_comparison": {
    "fixed_checklist": {
      "overall": {
        "support_variant_ids": [
          "P2A-BUG-001",
          "P2A-BUG-002",
          "P2A-BUG-003",
          "P2A-BUG-004",
          "P2A-BUG-005",
          "P2A-BUG-006",
          "P2A-BUG-007",
          "P2A-BUG-008",
          "P2A-BUG-009",
          "P2A-BUG-010"
        ],
        "saved_discovered_variant_ids": [
          "P2A-BUG-001",
          "P2A-BUG-002"
        ],
        "saved_missed_variant_ids": [
          "P2A-BUG-003",
          "P2A-BUG-004",
          "P2A-BUG-005",
          "P2A-BUG-006",
          "P2A-BUG-007",
          "P2A-BUG-008",
          "P2A-BUG-009",
          "P2A-BUG-010"
        ],
        "classification_variant_ids": {
          "catalog_unreachable": [],
          "catalog_reachable_not_budget_feasible": [],
          "catalog_reachable_policy_discovered": [
            "P2A-BUG-001",
            "P2A-BUG-002"
          ],
          "catalog_reachable_policy_missed": [
            "P2A-BUG-003",
            "P2A-BUG-004",
            "P2A-BUG-005",
            "P2A-BUG-006",
            "P2A-BUG-007",
            "P2A-BUG-008",
            "P2A-BUG-009",
            "P2A-BUG-010"
          ]
        },
        "saved_policy_discovery_rate": {
          "numerator": 2,
          "denominator": 10,
          "fraction": "1/5",
          "decimal": "0.2",
          "undefined_reason": null
        },
        "ceiling_discovery_rate": {
          "numerator": 10,
          "denominator": 10,
          "fraction": "1/1",
          "decimal": "1",
          "undefined_reason": null
        },
        "ceiling_gap": {
          "numerator": 4,
          "denominator": 5,
          "fraction": "4/5",
          "decimal": "0.8",
          "undefined_reason": null
        },
        "budget_feasible_policy_miss_rate": {
          "numerator": 8,
          "denominator": 10,
          "fraction": "4/5",
          "decimal": "0.8",
          "undefined_reason": null
        }
      },
      "by_bucket": {
        "boundary_precision": {
          "support_variant_ids": [
            "P2A-BUG-001",
            "P2A-BUG-002"
          ],
          "saved_discovered_variant_ids": [
            "P2A-BUG-001",
            "P2A-BUG-002"
          ],
          "saved_missed_variant_ids": [],
          "classification_variant_ids": {
            "catalog_unreachable": [],
            "catalog_reachable_not_budget_feasible": [],
            "catalog_reachable_policy_discovered": [
              "P2A-BUG-001",
              "P2A-BUG-002"
            ],
            "catalog_reachable_policy_missed": []
          },
          "saved_policy_discovery_rate": {
            "numerator": 2,
            "denominator": 2,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          },
          "ceiling_discovery_rate": {
            "numerator": 2,
            "denominator": 2,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          },
          "ceiling_gap": {
            "numerator": 0,
            "denominator": 1,
            "fraction": "0/1",
            "decimal": "0",
            "undefined_reason": null
          },
          "budget_feasible_policy_miss_rate": {
            "numerator": 0,
            "denominator": 2,
            "fraction": "0/1",
            "decimal": "0",
            "undefined_reason": null
          }
        },
        "missing_optional_input": {
          "support_variant_ids": [
            "P2A-BUG-003",
            "P2A-BUG-004"
          ],
          "saved_discovered_variant_ids": [],
          "saved_missed_variant_ids": [
            "P2A-BUG-003",
            "P2A-BUG-004"
          ],
          "classification_variant_ids": {
            "catalog_unreachable": [],
            "catalog_reachable_not_budget_feasible": [],
            "catalog_reachable_policy_discovered": [],
            "catalog_reachable_policy_missed": [
              "P2A-BUG-003",
              "P2A-BUG-004"
            ]
          },
          "saved_policy_discovery_rate": {
            "numerator": 0,
            "denominator": 2,
            "fraction": "0/1",
            "decimal": "0",
            "undefined_reason": null
          },
          "ceiling_discovery_rate": {
            "numerator": 2,
            "denominator": 2,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          },
          "ceiling_gap": {
            "numerator": 1,
            "denominator": 1,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          },
          "budget_feasible_policy_miss_rate": {
            "numerator": 2,
            "denominator": 2,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          }
        },
        "config_normalization": {
          "support_variant_ids": [
            "P2A-BUG-005",
            "P2A-BUG-006"
          ],
          "saved_discovered_variant_ids": [],
          "saved_missed_variant_ids": [
            "P2A-BUG-005",
            "P2A-BUG-006"
          ],
          "classification_variant_ids": {
            "catalog_unreachable": [],
            "catalog_reachable_not_budget_feasible": [],
            "catalog_reachable_policy_discovered": [],
            "catalog_reachable_policy_missed": [
              "P2A-BUG-005",
              "P2A-BUG-006"
            ]
          },
          "saved_policy_discovery_rate": {
            "numerator": 0,
            "denominator": 2,
            "fraction": "0/1",
            "decimal": "0",
            "undefined_reason": null
          },
          "ceiling_discovery_rate": {
            "numerator": 2,
            "denominator": 2,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          },
          "ceiling_gap": {
            "numerator": 1,
            "denominator": 1,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          },
          "budget_feasible_policy_miss_rate": {
            "numerator": 2,
            "denominator": 2,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          }
        },
        "state_sequence": {
          "support_variant_ids": [
            "P2A-BUG-007",
            "P2A-BUG-008"
          ],
          "saved_discovered_variant_ids": [],
          "saved_missed_variant_ids": [
            "P2A-BUG-007",
            "P2A-BUG-008"
          ],
          "classification_variant_ids": {
            "catalog_unreachable": [],
            "catalog_reachable_not_budget_feasible": [],
            "catalog_reachable_policy_discovered": [],
            "catalog_reachable_policy_missed": [
              "P2A-BUG-007",
              "P2A-BUG-008"
            ]
          },
          "saved_policy_discovery_rate": {
            "numerator": 0,
            "denominator": 2,
            "fraction": "0/1",
            "decimal": "0",
            "undefined_reason": null
          },
          "ceiling_discovery_rate": {
            "numerator": 2,
            "denominator": 2,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          },
          "ceiling_gap": {
            "numerator": 1,
            "denominator": 1,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          },
          "budget_feasible_policy_miss_rate": {
            "numerator": 2,
            "denominator": 2,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          }
        },
        "spec_semantics": {
          "support_variant_ids": [
            "P2A-BUG-009",
            "P2A-BUG-010"
          ],
          "saved_discovered_variant_ids": [],
          "saved_missed_variant_ids": [
            "P2A-BUG-009",
            "P2A-BUG-010"
          ],
          "classification_variant_ids": {
            "catalog_unreachable": [],
            "catalog_reachable_not_budget_feasible": [],
            "catalog_reachable_policy_discovered": [],
            "catalog_reachable_policy_missed": [
              "P2A-BUG-009",
              "P2A-BUG-010"
            ]
          },
          "saved_policy_discovery_rate": {
            "numerator": 0,
            "denominator": 2,
            "fraction": "0/1",
            "decimal": "0",
            "undefined_reason": null
          },
          "ceiling_discovery_rate": {
            "numerator": 2,
            "denominator": 2,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          },
          "ceiling_gap": {
            "numerator": 1,
            "denominator": 1,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          },
          "budget_feasible_policy_miss_rate": {
            "numerator": 2,
            "denominator": 2,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          }
        }
      }
    },
    "test_first": {
      "overall": {
        "support_variant_ids": [
          "P2A-BUG-001",
          "P2A-BUG-002",
          "P2A-BUG-003",
          "P2A-BUG-004",
          "P2A-BUG-005",
          "P2A-BUG-006",
          "P2A-BUG-007",
          "P2A-BUG-008",
          "P2A-BUG-009",
          "P2A-BUG-010"
        ],
        "saved_discovered_variant_ids": [
          "P2A-BUG-001",
          "P2A-BUG-002"
        ],
        "saved_missed_variant_ids": [
          "P2A-BUG-003",
          "P2A-BUG-004",
          "P2A-BUG-005",
          "P2A-BUG-006",
          "P2A-BUG-007",
          "P2A-BUG-008",
          "P2A-BUG-009",
          "P2A-BUG-010"
        ],
        "classification_variant_ids": {
          "catalog_unreachable": [],
          "catalog_reachable_not_budget_feasible": [],
          "catalog_reachable_policy_discovered": [
            "P2A-BUG-001",
            "P2A-BUG-002"
          ],
          "catalog_reachable_policy_missed": [
            "P2A-BUG-003",
            "P2A-BUG-004",
            "P2A-BUG-005",
            "P2A-BUG-006",
            "P2A-BUG-007",
            "P2A-BUG-008",
            "P2A-BUG-009",
            "P2A-BUG-010"
          ]
        },
        "saved_policy_discovery_rate": {
          "numerator": 2,
          "denominator": 10,
          "fraction": "1/5",
          "decimal": "0.2",
          "undefined_reason": null
        },
        "ceiling_discovery_rate": {
          "numerator": 10,
          "denominator": 10,
          "fraction": "1/1",
          "decimal": "1",
          "undefined_reason": null
        },
        "ceiling_gap": {
          "numerator": 4,
          "denominator": 5,
          "fraction": "4/5",
          "decimal": "0.8",
          "undefined_reason": null
        },
        "budget_feasible_policy_miss_rate": {
          "numerator": 8,
          "denominator": 10,
          "fraction": "4/5",
          "decimal": "0.8",
          "undefined_reason": null
        }
      },
      "by_bucket": {
        "boundary_precision": {
          "support_variant_ids": [
            "P2A-BUG-001",
            "P2A-BUG-002"
          ],
          "saved_discovered_variant_ids": [
            "P2A-BUG-001",
            "P2A-BUG-002"
          ],
          "saved_missed_variant_ids": [],
          "classification_variant_ids": {
            "catalog_unreachable": [],
            "catalog_reachable_not_budget_feasible": [],
            "catalog_reachable_policy_discovered": [
              "P2A-BUG-001",
              "P2A-BUG-002"
            ],
            "catalog_reachable_policy_missed": []
          },
          "saved_policy_discovery_rate": {
            "numerator": 2,
            "denominator": 2,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          },
          "ceiling_discovery_rate": {
            "numerator": 2,
            "denominator": 2,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          },
          "ceiling_gap": {
            "numerator": 0,
            "denominator": 1,
            "fraction": "0/1",
            "decimal": "0",
            "undefined_reason": null
          },
          "budget_feasible_policy_miss_rate": {
            "numerator": 0,
            "denominator": 2,
            "fraction": "0/1",
            "decimal": "0",
            "undefined_reason": null
          }
        },
        "missing_optional_input": {
          "support_variant_ids": [
            "P2A-BUG-003",
            "P2A-BUG-004"
          ],
          "saved_discovered_variant_ids": [],
          "saved_missed_variant_ids": [
            "P2A-BUG-003",
            "P2A-BUG-004"
          ],
          "classification_variant_ids": {
            "catalog_unreachable": [],
            "catalog_reachable_not_budget_feasible": [],
            "catalog_reachable_policy_discovered": [],
            "catalog_reachable_policy_missed": [
              "P2A-BUG-003",
              "P2A-BUG-004"
            ]
          },
          "saved_policy_discovery_rate": {
            "numerator": 0,
            "denominator": 2,
            "fraction": "0/1",
            "decimal": "0",
            "undefined_reason": null
          },
          "ceiling_discovery_rate": {
            "numerator": 2,
            "denominator": 2,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          },
          "ceiling_gap": {
            "numerator": 1,
            "denominator": 1,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          },
          "budget_feasible_policy_miss_rate": {
            "numerator": 2,
            "denominator": 2,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          }
        },
        "config_normalization": {
          "support_variant_ids": [
            "P2A-BUG-005",
            "P2A-BUG-006"
          ],
          "saved_discovered_variant_ids": [],
          "saved_missed_variant_ids": [
            "P2A-BUG-005",
            "P2A-BUG-006"
          ],
          "classification_variant_ids": {
            "catalog_unreachable": [],
            "catalog_reachable_not_budget_feasible": [],
            "catalog_reachable_policy_discovered": [],
            "catalog_reachable_policy_missed": [
              "P2A-BUG-005",
              "P2A-BUG-006"
            ]
          },
          "saved_policy_discovery_rate": {
            "numerator": 0,
            "denominator": 2,
            "fraction": "0/1",
            "decimal": "0",
            "undefined_reason": null
          },
          "ceiling_discovery_rate": {
            "numerator": 2,
            "denominator": 2,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          },
          "ceiling_gap": {
            "numerator": 1,
            "denominator": 1,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          },
          "budget_feasible_policy_miss_rate": {
            "numerator": 2,
            "denominator": 2,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          }
        },
        "state_sequence": {
          "support_variant_ids": [
            "P2A-BUG-007",
            "P2A-BUG-008"
          ],
          "saved_discovered_variant_ids": [],
          "saved_missed_variant_ids": [
            "P2A-BUG-007",
            "P2A-BUG-008"
          ],
          "classification_variant_ids": {
            "catalog_unreachable": [],
            "catalog_reachable_not_budget_feasible": [],
            "catalog_reachable_policy_discovered": [],
            "catalog_reachable_policy_missed": [
              "P2A-BUG-007",
              "P2A-BUG-008"
            ]
          },
          "saved_policy_discovery_rate": {
            "numerator": 0,
            "denominator": 2,
            "fraction": "0/1",
            "decimal": "0",
            "undefined_reason": null
          },
          "ceiling_discovery_rate": {
            "numerator": 2,
            "denominator": 2,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          },
          "ceiling_gap": {
            "numerator": 1,
            "denominator": 1,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          },
          "budget_feasible_policy_miss_rate": {
            "numerator": 2,
            "denominator": 2,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          }
        },
        "spec_semantics": {
          "support_variant_ids": [
            "P2A-BUG-009",
            "P2A-BUG-010"
          ],
          "saved_discovered_variant_ids": [],
          "saved_missed_variant_ids": [
            "P2A-BUG-009",
            "P2A-BUG-010"
          ],
          "classification_variant_ids": {
            "catalog_unreachable": [],
            "catalog_reachable_not_budget_feasible": [],
            "catalog_reachable_policy_discovered": [],
            "catalog_reachable_policy_missed": [
              "P2A-BUG-009",
              "P2A-BUG-010"
            ]
          },
          "saved_policy_discovery_rate": {
            "numerator": 0,
            "denominator": 2,
            "fraction": "0/1",
            "decimal": "0",
            "undefined_reason": null
          },
          "ceiling_discovery_rate": {
            "numerator": 2,
            "denominator": 2,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          },
          "ceiling_gap": {
            "numerator": 1,
            "denominator": 1,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          },
          "budget_feasible_policy_miss_rate": {
            "numerator": 2,
            "denominator": 2,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          }
        }
      }
    },
    "coverage_first": {
      "overall": {
        "support_variant_ids": [
          "P2A-BUG-001",
          "P2A-BUG-002",
          "P2A-BUG-003",
          "P2A-BUG-004",
          "P2A-BUG-005",
          "P2A-BUG-006",
          "P2A-BUG-007",
          "P2A-BUG-008",
          "P2A-BUG-009",
          "P2A-BUG-010"
        ],
        "saved_discovered_variant_ids": [
          "P2A-BUG-001",
          "P2A-BUG-002"
        ],
        "saved_missed_variant_ids": [
          "P2A-BUG-003",
          "P2A-BUG-004",
          "P2A-BUG-005",
          "P2A-BUG-006",
          "P2A-BUG-007",
          "P2A-BUG-008",
          "P2A-BUG-009",
          "P2A-BUG-010"
        ],
        "classification_variant_ids": {
          "catalog_unreachable": [],
          "catalog_reachable_not_budget_feasible": [],
          "catalog_reachable_policy_discovered": [
            "P2A-BUG-001",
            "P2A-BUG-002"
          ],
          "catalog_reachable_policy_missed": [
            "P2A-BUG-003",
            "P2A-BUG-004",
            "P2A-BUG-005",
            "P2A-BUG-006",
            "P2A-BUG-007",
            "P2A-BUG-008",
            "P2A-BUG-009",
            "P2A-BUG-010"
          ]
        },
        "saved_policy_discovery_rate": {
          "numerator": 2,
          "denominator": 10,
          "fraction": "1/5",
          "decimal": "0.2",
          "undefined_reason": null
        },
        "ceiling_discovery_rate": {
          "numerator": 10,
          "denominator": 10,
          "fraction": "1/1",
          "decimal": "1",
          "undefined_reason": null
        },
        "ceiling_gap": {
          "numerator": 4,
          "denominator": 5,
          "fraction": "4/5",
          "decimal": "0.8",
          "undefined_reason": null
        },
        "budget_feasible_policy_miss_rate": {
          "numerator": 8,
          "denominator": 10,
          "fraction": "4/5",
          "decimal": "0.8",
          "undefined_reason": null
        }
      },
      "by_bucket": {
        "boundary_precision": {
          "support_variant_ids": [
            "P2A-BUG-001",
            "P2A-BUG-002"
          ],
          "saved_discovered_variant_ids": [
            "P2A-BUG-001",
            "P2A-BUG-002"
          ],
          "saved_missed_variant_ids": [],
          "classification_variant_ids": {
            "catalog_unreachable": [],
            "catalog_reachable_not_budget_feasible": [],
            "catalog_reachable_policy_discovered": [
              "P2A-BUG-001",
              "P2A-BUG-002"
            ],
            "catalog_reachable_policy_missed": []
          },
          "saved_policy_discovery_rate": {
            "numerator": 2,
            "denominator": 2,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          },
          "ceiling_discovery_rate": {
            "numerator": 2,
            "denominator": 2,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          },
          "ceiling_gap": {
            "numerator": 0,
            "denominator": 1,
            "fraction": "0/1",
            "decimal": "0",
            "undefined_reason": null
          },
          "budget_feasible_policy_miss_rate": {
            "numerator": 0,
            "denominator": 2,
            "fraction": "0/1",
            "decimal": "0",
            "undefined_reason": null
          }
        },
        "missing_optional_input": {
          "support_variant_ids": [
            "P2A-BUG-003",
            "P2A-BUG-004"
          ],
          "saved_discovered_variant_ids": [],
          "saved_missed_variant_ids": [
            "P2A-BUG-003",
            "P2A-BUG-004"
          ],
          "classification_variant_ids": {
            "catalog_unreachable": [],
            "catalog_reachable_not_budget_feasible": [],
            "catalog_reachable_policy_discovered": [],
            "catalog_reachable_policy_missed": [
              "P2A-BUG-003",
              "P2A-BUG-004"
            ]
          },
          "saved_policy_discovery_rate": {
            "numerator": 0,
            "denominator": 2,
            "fraction": "0/1",
            "decimal": "0",
            "undefined_reason": null
          },
          "ceiling_discovery_rate": {
            "numerator": 2,
            "denominator": 2,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          },
          "ceiling_gap": {
            "numerator": 1,
            "denominator": 1,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          },
          "budget_feasible_policy_miss_rate": {
            "numerator": 2,
            "denominator": 2,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          }
        },
        "config_normalization": {
          "support_variant_ids": [
            "P2A-BUG-005",
            "P2A-BUG-006"
          ],
          "saved_discovered_variant_ids": [],
          "saved_missed_variant_ids": [
            "P2A-BUG-005",
            "P2A-BUG-006"
          ],
          "classification_variant_ids": {
            "catalog_unreachable": [],
            "catalog_reachable_not_budget_feasible": [],
            "catalog_reachable_policy_discovered": [],
            "catalog_reachable_policy_missed": [
              "P2A-BUG-005",
              "P2A-BUG-006"
            ]
          },
          "saved_policy_discovery_rate": {
            "numerator": 0,
            "denominator": 2,
            "fraction": "0/1",
            "decimal": "0",
            "undefined_reason": null
          },
          "ceiling_discovery_rate": {
            "numerator": 2,
            "denominator": 2,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          },
          "ceiling_gap": {
            "numerator": 1,
            "denominator": 1,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          },
          "budget_feasible_policy_miss_rate": {
            "numerator": 2,
            "denominator": 2,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          }
        },
        "state_sequence": {
          "support_variant_ids": [
            "P2A-BUG-007",
            "P2A-BUG-008"
          ],
          "saved_discovered_variant_ids": [],
          "saved_missed_variant_ids": [
            "P2A-BUG-007",
            "P2A-BUG-008"
          ],
          "classification_variant_ids": {
            "catalog_unreachable": [],
            "catalog_reachable_not_budget_feasible": [],
            "catalog_reachable_policy_discovered": [],
            "catalog_reachable_policy_missed": [
              "P2A-BUG-007",
              "P2A-BUG-008"
            ]
          },
          "saved_policy_discovery_rate": {
            "numerator": 0,
            "denominator": 2,
            "fraction": "0/1",
            "decimal": "0",
            "undefined_reason": null
          },
          "ceiling_discovery_rate": {
            "numerator": 2,
            "denominator": 2,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          },
          "ceiling_gap": {
            "numerator": 1,
            "denominator": 1,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          },
          "budget_feasible_policy_miss_rate": {
            "numerator": 2,
            "denominator": 2,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          }
        },
        "spec_semantics": {
          "support_variant_ids": [
            "P2A-BUG-009",
            "P2A-BUG-010"
          ],
          "saved_discovered_variant_ids": [],
          "saved_missed_variant_ids": [
            "P2A-BUG-009",
            "P2A-BUG-010"
          ],
          "classification_variant_ids": {
            "catalog_unreachable": [],
            "catalog_reachable_not_budget_feasible": [],
            "catalog_reachable_policy_discovered": [],
            "catalog_reachable_policy_missed": [
              "P2A-BUG-009",
              "P2A-BUG-010"
            ]
          },
          "saved_policy_discovery_rate": {
            "numerator": 0,
            "denominator": 2,
            "fraction": "0/1",
            "decimal": "0",
            "undefined_reason": null
          },
          "ceiling_discovery_rate": {
            "numerator": 2,
            "denominator": 2,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          },
          "ceiling_gap": {
            "numerator": 1,
            "denominator": 1,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          },
          "budget_feasible_policy_miss_rate": {
            "numerator": 2,
            "denominator": 2,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          }
        }
      }
    },
    "recent_diff_first": {
      "overall": {
        "support_variant_ids": [
          "P2A-BUG-001",
          "P2A-BUG-002",
          "P2A-BUG-003",
          "P2A-BUG-004",
          "P2A-BUG-005",
          "P2A-BUG-006",
          "P2A-BUG-007",
          "P2A-BUG-008",
          "P2A-BUG-009",
          "P2A-BUG-010"
        ],
        "saved_discovered_variant_ids": [
          "P2A-BUG-001",
          "P2A-BUG-002"
        ],
        "saved_missed_variant_ids": [
          "P2A-BUG-003",
          "P2A-BUG-004",
          "P2A-BUG-005",
          "P2A-BUG-006",
          "P2A-BUG-007",
          "P2A-BUG-008",
          "P2A-BUG-009",
          "P2A-BUG-010"
        ],
        "classification_variant_ids": {
          "catalog_unreachable": [],
          "catalog_reachable_not_budget_feasible": [],
          "catalog_reachable_policy_discovered": [
            "P2A-BUG-001",
            "P2A-BUG-002"
          ],
          "catalog_reachable_policy_missed": [
            "P2A-BUG-003",
            "P2A-BUG-004",
            "P2A-BUG-005",
            "P2A-BUG-006",
            "P2A-BUG-007",
            "P2A-BUG-008",
            "P2A-BUG-009",
            "P2A-BUG-010"
          ]
        },
        "saved_policy_discovery_rate": {
          "numerator": 2,
          "denominator": 10,
          "fraction": "1/5",
          "decimal": "0.2",
          "undefined_reason": null
        },
        "ceiling_discovery_rate": {
          "numerator": 10,
          "denominator": 10,
          "fraction": "1/1",
          "decimal": "1",
          "undefined_reason": null
        },
        "ceiling_gap": {
          "numerator": 4,
          "denominator": 5,
          "fraction": "4/5",
          "decimal": "0.8",
          "undefined_reason": null
        },
        "budget_feasible_policy_miss_rate": {
          "numerator": 8,
          "denominator": 10,
          "fraction": "4/5",
          "decimal": "0.8",
          "undefined_reason": null
        }
      },
      "by_bucket": {
        "boundary_precision": {
          "support_variant_ids": [
            "P2A-BUG-001",
            "P2A-BUG-002"
          ],
          "saved_discovered_variant_ids": [
            "P2A-BUG-001",
            "P2A-BUG-002"
          ],
          "saved_missed_variant_ids": [],
          "classification_variant_ids": {
            "catalog_unreachable": [],
            "catalog_reachable_not_budget_feasible": [],
            "catalog_reachable_policy_discovered": [
              "P2A-BUG-001",
              "P2A-BUG-002"
            ],
            "catalog_reachable_policy_missed": []
          },
          "saved_policy_discovery_rate": {
            "numerator": 2,
            "denominator": 2,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          },
          "ceiling_discovery_rate": {
            "numerator": 2,
            "denominator": 2,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          },
          "ceiling_gap": {
            "numerator": 0,
            "denominator": 1,
            "fraction": "0/1",
            "decimal": "0",
            "undefined_reason": null
          },
          "budget_feasible_policy_miss_rate": {
            "numerator": 0,
            "denominator": 2,
            "fraction": "0/1",
            "decimal": "0",
            "undefined_reason": null
          }
        },
        "missing_optional_input": {
          "support_variant_ids": [
            "P2A-BUG-003",
            "P2A-BUG-004"
          ],
          "saved_discovered_variant_ids": [],
          "saved_missed_variant_ids": [
            "P2A-BUG-003",
            "P2A-BUG-004"
          ],
          "classification_variant_ids": {
            "catalog_unreachable": [],
            "catalog_reachable_not_budget_feasible": [],
            "catalog_reachable_policy_discovered": [],
            "catalog_reachable_policy_missed": [
              "P2A-BUG-003",
              "P2A-BUG-004"
            ]
          },
          "saved_policy_discovery_rate": {
            "numerator": 0,
            "denominator": 2,
            "fraction": "0/1",
            "decimal": "0",
            "undefined_reason": null
          },
          "ceiling_discovery_rate": {
            "numerator": 2,
            "denominator": 2,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          },
          "ceiling_gap": {
            "numerator": 1,
            "denominator": 1,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          },
          "budget_feasible_policy_miss_rate": {
            "numerator": 2,
            "denominator": 2,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          }
        },
        "config_normalization": {
          "support_variant_ids": [
            "P2A-BUG-005",
            "P2A-BUG-006"
          ],
          "saved_discovered_variant_ids": [],
          "saved_missed_variant_ids": [
            "P2A-BUG-005",
            "P2A-BUG-006"
          ],
          "classification_variant_ids": {
            "catalog_unreachable": [],
            "catalog_reachable_not_budget_feasible": [],
            "catalog_reachable_policy_discovered": [],
            "catalog_reachable_policy_missed": [
              "P2A-BUG-005",
              "P2A-BUG-006"
            ]
          },
          "saved_policy_discovery_rate": {
            "numerator": 0,
            "denominator": 2,
            "fraction": "0/1",
            "decimal": "0",
            "undefined_reason": null
          },
          "ceiling_discovery_rate": {
            "numerator": 2,
            "denominator": 2,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          },
          "ceiling_gap": {
            "numerator": 1,
            "denominator": 1,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          },
          "budget_feasible_policy_miss_rate": {
            "numerator": 2,
            "denominator": 2,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          }
        },
        "state_sequence": {
          "support_variant_ids": [
            "P2A-BUG-007",
            "P2A-BUG-008"
          ],
          "saved_discovered_variant_ids": [],
          "saved_missed_variant_ids": [
            "P2A-BUG-007",
            "P2A-BUG-008"
          ],
          "classification_variant_ids": {
            "catalog_unreachable": [],
            "catalog_reachable_not_budget_feasible": [],
            "catalog_reachable_policy_discovered": [],
            "catalog_reachable_policy_missed": [
              "P2A-BUG-007",
              "P2A-BUG-008"
            ]
          },
          "saved_policy_discovery_rate": {
            "numerator": 0,
            "denominator": 2,
            "fraction": "0/1",
            "decimal": "0",
            "undefined_reason": null
          },
          "ceiling_discovery_rate": {
            "numerator": 2,
            "denominator": 2,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          },
          "ceiling_gap": {
            "numerator": 1,
            "denominator": 1,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          },
          "budget_feasible_policy_miss_rate": {
            "numerator": 2,
            "denominator": 2,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          }
        },
        "spec_semantics": {
          "support_variant_ids": [
            "P2A-BUG-009",
            "P2A-BUG-010"
          ],
          "saved_discovered_variant_ids": [],
          "saved_missed_variant_ids": [
            "P2A-BUG-009",
            "P2A-BUG-010"
          ],
          "classification_variant_ids": {
            "catalog_unreachable": [],
            "catalog_reachable_not_budget_feasible": [],
            "catalog_reachable_policy_discovered": [],
            "catalog_reachable_policy_missed": [
              "P2A-BUG-009",
              "P2A-BUG-010"
            ]
          },
          "saved_policy_discovery_rate": {
            "numerator": 0,
            "denominator": 2,
            "fraction": "0/1",
            "decimal": "0",
            "undefined_reason": null
          },
          "ceiling_discovery_rate": {
            "numerator": 2,
            "denominator": 2,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          },
          "ceiling_gap": {
            "numerator": 1,
            "denominator": 1,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          },
          "budget_feasible_policy_miss_rate": {
            "numerator": 2,
            "denominator": 2,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          }
        }
      }
    },
    "cause_only_p1a_style": {
      "overall": {
        "support_variant_ids": [
          "P2A-BUG-001",
          "P2A-BUG-002",
          "P2A-BUG-003",
          "P2A-BUG-004",
          "P2A-BUG-005",
          "P2A-BUG-006",
          "P2A-BUG-007",
          "P2A-BUG-008",
          "P2A-BUG-009",
          "P2A-BUG-010"
        ],
        "saved_discovered_variant_ids": [],
        "saved_missed_variant_ids": [
          "P2A-BUG-001",
          "P2A-BUG-002",
          "P2A-BUG-003",
          "P2A-BUG-004",
          "P2A-BUG-005",
          "P2A-BUG-006",
          "P2A-BUG-007",
          "P2A-BUG-008",
          "P2A-BUG-009",
          "P2A-BUG-010"
        ],
        "classification_variant_ids": {
          "catalog_unreachable": [],
          "catalog_reachable_not_budget_feasible": [],
          "catalog_reachable_policy_discovered": [],
          "catalog_reachable_policy_missed": [
            "P2A-BUG-001",
            "P2A-BUG-002",
            "P2A-BUG-003",
            "P2A-BUG-004",
            "P2A-BUG-005",
            "P2A-BUG-006",
            "P2A-BUG-007",
            "P2A-BUG-008",
            "P2A-BUG-009",
            "P2A-BUG-010"
          ]
        },
        "saved_policy_discovery_rate": {
          "numerator": 0,
          "denominator": 10,
          "fraction": "0/1",
          "decimal": "0",
          "undefined_reason": null
        },
        "ceiling_discovery_rate": {
          "numerator": 10,
          "denominator": 10,
          "fraction": "1/1",
          "decimal": "1",
          "undefined_reason": null
        },
        "ceiling_gap": {
          "numerator": 1,
          "denominator": 1,
          "fraction": "1/1",
          "decimal": "1",
          "undefined_reason": null
        },
        "budget_feasible_policy_miss_rate": {
          "numerator": 10,
          "denominator": 10,
          "fraction": "1/1",
          "decimal": "1",
          "undefined_reason": null
        }
      },
      "by_bucket": {
        "boundary_precision": {
          "support_variant_ids": [
            "P2A-BUG-001",
            "P2A-BUG-002"
          ],
          "saved_discovered_variant_ids": [],
          "saved_missed_variant_ids": [
            "P2A-BUG-001",
            "P2A-BUG-002"
          ],
          "classification_variant_ids": {
            "catalog_unreachable": [],
            "catalog_reachable_not_budget_feasible": [],
            "catalog_reachable_policy_discovered": [],
            "catalog_reachable_policy_missed": [
              "P2A-BUG-001",
              "P2A-BUG-002"
            ]
          },
          "saved_policy_discovery_rate": {
            "numerator": 0,
            "denominator": 2,
            "fraction": "0/1",
            "decimal": "0",
            "undefined_reason": null
          },
          "ceiling_discovery_rate": {
            "numerator": 2,
            "denominator": 2,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          },
          "ceiling_gap": {
            "numerator": 1,
            "denominator": 1,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          },
          "budget_feasible_policy_miss_rate": {
            "numerator": 2,
            "denominator": 2,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          }
        },
        "missing_optional_input": {
          "support_variant_ids": [
            "P2A-BUG-003",
            "P2A-BUG-004"
          ],
          "saved_discovered_variant_ids": [],
          "saved_missed_variant_ids": [
            "P2A-BUG-003",
            "P2A-BUG-004"
          ],
          "classification_variant_ids": {
            "catalog_unreachable": [],
            "catalog_reachable_not_budget_feasible": [],
            "catalog_reachable_policy_discovered": [],
            "catalog_reachable_policy_missed": [
              "P2A-BUG-003",
              "P2A-BUG-004"
            ]
          },
          "saved_policy_discovery_rate": {
            "numerator": 0,
            "denominator": 2,
            "fraction": "0/1",
            "decimal": "0",
            "undefined_reason": null
          },
          "ceiling_discovery_rate": {
            "numerator": 2,
            "denominator": 2,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          },
          "ceiling_gap": {
            "numerator": 1,
            "denominator": 1,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          },
          "budget_feasible_policy_miss_rate": {
            "numerator": 2,
            "denominator": 2,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          }
        },
        "config_normalization": {
          "support_variant_ids": [
            "P2A-BUG-005",
            "P2A-BUG-006"
          ],
          "saved_discovered_variant_ids": [],
          "saved_missed_variant_ids": [
            "P2A-BUG-005",
            "P2A-BUG-006"
          ],
          "classification_variant_ids": {
            "catalog_unreachable": [],
            "catalog_reachable_not_budget_feasible": [],
            "catalog_reachable_policy_discovered": [],
            "catalog_reachable_policy_missed": [
              "P2A-BUG-005",
              "P2A-BUG-006"
            ]
          },
          "saved_policy_discovery_rate": {
            "numerator": 0,
            "denominator": 2,
            "fraction": "0/1",
            "decimal": "0",
            "undefined_reason": null
          },
          "ceiling_discovery_rate": {
            "numerator": 2,
            "denominator": 2,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          },
          "ceiling_gap": {
            "numerator": 1,
            "denominator": 1,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          },
          "budget_feasible_policy_miss_rate": {
            "numerator": 2,
            "denominator": 2,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          }
        },
        "state_sequence": {
          "support_variant_ids": [
            "P2A-BUG-007",
            "P2A-BUG-008"
          ],
          "saved_discovered_variant_ids": [],
          "saved_missed_variant_ids": [
            "P2A-BUG-007",
            "P2A-BUG-008"
          ],
          "classification_variant_ids": {
            "catalog_unreachable": [],
            "catalog_reachable_not_budget_feasible": [],
            "catalog_reachable_policy_discovered": [],
            "catalog_reachable_policy_missed": [
              "P2A-BUG-007",
              "P2A-BUG-008"
            ]
          },
          "saved_policy_discovery_rate": {
            "numerator": 0,
            "denominator": 2,
            "fraction": "0/1",
            "decimal": "0",
            "undefined_reason": null
          },
          "ceiling_discovery_rate": {
            "numerator": 2,
            "denominator": 2,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          },
          "ceiling_gap": {
            "numerator": 1,
            "denominator": 1,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          },
          "budget_feasible_policy_miss_rate": {
            "numerator": 2,
            "denominator": 2,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          }
        },
        "spec_semantics": {
          "support_variant_ids": [
            "P2A-BUG-009",
            "P2A-BUG-010"
          ],
          "saved_discovered_variant_ids": [],
          "saved_missed_variant_ids": [
            "P2A-BUG-009",
            "P2A-BUG-010"
          ],
          "classification_variant_ids": {
            "catalog_unreachable": [],
            "catalog_reachable_not_budget_feasible": [],
            "catalog_reachable_policy_discovered": [],
            "catalog_reachable_policy_missed": [
              "P2A-BUG-009",
              "P2A-BUG-010"
            ]
          },
          "saved_policy_discovery_rate": {
            "numerator": 0,
            "denominator": 2,
            "fraction": "0/1",
            "decimal": "0",
            "undefined_reason": null
          },
          "ceiling_discovery_rate": {
            "numerator": 2,
            "denominator": 2,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          },
          "ceiling_gap": {
            "numerator": 1,
            "denominator": 1,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          },
          "budget_feasible_policy_miss_rate": {
            "numerator": 2,
            "denominator": 2,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          }
        }
      }
    },
    "expected_utility_per_cost": {
      "overall": {
        "support_variant_ids": [
          "P2A-BUG-001",
          "P2A-BUG-002",
          "P2A-BUG-003",
          "P2A-BUG-004",
          "P2A-BUG-005",
          "P2A-BUG-006",
          "P2A-BUG-007",
          "P2A-BUG-008",
          "P2A-BUG-009",
          "P2A-BUG-010"
        ],
        "saved_discovered_variant_ids": [],
        "saved_missed_variant_ids": [
          "P2A-BUG-001",
          "P2A-BUG-002",
          "P2A-BUG-003",
          "P2A-BUG-004",
          "P2A-BUG-005",
          "P2A-BUG-006",
          "P2A-BUG-007",
          "P2A-BUG-008",
          "P2A-BUG-009",
          "P2A-BUG-010"
        ],
        "classification_variant_ids": {
          "catalog_unreachable": [],
          "catalog_reachable_not_budget_feasible": [],
          "catalog_reachable_policy_discovered": [],
          "catalog_reachable_policy_missed": [
            "P2A-BUG-001",
            "P2A-BUG-002",
            "P2A-BUG-003",
            "P2A-BUG-004",
            "P2A-BUG-005",
            "P2A-BUG-006",
            "P2A-BUG-007",
            "P2A-BUG-008",
            "P2A-BUG-009",
            "P2A-BUG-010"
          ]
        },
        "saved_policy_discovery_rate": {
          "numerator": 0,
          "denominator": 10,
          "fraction": "0/1",
          "decimal": "0",
          "undefined_reason": null
        },
        "ceiling_discovery_rate": {
          "numerator": 10,
          "denominator": 10,
          "fraction": "1/1",
          "decimal": "1",
          "undefined_reason": null
        },
        "ceiling_gap": {
          "numerator": 1,
          "denominator": 1,
          "fraction": "1/1",
          "decimal": "1",
          "undefined_reason": null
        },
        "budget_feasible_policy_miss_rate": {
          "numerator": 10,
          "denominator": 10,
          "fraction": "1/1",
          "decimal": "1",
          "undefined_reason": null
        }
      },
      "by_bucket": {
        "boundary_precision": {
          "support_variant_ids": [
            "P2A-BUG-001",
            "P2A-BUG-002"
          ],
          "saved_discovered_variant_ids": [],
          "saved_missed_variant_ids": [
            "P2A-BUG-001",
            "P2A-BUG-002"
          ],
          "classification_variant_ids": {
            "catalog_unreachable": [],
            "catalog_reachable_not_budget_feasible": [],
            "catalog_reachable_policy_discovered": [],
            "catalog_reachable_policy_missed": [
              "P2A-BUG-001",
              "P2A-BUG-002"
            ]
          },
          "saved_policy_discovery_rate": {
            "numerator": 0,
            "denominator": 2,
            "fraction": "0/1",
            "decimal": "0",
            "undefined_reason": null
          },
          "ceiling_discovery_rate": {
            "numerator": 2,
            "denominator": 2,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          },
          "ceiling_gap": {
            "numerator": 1,
            "denominator": 1,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          },
          "budget_feasible_policy_miss_rate": {
            "numerator": 2,
            "denominator": 2,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          }
        },
        "missing_optional_input": {
          "support_variant_ids": [
            "P2A-BUG-003",
            "P2A-BUG-004"
          ],
          "saved_discovered_variant_ids": [],
          "saved_missed_variant_ids": [
            "P2A-BUG-003",
            "P2A-BUG-004"
          ],
          "classification_variant_ids": {
            "catalog_unreachable": [],
            "catalog_reachable_not_budget_feasible": [],
            "catalog_reachable_policy_discovered": [],
            "catalog_reachable_policy_missed": [
              "P2A-BUG-003",
              "P2A-BUG-004"
            ]
          },
          "saved_policy_discovery_rate": {
            "numerator": 0,
            "denominator": 2,
            "fraction": "0/1",
            "decimal": "0",
            "undefined_reason": null
          },
          "ceiling_discovery_rate": {
            "numerator": 2,
            "denominator": 2,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          },
          "ceiling_gap": {
            "numerator": 1,
            "denominator": 1,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          },
          "budget_feasible_policy_miss_rate": {
            "numerator": 2,
            "denominator": 2,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          }
        },
        "config_normalization": {
          "support_variant_ids": [
            "P2A-BUG-005",
            "P2A-BUG-006"
          ],
          "saved_discovered_variant_ids": [],
          "saved_missed_variant_ids": [
            "P2A-BUG-005",
            "P2A-BUG-006"
          ],
          "classification_variant_ids": {
            "catalog_unreachable": [],
            "catalog_reachable_not_budget_feasible": [],
            "catalog_reachable_policy_discovered": [],
            "catalog_reachable_policy_missed": [
              "P2A-BUG-005",
              "P2A-BUG-006"
            ]
          },
          "saved_policy_discovery_rate": {
            "numerator": 0,
            "denominator": 2,
            "fraction": "0/1",
            "decimal": "0",
            "undefined_reason": null
          },
          "ceiling_discovery_rate": {
            "numerator": 2,
            "denominator": 2,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          },
          "ceiling_gap": {
            "numerator": 1,
            "denominator": 1,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          },
          "budget_feasible_policy_miss_rate": {
            "numerator": 2,
            "denominator": 2,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          }
        },
        "state_sequence": {
          "support_variant_ids": [
            "P2A-BUG-007",
            "P2A-BUG-008"
          ],
          "saved_discovered_variant_ids": [],
          "saved_missed_variant_ids": [
            "P2A-BUG-007",
            "P2A-BUG-008"
          ],
          "classification_variant_ids": {
            "catalog_unreachable": [],
            "catalog_reachable_not_budget_feasible": [],
            "catalog_reachable_policy_discovered": [],
            "catalog_reachable_policy_missed": [
              "P2A-BUG-007",
              "P2A-BUG-008"
            ]
          },
          "saved_policy_discovery_rate": {
            "numerator": 0,
            "denominator": 2,
            "fraction": "0/1",
            "decimal": "0",
            "undefined_reason": null
          },
          "ceiling_discovery_rate": {
            "numerator": 2,
            "denominator": 2,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          },
          "ceiling_gap": {
            "numerator": 1,
            "denominator": 1,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          },
          "budget_feasible_policy_miss_rate": {
            "numerator": 2,
            "denominator": 2,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          }
        },
        "spec_semantics": {
          "support_variant_ids": [
            "P2A-BUG-009",
            "P2A-BUG-010"
          ],
          "saved_discovered_variant_ids": [],
          "saved_missed_variant_ids": [
            "P2A-BUG-009",
            "P2A-BUG-010"
          ],
          "classification_variant_ids": {
            "catalog_unreachable": [],
            "catalog_reachable_not_budget_feasible": [],
            "catalog_reachable_policy_discovered": [],
            "catalog_reachable_policy_missed": [
              "P2A-BUG-009",
              "P2A-BUG-010"
            ]
          },
          "saved_policy_discovery_rate": {
            "numerator": 0,
            "denominator": 2,
            "fraction": "0/1",
            "decimal": "0",
            "undefined_reason": null
          },
          "ceiling_discovery_rate": {
            "numerator": 2,
            "denominator": 2,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          },
          "ceiling_gap": {
            "numerator": 1,
            "denominator": 1,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          },
          "budget_feasible_policy_miss_rate": {
            "numerator": 2,
            "denominator": 2,
            "fraction": "1/1",
            "decimal": "1",
            "undefined_reason": null
          }
        }
      }
    }
  },
  "overall_diagnostic": {
    "support_variant_ids": [
      "P2A-BUG-001",
      "P2A-BUG-002",
      "P2A-BUG-003",
      "P2A-BUG-004",
      "P2A-BUG-005",
      "P2A-BUG-006",
      "P2A-BUG-007",
      "P2A-BUG-008",
      "P2A-BUG-009",
      "P2A-BUG-010"
    ],
    "catalog_reachable_variant_ids": [
      "P2A-BUG-001",
      "P2A-BUG-002",
      "P2A-BUG-003",
      "P2A-BUG-004",
      "P2A-BUG-005",
      "P2A-BUG-006",
      "P2A-BUG-007",
      "P2A-BUG-008",
      "P2A-BUG-009",
      "P2A-BUG-010"
    ],
    "catalog_unreachable_variant_ids": [],
    "budget_feasible_variant_ids": [
      "P2A-BUG-001",
      "P2A-BUG-002",
      "P2A-BUG-003",
      "P2A-BUG-004",
      "P2A-BUG-005",
      "P2A-BUG-006",
      "P2A-BUG-007",
      "P2A-BUG-008",
      "P2A-BUG-009",
      "P2A-BUG-010"
    ],
    "catalog_reachable_not_budget_feasible_variant_ids": [],
    "catalog_reachability_rate": {
      "numerator": 10,
      "denominator": 10,
      "fraction": "1/1",
      "decimal": "1",
      "undefined_reason": null
    },
    "ceiling_discovery_rate": {
      "numerator": 10,
      "denominator": 10,
      "fraction": "1/1",
      "decimal": "1",
      "undefined_reason": null
    },
    "ceiling_discovery_loss": {
      "numerator": 0,
      "denominator": 10,
      "fraction": "0/1",
      "decimal": "0",
      "undefined_reason": null
    },
    "minimum_detecting_cost_by_variant": {
      "P2A-BUG-001": 2,
      "P2A-BUG-002": 2,
      "P2A-BUG-003": 2,
      "P2A-BUG-004": 2,
      "P2A-BUG-005": 3,
      "P2A-BUG-006": 3,
      "P2A-BUG-007": 4,
      "P2A-BUG-008": 4,
      "P2A-BUG-009": 2,
      "P2A-BUG-010": 2
    },
    "uniform_over_buckets_ceiling_loss": {
      "numerator": 0,
      "denominator": 1,
      "fraction": "0/1",
      "decimal": "0",
      "undefined_reason": null
    }
  },
  "software_acceptance": {
    "accepted": false,
    "status": "pending_independent_implementation_review"
  },
  "result_acceptance": {
    "accepted": false,
    "status": "pending_separate_policy_management_decision"
  },
  "documentation_acceptance": {
    "accepted": false,
    "status": "not_included"
  },
  "limitations": [
    "The cohort is hand-authored, stratified, same-domain, and non-iid.",
    "The one-step ceiling ignores multi-step context-dependent evidence.",
    "The selector uses variant ground truth unavailable to deployable policies.",
    "Saved P2a policy outcomes are reused without rerunning policies.",
    "Clean safety behavior is outside the P2b primary diagnostic."
  ],
  "non_claims": [
    "This diagnostic is not a seventh formal policy or deployable strategy.",
    "This diagnostic is not a general upper bound or policy-superiority result.",
    "This diagnostic does not establish generalization, significance, causality, minimax, Nash, or regret claims.",
    "Catalog-unreachable variants are retained in the accepted support.",
    "Accepted P2a software, dataset, result, and documentation decisions are unchanged."
  ],
  "notes": [
    "P2b is an analysis-only, ground-truth-informed, non-deployable fixed-catalog diagnostic.",
    "All rates are descriptive exact counts over the accepted fixed support."
  ]
}
```
<!-- P2B_VALIDATED_SUMMARY_END -->
