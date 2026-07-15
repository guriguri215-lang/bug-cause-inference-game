"""Fail-closed exact compatibility gate for the P2a legacy adapter slice."""

from __future__ import annotations

import hashlib
import json
import math
import random
import re
from copy import deepcopy
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from bug_cause_inference.p1b.actions import P1B_ACTION_SPECS
from bug_cause_inference.p1b.dataset import LOCATION_CANDIDATES, load_p1b_variants
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
from bug_cause_inference.p1b import policies as p1b_policies
from bug_cause_inference.p1c.evaluation import _variant_outcome
from bug_cause_inference.p1c.labels import P1C_VARIANT_LABELS
from bug_cause_inference.p2a.execution import (
    isolated_legacy_checkout,
    legacy_catalog_contract,
    run_patch_grounded_legacy_action,
)


LEGACY_VARIANT_IDS = tuple(
    [f"P1B-BUG-{index:03d}" for index in range(1, 21)]
    + [f"P1B-CLEAN-{index:03d}" for index in range(21, 26)]
)
FORMAL_SIX_POLICY_IDS = (
    "fixed_checklist",
    "test_first",
    "coverage_first",
    "recent_diff_first",
    "cause_only_p1a_style",
    "expected_utility_per_cost",
)
STOP_PRECEDENCE = (
    "no_bug_probability_threshold",
    "bug_confidence_threshold",
    "budget_limit",
    "max_steps",
    "low_expected_utility",
)

OBSERVATION_FIELD_IDS = (
    "action_id",
    "cost",
    "observation_type",
    "bug_detected",
    "failure_found",
    "no_bug_evidence",
    "reproduction_input",
    "exception_type",
    "cause_scores",
    "location_scores",
    "fix_intent_scores",
    "failed_test_ids",
    "passed_test_ids",
    "executed_functions",
    "failing_executed_functions",
    "passing_executed_functions",
    "stack_functions",
    "coverage_suspicion",
    "coverage_counts",
    "changed_files",
    "changed_functions",
)
DIAGNOSTIC_FIELD_IDS = (
    "test_id",
    "group",
    "passed",
    "expected",
    "actual",
    "exception_type",
    "reproduction_input",
    "evidence_tags",
    "fix_intent_hints",
    "executed_functions",
    "stack_functions",
)
STATE_FIELD_IDS = (
    "bug_presence_posterior",
    "cause_posterior",
    "location_posterior",
    "fix_intent_posterior",
    "executed_action_ids",
    "cumulative_cost",
    "current_step",
    "bug_detected",
    "remaining_budget",
    "feasible_action_ids",
    "action_scores",
    "common_stop_result",
)

# Filled from the controlling base revision. Contract validation runs before any
# adapter execution, so drift cannot be normalized into a new accepted result.
EXPECTED_LEGACY_CATALOG_DIGEST = "a62d0c6a11ae5f57cffa572bd06277d863e52df6a5367235a6a804adc8bc01dd"
EXPECTED_LEGACY_RUNTIME_DIGEST = "755e97d46b9aa67c771d77548e996ec02e98d9eb91a87db7d273821465fb5563"
EXPECTED_LEGACY_ARTIFACT_DIGEST = "87f5fc00cde1cb8d02f4df7651b98c4e0e75ace833da82e256c29e1f90ad3d8c"

_P1B_SOURCE_FILES = (
    "p1b/dataset.py",
    "p1b/models.py",
    "p1b/actions.py",
    "p1b/execution.py",
    "p1b/policies.py",
    "p1b/evaluation.py",
    "p1b/real_diff.py",
    "p1c/labels.py",
    "p1c/evaluation.py",
)
_ABSOLUTE_PATH_RE = re.compile(r"(?:^|\s)(?:[A-Za-z]:[\\/]|/[^\s])")


@dataclass(frozen=True)
class CompatibilityMismatch:
    variant_id: str
    policy: str
    step: int | None
    action_id: str | None
    field_path: str
    current_value: Any
    adapter_value: Any


@dataclass(frozen=True)
class LegacyCompatibilityReport:
    status: str
    expected_pair_count: int
    observed_pair_count: int
    matched_pair_count: int
    mismatch_count: int
    variant_ids: tuple[str, ...]
    policy_ids: tuple[str, ...]
    catalog_digest: str
    runtime_digest: str
    artifact_digest: str
    generated_paths_in_identity: bool
    mismatches: tuple[CompatibilityMismatch, ...] = ()


