# P1c2 Specification: Adversarial Bucket Selection

Status: specification only. No code, dataset, policy, threshold, score, or real-diff artifact changes are included in this step.

P1c2 specifies a bounded adversarial bucket selector over the existing P1c0 primary buckets and P1c1 report fields. It is a reporting design for choosing the hardest bucket per policy and metric. It is not a new bug generator, a new observation harness, a single weighted utility model, or a formal adversarial game.

## Scope

P1c2 should use only existing artifacts:

- The existing P1b variants from `load_p1b_variants()`.
- The existing P1c0 primary buckets and P1c labels.
- The existing P1b policies from `P1B_POLICIES`.
- The existing P1b settings and run behavior.
- The existing P1c1 per-bucket metrics, headline worst-case metrics, raw variant worst-case IDs, and average-versus-worst gaps.
- `execution_grounded` as the headline observation mode.
- `metadata_synth` only as an optional diagnostic comparison.

P1c2 should not change:

- P1b variant source code.
- P1b dataset metadata.
- P1b real-diff artifacts.
- P1b observation code or run behavior.
- P1b policies, thresholds, action costs, or scoring.
- P1c0 bucket definitions or P1c1 metric definitions.
- README public claims.

The result of P1c2 is this specification. A later implementation may add a report, but P1c2 itself does not add a CLI command or change runtime behavior.

## Motivation From P1c1

P1c1 showed that average policy results can hide bucket-level fragility in the existing P1b scaffold.

For the current primary policy, `expected_utility_per_cost`, the `execution_grounded` average bug discovery rate is `0.40`, but the `state_sequence` bucket has `0.0` discovery, `0.0` location top-3 accuracy, `0.0` cause top-1 accuracy, and `0.0` fix-intent top-1 accuracy. This makes `state_sequence` the clearest initial stress bucket.

`config_normalization` is the next broad weak bucket. For the same primary policy, discovery, location top-3, cause top-1, and fix-intent top-1 are all `0.25`.

`recent_diff_first` shows why the selector must be metric-specific. It keeps location top-3 at `1.0` across buggy buckets, while discovery, cause, and fix-intent still collapse in the hardest buckets. A single headline utility would hide that distinction.

Clean false positives are not the current primary fragility driver. In the P1c1 `execution_grounded` report, all evaluated policies have `clean_false_positive_rate = 0.0`. The clean bucket should remain a separate false-positive stress target rather than being mixed into buggy discovery, localization, cause, or fix-intent metrics.

## Adversarial Bucket Selection Model

The P1c2 selector is a bounded reporting selector:

1. Choose one existing policy.
2. Choose one reported metric.
3. Choose an allowed bucket set for that metric.
4. Select the bucket or tied buckets with the worst metric value for that policy.

For higher-is-better buggy metrics, the selected bucket is the bucket with the lowest value. For lower-is-better buggy metrics, the selected bucket is the bucket with the highest value. Ties are reported as all selected bucket IDs in stable sorted order.

The selector is allowed to be policy-aware and metric-aware. It may select different buckets for `expected_utility_per_cost` than for `recent_diff_first`, and it may select different buckets for discovery than for location, cause, fix-intent, wrong-cause, or cost.

The selector is not a single weighted payoff. P1c2 does not define regret, minimax, equilibrium, or a formal payoff model. It should be described as adversarial bucket selection or worst-bucket selection inside a small injected benchmark, not as a formal adversarial game.

Initial P1c2 attention should focus on `state_sequence` and `config_normalization` because P1c1 exposed them as the most important weak buckets for the primary policy. The model still applies to all P1c0 primary buckets.

## Selector Information And Constraints

The selector may see:

- The policy ID.
- The metric name and direction.
- The observation mode being summarized.
- The fixed P1c0 bucket label for each existing variant.
- The P1c1 bucket metrics for the chosen policy and observation mode.
- The raw variant IDs behind the bucket failures, as diagnostic evidence.
- The P1c1 aggregate and average-versus-worst values.

The selector may not:

- Add, remove, or mutate variants.
- Change variant source, metadata, or clean/buggy status.
- Reassign P1c0 primary buckets during selection.
- Change P1b observation code, action outcomes, run order, budgets, thresholds, costs, or scores.
- Rerun with altered observation availability, observation delay, or cost profiles.
- Inspect or commit generated checkout source trees.
- Treat raw variant IDs as headline benchmark claims.

Raw variant IDs should remain evidence for why a bucket was selected. The headline unit is the selected bucket and metric, not a broad claim about individual variants or general software projects.

## Metrics And Reporting

P1c2 should keep metric-specific selection. A later report should present separate selected-bucket rows for at least these existing P1c1 headline dimensions:

| metric group | direction | allowed bucket set | selector rule |
|---|---|---|---|
| `bucket_bug_discovery_rate` | higher is better | five buggy buckets | select minimum |
| `bucket_cost_to_first_failure` | lower is better | five buggy buckets | select maximum |
| `bucket_location_top3_accuracy` | higher is better | five buggy buckets | select minimum |
| `bucket_cause_top1_accuracy` | higher is better | five buggy buckets | select minimum |
| `bucket_fix_intent_top1_accuracy` | higher is better | five buggy buckets | select minimum |
| `bucket_wrong_cause_high_confidence_rate` | lower is better | five buggy buckets | select maximum |
| `clean_false_positive_rate` | lower is better | clean false-positive bucket only | report clean bucket |
| `bucket_mean_investigation_cost` | lower is better | six buckets, with clean status preserved | select maximum and mark bucket type |

