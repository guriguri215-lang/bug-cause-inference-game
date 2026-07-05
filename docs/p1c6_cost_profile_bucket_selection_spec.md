# P1c6 Specification: Cost-Profile Bucket Selection Diagnostic

Status: specification only. No code, dataset, policy, threshold, score, P1b default action cost, cost-profile, observation behavior, CLI, or real-diff artifact changes are included in this step.

P1c6 specifies a profile-conditioned bucket-selection diagnostic over the existing P1c5 observation-cost stress results. It asks which P1c0 bucket becomes hardest for each policy and metric inside each P1c5 cost profile, then compares that selected bucket with the baseline P1c3 selected bucket. It is not a new cost-stress model, a new adversarial bug generator, a single weighted utility model, or a formal game model.

## Scope

P1c6 should use only existing artifacts:

- The existing P1b variants from `load_p1b_variants()`.
- The existing P1c0 primary buckets and P1c labels.
- The existing P1b policies from `P1B_POLICIES`.
- The existing P1b settings and run behavior.
- The existing P1c3 `adversarial_bucket_selection` report as the default-cost baseline selected-bucket report.
- The existing P1c5 `observation_cost_stress` report, especially `baseline_bucket_metrics_by_policy` and `results_by_profile[*].bucket_metrics_by_policy`.
- The existing P1c5 cost profiles: `trace_access_expensive`, `sequence_reproduction_expensive`, `localization_evidence_expensive`, and `targeted_reproduction_expensive`.
- `execution_grounded` as the headline observation mode.
- `metadata_synth` only as an optional diagnostic comparison.

P1c6 must not change:

- P1b variant source code.
- P1b dataset metadata.
- P1b real-diff artifacts.
- P1b observation content, observation availability, test behavior, execution traces, or generated checkout trees.
- P1b policies, thresholds, scoring constants, default action costs, or default run behavior.
- `P1B_ACTION_SPECS` or `action_cost()`.
- P1c0 bucket definitions or P1c1/P1c3/P1c5 metric semantics.
- P1c5 cost profile definitions or effective cost ranges.
- README public claims.

The result of P1c6 is this specification. A later implementation may add an analysis-only diagnostic to the existing `p1c-evaluate` output, but P1c6 itself does not add a CLI command or runtime behavior.

## Motivation From P1c3/P1c5

P1c3 added the default-cost selected-bucket view. It keeps selection metric-specific and policy-aware, selects buggy metrics from the five buggy P1c0 buckets, keeps clean false-positive stress separate, and reports `execution_grounded` as the headline primary observation mode.

P1c5 added bounded observation-cost stress. It runs the existing P1b policies under P1c-only policy-visible cost overlays and reports profile-level metrics, profile-vs-baseline gaps, and profile bucket metrics. It keeps `observation_cost_stress` separate from the P1c3 `adversarial_bucket_selection` object.

P1c6 sits between those reports. It does not define new cost profiles and does not replace P1c3. Instead, for each existing P1c5 cost profile, it applies the same metric-specific bucket selector to that profile's bucket metrics and asks whether the selected bucket shifted from the default-cost baseline.

This is useful because a cost profile can change the hardest bucket even when the aggregate profile gap is small. For example, a profile may preserve the same bug discovery average while moving the weakest bucket from `state_sequence` to `config_normalization`, or it may keep the selected bucket but worsen the selected value. Those are different diagnostic signals and should be reported per metric rather than collapsed into one utility.

## Cost-Profile Bucket-Selection Diagnostic Model

The P1c6 diagnostic is a bounded reporting selector:

1. Choose one existing P1c5 cost profile.
2. Choose one existing policy.
3. Choose one reported metric.
4. Choose the allowed bucket set for that metric.
5. Select the bucket or tied buckets with the worst metric value inside the cost profile.
6. Compare the profile-selected bucket set with the default-cost baseline selected bucket set for the same policy and metric.

The selector should reuse the P1c3 metric directions and allowed bucket sets:

| metric | direction | allowed bucket set | profile selector rule |
|---|---|---|---|
| `bucket_bug_discovery_rate` | higher is better | five buggy buckets | select minimum |
| `bucket_cost_to_first_failure` | lower is better | five buggy buckets | select maximum |
| `bucket_location_top3_accuracy` | higher is better | five buggy buckets | select minimum |
| `bucket_cause_top1_accuracy` | higher is better | five buggy buckets | select minimum |
| `bucket_fix_intent_top1_accuracy` | higher is better | five buggy buckets | select minimum |
| `bucket_wrong_cause_high_confidence_rate` | lower is better | five buggy buckets | select maximum |
| `bucket_mean_investigation_cost` | lower is better | all six primary buckets | select maximum and mark bucket type |

Ties should include all selected bucket IDs in stable sorted order. A bucket shift is true when the set of profile-selected bucket IDs differs from the set of baseline-selected bucket IDs. A value gap should remain metric-specific:

- For higher-is-better metrics, `profile_vs_baseline_selected_value_gap = baseline_selected_value - profile_selected_value`.
- For lower-is-better metrics, `profile_vs_baseline_selected_value_gap = profile_selected_value - baseline_selected_value`.

Positive value gaps mean the profile-selected value is worse than the baseline-selected value under that metric direction. A bucket can shift even when the value gap is `0.0`; that case is still important because it says the profile changed where the weakness appears, not necessarily how large the weakest value is.

The diagnostic should not aggregate bucket shifts, selected values, or profile gaps into a single score.

## Information And Constraints

The diagnostic may see:

- The profile ID and cost overlay metadata from P1c5.
- The policy ID.
- The metric name, direction, and selector rule.
- The fixed P1c0 bucket labels for existing variants.
- Baseline bucket metrics from the default-cost report.
- Profile bucket metrics from `observation_cost_stress.results_by_profile[profile_id].bucket_metrics_by_policy`.
- Baseline selected buckets from the top-level P1c3 `adversarial_bucket_selection`, or an equivalent recomputation from the baseline bucket metrics using the same selector rules.
- Profile aggregate metrics and profile-vs-baseline gaps as context.
- Raw variant IDs from profile outcomes only as diagnostic evidence when available.

The diagnostic may not:

- Add, remove, or mutate variants.
- Change variant source, metadata, clean/buggy status, or primary bucket labels.
- Change P1b observation code, action outcomes, run order, budgets, thresholds, costs, or scores.
- Add new P1c5 profiles or tune existing profiles after seeing bucket outcomes.
- Reassign selected buckets across metrics to force a single narrative.
- Mix the clean false-positive bucket into buggy discovery, localization, cause, fix-intent, wrong-cause, or first-failure-cost denominators.
- Treat raw variant IDs as headline benchmark claims.

Raw variant IDs should remain diagnostic evidence for why a profile-selected bucket was selected. The headline unit is the profile, policy, metric, selected bucket set, bucket-shift flag, and metric-specific value gap.

## Metrics And Reporting

A future P1c6 report should present profile-conditioned selected buckets by profile, policy, and metric.

Recommended future JSON shape:

```json
{
  "adversarial_bucket_selection": {
    "analysis_phase": "p1c3_adversarial_bucket_selection_report",
    "selector_model": "metric_specific_bucket_selection"
  },
  "observation_cost_stress": {
    "analysis_phase": "p1c5_bounded_observation_cost_stress_report",
    "profile_conditioned_bucket_selection_by_profile": {
      "sequence_reproduction_expensive": {
        "analysis_phase": "p1c6_cost_profile_bucket_selection_diagnostic",
        "selector_model": "profile_conditioned_metric_specific_bucket_selection",
        "source_profile_id": "sequence_reproduction_expensive",
        "baseline_selection_source": "adversarial_bucket_selection",
        "primary_observation_mode": "execution_grounded",
        "selected_buckets_by_policy": {
          "expected_utility_per_cost": {
            "bucket_bug_discovery_rate": {
              "direction": "higher_is_better",
              "selector_rule": "select_minimum",
              "allowed_bucket_set": "buggy_primary_buckets",
              "baseline_selected_bucket_ids": ["state_sequence"],
              "profile_selected_bucket_ids": ["config_normalization"],
              "bucket_shifted_from_baseline": true,
              "baseline_selected_value": 0.0,
              "profile_selected_value": 0.0,
              "profile_vs_baseline_selected_value_gap": 0.0,
              "diagnostic_variant_ids": ["P1B-BUG-009", "P1B-BUG-010"]
            },
            "bucket_mean_investigation_cost": {
              "direction": "lower_is_better",
              "selector_rule": "select_maximum",
              "allowed_bucket_set": "all_primary_buckets",
              "baseline_selected_bucket_ids": ["missing_optional_input"],
              "profile_selected_bucket_ids": ["clean_false_positive"],
              "profile_selected_bucket_types": {
                "clean_false_positive": "clean"
              },
              "bucket_shifted_from_baseline": true,
              "baseline_selected_value": 9.75,
              "profile_selected_value": 10.0,
              "profile_vs_baseline_selected_value_gap": 0.25,
              "diagnostic_variant_ids": ["P1B-CLEAN-021"]
            }
          }
        },
        "clean_false_positive_stress": {
          "metric": "clean_false_positive_rate",
          "allowed_bucket_set": "clean_false_positive_only",
          "selected_bucket_ids": ["clean_false_positive"],
          "by_policy": {
            "expected_utility_per_cost": {
              "baseline_false_positive_rate": 0.0,
              "profile_false_positive_rate": 0.0,
              "profile_vs_baseline_gap": 0.0,
              "diagnostic_variant_ids": [],
              "note": "Clean false positives are not triggered in this cost profile."
            }
          }
        }
      }
    }
  }
}
```