class LegacyCompatibilityError(RuntimeError):
    """Raised before acceptance whenever a frozen compatibility contract fails."""

    def __init__(
        self,
        message: str,
        mismatch: CompatibilityMismatch | None = None,
        report: LegacyCompatibilityReport | None = None,
    ) -> None:
        super().__init__(message)
        self.mismatch = mismatch
        self.report = report


def _typed_node(value: Any) -> dict[str, Any]:
    if value is None:
        return {"type": "none", "value": None}
    if type(value) is bool:
        return {"type": "bool", "value": value}
    if type(value) is int:
        return {"type": "int", "value": str(value)}
    if type(value) is float:
        if not math.isfinite(value):
            raise LegacyCompatibilityError("Non-finite floats are forbidden in canonical identity.")
        return {"type": "float", "value": repr(value)}
    if type(value) is str:
        return {"type": "str", "value": value}
    if type(value) is list:
        return {"type": "list", "items": [_typed_node(item) for item in value]}
    if type(value) is tuple:
        return {"type": "tuple", "items": [_typed_node(item) for item in value]}
    if type(value) is dict:
        return {
            "type": "dict",
            "items": [
                [_typed_node(key), _typed_node(child)]
                for key, child in value.items()
            ],
        }
    raise LegacyCompatibilityError(f"Unsupported canonical value type: {type(value).__name__}")


