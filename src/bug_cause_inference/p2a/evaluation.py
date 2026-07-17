"""Frozen P2a-B versioned evaluation and exact descriptive arithmetic.

The public entry point validates the accepted official freeze before any P2a
policy outcome is observed.  Accepted P1d1 rows are immutable reference data;
they are never rerun by this module and never enter combined arithmetic.
"""

from __future__ import annotations

import hashlib
import random
import sys
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from copy import deepcopy
from fractions import Fraction
from typing import Any

from bug_cause_inference.p1b import execution as p1b_execution
from bug_cause_inference.p1b import policies as p1b_policies
from bug_cause_inference.p1b.actions import P1B_ACTION_SPECS
from bug_cause_inference.p1b.dataset import LOCATION_CANDIDATES, load_p1b_variants
from bug_cause_inference.p1b.models import (
    P1B_CAUSE_CATEGORIES,
    P1B_FIX_INTENT_CATEGORIES,
    P1BObservation,
    P1BRunResult,
    P1BSettings,
    P1BStepTrace,
    P1BVariant,
    rank_distribution,
    uniform_distribution,
    update_distribution,
)
from bug_cause_inference.p1b.real_diff import inspect_real_diff_artifact
from bug_cause_inference.p2a.adequacy import (
    ANALYSIS_PHASE,
    BENCHMARK_ID,
    BUGGY_BUCKET_IDS,
    REPORT_SCHEMA_VERSION,
    canonical_digest,
    validate_portable_value,
)
from bug_cause_inference.p2a.candidate_authoring import _candidate_modules
from bug_cause_inference.p2a.candidate_oracles import run_oracle_record
from bug_cause_inference.p2a.candidates import (
    BUGGY_CANDIDATES,
    CANDIDATES,
    CLEAN_CANDIDATES,
    CandidateDefinition,
)
from bug_cause_inference.p2a.compatibility import (
    current_contract_digests,
    run_legacy_exact_compatibility,
    validate_frozen_legacy_contracts,
)
from bug_cause_inference.p2a.execution import isolated_legacy_checkout
from bug_cause_inference.p2a.freeze_realization import (
    ARTIFACT_MANIFEST_PATH,
    EXPECTED_AUTHORING_MANIFEST_DIGEST,
    EXPECTED_CANDIDATE_MANIFEST_DIGEST,
    EXPECTED_COVERAGE_GAP_REGISTRY_DIGEST,
    EXPECTED_LEGACY_ARTIFACT_DIGEST,
    EXPECTED_LEGACY_CATALOG_DIGEST,
    EXPECTED_LEGACY_RUNTIME_DIGEST,
    EXPECTED_TRUSTED_REFERENCE_REGISTRY_DIGEST,
    FORMAL_POLICY_IDS,
    OFFICIAL_FREEZE_BUNDLE_PATH,
    artifact_manifest_digest,
    load_tracked_artifact_manifest,
    load_tracked_official_freeze_bundle,
    repository_path,
    serialized_artifact_manifest,
    serialized_official_freeze_bundle,
)


REPORT_ROLE = "versioned_same_domain_evidence_expansion"
OBSERVATION_MODE = "p2a_patch_grounded_frozen_catalog"
VALID_STATUS = "valid"
INVALID_STATUS = "invalid_inconclusive"
FREEZE_TIMESTAMP = "2026-07-17T12:34:56Z"
OFFICIAL_DRAFT_DIGEST = "d6ebfc173361f9387b22c95d7a5642d3dad8999233e89f12fafa29a0afbabba1"
OFFICIAL_FREEZE_DIGEST = "d335f3f3a4731ee0f4d9b4648e2085eb9c687b7b2a3065d2b08eb2f65370cd9d"
ARTIFACT_MANIFEST_DIGEST = "674c3f56fbd2d4148a3e63367e4bba63ed7de634f5a219ec82a79a1c878a9544"
EXCLUDED_POLICY_IDS = ("random_action", "state_sequence_guard")
BUGGY_IDENTITIES = (
    "accepted_legacy_reference_buggy",
    "p2a_replayed_legacy_buggy",
    "expansion_only_buggy",
    "combined_versioned_buggy",
)
CLEAN_IDENTITIES = (
    "accepted_legacy_reference_clean",
    "p2a_replayed_legacy_clean",
    "expansion_only_clean",
    "combined_versioned_clean",
)
SECONDARY_METRIC_IDS = (
    "cost_to_first_failure",
    "location_top3_loss",
    "cause_top1_loss",
    "fix_intent_top1_loss",
    "wrong_cause_high_confidence_rate",
    "mean_investigation_cost",
)
BUGGY_LOVO_POLICY_METRIC_IDS = (
    "affected_cell_discovery_rate",
    "affected_cell_discovery_loss",
    "worst_bucket_loss",
    "reference_average_loss",
    "average_to_worst_gap",
)
BUGGY_LOVO_PROJECTION_METRIC_IDS = ("restricted_pure_security_loss",)
CLEAN_LOVO_METRIC_IDS = (
    "false_positive_rate",
    "mean_investigation_cost",
    "no_bug_stop_rate",
)
_EXTREMA_FIELDS = (
    "minimum_projected_value",
    "minimum_projected_value_variant_ids",
    "maximum_projected_value",
    "maximum_projected_value_variant_ids",
    "minimum_baseline_delta",
    "minimum_baseline_delta_variant_ids",
    "maximum_baseline_delta",
    "maximum_baseline_delta_variant_ids",
)
_GATE_FIELDS = (
    "status",
    "external_authorization_transition",
    "freeze_timestamp",
    "official_draft_digest",
    "official_freeze_digest",
    "artifact_manifest_digest",
    "contract_digests",
    "candidate_manifest_digest",
    "authoring_manifest_digest",
    "trusted_reference_registry_digest",
    "coverage_gap_registry_digest",
    "dataset_counts",
    "catalog_case_count",
    "legacy_compatibility",
    "accepted_four_file_sha256",
)
SAVED_OUTCOME_SNAPSHOT_DIGEST = "2a1b09b38de6b2e17943726508ebc1f6728290506165cfa263a78dbb57383755"

_EXPECTED_FOUR_FILE_HASHES = {
    "src/bug_cause_inference/p2a/adequacy.py": "bdef79f373a6398fa6756f1b77661b4dbd394d5470ea5ca84b80e0286ea6d400",
    "src/bug_cause_inference/p2a/freeze.py": "ec03b5ed7c7f1e3297d00cbb93680b1d2712656f445b074e7568883cc05eaad1",
    "tests/test_p2a_adequacy.py": "49bf9e9a1d9177bfecc2a0b51ddeab64c2d52c5c31c513e4618fcd6f18b50f6d",
    "tests/test_p2a_freeze.py": "2664bfc1a88141d9f0bef1933d318367bee7abc9917195c168e1353f965399e9",
}
_EXPECTED_CONTRACT_DIGESTS = {
    "adapter": "a3b5e94376d5df1baf0f329b780e71a0e1c0af7fe3bd0f3fabb6e46f2581f2de",
    "catalog": "07b41b4d61a8b63250f62bb01e49ecca38ee2ab9f8124ba9d6c03c0f87fb84bb",
    "policy": "02a25101cd10cacc6ddb2717cedf1a29c08643e44609be9909735263ae216def",
    "settings": "b11fe4cff40728a9225e154de36a4d56420f6d387ae6acec8d2b87009d30b954",
    "metric": "5ba8478b9c1a98d8fa56737188197f5e694c7a3e4b4b5c404c821e28d7e5e175",
    "serializer": "e6968cf3ae1d43889addad7d091ee89aa4834d854e9ca68584c5d78cb6b28f5d",
}
_FIXED_SETTINGS = {
    "budget_limit": 12,
    "max_steps": 6,
    "failure_cost": 14,
    "bug_presence_threshold": 0.75,
    "no_bug_probability_threshold": 0.8,
    "location_top1_threshold": 0.5,
    "cause_top1_threshold": 0.6,
    "min_expected_utility_per_cost": 0.03,
    "rng_seed": 0,
}
_STOP_PRECEDENCE = (
    "no_bug_probability_threshold",
    "bug_confidence_threshold",
    "budget_limit",
    "max_steps",
    "low_expected_utility",
)
_LEGACY_BUCKET_SUPPORT = {
    bucket: tuple(f"P1B-BUG-{index:03d}" for index in range(start, start + 4))
    for bucket, start in zip(BUGGY_BUCKET_IDS, (1, 5, 9, 13, 17), strict=True)
}
_LEGACY_CLEAN_IDS = tuple(f"P1B-CLEAN-{index:03d}" for index in range(21, 26))
_ACCEPTED_P1D1_ROWS = {
    policy: row
    for policy, row in zip(
        FORMAL_POLICY_IDS,
        (
            (0, 3, 4, 4, 2),
            (0, 3, 4, 4, 2),
            (0, 3, 4, 4, 2),
            (0, 3, 4, 4, 2),
            (3, 0, 3, 4, 2),
            (3, 0, 3, 4, 2),
        ),
        strict=True,
    )
}
_ACCEPTED_P1D1_CLEAN_COSTS = dict(
    zip(FORMAL_POLICY_IDS, (3, 3, 3, 5, 2, 2), strict=True)
)
_ACCEPTED_DISCOVERED_IDS = {
    policy: {
        "boundary_precision": list(_LEGACY_BUCKET_SUPPORT["boundary_precision"])
        if policy in FORMAL_POLICY_IDS[:4]
        else ["P1B-BUG-001"],
        "missing_optional_input": ["P1B-BUG-005"]
        if policy in FORMAL_POLICY_IDS[:4]
        else list(_LEGACY_BUCKET_SUPPORT["missing_optional_input"]),
        "config_normalization": []
        if policy in FORMAL_POLICY_IDS[:4]
        else ["P1B-BUG-012"],
        "state_sequence": [],
        "spec_semantics": ["P1B-BUG-019", "P1B-BUG-020"],
    }
    for policy in FORMAL_POLICY_IDS
}
_P1D1_IDENTITY = {
    "schema_version": "p1d1_finite_game_report.v1",
    "analysis_phase": "p1d1_finite_game_report",
    "game_id": "p1d0_g0_default_execution_grounded_v1",
    "benchmark_id": "p1b_injected_bug_benchmark",
    "json_sha256": "d1e86525240485b615f61b6261ea239a57b7a7148bdee4a5857452cc84169bac",
    "markdown_sha256": "9611e6cd8d3086a0b498a89278695f75c07ccdc9f840b6b3d00b14b0234f1dad",
}
_CAUSE_TAG_BY_ACTION = {
    "run_boundary_tests": "boundary_failure",
    "run_null_missing_tests": "null_exception",
    "run_config_matrix_tests": "config_matrix_failure",
    "run_state_sequence_tests": "state_invariant_failure",
    "inspect_spec_clause": "spec_rule_failure",
}
_LOCATION_SET = set(LOCATION_CANDIDATES)
_OUTCOME_FIELDS = (
    "variant_id",
    "cohort_id",
    "policy_id",
    "is_buggy",
    "taxonomy_id",
    "clean_family_id",
    "discovered_within_budget",
    "first_failure_cost_penalized",
    "location_top3_hit",
    "cause_top1_hit",
    "fix_intent_top1_hit",
    "wrong_cause_high_confidence",
    "investigation_cost",
    "false_positive",
    "no_bug_stop",
)