The top-level P1c3 `adversarial_bucket_selection` object should remain the default-cost baseline selected-bucket report. The P1c6 diagnostic should be nested under `observation_cost_stress` because it is conditioned on P1c5 profiles and is derived from P1c5 `results_by_profile`.

Recommended future Markdown shape:

- A short scope note stating that the diagnostic is analysis-only and profile-conditioned.
- A table of selected bucket shifts by profile, policy, and metric.
- Columns for baseline selected buckets, profile selected buckets, bucket shifted, baseline value, profile value, metric-specific gap, and diagnostic variant IDs.
- A separate clean false-positive subsection for each profile or a compact profile-by-policy clean table.
- A notes section repeating that P1c3 remains the baseline selected-bucket report, P1c5 remains the cost-stress report, and P1c6 does not introduce a weighted payoff, regret, minimax, equilibrium, or formal payoff model.

## Interaction With P1c3 And P1c5

P1c6 should keep the existing object boundaries:

- `adversarial_bucket_selection` remains the top-level P1c3 baseline selected-bucket report under default costs.
- `observation_cost_stress` remains the top-level P1c5 cost-profile stress report.
- `observation_cost_stress.profile_conditioned_bucket_selection_by_profile` is the recommended future location for the P1c6 nested diagnostic.

This nesting is preferred over a new top-level P1c6 object because the selection is not an independent baseline adversarial selector. It is conditioned on a specific P1c5 cost profile and should travel with that profile's metrics, clean false-positive cost stress, and profile-vs-baseline gaps.

P1c6 should not use profile-conditioned selected buckets to rewrite P1c3 baseline results. It should not use P1c3 selected buckets to tune cost profiles. It should not alter P1c5 overlay definitions or effective cost handling.

## Clean False-Positive Handling

Clean false-positive stress remains separate from buggy metric selection.

For buggy metrics:

- Allowed bucket set: the five buggy primary buckets only.
- The clean bucket must not appear in allowed bucket IDs.
- `diagnostic_variant_ids` should include only variants from the selected buggy bucket or buckets.

For `bucket_mean_investigation_cost`:

- Allowed bucket set: all six primary buckets.
- The report must mark selected bucket type as `buggy` or `clean`.
- Selecting `clean_false_positive` for mean cost does not make it part of buggy discovery, localization, cause, fix-intent, wrong-cause, or first-failure-cost metrics.

For clean false-positive stress:

- Allowed bucket set: `clean_false_positive` only.
- Primary metric: false-positive rate on clean cases.
- Supporting metrics: clean bucket mean investigation cost and clean no-bug stop rate when available from existing outcomes.
- If false positives remain `0.0`, the report should say they are not triggered in that profile. It must not claim that false-positive risk is solved beyond the current five clean variants.

## Observation Mode Contract

The headline P1c6 diagnostic uses `execution_grounded`.

