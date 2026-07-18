"""Descriptive audit of accepted frozen-policy P2a trajectories.

P2c replays the accepted expansion-only buggy policy/variant population without
changing policy semantics.  It records detector selection, recorded budget
feasibility, and exact termination as overlapping descriptive axes.  These
axes are not causal labels, policy rankings, or deployable recommendations.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import re
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterator, Mapping

from bug_cause_inference.p1b.actions import P1B_ACTION_SPECS
from bug_cause_inference.p1b.models import P1BSettings
from bug_cause_inference.p1b import policies as p1b_policies
from bug_cause_inference.p2a import evaluation as p2a_evaluation
from bug_cause_inference.p2a.adequacy import (
    canonical_digest,
    validate_portable_value,
)
from bug_cause_inference.p2a.candidates import BUGGY_CANDIDATES
from bug_cause_inference.p2b import reports as p2b_reports
from bug_cause_inference.p2b import solvability_ceiling as p2b_ceiling


SCHEMA_VERSION = "p2c_frozen_policy_trajectory_audit.v1"
ANALYSIS_PHASE = "p2c_frozen_policy_trajectory_audit"
REPORT_ROLE = (
    "analysis_only_fixed_input_descriptive_non_causal_non_deployable_audit"
)
VALID_STATUS = "valid"
INVALID_STATUS = "invalid_inconclusive"

BASE_COMMIT = "f6d4933caf7b0c1067b2c2d788a7fb86d6d8f45e"
SPECIFICATION_SHA256 = (
    "c285d0a42454699ecd01399a25a327d628ec13e4b347aee83909f866f36b529b"
)
SPECIFICATION_REVIEW_PROMPT_SHA256 = (
    "a7b2b28c0cf85be6a1370f7486e7674825db4d90182e51f2bd3f4aecfe38d99e"
)
SPECIFICATION_REVIEW_RECORD_SHA256 = (
    "3ee8f6cbca2cab0240e2150008544a22fe3532f17f7c1590bd3723113856dd4d"
)
IDENTITY_CONTRACT_DIGEST = (
    "1a7c59b40dc837b1c2199a6f1fe8fc8016b87400df89eda05c00e28f0b0767bc"
)
EXPECTED_P2B_JSON_SHA256 = (
    "1bbb71c5627f756f5dba3aba4f5f333f287f2fbacbb805e50118074d08ce928d"
)
EXPECTED_P2B_MARKDOWN_SHA256 = (
    "ad53651027e024febc04708763398112b81f1bf69aea4f104d94c70f4590ac3b"
)
EXPECTED_P2B_SUMMARY_DIGEST = (
    "873423a2cd15908300d604a970664152d931a8a306f64c797122851f887702e2"
)

FORMAL_POLICY_IDS = p2b_ceiling.FORMAL_POLICY_IDS
BUGGY_VARIANT_IDS = p2b_ceiling.BUGGY_VARIANT_IDS
BUCKET_IDS = p2b_ceiling.BUCKET_IDS
ACTION_IDS = p2b_ceiling.ACTION_IDS
STOP_REASON_IDS = (
    "no_bug_probability_threshold",
    "bug_confidence_threshold",
    "budget_limit",
    "max_steps",
    "low_expected_utility",
    "no_available_actions",
)

_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
_P2B_JSON_PATH = _REPOSITORY_ROOT / (
    "src/bug_cause_inference/p2b/artifacts/"
    "p2b_fixed_catalog_solvability_ceiling_v1.json"
)
_P2B_MARKDOWN_PATH = _REPOSITORY_ROOT / (
    "src/bug_cause_inference/p2b/artifacts/"
    "p2b_fixed_catalog_solvability_ceiling_v1.md"
)
_P2C_IMPLEMENTATION_PATHS = (
    "src/bug_cause_inference/p2c/__init__.py",
    "src/bug_cause_inference/p2c/trajectory_audit.py",
    "src/bug_cause_inference/p2c/reports.py",
)
_P2B_IDENTITY_APPEND = (
    (
        "p2b_solvability_source",
        "src/bug_cause_inference/p2b/solvability_ceiling.py",
        "cc7155407288a9d9045b49eb4a9f151808961ec58bd1c841e48ba076799e5b60",
    ),
    (
        "p2b_reports_source",
        "src/bug_cause_inference/p2b/reports.py",
        "3680c63c58356c792c45c1c5c04a1931dea0c2ebb610dde7f21024e790915b9b",
    ),
    (
        "p2b_json",
        "src/bug_cause_inference/p2b/artifacts/"
        "p2b_fixed_catalog_solvability_ceiling_v1.json",
        EXPECTED_P2B_JSON_SHA256,
    ),
    (
        "p2b_markdown",
        "src/bug_cause_inference/p2b/artifacts/"
        "p2b_fixed_catalog_solvability_ceiling_v1.md",
        EXPECTED_P2B_MARKDOWN_SHA256,
    ),
)

_PAIR_FIELDS = (
    "pair_index",
    "variant_id",
    "bucket_id",
    "policy_id",
    "accepted_p2a_discovered_within_budget",
    "replayed_discovered_within_budget",
    "accepted_replay_agreement",
    "direct_detecting_action_ids",
    "minimum_detecting_cost",
    "executed_action_ids",
    "step_count",
    "cumulative_cost",
    "stop_reason",
    "direct_detector_selected",
    "first_selected_direct_detector_action_id",
    "first_selected_direct_detector_step",
    "first_selected_direct_detector_cumulative_cost",
    "first_selected_direct_detector_observation_detected",
    "initial_feasible_direct_detector_ids",
    "any_pre_action_direct_detector_budget_feasible",
    "all_pre_action_states_direct_detector_budget_feasible",
    "terminal_feasible_direct_detector_ids",
    "terminal_direct_detector_budget_feasible",
    "terminal_common_stop_result",
    "pre_action_states",
    "pair_trace_digest",
    "consistency_checks",
)
_PRE_ACTION_FIELDS = (
    "decision_step",
    "executed_action_ids_before",
    "cumulative_cost_before",
    "remaining_budget_before",
    "feasible_direct_detector_ids",
    "direct_detector_budget_feasible",
    "selected_action_id",
    "selected_action_cost",
    "selected_action_is_direct_detector",
    "observation_bug_detected",
    "cumulative_cost_after",
)
_CONSISTENCY_FIELDS = (
    "accepted_p2a_outcome_matches_replay",
    "p2b_mapping_complete",
    "selected_detector_observation_consistent",
    "discovery_requires_selected_detector",
    "stop_reason_reconstruction_matches",
    "cost_step_action_consistent",
)
_AXIS_FIELDS = (
    "support_pair_count",
    "detector_selected_count",
    "detector_not_selected_count",
    "initial_detector_budget_feasible_count",
    "any_pre_action_detector_budget_feasible_count",
    "all_pre_action_states_detector_budget_feasible_count",
    "terminal_detector_budget_feasible_count",
    "detector_not_selected_terminal_feasible_count",
    "detector_not_selected_terminal_infeasible_count",
    "replayed_discovered_count",
    "stop_reason_counts",
    "unselected_stop_reason_counts",
    "selection_terminal_budget_stop_crosstab",
)
_VALID_TOP_FIELDS = (
    "schema_version",
    "analysis_phase",
    "report_role",
    "validation_status",
    "input_identity",
    "pre_outcome_freeze",
    "execution_boundary",
    "population",
    "definitions",
    "pair_trajectories",
    "aggregate_axes",
    "software_acceptance",
    "artifact_identity_acceptance",
    "result_acceptance",
    "documentation_acceptance",
    "limitations",
    "non_claims",
    "notes",
)
_INVALID_TOP_FIELDS = (
    "schema_version",
    "analysis_phase",
    "report_role",
    "validation_status",
    "reason_codes",
    "input_identity",
    "software_acceptance",
    "artifact_identity_acceptance",
    "result_acceptance",
    "documentation_acceptance",
    "non_claims",
)
_INPUT_IDENTITY_FIELDS = (
    "base_commit",
    "identity_hash_mode",
    "raw_drift_mode",
    "identity_contract_digest",
    "identity_support_count",
    "identity_rows",
    "p2a_summary_digest",
    "p2a_json_sha256",
    "p2a_markdown_sha256",
    "p2b_summary_digest",
    "p2b_json_sha256",
    "p2b_markdown_sha256",
    "p2b_accepted_identity_count",
    "implementation_file_sha256_lf",
)
_PRE_OUTCOME_FREEZE_FIELDS = (
    "specification_sha256",
    "review_prompt_sha256",
    "review_record_sha256",
    "specification_review_verdict",
    "first_pair_index",
    "first_variant_id",
    "first_policy_id",
    "schema_version",
)
_EXECUTION_BOUNDARY_FIELDS = (
    "first_execution_point",
    "pair_execution_count",
    "variant_context_count",
    "policies_per_variant",
    "raw_identity_pre_post_match",
    "implementation_raw_pre_post_match",
    "policy_runner_semantic_change",
)
_POPULATION_FIELDS = (
    "variant_ids",
    "policy_ids",
    "bucket_ids",
    "pair_order",
    "pair_count",
    "overall_denominator",
    "policy_denominator",
    "variant_denominator",
    "bucket_denominator",
)
_DEFINITION_FIELDS = (
    "selection_axis",
    "budget_state_axis",
    "termination_axis",
    "axis_relationship",
)
_ACCEPTANCE_FIELDS = ("scope", "accepted", "status")
_EXPECTED_DETECTOR_MAPPING = {
    "P2A-BUG-001": ("boundary_precision", ("run_boundary_tests",), 2),
    "P2A-BUG-002": ("boundary_precision", ("run_boundary_tests",), 2),
    "P2A-BUG-003": ("missing_optional_input", ("run_null_missing_tests",), 2),
    "P2A-BUG-004": (
        "missing_optional_input",
        ("run_null_missing_tests", "run_config_matrix_tests"),
        2,
    ),
    "P2A-BUG-005": ("config_normalization", ("run_config_matrix_tests",), 3),
    "P2A-BUG-006": ("config_normalization", ("run_config_matrix_tests",), 3),
    "P2A-BUG-007": ("state_sequence", ("run_state_sequence_tests",), 4),
    "P2A-BUG-008": ("state_sequence", ("run_state_sequence_tests",), 4),
    "P2A-BUG-009": ("spec_semantics", ("inspect_spec_clause",), 2),
    "P2A-BUG-010": ("spec_semantics", ("inspect_spec_clause",), 2),
}
_EXPECTED_DISCOVERED_PAIRS = frozenset(
    (variant_id, policy_id)
    for variant_id in ("P2A-BUG-001", "P2A-BUG-002")
    for policy_id in FORMAL_POLICY_IDS[:4]
)
_EXPECTED_BUDGET_STOP_PAIRS = frozenset(
    (("P2A-BUG-001", "coverage_first"), ("P2A-BUG-002", "coverage_first"))
)
_LOCAL_PATH_RE = re.compile(
    r"(?:"
    r"[A-Za-z]:[\\/]"
    r"|\\\\+[^\\/\s]+[\\/]+[^\\/\s]+"
    r"|\bfile://[^\s]+"
    r"|(?<![A-Za-z0-9_/\\])/(?!/)[^\s]+"
    r")",
    re.IGNORECASE,
)


class P2CTrajectoryAuditError(ValueError):
    """Raised when a frozen audit contract or complete result is invalid."""


def _repository_path(relative_path: str) -> Path:
    path = Path(relative_path)
    if path.is_absolute() or ".." in path.parts:
        raise P2CTrajectoryAuditError("identity path must be repository-relative")
    resolved = (_REPOSITORY_ROOT / path).resolve()
    try:
        resolved.relative_to(_REPOSITORY_ROOT)
    except ValueError as exc:
        raise P2CTrajectoryAuditError("identity path escapes repository") from exc
    return resolved


def _hash_file(path: Path) -> tuple[str, str]:
    raw = path.read_bytes()
    canonical = raw.replace(b"\r\n", b"\n")
    return hashlib.sha256(canonical).hexdigest(), hashlib.sha256(raw).hexdigest()


def _identity_rows() -> list[dict[str, str]]:
    rows = [
        {"identity": identity, "path": path, "sha256_lf": expected}
        for identity, (path, expected) in p2b_ceiling._ACCEPTED_FILE_IDENTITIES.items()
    ]
    rows.extend(
        {"identity": identity, "path": path, "sha256_lf": expected}
        for identity, path, expected in _P2B_IDENTITY_APPEND
    )
    if len(rows) != 43 or len({row["identity"] for row in rows}) != 43:
        raise P2CTrajectoryAuditError("43-file identity support drifted")
    return rows


def identity_contract_digest(rows: list[dict[str, str]]) -> str:
    canonical = json.dumps(
        rows,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _fresh_identity_snapshot() -> tuple[list[dict[str, str]], dict[str, str]]:
    rows = _identity_rows()
    if identity_contract_digest(rows) != IDENTITY_CONTRACT_DIGEST:
        raise P2CTrajectoryAuditError("43-file identity contract digest drifted")
    raw_hashes: dict[str, str] = {}
    for row in rows:
        portable, raw = _hash_file(_repository_path(row["path"]))
        if portable != row["sha256_lf"]:
            raise P2CTrajectoryAuditError(
                f"accepted input drifted: {row['identity']}"
            )
        raw_hashes[row["identity"]] = raw
    return rows, raw_hashes


def _implementation_identity() -> dict[str, str]:
    return {
        path: _hash_file(_repository_path(path))[0]
        for path in _P2C_IMPLEMENTATION_PATHS
    }


def _implementation_raw_snapshot() -> dict[str, str]:
    return {
        path: _hash_file(_repository_path(path))[1]
        for path in _P2C_IMPLEMENTATION_PATHS
    }


def _ratio(numerator: int, denominator: int, *, reason: str | None = None) -> dict[str, Any]:
    if type(numerator) is not int or type(denominator) is not int:
        raise P2CTrajectoryAuditError("ratio counts must be exact integers")
    if numerator < 0 or denominator < 0 or numerator > denominator:
        raise P2CTrajectoryAuditError("ratio counts are outside support")
    if denominator == 0:
        if not reason:
            raise P2CTrajectoryAuditError("zero support requires undefined reason")
        return {
            "numerator": numerator,
            "denominator": denominator,
            "fraction": None,
            "decimal": None,
            "undefined_reason": reason,
        }
    value = Fraction(numerator, denominator)
    return {
        "numerator": numerator,
        "denominator": denominator,
        "fraction": f"{value.numerator}/{value.denominator}",
        "decimal": format(float(value), ".12g"),
        "undefined_reason": None,
    }


def canonical_trace_digest(rows: list[dict[str, Any]]) -> str:
    canonical = json.dumps(
        rows,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _exact_fields(value: Any, fields: tuple[str, ...], path: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise P2CTrajectoryAuditError(f"{path}: expected object")
    if tuple(value) != fields:
        raise P2CTrajectoryAuditError(f"{path}: fields missing, extra, or reordered")
    return value


def _load_inputs() -> dict[str, Any]:
    identity_rows, raw_hashes = _fresh_identity_snapshot()
    p2b_inputs = p2b_ceiling._load_validated_inputs()
    p2b_json = json.loads(_P2B_JSON_PATH.read_text(encoding="utf-8"))
    p2b_ceiling.validate_diagnostic_summary(p2b_json)
    p2b_markdown = p2b_reports.summary_from_markdown(
        _P2B_MARKDOWN_PATH.read_text(encoding="utf-8")
    )
    if p2b_markdown != p2b_json:
        raise P2CTrajectoryAuditError("accepted P2b JSON/Markdown semantics drifted")
    if canonical_digest(p2b_json) != EXPECTED_P2B_SUMMARY_DIGEST:
        raise P2CTrajectoryAuditError("accepted P2b summary digest drifted")
    diagnostics = p2b_json["variant_diagnostics"]
    if tuple(row["variant_id"] for row in diagnostics) != BUGGY_VARIANT_IDS:
        raise P2CTrajectoryAuditError("P2b variant mapping order drifted")
    mapping: dict[str, dict[str, Any]] = {}
    for row in diagnostics:
        detectors = list(row["detecting_action_ids"])
        if not row["budget_feasible"] or not detectors:
            raise P2CTrajectoryAuditError("P2b detector mapping is incomplete")
        minimum = min(P1B_ACTION_SPECS[action].cost for action in detectors)
        if minimum != row["minimum_detecting_cost"]:
            raise P2CTrajectoryAuditError("P2b minimum detecting cost drifted")
        mapping[row["variant_id"]] = {
            "bucket_id": row["bucket_id"],
            "direct_detecting_action_ids": detectors,
            "minimum_detecting_cost": minimum,
        }
    saved_rows = p2b_inputs["buggy_saved_outcomes"]
    expected_pairs = [
        (variant, policy)
        for variant in BUGGY_VARIANT_IDS
        for policy in FORMAL_POLICY_IDS
    ]
    if [(row["variant_id"], row["policy_id"]) for row in saved_rows] != expected_pairs:
        raise P2CTrajectoryAuditError("accepted P2a saved pair order drifted")
    return {
        "p2b_inputs": p2b_inputs,
        "p2b_summary": p2b_json,
        "p2b_mapping": mapping,
        "saved_rows": saved_rows,
        "identity_rows": identity_rows,
        "raw_hashes": raw_hashes,
        "implementation_identity": _implementation_identity(),
        "implementation_raw_hashes": _implementation_raw_snapshot(),
    }


def _state_from_values(
    *,
    bug_presence: float,
    cause: Mapping[str, float],
    location: Mapping[str, float],
    fix_intent: Mapping[str, float],
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
        execution_context=None,
    )


def _feasible_detectors(
    detector_ids: list[str], executed: list[str], remaining_budget: int
) -> list[str]:
    return [
        action_id
        for action_id in ACTION_IDS
        if action_id in detector_ids
        and action_id not in executed
        and P1B_ACTION_SPECS[action_id].cost <= remaining_budget
    ]


def _build_pair_row(
    *,
    pair_index: int,
    variant: Any,
    policy_id: str,
    result: Any,
    accepted_row: Mapping[str, Any],
    detector_mapping: Mapping[str, Any],
) -> dict[str, Any]:
    settings = P1BSettings(**p2a_evaluation._FIXED_SETTINGS)
    detectors = list(detector_mapping["direct_detecting_action_ids"])
    executed_before: list[str] = []
    prior_cost = 0
    prior_bug_detected = False
    pre_action_states: list[dict[str, Any]] = []
    first_detector: dict[str, Any] | None = None
    cost_step_consistent = True
    selected_detector_consistent = True
    rng = random.Random(
        p1b_policies._stable_seed(variant.variant_id, settings.rng_seed)
    )
    for expected_step, trace in enumerate(result.trace, start=1):
        if trace.step != expected_step or trace.policy != policy_id:
            cost_step_consistent = False
        state = _state_from_values(
            bug_presence=trace.prior_bug_presence_posterior,
            cause=trace.prior_cause_posterior,
            location=trace.prior_location_posterior,
            fix_intent=trace.prior_fix_intent_posterior,
            executed_actions=executed_before,
            cumulative_cost=prior_cost,
            current_step=expected_step - 1,
            bug_detected=prior_bug_detected,
        )
        remaining = settings.budget_limit - prior_cost
        recomputed_scores = p1b_policies.score_actions(state, remaining)
        if recomputed_scores != trace.action_scores:
            cost_step_consistent = False
        best = (
            recomputed_scores[0]["expected_utility_per_cost"]
            if recomputed_scores
            else None
        )
        if p1b_policies._check_stop(state, settings, best) is not None:
            cost_step_consistent = False
        selected = p1b_policies.choose_action(policy_id, state, remaining, rng)
        if selected != trace.selected_action:
            cost_step_consistent = False
        action_id = trace.selected_action
        spec = P1B_ACTION_SPECS[action_id]
        feasible = _feasible_detectors(detectors, executed_before, remaining)
        selected_is_detector = action_id in detectors
        if (
            trace.observation.action_id != action_id
            or trace.observation.cost != spec.cost
            or trace.cumulative_cost != prior_cost + spec.cost
            or action_id in executed_before
            or spec.cost > remaining
        ):
            cost_step_consistent = False
        if selected_is_detector and not trace.observation.bug_detected:
            selected_detector_consistent = False
        pre_action_states.append(
            dict(
                zip(
                    _PRE_ACTION_FIELDS,
                    (
                        expected_step,
                        list(executed_before),
                        prior_cost,
                        remaining,
                        feasible,
                        bool(feasible),
                        action_id,
                        spec.cost,
                        selected_is_detector,
                        trace.observation.bug_detected,
                        trace.cumulative_cost,
                    ),
                    strict=True,
                )
            )
        )
        if selected_is_detector and first_detector is None:
            first_detector = {
                "action_id": action_id,
                "step": expected_step,
                "cumulative_cost": trace.cumulative_cost,
                "observation_detected": trace.observation.bug_detected,
            }
        executed_before.append(action_id)
        prior_cost = trace.cumulative_cost
        prior_bug_detected = prior_bug_detected or trace.observation.bug_detected

    if not pre_action_states:
        raise P2CTrajectoryAuditError("accepted initial state unexpectedly stopped")
    if executed_before != list(result.executed_actions):
        cost_step_consistent = False
    if prior_cost != result.cumulative_cost or len(pre_action_states) != result.current_step:
        cost_step_consistent = False
    terminal_state = _state_from_values(
        bug_presence=result.bug_presence_posterior,
        cause=result.cause_posterior,
        location=result.location_posterior,
        fix_intent=result.fix_intent_posterior,
        executed_actions=list(result.executed_actions),
        cumulative_cost=result.cumulative_cost,
        current_step=result.current_step,
        bug_detected=result.bug_detected,
    )
    terminal_remaining = settings.budget_limit - result.cumulative_cost
    terminal_scores = p1b_policies.score_actions(terminal_state, terminal_remaining)
    terminal_best = (
        terminal_scores[0]["expected_utility_per_cost"]
        if terminal_scores
        else None
    )
    terminal_common_stop = p1b_policies._check_stop(
        terminal_state, settings, terminal_best
    )
    feasible_all = [
        action_id
        for action_id in ACTION_IDS
        if action_id not in result.executed_actions
        and P1B_ACTION_SPECS[action_id].cost <= terminal_remaining
    ]
    if result.stop_reason == "no_available_actions":
        stop_matches = terminal_common_stop is None and not feasible_all
    else:
        stop_matches = terminal_common_stop == result.stop_reason
    terminal_feasible = _feasible_detectors(
        detectors, list(result.executed_actions), terminal_remaining
    )
    replayed = bool(
        result.bug_detected and result.cumulative_cost <= settings.budget_limit
    )
    accepted = accepted_row["discovered_within_budget"]
    detector_selected = first_detector is not None
    discovery_requires = replayed == detector_selected
    checks = dict(
        zip(
            _CONSISTENCY_FIELDS,
            (
                accepted == replayed,
                bool(detectors)
                and detector_mapping["minimum_detecting_cost"]
                == min(P1B_ACTION_SPECS[action].cost for action in detectors),
                selected_detector_consistent,
                discovery_requires,
                stop_matches,
                cost_step_consistent,
            ),
            strict=True,
        )
    )
    if not all(checks.values()):
        raise P2CTrajectoryAuditError("pair trajectory consistency check failed")
    first = first_detector or {
        "action_id": None,
        "step": None,
        "cumulative_cost": None,
        "observation_detected": None,
    }
    return dict(
        zip(
            _PAIR_FIELDS,
            (
                pair_index,
                variant.variant_id,
                detector_mapping["bucket_id"],
                policy_id,
                accepted,
                replayed,
                accepted == replayed,
                detectors,
                detector_mapping["minimum_detecting_cost"],
                list(result.executed_actions),
                result.current_step,
                result.cumulative_cost,
                result.stop_reason,
                detector_selected,
                first["action_id"],
                first["step"],
                first["cumulative_cost"],
                first["observation_detected"],
                list(pre_action_states[0]["feasible_direct_detector_ids"]),
                any(row["direct_detector_budget_feasible"] for row in pre_action_states),
                all(row["direct_detector_budget_feasible"] for row in pre_action_states),
                terminal_feasible,
                bool(terminal_feasible),
                terminal_common_stop,
                pre_action_states,
                canonical_trace_digest(pre_action_states),
                checks,
            ),
            strict=True,
        )
    )


def _axis_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    support = len(rows)
    selected = sum(row["direct_detector_selected"] for row in rows)
    initial = sum(bool(row["initial_feasible_direct_detector_ids"]) for row in rows)
    any_pre = sum(row["any_pre_action_direct_detector_budget_feasible"] for row in rows)
    all_pre = sum(row["all_pre_action_states_direct_detector_budget_feasible"] for row in rows)
    terminal = sum(row["terminal_direct_detector_budget_feasible"] for row in rows)
    unselected_terminal = sum(
        not row["direct_detector_selected"]
        and row["terminal_direct_detector_budget_feasible"]
        for row in rows
    )
    unselected_infeasible = sum(
        not row["direct_detector_selected"]
        and not row["terminal_direct_detector_budget_feasible"]
        for row in rows
    )
    discovered = sum(row["replayed_discovered_within_budget"] for row in rows)
    stop_counts = {
        reason: sum(row["stop_reason"] == reason for row in rows)
        for reason in STOP_REASON_IDS
    }
    unselected_stop_counts = {
        reason: sum(
            not row["direct_detector_selected"] and row["stop_reason"] == reason
            for row in rows
        )
        for reason in STOP_REASON_IDS
    }
    crosstab = [
        {
            "detector_selected": selected_flag,
            "terminal_direct_detector_budget_feasible": terminal_flag,
            "stop_reason": reason,
            "count": sum(
                row["direct_detector_selected"] is selected_flag
                and row["terminal_direct_detector_budget_feasible"] is terminal_flag
                and row["stop_reason"] == reason
                for row in rows
            ),
        }
        for selected_flag in (False, True)
        for terminal_flag in (False, True)
        for reason in STOP_REASON_IDS
    ]
    return dict(
        zip(
            _AXIS_FIELDS,
            (
                support,
                _ratio(selected, support, reason="no_pair_support"),
                _ratio(support - selected, support, reason="no_pair_support"),
                _ratio(initial, support, reason="no_pair_support"),
                _ratio(any_pre, support, reason="no_pair_support"),
                _ratio(all_pre, support, reason="no_pair_support"),
                _ratio(terminal, support, reason="no_pair_support"),
                _ratio(unselected_terminal, support - selected, reason="no_unselected_support"),
                _ratio(unselected_infeasible, support - selected, reason="no_unselected_support"),
                _ratio(discovered, support, reason="no_pair_support"),
                stop_counts,
                unselected_stop_counts,
                crosstab,
            ),
            strict=True,
        )
    )


def derive_aggregate_axes(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "overall": _axis_summary(rows),
        "by_policy": [
            {
                "policy_id": policy,
                "axes": _axis_summary([row for row in rows if row["policy_id"] == policy]),
            }
            for policy in FORMAL_POLICY_IDS
        ],
        "by_variant": [
            {
                "variant_id": variant,
                "axes": _axis_summary([row for row in rows if row["variant_id"] == variant]),
            }
            for variant in BUGGY_VARIANT_IDS
        ],
        "by_bucket": [
            {
                "bucket_id": bucket,
                "axes": _axis_summary([row for row in rows if row["bucket_id"] == bucket]),
            }
            for bucket in BUCKET_IDS
        ],
    }


def _input_identity(inputs: Mapping[str, Any]) -> dict[str, Any]:
    p2b = inputs["p2b_inputs"]
    return {
        "base_commit": BASE_COMMIT,
        "identity_hash_mode": "sha256_after_crlf_to_lf_normalization",
        "raw_drift_mode": "exact_working_tree_sha256_pre_post_same_run",
        "identity_contract_digest": IDENTITY_CONTRACT_DIGEST,
        "identity_support_count": 43,
        "identity_rows": deepcopy(inputs["identity_rows"]),
        "p2a_summary_digest": p2b_ceiling.EXPECTED_P2A_SUMMARY_DIGEST,
        "p2a_json_sha256": p2b_ceiling.EXPECTED_P2A_JSON_SHA256,
        "p2a_markdown_sha256": p2b_ceiling.EXPECTED_P2A_MARKDOWN_SHA256,
        "p2b_summary_digest": EXPECTED_P2B_SUMMARY_DIGEST,
        "p2b_json_sha256": EXPECTED_P2B_JSON_SHA256,
        "p2b_markdown_sha256": EXPECTED_P2B_MARKDOWN_SHA256,
        "p2b_accepted_identity_count": len(p2b["accepted_hashes"]),
        "implementation_file_sha256_lf": deepcopy(inputs["implementation_identity"]),
    }


def _pending_acceptance(scope: str) -> dict[str, Any]:
    return {"scope": scope, "accepted": False, "status": "pending_separate_acceptance"}


def _invalid_summary(
    reason: str,
    *,
    input_identity: dict[str, Any] | None = None,
) -> dict[str, Any]:
    summary = dict(
        zip(
            _INVALID_TOP_FIELDS,
            (
                SCHEMA_VERSION,
                ANALYSIS_PHASE,
                REPORT_ROLE,
                {"status": INVALID_STATUS},
                [reason],
                deepcopy(input_identity),
                _pending_acceptance("software_conformance"),
                _pending_acceptance("versioned_artifact_identity"),
                _pending_acceptance("descriptive_result"),
                _pending_acceptance("public_result_documentation"),
                [
                    "Invalid input or execution cannot support partial trajectory, aggregate, performance, or acceptance claims."
                ],
            ),
            strict=True,
        )
    )
    return validate_audit_summary(summary)


def _build_valid_summary(
    inputs: Mapping[str, Any], rows: list[dict[str, Any]]
) -> dict[str, Any]:
    summary = dict(
        zip(
            _VALID_TOP_FIELDS,
            (
                SCHEMA_VERSION,
                ANALYSIS_PHASE,
                REPORT_ROLE,
                {"status": VALID_STATUS},
                _input_identity(inputs),
                {
                    "specification_sha256": SPECIFICATION_SHA256,
                    "review_prompt_sha256": SPECIFICATION_REVIEW_PROMPT_SHA256,
                    "review_record_sha256": SPECIFICATION_REVIEW_RECORD_SHA256,
                    "specification_review_verdict": "accept",
                    "first_pair_index": 1,
                    "first_variant_id": BUGGY_VARIANT_IDS[0],
                    "first_policy_id": FORMAL_POLICY_IDS[0],
                    "schema_version": SCHEMA_VERSION,
                },
                {
                    "first_execution_point": "P2A-BUG-001::fixed_checklist",
                    "pair_execution_count": 60,
                    "variant_context_count": 10,
                    "policies_per_variant": 6,
                    "raw_identity_pre_post_match": True,
                    "implementation_raw_pre_post_match": True,
                    "policy_runner_semantic_change": False,
                },
                {
                    "variant_ids": list(BUGGY_VARIANT_IDS),
                    "policy_ids": list(FORMAL_POLICY_IDS),
                    "bucket_ids": list(BUCKET_IDS),
                    "pair_order": "variant_major_then_policy_minor",
                    "pair_count": 60,
                    "overall_denominator": 60,
                    "policy_denominator": 10,
                    "variant_denominator": 6,
                    "bucket_denominator": 12,
                },
                {
                    "selection_axis": "whether an accepted P2b direct detector was selected",
                    "budget_state_axis": "cost/executed-state feasibility at recorded decisions, not post-stop selectability",
                    "termination_axis": "exact accepted runner stop reason, step, and cost",
                    "axis_relationship": "overlapping descriptive observations, not mutually exclusive causal causes",
                },
                rows,
                derive_aggregate_axes(rows),
                _pending_acceptance("software_conformance"),
                _pending_acceptance("versioned_artifact_identity"),
                _pending_acceptance("descriptive_result"),
                _pending_acceptance("public_result_documentation"),
                [
                    "The audit covers only 60 fixed same-domain policy/variant pairs.",
                    "Detector mapping is ground-truth-informed and unavailable to deployable policies.",
                    "Terminal budget feasibility does not imply that the runner may select after a stop condition.",
                    "Only reduced recorded decision states are preserved; full posteriors and action scores are excluded.",
                ],
                [
                    "The selection, budget-state, and termination axes are not causal attributions.",
                    "This audit does not rank policies or establish policy superiority, inferiority, or defects.",
                    "This audit is not a new policy, counterfactual replay, sequence/DP ceiling, or optimality result.",
                    "This fixed-cohort result does not establish inference, generalization, or production readiness.",
                ],
                [
                    "Accepted P2a/P2b inputs, policies, artifacts, and results remain unchanged.",
                    "Artifact identity, descriptive result, and public documentation require separate post-merge acceptance.",
                ],
            ),
            strict=True,
        )
    )
    return validate_audit_summary(summary)


def _assert_finite_and_private_safe(value: Any) -> None:
    if type(value) is dict:
        for child in value.values():
            _assert_finite_and_private_safe(child)
        return
    if type(value) is list:
        for child in value:
            _assert_finite_and_private_safe(child)
        return
    if type(value) is float and not math.isfinite(value):
        raise P2CTrajectoryAuditError("summary contains non-finite value")
    if type(value) is str and _LOCAL_PATH_RE.search(value):
        raise P2CTrajectoryAuditError("summary contains private absolute path")


def _assert_exact_value(actual: Any, expected: Any, path: str) -> None:
    """Compare contract values without Python's bool/int equality aliasing."""

    if type(actual) is not type(expected):
        raise P2CTrajectoryAuditError(f"{path}: type drifted")
    if type(expected) is dict:
        if tuple(actual) != tuple(expected):
            raise P2CTrajectoryAuditError(f"{path}: fields or order drifted")
        for key, expected_value in expected.items():
            _assert_exact_value(actual[key], expected_value, f"{path}.{key}")
        return
    if type(expected) is list:
        if len(actual) != len(expected):
            raise P2CTrajectoryAuditError(f"{path}: list support drifted")
        for index, (actual_value, expected_value) in enumerate(
            zip(actual, expected, strict=True)
        ):
            _assert_exact_value(
                actual_value, expected_value, f"{path}[{index}]"
            )
        return
    if actual != expected:
        raise P2CTrajectoryAuditError(f"{path}: value drifted")


