# P1c Adversarial Planning Notes

Status: planning memo only.

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
- Regret against the best fixed policy for that profile.

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
- Should P1c use regret against the best existing P1b policy, or only report worst-case metric gaps?
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

Write the P1c0 specification for difficulty labels and worst-case metrics, then review it before touching code.
