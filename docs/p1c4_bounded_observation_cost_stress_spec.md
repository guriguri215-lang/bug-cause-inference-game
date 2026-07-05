# P1c4 Specification: Bounded Observation-Cost Stress

Status: specification only. No code, dataset, policy, threshold, score, P1b default action cost, observation behavior, or real-diff artifact changes are included in this step.

P1c4 specifies a bounded observation-cost stress model over the existing P1b/P1c artifacts. It asks how existing P1b policies may behave when observation actions are still available and unchanged, but their investigation costs are reweighted within a small documented range. It is not an observation dropout model, an adversarial bug generator, a single weighted payoff model, or a formal game model.

## Scope

P1c4 should use only existing artifacts:

- The existing P1b variants from `load_p1b_variants()`.
- The existing P1c0 primary buckets and P1c labels.
- The existing P1b policies from `P1B_POLICIES`.
- The existing P1b settings and default budget semantics.
- The existing P1b action IDs from `P1B_ACTION_SPECS`.
- The existing P1c1 bucket metrics and P1c3 selected-bucket report as background diagnostics.
- `execution_grounded` as the headline observation mode.
- `metadata_synth` only as an optional diagnostic comparison.

P1c4 must not change:

- P1b variant source code.
- P1b dataset metadata.
- P1b real-diff artifacts.
- P1b observation content, observation availability, test behavior, execution traces, or generated checkout trees.
- P1b policies, thresholds, scoring constants, default action costs, or default run behavior.
- P1c0 bucket definitions or P1c1/P1c3 metric semantics.
- README public claims.

The result of P1c4 is this specification. A later implementation may add an analysis-only report, preferably as an extension candidate for the existing `p1c-evaluate` command, but P1c4 itself does not add a CLI command or runtime behavior.

## Motivation From P1c1/P1c3

P1c1 showed that average execution-grounded policy results can hide bucket-level cost fragility.

For the current primary policy, `expected_utility_per_cost`, the execution-grounded average bug discovery rate is `0.40`, but the `state_sequence` bucket has `0.0` discovery, `0.0` location top-3 accuracy, `0.0` cause top-1 accuracy, and `0.0` fix-intent top-1 accuracy. Its penalized first-failure cost is `14`, which is the default failure cost for a missed first failure under the current budget.

`missing_optional_input` is the strongest success bucket for the same policy, with `1.0` discovery, location top-3, cause top-1, and fix-intent top-1 rates. However, its mean investigation cost is `9.75`, the max mean-cost bucket for the primary policy. This makes it useful for cost stress even though it is not a miss bucket.

P1c3 made the hardest-bucket view explicit through `adversarial_bucket_selection`. For `expected_utility_per_cost`, execution-grounded selected buckets include `state_sequence` for discovery, location, cause, and fix-intent, and `missing_optional_input` for mean investigation cost. P1c4 uses those findings as motivation only. It does not modify or reuse the P1c3 selector in the same slice.

Clean false positives are not the current execution-grounded fragility driver. P1c1/P1c3 report `clean_false_positive_rate = 0.0` for the evaluated policies, so P1c4 should keep clean false-positive stress separate rather than mixing the clean bucket into buggy metrics.

## Bounded Observation-Cost Stress Model

The P1c4 stress model is a bounded action-cost overlay:

```text
effective_cost(action_id, cost_profile)
  = cost_profile.overlay[action_id] if action_id is overridden
  = P1B_ACTION_SPECS[action_id].cost otherwise
```

The overlay is keyed only by existing P1b action IDs. It is not keyed by policy, variant, bucket, outcome, observation mode, or metric.

The overlay changes only the cost used by a future P1c cost-stress report. Observation content remains the same for the same action, variant, and observation mode. A cost profile may make an action more or less attractive or affordable, but it may not hide the action, delay its result, change its test result, change its evidence scores, or change the variant.

P1c4 recommends a policy-visible cost overlay for future implementation.

| option | meaning | risk | P1c4 decision |
|---|---|---|---|
| Post-hoc cost accounting | Run the existing policy sequence under default costs, then reprice the trace afterward. | It cannot test whether a cost-aware policy changes action choice when costs change, and may understate fragility for `expected_utility_per_cost`. | Not the primary model. It may be a diagnostic only. |
| Policy-visible overlay | Resolve effective costs before action scoring, affordability checks, cumulative cost updates, and cost metrics. | It requires a carefully scoped P1c cost resolver so P1b defaults are not mutated. | Recommended future contract. |

Under the recommended contract, a future implementation should pass the cost profile into a P1c-only report-time run path. It must not mutate `P1B_ACTION_SPECS`, change `action_cost()`, or change default `p1b-report` / `p1b-evaluate` behavior. If the overlay cannot be implemented without changing P1b default behavior, the work should stop for design review.

## Cost Profile Constraints

Every P1c4 cost profile must satisfy these constraints:

- It uses only existing P1b action IDs.
- It is a sparse overlay; actions not listed keep their P1b default cost.
- Effective costs are integers.
- Minimum effective cost is `1`.
- Maximum effective cost is `8`.
- The default P1b `budget_limit` remains `12`.
- The default P1b `failure_cost` remains `14` (`budget_limit + 2`).
- A profile's max action cost stays below the failure cost and at or below two-thirds of the default budget.
- Profiles are run independently; P1c4 does not stack multiple profiles unless a later specification explicitly says so.
- Profiles may not alter `max_steps`, stopping thresholds, posterior update logic, `discovery_power`, `location_power`, `strong_causes`, observation types, or evidence scores.
- Profiles may not be tuned per bucket after seeing the selected variant outcome.

The baseline action-cost table remains:

| action_id | default_cost |
|---|---:|
| `run_smoke_tests` | 1 |
| `run_boundary_tests` | 2 |
| `run_null_missing_tests` | 2 |
| `run_config_matrix_tests` | 3 |
| `run_state_sequence_tests` | 4 |
| `run_property_search` | 5 |
| `inspect_traceback` | 1 |
| `inspect_coverage_spectrum` | 3 |
| `inspect_recent_diff` | 2 |
| `inspect_spec_clause` | 2 |

## Candidate Cost Profiles

The initial profile set should be small. These profiles are candidates for a later implementation; P1c4 does not execute them.

| profile_id | overlay actions and costs | effective cost range | stress rationale | expected metric impact |
|---|---|---:|---|---|
| `trace_access_expensive` | `inspect_traceback = 4`, `run_null_missing_tests = 5` | 1 to 5 | Exception and null/missing evidence is not treated as nearly free. This targets the high mean-cost pattern in `missing_optional_input` without changing observation content. | May widen mean-cost gaps for `missing_optional_input`, delay discovery for exception-like variants, and test whether policies overuse cheap traceback access. |
| `sequence_reproduction_expensive` | `run_state_sequence_tests = 8`, `run_property_search = 7` | 1 to 8 | Sequential and property-style reproduction can be costly. This targets the `state_sequence` first-failure-cost stress and late or missed discovery. | May reduce discovery within budget for state-sequence and spec-overlap variants, increase first-failure cost, and expose whether a policy avoids decisive but expensive sequence evidence. |
| `localization_evidence_expensive` | `inspect_coverage_spectrum = 6`, `inspect_recent_diff = 5`, `inspect_spec_clause = 4` | 1 to 6 | Coverage, recent-diff, and spec inspection may require nontrivial review time even when their content is unchanged. | May lower location top-3, cause top-1, or fix-intent top-1 performance for policies that depend on inspection after discovery, while keeping clean false-positive metrics separate. |
| `targeted_reproduction_expensive` | `run_boundary_tests = 4`, `run_config_matrix_tests = 5`, `run_state_sequence_tests = 7`, `run_property_search = 8` | 1 to 8 | Targeted reproduction suites become more expensive than smoke checks and lightweight inspection. This tests whether policies rely on broad targeted testing under the default budget. | May reduce success-rate-by-budget, increase mean investigation cost, and reveal profile-specific gaps across `boundary_precision`, `config_normalization`, `state_sequence`, and `spec_semantics`. |

The candidate profiles are intentionally bounded. They keep every action feasible as a first action under the default budget, but make some two-step or three-step paths impossible within `budget_limit = 12`. The failure cost of `14` remains worse than any single observation and continues to penalize missing first failure.

## Metrics And Reporting

A future P1c4 report should keep metric-specific profile gaps rather than introducing a single weighted utility.

Recommended metrics reuse existing P1b/P1c1 dimensions:

- `bug_discovery_rate_within_budget`
- `cost_to_first_failure`
- `location_top3_accuracy`
- `cause_top1_accuracy`
- `fix_intent_top1_accuracy`
- `wrong_cause_high_confidence_rate`
- `false_positive_rate_on_clean_cases`
- `mean_investigation_cost`
- P1c bucket metrics for the five buggy buckets and the clean false-positive bucket

Recommended profile gap rules:

| metric kind | direction | profile gap |
|---|---|---|
| Higher-is-better rates | higher is better | `baseline_value - profile_value` |
| Lower-is-better costs or error rates | lower is better | `profile_value - baseline_value` |

Positive gaps should mean the cost profile made the metric worse. Gaps should be reported per metric, policy, profile, and where useful, bucket. The report should not sum them into one utility score.

Recommended future JSON shape:

```json
{
  "observation_cost_stress": {
    "analysis_phase": "p1c4_bounded_observation_cost_stress",
    "stress_model": "bounded_action_cost_overlay",
    "cost_visibility": "policy_visible_overlay",
    "primary_observation_mode": "execution_grounded",
    "base_budget_limit": 12,
    "base_failure_cost": 14,
    "profiles": [
      {
        "profile_id": "sequence_reproduction_expensive",
        "cost_range": {"min": 1, "max": 8},
        "overlay": {
          "run_state_sequence_tests": 8,
          "run_property_search": 7
        },
        "unchanged_actions_use_default": true
      }
    ],
    "results_by_profile": {
      "sequence_reproduction_expensive": {
        "aggregate_metrics_by_policy": {},
        "bucket_metrics_by_policy": {},
        "profile_vs_baseline_gap_by_policy": {},
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

The top-level field should be `observation_cost_stress`. It must remain separate from P1c3 `adversarial_bucket_selection`.

Recommended future Markdown shape:

- A scope note stating that the report is analysis-only and uses bounded action-cost overlays.
- A profile table showing baseline costs, overlay costs, min/max cost, budget, and failure cost.
- A profile-by-policy metric table.
- A profile-vs-baseline gap table with metric direction.
- A bucket table for the existing P1c0 buckets.
- A separate clean false-positive section.
- A notes section repeating non-claims, observation-mode roles, and the no-default-mutation rule.

Raw variant IDs may appear only as diagnostic evidence for unusual profile gaps. They should not become headline claims.

## Interaction With P1c3 Bucket Selection

P1c4 is a separate slice from P1c3.

P1c3 selects worst buckets from existing P1c1 report metrics. P1c4 specifies cost profiles that may change future P1c cost-stress runs by changing effective action costs. The two concepts should not be merged in P1c4.

A future combined analysis may be useful, but it should be a later slice with an explicit contract. If that later work happens, it should keep the objects separate, for example:

- `adversarial_bucket_selection`: the existing P1c3 baseline selected-bucket report.
- `observation_cost_stress`: profile-level cost stress results.
- Optional nested diagnostic selection inside each cost profile, clearly labeled as a later combined analysis.

P1c4 should not use P1c3 selected buckets to tune cost profiles. The candidate profiles above are action-ID overlays motivated by observed fragility, not bucket-specific adversarial choices.

## Clean False-Positive Handling

Clean false-positive stress remains separate from buggy bucket metrics.

Cost profiles apply to clean variants as well as buggy variants, but reporting should separate:

- Buggy metrics over the five buggy P1c0 buckets.
- Clean false-positive metrics over the `clean_false_positive` bucket only.

For clean variants, report at least:

- `false_positive_rate_on_clean_cases`
- clean bucket mean investigation cost
- clean no-bug stop rate, if available from existing outcomes
- diagnostic false-positive clean variant IDs, if any

If false positives remain `0.0`, the report should say they are not triggered in the current cost profile. It must not claim that false-positive risk is solved beyond the current five clean variants.

## Observation Mode Contract

The headline P1c4 model uses `execution_grounded`.

`execution_grounded` remains primary because it uses checkout test results, exceptions, traced checkout functions, function-level coverage suspicion, and Phase C real-diff artifacts for `inspect_recent_diff`.

`metadata_synth` may be included only as an optional diagnostic comparison. It should not become the headline claim because it is metadata-dependent and can make metrics look better than execution-grounded evidence.

In any future `both` mode implementation:

- Top-level `observation_cost_stress` uses `execution_grounded`.
- `metadata_synth` appears only under a diagnostic object or section.
- The same cost profile IDs and overlays may be used for both modes, but the observation-mode role must remain explicit.

## Acceptance Criteria

P1c4 is ready for a later implementation prompt when:

- This specification is linked from planning/status docs.
- Cost stress is defined only as a bounded integer overlay over existing P1b action IDs.
- The overlay has `min = 1`, `max = 8`, default `budget_limit = 12`, and default `failure_cost = 14`.
- The recommended future contract is policy-visible overlay, not post-hoc-only accounting.
- The P1b default cost table and default P1b behavior remain unchanged.
- The candidate profile set is small and documented.
- Metrics are reported as metric-specific profile gaps, not as a weighted payoff.
- `execution_grounded` remains headline primary and `metadata_synth` remains optional diagnostic.
- P1c3 bucket selection remains a separate object and separate slice.
- Clean false-positive stress remains separate from buggy metrics.
- The wording does not claim real-world debugging accuracy, automated repair, a production fault-localization engine, a minimax-optimal policy, or a game-theoretic guarantee.

## Non-Claims / Stop Rules

P1c4 does not claim:

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
- Changing P1c0 bucket definitions or P1c1/P1c3 metric behavior.
- Changing observation content, adding observation dropout, or adding observation delay.
- Adding new variants, generated checkout source trees, or adversarial bug generation.
- Mixing clean false-positive variants into buggy metric denominators.
- Introducing a single weighted utility, regret objective, minimax objective, equilibrium concept, or formal payoff model.
- Expanding README public claims.
- Using GitHub operations before explicit user approval.

## Future Work After P1c4

The next implementation candidate is an analysis-only observation-cost stress report, preferably as an extension candidate for the existing `p1c-evaluate` command rather than a new command by default. The command decision can remain open until implementation design.

Future implementation should:

- Add a top-level `observation_cost_stress` object separate from `adversarial_bucket_selection`.
- Resolve effective action costs from a P1c-only cost profile overlay.
- Keep P1b default behavior unchanged when no profile is passed.
- Compare each profile against the default-cost baseline by metric and bucket.
- Include a separate clean false-positive stress subsection.
- Keep generated example JSON/Markdown out of commits unless explicitly requested.

Later slices may consider a combined cost-profile plus bucket-selection diagnostic, observation dropout/delay, or a formal game model. Those should wait until bounded cost profiles have a reviewed implementation and should not be folded into P1c4.