def _assert_string_list(value: Any, path: str, *, allowed: tuple[str, ...]) -> None:
    if type(value) is not list or any(type(item) is not str for item in value):
        raise P2CTrajectoryAuditError(f"{path}: expected string list")
    if any(item not in allowed for item in value) or len(value) != len(set(value)):
        raise P2CTrajectoryAuditError(f"{path}: unsupported or duplicate item")


def _validate_acceptance(value: Any, scope: str, path: str) -> None:
    _exact_fields(value, _ACCEPTANCE_FIELDS, path)
    _assert_exact_value(value, _pending_acceptance(scope), path)


def _validate_frozen_contract(summary: dict[str, Any]) -> None:
    _assert_exact_value(summary["schema_version"], SCHEMA_VERSION, "schema_version")
    _assert_exact_value(summary["analysis_phase"], ANALYSIS_PHASE, "analysis_phase")
    _assert_exact_value(summary["report_role"], REPORT_ROLE, "report_role")
    _assert_exact_value(
        summary["validation_status"], {"status": VALID_STATUS}, "validation_status"
    )

    identity = _exact_fields(
        summary["input_identity"], _INPUT_IDENTITY_FIELDS, "input_identity"
    )
    expected_identity = {
        "base_commit": BASE_COMMIT,
        "identity_hash_mode": "sha256_after_crlf_to_lf_normalization",
        "raw_drift_mode": "exact_working_tree_sha256_pre_post_same_run",
        "identity_contract_digest": IDENTITY_CONTRACT_DIGEST,
        "identity_support_count": 43,
        "identity_rows": _identity_rows(),
        "p2a_summary_digest": p2b_ceiling.EXPECTED_P2A_SUMMARY_DIGEST,
        "p2a_json_sha256": p2b_ceiling.EXPECTED_P2A_JSON_SHA256,
        "p2a_markdown_sha256": p2b_ceiling.EXPECTED_P2A_MARKDOWN_SHA256,
        "p2b_summary_digest": EXPECTED_P2B_SUMMARY_DIGEST,
        "p2b_json_sha256": EXPECTED_P2B_JSON_SHA256,
        "p2b_markdown_sha256": EXPECTED_P2B_MARKDOWN_SHA256,
        "p2b_accepted_identity_count": 39,
        "implementation_file_sha256_lf": _implementation_identity(),
    }
    _assert_exact_value(identity, expected_identity, "input_identity")
    if identity_contract_digest(identity["identity_rows"]) != IDENTITY_CONTRACT_DIGEST:
        raise P2CTrajectoryAuditError("input identity rows differ from digest")

    freeze = _exact_fields(
        summary["pre_outcome_freeze"],
        _PRE_OUTCOME_FREEZE_FIELDS,
        "pre_outcome_freeze",
    )
    _assert_exact_value(
        freeze,
        {
            "specification_sha256": SPECIFICATION_SHA256,
            "review_prompt_sha256": SPECIFICATION_REVIEW_PROMPT_SHA256,
            "review_record_sha256": SPECIFICATION_REVIEW_RECORD_SHA256,
            "specification_review_verdict": "accept",
            "first_pair_index": 1,
            "first_variant_id": BUGGY_VARIANT_IDS[0],
            "first_policy_id": FORMAL_POLICY_IDS[0],
            "schema_version": SCHEMA_VERSION,
        },
        "pre_outcome_freeze",
    )
    boundary = _exact_fields(
        summary["execution_boundary"],
        _EXECUTION_BOUNDARY_FIELDS,
        "execution_boundary",
    )
    _assert_exact_value(
        boundary,
        {
            "first_execution_point": "P2A-BUG-001::fixed_checklist",
            "pair_execution_count": 60,
            "variant_context_count": 10,
            "policies_per_variant": 6,
            "raw_identity_pre_post_match": True,
            "implementation_raw_pre_post_match": True,
            "policy_runner_semantic_change": False,
        },
        "execution_boundary",
    )
    population = _exact_fields(
        summary["population"], _POPULATION_FIELDS, "population"
    )
    _assert_exact_value(
        population,
        {
            "variant_ids": list(BUGGY_VARIANT_IDS),
            "policy_ids": list(FORMAL_POLICY_IDS),
            "bucket_ids": list(BUCKET_IDS),
            "pair_order": "variant_major_then_policy_minor",
            "pair_count": 60,
            "overall_denominator": 60,
            "policy_denominator": 10,
            "variant_denominator": 6,
            "bucket_denominator": 12,
        },
        "population",
    )
    definitions = _exact_fields(
        summary["definitions"], _DEFINITION_FIELDS, "definitions"
    )
    _assert_exact_value(
        definitions,
        {
            "selection_axis": "whether an accepted P2b direct detector was selected",
            "budget_state_axis": "cost/executed-state feasibility at recorded decisions, not post-stop selectability",
            "termination_axis": "exact accepted runner stop reason, step, and cost",
            "axis_relationship": "overlapping descriptive observations, not mutually exclusive causal causes",
        },
        "definitions",
    )
    for field, scope in (
        ("software_acceptance", "software_conformance"),
        ("artifact_identity_acceptance", "versioned_artifact_identity"),
        ("result_acceptance", "descriptive_result"),
        ("documentation_acceptance", "public_result_documentation"),
    ):
        _validate_acceptance(summary[field], scope, field)
    _assert_exact_value(
        summary["limitations"],
        [
            "The audit covers only 60 fixed same-domain policy/variant pairs.",
            "Detector mapping is ground-truth-informed and unavailable to deployable policies.",
            "Terminal budget feasibility does not imply that the runner may select after a stop condition.",
            "Only reduced recorded decision states are preserved; full posteriors and action scores are excluded.",
        ],
        "limitations",
    )
    _assert_exact_value(
        summary["non_claims"],
        [
            "The selection, budget-state, and termination axes are not causal attributions.",
            "This audit does not rank policies or establish policy superiority, inferiority, or defects.",
            "This audit is not a new policy, counterfactual replay, sequence/DP ceiling, or optimality result.",
            "This fixed-cohort result does not establish inference, generalization, or production readiness.",
        ],
        "non_claims",
    )
    _assert_exact_value(
        summary["notes"],
        [
            "Accepted P2a/P2b inputs, policies, artifacts, and results remain unchanged.",
            "Artifact identity, descriptive result, and public documentation require separate post-merge acceptance.",
        ],
        "notes",
    )


