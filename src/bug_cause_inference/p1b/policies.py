"""Policies and investigation loop for the P1b benchmark."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Any

from bug_cause_inference.p1b.actions import P1B_ACTION_SPECS, P1B_ACTIONS, P1B_OBSERVATION_MODES, run_action
from bug_cause_inference.p1b.dataset import LOCATION_CANDIDATES
from bug_cause_inference.p1b.execution import P1BExecutionContext
from bug_cause_inference.p1b.models import (
    P1B_CAUSE_CATEGORIES,
    P1B_FIX_INTENT_CATEGORIES,
    P1BRunResult,
    P1BSettings,
    P1BStepTrace,
    P1BVariant,
    rank_distribution,
    uniform_distribution,
    update_distribution,
)


P1B_POLICIES = (
    "random_action",
    "fixed_checklist",
    "test_first",
    "coverage_first",
    "recent_diff_first",
    "cause_only_p1a_style",
    "expected_utility_per_cost",
)

P1B_PRIMARY_POLICY = "expected_utility_per_cost"

# P1d2-only policy ID. It is intentionally excluded from P1B_POLICIES and all
# existing P1b/P1c CLI choices and defaults.
STATE_SEQUENCE_GUARD_POLICY_ID = "state_sequence_guard"
_STATE_SEQUENCE_GUARD_TARGET_ACTION = "run_state_sequence_tests"
_STATE_SEQUENCE_GUARD_RESERVE = 4
_STATE_SEQUENCE_GUARD_MAX_STEPS = 6

FIXED_CHECKLIST_ORDER = (
    "run_smoke_tests",
    "run_boundary_tests",
    "run_null_missing_tests",
    "run_config_matrix_tests",
    "run_state_sequence_tests",
    "inspect_coverage_spectrum",
)

TEST_FIRST_ORDER = (
    "run_smoke_tests",
    "run_boundary_tests",
    "run_null_missing_tests",
    "run_config_matrix_tests",
    "run_state_sequence_tests",
    "run_property_search",
    "inspect_traceback",
    "inspect_coverage_spectrum",
    "inspect_spec_clause",
    "inspect_recent_diff",
)

RECENT_DIFF_FIRST_ORDER = (
    "inspect_recent_diff",
    "run_smoke_tests",
    "run_boundary_tests",
    "run_config_matrix_tests",
    "run_null_missing_tests",
    "run_state_sequence_tests",
    "inspect_coverage_spectrum",
    "inspect_spec_clause",
)


@dataclass
class _State:
    bug_presence: float
    cause_posterior: dict[str, float]
    location_posterior: dict[str, float]
    fix_intent_posterior: dict[str, float]
    executed_actions: list[str]
    cumulative_cost: int
    current_step: int
    bug_detected: bool
    execution_context: P1BExecutionContext | None = None


@dataclass(frozen=True)
class _StateSequenceGuardHistory:
    """Policy-visible projection used by the preregistered P1d2 selector."""

    bug_presence_posterior: float
    cause_posterior: dict[str, float]
    location_posterior: dict[str, float]
    fix_intent_posterior: dict[str, float]
    executed_action_ids: tuple[str, ...]
    cumulative_cost: int
    current_step: int
    bug_detected: bool


def _entropy(distribution: dict[str, float]) -> float:
    if not distribution:
        return 0.0
    max_entropy = math.log2(len(distribution))
    if max_entropy == 0:
        return 0.0
    entropy = -sum(value * math.log2(value) for value in distribution.values() if value > 0)
    return entropy / max_entropy


def _remaining_actions(state: _State, remaining_budget: int) -> list[str]:
    return [
        action_id
        for action_id, spec in P1B_ACTION_SPECS.items()
        if action_id not in state.executed_actions and spec.cost <= remaining_budget
    ]


def score_actions(state: _State, remaining_budget: int) -> list[dict[str, Any]]:
    scores: list[dict[str, Any]] = []
    cause_entropy = _entropy(state.cause_posterior)
    location_entropy = _entropy(state.location_posterior)
    fix_entropy = _entropy(state.fix_intent_posterior)
    for action_id in _remaining_actions(state, remaining_budget):
        spec = P1B_ACTION_SPECS[action_id]
        cause_relevance = sum(state.cause_posterior.get(cause, 0.0) for cause in spec.strong_causes)
        if not spec.strong_causes:
            cause_relevance = 0.25
        discovery_utility = spec.discovery_power * (1.0 - state.bug_presence)
        cause_utility = cause_entropy * cause_relevance
        location_utility = location_entropy * spec.location_power
        fix_utility = fix_entropy * 0.20
        if state.bug_detected:
            discovery_utility *= 0.35
            location_utility *= 1.25
        expected_utility = discovery_utility + cause_utility + location_utility + fix_utility
        scores.append(
            {
                "action": action_id,
                "cost": spec.cost,
                "expected_utility": round(expected_utility, 6),
                "expected_utility_per_cost": round(expected_utility / spec.cost, 6),
                "discovery_utility": round(discovery_utility, 6),
                "cause_utility": round(cause_utility, 6),
                "location_utility": round(location_utility, 6),
            }
        )
    return sorted(scores, key=lambda item: (-item["expected_utility_per_cost"], item["cost"], item["action"]))


def _first_available(order: tuple[str, ...], state: _State, remaining_budget: int) -> str | None:
    available = set(_remaining_actions(state, remaining_budget))
    for action_id in order:
        if action_id in available:
            return action_id
    return None


def _state_sequence_guard_history(state: _State) -> _StateSequenceGuardHistory:
    return _StateSequenceGuardHistory(
        bug_presence_posterior=state.bug_presence,
        cause_posterior=dict(state.cause_posterior),
        location_posterior=dict(state.location_posterior),
        fix_intent_posterior=dict(state.fix_intent_posterior),
        executed_action_ids=tuple(state.executed_actions),
        cumulative_cost=state.cumulative_cost,
        current_step=state.current_step,
        bug_detected=state.bug_detected,
    )


def _choose_state_sequence_guard(
    history: _StateSequenceGuardHistory,
    remaining_budget: int,
) -> str:
    """Return the exact preregistered P1d2 state-sequence-guard action.

    The runner calls this helper only after the common stop predicate is false,
    so at least one feasible action must exist. The helper receives no variant,
    bucket, ground-truth, execution-context, or report-only field.
    """

    scoring_state = _State(
        bug_presence=history.bug_presence_posterior,
        cause_posterior=dict(history.cause_posterior),
        location_posterior=dict(history.location_posterior),
        fix_intent_posterior=dict(history.fix_intent_posterior),
        executed_actions=list(history.executed_action_ids),
        cumulative_cost=history.cumulative_cost,
        current_step=history.current_step,
        bug_detected=history.bug_detected,
    )
    ranked = score_actions(scoring_state, remaining_budget)
    if not ranked:
        raise RuntimeError(
            "state_sequence_guard requires a nonterminal history with a feasible action"
        )

    target = _STATE_SEQUENCE_GUARD_TARGET_ACTION
    feasible_ids = {item["action"] for item in ranked}
    reserve_active = (
        not history.bug_detected
        and target not in history.executed_action_ids
        and target in feasible_ids
    )
    if not reserve_active:
        return ranked[0]["action"]

    reserve_preserving = [
        item["action"]
        for item in ranked
        if item["action"] != target
        and item["cost"] <= remaining_budget - _STATE_SEQUENCE_GUARD_RESERVE
    ]
    if (
        not reserve_preserving
        or history.current_step >= _STATE_SEQUENCE_GUARD_MAX_STEPS - 1
    ):
        return target

    candidate_pool = set(reserve_preserving)
    candidate_pool.add(target)
    return next(item["action"] for item in ranked if item["action"] in candidate_pool)


def choose_action(policy: str, state: _State, remaining_budget: int, rng: random.Random) -> str | None:
    available = _remaining_actions(state, remaining_budget)
    if not available:
        return None
    if policy == "random_action":
        return rng.choice(available)
    if policy == "fixed_checklist":
        return _first_available(FIXED_CHECKLIST_ORDER, state, remaining_budget) or available[0]
    if policy == "test_first":
        return _first_available(TEST_FIRST_ORDER, state, remaining_budget) or available[0]
    if policy == "coverage_first":
        if state.bug_detected and "inspect_coverage_spectrum" in available:
            return "inspect_coverage_spectrum"
        return _first_available(TEST_FIRST_ORDER, state, remaining_budget) or available[0]
    if policy == "recent_diff_first":
        return _first_available(RECENT_DIFF_FIRST_ORDER, state, remaining_budget) or available[0]
    if policy == STATE_SEQUENCE_GUARD_POLICY_ID:
        return _choose_state_sequence_guard(
            _state_sequence_guard_history(state),
            remaining_budget,
        )
    scores = score_actions(state, remaining_budget)
    if policy == "cause_only_p1a_style":
        cause_scores = []
        for item in scores:
            spec = P1B_ACTION_SPECS[item["action"]]
            relevance = sum(state.cause_posterior.get(cause, 0.0) for cause in spec.strong_causes)
            cause_scores.append((relevance / spec.cost, spec.cost, item["action"]))
        cause_scores.sort(key=lambda item: (-item[0], item[1], item[2]))
        return cause_scores[0][2]
    if policy == "expected_utility_per_cost":
        return scores[0]["action"]
    raise ValueError(f"Unknown P1b policy: {policy}")


def _update_bug_presence(current: float, observation_bug_detected: bool, no_bug_evidence: bool) -> float:
    if observation_bug_detected:
        return min(0.98, current + 0.35)
    if no_bug_evidence:
        return max(0.02, current - 0.18)
    return min(0.98, current + 0.05)


def _check_stop(state: _State, settings: P1BSettings, best_score: float | None = None) -> str | None:
    no_bug_probability = 1.0 - state.bug_presence
    cause_top = rank_distribution(state.cause_posterior)[0]
    location_top = rank_distribution(state.location_posterior)[0]
    if no_bug_probability >= settings.no_bug_probability_threshold:
        return "no_bug_probability_threshold"
    if (
        state.bug_detected
        and state.bug_presence >= settings.bug_presence_threshold
        and location_top[1] >= settings.location_top1_threshold
        and cause_top[1] >= settings.cause_top1_threshold
    ):
        return "bug_confidence_threshold"
    if state.cumulative_cost >= settings.budget_limit:
        return "budget_limit"
    if state.current_step >= settings.max_steps:
        return "max_steps"
    if best_score is not None and best_score < settings.min_expected_utility_per_cost:
        return "low_expected_utility"
    return None


def _stable_seed(variant_id: str, rng_seed: int) -> int:
    return rng_seed + sum((index + 1) * ord(char) for index, char in enumerate(variant_id))


def run_p1b_investigation(
    variant: P1BVariant,
    policy: str = P1B_PRIMARY_POLICY,
    settings: P1BSettings | None = None,
    rng_seed: int | None = None,
    observation_mode: str = "metadata_synth",
) -> P1BRunResult:
    if observation_mode not in P1B_OBSERVATION_MODES:
        raise ValueError(f"Unknown P1b observation mode: {observation_mode}")
    settings = settings or P1BSettings()
    seed = settings.rng_seed if rng_seed is None else rng_seed
    rng = random.Random(_stable_seed(variant.variant_id, seed))
    state = _State(
        bug_presence=0.50,
        cause_posterior=uniform_distribution(P1B_CAUSE_CATEGORIES),
        location_posterior=uniform_distribution(LOCATION_CANDIDATES),
        fix_intent_posterior=uniform_distribution(P1B_FIX_INTENT_CATEGORIES),
        executed_actions=[],
        cumulative_cost=0,
        current_step=0,
        bug_detected=False,
        execution_context=P1BExecutionContext() if observation_mode == "execution_grounded" else None,
    )
    trace: list[P1BStepTrace] = []
    reproduction_input: str | None = None
    first_failure_cost: int | None = None
    cost_to_true_cause_top1: int | None = None
    stop_reason = "not_started"

    while True:
        remaining_budget = settings.budget_limit - state.cumulative_cost
        action_scores = score_actions(state, remaining_budget)
        best_score = action_scores[0]["expected_utility_per_cost"] if action_scores else None
        stop_reason = _check_stop(state, settings, best_score)
        if stop_reason is not None:
            break
        action_id = choose_action(policy, state, remaining_budget, rng)
        if action_id is None:
            stop_reason = "no_available_actions"
            break

        prior_bug = state.bug_presence
        prior_cause = dict(state.cause_posterior)
        prior_location = dict(state.location_posterior)
        prior_fix = dict(state.fix_intent_posterior)
        observation = run_action(
            variant,
            action_id,
            observation_mode=observation_mode,
            execution_context=state.execution_context,
        )

        state.executed_actions.append(action_id)
        state.cumulative_cost += observation.cost
        state.current_step += 1
        state.bug_detected = state.bug_detected or observation.bug_detected
        state.bug_presence = _update_bug_presence(
            state.bug_presence,
            observation.bug_detected,
            observation.no_bug_evidence,
        )
        state.cause_posterior = update_distribution(state.cause_posterior, observation.cause_scores)
        state.location_posterior = update_distribution(state.location_posterior, observation.location_scores)
        state.fix_intent_posterior = update_distribution(state.fix_intent_posterior, observation.fix_intent_scores)
        if observation.reproduction_input and reproduction_input is None:
            reproduction_input = observation.reproduction_input
        if observation.failure_found and first_failure_cost is None:
            first_failure_cost = state.cumulative_cost
        if (
            variant.is_buggy
            and variant.true_cause_category
            and rank_distribution(state.cause_posterior)[0][0] == variant.true_cause_category
            and cost_to_true_cause_top1 is None
            and state.cumulative_cost <= settings.budget_limit
        ):
            cost_to_true_cause_top1 = state.cumulative_cost

        trace.append(
            P1BStepTrace(
                step=state.current_step,
                policy=policy,
                selected_action=action_id,
                observation=observation,
                prior_bug_presence_posterior=prior_bug,
                updated_bug_presence_posterior=state.bug_presence,
                prior_cause_posterior=prior_cause,
                updated_cause_posterior=dict(state.cause_posterior),
                prior_location_posterior=prior_location,
                updated_location_posterior=dict(state.location_posterior),
                prior_fix_intent_posterior=prior_fix,
                updated_fix_intent_posterior=dict(state.fix_intent_posterior),
                cumulative_cost=state.cumulative_cost,
                action_scores=action_scores,
            )
        )

    if variant.is_buggy and cost_to_true_cause_top1 is None:
        cost_to_true_cause_top1 = settings.failure_cost
    return P1BRunResult(
        variant_id=variant.variant_id,
        is_buggy=variant.is_buggy,
        policy=policy,
        bug_detected=state.bug_detected,
        reproduction_input=reproduction_input,
        bug_presence_posterior=state.bug_presence,
        cause_posterior=state.cause_posterior,
        location_posterior=state.location_posterior,
        fix_intent_posterior=state.fix_intent_posterior,
        executed_actions=state.executed_actions,
        cumulative_cost=state.cumulative_cost,
        current_step=state.current_step,
        stop_reason=stop_reason,
        trace=trace,
        first_failure_cost=first_failure_cost,
        cost_to_true_cause_top1=cost_to_true_cause_top1,
    )
