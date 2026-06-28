"""Investigation policies and sequential simulation."""

from __future__ import annotations

import random
from typing import Any

from bug_cause_inference.bayes import (
    expected_information_gain,
    expected_information_gain_per_cost,
    rank_hypotheses,
    uniform_prior,
    update,
)
from bug_cause_inference.likelihoods import (
    ACTION_ORDER,
    ACTION_SPECS,
    FIXED_CHECKLIST_ORDER,
    POSTERIOR_GREEDY_ACTIONS,
)
from bug_cause_inference.models import Distribution, Observation, SimulationResult, StepTrace, StopSettings, SyntheticCase

ACTIVE_POLICIES: tuple[str, ...] = (
    "random",
    "fixed_checklist",
    "posterior_greedy",
    "cheapest_first",
    "information_gain",
    "information_gain_per_cost",
)

POLICIES: tuple[str, ...] = ACTIVE_POLICIES + ("static_posterior",)
PRIMARY_POLICY = "information_gain_per_cost"


def available_actions(
    executed_actions: list[str] | tuple[str, ...],
    remaining_budget: int | None = None,
) -> list[str]:
    executed = set(executed_actions)
    actions = [action_id for action_id in ACTION_ORDER if action_id not in executed]
    if remaining_budget is not None:
        actions = [action_id for action_id in actions if ACTION_SPECS[action_id].cost <= remaining_budget]
    return actions


def score_actions(
    posterior: Distribution,
    executed_actions: list[str] | tuple[str, ...],
    remaining_budget: int | None = None,
) -> list[dict[str, Any]]:
    scores: list[dict[str, Any]] = []
    for action_id in available_actions(executed_actions, remaining_budget):
        ig = expected_information_gain(posterior, action_id)
        cost = ACTION_SPECS[action_id].cost
        scores.append(
            {
                "action": action_id,
                "cost": cost,
                "expected_information_gain": round(ig, 6),
                "expected_information_gain_per_cost": round(ig / cost, 6),
            }
        )
    return scores


def _tie_key(action_id: str) -> tuple[int, str]:
    return (ACTION_SPECS[action_id].cost, action_id)


def choose_action(
    policy: str,
    posterior: Distribution,
    executed_actions: list[str] | tuple[str, ...],
    rng: random.Random | None = None,
    remaining_budget: int | None = None,
) -> str | None:
    if policy not in POLICIES:
        raise ValueError(f"Unknown policy {policy!r}. Expected one of {POLICIES}.")
    if policy == "static_posterior":
        return None

    candidates = available_actions(executed_actions, remaining_budget)
    if not candidates:
        return None

    if policy == "random":
        return (rng or random.Random()).choice(candidates)

    if policy == "fixed_checklist":
        for action_id in FIXED_CHECKLIST_ORDER:
            if action_id in candidates:
                return action_id
        return None

    if policy == "posterior_greedy":
        top_cause = rank_hypotheses(posterior)[0][0]
        for action_id in POSTERIOR_GREEDY_ACTIONS[top_cause]:
            if action_id in candidates:
                return action_id
        return sorted(candidates, key=_tie_key)[0]

    if policy == "cheapest_first":
        return sorted(candidates, key=_tie_key)[0]

    if policy == "information_gain":
        return sorted(
            candidates,
            key=lambda action_id: (
                -expected_information_gain(posterior, action_id),
                ACTION_SPECS[action_id].cost,
                action_id,
            ),
        )[0]

    if policy == "information_gain_per_cost":
        return sorted(
            candidates,
            key=lambda action_id: (
                -expected_information_gain_per_cost(posterior, action_id),
                ACTION_SPECS[action_id].cost,
                action_id,
            ),
        )[0]

    raise AssertionError(f"Unhandled policy {policy!r}.")


def check_stop(
    posterior: Distribution,
    cumulative_cost: int,
    current_step: int,
    executed_actions: list[str],
    settings: StopSettings,
) -> str | None:
    ranked = rank_hypotheses(posterior)
    top_probability = ranked[0][1]
    second_probability = ranked[1][1]
    if top_probability >= settings.top_probability_threshold and (
        top_probability - second_probability
    ) >= settings.top_margin_threshold:
        return "top_probability_threshold"
    if cumulative_cost >= settings.budget_limit:
        return "budget_limit"
    if current_step >= settings.max_steps:
        return "max_steps"
    remaining_budget = settings.budget_limit - cumulative_cost
    candidates = available_actions(executed_actions, remaining_budget)
    if not candidates:
        return "no_available_actions_within_budget"
    best_ig_per_cost = max(expected_information_gain_per_cost(posterior, action_id) for action_id in candidates)
    if best_ig_per_cost < settings.min_expected_ig_per_cost:
        return "low_expected_information_gain"
    return None


def run_investigation(
    case: SyntheticCase,
    policy: str = PRIMARY_POLICY,
    settings: StopSettings | None = None,
    rng_seed: int = 0,
) -> SimulationResult:
    settings = settings or StopSettings()
    rng = random.Random(rng_seed)
    observations: list[Observation] = list(case.initial_observations)
    posterior = update(uniform_prior(), observations)
    executed_actions: list[str] = []
    trace: list[StepTrace] = []
    cumulative_cost = 0
    current_step = 0

    if policy == "static_posterior":
        return SimulationResult(
            case_id=case.case_id,
            true_cause=case.true_cause,
            policy=policy,
            observations=observations,
            posterior=posterior,
            executed_actions=executed_actions,
            cumulative_cost=cumulative_cost,
            current_step=current_step,
            stop_reason="static_posterior_no_investigation",
            trace=trace,
        )

    stop_reason = check_stop(posterior, cumulative_cost, current_step, executed_actions, settings)
    while stop_reason is None:
        remaining_budget = settings.budget_limit - cumulative_cost
        action_scores = score_actions(posterior, executed_actions, remaining_budget)
        selected = choose_action(policy, posterior, executed_actions, rng, remaining_budget)
        if selected is None:
            stop_reason = "no_available_actions_within_budget"
            break

        prior_posterior = dict(posterior)
        outcome = case.outcome_for(selected)
        observations.append(outcome.observation_if_run)
        posterior = update(posterior, [outcome.observation_if_run])
        executed_actions.append(selected)
        cumulative_cost += outcome.cost
        current_step += 1
        trace.append(
            StepTrace(
                step=current_step,
                policy=policy,
                selected_action=selected,
                action_cost=outcome.cost,
                observation=outcome.observation_if_run,
                prior_posterior=prior_posterior,
                updated_posterior=dict(posterior),
                cumulative_cost=cumulative_cost,
                action_scores=action_scores,
            )
        )
        stop_reason = check_stop(posterior, cumulative_cost, current_step, executed_actions, settings)

    return SimulationResult(
        case_id=case.case_id,
        true_cause=case.true_cause,
        policy=policy,
        observations=observations,
        posterior=posterior,
        executed_actions=executed_actions,
        cumulative_cost=cumulative_cost,
        current_step=current_step,
        stop_reason=stop_reason,
        trace=trace,
    )