def _validate_pair_semantics(row: dict[str, Any], index: int) -> None:
    path = f"pair_trajectories[{index - 1}]"
    if type(row["pair_index"]) is not int or row["pair_index"] != index:
        raise P2CTrajectoryAuditError("pair index drifted")
    for field in ("variant_id", "bucket_id", "policy_id", "stop_reason"):
        if type(row[field]) is not str:
            raise P2CTrajectoryAuditError(f"{path}.{field}: type drifted")
    if row["variant_id"] not in BUGGY_VARIANT_IDS or row["policy_id"] not in FORMAL_POLICY_IDS:
        raise P2CTrajectoryAuditError(f"{path}: variant or policy support drifted")
    for field in (
        "accepted_p2a_discovered_within_budget",
        "replayed_discovered_within_budget",
        "accepted_replay_agreement",
        "direct_detector_selected",
        "any_pre_action_direct_detector_budget_feasible",
        "all_pre_action_states_direct_detector_budget_feasible",
        "terminal_direct_detector_budget_feasible",
    ):
        if type(row[field]) is not bool:
            raise P2CTrajectoryAuditError(f"{path}.{field}: expected boolean")
    for field in ("minimum_detecting_cost", "step_count", "cumulative_cost"):
        if type(row[field]) is not int or row[field] < 0:
            raise P2CTrajectoryAuditError(f"{path}.{field}: expected nonnegative integer")

    expected_bucket, expected_detectors, expected_minimum = (
        _EXPECTED_DETECTOR_MAPPING[row["variant_id"]]
    )
    _assert_exact_value(row["bucket_id"], expected_bucket, f"{path}.bucket_id")
    _assert_exact_value(
        row["direct_detecting_action_ids"],
        list(expected_detectors),
        f"{path}.direct_detecting_action_ids",
    )
    _assert_exact_value(
        row["minimum_detecting_cost"],
        expected_minimum,
        f"{path}.minimum_detecting_cost",
    )
    expected_discovered = (row["variant_id"], row["policy_id"]) in (
        _EXPECTED_DISCOVERED_PAIRS
    )
    _assert_exact_value(
        row["accepted_p2a_discovered_within_budget"],
        expected_discovered,
        f"{path}.accepted_p2a_discovered_within_budget",
    )
    _assert_exact_value(
        row["replayed_discovered_within_budget"],
        expected_discovered,
        f"{path}.replayed_discovered_within_budget",
    )
    _assert_exact_value(row["accepted_replay_agreement"], True, f"{path}.accepted_replay_agreement")

    _assert_string_list(
        row["executed_action_ids"], f"{path}.executed_action_ids", allowed=ACTION_IDS
    )
    steps = row["pre_action_states"]
    if type(steps) is not list or not steps or row["step_count"] != len(steps):
        raise P2CTrajectoryAuditError(f"{path}: step support drifted")
    settings = P1BSettings(**p2a_evaluation._FIXED_SETTINGS)
    executed: list[str] = []
    cumulative_cost = 0
    any_observation_detected = False
    first_detector: tuple[str, int, int, bool] | None = None
    for step_index, step in enumerate(steps, start=1):
        step_path = f"{path}.pre_action_states[{step_index - 1}]"
        _exact_fields(step, _PRE_ACTION_FIELDS, step_path)
        for field in (
            "direct_detector_budget_feasible",
            "selected_action_is_direct_detector",
            "observation_bug_detected",
        ):
            if type(step[field]) is not bool:
                raise P2CTrajectoryAuditError(f"{step_path}.{field}: expected boolean")
        for field in (
            "decision_step",
            "cumulative_cost_before",
            "remaining_budget_before",
            "selected_action_cost",
            "cumulative_cost_after",
        ):
            if type(step[field]) is not int:
                raise P2CTrajectoryAuditError(f"{step_path}.{field}: expected integer")
        _assert_exact_value(step["decision_step"], step_index, f"{step_path}.decision_step")
        _assert_exact_value(step["executed_action_ids_before"], executed, f"{step_path}.executed_action_ids_before")
        _assert_exact_value(step["cumulative_cost_before"], cumulative_cost, f"{step_path}.cumulative_cost_before")
        remaining = settings.budget_limit - cumulative_cost
        _assert_exact_value(step["remaining_budget_before"], remaining, f"{step_path}.remaining_budget_before")
        feasible = _feasible_detectors(list(expected_detectors), executed, remaining)
        _assert_exact_value(step["feasible_direct_detector_ids"], feasible, f"{step_path}.feasible_direct_detector_ids")
        _assert_exact_value(step["direct_detector_budget_feasible"], bool(feasible), f"{step_path}.direct_detector_budget_feasible")
        action_id = step["selected_action_id"]
        if type(action_id) is not str or action_id not in ACTION_IDS or action_id in executed:
            raise P2CTrajectoryAuditError(f"{step_path}.selected_action_id: invalid action")
        action_cost = P1B_ACTION_SPECS[action_id].cost
        _assert_exact_value(step["selected_action_cost"], action_cost, f"{step_path}.selected_action_cost")
        if action_cost > remaining:
            raise P2CTrajectoryAuditError(f"{step_path}: selected action exceeds budget")
        is_detector = action_id in expected_detectors
        _assert_exact_value(step["selected_action_is_direct_detector"], is_detector, f"{step_path}.selected_action_is_direct_detector")
        if is_detector and step["observation_bug_detected"] is not True:
            raise P2CTrajectoryAuditError(f"{step_path}: selected detector did not detect")
        any_observation_detected = (
            any_observation_detected or step["observation_bug_detected"]
        )
        cumulative_cost += action_cost
        _assert_exact_value(step["cumulative_cost_after"], cumulative_cost, f"{step_path}.cumulative_cost_after")
        if is_detector and first_detector is None:
            first_detector = (action_id, step_index, cumulative_cost, True)
        executed.append(action_id)
    _assert_exact_value(row["executed_action_ids"], executed, f"{path}.executed_action_ids")
    _assert_exact_value(row["cumulative_cost"], cumulative_cost, f"{path}.cumulative_cost")
    _assert_exact_value(row["initial_feasible_direct_detector_ids"], steps[0]["feasible_direct_detector_ids"], f"{path}.initial_feasible_direct_detector_ids")
    _assert_exact_value(row["any_pre_action_direct_detector_budget_feasible"], any(step["direct_detector_budget_feasible"] for step in steps), f"{path}.any_pre_action_direct_detector_budget_feasible")
    _assert_exact_value(row["all_pre_action_states_direct_detector_budget_feasible"], all(step["direct_detector_budget_feasible"] for step in steps), f"{path}.all_pre_action_states_direct_detector_budget_feasible")
    terminal_feasible = _feasible_detectors(
        list(expected_detectors), executed, settings.budget_limit - cumulative_cost
    )
    _assert_exact_value(row["terminal_feasible_direct_detector_ids"], terminal_feasible, f"{path}.terminal_feasible_direct_detector_ids")
    _assert_exact_value(row["terminal_direct_detector_budget_feasible"], bool(terminal_feasible), f"{path}.terminal_direct_detector_budget_feasible")
    expected_first = first_detector or (None, None, None, None)
    for field, expected in zip(
        (
            "first_selected_direct_detector_action_id",
            "first_selected_direct_detector_step",
            "first_selected_direct_detector_cumulative_cost",
            "first_selected_direct_detector_observation_detected",
        ),
        expected_first,
        strict=True,
    ):
        _assert_exact_value(row[field], expected, f"{path}.{field}")
    _assert_exact_value(row["direct_detector_selected"], first_detector is not None, f"{path}.direct_detector_selected")
    _assert_exact_value(row["replayed_discovered_within_budget"], first_detector is not None, f"{path}.replayed_discovered_within_budget")
    _assert_exact_value(
        row["replayed_discovered_within_budget"],
        any_observation_detected,
        f"{path}.replayed_discovered_within_budget",
    )
    if row["stop_reason"] not in STOP_REASON_IDS:
        raise P2CTrajectoryAuditError("unknown stop reason")
    expected_stop_reason = (
        "budget_limit"
        if (row["variant_id"], row["policy_id"]) in _EXPECTED_BUDGET_STOP_PAIRS
        else "no_bug_probability_threshold"
    )
    _assert_exact_value(
        row["stop_reason"], expected_stop_reason, f"{path}.stop_reason"
    )
    if row["stop_reason"] == "budget_limit" and cumulative_cost < settings.budget_limit:
        raise P2CTrajectoryAuditError(f"{path}: budget stop before limit")
    if row["stop_reason"] == "max_steps" and len(steps) < settings.max_steps:
        raise P2CTrajectoryAuditError(f"{path}: max-step stop before limit")
    if row["stop_reason"] == "no_available_actions":
        remaining = settings.budget_limit - cumulative_cost
        if any(
            action_id not in executed
            and P1B_ACTION_SPECS[action_id].cost <= remaining
            for action_id in ACTION_IDS
        ):
            raise P2CTrajectoryAuditError(
                f"{path}: no-available-actions stop has feasible action"
            )
    if row["stop_reason"] == "no_available_actions":
        _assert_exact_value(row["terminal_common_stop_result"], None, f"{path}.terminal_common_stop_result")
    else:
        _assert_exact_value(row["terminal_common_stop_result"], row["stop_reason"], f"{path}.terminal_common_stop_result")
    if canonical_trace_digest(steps) != row["pair_trace_digest"]:
        raise P2CTrajectoryAuditError("pair trace digest mismatch")
    checks = _exact_fields(row["consistency_checks"], _CONSISTENCY_FIELDS, f"{path}.consistency_checks")
    _assert_exact_value(checks, {field: True for field in _CONSISTENCY_FIELDS}, f"{path}.consistency_checks")


