# P1c Adversarial Planning Notes

Status: planning memo with implemented P1c1/P1c2/P1c3/P1c5/P1c7/P1c9 follow-through notes plus P1c4/P1c6/P1c8 specification links.

This memo starts P1c without implementing it. It records a safe design direction for adversarial or worst-case bug models after P1a and P1b, while preserving the current public boundary: the project is not yet a formal game-theoretic debugging system and does not claim a minimax guarantee.

## Current Baseline

P1a is a small synthetic baseline for Bayesian active bug-cause inference. It ranks coarse cause categories and recommends the next investigation action under a limited debugging budget.

P1b is a small injected checkout/pricing benchmark scaffold. It evaluates budget-aware policies on 20 buggy variants and 5 clean variants, with function-level location metrics, cause inference, fix-intent prediction, execution-derived observations, and Phase C real-diff artifacts.

P1c should build on those artifacts only after keeping the P1a/P1b boundaries clear.

## P1c Goal

The first P1c goal is not to generate new bugs or repair code. It is to ask whether existing investigation policies remain useful when the evidence is deliberately difficult, ambiguous, expensive, or misleading within a small reproducible benchmark.

A safe first framing:

> P1c studies robustness of cost-aware investigation policies under adversarially selected or worst-case evidence conditions in a small injected benchmark.

## Non-Goals

- Do not claim a production fault-localization engine.
- Do not generate patches or evaluate automated repair.
- Do not introduce LLM agent battles.
- Do not claim real-world debugging accuracy.
- Do not treat P1b real-diff artifacts as real repository histories.
- Do not add randomized fuzzing or property-based generation as the first P1c step.
- Do not claim a formal game-theoretic debugging system until there is an explicit player model, action space, payoff, and evaluation result.
- Do not claim a minimax-optimal policy or game-theoretic guarantee.

## Candidate Adversarial Models

### A. Worst-Case Variant Selection

The adversary selects from existing P1b variants after seeing the policy, but cannot change the variant source, metadata, or observation code. This is the smallest safe step because it uses the current benchmark without generating new artifacts.

Possible metric:

- Worst-case success rate within budget across variants.
- Worst-case cost to first failure.
- Worst-case location top-3 accuracy.
- Worst-case cause top-1 accuracy.
- Worst-case fix-intent top-1 accuracy.

### B. Evidence-Ambiguity Buckets

The benchmark labels variants by why they are difficult: weak coverage separation, misleading recent diff, late reproduction, clean-case false-positive risk, or cause ambiguity. The adversary selects a bucket rather than a raw variant.

Possible metric:

- Per-bucket policy rank.
- Gap between average performance and hardest-bucket performance.
- Policy instability across difficulty buckets.

### C. Observation-Cost Stress

The environment increases or reweights investigation costs within a fixed, documented range. This asks whether a policy depends too heavily on cheap but weak evidence or expensive but decisive evidence.

Possible metric:

- Success-rate-by-budget under cost profiles.
- Area under budget curve under cost profiles.
- Metric-specific profile-versus-baseline gaps for each policy and bucket.

### D. Observation Dropout Or Delay

The environment hides or delays a bounded subset of observations. This is not a free-form adversary; the dropout rules must be deterministic, reproducible, and documented.

Possible metric:

- Recovery rate after missing observations.
- Wrong-cause high-confidence rate.
- False positive rate on clean cases.

## Recommended First Slice

Start with A and B only.

Reasons:

- They reuse the existing P1b injected benchmark.
- They do not require generated source trees or new bug injection.
- They do not change policy logic, thresholds, or scoring.
- They can be implemented as analysis/reporting around existing P1b evaluation results.
- They keep P1c as robustness analysis rather than a new bug generator.

The first implementation candidate should therefore be a P1c analysis report, not a new execution harness.

P1c2 records the next slice as specification-only adversarial bucket selection. See [`p1c2_adversarial_bucket_selection_spec.md`](p1c2_adversarial_bucket_selection_spec.md). It keeps selection metric-specific, separates clean false-positive stress from buggy bucket metrics, and preserves `execution_grounded` as the headline observation mode with `metadata_synth` as diagnostic only.

P1c3 implements that P1c2 bucket-selection report as an analysis-only addition to `p1c-evaluate`. It consumes the existing P1c1 bucket metrics and per-variant outcomes, reports metric-specific selected buckets by policy, and keeps clean false-positive stress separate from buggy bucket metrics.