`execution_grounded` remains primary because it uses checkout test results, exceptions, traced checkout functions, function-level coverage suspicion, and Phase C real-diff artifacts for `inspect_recent_diff`.

`metadata_synth` may be included only as an optional diagnostic comparison. It should not become the headline claim because it is metadata-dependent and can make metrics look better than execution-grounded evidence.

In a future `both` mode implementation:

- Top-level P1c3 selected buckets continue to use the `execution_grounded` primary report.
- Top-level P1c5 `observation_cost_stress` continues to use the `execution_grounded` primary report.
- The P1c6 nested diagnostic under top-level `observation_cost_stress` should also use `execution_grounded`.
- `metadata_synth` profile-conditioned diagnostics may appear only under `diagnostic_reports_by_observation_mode["metadata_synth"].observation_cost_stress.profile_conditioned_bucket_selection_by_profile` or an equivalently explicit diagnostic location.

## Acceptance Criteria

P1c6 is ready for a later implementation prompt when:

- This specification is linked from planning/status docs.
- The diagnostic is defined only over existing P1c5 profile bucket metrics and baseline bucket metrics.
- The P1c3 top-level `adversarial_bucket_selection` object remains the default-cost baseline selection.
- The recommended future implementation is nested under P1c5 `observation_cost_stress`.
- The selector reuses P1c3 metric directions and allowed bucket sets.
- Buggy metric selection uses only the five buggy buckets.
- `bucket_mean_investigation_cost` may select from all six buckets and marks selected bucket type.
- Clean false-positive stress is separate from buggy metrics.
- Baseline selected buckets and profile selected buckets are compared per metric, including a bucket-shift flag.
- Metric gaps and shifts are not collapsed into one utility score.
- `execution_grounded` remains headline primary and `metadata_synth` remains optional diagnostic.
- Raw variant IDs are diagnostic evidence, not headline claims.
- No implementation logic, dataset, policy, threshold, score, action-cost, cost-profile, observation-code, or real-diff artifact change is required.
- The wording does not claim real-world debugging accuracy, automated repair, a production fault-localization engine, a minimax-optimal policy, or a game-theoretic guarantee.

## Non-Claims / Stop Rules

P1c6 does not claim:

- Real-world debugging accuracy.
- Production source-code fault localization.
- Automated bug discovery.
- Automated patch generation.
- LLM agent evaluation.
- A real repository history benchmark.
- A formal game-theoretic guarantee.
- A minimax-optimal, regret-optimal, or equilibrium policy.
- A single weighted payoff or formal payoff table.

Stop and return to design review if a future implementation would require:

- Changing P1b default action costs.
- Mutating `P1B_ACTION_SPECS` or changing default `action_cost()`.
- Changing P1b logic, policies, thresholds, scores, dataset metadata, or real-diff artifacts.
- Changing P1c0 bucket definitions or P1c1/P1c3/P1c5 metric behavior.
- Changing P1c5 cost profiles or adding new profiles in the same slice.
- Changing observation content, adding observation dropout, or adding observation delay.
- Adding new variants, generated checkout source trees, or adversarial bug generation.
- Mixing clean false-positive variants into buggy metric denominators.
- Replacing P1c3 `adversarial_bucket_selection` with profile-conditioned results.
- Introducing a single weighted utility, weighted payoff, regret objective, minimax objective, equilibrium concept, or formal payoff model.
- Expanding README public claims.
- Adding a new CLI command before design review.
- Using GitHub operations before explicit user approval.

## Future Work After P1c6

The next implementation candidate is an analysis-only P1c profile-conditioned bucket-selection diagnostic, preferably as an extension to the existing `p1c-evaluate` output rather than a new command.

Future implementation should:

- Keep the top-level P1c3 `adversarial_bucket_selection` object unchanged.
- Add `profile_conditioned_bucket_selection_by_profile` under `observation_cost_stress`.
- Derive profile selections from existing `results_by_profile[profile_id].bucket_metrics_by_policy`.
- Compare each profile-selected bucket set with the baseline selected bucket set per policy and metric.
- Include a separate clean false-positive subsection.
- Keep generated example JSON/Markdown out of commits unless explicitly requested.

Later slices may consider observation dropout/delay or a formal game model. Those should wait until the profile-conditioned diagnostic has a reviewed implementation and should not be folded into P1c6.