def validate_audit_summary(summary: Any) -> dict[str, Any]:
    if type(summary) is not dict:
        raise P2CTrajectoryAuditError("summary must be object")
    status = summary.get("validation_status", {}).get("status")
    if status == INVALID_STATUS:
        _exact_fields(summary, _INVALID_TOP_FIELDS, "summary")
        _assert_exact_value(summary["schema_version"], SCHEMA_VERSION, "schema_version")
        _assert_exact_value(summary["analysis_phase"], ANALYSIS_PHASE, "analysis_phase")
        _assert_exact_value(summary["report_role"], REPORT_ROLE, "report_role")
        _assert_exact_value(
            summary["validation_status"],
            {"status": INVALID_STATUS},
            "validation_status",
        )
        if (
            type(summary["reason_codes"]) is not list
            or not summary["reason_codes"]
            or any(type(reason) is not str or not reason for reason in summary["reason_codes"])
        ):
            raise P2CTrajectoryAuditError("invalid summary requires reason code")
        if summary["input_identity"] is not None and type(summary["input_identity"]) is not dict:
            raise P2CTrajectoryAuditError("invalid summary input identity is malformed")
        for field, scope in (
            ("software_acceptance", "software_conformance"),
            ("artifact_identity_acceptance", "versioned_artifact_identity"),
            ("result_acceptance", "descriptive_result"),
            ("documentation_acceptance", "public_result_documentation"),
        ):
            _validate_acceptance(summary[field], scope, field)
        _assert_exact_value(
            summary["non_claims"],
            [
                "Invalid input or execution cannot support partial trajectory, aggregate, performance, or acceptance claims."
            ],
            "non_claims",
        )
        _assert_finite_and_private_safe(summary)
        return summary
    if status != VALID_STATUS:
        raise P2CTrajectoryAuditError("summary status is invalid")
    _exact_fields(summary, _VALID_TOP_FIELDS, "summary")
    _assert_finite_and_private_safe(summary)
    _validate_frozen_contract(summary)
    rows = summary["pair_trajectories"]
    if type(rows) is not list or len(rows) != 60:
        raise P2CTrajectoryAuditError("pair support is not exactly 60")
    expected_pairs = [
        (variant, policy)
        for variant in BUGGY_VARIANT_IDS
        for policy in FORMAL_POLICY_IDS
    ]
    observed_pairs: list[tuple[str, str]] = []
    for index, row in enumerate(rows, start=1):
        _exact_fields(row, _PAIR_FIELDS, f"pair_trajectories[{index - 1}]")
        _validate_pair_semantics(row, index)
        observed_pairs.append((row["variant_id"], row["policy_id"]))
    if observed_pairs != expected_pairs:
        raise P2CTrajectoryAuditError("pair support or order drifted")
    expected_axes = derive_aggregate_axes(rows)
    _assert_exact_value(summary["aggregate_axes"], expected_axes, "aggregate_axes")
    for axis in [expected_axes["overall"]] + [
        item["axes"]
        for key in ("by_policy", "by_variant", "by_bucket")
        for item in expected_axes[key]
    ]:
        _exact_fields(axis, _AXIS_FIELDS, "aggregate axis")
        if len(axis["selection_terminal_budget_stop_crosstab"]) != 24:
            raise P2CTrajectoryAuditError("cross-tab support is not 24")
    validate_portable_value(summary, "p2c_summary")
    return summary