Recommended future JSON shape:

```json
{
  "analysis_phase": "p1c3_adversarial_bucket_selection_report",
  "selector_model": "metric_specific_bucket_selection",
  "primary_observation_mode": "execution_grounded",
  "policies_evaluated": ["expected_utility_per_cost"],
  "selected_buckets_by_policy": {
    "expected_utility_per_cost": {
      "bucket_bug_discovery_rate": {
        "direction": "higher_is_better",
        "allowed_bucket_set": "buggy_primary_buckets",
        "selected_bucket_ids": ["state_sequence"],
        "selected_value": 0.0,
        "average_metric": 0.4,
        "average_vs_selected_gap": 0.4,
        "diagnostic_variant_ids": ["P1B-BUG-013", "P1B-BUG-014", "P1B-BUG-015", "P1B-BUG-016"]
      }
    }
  },
  "clean_false_positive_stress": {
    "allowed_bucket_set": "clean_false_positive_only"
  },
  "diagnostic_reports_by_observation_mode": {
    "metadata_synth": "optional"
  }
}
```

Recommended future Markdown shape:

- A short scope note stating that the report is analysis-only and uses existing P1b/P1c1 artifacts.
- A table of selected buckets by policy and metric.
- A separate clean false-positive section.
- An optional diagnostic comparison for `metadata_synth`.
- A notes section repeating the non-claims and small-benchmark boundary.

## Clean False-Positive Handling

The `clean_false_positive` bucket is not part of the buggy metric selector for discovery, first-failure cost, localization, cause, fix-intent, or wrong-cause high-confidence metrics.

Clean false-positive stress should be reported separately:

- Allowed bucket set: `clean_false_positive` only.
- Primary metric: `clean_false_positive_rate`.
- Supporting metric: clean bucket investigation cost.
- Diagnostic evidence: `false_positive_clean_variant_ids`.

If the false-positive rate remains `0.0`, the report should say that clean false positives are not triggered in the current run. It should not infer that false-positive risk is solved beyond the current 5 clean variants.

## Observation Mode Contract

The headline P1c2 model uses `execution_grounded`.

`execution_grounded` is the primary mode because it uses checkout test results, exceptions, traced checkout functions, function-level coverage suspicion, and Phase C real-diff artifacts for `inspect_recent_diff`.

`metadata_synth` may be included only as an optional diagnostic comparison. It should remain secondary because it is metadata-dependent and can make some metrics look better than execution-grounded evidence.

In any future `both` mode implementation, top-level selected buckets should come from `execution_grounded`. `metadata_synth` should appear under a clearly named diagnostic object or section.

## Acceptance Criteria

P1c2 is ready for a later implementation prompt when:

- The selector is defined over existing P1c0 primary buckets.
- Buggy metric selection uses only the five buggy buckets.
- Clean false-positive stress is separate from buggy bucket metrics.
- Selection is metric-specific and policy-aware.
- Ties are reported without inventing a secondary ranking.
- `execution_grounded` remains the headline observation mode.
- `metadata_synth` is marked as optional diagnostic comparison.
- Raw variant IDs are diagnostic evidence, not headline claims.
- No implementation logic, dataset, policy, threshold, score, observation code, or real-diff artifact change is required.
- The wording does not claim real-world debugging accuracy, automated repair, a production fault-localization engine, a minimax-optimal policy, or a game-theoretic guarantee.

## Non-Claims / Stop Rules

P1c2 does not claim:

- Real-world debugging accuracy.
- Production source-code fault localization.
- Automated bug discovery.
- Automated patch generation.
- LLM agent evaluation.
- A real repository history benchmark.
- A formal game-theoretic guarantee.
- A minimax-optimal, regret-optimal, or equilibrium policy.

Stop and return to design review if a future implementation would require:

- Changing P1b logic, policies, thresholds, costs, scores, or dataset metadata.
- Changing P1c0 bucket definitions or P1c1 metric behavior.
- Adding new variants or generated source trees.
- Introducing observation-cost stress, observation dropout, or observation delay in the same slice.
- Introducing a single weighted utility, regret objective, minimax objective, equilibrium concept, or formal payoff table.
- Expanding README public claims.
- Using GitHub operations before explicit user approval.

## Future Work After P1c2

The next implementation candidate is a P1c3 analysis-only report that consumes the existing P1c1 report structure and emits metric-specific selected buckets by policy. It should not add a new execution harness.

After that, bounded observation-cost stress can be specified as a separate slice if the cost gaps remain important. Observation dropout or delay should come later because it changes observation availability and is more likely to require a new execution contract.

Moving toward a formal game model should wait until there is an explicit player model, action space, payoff definition, and acceptance criteria. P1c2 deliberately stops before that point.
