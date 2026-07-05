# P1c8 Specification: Bounded Observation Dropout/Delay

Status: specification only. No code, dataset, policy, threshold, score, P1b observation behavior, P1b default action cost, CLI, generated checkout tree, execution trace, real-diff artifact, or P1c metric semantic changes are included in this step.

P1c8 specifies a bounded observation dropout/delay model over the existing P1b/P1c artifacts. It asks how existing investigation policies may behave when a small documented subset of observation evidence is hidden from the policy or arrives after a fixed short delay inside a future P1c-only analysis path. It is not an implementation, a cost-stress extension, an adversarial bug generator, a single weighted utility model, or a formal game model.

## Scope

P1c8 should use only existing artifacts:

- The existing P1b variants from `load_p1b_variants()`.
- The existing P1c0 primary buckets and P1c labels.
- The existing P1b policies from `P1B_POLICIES`.
- The existing P1b settings and default budget semantics.
- The existing P1b action IDs and observation families from `P1B_ACTION_SPECS`.
- The existing P1b default observations as the source observations.
- The existing P1c1 bucket metrics, P1c3 selected-bucket report, P1c5 observation-cost stress report, and P1c7 nested diagnostic as background diagnostics.
- `execution_grounded` as the headline observation mode.
- `metadata_synth` only as an optional diagnostic comparison.

P1c8 must not change:

- P1b variant source code.
- P1b dataset metadata.
- P1b real-diff artifacts.
- P1b observation content, default observation availability, test behavior, execution traces, or generated checkout trees.
- P1b policies, thresholds, scoring constants, default action costs, default budgets, or default run behavior.
- `P1B_ACTION_SPECS` or `action_cost()`.
- P1c0 bucket definitions or P1c1/P1c3/P1c5/P1c7 metric semantics.
- P1c5 cost profiles or P1c7 profile-conditioned selected-bucket logic.
- README public claims.

The result of P1c8 is this specification. A later implementation may add an analysis-only report to the existing `p1c-evaluate` output, but P1c8 itself does not add a CLI command or runtime behavior.

## Motivation From P1c Planning And P1c7

The P1c planning memo listed observation dropout or delay as a later candidate after bucket selection and cost stress. The candidate is useful because some current weak patterns involve evidence that may be late, indirect, or unavailable in realistic debugging work.

P1c1 and P1c3 showed that the `state_sequence` bucket is brittle for the current primary policy, especially for discovery, location, cause, and fix-intent metrics. P1c5 and P1c7 then showed that cost profiles can shift or intensify bucket-level weaknesses without changing P1b defaults.

P1c8 takes the next step only at the specification level: it defines how a future P1c-only report could perturb observation visibility or arrival timing while preserving the source P1b observations and all existing report boundaries.

The motivation is diagnostic, not generative. P1c8 does not create harder bugs, mutate traces, modify real-diff artifacts, or claim that missing evidence is common in real projects. It defines a small reproducible stress contract for later review.

## Bounded Observation Dropout/Delay Model

The P1c8 model is a bounded observation-visibility perturbation:

```text
source_observation = P1b default observation for (variant, action, observation_mode)
visible_observation = deterministic_copy(source_observation, dropout_or_delay_profile)
```

The source observation remains unchanged and should be retained as diagnostic evidence in any future report. The visible observation is the copy used only by a future P1c-only dropout/delay analysis path.

Two perturbation types are allowed:

| perturbation type | meaning | permitted future effect |
|---|---|---|
| `dropout` | Hide a fixed subset of evidence fields from the policy-facing visible observation. | The policy may see a weaker observation for the same action and cost, while the source observation is preserved in the report. |
| `delay` | Hold a fixed subset of evidence fields for a fixed number of later investigation steps. | The policy-facing posterior update may receive the delayed fields only after the release step, while the source observation remains available for diagnostics. |

A future implementation should treat the perturbation as policy-visible inside a P1c-only analysis path. Post-hoc accounting over an unperturbed trace may be useful as a secondary diagnostic, but it is not the primary contract because it cannot test whether a policy changes action choice when evidence is missing or late.

The perturbation may affect only copied report-time evidence fields, such as exception detail, stack functions, coverage suspicion, recent-diff location scores, failed test identifiers, or reproduction inputs. It must not change whether the underlying checkout test passes or fails, the real-diff artifact itself, the generated checkout source, or the default P1b action result.

If a future implementation cannot preserve the source observation and keep the perturbation inside a separate P1c-only object, it should stop for design review.

## Determinism And Reproducibility Constraints

Every dropout/delay profile must be deterministic, reproducible, documented, and bounded.