class P2AEvaluationError(ValueError):
    """Raised when a frozen evaluation input or complete outcome set is invalid."""


def _rate(numerator: int, denominator: int) -> dict[str, Any]:
    if type(numerator) is not int or type(denominator) is not int or denominator <= 0:
        raise P2AEvaluationError("exact rate requires integer numerator and positive denominator")
    if numerator < 0 or numerator > denominator:
        raise P2AEvaluationError("exact rate numerator is outside its denominator")
    fraction = Fraction(numerator, denominator)
    return {
        "numerator": fraction.numerator,
        "denominator": fraction.denominator,
        "decimal": format(float(fraction), ".12g"),
    }


def _fraction_value(value: Fraction) -> dict[str, Any]:
    return {
        "numerator": value.numerator,
        "denominator": value.denominator,
        "decimal": format(float(value), ".12g"),
    }


def _fraction(value: Mapping[str, Any]) -> Fraction:
    return Fraction(value["numerator"], value["denominator"])


def _sha256(relative_path: str) -> str:
    return hashlib.sha256(repository_path(relative_path).read_bytes()).hexdigest()


def _canonical_gate_identity() -> dict[str, Any]:
    return {
        "status": "pre_outcome_gate_valid",
        "external_authorization_transition": {
            "source": "prompt_124_after_review_123_acceptance",
            "official_frozen_dataset_accepted": True,
            "p2a_b_implementation_prompt_approved": True,
            "bundle_provenance_remains_evaluation_authorized_false": True,
            "repository_authorization_artifact_required": False,
        },
        "freeze_timestamp": FREEZE_TIMESTAMP,
        "official_draft_digest": OFFICIAL_DRAFT_DIGEST,
        "official_freeze_digest": OFFICIAL_FREEZE_DIGEST,
        "artifact_manifest_digest": ARTIFACT_MANIFEST_DIGEST,
        "contract_digests": deepcopy(_EXPECTED_CONTRACT_DIGESTS),
        "candidate_manifest_digest": EXPECTED_CANDIDATE_MANIFEST_DIGEST,
        "authoring_manifest_digest": EXPECTED_AUTHORING_MANIFEST_DIGEST,
        "trusted_reference_registry_digest": EXPECTED_TRUSTED_REFERENCE_REGISTRY_DIGEST,
        "coverage_gap_registry_digest": EXPECTED_COVERAGE_GAP_REGISTRY_DIGEST,
        "dataset_counts": {"total": 15, "buggy": 10, "clean": 5},
        "catalog_case_count": 24,
        "legacy_compatibility": {
            "status": "valid",
            "expected_pair_count": 150,
            "observed_pair_count": 150,
            "matched_pair_count": 150,
            "mismatch_count": 0,
            "runtime_digest": EXPECTED_LEGACY_RUNTIME_DIGEST,
            "catalog_digest": EXPECTED_LEGACY_CATALOG_DIGEST,
            "artifact_digest": EXPECTED_LEGACY_ARTIFACT_DIGEST,
        },
        "accepted_four_file_sha256": deepcopy(_EXPECTED_FOUR_FILE_HASHES),
    }


def _validate_exact_typed_identity(value: Any, expected: Any, path: str) -> None:
    if type(value) is not type(expected):
        raise P2AEvaluationError(f"{path}: exact type drifted")
    if type(expected) is dict:
        if tuple(value) != tuple(expected):
            raise P2AEvaluationError(f"{path}: missing, unknown, or reordered fields")
        for key in expected:
            _validate_exact_typed_identity(value[key], expected[key], f"{path}.{key}")
    elif type(expected) is list:
        if len(value) != len(expected):
            raise P2AEvaluationError(f"{path}: exact list length drifted")
        for index, (observed, canonical) in enumerate(zip(value, expected, strict=True)):
            _validate_exact_typed_identity(observed, canonical, f"{path}[{index}]")
    elif value != expected:
        raise P2AEvaluationError(f"{path}: immutable identity drifted")


def validate_canonical_gate_identity(value: Any) -> dict[str, Any]:
    """Validate the pure exact gate schema, ordering, types, and immutable values."""

    expected = _canonical_gate_identity()
    _validate_exact_typed_identity(value, expected, "gate")
    return value


def validate_pre_outcome_gate(*, run_compatibility: bool = True) -> dict[str, Any]:
    """Validate immutable freeze and current accepted contracts before outcomes."""

    observed_hashes = {path: _sha256(path) for path in _EXPECTED_FOUR_FILE_HASHES}
    if observed_hashes != _EXPECTED_FOUR_FILE_HASHES:
        raise P2AEvaluationError("accepted adequacy/freeze four-file identity drifted")
    artifact = load_tracked_artifact_manifest()
    bundle = load_tracked_official_freeze_bundle()
    if artifact_manifest_digest(artifact) != ARTIFACT_MANIFEST_DIGEST:
        raise P2AEvaluationError("official artifact manifest digest drifted")
    if repository_path(ARTIFACT_MANIFEST_PATH).read_text(encoding="utf-8") != serialized_artifact_manifest():
        raise P2AEvaluationError("official artifact manifest byte agreement failed")
    if repository_path(OFFICIAL_FREEZE_BUNDLE_PATH).read_text(encoding="utf-8") != serialized_official_freeze_bundle(FREEZE_TIMESTAMP):
        raise P2AEvaluationError("official freeze bundle byte agreement failed")
    payload = bundle["freeze_payload"]
    if bundle["official_freeze_digest"] != OFFICIAL_FREEZE_DIGEST:
        raise P2AEvaluationError("official freeze digest drifted")
    draft_validation = payload["draft_validation"]
    if draft_validation != {
        "status": "draft_valid",
        "draft_digest": OFFICIAL_DRAFT_DIGEST,
        "candidate_manifest_digest": EXPECTED_CANDIDATE_MANIFEST_DIGEST,
        "variant_count": 15,
        "buggy_count": 10,
        "clean_count": 5,
    }:
        raise P2AEvaluationError("official draft validation result drifted")
    if payload["freeze_timestamp"] != FREEZE_TIMESTAMP:
        raise P2AEvaluationError("official freeze timestamp drifted")
    provenance = payload["provenance"]
    if provenance != {
        "candidate_policy_outcome_observed": False,
        "evaluation_authorized": False,
    }:
        raise P2AEvaluationError("immutable freeze provenance drifted")
    contracts = {
        name: item["identity"]["digest"]
        for name, item in payload["outcome_free_contracts"].items()
    }
    if contracts != _EXPECTED_CONTRACT_DIGESTS:
        raise P2AEvaluationError("outcome-free contract identity drifted")
    inputs = payload["accepted_input_identities"]
    if inputs["candidate_manifest_digest"] != EXPECTED_CANDIDATE_MANIFEST_DIGEST:
        raise P2AEvaluationError("candidate manifest identity drifted")
    if inputs["trusted_reference_registry_digest"] != EXPECTED_TRUSTED_REFERENCE_REGISTRY_DIGEST:
        raise P2AEvaluationError("trusted registry identity drifted")
    if inputs["coverage_gap_registry_digest"] != EXPECTED_COVERAGE_GAP_REGISTRY_DIGEST:
        raise P2AEvaluationError("coverage registry identity drifted")
    current = current_contract_digests()
    validate_frozen_legacy_contracts(current)
    compatibility = payload["accepted_input_identities"]["legacy_compatibility"]
    expected_compatibility = {
        "status": "valid",
        "expected_pair_count": 150,
        "observed_pair_count": 150,
        "matched_pair_count": 150,
        "mismatch_count": 0,
        "runtime_digest": EXPECTED_LEGACY_RUNTIME_DIGEST,
        "catalog_digest": EXPECTED_LEGACY_CATALOG_DIGEST,
        "artifact_digest": EXPECTED_LEGACY_ARTIFACT_DIGEST,
    }
    if compatibility != expected_compatibility:
        raise P2AEvaluationError("accepted legacy compatibility identity drifted")
    if run_compatibility:
        report = run_legacy_exact_compatibility()
        if report.status != "valid" or report.matched_pair_count != 150:
            raise P2AEvaluationError("current legacy compatibility gate failed")
    gate = {
        "status": "pre_outcome_gate_valid",
        "external_authorization_transition": {
            "source": "prompt_124_after_review_123_acceptance",
            "official_frozen_dataset_accepted": True,
            "p2a_b_implementation_prompt_approved": True,
            "bundle_provenance_remains_evaluation_authorized_false": True,
            "repository_authorization_artifact_required": False,
        },
        "freeze_timestamp": FREEZE_TIMESTAMP,
        "official_draft_digest": OFFICIAL_DRAFT_DIGEST,
        "official_freeze_digest": OFFICIAL_FREEZE_DIGEST,
        "artifact_manifest_digest": ARTIFACT_MANIFEST_DIGEST,
        "contract_digests": contracts,
        "candidate_manifest_digest": EXPECTED_CANDIDATE_MANIFEST_DIGEST,
        "authoring_manifest_digest": EXPECTED_AUTHORING_MANIFEST_DIGEST,
        "trusted_reference_registry_digest": EXPECTED_TRUSTED_REFERENCE_REGISTRY_DIGEST,
        "coverage_gap_registry_digest": EXPECTED_COVERAGE_GAP_REGISTRY_DIGEST,
        "dataset_counts": {"total": 15, "buggy": 10, "clean": 5},
        "catalog_case_count": len(payload["outcome_free_contracts"]["catalog"]["payload"]["cases"]),
        "legacy_compatibility": compatibility,
        "accepted_four_file_sha256": observed_hashes,
    }
    validate_canonical_gate_identity(gate)
    return gate


