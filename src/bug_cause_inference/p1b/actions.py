"""Investigation actions for the P1b injected-bug benchmark."""

from __future__ import annotations

from typing import Any

from bug_cause_inference.p1b.checkout import cart, config, shipping
from bug_cause_inference.p1b.execution import P1BExecutionContext, run_execution_grounded_action
from bug_cause_inference.p1b.models import P1BActionSpec, P1BObservation, P1BVariant


P1B_ACTION_SPECS: dict[str, P1BActionSpec] = {
    "run_smoke_tests": P1BActionSpec(
        "run_smoke_tests",
        1,
        "test_failure",
        ("specification_mismatch", "missing_null_handling"),
        0.45,
        0.25,
    ),
    "run_boundary_tests": P1BActionSpec(
        "run_boundary_tests",
        2,
        "boundary_counterexample",
        ("boundary_condition",),
        0.70,
        0.45,
    ),
    "run_null_missing_tests": P1BActionSpec(
        "run_null_missing_tests",
        2,
        "exception_trace",
        ("missing_null_handling",),
        0.70,
        0.55,
    ),
    "run_config_matrix_tests": P1BActionSpec(
        "run_config_matrix_tests",
        3,
        "config_counterexample",
        ("configuration_environment",),
        0.70,
        0.45,
    ),
    "run_state_sequence_tests": P1BActionSpec(
        "run_state_sequence_tests",
        4,
        "state_sequence_counterexample",
        ("state_order_dependence",),
        0.75,
        0.55,
    ),
    "run_property_search": P1BActionSpec(
        "run_property_search",
        5,
        "property_counterexample",
        ("boundary_condition", "state_order_dependence", "specification_mismatch"),
        0.65,
        0.35,
    ),
    "inspect_traceback": P1BActionSpec(
        "inspect_traceback",
        1,
        "exception_trace",
        ("missing_null_handling", "configuration_environment"),
        0.30,
        0.70,
    ),
    "inspect_coverage_spectrum": P1BActionSpec(
        "inspect_coverage_spectrum",
        3,
        "coverage_suspicious_location",
        tuple(),
        0.15,
        0.85,
    ),
    "inspect_recent_diff": P1BActionSpec(
        "inspect_recent_diff",
        2,
        "recent_diff_signal",
        ("configuration_environment", "state_order_dependence", "boundary_condition"),
        0.20,
        0.55,
    ),
    "inspect_spec_clause": P1BActionSpec(
        "inspect_spec_clause",
        2,
        "spec_clause_mismatch",
        ("specification_mismatch", "boundary_condition", "configuration_environment"),
        0.45,
        0.50,
    ),
}

P1B_ACTIONS = tuple(P1B_ACTION_SPECS)
P1B_OBSERVATION_MODES = ("metadata_synth", "execution_grounded")


def action_cost(action_id: str) -> int:
    return P1B_ACTION_SPECS[action_id].cost


def _action_matches_variant(variant: P1BVariant, action_id: str) -> bool:
    return action_id == variant.primary_discovery_action or action_id in variant.secondary_discovery_actions


def _is_failure_action(action_id: str) -> bool:
    return action_id.startswith("run_") or action_id in {"inspect_traceback", "inspect_spec_clause"}


def _exception_for_variant(variant: P1BVariant, action_id: str) -> str | None:
    if variant.variant_id == "P1B-BUG-007" and action_id in {
        "run_null_missing_tests",
        "inspect_traceback",
        "run_smoke_tests",
    }:
        try:
            cart.cart_subtotal(None, variant_id=variant.variant_id)
        except Exception as exc:  # noqa: BLE001 - structured benchmark observation
            return type(exc).__name__
    if variant.variant_id == "P1B-BUG-012" and action_id in {
        "run_config_matrix_tests",
        "inspect_traceback",
        "run_boundary_tests",
    }:
        try:
            cfg = config.load_config({"FREE_SHIPPING_THRESHOLD": "9000"}, variant_id=variant.variant_id)
            shipping.free_shipping_eligible(10000, cfg, variant_id=variant.variant_id)
        except Exception as exc:  # noqa: BLE001 - structured benchmark observation
            return type(exc).__name__
    return None


def _synthetic_recent_diff_prior(action_id: str, spec: P1BActionSpec) -> P1BObservation:
    """Keep recent-diff evidence synthetic until Phase C real diff artifacts."""

    return P1BObservation(
        action_id=action_id,
        cost=spec.cost,
        observation_type=spec.observation_type,
        summary=(
            "Synthetic recent-diff prior retained for Phase B; real per-variant "
            "git diff artifacts are deferred to Phase C."
        ),
        cause_scores={cause: 1.2 for cause in spec.strong_causes},
        evidence_source="metadata_synth",
    )


