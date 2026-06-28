"""Shared data models for the bug-cause inference prototype."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

Distribution = dict[str, float]


@dataclass(frozen=True)
class Observation:
    """Discrete evidence emitted by a synthetic case or investigation action."""

    type: str
    evidence_id: str
    value: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Observation":
        return cls(type=data["type"], evidence_id=data["evidence_id"], value=data["value"])

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ActionSpec:
    """A fixed investigation action available in every synthetic case."""

    action_id: str
    label: str
    cost: int
    observation_type: str
    target_hypotheses: tuple[str, ...]


@dataclass(frozen=True)
class ActionOutcome:
    """The deterministic hidden result for running one action on one case."""

    action: str
    cost: int
    observation_if_run: Observation

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ActionOutcome":
        return cls(
            action=data["action"],
            cost=int(data["cost"]),
            observation_if_run=Observation.from_dict(data["observation_if_run"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "cost": self.cost,
            "observation_if_run": self.observation_if_run.to_dict(),
        }


@dataclass(frozen=True)
class SyntheticCase:
    """A reproducible synthetic observed-bug case."""

    case_id: str
    true_cause: str
    difficulty: str
    template_id: str
    seed: int
    initial_observations: tuple[Observation, ...]
    available_investigations: tuple[ActionOutcome, ...]
    notes: str = "Synthetic case. No private project data."

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SyntheticCase":
        return cls(
            case_id=data["case_id"],
            true_cause=data["true_cause"],
            difficulty=data["difficulty"],
            template_id=data["template_id"],
            seed=int(data["seed"]),
            initial_observations=tuple(Observation.from_dict(item) for item in data["initial_observations"]),
            available_investigations=tuple(
                ActionOutcome.from_dict(item) for item in data["available_investigations"]
            ),
            notes=data.get("notes", "Synthetic case. No private project data."),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "true_cause": self.true_cause,
            "difficulty": self.difficulty,
            "template_id": self.template_id,
            "seed": self.seed,
            "initial_observations": [item.to_dict() for item in self.initial_observations],
            "available_investigations": [item.to_dict() for item in self.available_investigations],
            "notes": self.notes,
        }

    def outcome_for(self, action_id: str) -> ActionOutcome:
        for outcome in self.available_investigations:
            if outcome.action == action_id:
                return outcome
        raise KeyError(f"Case {self.case_id} has no outcome for action {action_id!r}.")


@dataclass(frozen=True)
class HypothesisScore:
    rank: int
    hypothesis: str
    posterior_probability: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class StepTrace:
    """One executed investigation step."""

    step: int
    policy: str
    selected_action: str
    action_cost: int
    observation: Observation
    prior_posterior: Distribution
    updated_posterior: Distribution
    cumulative_cost: int
    action_scores: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "step": self.step,
            "policy": self.policy,
            "selected_action": self.selected_action,
            "action_cost": self.action_cost,
            "observation": self.observation.to_dict(),
            "prior_posterior": dict(self.prior_posterior),
            "updated_posterior": dict(self.updated_posterior),
            "cumulative_cost": self.cumulative_cost,
            "action_scores": self.action_scores,
        }


@dataclass
class SimulationResult:
    """Final state and trace for one policy run on one synthetic case."""

    case_id: str
    true_cause: str
    policy: str
    observations: list[Observation]
    posterior: Distribution
    executed_actions: list[str]
    cumulative_cost: int
    current_step: int
    stop_reason: str | None
    trace: list[StepTrace]

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "true_cause": self.true_cause,
            "policy": self.policy,
            "observations": [item.to_dict() for item in self.observations],
            "posterior": dict(self.posterior),
            "executed_actions": list(self.executed_actions),
            "cumulative_cost": self.cumulative_cost,
            "current_step": self.current_step,
            "stop_reason": self.stop_reason,
            "trace": [item.to_dict() for item in self.trace],
        }


@dataclass(frozen=True)
class StopSettings:
    top_probability_threshold: float = 0.75
    top_margin_threshold: float = 0.15
    budget_limit: int = 10
    max_steps: int = 5
    min_expected_ig_per_cost: float = 0.03
    failure_cost: int = 12