def _exact_fields(value: Any, fields: tuple[str, ...], path: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise P2AEvaluationError(f"{path}: expected object")
    if tuple(value) != fields:
        raise P2AEvaluationError(f"{path}: missing, unknown, or reordered fields")
    return value


def _candidate_variant(candidate: CandidateDefinition) -> P1BVariant:
    metadata = candidate.metadata
    if candidate.cohort_kind == "buggy":
        target = metadata["target_functions"][0]
        module, function = target.split(".", 1)
        return P1BVariant(
            variant_id=candidate.variant_id,
            is_buggy=True,
            true_cause_category=metadata["cause_category"],
            target_module=module,
            target_function=function,
            expected_behavior=metadata["expected_behavior"],
            actual_behavior=metadata["actual_behavior"],
            fix_intent_category=metadata["fix_intent_category"],
        )
    return P1BVariant(
        variant_id=candidate.variant_id,
        is_buggy=False,
        expected_clean_behavior=metadata["expected_clean_behavior"],
        recommended_no_bug_evidence=metadata["recommended_no_bug_evidence"],
    )


@contextmanager
def _module_trace(modules: Mapping[str, Any]) -> Iterator[list[str]]:
    module_names = {module.__name__: name for name, module in modules.items()}
    calls: list[str] = []
    previous = sys.gettrace()

    def tracer(frame: Any, event: str, arg: Any) -> Any:
        if event == "call" and frame.f_globals.get("__name__") in module_names:
            candidate = f"{module_names[frame.f_globals['__name__']]}.{frame.f_code.co_name}"
            if candidate in _LOCATION_SET:
                calls.append(candidate)
        return tracer

    sys.settrace(tracer)
    try:
        yield calls
    finally:
        sys.settrace(previous)


def _catalog_cases(bundle: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    catalog = bundle["freeze_payload"]["outcome_free_contracts"]["catalog"]["payload"]
    if len(catalog["cases"]) != 24:
        raise P2AEvaluationError("frozen P2a catalog must contain exactly 24 cases")
    by_action: dict[str, list[dict[str, Any]]] = {action: [] for action in P1B_ACTION_SPECS}
    for case in catalog["cases"]:
        by_action[case["action_id"]].append(case)
    return by_action


def _run_case(case: dict[str, Any], modules: Mapping[str, Any]) -> dict[str, Any]:
    with _module_trace(modules) as calls:
        result = run_oracle_record(case["oracle_definition"], modules)
    tag = _CAUSE_TAG_BY_ACTION.get(case["action_id"])
    return {
        "test_id": f"{case['candidate_id']}::{case['oracle_id']}",
        "group": case["action_id"],
        "passed": result.passed,
        "expected": result.expected,
        "actual": result.actual,
        "exception_type": None,
        "reproduction_input": case["oracle_id"],
        "executed_functions": sorted(set(calls)),
        "stack_functions": [],
        "evidence_tags": [tag] if tag else [],
        "fix_intent_hints": [],
    }


def _recent_diff_observation(
    variant_id: str,
    *,
    candidate_artifact: dict[str, Any] | None,
) -> P1BObservation:
    spec = P1B_ACTION_SPECS["inspect_recent_diff"]
    if candidate_artifact is None:
        artifact = inspect_real_diff_artifact(variant_id)
        changed_files = list(artifact["changed_files"])
        changed_functions = list(artifact["changed_functions"])
    else:
        changed_files = list(candidate_artifact["patch_identity"]["changed_files"])
        changed_functions = list(candidate_artifact["patch_identity"]["changed_functions"])
    return P1BObservation(
        action_id="inspect_recent_diff",
        cost=spec.cost,
        observation_type=spec.observation_type,
        summary="inspect_recent_diff observed the frozen repository-relative patch identity.",
        no_bug_evidence=False,
        location_scores=p1b_execution._location_scores_from_changed_functions(changed_functions),
        evidence_source="p2a_frozen_patch_identity",
        changed_files=changed_files,
        changed_functions=changed_functions,
    )


def _run_frozen_action(
    *,
    variant_id: str,
    action_id: str,
    context: p1b_execution.P1BExecutionContext,
    modules: Mapping[str, Any],
    cases_by_action: Mapping[str, list[dict[str, Any]]],
    candidate_artifact: dict[str, Any] | None,
) -> P1BObservation:
    spec = P1B_ACTION_SPECS[action_id]
    if action_id == "inspect_recent_diff":
        return _recent_diff_observation(variant_id, candidate_artifact=candidate_artifact)
    if action_id == "inspect_coverage_spectrum":
        return p1b_execution._inspect_coverage_spectrum(
            action_id=action_id,
            cost=spec.cost,
            observation_type=spec.observation_type,
            context=context,
        )
    if action_id == "inspect_traceback":
        failures = context.failed_results()
        return p1b_execution._observation_from_results(
            action_id=action_id,
            cost=spec.cost,
            observation_type=spec.observation_type,
            results=failures,
            recordable=False,
        )
    results = context.record(
        action_id,
        [_run_case(case, modules) for case in cases_by_action[action_id]],
    )
    return p1b_execution._observation_from_results(
        action_id=action_id,
        cost=spec.cost,
        observation_type=spec.observation_type,
        results=results,
    )


def _run_policy(
    variant: P1BVariant,
    policy: str,
    modules: Mapping[str, Any],
    cases_by_action: Mapping[str, list[dict[str, Any]]],
    candidate_artifact: dict[str, Any] | None,
) -> P1BRunResult:
    if policy not in FORMAL_POLICY_IDS:
        raise P2AEvaluationError("policy is outside the frozen formal six")
    settings = P1BSettings(**_FIXED_SETTINGS)
    state = p1b_policies._State(
        bug_presence=0.5,
        cause_posterior=uniform_distribution(P1B_CAUSE_CATEGORIES),
        location_posterior=uniform_distribution(LOCATION_CANDIDATES),
        fix_intent_posterior=uniform_distribution(P1B_FIX_INTENT_CATEGORIES),
        executed_actions=[],
        cumulative_cost=0,
        current_step=0,
        bug_detected=False,
        execution_context=p1b_execution.P1BExecutionContext(),
    )
    trace: list[P1BStepTrace] = []
    first_failure_cost: int | None = None
    reproduction_input: str | None = None
    rng = random.Random(p1b_policies._stable_seed(variant.variant_id, settings.rng_seed))
    while True:
        remaining = settings.budget_limit - state.cumulative_cost
        scores = p1b_policies.score_actions(state, remaining)
        best = scores[0]["expected_utility_per_cost"] if scores else None
        stop_reason = p1b_policies._check_stop(state, settings, best)
        if stop_reason is not None:
            break
        action_id = p1b_policies.choose_action(policy, state, remaining, rng)
        if action_id is None:
            stop_reason = "no_available_actions"
            break
        prior_bug = state.bug_presence
        prior_cause = dict(state.cause_posterior)
        prior_location = dict(state.location_posterior)
        prior_fix = dict(state.fix_intent_posterior)
        observation = _run_frozen_action(
            variant_id=variant.variant_id,
            action_id=action_id,
            context=state.execution_context,
            modules=modules,
            cases_by_action=cases_by_action,
            candidate_artifact=candidate_artifact,
        )
        state.executed_actions.append(action_id)
        state.cumulative_cost += observation.cost
        state.current_step += 1
        state.bug_detected = state.bug_detected or observation.bug_detected
        state.bug_presence = p1b_policies._update_bug_presence(
            state.bug_presence, observation.bug_detected, observation.no_bug_evidence
        )
        state.cause_posterior = update_distribution(state.cause_posterior, observation.cause_scores)
        state.location_posterior = update_distribution(state.location_posterior, observation.location_scores)
        state.fix_intent_posterior = update_distribution(state.fix_intent_posterior, observation.fix_intent_scores)
        if observation.reproduction_input and reproduction_input is None:
            reproduction_input = observation.reproduction_input
        if observation.failure_found and first_failure_cost is None:
            first_failure_cost = state.cumulative_cost
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
                action_scores=scores,
            )
        )
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
        cost_to_true_cause_top1=None,
    )


def _rank_position(distribution: Mapping[str, float], identity: str | None) -> int | None:
    if identity is None:
        return None
    ranked = [key for key, _ in rank_distribution(dict(distribution))]
    return ranked.index(identity) + 1 if identity in ranked else None


def _outcome(
    variant: P1BVariant,
    result: P1BRunResult,
    *,
    cohort_id: str,
    taxonomy_id: str,
    clean_family_id: str | None,
) -> dict[str, Any]:
    settings = P1BSettings(**_FIXED_SETTINGS)
    if variant.is_buggy:
        location_rank = _rank_position(result.location_posterior, variant.target_location)
        cause_top = rank_distribution(result.cause_posterior)[0]
        return dict(
            zip(
                _OUTCOME_FIELDS,
                (
                    variant.variant_id,
                    cohort_id,
                    result.policy,
                    True,
                    taxonomy_id,
                    None,
                    result.bug_detected and result.cumulative_cost <= settings.budget_limit,
                    result.first_failure_cost if result.first_failure_cost is not None else 14,
                    location_rank is not None and location_rank <= 3,
                    cause_top[0] == variant.true_cause_category,
                    rank_distribution(result.fix_intent_posterior)[0][0] == variant.fix_intent_category,
                    cause_top[1] >= settings.cause_top1_threshold and cause_top[0] != variant.true_cause_category,
                    result.cumulative_cost,
                    False,
                    False,
                ),
                strict=True,
            )
        )
    return dict(
        zip(
            _OUTCOME_FIELDS,
            (
                variant.variant_id,
                cohort_id,
                result.policy,
                False,
                taxonomy_id,
                clean_family_id,
                False,
                14,
                False,
                False,
                False,
                False,
                result.cumulative_cost,
                result.stop_reason == "bug_confidence_threshold" or result.bug_presence_posterior >= 0.75,
                result.stop_reason == "no_bug_probability_threshold",
            ),
            strict=True,
        )
    )