P1c4 records the next slice as specification-only bounded observation-cost stress. See [`p1c4_bounded_observation_cost_stress_spec.md`](p1c4_bounded_observation_cost_stress_spec.md). It defines bounded integer cost overlays over existing P1b action IDs, keeps the overlays separate from P1c3 bucket selection, and preserves `execution_grounded` as the headline observation mode with `metadata_synth` as diagnostic only.

P1c5 implements that P1c4 bounded observation-cost stress design as an analysis-only `observation_cost_stress` extension to the existing `p1c-evaluate` output. It uses P1c-only policy-visible cost overlays for action scoring, affordability, cumulative cost, and metrics; it does not mutate `P1B_ACTION_SPECS`, change `action_cost()`, or change default P1b behavior. The report keeps cost-profile stress separate from P1c3 `adversarial_bucket_selection`, keeps clean false-positive stress separate from buggy metrics, and avoids weighted payoff, regret, minimax, equilibrium, or formal payoff framing.

P1c6 records the next slice as a specification-only cost-profile bucket-selection diagnostic. See [`p1c6_cost_profile_bucket_selection_spec.md`](p1c6_cost_profile_bucket_selection_spec.md). It keeps the P1c3 top-level `adversarial_bucket_selection` as the default-cost baseline selected-bucket report, and recommends a future nested diagnostic under P1c5 `observation_cost_stress` for profile-conditioned selected-bucket shifts by policy and metric.

P1c7 implements that P1c6 nested diagnostic inside the existing `p1c-evaluate` output. It adds `observation_cost_stress.profile_conditioned_bucket_selection_by_profile`, derives selected buckets from existing P1c5 profile bucket metrics, compares them with the P1c3 baseline selection, keeps clean false-positive stress separate, and avoids weighted payoff, regret, minimax, equilibrium, or formal payoff framing.

P1c8 records the next slice as specification-only bounded observation dropout/delay. See [`p1c8_bounded_observation_dropout_delay_spec.md`](p1c8_bounded_observation_dropout_delay_spec.md). It defines deterministic, reproducible, bounded future profiles for P1c-only observation visibility or arrival-timing perturbations, keeps P1b default observations and traces unchanged, keeps P1c3/P1c5/P1c7 objects separate, and avoids weighted payoff, regret, minimax, equilibrium, or formal payoff framing.

P1c9 implements the P1c8 report candidate as an analysis-only `observation_dropout_delay_stress` extension to the existing `p1c-evaluate` output. It applies four deterministic copied-observation profiles, retains source observations while perturbing only policy-facing visible copies, keeps clean false-positive stress separate from buggy metrics, preserves `execution_grounded` as the headline primary mode with `metadata_synth` diagnostic only, and keeps P1c3/P1c5/P1c7 report objects separate.

## Proposed P1c0 Deliverable

Before implementation, create a compact specification with:

- Difficulty labels for existing P1b variants.
- A definition of "worst-case" for each metric.
- A distinction between average-case P1b evaluation and worst-case P1c reporting.
- A small table of candidate policies to compare.
- A stop rule for avoiding claims that require a larger benchmark.

No code should change until that specification is reviewed.

## Proposed P1c1 Deliverable

After P1c0 is accepted, implement an analysis-only command or report that consumes existing P1b evaluation traces and produces:

- Worst-case metrics by policy.
- Difficulty-bucket metrics by policy.
- Average-versus-worst gap by policy.
- A short Markdown summary of which policies are brittle and why.

This should not add new injected variants, randomized test generation, patch generation, or LLM-based debugging.

## Open Design Questions

- Should the adversary choose a raw variant, a difficulty bucket, or an observation condition?
- Should "worst-case" be measured per metric or by a weighted utility score?
- Should clean variants be part of the adversary's choice, especially for false-positive stress?
- Which metric-specific profile gaps should be reported before considering any later regret or formal payoff framing?
- How many difficulty labels can be assigned without making the 25-variant benchmark look more general than it is?
- Which P1c result would justify moving from robustness reporting to a more formal game model?

## Safety Checks

Before any P1c implementation, verify:

- The README still says this is not yet a formal game-theoretic debugging system.
- `docs/implementation_status.md` still separates implemented work from future work.
- P1c text does not claim real-world debugging accuracy.
- P1c text does not imply automated repair.
- P1c text does not treat P1b real-diff artifacts as real repository histories.
- Any adversarial language is tied to a small, bounded, reproducible benchmark.

## Suggested Next Step

Review the P1c9 `observation_dropout_delay_stress` results before deciding whether to run a larger design review, add a new specification-only P1c slice, or pause P1c expansion.
