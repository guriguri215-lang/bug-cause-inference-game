# P1a Evaluation Notes

## Scope

P1a is a Bayesian active bug-cause inference prototype. It recommends the next investigation action under a limited debugging budget.

It does not discover real code bugs, localize source code, or generate patches. It works on synthetic observed-bug cases with known cause labels and fixed observation likelihoods.

## Dataset Diagnostics

The current dataset contains 50 synthetic cases: 5 cause categories x 10 cases. The fixed generation seed is `20260627`.

Current initial-state diagnostics:

- initial top-1 accuracy: 70%
- initial top-2 accuracy: 100%
- initially wrong top-1 cases: 15 out of 50

These diagnostics mean the two initial observations are already highly informative. This is useful for validating the mechanics of the first MVP, but it also means the current dataset is not a hard benchmark.

## Main Evaluation Results

Main policy: `information_gain_per_cost`.

Current all-case results:

- `information_gain_per_cost` mean `cost_to_true_cause_top1`: 1.12
- `fixed_checklist` mean `cost_to_true_cause_top1`: 1.56
- fixed-checklist cost reduction: 28.2051%
- primary success rate within budget: 94%
- primary wrong-stop rate: 13.0435%

These results support the idea that cost-aware active investigation can reduce investigation cost on this synthetic setup. They do not prove real-world debugging accuracy.

The `primary_success_rate_at_least_80_percent` success check is a diagnostic default, not a charter success criterion.

## Initially Wrong Cases

For cases where the initial top-1 hypothesis is wrong:

- `information_gain_per_cost` mean cost: 3.733333
- `information_gain_per_cost` success rate: 0.8
- `fixed_checklist` mean cost: 5.2
- `fixed_checklist` success rate: 0.866667

This is an important tradeoff. The main policy is more cost-efficient on average for initially-wrong cases, but the fixed checklist has a better success rate on that subset. This should be treated as a useful limitation, not hidden.

## Interpretation

The current P1a result is promising for a small synthetic prototype: `information_gain_per_cost` lowers average investigation cost against the fixed checklist and performs strongly on the initially-wrong subset by cost.

The result should be read with caution:

- The synthetic data may be too easy because top-2 accuracy is already 100% before any investigation action.
- A non-trivial wrong-stop rate means high-confidence stopping needs caution.
- The expected-information-gain score is a P1a heuristic, not a fully coherent real-world observation model.
- The evaluation validates this synthetic setup, not real project debugging.

## Recommended Next Work

- Keep the current P1a as a baseline.
- Add harder synthetic cases later instead of tuning the current dataset just to improve headline results.
- Consider threshold and calibration analysis later.
- Defer real-code injected bug discovery and localization to P1b.
- Defer adversarial or worst-case bug modeling to P1c.

## Analysis-Only Patch

The analysis-only patch adds reports for wrong-stop cases, initially-wrong cases, stop reasons, category-level failures, and a small threshold sweep. It does not change the model, dataset, default stop thresholds, likelihood table, or main policy.

The purpose is to make current failure modes easier to inspect before deciding whether to design harder synthetic cases, run calibration analysis, or move toward P1b.

Analysis report policy runs use one diagnostic run per policy and case. The `random` policy uses `rng_seed=0`, so its analysis rows should be read as fixed-seed diagnostic traces rather than repeated-random averages.

The analysis report separates related but different quantities:

- `wrong_stop_rate_within_confidence_stops` is `wrong_stop_count / confidence_stop_count`.
- `wrong_stop_rate_per_case` is `wrong_stop_count / num_cases`.
- Threshold-sweep `wrong_stop_rate` uses the existing evaluation definition: wrong stops divided by confidence stops.
- `ever_true_cause_top1_within_budget` means the true cause became the top-1 hypothesis within budget at least once.
- `final_top_is_true` records whether the final top hypothesis is the true cause.
- `is_wrong_stop` records a high-confidence stop on an incorrect final top hypothesis.