def _score_maps(variant: P1BVariant, action_id: str, directness: float) -> tuple[dict[str, float], dict[str, float], dict[str, float]]:
    cause_scores: dict[str, float] = {}
    location_scores: dict[str, float] = {}
    fix_intent_scores: dict[str, float] = {}
    if not variant.is_buggy:
        return cause_scores, location_scores, fix_intent_scores

    spec = P1B_ACTION_SPECS[action_id]
    if variant.true_cause_category:
        if directness > 0:
            cause_scores[variant.true_cause_category] = 8.0 * directness
        elif variant.true_cause_category in spec.strong_causes:
            cause_scores[variant.true_cause_category] = 1.5

    if variant.target_location:
        if directness > 0:
            location_scores[variant.target_location] = 60.0 * directness
        elif action_id in {"inspect_coverage_spectrum", "inspect_recent_diff", "inspect_spec_clause"}:
            location_scores[variant.target_location] = 2.0
    for distractor in variant.distractor_locations:
        location_scores[distractor] = max(location_scores.get(distractor, 1.0), 2.0 * directness)

    if variant.fix_intent_category:
        if directness > 0:
            fix_intent_scores[variant.fix_intent_category] = 14.0 * directness
        elif variant.true_cause_category in spec.strong_causes:
            fix_intent_scores[variant.fix_intent_category] = 1.4
    return cause_scores, location_scores, fix_intent_scores


def run_action(
    variant: P1BVariant,
    action_id: str,
    *,
    observation_mode: str = "metadata_synth",
    execution_context: P1BExecutionContext | None = None,
) -> P1BObservation:
    """Run one P1b action and return a structured observation.

    ``metadata_synth`` preserves the Phase A baseline that synthesizes evidence
    from variant metadata. ``execution_grounded`` runs checkout test cases and
    constructs observations from actual values, exceptions, and traced functions.
    """

    spec = P1B_ACTION_SPECS[action_id]
    if observation_mode not in P1B_OBSERVATION_MODES:
        raise ValueError(f"Unknown P1b observation mode: {observation_mode}")
    if observation_mode == "execution_grounded":
        if action_id == "inspect_recent_diff":
            return _synthetic_recent_diff_prior(action_id, spec)
        return run_execution_grounded_action(
            variant_id=variant.variant_id,
            action_id=action_id,
            cost=spec.cost,
            observation_type=spec.observation_type,
            context=execution_context,
        )

    if not variant.is_buggy:
        return P1BObservation(
            action_id=action_id,
            cost=spec.cost,
            observation_type="clean_test_pass",
            summary=f"No failure found for clean variant {variant.variant_id}: {variant.recommended_no_bug_evidence}",
            no_bug_evidence=True,
        )

    matches = _action_matches_variant(variant, action_id)
    directness = 1.0 if action_id == variant.primary_discovery_action else 0.65 if matches else 0.0
    exception_type = _exception_for_variant(variant, action_id)
    failure_found = matches and _is_failure_action(action_id)
    bug_detected = failure_found or exception_type is not None
    cause_scores, location_scores, fix_intent_scores = _score_maps(variant, action_id, directness)
    if exception_type is not None:
        cause_scores[variant.true_cause_category or ""] = max(cause_scores.get(variant.true_cause_category or "", 1.0), 8.0)
        if variant.target_location:
            location_scores[variant.target_location] = max(location_scores.get(variant.target_location, 1.0), 60.0)

    if bug_detected:
        summary = (
            f"{action_id} exposed {variant.variant_id}: expected {variant.expected_behavior}; "
            f"observed {variant.actual_behavior}"
        )
    elif matches:
        summary = f"{action_id} produced a useful prior signal for {variant.variant_id}: {variant.observable_signals}"
    else:
        summary = f"{action_id} did not expose {variant.variant_id}; signal is weak for this injected bug."

    return P1BObservation(
        action_id=action_id,
        cost=spec.cost,
        observation_type=spec.observation_type if not exception_type else "exception_trace",
        summary=summary,
        bug_detected=bug_detected,
        failure_found=failure_found,
        no_bug_evidence=not matches and not bug_detected,
        reproduction_input=variant.failing_input_or_sequence if bug_detected else None,
        exception_type=exception_type,
        cause_scores={key: value for key, value in cause_scores.items() if key},
        location_scores=location_scores,
        fix_intent_scores=fix_intent_scores,
    )


def action_specs_to_dict() -> dict[str, dict[str, Any]]:
    return {action_id: spec.__dict__.copy() for action_id, spec in P1B_ACTION_SPECS.items()}
