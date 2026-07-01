"""Data models for the P1b injected-bug benchmark scaffold."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


P1B_CAUSE_CATEGORIES = (
    "boundary_condition",
    "missing_null_handling",
    "configuration_environment",
    "state_order_dependence",
    "specification_mismatch",
)

P1B_FIX_INTENT_CATEGORIES = (
    "change_comparison",
    "add_missing_value_guard",
    "fix_config_default",
    "normalize_config_or_input",
    "fix_state_transition",
    "make_operation_idempotent",
    "recompute_stale_state",
    "align_calculation_order_with_spec",
    "align_selection_rule_with_spec",
    "add_spec_exception_rule",
)


@dataclass(frozen=True)
class P1BSettings:
    """Default P1b MVP policy and stopping parameters."""

    budget_limit: int = 12
    max_steps: int = 6
    failure_cost: int | None = None
    bug_presence_threshold: float = 0.75
    no_bug_probability_threshold: float = 0.80
    location_top1_threshold: float = 0.50
    cause_top1_threshold: float = 0.60
    min_expected_utility_per_cost: float = 0.03
    rng_seed: int = 0

    def __post_init__(self) -> None:
        if self.failure_cost is None:
            object.__setattr__(self, "failure_cost", self.budget_limit + 2)


@dataclass(frozen=True)
class P1BActionSpec:
    action_id: str
    cost: int
    observation_type: str
    strong_causes: tuple[str, ...]
    discovery_power: float
    location_power: float


@dataclass(frozen=True)
class P1BVariant:
    variant_id: str
    is_buggy: bool
    true_cause_category: str | None = None
    target_module: str | None = None
    target_function: str | None = None
    line_span_hint: str | None = None
    bug_summary: str | None = None
    trigger_condition: str | None = None
    failing_input_or_sequence: str | None = None
    expected_behavior: str | None = None
    actual_behavior: str | None = None
    fix_intent_category: str | None = None
    fix_intent_description: str | None = None
    difficulty: str | None = None
    primary_discovery_action: str | None = None
    secondary_discovery_actions: tuple[str, ...] = ()
    observable_signals: str | None = None
    distractor_locations: tuple[str, ...] = ()
    covered_spec_area: str | None = None
    expected_clean_behavior: str | None = None
    confusing_signals: str | None = None
    why_false_positive_might_happen: str | None = None
    recommended_no_bug_evidence: str | None = None

    @property
    def target_location(self) -> str | None:
        if self.target_module is None or self.target_function is None:
            return None
        return f"{self.target_module.removesuffix('.py')}.{self.target_function}"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "P1BVariant":
        copied = dict(data)
        for key in ("secondary_discovery_actions", "distractor_locations"):
            if key in copied:
                copied[key] = tuple(copied[key])
        return cls(**copied)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class P1BObservation:
    action_id: str
    cost: int
    observation_type: str
    summary: str
    bug_detected: bool = False
    failure_found: bool = False
    no_bug_evidence: bool = False
    reproduction_input: str | None = None
    exception_type: str | None = None
    cause_scores: dict[str, float] = field(default_factory=dict)
    location_scores: dict[str, float] = field(default_factory=dict)
    fix_intent_scores: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class P1BStepTrace:
    step: int
    policy: str
    selected_action: str
    observation: P1BObservation
    prior_bug_presence_posterior: float
    updated_bug_presence_posterior: float
    prior_cause_posterior: dict[str, float]
    updated_cause_posterior: dict[str, float]
    prior_location_posterior: dict[str, float]
    updated_location_posterior: dict[str, float]
    prior_fix_intent_posterior: dict[str, float]
    updated_fix_intent_posterior: dict[str, float]
    cumulative_cost: int
    action_scores: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["observation"] = self.observation.to_dict()
        return data


@dataclass
class P1BRunResult:
    variant_id: str
    is_buggy: bool
    policy: str
    bug_detected: bool
    reproduction_input: str | None
    bug_presence_posterior: float
    cause_posterior: dict[str, float]
    location_posterior: dict[str, float]
    fix_intent_posterior: dict[str, float]
    executed_actions: list[str]
    cumulative_cost: int
    current_step: int
    stop_reason: str
    trace: list[P1BStepTrace]
    first_failure_cost: int | None = None
    cost_to_true_cause_top1: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "variant_id": self.variant_id,
            "is_buggy": self.is_buggy,
            "policy": self.policy,
            "bug_detected": self.bug_detected,
            "reproduction_input": self.reproduction_input,
            "bug_presence_posterior": round(self.bug_presence_posterior, 6),
            "cause_posterior": round_distribution(self.cause_posterior),
            "location_posterior": round_distribution(self.location_posterior),
            "fix_intent_posterior": round_distribution(self.fix_intent_posterior),
            "executed_actions": list(self.executed_actions),
            "cumulative_cost": self.cumulative_cost,
            "current_step": self.current_step,
            "stop_reason": self.stop_reason,
            "trace": [item.to_dict() for item in self.trace],
            "first_failure_cost": self.first_failure_cost,
            "cost_to_true_cause_top1": self.cost_to_true_cause_top1,
        }


def normalize_distribution(scores: dict[str, float]) -> dict[str, float]:
    total = sum(max(value, 0.0) for value in scores.values())
    if total <= 0:
        if not scores:
            return {}
        value = 1.0 / len(scores)
        return {key: value for key in scores}
    return {key: max(value, 0.0) / total for key, value in scores.items()}


def uniform_distribution(labels: tuple[str, ...] | list[str]) -> dict[str, float]:
    value = 1.0 / len(labels)
    return {label: value for label in labels}


def update_distribution(prior: dict[str, float], weights: dict[str, float]) -> dict[str, float]:
    combined = {label: probability * weights.get(label, 1.0) for label, probability in prior.items()}
    return normalize_distribution(combined)


def rank_distribution(distribution: dict[str, float]) -> list[tuple[str, float]]:
    return sorted(distribution.items(), key=lambda item: (-item[1], item[0]))


def round_distribution(distribution: dict[str, float]) -> dict[str, float]:
    return {key: round(value, 6) for key, value in distribution.items()}
