"""Bayesian updating and information-gain utilities."""

from __future__ import annotations

import math
from typing import Iterable

from bug_cause_inference.likelihoods import (
    ACTION_CANDIDATE_EVIDENCE,
    ACTION_SPECS,
    CAUSES,
    EVIDENCE_LIKELIHOODS,
)
from bug_cause_inference.models import Distribution, Observation


def normalize(weights: Distribution) -> Distribution:
    total = sum(weights.values())
    if total <= 0.0:
        raise ValueError("Cannot normalize non-positive distribution.")
    return {key: value / total for key, value in weights.items()}


def uniform_prior() -> Distribution:
    probability = 1.0 / len(CAUSES)
    return {cause: probability for cause in CAUSES}


def update_with_evidence(prior: Distribution, evidence_id: str) -> Distribution:
    if evidence_id not in EVIDENCE_LIKELIHOODS:
        raise KeyError(f"Unknown evidence_id {evidence_id!r}.")
    row = EVIDENCE_LIKELIHOODS[evidence_id]
    return normalize({cause: prior[cause] * row[cause] for cause in CAUSES})


def update(prior: Distribution, observations: Iterable[Observation]) -> Distribution:
    posterior = dict(prior)
    for observation in observations:
        posterior = update_with_evidence(posterior, observation.evidence_id)
    return posterior


def entropy(distribution: Distribution) -> float:
    return -sum(probability * math.log2(probability) for probability in distribution.values() if probability > 0.0)


def rank_hypotheses(distribution: Distribution) -> list[tuple[str, float]]:
    return sorted(distribution.items(), key=lambda item: (-item[1], item[0]))


def top_hypothesis(distribution: Distribution) -> tuple[str, float]:
    return rank_hypotheses(distribution)[0]


def _conditional_candidate_likelihoods(action_id: str) -> dict[str, Distribution]:
    candidates = ACTION_CANDIDATE_EVIDENCE[action_id]
    by_evidence: dict[str, Distribution] = {}
    totals_by_cause = {
        cause: sum(EVIDENCE_LIKELIHOODS[evidence_id][cause] for evidence_id in candidates)
        for cause in CAUSES
    }
    for evidence_id in candidates:
        by_evidence[evidence_id] = {
            cause: EVIDENCE_LIKELIHOODS[evidence_id][cause] / totals_by_cause[cause] for cause in CAUSES
        }
    return by_evidence


def predictive_observation_distribution(posterior: Distribution, action_id: str) -> Distribution:
    """Estimate P(evidence | current posterior, action) over action-specific outcomes.

    This is a deliberately simple P1a scoring heuristic. Prediction is restricted
    to an action-specific candidate evidence set, while posterior updates use the
    global evidence likelihood table. It is not a fully coherent generative
    observation model for real debugging data.
    """

    conditional = _conditional_candidate_likelihoods(action_id)
    raw = {
        evidence_id: sum(posterior[cause] * likelihoods[cause] for cause in CAUSES)
        for evidence_id, likelihoods in conditional.items()
    }
    return normalize(raw)


def expected_information_gain(posterior: Distribution, action_id: str) -> float:
    """Expected entropy reduction for one not-yet-run action.

    Candidate observation probabilities are action-conditioned for prediction,
    while the posterior update still uses the fixed global evidence likelihood
    table. This keeps the P1a model simple and fully reproducible, but the score
    should be read as a heuristic action-ranking signal rather than as a fully
    coherent action-conditioned generative model.
    """

    before = entropy(posterior)
    predictive = predictive_observation_distribution(posterior, action_id)
    expected_after = 0.0
    for evidence_id, probability in predictive.items():
        after = update_with_evidence(posterior, evidence_id)
        expected_after += probability * entropy(after)
    return max(0.0, before - expected_after)


def expected_information_gain_per_cost(posterior: Distribution, action_id: str) -> float:
    return expected_information_gain(posterior, action_id) / ACTION_SPECS[action_id].cost