def _execute_all_outcomes(
    bundle: dict[str, Any], event_log: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    cases = _catalog_cases(bundle)
    artifact = load_tracked_artifact_manifest()
    candidate_artifact = {item["variant_id"]: item for item in artifact["candidates"]}
    legacy_outcomes: list[dict[str, Any]] = []
    bucket_by_legacy = {
        variant_id: bucket
        for bucket, variant_ids in _LEGACY_BUCKET_SUPPORT.items()
        for variant_id in variant_ids
    }
    variants = load_p1b_variants()
    for variant in variants:
        taxonomy = bucket_by_legacy.get(variant.variant_id, "clean_false_positive")
        with isolated_legacy_checkout(variant.variant_id) as (modules, _):
            for policy in FORMAL_POLICY_IDS:
                result = _run_policy(variant, policy, modules, cases, None)
                legacy_outcomes.append(
                    _outcome(
                        variant,
                        result,
                        cohort_id="p2a_replayed_legacy",
                        taxonomy_id=taxonomy,
                        clean_family_id=None,
                    )
                )
    event_log.append(
        {
            "event": "actual_candidate_outcome_execution_started",
            "first_candidate_id": CANDIDATES[0].variant_id,
            "first_policy_id": FORMAL_POLICY_IDS[0],
            "pre_outcome_gate_complete": True,
        }
    )
    expansion_outcomes: list[dict[str, Any]] = []
    for candidate in CANDIDATES:
        variant = _candidate_variant(candidate)
        metadata = candidate.metadata
        taxonomy = metadata.get("primary_bucket", "clean_false_positive")
        family = metadata.get("clean_stress_family_id")
        with _candidate_modules(candidate) as modules:
            for policy in FORMAL_POLICY_IDS:
                result = _run_policy(
                    variant,
                    policy,
                    modules,
                    cases,
                    candidate_artifact[candidate.variant_id],
                )
                expansion_outcomes.append(
                    _outcome(
                        variant,
                        result,
                        cohort_id="expansion_only",
                        taxonomy_id=taxonomy,
                        clean_family_id=family,
                    )
                )
    event_log.append(
        {
            "event": "all_frozen_policy_outcomes_completed",
            "legacy_run_count": len(legacy_outcomes),
            "expansion_run_count": len(expansion_outcomes),
            "contract_changed_after_outcome": False,
        }
    )
    return legacy_outcomes, expansion_outcomes


def _validate_outcomes(
    outcomes: Any,
    *,
    expected_variants: list[tuple[str, bool, str, str | None]],
    cohort_id: str,
) -> list[dict[str, Any]]:
    if type(outcomes) is not list:
        raise P2AEvaluationError("outcomes must be a complete ordered list")
    expected_pairs = [
        (variant_id, policy)
        for variant_id, _, _, _ in expected_variants
        for policy in FORMAL_POLICY_IDS
    ]
    if len(outcomes) != len(expected_pairs):
        raise P2AEvaluationError("outcome set is incomplete")
    observed_pairs: list[tuple[str, str]] = []
    expected_by_id = {item[0]: item for item in expected_variants}
    validated: list[dict[str, Any]] = []
    for index, outcome in enumerate(outcomes):
        row = _exact_fields(outcome, _OUTCOME_FIELDS, f"outcomes[{index}]")
        validate_portable_value(row, f"outcomes[{index}]")
        variant_id, policy_id = row["variant_id"], row["policy_id"]
        if (variant_id, policy_id) != expected_pairs[index]:
            raise P2AEvaluationError("outcome identity/order differs from frozen product")
        expected_id, is_buggy, taxonomy, family = expected_by_id[variant_id]
        if row["cohort_id"] != cohort_id or row["variant_id"] != expected_id:
            raise P2AEvaluationError("outcome cohort or variant identity mismatch")
        if row["is_buggy"] is not is_buggy or row["taxonomy_id"] != taxonomy:
            raise P2AEvaluationError("outcome taxonomy identity mismatch")
        if row["clean_family_id"] != family:
            raise P2AEvaluationError("outcome clean family identity mismatch")
        boolean_fields = (
            "discovered_within_budget",
            "location_top3_hit",
            "cause_top1_hit",
            "fix_intent_top1_hit",
            "wrong_cause_high_confidence",
            "false_positive",
            "no_bug_stop",
        )
        if any(type(row[field]) is not bool for field in boolean_fields):
            raise P2AEvaluationError("outcome boolean field is not exact bool")
        if type(row["first_failure_cost_penalized"]) is not int or not 0 <= row["first_failure_cost_penalized"] <= 14:
            raise P2AEvaluationError("first-failure cost is invalid")
        if type(row["investigation_cost"]) is not int or not 0 <= row["investigation_cost"] <= 12:
            raise P2AEvaluationError("investigation cost is invalid")
        observed_pairs.append((variant_id, policy_id))
        validated.append(deepcopy(row))
    if observed_pairs != expected_pairs:
        raise P2AEvaluationError("outcome pair coverage is not exact")
    return validated


def _buggy_support(outcomes: list[dict[str, Any]]) -> dict[str, list[str]]:
    support: dict[str, list[str]] = {}
    for bucket in BUGGY_BUCKET_IDS:
        support[bucket] = [
            row["variant_id"]
            for row in outcomes
            if row["policy_id"] == FORMAL_POLICY_IDS[0]
            and row["is_buggy"]
            and row["taxonomy_id"] == bucket
        ]
        if not support[bucket]:
            raise P2AEvaluationError("buggy cohort has an empty bucket")
    return support


def _solution(cells_by_policy: Mapping[str, Mapping[str, dict[str, Any]]]) -> dict[str, Any]:
    rows: dict[str, Any] = {}
    worsts: dict[str, Fraction] = {}
    for policy in FORMAL_POLICY_IDS:
        losses = {bucket: _fraction(cells_by_policy[policy][bucket]["discovery_loss"]) for bucket in BUGGY_BUCKET_IDS}
        worst = max(losses.values())
        average = sum(losses.values(), Fraction()) / 5
        worsts[policy] = worst
        rows[policy] = {
            "worst_bucket_loss": _fraction_value(worst),
            "worst_bucket_ids": [bucket for bucket in BUGGY_BUCKET_IDS if losses[bucket] == worst],
            "reference_average_loss": _fraction_value(average),
            "average_to_worst_gap": _fraction_value(worst - average),
        }
    security = min(worsts.values())
    return {
        "qualification": "restricted-pure empirical result among the fixed six deterministic policies",
        "by_policy": rows,
        "restricted_pure_security_loss": _fraction_value(security),
        "restricted_pure_security_policies": [policy for policy in FORMAL_POLICY_IDS if worsts[policy] == security],
        "tie_rule": "exact rational arithmetic followed by declared stable order",
    }


def _buggy_bucket_cells(
    outcomes: list[dict[str, Any]],
    bucket: str,
    support_variant_ids: list[str],
) -> dict[str, dict[str, Any]]:
    """Compute exactly one buggy bucket cell for every formal policy."""

    cells: dict[str, dict[str, Any]] = {}
    for policy in FORMAL_POLICY_IDS:
        rows = [
            row
            for row in outcomes
            if row["policy_id"] == policy and row["is_buggy"] and row["taxonomy_id"] == bucket
        ]
        if [row["variant_id"] for row in rows] != support_variant_ids:
            raise P2AEvaluationError("buggy cell support/order is incomplete")
        discovered = [row["variant_id"] for row in rows if row["discovered_within_budget"]]
        cells[policy] = {
            "policy_id": policy,
            "bucket_id": bucket,
            "support_variant_ids": deepcopy(support_variant_ids),
            "discovered_variant_ids": discovered,
            "missed_variant_ids": [
                variant_id for variant_id in support_variant_ids if variant_id not in discovered
            ],
            "discovery_rate": _rate(len(discovered), len(rows)),
            "discovery_loss": _rate(len(rows) - len(discovered), len(rows)),
        }
    return cells


def _buggy_result(
    identity: str,
    outcomes: list[dict[str, Any]],
    *,
    report_role: str,
    arithmetic_sources: list[str],
) -> dict[str, Any]:
    support = _buggy_support(outcomes)
    cells: dict[str, Any] = {}
    bucket_cells = {
        bucket: _buggy_bucket_cells(outcomes, bucket, support[bucket])
        for bucket in BUGGY_BUCKET_IDS
    }
    for policy in FORMAL_POLICY_IDS:
        cells[policy] = {
            bucket: bucket_cells[bucket][policy]
            for bucket in BUGGY_BUCKET_IDS
        }
    result = {
        "identity": identity,
        "report_role": report_role,
        "arithmetic_sources": arithmetic_sources,
        "accepted_legacy_reference_used_as_arithmetic_input": False,
        "support_by_bucket": support,
        "reference_distribution": {
            "kind": "uniform_over_buckets_then_uniform_within_bucket",
            "bucket_weights": {bucket: _rate(1, 5) for bucket in BUGGY_BUCKET_IDS},
            "within_bucket_weights": {
                bucket: {variant_id: _rate(1, len(ids)) for variant_id in ids}
                for bucket, ids in support.items()
            },
            "variant_pooled_primary_weighting": False,
        },
        "cells_by_policy": cells,
        "restricted_pure_result": _solution(cells),
        "per_variant_outcomes": deepcopy(outcomes),
    }
    return result


def _accepted_buggy_reference() -> dict[str, Any]:
    outcomes: list[dict[str, Any]] = []
    cells: dict[str, Any] = {}
    for policy in FORMAL_POLICY_IDS:
        policy_cells: dict[str, Any] = {}
        for bucket, missed in zip(BUGGY_BUCKET_IDS, _ACCEPTED_P1D1_ROWS[policy], strict=True):
            support = list(_LEGACY_BUCKET_SUPPORT[bucket])
            discovered = list(_ACCEPTED_DISCOVERED_IDS[policy][bucket])
            discovered_count = len(discovered)
            if discovered_count != 4 - missed:
                raise P2AEvaluationError("accepted P1d1 row and diagnostic partition disagree")
            policy_cells[bucket] = {
                "policy_id": policy,
                "bucket_id": bucket,
                "support_variant_ids": support,
                "discovered_variant_ids": discovered,
                "missed_variant_ids": [variant_id for variant_id in support if variant_id not in discovered],
                "discovery_rate": _rate(discovered_count, 4),
                "discovery_loss": _rate(missed, 4),
            }
        cells[policy] = policy_cells
    return {
        "identity": BUGGY_IDENTITIES[0],
        "report_role": "immutable_accepted_reference_context",
        "arithmetic_sources": ["accepted_p1d1_public_contract"],
        "accepted_reference_identity": deepcopy(_P1D1_IDENTITY),
        "accepted_legacy_reference_used_as_arithmetic_input": False,
        "support_by_bucket": {bucket: list(ids) for bucket, ids in _LEGACY_BUCKET_SUPPORT.items()},
        "reference_distribution": {
            "kind": "uniform_over_buckets_then_uniform_within_bucket",
            "bucket_weights": {bucket: _rate(1, 5) for bucket in BUGGY_BUCKET_IDS},
            "within_bucket_weights": {
                bucket: {variant_id: _rate(1, 4) for variant_id in ids}
                for bucket, ids in _LEGACY_BUCKET_SUPPORT.items()
            },
            "variant_pooled_primary_weighting": False,
        },
        "cells_by_policy": cells,
        "restricted_pure_result": _solution(cells),
        "per_variant_outcomes": outcomes,
    }


def _clean_result(
    identity: str,
    outcomes: list[dict[str, Any]],
    *,
    report_role: str,
    arithmetic_sources: list[str],
) -> dict[str, Any]:
    rows: dict[str, Any] = {}
    support = [
        row["variant_id"]
        for row in outcomes
        if row["policy_id"] == FORMAL_POLICY_IDS[0] and not row["is_buggy"]
    ]
    if not support:
        raise P2AEvaluationError("clean cohort is empty")
    for policy in FORMAL_POLICY_IDS:
        policy_rows = [row for row in outcomes if row["policy_id"] == policy and not row["is_buggy"]]
        if [row["variant_id"] for row in policy_rows] != support:
            raise P2AEvaluationError("clean support/order is incomplete")
        fp_ids = [row["variant_id"] for row in policy_rows if row["false_positive"]]
        no_bug = sum(row["no_bug_stop"] for row in policy_rows)
        total_cost = sum(row["investigation_cost"] for row in policy_rows)
        rows[policy] = {
            "support_variant_ids": support,
            "false_positive_ids": fp_ids,
            "false_positive_rate": _rate(len(fp_ids), len(policy_rows)),
            "mean_investigation_cost": _fraction_value(Fraction(total_cost, len(policy_rows))),
            "no_bug_stop_rate": _rate(no_bug, len(policy_rows)),
        }
    return {
        "identity": identity,
        "report_role": report_role,
        "formal_buggy_game_membership": "excluded",
        "arithmetic_sources": arithmetic_sources,
        "accepted_legacy_reference_used_as_arithmetic_input": False,
        "support_variant_ids": support,
        "by_policy": rows,
        "per_variant_outcomes": deepcopy(outcomes),
    }


def _accepted_clean_reference() -> dict[str, Any]:
    rows = {
        policy: {
            "support_variant_ids": list(_LEGACY_CLEAN_IDS),
            "false_positive_ids": [],
            "false_positive_rate": _rate(0, 5),
            "mean_investigation_cost": _fraction_value(Fraction(_ACCEPTED_P1D1_CLEAN_COSTS[policy], 1)),
            "no_bug_stop_rate": _rate(5, 5),
        }
        for policy in FORMAL_POLICY_IDS
    }
    return {
        "identity": CLEAN_IDENTITIES[0],
        "report_role": "immutable_accepted_reference_context",
        "formal_buggy_game_membership": "excluded",
        "arithmetic_sources": ["accepted_p1d1_public_contract"],
        "accepted_reference_identity": deepcopy(_P1D1_IDENTITY),
        "accepted_legacy_reference_used_as_arithmetic_input": False,
        "support_variant_ids": list(_LEGACY_CLEAN_IDS),
        "by_policy": rows,
        "per_variant_outcomes": [],
    }


def _secondary_results(identity: str, outcomes: list[dict[str, Any]]) -> dict[str, Any]:
    support = _buggy_support(outcomes)
    matrices = {metric: {policy: {} for policy in FORMAL_POLICY_IDS} for metric in SECONDARY_METRIC_IDS}
    for policy in FORMAL_POLICY_IDS:
        for bucket in BUGGY_BUCKET_IDS:
            rows = [row for row in outcomes if row["policy_id"] == policy and row["is_buggy"] and row["taxonomy_id"] == bucket]
            denominator = len(rows)
            matrices["cost_to_first_failure"][policy][bucket] = _fraction_value(
                Fraction(sum(row["first_failure_cost_penalized"] for row in rows), denominator)
            )
            matrices["location_top3_loss"][policy][bucket] = _rate(
                sum(not row["location_top3_hit"] for row in rows), denominator
            )
            matrices["cause_top1_loss"][policy][bucket] = _rate(
                sum(not row["cause_top1_hit"] for row in rows), denominator
            )
            matrices["fix_intent_top1_loss"][policy][bucket] = _rate(
                sum(not row["fix_intent_top1_hit"] for row in rows), denominator
            )
            matrices["wrong_cause_high_confidence_rate"][policy][bucket] = _rate(
                sum(row["wrong_cause_high_confidence"] for row in rows), denominator
            )
            matrices["mean_investigation_cost"][policy][bucket] = _fraction_value(
                Fraction(sum(row["investigation_cost"] for row in rows), denominator)
            )
    return {
        "identity": identity,
        "metric_ids": list(SECONDARY_METRIC_IDS),
        "support_by_bucket": support,
        "failure_cost_for_missed_first_failure": 14,
        "added_to_discovery_loss": False,
        "used_in_restricted_pure_result": False,
        "matrices": matrices,
    }


def _extrema_record(
    projections: list[dict[str, Any]],
    variant_order: list[str],
    value_getter: Any,
    delta_getter: Any,
) -> dict[str, Any]:
    values = {item["removed_variant_id"]: value_getter(item) for item in projections}
    deltas = {item["removed_variant_id"]: delta_getter(item) for item in projections}
    if tuple(values) != tuple(variant_order) or tuple(deltas) != tuple(variant_order):
        raise P2AEvaluationError("LOVO extrema input order is incomplete")
    minimum_value, maximum_value = min(values.values()), max(values.values())
    minimum_delta, maximum_delta = min(deltas.values()), max(deltas.values())
    return {
        "minimum_projected_value": _fraction_value(minimum_value),
        "minimum_projected_value_variant_ids": [
            variant for variant in variant_order if values[variant] == minimum_value
        ],
        "maximum_projected_value": _fraction_value(maximum_value),
        "maximum_projected_value_variant_ids": [
            variant for variant in variant_order if values[variant] == maximum_value
        ],
        "minimum_baseline_delta": _fraction_value(minimum_delta),
        "minimum_baseline_delta_variant_ids": [
            variant for variant in variant_order if deltas[variant] == minimum_delta
        ],
        "maximum_baseline_delta": _fraction_value(maximum_delta),
        "maximum_baseline_delta_variant_ids": [
            variant for variant in variant_order if deltas[variant] == maximum_delta
        ],
    }


def _buggy_lovo(
    expansion: list[dict[str, Any]], combined: list[dict[str, Any]], baseline_results: Mapping[str, dict[str, Any]]
) -> dict[str, Any]:
    variants = [candidate.variant_id for candidate in BUGGY_CANDIDATES]
    projections = []
    for variant_id in variants:
        bucket = next(candidate.metadata["primary_bucket"] for candidate in BUGGY_CANDIDATES if candidate.variant_id == variant_id)
        for projection_id, source, baseline_id in (
            ("expansion_only_buggy_minus_v", expansion, BUGGY_IDENTITIES[2]),
            ("combined_versioned_buggy_minus_v", combined, BUGGY_IDENTITIES[3]),
        ):
            reduced = [row for row in source if row["variant_id"] != variant_id]
            baseline = baseline_results[baseline_id]
            affected_support = [
                item for item in baseline["support_by_bucket"][bucket] if item != variant_id
            ]
            affected = _buggy_bucket_cells(reduced, bucket, affected_support)
            five_cells = {
                policy: {
                    current_bucket: (
                        deepcopy(affected[policy])
                        if current_bucket == bucket
                        else deepcopy(baseline["cells_by_policy"][policy][current_bucket])
                    )
                    for current_bucket in BUGGY_BUCKET_IDS
                }
                for policy in FORMAL_POLICY_IDS
            }
            derived = _solution(five_cells)
            affected_deltas = {
                policy: {
                    "discovery_rate_delta": _fraction_value(
                        _fraction(affected[policy]["discovery_rate"])
                        - _fraction(baseline["cells_by_policy"][policy][bucket]["discovery_rate"])
                    ),
                    "discovery_loss_delta": _fraction_value(
                        _fraction(affected[policy]["discovery_loss"])
                        - _fraction(baseline["cells_by_policy"][policy][bucket]["discovery_loss"])
                    ),
                }
                for policy in FORMAL_POLICY_IDS
            }
            derived_deltas = {
                policy: {
                    "worst_bucket_delta": _fraction_value(
                        _fraction(derived["by_policy"][policy]["worst_bucket_loss"])
                        - _fraction(baseline["restricted_pure_result"]["by_policy"][policy]["worst_bucket_loss"])
                    ),
                    "reference_average_delta": _fraction_value(
                        _fraction(derived["by_policy"][policy]["reference_average_loss"])
                        - _fraction(baseline["restricted_pure_result"]["by_policy"][policy]["reference_average_loss"])
                    ),
                    "average_to_worst_gap_delta": _fraction_value(
                        _fraction(derived["by_policy"][policy]["average_to_worst_gap"])
                        - _fraction(baseline["restricted_pure_result"]["by_policy"][policy]["average_to_worst_gap"])
                    ),
                }
                for policy in FORMAL_POLICY_IDS
            }
            projections.append(
                {
                    "projection_id": projection_id,
                    "removed_variant_id": variant_id,
                    "affected_bucket_id": bucket,
                    "affected_cells_by_policy": affected,
                    "affected_cell_deltas_by_policy": affected_deltas,
                    "five_cells_by_policy": five_cells,
                    "derived_five_cell_result": derived,
                    "derived_baseline_deltas_by_policy": derived_deltas,
                    "restricted_pure_security_loss_delta": _fraction_value(
                        _fraction(derived["restricted_pure_security_loss"])
                        - _fraction(baseline["restricted_pure_result"]["restricted_pure_security_loss"])
                    ),
                    "recomputed_scope": ["affected_bucket_cell", "five_cell_derived_result"],
                    "non_recomputed_scope": ["unchanged_four_baseline_cells", "accepted_reference", "p2a_replay", "secondary", "clean", "policy_outcomes"],
                }
            )
    extremes: dict[str, Any] = {}
    for projection_id in ("expansion_only_buggy_minus_v", "combined_versioned_buggy_minus_v"):
        relevant = [item for item in projections if item["projection_id"] == projection_id]
        policy_metrics: dict[str, Any] = {}
        for policy in FORMAL_POLICY_IDS:
            metric_values = {
                "affected_cell_discovery_rate": (
                    lambda item: _fraction(item["affected_cells_by_policy"][policy]["discovery_rate"]),
                    lambda item: _fraction(item["affected_cell_deltas_by_policy"][policy]["discovery_rate_delta"]),
                ),
                "affected_cell_discovery_loss": (
                    lambda item: _fraction(item["affected_cells_by_policy"][policy]["discovery_loss"]),
                    lambda item: _fraction(item["affected_cell_deltas_by_policy"][policy]["discovery_loss_delta"]),
                ),
                "worst_bucket_loss": (
                    lambda item: _fraction(item["derived_five_cell_result"]["by_policy"][policy]["worst_bucket_loss"]),
                    lambda item: _fraction(item["derived_baseline_deltas_by_policy"][policy]["worst_bucket_delta"]),
                ),
                "reference_average_loss": (
                    lambda item: _fraction(item["derived_five_cell_result"]["by_policy"][policy]["reference_average_loss"]),
                    lambda item: _fraction(item["derived_baseline_deltas_by_policy"][policy]["reference_average_delta"]),
                ),
                "average_to_worst_gap": (
                    lambda item: _fraction(item["derived_five_cell_result"]["by_policy"][policy]["average_to_worst_gap"]),
                    lambda item: _fraction(item["derived_baseline_deltas_by_policy"][policy]["average_to_worst_gap_delta"]),
                ),
            }
            policy_metrics[policy] = {
                metric: _extrema_record(relevant, variants, value_getter, delta_getter)
                for metric, (value_getter, delta_getter) in metric_values.items()
            }
        projection_metrics = {
            "restricted_pure_security_loss": _extrema_record(
                relevant,
                variants,
                lambda item: _fraction(item["derived_five_cell_result"]["restricted_pure_security_loss"]),
                lambda item: _fraction(item["restricted_pure_security_loss_delta"]),
            )
        }
        extremes[projection_id] = {
            "policy_metrics": policy_metrics,
            "projection_metrics": projection_metrics,
        }
    return {
        "interpretation": "descriptive influence only; not uncertainty, significance, or a new dataset identity",
        "policy_rerun": False,
        "target_variant_ids": variants,
        "projection_ids": ["expansion_only_buggy_minus_v", "combined_versioned_buggy_minus_v"],
        "projections": projections,
        "extremes": extremes,
    }


def _clean_lovo(
    expansion: list[dict[str, Any]], combined: list[dict[str, Any]], baseline_results: Mapping[str, dict[str, Any]]
) -> dict[str, Any]:
    variants = [candidate.variant_id for candidate in CLEAN_CANDIDATES]
    projections = []
    for variant_id in variants:
        for projection_id, source, baseline_id in (
            ("expansion_only_clean_minus_v", expansion, CLEAN_IDENTITIES[2]),
            ("combined_versioned_clean_minus_v", combined, CLEAN_IDENTITIES[3]),
        ):
            reduced = [row for row in source if row["variant_id"] != variant_id]
            result = _clean_result("descriptive_lovo_projection", reduced, report_role="descriptive_influence_only", arithmetic_sources=[baseline_id, f"minus:{variant_id}"])
            rows: dict[str, Any] = {}
            for policy in FORMAL_POLICY_IDS:
                projected = result["by_policy"][policy]
                baseline = baseline_results[baseline_id]["by_policy"][policy]
                rows[policy] = {
                    **projected,
                    "false_positive_rate_delta": _fraction_value(_fraction(projected["false_positive_rate"]) - _fraction(baseline["false_positive_rate"])),
                    "mean_investigation_cost_delta": _fraction_value(_fraction(projected["mean_investigation_cost"]) - _fraction(baseline["mean_investigation_cost"])),
                    "no_bug_stop_rate_delta": _fraction_value(_fraction(projected["no_bug_stop_rate"]) - _fraction(baseline["no_bug_stop_rate"])),
                }
            projections.append(
                {
                    "projection_id": projection_id,
                    "removed_variant_id": variant_id,
                    "rows_by_policy": rows,
                    "recomputed_scope": ["false_positive_rate", "mean_investigation_cost", "no_bug_stop_rate"],
                    "non_recomputed_scope": ["accepted_reference", "p2a_replay", "buggy", "restricted_pure", "secondary", "policy_outcomes"],
                }
            )
    extremes: dict[str, Any] = {}
    for projection_id in ("expansion_only_clean_minus_v", "combined_versioned_clean_minus_v"):
        relevant = [item for item in projections if item["projection_id"] == projection_id]
        extremes[projection_id] = {}
        for policy in FORMAL_POLICY_IDS:
            extremes[projection_id][policy] = {
                metric: _extrema_record(
                    relevant,
                    variants,
                    lambda item, metric=metric: _fraction(item["rows_by_policy"][policy][metric]),
                    lambda item, metric=metric: _fraction(item["rows_by_policy"][policy][f"{metric}_delta"]),
                )
                for metric in CLEAN_LOVO_METRIC_IDS
            }
    return {
        "interpretation": "descriptive influence only; not uncertainty, significance, or a new dataset identity",
        "policy_rerun": False,
        "target_variant_ids": variants,
        "projection_ids": ["expansion_only_clean_minus_v", "combined_versioned_clean_minus_v"],
        "projections": projections,
        "extremes": extremes,
    }


def _validate_fraction_schema(value: Any, path: str) -> None:
    item = _exact_fields(value, ("numerator", "denominator", "decimal"), path)
    if type(item["numerator"]) is not int or type(item["denominator"]) is not int:
        raise P2AEvaluationError(f"{path}: fraction integers drifted")
    if item["denominator"] <= 0 or type(item["decimal"]) is not str:
        raise P2AEvaluationError(f"{path}: fraction representation drifted")
    fraction = Fraction(item["numerator"], item["denominator"])
    if fraction.numerator != item["numerator"] or fraction.denominator != item["denominator"]:
        raise P2AEvaluationError(f"{path}: fraction is not reduced")
    if item["decimal"] != format(float(fraction), ".12g"):
        raise P2AEvaluationError(f"{path}: fraction decimal drifted")


def _validate_extrema_schema(value: Any, path: str, variant_order: list[str]) -> None:
    item = _exact_fields(value, _EXTREMA_FIELDS, path)
    for field in _EXTREMA_FIELDS[::2]:
        _validate_fraction_schema(item[field], f"{path}.{field}")
    for field in _EXTREMA_FIELDS[1::2]:
        ids = item[field]
        if type(ids) is not list or not ids:
            raise P2AEvaluationError(f"{path}.{field}: extreme IDs are incomplete")
        if ids != [variant for variant in variant_order if variant in ids]:
            raise P2AEvaluationError(f"{path}.{field}: extreme IDs are not in stable order")


def validate_lovo_contract(value: Any) -> dict[str, Any]:
    """Validate complete LOVO projection and extrema schemas without recomputation."""

    sensitivity = _exact_fields(value, ("buggy_lovo", "clean_lovo"), "sensitivity")
    buggy = _exact_fields(
        sensitivity["buggy_lovo"],
        ("interpretation", "policy_rerun", "target_variant_ids", "projection_ids", "projections", "extremes"),
        "sensitivity.buggy_lovo",
    )
    buggy_variants = [candidate.variant_id for candidate in BUGGY_CANDIDATES]
    buggy_projection_ids = ["expansion_only_buggy_minus_v", "combined_versioned_buggy_minus_v"]
    if buggy["target_variant_ids"] != buggy_variants or buggy["projection_ids"] != buggy_projection_ids:
        raise P2AEvaluationError("buggy LOVO target/projection identity drifted")
    if buggy["policy_rerun"] is not False or len(buggy["projections"]) != 20:
        raise P2AEvaluationError("buggy LOVO projection count or rerun flag drifted")
    expected_pairs = [(variant, projection) for variant in buggy_variants for projection in buggy_projection_ids]
    for index, projection in enumerate(buggy["projections"]):
        item = _exact_fields(
            projection,
            (
                "projection_id",
                "removed_variant_id",
                "affected_bucket_id",
                "affected_cells_by_policy",
                "affected_cell_deltas_by_policy",
                "five_cells_by_policy",
                "derived_five_cell_result",
                "derived_baseline_deltas_by_policy",
                "restricted_pure_security_loss_delta",
                "recomputed_scope",
                "non_recomputed_scope",
            ),
            f"sensitivity.buggy_lovo.projections[{index}]",
        )
        if (item["removed_variant_id"], item["projection_id"]) != expected_pairs[index]:
            raise P2AEvaluationError("buggy LOVO projection order drifted")
        for mapping_name in (
            "affected_cells_by_policy",
            "affected_cell_deltas_by_policy",
            "five_cells_by_policy",
            "derived_baseline_deltas_by_policy",
        ):
            if tuple(item[mapping_name]) != FORMAL_POLICY_IDS:
                raise P2AEvaluationError(f"buggy LOVO {mapping_name} policy order drifted")
        for policy in FORMAL_POLICY_IDS:
            deltas = _exact_fields(
                item["affected_cell_deltas_by_policy"][policy],
                ("discovery_rate_delta", "discovery_loss_delta"),
                f"buggy projection affected deltas {policy}",
            )
            for delta in deltas.values():
                _validate_fraction_schema(delta, "buggy affected-cell delta")
            derived_deltas = _exact_fields(
                item["derived_baseline_deltas_by_policy"][policy],
                ("worst_bucket_delta", "reference_average_delta", "average_to_worst_gap_delta"),
                f"buggy projection derived deltas {policy}",
            )
            for delta in derived_deltas.values():
                _validate_fraction_schema(delta, "buggy derived delta")
        _validate_fraction_schema(
            item["restricted_pure_security_loss_delta"],
            "buggy projection restricted-pure delta",
        )
    if tuple(buggy["extremes"]) != tuple(buggy_projection_ids):
        raise P2AEvaluationError("buggy LOVO extrema projection order drifted")
    for projection_id in buggy_projection_ids:
        extrema = _exact_fields(
            buggy["extremes"][projection_id],
            ("policy_metrics", "projection_metrics"),
            f"buggy extrema {projection_id}",
        )
        if tuple(extrema["policy_metrics"]) != FORMAL_POLICY_IDS:
            raise P2AEvaluationError("buggy LOVO extrema policy order drifted")
        for policy in FORMAL_POLICY_IDS:
            metrics = extrema["policy_metrics"][policy]
            if tuple(metrics) != BUGGY_LOVO_POLICY_METRIC_IDS:
                raise P2AEvaluationError("buggy LOVO policy metric schema drifted")
            for metric, record in metrics.items():
                _validate_extrema_schema(record, f"buggy extrema {policy}.{metric}", buggy_variants)
        if tuple(extrema["projection_metrics"]) != BUGGY_LOVO_PROJECTION_METRIC_IDS:
            raise P2AEvaluationError("buggy LOVO projection metric schema drifted")
        for metric, record in extrema["projection_metrics"].items():
            _validate_extrema_schema(record, f"buggy extrema {metric}", buggy_variants)

    clean = _exact_fields(
        sensitivity["clean_lovo"],
        ("interpretation", "policy_rerun", "target_variant_ids", "projection_ids", "projections", "extremes"),
        "sensitivity.clean_lovo",
    )
    clean_variants = [candidate.variant_id for candidate in CLEAN_CANDIDATES]
    clean_projection_ids = ["expansion_only_clean_minus_v", "combined_versioned_clean_minus_v"]
    if clean["target_variant_ids"] != clean_variants or clean["projection_ids"] != clean_projection_ids:
        raise P2AEvaluationError("clean LOVO target/projection identity drifted")
    if clean["policy_rerun"] is not False or len(clean["projections"]) != 10:
        raise P2AEvaluationError("clean LOVO projection count or rerun flag drifted")
    expected_pairs = [(variant, projection) for variant in clean_variants for projection in clean_projection_ids]
    for index, projection in enumerate(clean["projections"]):
        item = _exact_fields(
            projection,
            (
                "projection_id",
                "removed_variant_id",
                "rows_by_policy",
                "recomputed_scope",
                "non_recomputed_scope",
            ),
            f"sensitivity.clean_lovo.projections[{index}]",
        )
        if (item["removed_variant_id"], item["projection_id"]) != expected_pairs[index]:
            raise P2AEvaluationError("clean LOVO projection order drifted")
        if tuple(item["rows_by_policy"]) != FORMAL_POLICY_IDS:
            raise P2AEvaluationError("clean LOVO row policy order drifted")
    if tuple(clean["extremes"]) != tuple(clean_projection_ids):
        raise P2AEvaluationError("clean LOVO extrema projection order drifted")
    for projection_id in clean_projection_ids:
        by_policy = clean["extremes"][projection_id]
        if tuple(by_policy) != FORMAL_POLICY_IDS:
            raise P2AEvaluationError("clean LOVO extrema policy order drifted")
        for policy in FORMAL_POLICY_IDS:
            metrics = by_policy[policy]
            if tuple(metrics) != CLEAN_LOVO_METRIC_IDS:
                raise P2AEvaluationError("clean LOVO metric schema drifted")
            for metric, record in metrics.items():
                _validate_extrema_schema(record, f"clean extrema {policy}.{metric}", clean_variants)
    return sensitivity


def _invalid_summary(reason: str, gate: dict[str, Any] | None = None) -> dict[str, Any]:
    safe_gate: dict[str, Any] = {}
    if gate is not None:
        try:
            validate_canonical_gate_identity(gate)
            safe_gate = deepcopy(gate)
        except Exception:  # noqa: BLE001 - invalid reports must remain safely serializable
            safe_gate = {}
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "analysis_phase": ANALYSIS_PHASE,
        "benchmark_id": BENCHMARK_ID,
        "report_role": REPORT_ROLE,
        "observation_mode": OBSERVATION_MODE,
        "legacy_benchmark_identity": deepcopy(_P1D1_IDENTITY),
        "dataset_identity": {"status": INVALID_STATUS},
        "adapter_identity": {},
        "action_test_catalog_identity": {},
        "freeze_identity": safe_gate,
        "validation_status": {"status": INVALID_STATUS, "reason": reason},
        "dataset_summary": {},
        "cohort_definitions": {},
        "formal_strategy_ids": list(FORMAL_POLICY_IDS),
        "excluded_policy_ids": list(EXCLUDED_POLICY_IDS),
        "fixed_settings": deepcopy(_FIXED_SETTINGS),
        "bucket_ids": list(BUGGY_BUCKET_IDS),
        "bucket_support_by_cohort": {},
        "clean_family_support_by_cohort": {},
        "reference_distribution_by_cohort": {},
        "primary_buggy_results_by_cohort": {},
        "clean_results_by_cohort": {},
        "secondary_metric_results_by_cohort": {},
        "sensitivity": {},
        "software_acceptance": {"status": INVALID_STATUS, "accepted": False},
        "limitations": [],
        "non_claims": ["No partial matrix or performance claim is emitted from invalid or incomplete input."],
        "notes": [],
    }