Allowed rule axes:

- `profile_id`.
- `perturbation_type`.
- `source_observation_mode`.
- Existing P1b `action_id`.
- Existing P1b `observation_type`.
- A fixed evidence-field family, such as traceback details, recent-diff location scores, coverage suspicion, or reproduction inputs.
- A fixed release delay in investigation steps for delay profiles.

Disallowed rule axes:

- Policy ID.
- Variant ID.
- Raw outcome value.
- Whether the action helped or hurt a metric.
- Posterior state.
- Selected bucket after evaluation.
- Random sampling.
- Manual exception lists chosen after looking at profile results.

Bound constraints:

- A profile targets at most two action IDs or one observation family.
- A profile hides or delays only a small named field family, not the entire P1b observation object.
- A delay uses a fixed release delay of one or two investigation steps.
- A profile is evaluated independently; profiles are not stacked unless a later reviewed specification says so.
- The same profile definition applies to all policies and variants for the selected observation mode.
- Ties and missing delayed evidence are reported in stable sorted order without inventing a secondary chooser.

These constraints are intended to keep dropout/delay from becoming a free-form adversary. The rule must be known before running the report and must not be tuned to make a specific policy, variant, bucket, or metric look worse.

## Candidate Dropout/Delay Scenarios

The initial scenario set should be small. These profiles are candidates for a later implementation; P1c8 does not execute them.

| profile_id | perturbation type | target action / observation family | bound | deterministic rule | expected diagnostic signal | non-goal |
|---|---|---|---|---|---|---|
| `traceback_signal_dropout` | `dropout` | `inspect_traceback`, `run_null_missing_tests`, and `exception_trace` details | Hide exception-specific detail, stack functions, and exception-derived cause/location/fix-intent score fields for the first matching visible observation per run. Keep action cost and source observation unchanged. | If the visible observation has `observation_type = exception_trace` for a targeted action, copy it with the named traceback detail fields empty. Apply the same rule to every variant and policy. | Tests whether policies can recover from missing traceback detail through tests, coverage, spec, or diff evidence; watch discovery, cause top-1, location top-3, and wrong-cause high-confidence metrics. | Does not delete the source exception, change test outcomes, or simulate logging infrastructure. |
| `recent_diff_signal_delay` | `delay` | `inspect_recent_diff` and `recent_diff_signal` fields | Delay recent-diff location scores, changed files, changed functions, and diff excerpt by one investigation step. | When `inspect_recent_diff` is selected, expose a placeholder visible observation immediately and release the named fields exactly one later step if the run continues. | Tests reliance on immediate diff evidence; watch location top-3, cause top-1, fix-intent top-1, and mean investigation cost. | Does not alter Phase C real-diff artifacts, create repository histories, or reweight action costs. |
| `coverage_signal_dropout` | `dropout` | `inspect_coverage_spectrum` and `coverage_suspicious_location` fields | Hide coverage suspicion scores and coverage counts for the first coverage observation per run. Keep cached test results and source coverage payload intact for diagnostics. | If the visible action is `inspect_coverage_spectrum`, copy it with empty `coverage_suspicion`, empty `coverage_counts`, and no coverage-derived location scores. | Tests whether localization and cause inference recover when spectrum evidence is unavailable; watch location top-3, cause top-1, fix-intent top-1, and wrong-cause high-confidence metrics. | Does not change the coverage algorithm, test registry, traced functions, or source execution trace. |
| `sequence_reproduction_delay` | `delay` | `run_state_sequence_tests` and `state_sequence_counterexample` reproduction evidence | Delay reproduction input, failed test IDs, failure-found signal, and state-sequence derived cause/fix-intent scores by one investigation step. | When `run_state_sequence_tests` produces a failure-bearing source observation, expose only a bounded placeholder immediately and release the named fields exactly one later step if the run continues. | Tests recovery from late sequence evidence, especially in the `state_sequence` bucket; watch discovery within budget, first-failure cost, cause top-1, fix-intent top-1, and stop reasons. | Does not add new sequence tests, change state behavior, or make sequence actions more expensive. |

The profile IDs are scenario IDs for the dropout/delay model. They are separate from P1c5 cost-profile IDs and should not be nested under `observation_cost_stress`.

## Metrics And Reporting

A future P1c8 report should keep metric-specific reporting. It should compare each dropout/delay profile against the unperturbed baseline for the same policy and observation mode.

Recommended metrics reuse existing P1b/P1c dimensions:

- `bug_discovery_rate_within_budget`.
- `cost_to_first_failure`.
- `location_top3_accuracy`.
- `cause_top1_accuracy`.
- `fix_intent_top1_accuracy`.
- `wrong_cause_high_confidence_rate`.
- `false_positive_rate_on_clean_cases`.
- `mean_investigation_cost`.
- P1c bucket metrics for the five buggy buckets and the clean false-positive bucket.

Recommended additional dropout/delay diagnostics:

| metric | direction | meaning |
|---|---|---|
| `recovery_rate_after_missing_observation` | higher is better | Among runs where a source observation had fields hidden or delayed, the fraction that still discovers the bug within budget after later evidence or alternative evidence. |
| `delayed_evidence_released_rate` | diagnostic | Fraction of delayed evidence payloads that are eventually released before the run stops. |
| `stop_before_delayed_evidence_rate` | lower is better | Fraction of delayed evidence payloads where the run stops before the evidence release step. |

Profile-vs-baseline gaps should remain metric-specific:

| metric kind | direction | profile gap |
|---|---|---|
| Higher-is-better rates | higher is better | `baseline_value - profile_value` |
| Lower-is-better costs or error rates | lower is better | `profile_value - baseline_value` |
| Diagnostic release rates | diagnostic | Report values without converting them into policy quality claims. |

Positive gaps mean the dropout/delay profile made the metric worse under the metric direction. The report must not collapse these gaps into one utility score.

Raw variant IDs may appear only as diagnostic evidence for a profile, bucket, or metric. They should not be headline claims.

## Interaction With P1c3/P1c5/P1c7

P1c8 is a separate slice from P1c3, P1c5, and P1c7.

- P1c3 `adversarial_bucket_selection` remains the default-cost baseline selected-bucket report.
- P1c5 `observation_cost_stress` remains the bounded action-cost overlay report.
- P1c7 `observation_cost_stress.profile_conditioned_bucket_selection_by_profile` remains a nested diagnostic inside cost stress.
- P1c8 should use a separate future object, recommended as `observation_dropout_delay_stress`.

Dropout/delay profiles must not tune or replace cost profiles. They must not use P1c3 or P1c7 selected buckets to decide which fields to hide. A later combined analysis may compare dropout/delay results with selected buckets or cost profiles, but that should be a separate reviewed slice with explicit object boundaries.

## Clean False-Positive Handling

Clean false-positive stress remains separate from buggy metric reporting.

Dropout/delay profiles may be applied to clean variants because clean variants also exercise observation paths. However, reporting must separate:

- Buggy metrics over the five buggy P1c0 buckets.
- Clean false-positive metrics over the `clean_false_positive` bucket only.

For clean variants, report at least:

- `false_positive_rate_on_clean_cases`.
- Clean bucket mean investigation cost.
- Clean no-bug stop rate, if available from existing outcomes.
- Diagnostic false-positive clean variant IDs, if any.

If false positives remain `0.0`, the report should say they are not triggered in the current dropout/delay profile. It must not claim that false-positive risk is solved beyond the current five clean variants.

The clean bucket must not appear in buggy discovery, first-failure-cost, localization, cause, fix-intent, or wrong-cause metric denominators.

## Observation Mode Contract

The headline P1c8 model uses `execution_grounded`.

`execution_grounded` remains primary because it uses checkout test results, exceptions, traced checkout functions, function-level coverage suspicion, and Phase C real-diff artifacts for `inspect_recent_diff`.

`metadata_synth` may be included only as an optional diagnostic comparison. It should not become the headline claim because it is metadata-dependent and can make metrics look better than execution-grounded evidence.

In a future `both` mode implementation:

- Top-level `observation_dropout_delay_stress` uses the `execution_grounded` primary report.
- `metadata_synth` appears only under `diagnostic_reports_by_observation_mode["metadata_synth"].observation_dropout_delay_stress` or an equivalently explicit diagnostic location.
- The same dropout/delay profile IDs may be used for both modes, but the observation-mode role must remain explicit.

Any future report should include both:

- `source_observation_mode`, describing where the source observation came from.
- `report_role`, either `headline_primary` or `diagnostic`.

## Acceptance Criteria

P1c8 is ready for a later implementation prompt when:

- This specification is linked from planning/status docs.
- Dropout/delay is defined only as a P1c-only copied-observation perturbation.
- P1b default observation content, availability, test behavior, execution traces, and real-diff artifacts remain unchanged.
- The scenario set is small and documented.
- Every profile is deterministic, reproducible, and bounded.
- Rules are not keyed by policy, variant, outcome, posterior state, selected bucket, or metric result.
- `execution_grounded` remains headline primary and `metadata_synth` remains optional diagnostic.
- P1c3 baseline bucket selection, P1c5 observation-cost stress, and P1c7 profile-conditioned bucket selection remain separate.
- Clean false-positive stress remains separate from buggy metrics.
- Metric gaps are not collapsed into one utility score.
- Raw variant IDs are diagnostic evidence, not headline claims.
- No implementation logic, dataset, policy, threshold, score, default action-cost, observation-code, CLI, or real-diff artifact change is required.
- The wording does not claim real-world debugging accuracy, automated repair, a production fault-localization engine, a minimax-optimal policy, or a formal game guarantee.

## Non-Claims / Stop Rules

P1c8 does not claim:

- Real-world debugging accuracy.
- Production source-code fault localization.
- Automated bug discovery.
- Automated patch generation.
- LLM agent evaluation.
- A real repository history benchmark.
- A minimax-optimal, regret-optimal, or equilibrium policy.
- A single weighted payoff or formal payoff table.

Stop and return to design review if a future implementation would require:

- Changing P1b default action costs.
- Mutating `P1B_ACTION_SPECS` or changing default `action_cost()`.
- Changing P1b logic, policies, thresholds, scores, dataset metadata, or real-diff artifacts.
- Changing P1b default observation content, availability, test behavior, execution traces, or generated checkout trees.
- Changing P1c0 bucket definitions or P1c1/P1c3/P1c5/P1c7 metric behavior.
- Changing P1c5 cost profiles or adding cost overlays in the same slice.
- Replacing P1c3 `adversarial_bucket_selection`.
- Replacing P1c5 `observation_cost_stress` or P1c7 nested diagnostics.
- Mixing clean false-positive variants into buggy metric denominators.
- Adding new variants, generated checkout source trees, or adversarial bug generation.
- Introducing a single weighted utility, weighted payoff, regret objective, minimax objective, equilibrium concept, or formal payoff model.
- Expanding README public claims.
- Adding a new CLI command before design review.
- Using GitHub operations before explicit user approval.

## Future Work After P1c8

The next implementation candidate, if reviewed and accepted, is an analysis-only bounded observation dropout/delay stress report. The first-choice integration point should be the existing `p1c-evaluate` command, not a new CLI command.

Recommended future JSON shape:

```json
{
  "observation_dropout_delay_stress": {
    "analysis_phase": "p1c9_bounded_observation_dropout_delay_stress_report",
    "stress_model": "bounded_observation_visibility_or_delay_profile",
    "perturbation_visibility": "policy_visible_p1c_only",
    "primary_observation_mode": "execution_grounded",
    "source_observation_mode": "execution_grounded",
    "baseline_source": "unperturbed_p1c_report",
    "profiles": [
      {
        "profile_id": "recent_diff_signal_delay",
        "perturbation_type": "delay",
        "target_action_ids": ["inspect_recent_diff"],
        "target_observation_families": ["recent_diff_signal"],
        "delay_steps": 1,
        "bounded": true,
        "deterministic_rule": "release named recent-diff fields exactly one investigation step after inspect_recent_diff"
      }
    ],
    "results_by_profile": {
      "recent_diff_signal_delay": {
        "aggregate_metrics_by_policy": {},
        "bucket_metrics_by_policy": {},
        "profile_vs_baseline_gap_by_policy": {},
        "recovery_diagnostics_by_policy": {},
        "clean_false_positive_stress_by_policy": {}
      }
    },
    "diagnostic_reports_by_observation_mode": {
      "metadata_synth": "optional"
    },
    "notes": []
  }
}
```

The future object should not replace `adversarial_bucket_selection`, `observation_cost_stress`, or `profile_conditioned_bucket_selection_by_profile`.

Recommended future Markdown shape:

- A scope note stating that the report is analysis-only and P1c-only.
- A profile/scenario table with profile ID, perturbation type, targeted action or observation family, bound, and deterministic rule.
- A profile-by-policy metric table.
- A profile-vs-baseline metric gap table.
- A bucket table over the existing P1c0 buckets.
- A recovery diagnostics subsection.
- A separate clean false-positive subsection.
- Scope/non-claim notes repeating that P1b defaults are unchanged, `execution_grounded` is primary, `metadata_synth` is diagnostic, P1c3/P1c5/P1c7 objects are not replaced, and no weighted payoff, regret, minimax, equilibrium, or formal payoff model is introduced.

Generated example JSON/Markdown should stay out of commits unless explicitly requested.

Later slices may consider combined dropout/delay plus cost-profile diagnostics, richer missing-observation models, or a formal game model. Those should wait until the bounded dropout/delay report has a reviewed implementation and should not be folded into P1c8.