def run_trajectory_audit(
    *, event_log: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    """Replay the exact accepted 60 pairs and return a validated reduced audit."""

    events = event_log if event_log is not None else []
    try:
        inputs = _load_inputs()
    except Exception as exc:  # noqa: BLE001 - fail-closed preflight boundary
        return _invalid_summary(type(exc).__name__)
    input_identity = _input_identity(inputs)
    events.append({"event": "p2c_identity_preflight_passed", "identity_count": 43})
    events.append(
        {
            "event": "p2c_first_pair_execution_started",
            "pair_index": 1,
            "variant_id": BUGGY_VARIANT_IDS[0],
            "policy_id": FORMAL_POLICY_IDS[0],
        }
    )
    try:
        p2b_inputs = inputs["p2b_inputs"]
        cases_by_action = p2a_evaluation._catalog_cases(p2b_inputs["bundle"])
        candidate_artifacts = {
            item["variant_id"]: item
            for item in p2b_inputs["artifact"]["candidates"]
        }
        accepted_by_pair = {
            (row["variant_id"], row["policy_id"]): row
            for row in inputs["saved_rows"]
        }
        rows: list[dict[str, Any]] = []
        pair_index = 0
        for candidate in BUGGY_CANDIDATES:
            variant = p2a_evaluation._candidate_variant(candidate)
            with p2a_evaluation._candidate_modules(candidate) as modules:
                for policy_id in FORMAL_POLICY_IDS:
                    pair_index += 1
                    result = p2a_evaluation._run_policy(
                        variant,
                        policy_id,
                        modules,
                        cases_by_action,
                        candidate_artifacts[candidate.variant_id],
                    )
                    rows.append(
                        _build_pair_row(
                            pair_index=pair_index,
                            variant=variant,
                            policy_id=policy_id,
                            result=result,
                            accepted_row=accepted_by_pair[(candidate.variant_id, policy_id)],
                            detector_mapping=inputs["p2b_mapping"][candidate.variant_id],
                        )
                    )
        events.append(
            {
                "event": "p2c_all_pairs_execution_completed",
                "pair_count": len(rows),
                "variant_count": 10,
                "policy_count": 6,
            }
        )
        post_rows, post_raw = _fresh_identity_snapshot()
        if post_rows != inputs["identity_rows"] or post_raw != inputs["raw_hashes"]:
            raise P2CTrajectoryAuditError("accepted identity changed during execution")
        if _implementation_identity() != inputs["implementation_identity"]:
            raise P2CTrajectoryAuditError("P2c implementation identity changed during execution")
        if _implementation_raw_snapshot() != inputs["implementation_raw_hashes"]:
            raise P2CTrajectoryAuditError("P2c implementation raw bytes changed during execution")
        summary = _build_valid_summary(inputs, rows)
    except Exception as exc:  # noqa: BLE001 - no partial claims after first pair
        return _invalid_summary(type(exc).__name__, input_identity=input_identity)
    events.append({"event": "p2c_summary_validated"})
    return summary


def record_artifacts_serialized(event_log: list[dict[str, Any]]) -> None:
    """Record serialization only after both artifact writes succeed."""

    event_log.append({"event": "p2c_artifacts_serialized"})


def walk_scalars(value: Any) -> Iterator[Any]:
    """Yield scalar values for defensive tests and scope scans."""

    if type(value) is dict:
        for child in value.values():
            yield from walk_scalars(child)
    elif type(value) is list:
        for child in value:
            yield from walk_scalars(child)
    else:
        yield value