def canonical_digest(value: Any) -> str:
    payload = json.dumps(
        _typed_node(value),
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _source_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _normalized_text_hash(path: Path) -> str:
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _runtime_contract() -> dict[str, Any]:
    source_root = _source_root()
    settings = asdict(P1BSettings())
    return {
        "source_hashes": [
            {"path": relative, "sha256": _normalized_text_hash(source_root / relative)}
            for relative in _P1B_SOURCE_FILES
        ],
        "legacy_variant_ids": tuple(variant.variant_id for variant in load_p1b_variants()),
        "formal_policy_ids": FORMAL_SIX_POLICY_IDS,
        "full_policy_registry": p1b_policies.P1B_POLICIES,
        "primary_policy": p1b_policies.P1B_PRIMARY_POLICY,
        "action_specs": [
            {
                "action_id": action_id,
                "cost": spec.cost,
                "observation_type": spec.observation_type,
                "strong_causes": spec.strong_causes,
                "discovery_power": spec.discovery_power,
                "location_power": spec.location_power,
            }
            for action_id, spec in P1B_ACTION_SPECS.items()
        ],
        "settings": settings,
        "stop_precedence": STOP_PRECEDENCE,
        "fixed_checklist_order": p1b_policies.FIXED_CHECKLIST_ORDER,
        "test_first_order": p1b_policies.TEST_FIRST_ORDER,
        "recent_diff_first_order": p1b_policies.RECENT_DIFF_FIRST_ORDER,
        "score_tie_order": (
            "expected_utility_per_cost_desc",
            "cost_asc",
            "action_id_asc",
        ),
    }


def _artifact_contract() -> dict[str, Any]:
    artifact_root = _source_root() / "p1b" / "artifacts" / "real_diff"
    paths = [artifact_root / "manifest.json"]
    paths.extend(sorted((artifact_root / "baseline").rglob("*.py")))
    paths.extend(sorted((artifact_root / "patches").glob("*.patch")))
    return {
        "files": [
            {
                "path": path.relative_to(artifact_root).as_posix(),
                "sha256": _normalized_text_hash(path),
            }
            for path in paths
        ]
    }


def current_contract_digests() -> dict[str, str]:
    return {
        "catalog_digest": canonical_digest(legacy_catalog_contract()),
        "runtime_digest": canonical_digest(_runtime_contract()),
        "artifact_digest": canonical_digest(_artifact_contract()),
    }


def validate_frozen_legacy_contracts() -> dict[str, str]:
    variants = tuple(variant.variant_id for variant in load_p1b_variants())
    if variants != LEGACY_VARIANT_IDS:
        raise LegacyCompatibilityError(
            f"Legacy variant IDs/order drifted: expected {LEGACY_VARIANT_IDS!r}, observed {variants!r}."
        )
    if FORMAL_SIX_POLICY_IDS != p1b_policies.P1B_POLICIES[1:]:
        raise LegacyCompatibilityError("Formal six policy IDs/order drifted.")
    if len(set(variants)) != 25 or len(set(FORMAL_SIX_POLICY_IDS)) != 6:
        raise LegacyCompatibilityError("Legacy variant or policy registry contains duplicates.")
    digests = current_contract_digests()
    expected = {
        "catalog_digest": EXPECTED_LEGACY_CATALOG_DIGEST,
        "runtime_digest": EXPECTED_LEGACY_RUNTIME_DIGEST,
        "artifact_digest": EXPECTED_LEGACY_ARTIFACT_DIGEST,
    }
    for key, expected_value in expected.items():
        if digests[key] != expected_value:
            raise LegacyCompatibilityError(
                f"Frozen {key} drifted: expected {expected_value}, observed {digests[key]}."
            )
    return digests


def _exception_actual(result: dict[str, Any]) -> Any:
    if result.get("exception_type") is None:
        return deepcopy(result["actual"])
    return {
        "payload_kind": "exception",
        "exception_type": result["exception_type"],
    }


def canonical_test_diagnostics(observation: Any) -> list[dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    for result in observation.test_results:
        diagnostics.append(
            {
                "test_id": result["test_id"],
                "group": result["group"],
                "passed": result["passed"],
                "expected": deepcopy(result["expected"]),
                "actual": _exception_actual(result),
                "exception_type": result["exception_type"],
                "reproduction_input": result["reproduction_input"],
                "evidence_tags": deepcopy(result["evidence_tags"]),
                "fix_intent_hints": deepcopy(result["fix_intent_hints"]),
                "executed_functions": deepcopy(result["executed_functions"]),
                "stack_functions": deepcopy(result["stack_functions"]),
            }
        )
    return diagnostics


def canonical_policy_visible_observation(observation: Any) -> dict[str, Any]:
    return {
        field: deepcopy(getattr(observation, field))
        for field in OBSERVATION_FIELD_IDS
    }


def _state_from_values(
    *,
    bug_presence: float,
    cause: dict[str, float],
    location: dict[str, float],
    fix_intent: dict[str, float],
    executed_actions: list[str],
    cumulative_cost: int,
    current_step: int,
    bug_detected: bool,
) -> Any:
    return p1b_policies._State(
        bug_presence=bug_presence,
        cause_posterior=dict(cause),
        location_posterior=dict(location),
        fix_intent_posterior=dict(fix_intent),
        executed_actions=list(executed_actions),
        cumulative_cost=cumulative_cost,
        current_step=current_step,
        bug_detected=bug_detected,
    )


def canonical_policy_state(
    state: Any,
    settings: P1BSettings,
    *,
    recorded_action_scores: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    remaining_budget = settings.budget_limit - state.cumulative_cost
    action_scores = (
        p1b_policies.score_actions(state, remaining_budget)
        if recorded_action_scores is None
        else deepcopy(recorded_action_scores)
    )
    feasible_action_ids = [
        action_id
        for action_id, spec in P1B_ACTION_SPECS.items()
        if action_id not in state.executed_actions and spec.cost <= remaining_budget
    ]
    best_score = action_scores[0]["expected_utility_per_cost"] if action_scores else None
    return {
        "bug_presence_posterior": state.bug_presence,
        "cause_posterior": dict(state.cause_posterior),
        "location_posterior": dict(state.location_posterior),
        "fix_intent_posterior": dict(state.fix_intent_posterior),
        "executed_action_ids": list(state.executed_actions),
        "cumulative_cost": state.cumulative_cost,
        "current_step": state.current_step,
        "bug_detected": state.bug_detected,
        "remaining_budget": remaining_budget,
        "feasible_action_ids": feasible_action_ids,
        "action_scores": deepcopy(action_scores),
        "common_stop_result": p1b_policies._check_stop(state, settings, best_score),
    }


def _selection_contract() -> dict[str, Any]:
    return {
        "score_row_order": (
            "expected_utility_per_cost_desc",
            "cost_asc",
            "action_id_asc",
        ),
        "fixed_checklist_fallback_order": p1b_policies.FIXED_CHECKLIST_ORDER,
        "test_first_fallback_order": p1b_policies.TEST_FIRST_ORDER,
        "recent_diff_first_fallback_order": p1b_policies.RECENT_DIFF_FIRST_ORDER,
        "cause_only_tie_order": (
            "cause_relevance_per_cost_desc",
            "cost_asc",
            "action_id_asc",
        ),
    }


def canonical_run_projection(
    variant: P1BVariant,
    result: P1BRunResult,
    settings: P1BSettings,
) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    executed: list[str] = []
    prior_bug_detected = False
    prior_cost = 0
    for trace_index, trace in enumerate(result.trace):
        prior_state = _state_from_values(
            bug_presence=trace.prior_bug_presence_posterior,
            cause=trace.prior_cause_posterior,
            location=trace.prior_location_posterior,
            fix_intent=trace.prior_fix_intent_posterior,
            executed_actions=executed,
            cumulative_cost=prior_cost,
            current_step=trace.step - 1,
            bug_detected=prior_bug_detected,
        )
        executed = [*executed, trace.selected_action]
        prior_bug_detected = prior_bug_detected or trace.observation.bug_detected
        prior_cost = trace.cumulative_cost
        updated_state = _state_from_values(
            bug_presence=trace.updated_bug_presence_posterior,
            cause=trace.updated_cause_posterior,
            location=trace.updated_location_posterior,
            fix_intent=trace.updated_fix_intent_posterior,
            executed_actions=executed,
            cumulative_cost=trace.cumulative_cost,
            current_step=trace.step,
            bug_detected=prior_bug_detected,
        )
        diagnostics = canonical_test_diagnostics(trace.observation)
        steps.append(
            {
                "step": trace.step,
                "policy": trace.policy,
                "selected_action": trace.selected_action,
                "observation": canonical_policy_visible_observation(trace.observation),
                "diagnostic_cases": diagnostics,
                "diagnostic_digest": canonical_digest(diagnostics),
                "prior_state": canonical_policy_state(
                    prior_state,
                    settings,
                    recorded_action_scores=trace.action_scores,
                ),
                "updated_state": canonical_policy_state(
                    updated_state,
                    settings,
                    recorded_action_scores=(
                        result.trace[trace_index + 1].action_scores
                        if trace_index + 1 < len(result.trace)
                        else None
                    ),
                ),
            }
        )
    terminal_state = _state_from_values(
        bug_presence=result.bug_presence_posterior,
        cause=result.cause_posterior,
        location=result.location_posterior,
        fix_intent=result.fix_intent_posterior,
        executed_actions=result.executed_actions,
        cumulative_cost=result.cumulative_cost,
        current_step=result.current_step,
        bug_detected=result.bug_detected,
    )
    label = P1C_VARIANT_LABELS[variant.variant_id]
    projection = {
        "variant_id": result.variant_id,
        "policy": result.policy,
        "stop_precedence": STOP_PRECEDENCE,
        "selection_order_contract": _selection_contract(),
        "steps": steps,
        "terminal_state": canonical_policy_state(terminal_state, settings),
        "final_run": {
            "stop_reason": result.stop_reason,
            "bug_detected": result.bug_detected,
            "reproduction_input": result.reproduction_input,
            "bug_presence_posterior": result.bug_presence_posterior,
            "cause_posterior": dict(result.cause_posterior),
            "location_posterior": dict(result.location_posterior),
            "fix_intent_posterior": dict(result.fix_intent_posterior),
            "executed_action_ids": list(result.executed_actions),
            "cumulative_cost": result.cumulative_cost,
            "current_step": result.current_step,
            "first_failure_cost": result.first_failure_cost,
            "cost_to_true_cause_top1": result.cost_to_true_cause_top1,
        },
        "p1c_compatible_outcome": _variant_outcome(
            variant,
            result,
            settings,
            label.primary_bucket,
        ),
    }
    validate_canonical_path_boundary(projection)
    return projection


def _safe_value(value: Any) -> Any:
    if type(value) is str:
        if _ABSOLUTE_PATH_RE.search(value):
            return "<redacted-local-path>"
        return value if len(value) <= 240 else f"{value[:237]}..."
    if type(value) is list:
        return [_safe_value(item) for item in value[:12]]
    if type(value) is tuple:
        return tuple(_safe_value(item) for item in value[:12])
    if type(value) is dict:
        return {key: _safe_value(child) for key, child in list(value.items())[:12]}
    return value


def _first_difference(left: Any, right: Any, path: str = "$" ) -> tuple[str, Any, Any] | None:
    if type(left) is not type(right):
        return f"{path}.<type>", type(left).__name__, type(right).__name__
    if type(left) is dict:
        left_keys = list(left)
        right_keys = list(right)
        if left_keys != right_keys:
            return f"{path}.<key_order>", left_keys, right_keys
        for key in left_keys:
            mismatch = _first_difference(left[key], right[key], f"{path}.{key}")
            if mismatch:
                return mismatch
        return None
    if type(left) in {list, tuple}:
        if len(left) != len(right):
            return f"{path}.<length>", len(left), len(right)
        for index, (left_item, right_item) in enumerate(zip(left, right)):
            mismatch = _first_difference(left_item, right_item, f"{path}[{index}]")
            if mismatch:
                return mismatch
        return None
    if left != right:
        return path, left, right
    return None


def assert_canonical_runs_equal(
    current: dict[str, Any],
    adapter: dict[str, Any],
    *,
    variant_id: str,
    policy: str,
) -> None:
    mismatch = _first_difference(current, adapter)
    if mismatch is None:
        return
    path, current_value, adapter_value = mismatch
    match = re.search(r"\.steps\[(\d+)\]", path)
    step_index = int(match.group(1)) if match else None
    step = step_index + 1 if step_index is not None else None
    action_id = None
    if step_index is not None and step_index < len(current.get("steps", [])):
        action_id = current["steps"][step_index].get("selected_action")
    diagnostic = CompatibilityMismatch(
        variant_id=variant_id,
        policy=policy,
        step=step,
        action_id=action_id,
        field_path=path,
        current_value=_safe_value(current_value),
        adapter_value=_safe_value(adapter_value),
    )
    raise LegacyCompatibilityError(
        "Legacy compatibility mismatch: "
        f"variant={variant_id}, policy={policy}, step={step}, action={action_id}, "
        f"field={path}, current={diagnostic.current_value!r}, "
        f"adapter={diagnostic.adapter_value!r}",
        mismatch=diagnostic,
    )


def expected_legacy_pairs() -> list[tuple[str, str]]:
    return [
        (variant_id, policy)
        for variant_id in LEGACY_VARIANT_IDS
        for policy in FORMAL_SIX_POLICY_IDS
    ]


def validate_exact_pair_coverage(pairs: list[tuple[str, str]]) -> None:
    expected = expected_legacy_pairs()
    if pairs == expected:
        return
    duplicates = sorted({pair for pair in pairs if pairs.count(pair) > 1})
    missing = [pair for pair in expected if pair not in pairs]
    extra = [pair for pair in pairs if pair not in expected]
    if not missing and not extra and not duplicates:
        detail = "pair order differs from the stable variant-policy product"
    else:
        detail = f"missing={missing[:3]}, extra={extra[:3]}, duplicates={duplicates[:3]}"
    raise LegacyCompatibilityError(
        f"Legacy pair coverage must be exactly 25 x 6 = 150 in stable order; {detail}."
    )


def validate_canonical_path_boundary(value: Any, path: str = "$") -> None:
    """Reject absolute local paths anywhere in a canonical identity value."""

    if type(value) is str and _ABSOLUTE_PATH_RE.search(value):
        raise LegacyCompatibilityError(f"Absolute local path entered canonical identity at {path}.")
    if type(value) is dict:
        for key, child in value.items():
            validate_canonical_path_boundary(key, f"{path}.<key>")
            validate_canonical_path_boundary(child, f"{path}.{key}")
    elif type(value) in {list, tuple}:
        for index, child in enumerate(value):
            validate_canonical_path_boundary(child, f"{path}[{index}]")


def run_patch_grounded_legacy_investigation(
    variant: P1BVariant,
    policy: str,
    settings: P1BSettings,
    modules: dict[str, Any],
    module_prefix: str,
) -> P1BRunResult:
    """Run the current policy loop with P2a-only patch-grounded observations."""

    if policy not in FORMAL_SIX_POLICY_IDS:
        raise LegacyCompatibilityError(f"Policy {policy!r} is outside the formal six.")
    state = p1b_policies._State(
        bug_presence=0.50,
        cause_posterior=uniform_distribution(P1B_CAUSE_CATEGORIES),
        location_posterior=uniform_distribution(LOCATION_CANDIDATES),
        fix_intent_posterior=uniform_distribution(P1B_FIX_INTENT_CATEGORIES),
        executed_actions=[],
        cumulative_cost=0,
        current_step=0,
        bug_detected=False,
        execution_context=P1BExecutionContext(),
    )
    trace: list[P1BStepTrace] = []
    reproduction_input: str | None = None
    first_failure_cost: int | None = None
    cost_to_true_cause_top1: int | None = None
    stop_reason = "not_started"
    rng = random.Random(p1b_policies._stable_seed(variant.variant_id, settings.rng_seed))

    while True:
        remaining_budget = settings.budget_limit - state.cumulative_cost
        action_scores = p1b_policies.score_actions(state, remaining_budget)
        best_score = action_scores[0]["expected_utility_per_cost"] if action_scores else None
        stop_reason = p1b_policies._check_stop(state, settings, best_score)
        if stop_reason is not None:
            break
        action_id = p1b_policies.choose_action(policy, state, remaining_budget, rng)
        if action_id is None:
            stop_reason = "no_available_actions"
            break

        prior_bug = state.bug_presence
        prior_cause = dict(state.cause_posterior)
        prior_location = dict(state.location_posterior)
        prior_fix = dict(state.fix_intent_posterior)
        observation = run_patch_grounded_legacy_action(
            variant_id=variant.variant_id,
            action_id=action_id,
            context=state.execution_context,
            modules=modules,
            module_prefix=module_prefix,
        )
        state.executed_actions.append(action_id)
        state.cumulative_cost += observation.cost
        state.current_step += 1
        state.bug_detected = state.bug_detected or observation.bug_detected
        state.bug_presence = p1b_policies._update_bug_presence(
            state.bug_presence,
            observation.bug_detected,
            observation.no_bug_evidence,
        )
        state.cause_posterior = update_distribution(state.cause_posterior, observation.cause_scores)
        state.location_posterior = update_distribution(state.location_posterior, observation.location_scores)
        state.fix_intent_posterior = update_distribution(
            state.fix_intent_posterior,
            observation.fix_intent_scores,
        )
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


def run_legacy_exact_compatibility() -> LegacyCompatibilityReport:
    """Execute and compare every ordered legacy variant-policy pair exactly once."""

    digests = validate_frozen_legacy_contracts()
    variants = load_p1b_variants()
    settings = P1BSettings()
    observed_pairs: list[tuple[str, str]] = []
    mismatches: list[CompatibilityMismatch] = []
    matched = 0
    for variant in variants:
        with isolated_legacy_checkout(variant.variant_id) as (modules, module_prefix):
            for policy in FORMAL_SIX_POLICY_IDS:
                observed_pairs.append((variant.variant_id, policy))
                current_result = p1b_policies.run_p1b_investigation(
                    variant,
                    policy=policy,
                    settings=settings,
                    observation_mode="execution_grounded",
                )
                adapter_result = run_patch_grounded_legacy_investigation(
                    variant,
                    policy,
                    settings,
                    modules,
                    module_prefix,
                )
                current = canonical_run_projection(variant, current_result, settings)
                adapter = canonical_run_projection(variant, adapter_result, settings)
                try:
                    assert_canonical_runs_equal(
                        current,
                        adapter,
                        variant_id=variant.variant_id,
                        policy=policy,
                    )
                except LegacyCompatibilityError as exc:
                    if exc.mismatch is not None:
                        mismatches.append(exc.mismatch)
                    invalid_report = LegacyCompatibilityReport(
                        status="invalid",
                        expected_pair_count=150,
                        observed_pair_count=len(observed_pairs),
                        matched_pair_count=matched,
                        mismatch_count=len(mismatches),
                        variant_ids=LEGACY_VARIANT_IDS,
                        policy_ids=FORMAL_SIX_POLICY_IDS,
                        catalog_digest=digests["catalog_digest"],
                        runtime_digest=digests["runtime_digest"],
                        artifact_digest=digests["artifact_digest"],
                        generated_paths_in_identity=False,
                        mismatches=tuple(mismatches),
                    )
                    raise LegacyCompatibilityError(
                        str(exc),
                        exc.mismatch,
                        invalid_report,
                    ) from exc
                matched += 1
    validate_exact_pair_coverage(observed_pairs)
    return LegacyCompatibilityReport(
        status="valid",
        expected_pair_count=150,
        observed_pair_count=len(observed_pairs),
        matched_pair_count=matched,
        mismatch_count=0,
        variant_ids=LEGACY_VARIANT_IDS,
        policy_ids=FORMAL_SIX_POLICY_IDS,
        catalog_digest=digests["catalog_digest"],
        runtime_digest=digests["runtime_digest"],
        artifact_digest=digests["artifact_digest"],
        generated_paths_in_identity=False,
    )