def build_versioned_summary(
    legacy_outcomes: Any,
    expansion_outcomes: Any,
    *,
    gate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one validated report summary or a fail-closed invalid summary."""

    try:
        supplied_gate = deepcopy(gate) if gate is not None else None
        current_gate = validate_pre_outcome_gate(run_compatibility=False)
        validate_canonical_gate_identity(current_gate)
        if supplied_gate is not None:
            validate_canonical_gate_identity(supplied_gate)
            _validate_exact_typed_identity(supplied_gate, current_gate, "supplied_gate")
            gate = supplied_gate
        else:
            gate = current_gate
        legacy_expected = [
            (variant.variant_id, variant.is_buggy, next((bucket for bucket, ids in _LEGACY_BUCKET_SUPPORT.items() if variant.variant_id in ids), "clean_false_positive"), None)
            for variant in load_p1b_variants()
        ]
        expansion_expected = [
            (
                candidate.variant_id,
                candidate.cohort_kind == "buggy",
                candidate.metadata.get("primary_bucket", "clean_false_positive"),
                candidate.metadata.get("clean_stress_family_id"),
            )
            for candidate in CANDIDATES
        ]
        legacy = _validate_outcomes(legacy_outcomes, expected_variants=legacy_expected, cohort_id="p2a_replayed_legacy")
        expansion = _validate_outcomes(expansion_outcomes, expected_variants=expansion_expected, cohort_id="expansion_only")
        legacy_buggy = [row for row in legacy if row["is_buggy"]]
        expansion_buggy = [row for row in expansion if row["is_buggy"]]
        legacy_clean = [row for row in legacy if not row["is_buggy"]]
        expansion_clean = [row for row in expansion if not row["is_buggy"]]
        combined_buggy = legacy_buggy + expansion_buggy
        combined_clean = legacy_clean + expansion_clean
        buggy_results = {
            BUGGY_IDENTITIES[0]: _accepted_buggy_reference(),
            BUGGY_IDENTITIES[1]: _buggy_result(BUGGY_IDENTITIES[1], legacy_buggy, report_role="catalog_context_delta_replay", arithmetic_sources=["p2a_replayed_legacy_outcomes"]),
            BUGGY_IDENTITIES[2]: _buggy_result(BUGGY_IDENTITIES[2], expansion_buggy, report_role="primary", arithmetic_sources=["frozen_expansion_outcomes"]),
            BUGGY_IDENTITIES[3]: _buggy_result(BUGGY_IDENTITIES[3], combined_buggy, report_role="descriptive", arithmetic_sources=[BUGGY_IDENTITIES[1], BUGGY_IDENTITIES[2]]),
        }
        clean_results = {
            CLEAN_IDENTITIES[0]: _accepted_clean_reference(),
            CLEAN_IDENTITIES[1]: _clean_result(CLEAN_IDENTITIES[1], legacy_clean, report_role="catalog_context_delta_replay", arithmetic_sources=["p2a_replayed_legacy_outcomes"]),
            CLEAN_IDENTITIES[2]: _clean_result(CLEAN_IDENTITIES[2], expansion_clean, report_role="primary_safety", arithmetic_sources=["frozen_expansion_outcomes"]),
            CLEAN_IDENTITIES[3]: _clean_result(CLEAN_IDENTITIES[3], combined_clean, report_role="descriptive_safety", arithmetic_sources=[CLEAN_IDENTITIES[1], CLEAN_IDENTITIES[2]]),
        }
        if tuple(buggy_results) != BUGGY_IDENTITIES or tuple(clean_results) != CLEAN_IDENTITIES:
            raise P2AEvaluationError("four identity order drifted")
        if len({id(value) for value in buggy_results.values()}) != 4 or len({id(value) for value in clean_results.values()}) != 4:
            raise P2AEvaluationError("four result objects alias")
        secondary = {
            BUGGY_IDENTITIES[0]: {
                "identity": BUGGY_IDENTITIES[0],
                "source": "accepted P1d1 secondary matrices",
                "source_json_sha256": _P1D1_IDENTITY["json_sha256"],
                "copied_or_recomputed_by_p2a": False,
                "metric_ids": list(SECONDARY_METRIC_IDS),
            },
            BUGGY_IDENTITIES[1]: _secondary_results(BUGGY_IDENTITIES[1], legacy_buggy),
            BUGGY_IDENTITIES[2]: _secondary_results(BUGGY_IDENTITIES[2], expansion_buggy),
            BUGGY_IDENTITIES[3]: _secondary_results(BUGGY_IDENTITIES[3], combined_buggy),
        }
        sensitivity = {
            "buggy_lovo": _buggy_lovo(expansion_buggy, combined_buggy, buggy_results),
            "clean_lovo": _clean_lovo(expansion_clean, combined_clean, clean_results),
        }
        validate_lovo_contract(sensitivity)
        summary = {
            "schema_version": REPORT_SCHEMA_VERSION,
            "analysis_phase": ANALYSIS_PHASE,
            "benchmark_id": BENCHMARK_ID,
            "report_role": REPORT_ROLE,
            "observation_mode": OBSERVATION_MODE,
            "legacy_benchmark_identity": deepcopy(_P1D1_IDENTITY),
            "dataset_identity": {
                "schema_version": "p2a_same_domain_dataset.v1",
                "benchmark_id": BENCHMARK_ID,
                "candidate_manifest_digest": EXPECTED_CANDIDATE_MANIFEST_DIGEST,
                "official_freeze_digest": OFFICIAL_FREEZE_DIGEST,
            },
            "adapter_identity": {
                "identity_version": "p2a_patch_grounded_adapter.v1",
                "digest": _EXPECTED_CONTRACT_DIGESTS["adapter"],
            },
            "action_test_catalog_identity": {
                "identity_version": "p2a_action_test_catalog.v1",
                "digest": _EXPECTED_CONTRACT_DIGESTS["catalog"],
            },
            "freeze_identity": gate,
            "validation_status": {
                "status": VALID_STATUS,
                "pre_outcome_gate_completed_before_candidate_outcomes": True,
                "complete_policy_variant_run_count": 240,
                "complete_primary_cell_count": 120,
                "post_outcome_contract_changed": False,
            },
            "dataset_summary": {
                "legacy": {"total": 25, "buggy": 20, "clean": 5},
                "expansion": {"total": 15, "buggy": 10, "clean": 5},
                "combined_p2a_derived": {"total": 40, "buggy": 30, "clean": 10},
            },
            "cohort_definitions": {
                "accepted_reference": "immutable accepted P1d1 context; never an arithmetic input to combined",
                "p2a_replay": "legacy variants executed under the frozen P2a adapter/catalog",
                "expansion_only": "frozen P2a variants only",
                "combined_versioned": "P2a replay plus expansion only",
            },
            "formal_strategy_ids": list(FORMAL_POLICY_IDS),
            "excluded_policy_ids": list(EXCLUDED_POLICY_IDS),
            "fixed_settings": {**deepcopy(_FIXED_SETTINGS), "stop_precedence": list(_STOP_PRECEDENCE)},
            "bucket_ids": list(BUGGY_BUCKET_IDS),
            "bucket_support_by_cohort": {identity: result["support_by_bucket"] for identity, result in buggy_results.items()},
            "clean_family_support_by_cohort": {
                CLEAN_IDENTITIES[2]: {
                    candidate.metadata["clean_stress_family_id"]: [candidate.variant_id]
                    for candidate in CLEAN_CANDIDATES
                }
            },
            "reference_distribution_by_cohort": {identity: result["reference_distribution"] for identity, result in buggy_results.items()},
            "primary_buggy_results_by_cohort": buggy_results,
            "clean_results_by_cohort": clean_results,
            "secondary_metric_results_by_cohort": secondary,
            "sensitivity": sensitivity,
            "software_acceptance": {
                "status": "implementation_conformant_pending_independent_review",
                "accepted_result": False,
                "performance_pattern_required_for_acceptance": False,
            },
            "limitations": [
                "Hand-authored stratified same-domain checkout/pricing variants.",
                "Non-iid empirical evidence with function-level location only.",
                "Synthetic real-diff artifacts rather than real repository histories.",
                "LOVO is descriptive influence only, not uncertainty or significance.",
                "A clean zero applies only to the included clean cohort.",
                "The fixed legacy fix-intent posterior label space does not contain the expansion authoring labels.",
            ],
            "non_claims": [
                "No second-domain, production, iid, causal, or generalization claim.",
                "No CI, bootstrap, significance, combined profile, weighted headline, mixed strategy, Nash, regret, or general minimax claim.",
                "Accepted-reference versus P2a-replay differences are catalog/context deltas, not variant expansion effects.",
            ],
            "notes": [
                "Expansion-only buggy discovery rate/loss is primary; combined buggy is descriptive.",
                "Clean evidence remains separate from buggy matrices, reference averages, and restricted-pure results.",
                "All equivalence and tie decisions use exact rational arithmetic before display formatting.",
            ],
        }
        validate_portable_value(summary, "summary")
        return summary
    except Exception as exc:  # noqa: BLE001 - fail-closed report boundary
        return _invalid_summary(str(exc), gate)


def saved_outcomes_from_report(source_summary: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Extract and validate the immutable replay/expansion outcomes from a saved report."""

    if type(source_summary) is not dict:
        raise P2AEvaluationError("saved outcome source must be a report object")
    if source_summary.get("schema_version") != REPORT_SCHEMA_VERSION:
        raise P2AEvaluationError("saved outcome source schema drifted")
    if source_summary.get("analysis_phase") != ANALYSIS_PHASE:
        raise P2AEvaluationError("saved outcome source analysis phase drifted")
    if source_summary.get("validation_status", {}).get("status") != VALID_STATUS:
        raise P2AEvaluationError("saved outcome source is not valid")
    if tuple(source_summary.get("formal_strategy_ids", ())) != FORMAL_POLICY_IDS:
        raise P2AEvaluationError("saved outcome source policy order drifted")
    validate_canonical_gate_identity(source_summary.get("freeze_identity"))
    buggy = source_summary.get("primary_buggy_results_by_cohort")
    clean = source_summary.get("clean_results_by_cohort")
    if type(buggy) is not dict or tuple(buggy) != BUGGY_IDENTITIES:
        raise P2AEvaluationError("saved buggy identity order drifted")
    if type(clean) is not dict or tuple(clean) != CLEAN_IDENTITIES:
        raise P2AEvaluationError("saved clean identity order drifted")
    legacy_raw = deepcopy(
        buggy[BUGGY_IDENTITIES[1]]["per_variant_outcomes"]
        + clean[CLEAN_IDENTITIES[1]]["per_variant_outcomes"]
    )
    expansion_raw = deepcopy(
        buggy[BUGGY_IDENTITIES[2]]["per_variant_outcomes"]
        + clean[CLEAN_IDENTITIES[2]]["per_variant_outcomes"]
    )
    legacy_expected = [
        (
            variant.variant_id,
            variant.is_buggy,
            next(
                (bucket for bucket, ids in _LEGACY_BUCKET_SUPPORT.items() if variant.variant_id in ids),
                "clean_false_positive",
            ),
            None,
        )
        for variant in load_p1b_variants()
    ]
    expansion_expected = [
        (
            candidate.variant_id,
            candidate.cohort_kind == "buggy",
            candidate.metadata.get("primary_bucket", "clean_false_positive"),
            candidate.metadata.get("clean_stress_family_id"),
        )
        for candidate in CANDIDATES
    ]
    legacy = _validate_outcomes(
        legacy_raw,
        expected_variants=legacy_expected,
        cohort_id="p2a_replayed_legacy",
    )
    expansion = _validate_outcomes(
        expansion_raw,
        expected_variants=expansion_expected,
        cohort_id="expansion_only",
    )
    legacy_buggy = [row for row in legacy if row["is_buggy"]]
    legacy_clean = [row for row in legacy if not row["is_buggy"]]
    expansion_buggy = [row for row in expansion if row["is_buggy"]]
    expansion_clean = [row for row in expansion if not row["is_buggy"]]
    if buggy[BUGGY_IDENTITIES[3]]["per_variant_outcomes"] != legacy_buggy + expansion_buggy:
        raise P2AEvaluationError("saved combined buggy outcomes are not replay plus expansion")
    if clean[CLEAN_IDENTITIES[3]]["per_variant_outcomes"] != legacy_clean + expansion_clean:
        raise P2AEvaluationError("saved combined clean outcomes are not replay plus expansion")
    snapshot = {
        "source_report_schema_version": source_summary["schema_version"],
        "formal_strategy_ids": list(FORMAL_POLICY_IDS),
        "outcome_fields": list(_OUTCOME_FIELDS),
        "legacy_outcomes": legacy,
        "expansion_outcomes": expansion,
    }
    if canonical_digest(snapshot) != SAVED_OUTCOME_SNAPSHOT_DIGEST:
        raise P2AEvaluationError("saved outcome canonical snapshot digest drifted")
    return legacy, expansion


def rebuild_versioned_summary_from_saved_report(source_summary: Any) -> dict[str, Any]:
    """Rebuild one corrected summary from saved outcomes without any outcome runner."""

    legacy, expansion = saved_outcomes_from_report(source_summary)
    return build_versioned_summary(legacy, expansion)


def run_versioned_evaluation(*, event_log: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Run the accepted frozen evaluation once after the complete gate."""

    events = event_log if event_log is not None else []
    gate = validate_pre_outcome_gate(run_compatibility=True)
    events.append({"event": "pre_outcome_gate_completed", "gate_digest": canonical_digest(gate)})
    bundle = load_tracked_official_freeze_bundle()
    legacy, expansion = _execute_all_outcomes(bundle, events)
    summary = build_versioned_summary(legacy, expansion, gate=gate)
    if summary["validation_status"]["status"] != VALID_STATUS:
        raise P2AEvaluationError(summary["validation_status"]["reason"])
    events.append({"event": "validated_summary_completed", "summary_digest": canonical_digest(summary)})
    return summary


def make_synthetic_outcomes() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return complete deterministic fixtures without executing any policy outcome."""

    legacy: list[dict[str, Any]] = []
    for variant in load_p1b_variants():
        bucket = next((bucket for bucket, ids in _LEGACY_BUCKET_SUPPORT.items() if variant.variant_id in ids), "clean_false_positive")
        for policy_index, policy in enumerate(FORMAL_POLICY_IDS):
            discovered = variant.is_buggy and (int(variant.variant_id[-3:]) + policy_index) % 3 != 0
            legacy.append(dict(zip(_OUTCOME_FIELDS, (variant.variant_id, "p2a_replayed_legacy", policy, variant.is_buggy, bucket, None, discovered, 2 if discovered else 14, discovered, discovered, False, False, 3, False, not variant.is_buggy), strict=True)))
    expansion: list[dict[str, Any]] = []
    for candidate_index, candidate in enumerate(CANDIDATES):
        is_buggy = candidate.cohort_kind == "buggy"
        taxonomy = candidate.metadata.get("primary_bucket", "clean_false_positive")
        family = candidate.metadata.get("clean_stress_family_id")
        for policy_index, policy in enumerate(FORMAL_POLICY_IDS):
            discovered = is_buggy and (candidate_index + policy_index) % 2 == 0
            expansion.append(dict(zip(_OUTCOME_FIELDS, (candidate.variant_id, "expansion_only", policy, is_buggy, taxonomy, family, discovered, 2 if discovered else 14, discovered, discovered, False, False, 4, False, not is_buggy), strict=True)))
    return legacy, expansion
