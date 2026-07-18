"""One-step relaxation of the accepted terminal no-bug stop predicate.

The P2d audit first replays each accepted P2c pair to its normal terminal
state. For the 52 preregistered candidate pairs only, it suppresses the
terminal ``no_bug_probability_threshold`` predicate once, evaluates the
remaining common-stop predicates, and executes at most one action selected by
the same frozen policy. This is a model-internal, non-causal, non-deployable
diagnostic; it is not a policy change or a multi-step continuation.
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

from bug_cause_inference.p1b import execution as p1b_execution
from bug_cause_inference.p1b import policies as p1b_policies
from bug_cause_inference.p1b.actions import P1B_ACTION_SPECS
from bug_cause_inference.p1b.dataset import LOCATION_CANDIDATES
from bug_cause_inference.p1b.models import (
    P1B_CAUSE_CATEGORIES,
    P1B_FIX_INTENT_CATEGORIES,
    P1BRunResult,
    P1BSettings,
    P1BStepTrace,
    rank_distribution,
    uniform_distribution,
    update_distribution,
)
from bug_cause_inference.p2a import evaluation as p2a_evaluation
from bug_cause_inference.p2a.adequacy import validate_portable_value
from bug_cause_inference.p2a.candidates import BUGGY_CANDIDATES
from bug_cause_inference.p2c import reports as p2c_reports
from bug_cause_inference.p2c import trajectory_audit as p2c_audit


SCHEMA_VERSION = "p2d_one_step_stop_relaxation_audit.v1"
ANALYSIS_PHASE = "p2d_one_step_stop_relaxation_audit"
REPORT_ROLE = (
    "analysis_only_fixed_input_ground_truth_informed_model_internal_one_step_"
    "non_causal_non_deployable_audit"
)
VALID_STATUS = "valid"
INVALID_STATUS = "invalid_inconclusive"

BASE_COMMIT = "990cd3444009f1ee92e8ec5c839fa2aead46a162"
SPECIFICATION_SHA256 = (
    "17298e6cca657a2a35c40613f4757a55f591206383114a6d047d9cca96061305"
)
SPECIFICATION_REVIEW_RECORD_SHA256 = (
    "98ff881a847d858381e0201b686dc9267bec7400b602e45270f04ad627fafaad"
)
IDENTITY_CONTRACT_DIGEST = (
    "7d127bcedb58f59487e16b3ec9c3a300753fe48108ef2d8a676b4c8b059217b8"
)
EXPECTED_P2C_JSON_SHA256 = (
    "1ebfb62edd5034fd57ea69e18c3eb647a3a8746946ecb98d80b66fa127d989d7"
)
EXPECTED_P2C_MARKDOWN_SHA256 = (
    "ee9bfda6a7b352ff770fa3025dff4d4feb94e4e36201d256a76de6d569286666"
)
EXPECTED_P2C_SUMMARY_DIGEST = (
    "3872257449d76453f6910b56d28f8e4fdf6c7bb7de30410b2d26335143c0392c"
)

FORMAL_POLICY_IDS = p2c_audit.FORMAL_POLICY_IDS
BUGGY_VARIANT_IDS = p2c_audit.BUGGY_VARIANT_IDS
BUCKET_IDS = p2c_audit.BUCKET_IDS
ACTION_IDS = p2c_audit.ACTION_IDS
TARGET_STOP_ID = "no_bug_probability_threshold"
RESIDUAL_STOP_IDS = (
    "bug_confidence_threshold",
    "budget_limit",
    "max_steps",
    "low_expected_utility",
)
OUTCOME_CLASS_IDS = (
    "not_applicable",
    "alternate_stop_before_action",
    "action_decision_reached",
)
NOT_APPLICABLE_REASON_IDS = (
    "direct_detector_already_selected",
    "terminal_direct_detector_not_budget_feasible",
    "terminal_stop_not_target_threshold",
)
POST_ACTION_STATUS_IDS = (
    "no_bug_probability_threshold",
    "bug_confidence_threshold",
    "budget_limit",
    "max_steps",
    "low_expected_utility",
    "one_step_horizon_reached",
)
INVALID_REASON_CODES = (
    "accepted_input_identity_error",
    "accepted_p2c_artifact_error",
    "population_eligibility_error",
    "terminal_replay_agreement_error",
    "intervention_contract_error",
    "payload_validation_error",
    "aggregate_validation_error",
    "serialization_agreement_error",
    "execution_drift_error",
    "unexpected_audit_error",
)

_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
_P2C_JSON_PATH = _REPOSITORY_ROOT / (
    "src/bug_cause_inference/p2c/artifacts/p2c_frozen_policy_trajectory_audit_v1.json"
)
_P2C_MARKDOWN_PATH = _REPOSITORY_ROOT / (
    "src/bug_cause_inference/p2c/artifacts/p2c_frozen_policy_trajectory_audit_v1.md"
)
_P2D_IMPLEMENTATION_PATHS = (
    "src/bug_cause_inference/p2d/__init__.py",
    "src/bug_cause_inference/p2d/stop_relaxation_audit.py",
    "src/bug_cause_inference/p2d/reports.py",
    "tests/test_p2d_stop_relaxation_audit.py",
    "tests/test_p2d_reports.py",
)

_EXPECTED_PAIR_RESULT_DIGESTS = (
    "fe9e8b71e42b4443eb1bfc74b779bcc680c1f995cf4ba36e7040a6389ce75c9c",
    "3fdaaa0d7aa9cc398a4971bcd2c4e5b5905e6006876cc35fe17a0a8a1688442f",
    "58cf227303a5d564ad293432b7128a1f757f8863e0acee089328961d82f2339e",
    "7d4b45066d718b31821e24514daa77909f9e659d489216fc64744194d6fac293",
    "41b37e7081caf7ef3c39d3544094b2d0adf8e58012975db483a4987a197769a6",
    "67444940d986508d0b392275f0efd28b5348318de18b1440a9baa6cd239eeb8f",
    "ebf19efb4e2901958b891b3c933ae09c2afa6e142fd8b5158a0dc9813236a405",
    "138c7165ed3dca86e07fcb49abf524487f299ac16a5d5c9506e6aed2c818813d",
    "64abd35bbc4d1519aa31113e1e0736b4cddc20771657995963dcc543c3895402",
    "6367044cd5ec1e6d90656718d331d04f1d626c70da9fe283ecb35875a8efad1b",
    "60820a547ee7afc89f371b712f59886e95ea66520d29ae7081b5154335021265",
    "686f1411018d6d231715df4f196b67c611e2af9f167876da382223f914d5fcd4",
    "e71607249b62d4668df3d9d6b1121817ffac699c81b4e3fd3d4aa97dc5fc4c7a",
    "b274e632f6abf484882e52b2d64ee542da0e6f962d3c972a7e38f2fa4cd014f2",
    "634d0041ceda9a1a1d56d0514ea09837e4472a50e91a09660a536fc6539f23dd",
    "a5ee9745ce4ecc27469347ed55334975eb908a75fb8f4b30b4831e333dd1a284",
    "d94dc2b3969054c5f062a748daf510c6a1aa6c9a48a6e8a51254d55ac8139181",
    "91f12f96d96aebf2e2e57bddffd29132ff8ce2e7640b1f11b1fc94053069165e",
    "28779eddaab93fa1eb0349a410fe5673b5f502c2b3eea07244f24b7b619b3b75",
    "e65e1a0478d8b468821cddc5578e5c47823a504bf89e836198b44be96dae2d06",
    "f74521c224136e1685d2d16cac202267355e612092ba575d217a3d5edc56faa4",
    "1c838ddda33f56f4ffac530dfceb5ebe1263e07538f91e15dfe7176686ee261b",
    "41185afe690cdffd775103bbbd3cf9ec098754a97eeca3d41a8587aae0798d19",
    "7f16c5fb4d8d0f6f3c625fb918176838e8fa72afc552d1c3e94981602f3cb170",
    "72b40c8cd1feafebdae959d1e415e2d6e345bb4b4a0585491de115ee51e91a79",
    "d1c4c3a95f60f05d8f673a3cf8f6d47d2dc4985f7e06a463c60fc8b28e02b635",
    "3e8436a157c3f4476c3622c1e5f6a250a025da084952766af756a48dbb22a9d8",
    "6650d05d49410e9230b3f329cc104d3bf55d3c40dcf7b705897b9e4d9fd5519d",
    "b46714b3df5b6de261dea0d2c3e2c025d064a7a8f9db8cd5fcc69f9c644cd4ce",
    "747a0431875aeef0a5a84d4f14c8eea43ec783cd48c9c87b1c681795563bfce3",
    "f085fcfbe52c73c84073caf2b9ec64bdf413cd62ea811c1ac7a17587bd5a5764",
    "6f65b85858b67773a20e27c1ab991b185c78d2a624e93f48c5a35ba5cf458f86",
    "5360659132fcd3d8ceed62af5e682f0dbaa84014dbd0dd8f1e753e52d7c621f2",
    "7092f9fb37998f5ad14628be1f03e61e394a423abc0eec3ae523f631c69548ea",
    "248ac2ddaeaf19ebe501e2c8ff0180ce4a66e3710bb89be2f81e5c344aad610a",
    "2f9c8b2437501d0d16cea4115b851d554677224cd5b159d0eb5b06cc36017f28",
    "d36f7ea1d4a4c99e14f4efc9785c3b788c55f59b6751c83a1066b3405856676d",
    "c9e8536e137fec4deadda1ca525ea1fd8965874ff4299b5b3dc0205bed73650b",
    "dc0b811436d44be8b92fd81f4328794f94ce872b46eac443dc2af95ef92b4f7c",
    "b05e154a118ad3fb83b3a49c89d5cdd14f8a7955099ac581919be6ddd95cb3ca",
    "be6cd3279b9cb2e16afd1e1578aeca52f277dd8d69466a7c6cbe1663690ce254",
    "15fa9000d2bcdfe09b3266dfdedee7983fa16275e70492e5fdac9f00eb8b5956",
    "2f3ba6c69e9fb1177111e2bc2a4b6066915a3cb7e2e4d97d71aad9e3cc839224",
    "650ae04e250bd544c2987dc1868241ac0f7c7d5ec068ce668350fdf3fea47bb6",
    "5c86680df2916e14fe981b1cb497626ea1d75eeb29c92b434afc0c001db52551",
    "c09244862d765a6a8795cce01a1673c76e986e5248f0a76fbef36a90264d4fb1",
    "f86af89bd2004cb421d69097c4c4f9afa2506b86d4cde58d4bf6c984543e3bdf",
    "ec40d3e290d6ee49afb360e231c10b49761d37213437f095165e844444646eeb",
    "ece3300bc4deaa925889bcf97b4cce735b0b942449b7dd93675b572c34a96f44",
    "1f5740611d85887d6cfa8fc92a8990404da9310ba447a41f6ac26f0e8a8ef2a0",
    "5ae24ecd976f1253cf5124b05a979d4fd89d22a287d175912b22d39f39ad2dfc",
    "8e521433b11db0b31fdec62ab8a6dfd7d2ff08059989b34dcb89f430d93d8735",
    "c166e036f230377bd9cadc2e5a19aba3f590f76b258865caddee9dd62c782e6b",
    "3fc5011263cdbb7ccaafd49286d87dca4efea2ba124e8941d87188eff6ad9ace",
    "b1e4224ab9de8f36a10409ebcf6ba1904ef56c69bb136b45087613f78b07daa9",
    "2263a24bfe13e523942792d295041c4af869a2cbc05dd62049c08b0c4bca057d",
    "0aa2d24ac907440941755bd966c36ce01a8cd149ac75b82c66589333cd4f9158",
    "251af4a81c3b30e592fe8e883574947ae99771b17e8b58aa27f628819dec2218",
    "2e8691a285dbbc94f1d9ba53ef192f0ae543673b1dae629d219da13fbdb8584f",
    "68779a782a388fee0e2f5ea0eb6127d76b0fadefb86031c5feb505fdb2d73800",
)
_P2C_IDENTITY_APPEND = (
    (
        "p2c_init_source",
        "src/bug_cause_inference/p2c/__init__.py",
        "9f5368cfffca746c19874a7f6cd68ff8e92ecacee1db7ded9dcd068bfd3eae59",
    ),
    (
        "p2c_trajectory_audit_source",
        "src/bug_cause_inference/p2c/trajectory_audit.py",
        "32d4387053fb277178d648a67e4d8e913e15c0b00bb7df2fa2ffbeb6b4ad7c17",
    ),
    (
        "p2c_reports_source",
        "src/bug_cause_inference/p2c/reports.py",
        "5fc076ca798f6e7cb023b090713f668cd99b665cd17d933e3bc594a587753d49",
    ),
    (
        "p2c_json",
        "src/bug_cause_inference/p2c/artifacts/"
        "p2c_frozen_policy_trajectory_audit_v1.json",
        EXPECTED_P2C_JSON_SHA256,
    ),
    (
        "p2c_markdown",
        "src/bug_cause_inference/p2c/artifacts/"
        "p2c_frozen_policy_trajectory_audit_v1.md",
        EXPECTED_P2C_MARKDOWN_SHA256,
    ),
    (
        "p2c_trajectory_tests",
        "tests/test_p2c_trajectory_audit.py",
        "bd1115bf689453541811c6703325b2333bcab12cccc314f89e82a6ee99843c61",
    ),
    (
        "p2c_reports_tests",
        "tests/test_p2c_reports.py",
        "1251cf34767e2068c4e83beb266866f59f1101efbdefc47dc4a2cef4e7573d24",
    ),
)

_ROW_FIELDS = (
    "pair_index",
    "variant_id",
    "bucket_id",
    "policy_id",
    "p2c_source_row_sha256",
    "replayed_p2c_row_sha256",
    "input_identity_checks",
    "terminal_state_reconstruction_agreement",
    "terminal_state_digest",
    "intervention_candidate",
    "not_applicable_reason",
    "original_terminal",
    "intervention",
    "row_consistency_checks",
)
_INPUT_CHECK_FIELDS = (
    "accepted_p2a_replay_agreement",
    "accepted_p2b_mapping_agreement",
    "accepted_p2c_row_agreement",
    "source_identity_preflight_passed",
)
_ORIGINAL_TERMINAL_FIELDS = (
    "direct_detector_selected",
    "replayed_discovered_within_budget",
    "terminal_step",
    "terminal_cumulative_cost",
    "terminal_remaining_budget",
    "stop_reason",
    "terminal_common_stop_result",
    "terminal_feasible_direct_detector_ids",
)
_INTERVENTION_FIELDS = (
    "suppressed_stop_id",
    "suppression_count",
    "residual_stop_predicates",
    "residual_stop_result",
    "outcome_class",
    "counterfactual_decision_step",
    "pre_action_remaining_budget",
    "action_execution",
)
_ACTION_EXECUTION_FIELDS = (
    "selected_action_id",
    "selected_action_cost",
    "selected_action_is_direct_detector",
    "observation_bug_detected",
    "post_action_cumulative_cost",
    "post_action_step",
    "post_action_common_stop_result",
    "horizon_status",
    "executed_action_count",
    "second_action_execution_count",
)
_ROW_CHECK_FIELDS = (
    "eligibility_truth_table_matches",
    "not_applicable_payload_separation",
    "normal_terminal_stop_reconstructed",
    "projected_p2c_row_matches_source",
    "suppression_is_target_only_and_once",
    "residual_stop_precedence_matches",
    "action_payload_matches_outcome_class",
    "action_execution_horizon_is_zero_or_one",
    "detector_label_observation_consistent",
    "policy_visibility_boundary_preserved",
)
_AXIS_FIELDS = (
    "support_pair_count",
    "intervention_candidate_count",
    "not_applicable_count",
    "not_applicable_reason_counts",
    "outcome_class_counts",
    "residual_stop_reason_counts",
    "action_execution_count",
    "direct_detector_selected_candidate_ratio",
    "direct_detector_selected_action_reached_ratio",
    "observation_detected_candidate_ratio",
    "observation_detected_action_reached_ratio",
    "selected_action_counts",
    "post_action_stop_or_horizon_counts",
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
    "pair_results",
    "aggregate_results",
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
_LOCAL_PATH_RE = re.compile(
    r"(?:[A-Za-z]:[\\/]|\\\\+[^\\/\s]+[\\/]+[^\\/\s]+|\bfile://[^\s]+|(?<![A-Za-z0-9_/\\])/(?!/)[^\s]+)",
    re.IGNORECASE,
)


class P2DStopRelaxationAuditError(ValueError):
    """Raised when the frozen P2d contract or a complete result is invalid."""


def _repository_path(relative_path: str) -> Path:
    path = Path(relative_path)
    if path.is_absolute() or ".." in path.parts:
        raise P2DStopRelaxationAuditError("identity path must be repository-relative")
    resolved = (_REPOSITORY_ROOT / path).resolve()
    try:
        resolved.relative_to(_REPOSITORY_ROOT)
    except ValueError as exc:
        raise P2DStopRelaxationAuditError("identity path escapes repository") from exc
    return resolved


def _hash_file(path: Path) -> tuple[str, str]:
    raw = path.read_bytes()
    canonical = raw.replace(b"\r\n", b"\n")
    return hashlib.sha256(canonical).hexdigest(), hashlib.sha256(raw).hexdigest()


def _identity_rows() -> list[dict[str, str]]:
    rows = deepcopy(p2c_audit._identity_rows())
    rows.extend(
        {"identity": identity, "path": path, "sha256_lf": expected}
        for identity, path, expected in _P2C_IDENTITY_APPEND
    )
    if len(rows) != 50 or len({row["identity"] for row in rows}) != 50:
        raise P2DStopRelaxationAuditError("50-file identity support drifted")
    return rows


def identity_contract_digest(rows: list[dict[str, str]]) -> str:
    payload = json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def _fresh_identity_snapshot() -> tuple[list[dict[str, str]], dict[str, str]]:
    rows = _identity_rows()
    if identity_contract_digest(rows) != IDENTITY_CONTRACT_DIGEST:
        raise P2DStopRelaxationAuditError("50-file identity contract digest drifted")
    raw_hashes: dict[str, str] = {}
    for row in rows:
        portable, raw = _hash_file(_repository_path(row["path"]))
        if portable != row["sha256_lf"]:
            raise P2DStopRelaxationAuditError(
                f"accepted input drifted: {row['identity']}"
            )
        raw_hashes[row["identity"]] = raw
    return rows, raw_hashes


def _implementation_identity() -> dict[str, str]:
    return {
        path: _hash_file(_repository_path(path))[0]
        for path in _P2D_IMPLEMENTATION_PATHS
    }


def _implementation_raw_snapshot() -> dict[str, str]:
    return {
        path: _hash_file(_repository_path(path))[1]
        for path in _P2D_IMPLEMENTATION_PATHS
    }


def _canonical_digest(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, allow_nan=False, separators=(",", ":")
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def _ratio(
    numerator: int,
    denominator: int,
    *,
    zero_reason: str,
) -> dict[str, Any]:
    if type(numerator) is not int or type(denominator) is not int:
        raise P2DStopRelaxationAuditError("ratio counts must be exact integers")
    if numerator < 0 or denominator < 0 or numerator > denominator:
        raise P2DStopRelaxationAuditError("ratio counts are outside support")
    if denominator == 0:
        return {
            "numerator": numerator,
            "denominator": denominator,
            "fraction": None,
            "decimal": None,
            "undefined_reason": zero_reason,
        }
    value = Fraction(numerator, denominator)
    return {
        "numerator": numerator,
        "denominator": denominator,
        "fraction": f"{value.numerator}/{value.denominator}",
        "decimal": format(float(value), ".12g"),
        "undefined_reason": None,
    }


def _pending_acceptance(scope: str) -> dict[str, Any]:
    return {"scope": scope, "accepted": False, "status": "pending_separate_acceptance"}


def _load_inputs() -> dict[str, Any]:
    identity_rows, raw_hashes = _fresh_identity_snapshot()
    p2c_summary = json.loads(_P2C_JSON_PATH.read_text(encoding="utf-8"))
    p2c_audit.validate_audit_summary(p2c_summary)
    recovered = p2c_reports.summary_from_markdown(
        _P2C_MARKDOWN_PATH.read_text(encoding="utf-8")
    )
    if recovered != p2c_summary:
        raise P2DStopRelaxationAuditError("accepted P2c artifact semantics drifted")
    if _canonical_digest(p2c_summary) != EXPECTED_P2C_SUMMARY_DIGEST:
        raise P2DStopRelaxationAuditError("accepted P2c summary digest drifted")
    p2c_inputs = p2c_audit._load_inputs()
    rows = p2c_summary["pair_trajectories"]
    expected_pairs = [
        (variant, policy)
        for variant in BUGGY_VARIANT_IDS
        for policy in FORMAL_POLICY_IDS
    ]
    if [(row["variant_id"], row["policy_id"]) for row in rows] != expected_pairs:
        raise P2DStopRelaxationAuditError("accepted P2c pair order drifted")
    candidate_count = sum(_is_candidate(row) for row in rows)
    if candidate_count != 52 or len(rows) - candidate_count != 8:
        raise P2DStopRelaxationAuditError("accepted P2c eligibility support drifted")
    first_candidate = next(row for row in rows if _is_candidate(row))
    if (
        first_candidate["pair_index"],
        first_candidate["variant_id"],
        first_candidate["policy_id"],
    ) != (5, "P2A-BUG-001", "cause_only_p1a_style"):
        raise P2DStopRelaxationAuditError("first intervention candidate drifted")
    return {
        "identity_rows": identity_rows,
        "raw_hashes": raw_hashes,
        "implementation_identity": _implementation_identity(),
        "implementation_raw_hashes": _implementation_raw_snapshot(),
        "p2c_summary": p2c_summary,
        "p2c_inputs": p2c_inputs,
    }


def _is_candidate(row: Mapping[str, Any]) -> bool:
    return (
        row["direct_detector_selected"] is False
        and row["terminal_direct_detector_budget_feasible"] is True
        and row["stop_reason"] == TARGET_STOP_ID
        and row["terminal_common_stop_result"] == TARGET_STOP_ID
    )


def _not_applicable_reason(row: Mapping[str, Any]) -> str | None:
    if _is_candidate(row):
        return None
    if row["direct_detector_selected"] is True:
        return "direct_detector_already_selected"
    if row["terminal_direct_detector_budget_feasible"] is False:
        return "terminal_direct_detector_not_budget_feasible"
    return "terminal_stop_not_target_threshold"


def _terminal_state_payload(state: Any) -> dict[str, Any]:
    return {
        "bug_presence_posterior": state.bug_presence,
        "cause_posterior": {
            key: state.cause_posterior[key] for key in P1B_CAUSE_CATEGORIES
        },
        "location_posterior": {
            key: state.location_posterior[key] for key in LOCATION_CANDIDATES
        },
        "fix_intent_posterior": {
            key: state.fix_intent_posterior[key] for key in P1B_FIX_INTENT_CATEGORIES
        },
        "executed_action_ids": list(state.executed_actions),
        "cumulative_cost": state.cumulative_cost,
        "current_step": state.current_step,
        "bug_detected": state.bug_detected,
    }


def terminal_state_digest(state: Any) -> str:
    return _canonical_digest(_terminal_state_payload(state))


def _run_policy_to_terminal(
    variant: Any,
    policy: str,
    modules: Mapping[str, Any],
    cases_by_action: Mapping[str, list[dict[str, Any]]],
    candidate_artifact: dict[str, Any],
) -> tuple[P1BRunResult, Any, random.Random]:
    """Replay accepted P2a semantics while retaining terminal execution state."""

    if policy not in FORMAL_POLICY_IDS:
        raise P2DStopRelaxationAuditError("policy is outside the frozen formal six")
    settings = P1BSettings(**p2a_evaluation._FIXED_SETTINGS)
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
    rng = random.Random(
        p1b_policies._stable_seed(variant.variant_id, settings.rng_seed)
    )
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
        observation = p2a_evaluation._run_frozen_action(
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
        state.cause_posterior = update_distribution(
            state.cause_posterior, observation.cause_scores
        )
        state.location_posterior = update_distribution(
            state.location_posterior, observation.location_scores
        )
        state.fix_intent_posterior = update_distribution(
            state.fix_intent_posterior, observation.fix_intent_scores
        )
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
    result = P1BRunResult(
        variant_id=variant.variant_id,
        is_buggy=variant.is_buggy,
        policy=policy,
        bug_detected=state.bug_detected,
        reproduction_input=reproduction_input,
        bug_presence_posterior=state.bug_presence,
        cause_posterior=state.cause_posterior,
        location_posterior=state.location_posterior,
        fix_intent_posterior=state.fix_intent_posterior,
        executed_actions=list(state.executed_actions),
        cumulative_cost=state.cumulative_cost,
        current_step=state.current_step,
        stop_reason=stop_reason,
        trace=trace,
        first_failure_cost=first_failure_cost,
        cost_to_true_cause_top1=None,
    )
    return result, state, rng


def _residual_stop_evaluation(
    state: Any, settings: P1BSettings
) -> tuple[list[dict[str, Any]], str | None]:
    remaining = settings.budget_limit - state.cumulative_cost
    scores = p1b_policies.score_actions(state, remaining)
    best = scores[0]["expected_utility_per_cost"] if scores else None
    cause_top = rank_distribution(state.cause_posterior)[0]
    location_top = rank_distribution(state.location_posterior)[0]
    fired = {
        "bug_confidence_threshold": (
            state.bug_detected
            and state.bug_presence >= settings.bug_presence_threshold
            and location_top[1] >= settings.location_top1_threshold
            and cause_top[1] >= settings.cause_top1_threshold
        ),
        "budget_limit": state.cumulative_cost >= settings.budget_limit,
        "max_steps": state.current_step >= settings.max_steps,
        "low_expected_utility": (
            best is not None and best < settings.min_expected_utility_per_cost
        ),
    }
    rows = [
        {"stop_id": stop_id, "fired": bool(fired[stop_id])}
        for stop_id in RESIDUAL_STOP_IDS
    ]
    result = next((row["stop_id"] for row in rows if row["fired"]), None)
    return rows, result


def _execute_one_action(
    *,
    variant: Any,
    policy_id: str,
    state: Any,
    rng: random.Random,
    modules: Mapping[str, Any],
    cases_by_action: Mapping[str, list[dict[str, Any]]],
    candidate_artifact: dict[str, Any],
    detector_ids: list[str],
) -> dict[str, Any]:
    settings = P1BSettings(**p2a_evaluation._FIXED_SETTINGS)
    remaining = settings.budget_limit - state.cumulative_cost
    action_id = p1b_policies.choose_action(policy_id, state, remaining, rng)
    if action_id is None:
        raise P2DStopRelaxationAuditError(
            "candidate action decision contradicted feasible detector support"
        )
    observation = p2a_evaluation._run_frozen_action(
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
    state.cause_posterior = update_distribution(
        state.cause_posterior, observation.cause_scores
    )
    state.location_posterior = update_distribution(
        state.location_posterior, observation.location_scores
    )
    state.fix_intent_posterior = update_distribution(
        state.fix_intent_posterior, observation.fix_intent_scores
    )
    post_remaining = settings.budget_limit - state.cumulative_cost
    post_scores = p1b_policies.score_actions(state, post_remaining)
    post_best = post_scores[0]["expected_utility_per_cost"] if post_scores else None
    post_stop = p1b_policies._check_stop(state, settings, post_best)
    horizon_status = (
        "normal_stop_after_action"
        if post_stop is not None
        else "one_step_horizon_reached"
    )
    return dict(
        zip(
            _ACTION_EXECUTION_FIELDS,
            (
                action_id,
                observation.cost,
                action_id in detector_ids,
                observation.bug_detected,
                state.cumulative_cost,
                state.current_step,
                post_stop,
                horizon_status,
                1,
                0,
            ),
            strict=True,
        )
    )


def _build_pair_result(
    *,
    pair_index: int,
    variant: Any,
    policy_id: str,
    source_row: Mapping[str, Any],
    accepted_row: Mapping[str, Any],
    detector_mapping: Mapping[str, Any],
    modules: Mapping[str, Any],
    cases_by_action: Mapping[str, list[dict[str, Any]]],
    candidate_artifact: dict[str, Any],
    event_log: list[dict[str, Any]],
) -> dict[str, Any]:
    result, state, rng = _run_policy_to_terminal(
        variant, policy_id, modules, cases_by_action, candidate_artifact
    )
    projected = p2c_audit._build_pair_row(
        pair_index=pair_index,
        variant=variant,
        policy_id=policy_id,
        result=result,
        accepted_row=accepted_row,
        detector_mapping=detector_mapping,
    )
    source_digest = _canonical_digest(source_row)
    projected_digest = _canonical_digest(projected)
    if projected != source_row or source_digest != projected_digest:
        raise P2DStopRelaxationAuditError("normal replay differs from accepted P2c row")
    settings = P1BSettings(**p2a_evaluation._FIXED_SETTINGS)
    terminal_remaining = settings.budget_limit - state.cumulative_cost
    terminal_scores = p1b_policies.score_actions(state, terminal_remaining)
    terminal_best = (
        terminal_scores[0]["expected_utility_per_cost"] if terminal_scores else None
    )
    terminal_stop = p1b_policies._check_stop(state, settings, terminal_best)
    if terminal_stop != source_row["terminal_common_stop_result"]:
        raise P2DStopRelaxationAuditError("normal terminal stop reconstruction drifted")
    candidate = _is_candidate(source_row)
    not_applicable = _not_applicable_reason(source_row)
    intervention: dict[str, Any] | None = None
    if candidate:
        if pair_index == 5:
            event_log.append(
                {
                    "event": "p2d_first_intervention_candidate_started",
                    "pair_index": pair_index,
                    "variant_id": variant.variant_id,
                    "policy_id": policy_id,
                }
            )
        residual_rows, residual_result = _residual_stop_evaluation(state, settings)
        outcome_class = (
            "alternate_stop_before_action"
            if residual_result is not None
            else "action_decision_reached"
        )
        action_execution = None
        if outcome_class == "action_decision_reached":
            action_execution = _execute_one_action(
                variant=variant,
                policy_id=policy_id,
                state=state,
                rng=rng,
                modules=modules,
                cases_by_action=cases_by_action,
                candidate_artifact=candidate_artifact,
                detector_ids=list(detector_mapping["direct_detecting_action_ids"]),
            )
        intervention = dict(
            zip(
                _INTERVENTION_FIELDS,
                (
                    TARGET_STOP_ID,
                    1,
                    residual_rows,
                    residual_result,
                    outcome_class,
                    source_row["step_count"] + 1,
                    terminal_remaining,
                    action_execution,
                ),
                strict=True,
            )
        )
    original_terminal = dict(
        zip(
            _ORIGINAL_TERMINAL_FIELDS,
            (
                source_row["direct_detector_selected"],
                source_row["replayed_discovered_within_budget"],
                source_row["step_count"],
                source_row["cumulative_cost"],
                terminal_remaining,
                source_row["stop_reason"],
                source_row["terminal_common_stop_result"],
                list(source_row["terminal_feasible_direct_detector_ids"]),
            ),
            strict=True,
        )
    )
    input_checks = {field: True for field in _INPUT_CHECK_FIELDS}
    row_checks = {field: True for field in _ROW_CHECK_FIELDS}
    return dict(
        zip(
            _ROW_FIELDS,
            (
                pair_index,
                variant.variant_id,
                detector_mapping["bucket_id"],
                policy_id,
                source_digest,
                projected_digest,
                input_checks,
                True,
                terminal_state_digest(
                    p1b_policies._State(
                        bug_presence=result.bug_presence_posterior,
                        cause_posterior=dict(result.cause_posterior),
                        location_posterior=dict(result.location_posterior),
                        fix_intent_posterior=dict(result.fix_intent_posterior),
                        executed_actions=list(result.executed_actions),
                        cumulative_cost=result.cumulative_cost,
                        current_step=result.current_step,
                        bug_detected=result.bug_detected,
                        execution_context=None,
                    )
                ),
                candidate,
                not_applicable,
                original_terminal,
                intervention,
                row_checks,
            ),
            strict=True,
        )
    )


def _axis_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    support = len(rows)
    candidates = [row for row in rows if row["intervention_candidate"]]
    action_reached = [
        row
        for row in candidates
        if row["intervention"]["outcome_class"] == "action_decision_reached"
    ]
    actions = [row["intervention"]["action_execution"] for row in action_reached]
    candidate_selected = sum(
        item["selected_action_is_direct_detector"] for item in actions
    )
    candidate_detected = sum(item["observation_bug_detected"] for item in actions)
    reason_counts = {
        reason: sum(row["not_applicable_reason"] == reason for row in rows)
        for reason in NOT_APPLICABLE_REASON_IDS
    }
    outcome_counts = {
        "not_applicable": support - len(candidates),
        "alternate_stop_before_action": sum(
            row["intervention"]["outcome_class"] == "alternate_stop_before_action"
            for row in candidates
        ),
        "action_decision_reached": len(action_reached),
    }
    residual_counts = {
        reason: sum(
            row["intervention"]["residual_stop_result"] == reason for row in candidates
        )
        for reason in RESIDUAL_STOP_IDS
    }
    residual_counts["none"] = sum(
        row["intervention"]["residual_stop_result"] is None for row in candidates
    )
    action_counts = {
        action_id: sum(item["selected_action_id"] == action_id for item in actions)
        for action_id in ACTION_IDS
    }
    post_counts = {
        status: sum(
            (
                item["post_action_common_stop_result"]
                if item["post_action_common_stop_result"] is not None
                else item["horizon_status"]
            )
            == status
            for item in actions
        )
        for status in POST_ACTION_STATUS_IDS
    }
    return dict(
        zip(
            _AXIS_FIELDS,
            (
                support,
                len(candidates),
                support - len(candidates),
                reason_counts,
                outcome_counts,
                residual_counts,
                len(actions),
                _ratio(
                    candidate_selected,
                    len(candidates),
                    zero_reason="no_intervention_candidate_support",
                ),
                _ratio(
                    candidate_selected,
                    len(action_reached),
                    zero_reason="no_action_decision_reached_support",
                ),
                _ratio(
                    candidate_detected,
                    len(candidates),
                    zero_reason="no_intervention_candidate_support",
                ),
                _ratio(
                    candidate_detected,
                    len(action_reached),
                    zero_reason="no_action_decision_reached_support",
                ),
                action_counts,
                post_counts,
            ),
            strict=True,
        )
    )


def derive_aggregate_results(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "overall": _axis_summary(rows),
        "by_policy": [
            {
                "policy_id": policy,
                "axes": _axis_summary(
                    [row for row in rows if row["policy_id"] == policy]
                ),
            }
            for policy in FORMAL_POLICY_IDS
        ],
        "by_variant": [
            {
                "variant_id": variant,
                "axes": _axis_summary(
                    [row for row in rows if row["variant_id"] == variant]
                ),
            }
            for variant in BUGGY_VARIANT_IDS
        ],
        "by_bucket": [
            {
                "bucket_id": bucket,
                "axes": _axis_summary(
                    [row for row in rows if row["bucket_id"] == bucket]
                ),
            }
            for bucket in BUCKET_IDS
        ],
    }


def _input_identity(inputs: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "base_commit": BASE_COMMIT,
        "identity_hash_mode": "sha256_after_crlf_to_lf_normalization",
        "raw_drift_mode": "exact_working_tree_sha256_pre_post_same_run",
        "identity_contract_digest": IDENTITY_CONTRACT_DIGEST,
        "identity_support_count": 50,
        "identity_rows": deepcopy(inputs["identity_rows"]),
        "p2a_summary_digest": p2c_audit.p2b_ceiling.EXPECTED_P2A_SUMMARY_DIGEST,
        "p2a_json_sha256": p2c_audit.p2b_ceiling.EXPECTED_P2A_JSON_SHA256,
        "p2a_markdown_sha256": p2c_audit.p2b_ceiling.EXPECTED_P2A_MARKDOWN_SHA256,
        "p2b_summary_digest": p2c_audit.EXPECTED_P2B_SUMMARY_DIGEST,
        "p2b_json_sha256": p2c_audit.EXPECTED_P2B_JSON_SHA256,
        "p2b_markdown_sha256": p2c_audit.EXPECTED_P2B_MARKDOWN_SHA256,
        "p2c_summary_digest": EXPECTED_P2C_SUMMARY_DIGEST,
        "p2c_json_sha256": EXPECTED_P2C_JSON_SHA256,
        "p2c_markdown_sha256": EXPECTED_P2C_MARKDOWN_SHA256,
        "p2c_pair_count": 60,
        "p2c_intervention_candidate_count": 52,
        "implementation_file_sha256_lf": deepcopy(inputs["implementation_identity"]),
    }


def _expected_input_identity() -> dict[str, Any]:
    return {
        "base_commit": BASE_COMMIT,
        "identity_hash_mode": "sha256_after_crlf_to_lf_normalization",
        "raw_drift_mode": "exact_working_tree_sha256_pre_post_same_run",
        "identity_contract_digest": IDENTITY_CONTRACT_DIGEST,
        "identity_support_count": 50,
        "identity_rows": _identity_rows(),
        "p2a_summary_digest": p2c_audit.p2b_ceiling.EXPECTED_P2A_SUMMARY_DIGEST,
        "p2a_json_sha256": p2c_audit.p2b_ceiling.EXPECTED_P2A_JSON_SHA256,
        "p2a_markdown_sha256": p2c_audit.p2b_ceiling.EXPECTED_P2A_MARKDOWN_SHA256,
        "p2b_summary_digest": p2c_audit.EXPECTED_P2B_SUMMARY_DIGEST,
        "p2b_json_sha256": p2c_audit.EXPECTED_P2B_JSON_SHA256,
        "p2b_markdown_sha256": p2c_audit.EXPECTED_P2B_MARKDOWN_SHA256,
        "p2c_summary_digest": EXPECTED_P2C_SUMMARY_DIGEST,
        "p2c_json_sha256": EXPECTED_P2C_JSON_SHA256,
        "p2c_markdown_sha256": EXPECTED_P2C_MARKDOWN_SHA256,
        "p2c_pair_count": 60,
        "p2c_intervention_candidate_count": 52,
        "implementation_file_sha256_lf": _implementation_identity(),
    }


def _expected_freeze() -> dict[str, Any]:
    return {
        "specification_sha256": SPECIFICATION_SHA256,
        "review_record_sha256": SPECIFICATION_REVIEW_RECORD_SHA256,
        "specification_review_verdict": "accept",
        "identity_contract_digest": IDENTITY_CONTRACT_DIGEST,
        "first_original_replay_pair_index": 1,
        "first_intervention_pair_index": 5,
        "schema_version": SCHEMA_VERSION,
    }


def _expected_execution_boundary() -> dict[str, Any]:
    return {
        "original_replay_count": 60,
        "intervention_candidate_count": 52,
        "not_applicable_count": 8,
        "suppressed_stop_id": TARGET_STOP_ID,
        "maximum_counterfactual_action_count_per_pair": 1,
        "second_action_execution_count": 0,
        "raw_identity_pre_post_match": True,
        "implementation_raw_pre_post_match": True,
        "accepted_runner_semantic_change": False,
    }


def _expected_population() -> dict[str, Any]:
    return {
        "variant_ids": list(BUGGY_VARIANT_IDS),
        "policy_ids": list(FORMAL_POLICY_IDS),
        "bucket_ids": list(BUCKET_IDS),
        "pair_order": "variant_major_then_policy_minor",
        "pair_count": 60,
        "intervention_candidate_count": 52,
        "not_applicable_count": 8,
        "first_intervention_pair_index": 5,
    }


def _expected_definitions() -> dict[str, Any]:
    return {
        "intervention_candidate": (
            "P2c detector not selected, terminal detector feasible, and both stop fields equal the no-bug threshold"
        ),
        "intervention": (
            "suppress only the terminal no-bug probability predicate once, then execute at most one frozen-policy action"
        ),
        "policy_visibility": (
            "policy, retained state, remaining budget, and RNG only; detector mapping is post-selection audit labeling"
        ),
        "horizon": "zero or one counterfactual action; never a second action",
    }


def _build_valid_summary(
    inputs: Mapping[str, Any], rows: list[dict[str, Any]]
) -> dict[str, Any]:
    summary = {
        "schema_version": SCHEMA_VERSION,
        "analysis_phase": ANALYSIS_PHASE,
        "report_role": REPORT_ROLE,
        "validation_status": {"status": VALID_STATUS},
        "input_identity": _input_identity(inputs),
        "pre_outcome_freeze": _expected_freeze(),
        "execution_boundary": _expected_execution_boundary(),
        "population": _expected_population(),
        "definitions": _expected_definitions(),
        "pair_results": rows,
        "aggregate_results": derive_aggregate_results(rows),
        "software_acceptance": _pending_acceptance("software_conformance"),
        "artifact_identity_acceptance": _pending_acceptance(
            "versioned_artifact_identity"
        ),
        "result_acceptance": _pending_acceptance("descriptive_result"),
        "documentation_acceptance": _pending_acceptance("public_result_documentation"),
        "limitations": [
            "The audit covers 60 fixed same-domain pairs and 52 fixed intervention candidates.",
            "The detector mapping is ground-truth-informed and unavailable to deployable policies.",
            "The counterfactual is model-internal and ends after zero or one action.",
            "The artifact preserves reduced audit payloads rather than complete execution contexts.",
        ],
        "non_claims": [
            "The audit does not establish that the threshold causally produced a miss or is a policy defect.",
            "The audit does not rank, tune, improve, or recommend a deployable policy.",
            "One-step selection or non-selection does not establish multi-step reachability or impossibility.",
            "The audit is not sequence search, dynamic programming, optimality, inference, generalization, or production readiness.",
        ],
        "notes": [
            "Accepted P2a/P2b/P2c inputs, policies, tests, artifacts, and results remain unchanged.",
            "Software conformance, artifact identity, descriptive result, and public documentation remain separate decisions.",
        ],
    }
    return validate_audit_summary(summary)


def _invalid_summary(
    reason_code: str,
    *,
    input_identity: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if reason_code not in INVALID_REASON_CODES:
        reason_code = "unexpected_audit_error"
    summary = {
        "schema_version": SCHEMA_VERSION,
        "analysis_phase": ANALYSIS_PHASE,
        "report_role": REPORT_ROLE,
        "validation_status": {"status": INVALID_STATUS},
        "reason_codes": [reason_code],
        "input_identity": deepcopy(input_identity),
        "software_acceptance": _pending_acceptance("software_conformance"),
        "artifact_identity_acceptance": _pending_acceptance(
            "versioned_artifact_identity"
        ),
        "result_acceptance": _pending_acceptance("descriptive_result"),
        "documentation_acceptance": _pending_acceptance("public_result_documentation"),
        "non_claims": [
            "Invalid input or execution cannot support partial P2d rows, aggregates, policy-performance, causal, deployment, or acceptance claims."
        ],
    }
    return validate_audit_summary(summary)


def _exact_fields(value: Any, fields: tuple[str, ...], path: str) -> dict[str, Any]:
    if type(value) is not dict or tuple(value) != fields:
        raise P2DStopRelaxationAuditError(
            f"{path}: fields missing, extra, or reordered"
        )
    return value


def _assert_exact(actual: Any, expected: Any, path: str) -> None:
    if type(actual) is not type(expected):
        raise P2DStopRelaxationAuditError(f"{path}: type drifted")
    if type(expected) is dict:
        if tuple(actual) != tuple(expected):
            raise P2DStopRelaxationAuditError(f"{path}: fields or order drifted")
        for key in expected:
            _assert_exact(actual[key], expected[key], f"{path}.{key}")
        return
    if type(expected) is list:
        if len(actual) != len(expected):
            raise P2DStopRelaxationAuditError(f"{path}: list support drifted")
        for index, (left, right) in enumerate(zip(actual, expected, strict=True)):
            _assert_exact(left, right, f"{path}[{index}]")
        return
    if actual != expected:
        raise P2DStopRelaxationAuditError(f"{path}: value drifted")


def _assert_safe(value: Any) -> None:
    if type(value) is dict:
        for child in value.values():
            _assert_safe(child)
    elif type(value) is list:
        for child in value:
            _assert_safe(child)
    elif type(value) is float and not math.isfinite(value):
        raise P2DStopRelaxationAuditError("summary contains non-finite value")
    elif type(value) is str and _LOCAL_PATH_RE.search(value):
        raise P2DStopRelaxationAuditError("summary contains private absolute path")


def _validate_ratio(value: Any, numerator: int, denominator: int, reason: str) -> None:
    _assert_exact(value, _ratio(numerator, denominator, zero_reason=reason), "ratio")


def _validate_row(
    row: dict[str, Any], index: int, source_row: Mapping[str, Any]
) -> None:
    _exact_fields(row, _ROW_FIELDS, f"pair_results[{index - 1}]")
    expected_identity_checks = {field: True for field in _INPUT_CHECK_FIELDS}
    expected_row_checks = {field: True for field in _ROW_CHECK_FIELDS}
    _assert_exact(row["pair_index"], index, "pair_index")
    _assert_exact(row["variant_id"], source_row["variant_id"], "variant_id")
    _assert_exact(row["bucket_id"], source_row["bucket_id"], "bucket_id")
    _assert_exact(row["policy_id"], source_row["policy_id"], "policy_id")
    source_digest = _canonical_digest(source_row)
    _assert_exact(row["p2c_source_row_sha256"], source_digest, "p2c_source_row_sha256")
    _assert_exact(
        row["replayed_p2c_row_sha256"], source_digest, "replayed_p2c_row_sha256"
    )
    _assert_exact(
        row["input_identity_checks"], expected_identity_checks, "input_identity_checks"
    )
    _assert_exact(
        row["terminal_state_reconstruction_agreement"], True, "terminal agreement"
    )
    if type(row["terminal_state_digest"]) is not str or not re.fullmatch(
        r"[0-9a-f]{64}", row["terminal_state_digest"]
    ):
        raise P2DStopRelaxationAuditError("terminal state digest is malformed")
    candidate = _is_candidate(source_row)
    _assert_exact(row["intervention_candidate"], candidate, "intervention_candidate")
    _assert_exact(
        row["not_applicable_reason"],
        _not_applicable_reason(source_row),
        "not_applicable_reason",
    )
    expected_terminal = {
        "direct_detector_selected": source_row["direct_detector_selected"],
        "replayed_discovered_within_budget": source_row[
            "replayed_discovered_within_budget"
        ],
        "terminal_step": source_row["step_count"],
        "terminal_cumulative_cost": source_row["cumulative_cost"],
        "terminal_remaining_budget": 12 - source_row["cumulative_cost"],
        "stop_reason": source_row["stop_reason"],
        "terminal_common_stop_result": source_row["terminal_common_stop_result"],
        "terminal_feasible_direct_detector_ids": list(
            source_row["terminal_feasible_direct_detector_ids"]
        ),
    }
    _assert_exact(row["original_terminal"], expected_terminal, "original_terminal")
    intervention = row["intervention"]
    if not candidate:
        _assert_exact(intervention, None, "intervention")
    else:
        _exact_fields(intervention, _INTERVENTION_FIELDS, "intervention")
        _assert_exact(
            intervention["suppressed_stop_id"], TARGET_STOP_ID, "suppressed_stop_id"
        )
        _assert_exact(intervention["suppression_count"], 1, "suppression_count")
        residual = intervention["residual_stop_predicates"]
        if type(residual) is not list or len(residual) != 4:
            raise P2DStopRelaxationAuditError("residual stop support drifted")
        for item, stop_id in zip(residual, RESIDUAL_STOP_IDS, strict=True):
            _assert_exact(tuple(item), ("stop_id", "fired"), "residual fields")
            _assert_exact(item["stop_id"], stop_id, "residual stop id")
            if type(item["fired"]) is not bool:
                raise P2DStopRelaxationAuditError("residual predicate type drifted")
        expected_residual = next(
            (item["stop_id"] for item in residual if item["fired"]), None
        )
        _assert_exact(
            intervention["residual_stop_result"], expected_residual, "residual result"
        )
        expected_class = (
            "alternate_stop_before_action"
            if expected_residual
            else "action_decision_reached"
        )
        _assert_exact(intervention["outcome_class"], expected_class, "outcome class")
        _assert_exact(
            intervention["counterfactual_decision_step"],
            source_row["step_count"] + 1,
            "decision step",
        )
        _assert_exact(
            intervention["pre_action_remaining_budget"],
            12 - source_row["cumulative_cost"],
            "remaining budget",
        )
        action = intervention["action_execution"]
        if expected_class == "alternate_stop_before_action":
            _assert_exact(action, None, "action execution")
        else:
            _exact_fields(action, _ACTION_EXECUTION_FIELDS, "action_execution")
            action_id = action["selected_action_id"]
            if type(action_id) is not str or action_id not in ACTION_IDS:
                raise P2DStopRelaxationAuditError("selected action is invalid")
            _assert_exact(
                action["selected_action_cost"],
                P1B_ACTION_SPECS[action_id].cost,
                "action cost",
            )
            _assert_exact(
                action["selected_action_is_direct_detector"],
                action_id in source_row["direct_detecting_action_ids"],
                "detector label",
            )
            if type(action["observation_bug_detected"]) is not bool:
                raise P2DStopRelaxationAuditError("observation detection type drifted")
            if (
                action["selected_action_is_direct_detector"]
                and not action["observation_bug_detected"]
            ):
                raise P2DStopRelaxationAuditError("selected detector did not detect")
            _assert_exact(
                action["post_action_cumulative_cost"],
                source_row["cumulative_cost"] + action["selected_action_cost"],
                "post cost",
            )
            _assert_exact(
                action["post_action_step"], source_row["step_count"] + 1, "post step"
            )
            post_stop = action["post_action_common_stop_result"]
            if (
                post_stop is not None
                and post_stop not in p2c_audit.STOP_REASON_IDS[:-1]
            ):
                raise P2DStopRelaxationAuditError("post-action stop reason is invalid")
            expected_horizon = (
                "normal_stop_after_action" if post_stop else "one_step_horizon_reached"
            )
            _assert_exact(action["horizon_status"], expected_horizon, "horizon status")
            _assert_exact(action["executed_action_count"], 1, "executed action count")
            _assert_exact(
                action["second_action_execution_count"], 0, "second action count"
            )
    _assert_exact(row["row_consistency_checks"], expected_row_checks, "row checks")
    _assert_exact(
        _canonical_digest(row),
        _EXPECTED_PAIR_RESULT_DIGESTS[index - 1],
        f"pair_results[{index - 1}] authoritative digest",
    )


def validate_audit_summary(summary: Any) -> dict[str, Any]:
    if type(summary) is not dict:
        raise P2DStopRelaxationAuditError("summary must be object")
    _assert_safe(summary)
    status = summary.get("validation_status", {}).get("status")
    if status == INVALID_STATUS:
        _exact_fields(summary, _INVALID_TOP_FIELDS, "summary")
        _assert_exact(summary["schema_version"], SCHEMA_VERSION, "schema")
        _assert_exact(summary["analysis_phase"], ANALYSIS_PHASE, "phase")
        _assert_exact(summary["report_role"], REPORT_ROLE, "role")
        codes = summary["reason_codes"]
        if type(codes) is not list or not codes or len(codes) != len(set(codes)):
            raise P2DStopRelaxationAuditError("invalid summary reason codes malformed")
        if any(
            type(code) is not str or code not in INVALID_REASON_CODES for code in codes
        ):
            raise P2DStopRelaxationAuditError("invalid summary reason code unsupported")
        if summary["input_identity"] is not None:
            _assert_exact(
                summary["input_identity"],
                _expected_input_identity(),
                "invalid input identity",
            )
        for field, scope in (
            ("software_acceptance", "software_conformance"),
            ("artifact_identity_acceptance", "versioned_artifact_identity"),
            ("result_acceptance", "descriptive_result"),
            ("documentation_acceptance", "public_result_documentation"),
        ):
            _assert_exact(summary[field], _pending_acceptance(scope), field)
        _assert_exact(
            summary["non_claims"],
            [
                "Invalid input or execution cannot support partial P2d rows, aggregates, policy-performance, causal, deployment, or acceptance claims."
            ],
            "invalid non-claims",
        )
        return summary
    if status != VALID_STATUS:
        raise P2DStopRelaxationAuditError("summary status is invalid")
    _exact_fields(summary, _VALID_TOP_FIELDS, "summary")
    _assert_exact(summary["schema_version"], SCHEMA_VERSION, "schema")
    _assert_exact(summary["analysis_phase"], ANALYSIS_PHASE, "phase")
    _assert_exact(summary["report_role"], REPORT_ROLE, "role")
    _assert_exact(
        summary["input_identity"], _expected_input_identity(), "input_identity"
    )
    _assert_exact(
        summary["pre_outcome_freeze"], _expected_freeze(), "pre_outcome_freeze"
    )
    _assert_exact(
        summary["execution_boundary"],
        _expected_execution_boundary(),
        "execution_boundary",
    )
    _assert_exact(summary["population"], _expected_population(), "population")
    _assert_exact(summary["definitions"], _expected_definitions(), "definitions")
    for field, scope in (
        ("software_acceptance", "software_conformance"),
        ("artifact_identity_acceptance", "versioned_artifact_identity"),
        ("result_acceptance", "descriptive_result"),
        ("documentation_acceptance", "public_result_documentation"),
    ):
        _assert_exact(summary[field], _pending_acceptance(scope), field)
    p2c_summary = json.loads(_P2C_JSON_PATH.read_text(encoding="utf-8"))
    p2c_audit.validate_audit_summary(p2c_summary)
    source_rows = p2c_summary["pair_trajectories"]
    rows = summary["pair_results"]
    if type(rows) is not list or len(rows) != 60:
        raise P2DStopRelaxationAuditError("pair support is not exactly 60")
    for index, (row, source_row) in enumerate(
        zip(rows, source_rows, strict=True), start=1
    ):
        _validate_row(row, index, source_row)
    aggregates = derive_aggregate_results(rows)
    _assert_exact(summary["aggregate_results"], aggregates, "aggregate_results")
    overall = aggregates["overall"]
    if (
        overall["intervention_candidate_count"] != 52
        or overall["not_applicable_count"] != 8
    ):
        raise P2DStopRelaxationAuditError("overall eligibility support drifted")
    if (
        overall["outcome_class_counts"]["alternate_stop_before_action"]
        + overall["outcome_class_counts"]["action_decision_reached"]
        != 52
    ):
        raise P2DStopRelaxationAuditError("candidate partition drifted")
    if (
        overall["action_execution_count"]
        != overall["outcome_class_counts"]["action_decision_reached"]
    ):
        raise P2DStopRelaxationAuditError("action execution count drifted")
    validate_portable_value(summary, "p2d_summary")
    return summary


def run_stop_relaxation_audit(
    *, event_log: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    """Replay all 60 pairs and apply the frozen intervention to 52 candidates."""

    events = event_log if event_log is not None else []
    events.append(
        {
            "event": "p2d_specification_frozen",
            "specification_sha256": SPECIFICATION_SHA256,
        }
    )
    events.append(
        {
            "event": "p2d_specification_review_accepted",
            "review_record_sha256": SPECIFICATION_REVIEW_RECORD_SHA256,
        }
    )
    try:
        inputs = _load_inputs()
    except Exception:  # noqa: BLE001 - fail-closed preflight boundary
        events.append(
            {
                "event": "p2d_preflight_failed",
                "reason_code": "accepted_input_identity_error",
            }
        )
        return _invalid_summary("accepted_input_identity_error")
    input_identity = _input_identity(inputs)
    events.append({"event": "p2d_identity_preflight_passed", "identity_count": 50})
    events.append(
        {
            "event": "p2d_original_replay_started",
            "pair_index": 1,
            "variant_id": BUGGY_VARIANT_IDS[0],
            "policy_id": FORMAL_POLICY_IDS[0],
        }
    )
    try:
        p2c_inputs = inputs["p2c_inputs"]
        cases_by_action = p2a_evaluation._catalog_cases(
            p2c_inputs["p2b_inputs"]["bundle"]
        )
        candidate_artifacts = {
            item["variant_id"]: item
            for item in p2c_inputs["p2b_inputs"]["artifact"]["candidates"]
        }
        accepted_by_pair = {
            (row["variant_id"], row["policy_id"]): row
            for row in p2c_inputs["saved_rows"]
        }
        source_by_pair = {
            (row["variant_id"], row["policy_id"]): row
            for row in inputs["p2c_summary"]["pair_trajectories"]
        }
        rows: list[dict[str, Any]] = []
        pair_index = 0
        for candidate in BUGGY_CANDIDATES:
            variant = p2a_evaluation._candidate_variant(candidate)
            with p2a_evaluation._candidate_modules(candidate) as modules:
                for policy_id in FORMAL_POLICY_IDS:
                    pair_index += 1
                    pair = (candidate.variant_id, policy_id)
                    rows.append(
                        _build_pair_result(
                            pair_index=pair_index,
                            variant=variant,
                            policy_id=policy_id,
                            source_row=source_by_pair[pair],
                            accepted_row=accepted_by_pair[pair],
                            detector_mapping=p2c_inputs["p2b_mapping"][
                                candidate.variant_id
                            ],
                            modules=modules,
                            cases_by_action=cases_by_action,
                            candidate_artifact=candidate_artifacts[
                                candidate.variant_id
                            ],
                            event_log=events,
                        )
                    )
        events.append(
            {
                "event": "p2d_all_pairs_completed",
                "pair_count": len(rows),
                "intervention_candidate_count": sum(
                    row["intervention_candidate"] for row in rows
                ),
            }
        )
        post_rows, post_raw = _fresh_identity_snapshot()
        if post_rows != inputs["identity_rows"] or post_raw != inputs["raw_hashes"]:
            raise P2DStopRelaxationAuditError("accepted input changed during execution")
        if _implementation_identity() != inputs["implementation_identity"]:
            raise P2DStopRelaxationAuditError("P2d implementation identity changed")
        if _implementation_raw_snapshot() != inputs["implementation_raw_hashes"]:
            raise P2DStopRelaxationAuditError("P2d implementation raw bytes changed")
        summary = _build_valid_summary(inputs, rows)
    except P2DStopRelaxationAuditError as exc:
        events.append(
            {
                "event": "p2d_execution_failed",
                "reason_code": "intervention_contract_error",
                "diagnostic": str(exc),
            }
        )
        return _invalid_summary(
            "intervention_contract_error", input_identity=input_identity
        )
    except Exception:  # noqa: BLE001 - no partial post-intervention claims
        events.append(
            {
                "event": "p2d_execution_failed",
                "reason_code": "unexpected_audit_error",
            }
        )
        return _invalid_summary("unexpected_audit_error", input_identity=input_identity)
    events.append({"event": "p2d_summary_validated"})
    return summary


def record_artifacts_serialized(event_log: list[dict[str, Any]]) -> None:
    """Record serialization only after both report files are written."""

    event_log.append({"event": "p2d_artifacts_serialized"})


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
