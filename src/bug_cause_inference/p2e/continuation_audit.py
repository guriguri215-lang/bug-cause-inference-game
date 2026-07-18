"""Bounded same-policy continuation after accepted P2d threshold states.

P2e replays the accepted P2d one-step audit and, for the 41 rows whose
non-detector action returned to the no-bug threshold, suppresses only that
predicate at every later decision.  The same retained state, RNG, execution
context, policy, costs, budget, max-step contract, observations, and portable
state update are preserved.  This is an analysis-only, model-internal,
non-causal, non-deployable audit, not a policy change or recommendation.
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
from typing import Any, Mapping

from bug_cause_inference.p1b import policies as p1b_policies
from bug_cause_inference.p1b.actions import P1B_ACTION_SPECS
from bug_cause_inference.p1b.models import P1BSettings, rank_distribution
from bug_cause_inference.p2a import evaluation as p2a_evaluation
from bug_cause_inference.p2a.adequacy import validate_portable_value
from bug_cause_inference.p2a.candidates import BUGGY_CANDIDATES
from bug_cause_inference.p2c import trajectory_audit as p2c_audit
from bug_cause_inference.p2d import reports as p2d_reports
from bug_cause_inference.p2d import stop_relaxation_audit as p2d_audit


SCHEMA_VERSION = "p2e_bounded_threshold_relaxation_continuation_audit.v1"
ANALYSIS_PHASE = "p2e_bounded_threshold_relaxation_continuation_audit"
REPORT_ROLE = (
    "analysis_only_fixed_input_ground_truth_informed_model_internal_bounded_"
    "sequence_non_causal_non_deployable_audit"
)
VALID_STATUS = "valid"
INVALID_STATUS = "invalid_inconclusive"

BASE_COMMIT = "fe2b80dda8430f85485a3fde67cfd5ca56964b29"
SPECIFICATION_SHA256 = (
    "d3edfed2db20aacc390eacb4c0c377139015334d1f6547096f0ac33620249af9"
)
SPECIFICATION_REVIEW_RECORD_SHA256 = (
    "f98f8b1fad8dc652ed9b487a5b48011bfac61bbb2b7bb159f8022257dcc2aa82"
)
IDENTITY_CONTRACT_DIGEST = (
    "10151569d670f0ada06ae167df1d82f4c77ce66c086c778a299b50ce61e4add5"
)
EXPECTED_P2D_JSON_SHA256 = (
    "5fb30992bc16666fd3210709b1143e34f62c6f07635fe72962a4a7880c336f93"
)
EXPECTED_P2D_MARKDOWN_SHA256 = (
    "633305a95afbf237c2163ac3b1de634bf9c6e9a696747ec04a58e14a7c015dd4"
)
EXPECTED_P2D_SUMMARY_DIGEST = (
    "fab660ba884ec3c1b1bc0ba5348dff168a850cb6e305f9eb708b03c3205e4fc0"
)

FORMAL_POLICY_IDS = p2d_audit.FORMAL_POLICY_IDS
BUGGY_VARIANT_IDS = p2d_audit.BUGGY_VARIANT_IDS
BUCKET_IDS = p2d_audit.BUCKET_IDS
ACTION_IDS = p2d_audit.ACTION_IDS
TARGET_STOP_ID = "no_bug_probability_threshold"
SUPPRESSION_MODE = "every_later_pre_action_decision"
RESIDUAL_STOP_IDS = p2d_audit.RESIDUAL_STOP_IDS
CLASSIFICATION_IDS = (
    "continuation_candidate",
    "p2d_direct_detector_endpoint",
    "p2d_not_applicable",
)
TERMINAL_REASON_IDS = (
    "direct_detector_observed",
    "bug_confidence_threshold",
    "budget_limit",
    "max_steps",
    "low_expected_utility",
    "no_available_actions",
)
FEASIBILITY_CATEGORY_IDS = (
    "initially_infeasible",
    "initially_feasible_selected_direct_detector",
    "initially_feasible_became_infeasible_before_selection",
    "initially_feasible_through_non_detector_termination",
)
CONTINUATION_CANDIDATE_INDICES = (
    5,
    6,
    11,
    12,
    16,
    17,
    18,
    23,
    24,
    25,
    26,
    27,
    29,
    30,
    31,
    32,
    33,
    35,
    36,
    37,
    38,
    39,
    40,
    41,
    42,
    43,
    44,
    45,
    46,
    47,
    48,
    49,
    50,
    51,
    52,
    53,
    55,
    56,
    57,
    58,
    59,
)
INVALID_REASON_CODES = (
    "accepted_input_identity_error",
    "accepted_p2d_artifact_error",
    "population_classification_error",
    "starting_state_reconstruction_error",
    "continuation_contract_error",
    "policy_visibility_error",
    "payload_validation_error",
    "aggregate_validation_error",
    "serialization_agreement_error",
    "execution_drift_error",
    "unexpected_audit_error",
)

_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
_P2D_JSON_PATH = _REPOSITORY_ROOT / (
    "src/bug_cause_inference/p2d/artifacts/"
    "p2d_one_step_stop_relaxation_audit_v1.json"
)
_P2D_MARKDOWN_PATH = _REPOSITORY_ROOT / (
    "src/bug_cause_inference/p2d/artifacts/"
    "p2d_one_step_stop_relaxation_audit_v1.md"
)
_P2E_IMPLEMENTATION_PATHS = (
    "src/bug_cause_inference/p2e/__init__.py",
    "src/bug_cause_inference/p2e/continuation_audit.py",
    "src/bug_cause_inference/p2e/reports.py",
    "tests/test_p2e_continuation_audit.py",
    "tests/test_p2e_reports.py",
)
FROZEN_IMPLEMENTATION_FILE_SHA256_LF = {
    "src/bug_cause_inference/p2e/__init__.py": (
        "bed9dc32d78fd419c34929a425d09800e53b536792dec16bac8c2eec398b98ff"
    ),
    "src/bug_cause_inference/p2e/continuation_audit.py": (
        "15b2e7525399e609de95a13c9ce4e747c38acef88f8cf937ff7e6764dc7f9ca9"
    ),
    "src/bug_cause_inference/p2e/reports.py": (
        "48477174f16ad1caeaedfe5c5b165bb6c45a0c743592faaa46ea2dc2d1eb7566"
    ),
    "tests/test_p2e_continuation_audit.py": (
        "17775c3ca167a6a8dbc1e340b6b4192640f2766a4c17c4befeca11a411aab1a9"
    ),
    "tests/test_p2e_reports.py": (
        "81af3c35c5be84ba8c33d8ee0e54922ba4e521696e666904d6d98615a74c9b4c"
    ),
}
FROZEN_IMPLEMENTATION_FILE_SHA256_RAW = deepcopy(
    FROZEN_IMPLEMENTATION_FILE_SHA256_LF
)
_P2D_IDENTITY_APPEND = (
    (
        "p2d_init_source",
        "src/bug_cause_inference/p2d/__init__.py",
        "ab08a163455be343d89ca5e1ffe4b266453d2c335c447a8f79c2f198c05f2ab3",
    ),
    (
        "p2d_stop_relaxation_source",
        "src/bug_cause_inference/p2d/stop_relaxation_audit.py",
        "0fc32737233388c3d26f228f2b3048eef1807df05af0148ad2c9eedf834ba9a5",
    ),
    (
        "p2d_reports_source",
        "src/bug_cause_inference/p2d/reports.py",
        "b1382ab2874f282011ee69c9b231e4285c426b8b282f7b43c66884314fda2b59",
    ),
    (
        "p2d_json",
        "src/bug_cause_inference/p2d/artifacts/"
        "p2d_one_step_stop_relaxation_audit_v1.json",
        EXPECTED_P2D_JSON_SHA256,
    ),
    (
        "p2d_markdown",
        "src/bug_cause_inference/p2d/artifacts/"
        "p2d_one_step_stop_relaxation_audit_v1.md",
        EXPECTED_P2D_MARKDOWN_SHA256,
    ),
    (
        "p2d_stop_relaxation_tests",
        "tests/test_p2d_stop_relaxation_audit.py",
        "147f932602a73ef0465b6d76bcef7ad0403c8ee77f10cea6a3090a5a026d9cc9",
    ),
    (
        "p2d_reports_tests",
        "tests/test_p2d_reports.py",
        "4ca535f46306aab77aca48e4df49a12ba4a2cd64716743502ba286bc413440e0",
    ),
)

# Authoritative compact-row anchors captured from the first valid frozen run.
_EXPECTED_PAIR_RESULT_DIGESTS = (
    "3120f496ca2412b211e202441d3d823293ee4e4328c8be2bd4a0b62231337e8e",
    "1a1041f8afd18fd83fdb225325621aef09293c3670285112106f8423bf1859d3",
    "9af0690e85d24f379b37315b312ad33596172f4e522f8cd0935ed309dc694c04",
    "2f504527c49bd3aa9cf218deb6d507066fa1804b2f0ce54b13bb53991c9b76b5",
    "99fdfa68c70d58606a9dd3edec3e7282662947b76780e46efc6e53d770d1a8f4",
    "ff9a38c55b37b47ddb0cb09b4ffe3cee29a954d163c273cc8a6d363f919736e2",
    "77a4207ba622ad88529f00adb53cca0cf4a627f4331ee901c7e42c76d70551cc",
    "4e4ab98bbb5bce4e46d39d819702873d567b6cce2e6b37eacde1829e34a5e926",
    "665659b6b9f17c551ecf0171ac2cb1afb873ee3ac7cfbd53d107df8f87358649",
    "1a01e6d06c882f4706eba9221b55655e941bbc50a8f5f8886d0085dd5feae7a7",
    "5f479c566294f62cbb72da1352ee0af54ac279313ad08ff191f557b90e0f7ccb",
    "f469c8a35d9019a1da8d68abced9b463d87ea20da2c6741a79718103ff2353ae",
    "7bcf9e71fc3128f798b2ef07a9634acab2090e48de7bacafc1d1f8c2084c3533",
    "fc770128332c94f844f0f39c90b209d9ca1f4b33698fe36b87d879f36fee447b",
    "33cc3f84e7d06c0f3ca56e820754b4be26d5af95f0ced26a09e2dae090dc1b5e",
    "ee9dba0607fd632bbf05da7bef21eaa3019212e73483d54cf001008d774ba47e",
    "fec2f03ac502b3579bf28cd0cc5c7512e88442cff559d40e614f72b4d7cb0266",
    "b31b1a0cdb3234c97cf502b81a56a3a05f4672ca3cebe87a7a618e55c29e5c06",
    "0bf1725847fb63ded48d0e4b03eced0ce93f08e94bf14cc622e636bf8a9f324a",
    "66f7493841d1352ad95a9a46d7150d4a9842cb7138f194ae4bb50708501daf0b",
    "09f043f537ddfa0cbaa2d5387efa5301b4f38eaf9e94dc9ddd63b1435040a145",
    "88e5e8f13c2206c69583cf7de84794b667d6c417280cc71484ba64ed315ea857",
    "3df01d18b2a413109478cdcee6bf115d9fa50818a494a3e833c47b50e3a3ef16",
    "ea55f5868cbac0cc845bfe00b256872ede48c20e7317a7ea136cef407c0e0b96",
    "a8269773e37997faa1df941b4eab87ce0b48d982032b08e241d45bbab65d4a0f",
    "56bdcd45df3de153eede1a3f5fdc92c1d3bc8c781ef5b166009fa613cb745d30",
    "2d0a5bd46c30ccc4f5fe3381c7c840f6149ab9c64b6e597ef7a5d94e502eda2c",
    "58dc253740589edf047ccfd91590b137d7ff1437e747d200f693189783816bd7",
    "480381ff9479293afeecec82e042a34c53c5b9d9b7c357091694ba3509b45bca",
    "5ead0350855d0675a4fa87bf3957b7e1dd49d86a2973fc6e8ee40a83139ee8ed",
    "b001e64f304be743b4ef8ac50f4b53607a019fc68fd88b4aac23d977512cfab1",
    "f784c0d16313d1841b690ada811bfdd111d59f17ef215476e8aeee4e73f5e0bc",
    "e6f43daab08d91a34c94fa950ba82f0e9800c83b8072192c07d386702200aabb",
    "e602dcecde6dffab46f2b6cf874f747006f4ff6d5edce6c7e5c41cc73d10cf63",
    "81998895438bdfd3957e8af703a4d3720791670a164da457b9ae54362e3e6070",
    "6af5089af93c5497dda03d82da641e283542d61035ecba961df7bfa7a5cdade5",
    "43cde44b97517c9067906850516ee0a072e7d6425bea257c740423d8eefcfd4e",
    "d8d320eb284b7d56bec11a72068a7d325008088b99d4a67e49d82c35a9865fc6",
    "178406b4684e91aee1d66818608c5db430972bb91b864384bd63bbb78e9274a5",
    "a0a6670a8f52c368b6e95205f48e263aa650d467077cdcdbb2c6c092054c1c30",
    "1360cd0473fee4c03f438808a9804f1f18f3fae38f9d668f320a2b7ef3de418b",
    "27907929eceb1b44d40d0034f01762cd2166233ee8ac2a3e9ef533dea7cbd1f2",
    "663198b9c6de3a80435ad9d683bba2779e4b0361515e180417ac7db7da28f4a5",
    "dab9d8fef63490e3013349f5fb7c2cf08bf3a49957d18d2759d191f57c002d00",
    "7bbab80e75a65ccef4c21014510e0668eeb83da2f58ed25bf0cb5ba24c6f85f6",
    "b296d9a122db60da189282dee4b44cb8f5626a2446033087bbb25e37fbff2e5a",
    "4acdffb2197d06cfe7d5e8062851bf8801cca73dda86561ebf8ba65ccbc9c74a",
    "2f9325f3ca12560f3c1271298b931f5ce0315afc804fcaaaec3d39994b84f0a5",
    "84f9957de273f992dc20c5dc31aa097c85c631f202c7c42caa9afddb1e5a5c8f",
    "e39db01122216d3ef2fe0374ad1dc0fc22e50bdce31cad31db6eb96bd1948a0e",
    "502e90dcd01970b11610ce17be75ee4bcb7e019acb658a4edb843f9a617ee6df",
    "c13a238f72a198904d864f1762b69b7ee3b8d86ca001f720b4ad35877addbd8a",
    "a44447f9285c8455d5a5d952ff0e0983a3792eac34f8010eaa8de42ddaf857b1",
    "83dddcc4da5bbb7f5d6fce0c156a5f1de1babee502c207b7cb6d244af23b9a18",
    "2705e924aa619ce388d7381f3cd6cb9331329f3e7682d3122a5e4aca7d8f7184",
    "72cca70c810f6ddb6dd2db35b73d0d8167c726f60e8d29c3a2638c5d282d3627",
    "e1cc9cb43013ff0b8ef06470bec54d27ff5968eac25c2afdb53b7a053b8ddea8",
    "174d89e17e03a6f667127544f1924668acd399ffb5a931c9ba46e5593b5f69ad",
    "11791cc6871df2135db4300325ede496b8a7d76273e953a6b973e9e9265810c6",
    "540fed6ce4754fe3105ed69851ed8c572e1bc2ee816955291c1639f0ffc3e461",
)

_ROW_FIELDS = (
    "pair_index",
    "variant_id",
    "bucket_id",
    "policy_id",
    "p2d_source_row_sha256",
    "replayed_p2d_row_sha256",
    "input_identity_checks",
    "classification",
    "p2d_replay_agreement",
    "p2e_start_state_digest",
    "p2e_start_rng_state_digest",
    "p2e_start_execution_context_digest",
    "baseline",
    "continuation",
    "row_consistency_checks",
)
_INPUT_CHECK_FIELDS = (
    "accepted_p2a_replay_agreement",
    "accepted_p2b_mapping_agreement",
    "accepted_p2c_replay_agreement",
    "accepted_p2d_row_agreement",
    "source_identity_preflight_passed",
    "p2d_post_action_rng_checkpoint_matches_preflight",
    "p2d_post_action_execution_context_checkpoint_matches_preflight",
)
_BASELINE_FIELDS = (
    "p2d_intervention_candidate",
    "p2d_outcome_class",
    "p2d_selected_action_id",
    "p2d_selected_action_cost",
    "p2d_selected_action_is_direct_detector",
    "p2d_observation_bug_detected",
    "p2d_post_action_common_stop_result",
    "p2d_post_action_step",
    "p2d_post_action_cumulative_cost",
    "p2d_post_action_remaining_budget",
    "p2d_not_applicable_reason",
)
_CONTINUATION_FIELDS = (
    "suppressed_stop_id",
    "suppression_mode",
    "initial_feasible_direct_detector_ids",
    "initial_direct_detector_budget_feasible",
    "terminal_outcome",
    "terminal_reason",
    "direct_detector_selected",
    "direct_detector_observation_detected",
    "direct_detector_selected_additional_action_index",
    "direct_detector_selected_action_id",
    "additional_action_count",
    "cumulative_additional_cost",
    "final_step",
    "final_cumulative_cost",
    "final_remaining_budget",
    "detector_feasibility_category",
    "maximum_additional_action_count",
    "decisions",
    "continuation_trace_digest",
)
_DECISION_FIELDS = (
    "decision_index",
    "absolute_decision_step",
    "additional_actions_executed_before",
    "cumulative_additional_cost_before",
    "state_digest_before",
    "cumulative_cost_before",
    "remaining_budget_before",
    "feasible_direct_detector_ids",
    "direct_detector_budget_feasible",
    "suppressed_stop_id",
    "residual_stop_predicates",
    "residual_stop_result",
    "selection_attempted",
    "selected_action_id",
    "selected_action_cost",
    "selected_action_is_direct_detector",
    "observation_bug_detected",
    "state_digest_after",
    "post_action_cumulative_cost",
    "post_action_step",
    "post_action_common_stop_result",
    "terminal_after_decision",
    "terminal_reason",
)
_ROW_CHECK_FIELDS = (
    "classification_truth_table_matches",
    "p2d_replay_matches_source",
    "p2e_start_state_matches_p2d_post_action",
    "target_only_repeated_suppression",
    "residual_stop_precedence_matches",
    "policy_visibility_boundary_preserved",
    "decision_payload_matches_outcome",
    "action_cost_step_state_consistent",
    "detector_feasibility_monotone",
    "termination_partition_and_bound_match",
    "detector_endpoint_has_no_later_action",
    "p2e_start_rng_matches_preflight",
    "p2e_start_execution_context_matches_preflight",
    "retained_objects_used_without_clone_or_reseed",
)
_AXIS_FIELDS = (
    "support_pair_count",
    "classification_counts",
    "candidate_terminal_reason_counts",
    "direct_detector_selected_count",
    "observation_detected_count",
    "additional_action_count_distribution",
    "additional_cost_distribution",
    "detector_feasibility_category_counts",
    "selected_action_counts",
    "direct_detector_selected_candidate_ratio",
    "observation_detected_candidate_ratio",
    "terminal_reason_ratios",
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


class P2EContinuationAuditError(ValueError):
    """Raised when the frozen P2e contract or a complete result is invalid."""


def _repository_path(relative_path: str) -> Path:
    path = Path(relative_path)
    if path.is_absolute() or ".." in path.parts:
        raise P2EContinuationAuditError("identity path must be repository-relative")
    resolved = (_REPOSITORY_ROOT / path).resolve()
    try:
        resolved.relative_to(_REPOSITORY_ROOT)
    except ValueError as exc:
        raise P2EContinuationAuditError("identity path escapes repository") from exc
    return resolved


def _hash_file(path: Path) -> tuple[str, str]:
    raw = path.read_bytes()
    canonical = raw.replace(b"\r\n", b"\n")
    return hashlib.sha256(canonical).hexdigest(), hashlib.sha256(raw).hexdigest()


def _canonical_digest(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, allow_nan=False, separators=(",", ":")
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def _identity_rows() -> list[dict[str, str]]:
    rows = deepcopy(p2d_audit._identity_rows())
    rows.extend(
        {"identity": identity, "path": path, "sha256_lf": expected}
        for identity, path, expected in _P2D_IDENTITY_APPEND
    )
    if len(rows) != 57 or len({row["identity"] for row in rows}) != 57:
        raise P2EContinuationAuditError("57-file identity support drifted")
    return rows


def identity_contract_digest(rows: list[dict[str, str]]) -> str:
    return _canonical_digest(rows)


def _fresh_identity_snapshot() -> tuple[list[dict[str, str]], dict[str, str]]:
    rows = _identity_rows()
    if identity_contract_digest(rows) != IDENTITY_CONTRACT_DIGEST:
        raise P2EContinuationAuditError("57-file identity contract digest drifted")
    raw_hashes: dict[str, str] = {}
    for row in rows:
        portable, raw = _hash_file(_repository_path(row["path"]))
        if portable != row["sha256_lf"]:
            raise P2EContinuationAuditError(
                f"accepted input drifted: {row['identity']}"
            )
        raw_hashes[row["identity"]] = raw
    return rows, raw_hashes


def _implementation_identity() -> dict[str, str]:
    return {
        path: _hash_file(_repository_path(path))[0]
        for path in _P2E_IMPLEMENTATION_PATHS
    }


def _implementation_raw_snapshot() -> dict[str, str]:
    return {
        path: _hash_file(_repository_path(path))[1]
        for path in _P2E_IMPLEMENTATION_PATHS
    }


def _classification(source_row: Mapping[str, Any]) -> str:
    if source_row["intervention_candidate"] is False:
        if source_row["intervention"] is not None:
            raise P2EContinuationAuditError("P2d NA row contains intervention payload")
        return "p2d_not_applicable"
    intervention = source_row["intervention"]
    if type(intervention) is not dict:
        raise P2EContinuationAuditError("P2d candidate intervention is missing")
    if intervention["outcome_class"] != "action_decision_reached":
        raise P2EContinuationAuditError("P2d candidate did not reach an action")
    action = intervention["action_execution"]
    if type(action) is not dict or action["executed_action_count"] != 1:
        raise P2EContinuationAuditError("P2d action payload is incomplete")
    if action["second_action_execution_count"] != 0:
        raise P2EContinuationAuditError("P2d executed a second action")
    detector = action["selected_action_is_direct_detector"]
    detected = action["observation_bug_detected"]
    if detector is True and detected is True:
        return "p2d_direct_detector_endpoint"
    if (
        detector is False
        and detected is False
        and action["post_action_common_stop_result"] == TARGET_STOP_ID
        and action["horizon_status"] == "normal_stop_after_action"
    ):
        return "continuation_candidate"
    raise P2EContinuationAuditError("P2d row is outside the frozen 41/11/8 partition")


def _load_inputs() -> dict[str, Any]:
    identity_rows, raw_hashes = _fresh_identity_snapshot()
    p2d_summary = json.loads(_P2D_JSON_PATH.read_text(encoding="utf-8"))
    p2d_audit.validate_audit_summary(p2d_summary)
    recovered = p2d_reports.summary_from_markdown(
        _P2D_MARKDOWN_PATH.read_text(encoding="utf-8")
    )
    if recovered != p2d_summary:
        raise P2EContinuationAuditError("accepted P2d artifact semantics drifted")
    if _hash_file(_P2D_JSON_PATH)[0] != EXPECTED_P2D_JSON_SHA256:
        raise P2EContinuationAuditError("accepted P2d JSON bytes drifted")
    if _hash_file(_P2D_MARKDOWN_PATH)[0] != EXPECTED_P2D_MARKDOWN_SHA256:
        raise P2EContinuationAuditError("accepted P2d Markdown bytes drifted")
    if _canonical_digest(p2d_summary) != EXPECTED_P2D_SUMMARY_DIGEST:
        raise P2EContinuationAuditError("accepted P2d summary digest drifted")
    rows = p2d_summary["pair_results"]
    classifications = [_classification(row) for row in rows]
    counts = {item: classifications.count(item) for item in CLASSIFICATION_IDS}
    indices = tuple(
        index
        for index, item in enumerate(classifications, start=1)
        if item == "continuation_candidate"
    )
    if counts != {
        "continuation_candidate": 41,
        "p2d_direct_detector_endpoint": 11,
        "p2d_not_applicable": 8,
    }:
        raise P2EContinuationAuditError("accepted P2d 41/11/8 partition drifted")
    if indices != CONTINUATION_CANDIDATE_INDICES:
        raise P2EContinuationAuditError("accepted P2d candidate indices drifted")
    p2d_inputs = p2d_audit._load_inputs()
    return {
        "identity_rows": identity_rows,
        "raw_hashes": raw_hashes,
        "implementation_identity": _implementation_identity(),
        "implementation_raw_hashes": _implementation_raw_snapshot(),
        "p2d_summary": p2d_summary,
        "p2d_inputs": p2d_inputs,
    }


def _canonical_context_value(value: Any) -> Any:
    if value is None or type(value) in (bool, int, str):
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise P2EContinuationAuditError("execution context contains non-finite float")
        return value
    if type(value) is list or type(value) is tuple:
        return [_canonical_context_value(item) for item in value]
    if type(value) is dict:
        if any(type(key) is not str for key in value):
            raise P2EContinuationAuditError("execution context key is not a string")
        return {
            key: _canonical_context_value(value[key])
            for key in sorted(value)
        }
    raise P2EContinuationAuditError("execution context contains unsupported value")


def rng_state_digest(rng: random.Random) -> str:
    state = rng.getstate()
    if type(state) is not tuple or len(state) != 3:
        raise P2EContinuationAuditError("RNG state shape drifted")
    version, internal, gauss_next = state
    if type(version) is not int:
        raise P2EContinuationAuditError("RNG state version is not an exact integer")
    if type(internal) is not tuple or not internal:
        raise P2EContinuationAuditError("RNG internal state is malformed")
    if any(type(item) is not int for item in internal):
        raise P2EContinuationAuditError("RNG internal state contains non-integer")
    if gauss_next is not None and (
        type(gauss_next) is not float or not math.isfinite(gauss_next)
    ):
        raise P2EContinuationAuditError("RNG Gaussian cache is malformed")
    return _canonical_digest(
        {
            "version": version,
            "internal_state": list(internal),
            "gauss_next": gauss_next,
        }
    )


def execution_context_digest(context: Any) -> str:
    if type(context.test_results) is not list or type(context.action_results) is not dict:
        raise P2EContinuationAuditError("execution context shape drifted")
    projection = {
        "test_results": [
            _canonical_context_value(item) for item in context.test_results
        ],
        "action_results": [
            {
                "action_id": action_id,
                "results": [_canonical_context_value(item) for item in results],
            }
            for action_id, results in context.action_results.items()
        ],
    }
    if any(
        type(item["action_id"]) is not str or type(item["results"]) is not list
        for item in projection["action_results"]
    ):
        raise P2EContinuationAuditError("execution context action projection drifted")
    return _canonical_digest(projection)


def _checkpoint(state: Any, rng: random.Random) -> dict[str, str]:
    return {
        "state": p2d_audit.terminal_state_digest(state),
        "rng": rng_state_digest(rng),
        "context": execution_context_digest(state.execution_context),
    }


def _replay_p2d_pair(
    *,
    pair_index: int,
    variant: Any,
    policy_id: str,
    p2c_source_row: Mapping[str, Any],
    accepted_p2a_row: Mapping[str, Any],
    detector_mapping: Mapping[str, Any],
    modules: Mapping[str, Any],
    cases_by_action: Mapping[str, list[dict[str, Any]]],
    candidate_artifact: dict[str, Any],
    accepted_p2d_row: Mapping[str, Any],
) -> tuple[Any, random.Random, dict[str, Any]]:
    result, state, rng = p2d_audit._run_policy_to_terminal(
        variant, policy_id, modules, cases_by_action, candidate_artifact
    )
    projected = p2c_audit._build_pair_row(
        pair_index=pair_index,
        variant=variant,
        policy_id=policy_id,
        result=result,
        accepted_row=accepted_p2a_row,
        detector_mapping=detector_mapping,
    )
    if projected != p2c_source_row:
        raise P2EContinuationAuditError("normal replay differs from accepted P2c row")
    settings = P1BSettings(**p2a_evaluation._FIXED_SETTINGS)
    terminal_remaining = settings.budget_limit - state.cumulative_cost
    terminal_scores = p1b_policies.score_actions(state, terminal_remaining)
    terminal_best = (
        terminal_scores[0]["expected_utility_per_cost"] if terminal_scores else None
    )
    if (
        p1b_policies._check_stop(state, settings, terminal_best)
        != p2c_source_row["terminal_common_stop_result"]
    ):
        raise P2EContinuationAuditError("normal terminal stop reconstruction drifted")

    candidate = p2d_audit._is_candidate(p2c_source_row)
    intervention: dict[str, Any] | None = None
    if candidate:
        residual_rows, residual_result = p2d_audit._residual_stop_evaluation(
            state, settings
        )
        outcome_class = (
            "alternate_stop_before_action"
            if residual_result is not None
            else "action_decision_reached"
        )
        action_execution = None
        if outcome_class == "action_decision_reached":
            action_execution = p2d_audit._execute_one_action(
                variant=variant,
                policy_id=policy_id,
                state=state,
                rng=rng,
                modules=modules,
                cases_by_action=cases_by_action,
                candidate_artifact=candidate_artifact,
                detector_ids=list(detector_mapping["direct_detecting_action_ids"]),
            )
        intervention = {
            "suppressed_stop_id": TARGET_STOP_ID,
            "suppression_count": 1,
            "residual_stop_predicates": residual_rows,
            "residual_stop_result": residual_result,
            "outcome_class": outcome_class,
            "counterfactual_decision_step": p2c_source_row["step_count"] + 1,
            "pre_action_remaining_budget": terminal_remaining,
            "action_execution": action_execution,
        }
    original_terminal = {
        "direct_detector_selected": p2c_source_row["direct_detector_selected"],
        "replayed_discovered_within_budget": p2c_source_row[
            "replayed_discovered_within_budget"
        ],
        "terminal_step": p2c_source_row["step_count"],
        "terminal_cumulative_cost": p2c_source_row["cumulative_cost"],
        "terminal_remaining_budget": terminal_remaining,
        "stop_reason": p2c_source_row["stop_reason"],
        "terminal_common_stop_result": p2c_source_row[
            "terminal_common_stop_result"
        ],
        "terminal_feasible_direct_detector_ids": list(
            p2c_source_row["terminal_feasible_direct_detector_ids"]
        ),
    }
    terminal_state = p1b_policies._State(
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
    replayed = {
        "pair_index": pair_index,
        "variant_id": variant.variant_id,
        "bucket_id": detector_mapping["bucket_id"],
        "policy_id": policy_id,
        "p2c_source_row_sha256": _canonical_digest(p2c_source_row),
        "replayed_p2c_row_sha256": _canonical_digest(projected),
        "input_identity_checks": {
            field: True for field in p2d_audit._INPUT_CHECK_FIELDS
        },
        "terminal_state_reconstruction_agreement": True,
        "terminal_state_digest": p2d_audit.terminal_state_digest(terminal_state),
        "intervention_candidate": candidate,
        "not_applicable_reason": p2d_audit._not_applicable_reason(p2c_source_row),
        "original_terminal": original_terminal,
        "intervention": intervention,
        "row_consistency_checks": {
            field: True for field in p2d_audit._ROW_CHECK_FIELDS
        },
    }
    if replayed != accepted_p2d_row:
        raise P2EContinuationAuditError("replayed P2d row differs from accepted row")
    return state, rng, replayed


def _residual_stop_evaluation(
    state: Any, settings: P1BSettings, scores: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], str | None]:
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


def _feasible_detector_ids(
    state: Any, detector_ids: list[str], remaining: int
) -> list[str]:
    return [
        action_id
        for action_id in detector_ids
        if action_id not in state.executed_actions
        and P1B_ACTION_SPECS[action_id].cost <= remaining
    ]


def _post_action_stop(state: Any, settings: P1BSettings) -> str | None:
    remaining = settings.budget_limit - state.cumulative_cost
    scores = p1b_policies.score_actions(state, remaining)
    best = scores[0]["expected_utility_per_cost"] if scores else None
    return p1b_policies._check_stop(state, settings, best)


def _execute_action(
    *,
    variant: Any,
    state: Any,
    action_id: str,
    modules: Mapping[str, Any],
    cases_by_action: Mapping[str, list[dict[str, Any]]],
    candidate_artifact: dict[str, Any],
) -> Any:
    observation = p2a_evaluation._run_frozen_action(
        variant_id=variant.variant_id,
        action_id=action_id,
        context=state.execution_context,
        modules=modules,
        cases_by_action=cases_by_action,
        candidate_artifact=candidate_artifact,
    )
    if observation.cost != P1B_ACTION_SPECS[action_id].cost:
        raise P2EContinuationAuditError("accepted action cost drifted")
    state.executed_actions.append(action_id)
    state.cumulative_cost += observation.cost
    state.current_step += 1
    state.bug_detected = state.bug_detected or observation.bug_detected
    state.bug_presence = p1b_policies._update_bug_presence(
        state.bug_presence, observation.bug_detected, observation.no_bug_evidence
    )
    state.cause_posterior = p2d_audit._update_distribution_portable(
        state.cause_posterior, observation.cause_scores
    )
    state.location_posterior = p2d_audit._update_distribution_portable(
        state.location_posterior, observation.location_scores
    )
    state.fix_intent_posterior = p2d_audit._update_distribution_portable(
        state.fix_intent_posterior, observation.fix_intent_scores
    )
    return observation


def _run_continuation(
    *,
    variant: Any,
    policy_id: str,
    state: Any,
    rng: random.Random,
    detector_ids: list[str],
    modules: Mapping[str, Any],
    cases_by_action: Mapping[str, list[dict[str, Any]]],
    candidate_artifact: dict[str, Any],
) -> dict[str, Any]:
    settings = P1BSettings(**p2a_evaluation._FIXED_SETTINGS)
    start_step = state.current_step
    start_cost = state.cumulative_cost
    remaining_action_bound = len(
        [action for action in ACTION_IDS if action not in state.executed_actions]
    )
    maximum_actions = min(settings.max_steps - start_step, remaining_action_bound)
    initial_feasible_ids = _feasible_detector_ids(
        state, detector_ids, settings.budget_limit - state.cumulative_cost
    )
    initial_feasible = bool(initial_feasible_ids)
    decisions: list[dict[str, Any]] = []
    feasibility_history: list[bool] = []
    selected_detector_index: int | None = None
    selected_detector_id: str | None = None
    terminal_reason: str | None = None

    while terminal_reason is None:
        additional_before = state.current_step - start_step
        additional_cost_before = state.cumulative_cost - start_cost
        remaining = settings.budget_limit - state.cumulative_cost
        feasible_ids = _feasible_detector_ids(state, detector_ids, remaining)
        feasibility_history.append(bool(feasible_ids))
        scores = p1b_policies.score_actions(state, remaining)
        residual_rows, residual_result = _residual_stop_evaluation(
            state, settings, scores
        )
        base = {
            "decision_index": len(decisions) + 1,
            "absolute_decision_step": state.current_step + 1,
            "additional_actions_executed_before": additional_before,
            "cumulative_additional_cost_before": additional_cost_before,
            "state_digest_before": p2d_audit.terminal_state_digest(state),
            "cumulative_cost_before": state.cumulative_cost,
            "remaining_budget_before": remaining,
            "feasible_direct_detector_ids": feasible_ids,
            "direct_detector_budget_feasible": bool(feasible_ids),
            "suppressed_stop_id": TARGET_STOP_ID,
            "residual_stop_predicates": residual_rows,
            "residual_stop_result": residual_result,
        }
        if residual_result is not None:
            terminal_reason = residual_result
            decisions.append(
                {
                    **base,
                    "selection_attempted": False,
                    "selected_action_id": None,
                    "selected_action_cost": None,
                    "selected_action_is_direct_detector": None,
                    "observation_bug_detected": None,
                    "state_digest_after": None,
                    "post_action_cumulative_cost": None,
                    "post_action_step": None,
                    "post_action_common_stop_result": None,
                    "terminal_after_decision": True,
                    "terminal_reason": residual_result,
                }
            )
            break

        action_id = p1b_policies.choose_action(policy_id, state, remaining, rng)
        if action_id is None:
            terminal_reason = "no_available_actions"
            decisions.append(
                {
                    **base,
                    "selection_attempted": True,
                    "selected_action_id": None,
                    "selected_action_cost": None,
                    "selected_action_is_direct_detector": None,
                    "observation_bug_detected": None,
                    "state_digest_after": None,
                    "post_action_cumulative_cost": None,
                    "post_action_step": None,
                    "post_action_common_stop_result": None,
                    "terminal_after_decision": True,
                    "terminal_reason": terminal_reason,
                }
            )
            break
        if action_id not in ACTION_IDS or action_id in state.executed_actions:
            raise P2EContinuationAuditError("selector returned unavailable action")
        if P1B_ACTION_SPECS[action_id].cost > remaining:
            raise P2EContinuationAuditError("selector returned over-budget action")

        direct = action_id in detector_ids
        observation = _execute_action(
            variant=variant,
            state=state,
            action_id=action_id,
            modules=modules,
            cases_by_action=cases_by_action,
            candidate_artifact=candidate_artifact,
        )
        if direct is not observation.bug_detected:
            raise P2EContinuationAuditError(
                "direct-detector mapping and accepted observation disagree"
            )
        post_stop = _post_action_stop(state, settings)
        terminal_after = direct and observation.bug_detected
        if terminal_after:
            terminal_reason = "direct_detector_observed"
            selected_detector_index = state.current_step - start_step
            selected_detector_id = action_id
        decisions.append(
            {
                **base,
                "selection_attempted": True,
                "selected_action_id": action_id,
                "selected_action_cost": observation.cost,
                "selected_action_is_direct_detector": direct,
                "observation_bug_detected": observation.bug_detected,
                "state_digest_after": p2d_audit.terminal_state_digest(state),
                "post_action_cumulative_cost": state.cumulative_cost,
                "post_action_step": state.current_step,
                "post_action_common_stop_result": post_stop,
                "terminal_after_decision": terminal_after,
                "terminal_reason": terminal_reason if terminal_after else None,
            }
        )

    if any(not earlier and later for earlier, later in zip(feasibility_history, feasibility_history[1:])):
        raise P2EContinuationAuditError("detector feasibility changed false to true")
    selected = selected_detector_id is not None
    if not initial_feasible:
        feasibility_category = "initially_infeasible"
    elif selected:
        feasibility_category = "initially_feasible_selected_direct_detector"
    elif not all(feasibility_history):
        feasibility_category = "initially_feasible_became_infeasible_before_selection"
    else:
        feasibility_category = "initially_feasible_through_non_detector_termination"
    terminal_outcome = (
        "direct_detector_observed"
        if terminal_reason == "direct_detector_observed"
        else "terminated_without_direct_detector"
    )
    return {
        "suppressed_stop_id": TARGET_STOP_ID,
        "suppression_mode": SUPPRESSION_MODE,
        "initial_feasible_direct_detector_ids": initial_feasible_ids,
        "initial_direct_detector_budget_feasible": initial_feasible,
        "terminal_outcome": terminal_outcome,
        "terminal_reason": terminal_reason,
        "direct_detector_selected": selected,
        "direct_detector_observation_detected": selected,
        "direct_detector_selected_additional_action_index": selected_detector_index,
        "direct_detector_selected_action_id": selected_detector_id,
        "additional_action_count": state.current_step - start_step,
        "cumulative_additional_cost": state.cumulative_cost - start_cost,
        "final_step": state.current_step,
        "final_cumulative_cost": state.cumulative_cost,
        "final_remaining_budget": settings.budget_limit - state.cumulative_cost,
        "detector_feasibility_category": feasibility_category,
        "maximum_additional_action_count": maximum_actions,
        "decisions": decisions,
        "continuation_trace_digest": _canonical_digest(decisions),
    }


def _runtime_maps(inputs: Mapping[str, Any]) -> dict[str, Any]:
    p2d_inputs = inputs["p2d_inputs"]
    p2c_inputs = p2d_inputs["p2c_inputs"]
    return {
        "cases_by_action": p2a_evaluation._catalog_cases(
            p2c_inputs["p2b_inputs"]["bundle"]
        ),
        "candidate_artifacts": {
            item["variant_id"]: item
            for item in p2c_inputs["p2b_inputs"]["artifact"]["candidates"]
        },
        "accepted_p2a_by_pair": {
            (row["variant_id"], row["policy_id"]): row
            for row in p2c_inputs["saved_rows"]
        },
        "p2c_by_pair": {
            (row["variant_id"], row["policy_id"]): row
            for row in p2d_inputs["p2c_summary"]["pair_trajectories"]
        },
        "p2d_by_pair": {
            (row["variant_id"], row["policy_id"]): row
            for row in inputs["p2d_summary"]["pair_results"]
        },
        "detector_mapping": p2c_inputs["p2b_mapping"],
    }


def _preflight_checkpoints(inputs: Mapping[str, Any]) -> dict[int, dict[str, str]]:
    runtime = _runtime_maps(inputs)
    checkpoints: dict[int, dict[str, str]] = {}
    pair_index = 0
    for candidate in BUGGY_CANDIDATES:
        variant = p2a_evaluation._candidate_variant(candidate)
        with p2a_evaluation._candidate_modules(candidate) as modules:
            for policy_id in FORMAL_POLICY_IDS:
                pair_index += 1
                pair = (candidate.variant_id, policy_id)
                accepted_p2d = runtime["p2d_by_pair"][pair]
                state, rng, _ = _replay_p2d_pair(
                    pair_index=pair_index,
                    variant=variant,
                    policy_id=policy_id,
                    p2c_source_row=runtime["p2c_by_pair"][pair],
                    accepted_p2a_row=runtime["accepted_p2a_by_pair"][pair],
                    detector_mapping=runtime["detector_mapping"][candidate.variant_id],
                    modules=modules,
                    cases_by_action=runtime["cases_by_action"],
                    candidate_artifact=runtime["candidate_artifacts"][
                        candidate.variant_id
                    ],
                    accepted_p2d_row=accepted_p2d,
                )
                if _classification(accepted_p2d) == "continuation_candidate":
                    checkpoints[pair_index] = _checkpoint(state, rng)
    if tuple(checkpoints) != CONTINUATION_CANDIDATE_INDICES:
        raise P2EContinuationAuditError("41 preflight checkpoints are incomplete")
    return checkpoints


def _baseline(source_row: Mapping[str, Any]) -> dict[str, Any]:
    if source_row["intervention_candidate"] is False:
        values: tuple[Any, ...] = (
            False,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            source_row["not_applicable_reason"],
        )
    else:
        intervention = source_row["intervention"]
        action = intervention["action_execution"]
        values = (
            True,
            intervention["outcome_class"],
            action["selected_action_id"],
            action["selected_action_cost"],
            action["selected_action_is_direct_detector"],
            action["observation_bug_detected"],
            action["post_action_common_stop_result"],
            action["post_action_step"],
            action["post_action_cumulative_cost"],
            12 - action["post_action_cumulative_cost"],
            None,
        )
    return dict(zip(_BASELINE_FIELDS, values, strict=True))


def _build_pair_row(
    *,
    pair_index: int,
    accepted_p2d_row: Mapping[str, Any],
    replayed_p2d_row: Mapping[str, Any],
    checkpoint: dict[str, str] | None,
    continuation: dict[str, Any] | None,
) -> dict[str, Any]:
    classification = _classification(accepted_p2d_row)
    if (classification == "continuation_candidate") is not (
        checkpoint is not None and continuation is not None
    ):
        raise P2EContinuationAuditError("classification payload separation failed")
    source_digest = _canonical_digest(accepted_p2d_row)
    replayed_digest = _canonical_digest(replayed_p2d_row)
    return dict(
        zip(
            _ROW_FIELDS,
            (
                pair_index,
                accepted_p2d_row["variant_id"],
                accepted_p2d_row["bucket_id"],
                accepted_p2d_row["policy_id"],
                source_digest,
                replayed_digest,
                {field: True for field in _INPUT_CHECK_FIELDS},
                classification,
                True,
                checkpoint["state"] if checkpoint else None,
                checkpoint["rng"] if checkpoint else None,
                checkpoint["context"] if checkpoint else None,
                _baseline(accepted_p2d_row),
                continuation,
                {field: True for field in _ROW_CHECK_FIELDS},
            ),
            strict=True,
        )
    )


def _execute_all_pairs(
    inputs: Mapping[str, Any],
    preflight: Mapping[int, dict[str, str]],
    events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    runtime = _runtime_maps(inputs)
    rows: list[dict[str, Any]] = []
    pair_index = 0
    for candidate in BUGGY_CANDIDATES:
        variant = p2a_evaluation._candidate_variant(candidate)
        with p2a_evaluation._candidate_modules(candidate) as modules:
            for policy_id in FORMAL_POLICY_IDS:
                pair_index += 1
                pair = (candidate.variant_id, policy_id)
                accepted_p2d = runtime["p2d_by_pair"][pair]
                state, rng, replayed = _replay_p2d_pair(
                    pair_index=pair_index,
                    variant=variant,
                    policy_id=policy_id,
                    p2c_source_row=runtime["p2c_by_pair"][pair],
                    accepted_p2a_row=runtime["accepted_p2a_by_pair"][pair],
                    detector_mapping=runtime["detector_mapping"][candidate.variant_id],
                    modules=modules,
                    cases_by_action=runtime["cases_by_action"],
                    candidate_artifact=runtime["candidate_artifacts"][
                        candidate.variant_id
                    ],
                    accepted_p2d_row=accepted_p2d,
                )
                classification = _classification(accepted_p2d)
                checkpoint = None
                continuation = None
                if classification == "continuation_candidate":
                    checkpoint = _checkpoint(state, rng)
                    if checkpoint != preflight.get(pair_index):
                        raise P2EContinuationAuditError(
                            "P2e start state/RNG/context checkpoint drifted"
                        )
                    if pair_index == 5:
                        events.append(
                            {
                                "event": "p2e_first_continuation_candidate_started",
                                "pair_index": pair_index,
                                "variant_id": candidate.variant_id,
                                "policy_id": policy_id,
                            }
                        )
                    continuation = _run_continuation(
                        variant=variant,
                        policy_id=policy_id,
                        state=state,
                        rng=rng,
                        detector_ids=list(
                            runtime["detector_mapping"][candidate.variant_id][
                                "direct_detecting_action_ids"
                            ]
                        ),
                        modules=modules,
                        cases_by_action=runtime["cases_by_action"],
                        candidate_artifact=runtime["candidate_artifacts"][
                            candidate.variant_id
                        ],
                    )
                rows.append(
                    _build_pair_row(
                        pair_index=pair_index,
                        accepted_p2d_row=accepted_p2d,
                        replayed_p2d_row=replayed,
                        checkpoint=checkpoint,
                        continuation=continuation,
                    )
                )
    return rows


def _ratio(numerator: int, denominator: int) -> dict[str, Any]:
    if type(numerator) is not int or type(denominator) is not int:
        raise P2EContinuationAuditError("ratio counts must be exact integers")
    if numerator < 0 or denominator < 0 or numerator > denominator:
        raise P2EContinuationAuditError("ratio counts are outside support")
    if denominator == 0:
        return {
            "numerator": numerator,
            "denominator": denominator,
            "fraction": None,
            "decimal": None,
            "undefined_reason": "no_continuation_candidate_support",
        }
    value = Fraction(numerator, denominator)
    return {
        "numerator": numerator,
        "denominator": denominator,
        "fraction": f"{value.numerator}/{value.denominator}",
        "decimal": format(float(value), ".12g"),
        "undefined_reason": None,
    }


def _axis_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    candidates = [
        row for row in rows if row["classification"] == "continuation_candidate"
    ]
    continuations = [row["continuation"] for row in candidates]
    selected = sum(item["direct_detector_selected"] for item in continuations)
    detected = sum(
        item["direct_detector_observation_detected"] for item in continuations
    )
    action_counts = {str(value): 0 for value in range(7)}
    cost_counts = {str(value): 0 for value in range(13)}
    selected_action_counts = {action_id: 0 for action_id in ACTION_IDS}
    for item in continuations:
        action_counts[str(item["additional_action_count"])] += 1
        cost_counts[str(item["cumulative_additional_cost"])] += 1
        for decision in item["decisions"]:
            action_id = decision["selected_action_id"]
            if action_id is not None:
                selected_action_counts[action_id] += 1
    candidate_count = len(candidates)
    return dict(
        zip(
            _AXIS_FIELDS,
            (
                len(rows),
                {
                    item: sum(row["classification"] == item for row in rows)
                    for item in CLASSIFICATION_IDS
                },
                {
                    item: sum(
                        continuation["terminal_reason"] == item
                        for continuation in continuations
                    )
                    for item in TERMINAL_REASON_IDS
                },
                selected,
                detected,
                action_counts,
                cost_counts,
                {
                    item: sum(
                        continuation["detector_feasibility_category"] == item
                        for continuation in continuations
                    )
                    for item in FEASIBILITY_CATEGORY_IDS
                },
                selected_action_counts,
                _ratio(selected, candidate_count),
                _ratio(detected, candidate_count),
                {
                    item: _ratio(
                        sum(
                            continuation["terminal_reason"] == item
                            for continuation in continuations
                        ),
                        candidate_count,
                    )
                    for item in TERMINAL_REASON_IDS
                },
            ),
            strict=True,
        )
    )


def derive_aggregate_results(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "overall": _axis_summary(rows),
        "by_policy": [
            {
                "policy_id": policy_id,
                "axes": _axis_summary(
                    [row for row in rows if row["policy_id"] == policy_id]
                ),
            }
            for policy_id in FORMAL_POLICY_IDS
        ],
        "by_variant": [
            {
                "variant_id": variant_id,
                "axes": _axis_summary(
                    [row for row in rows if row["variant_id"] == variant_id]
                ),
            }
            for variant_id in BUGGY_VARIANT_IDS
        ],
        "by_bucket": [
            {
                "bucket_id": bucket_id,
                "axes": _axis_summary(
                    [row for row in rows if row["bucket_id"] == bucket_id]
                ),
            }
            for bucket_id in BUCKET_IDS
        ],
    }


def _pending_acceptance(scope: str) -> dict[str, Any]:
    return {"scope": scope, "accepted": False, "status": "pending_separate_acceptance"}


def _expected_input_identity() -> dict[str, Any]:
    upstream = p2d_audit._expected_input_identity()
    return {
        "base_commit": BASE_COMMIT,
        "identity_hash_mode": "sha256_after_crlf_to_lf_normalization",
        "raw_drift_mode": "exact_working_tree_sha256_pre_post_same_run",
        "identity_contract_digest": IDENTITY_CONTRACT_DIGEST,
        "identity_support_count": 57,
        "identity_rows": _identity_rows(),
        "p2a_summary_digest": upstream["p2a_summary_digest"],
        "p2a_json_sha256": upstream["p2a_json_sha256"],
        "p2a_markdown_sha256": upstream["p2a_markdown_sha256"],
        "p2b_summary_digest": upstream["p2b_summary_digest"],
        "p2b_json_sha256": upstream["p2b_json_sha256"],
        "p2b_markdown_sha256": upstream["p2b_markdown_sha256"],
        "p2c_summary_digest": upstream["p2c_summary_digest"],
        "p2c_json_sha256": upstream["p2c_json_sha256"],
        "p2c_markdown_sha256": upstream["p2c_markdown_sha256"],
        "p2d_summary_digest": EXPECTED_P2D_SUMMARY_DIGEST,
        "p2d_json_sha256": EXPECTED_P2D_JSON_SHA256,
        "p2d_markdown_sha256": EXPECTED_P2D_MARKDOWN_SHA256,
        "p2d_pair_count": 60,
        "p2d_action_decision_reached_count": 52,
        "p2d_direct_detector_endpoint_count": 11,
        "p2d_post_action_threshold_candidate_count": 41,
        "implementation_file_sha256_lf": deepcopy(
            FROZEN_IMPLEMENTATION_FILE_SHA256_LF
        ),
    }


def _input_identity(inputs: Mapping[str, Any]) -> dict[str, Any]:
    value = _expected_input_identity()
    value["identity_rows"] = deepcopy(inputs["identity_rows"])
    return value


def _expected_freeze() -> dict[str, Any]:
    return {
        "specification_sha256": SPECIFICATION_SHA256,
        "review_record_sha256": SPECIFICATION_REVIEW_RECORD_SHA256,
        "specification_review_verdict": "accept",
        "identity_contract_digest": IDENTITY_CONTRACT_DIGEST,
        "implementation_file_sha256_lf": deepcopy(
            FROZEN_IMPLEMENTATION_FILE_SHA256_LF
        ),
        "implementation_file_sha256_raw": deepcopy(
            FROZEN_IMPLEMENTATION_FILE_SHA256_RAW
        ),
        "first_original_replay_pair_index": 1,
        "first_continuation_pair_index": 5,
        "schema_version": SCHEMA_VERSION,
    }


def _freeze(_inputs: Mapping[str, Any]) -> dict[str, Any]:
    return _expected_freeze()


def _expected_execution_boundary() -> dict[str, Any]:
    return {
        "original_replay_count": 60,
        "p2d_post_action_reconstruction_count": 52,
        "continuation_candidate_count": 41,
        "p2d_direct_detector_endpoint_count": 11,
        "p2d_not_applicable_count": 8,
        "preflight_state_rng_context_checkpoint_count": 41,
        "continuation_execution_count": 41,
        "suppressed_stop_id": TARGET_STOP_ID,
        "suppression_mode": SUPPRESSION_MODE,
        "maximum_additional_action_count_per_pair": 6,
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
        "continuation_candidate_count": 41,
        "p2d_direct_detector_endpoint_count": 11,
        "p2d_not_applicable_count": 8,
        "continuation_candidate_indices": list(CONTINUATION_CANDIDATE_INDICES),
        "first_continuation_pair_index": 5,
    }


def _expected_definitions() -> dict[str, str]:
    return {
        "continuation_candidate": (
            "Accepted P2d action-decision row whose one non-detector action did not detect a bug and whose post-action common stop is no_bug_probability_threshold."
        ),
        "p2e_start": (
            "The retained post-action state, RNG, and execution context immediately after the accepted P2d non-detector action."
        ),
        "repeated_suppression": (
            "Suppress only no_bug_probability_threshold at every later pre-action decision while preserving all other accepted semantics."
        ),
        "policy_visibility": (
            "The selector receives only policy ID, retained state, remaining budget, and retained RNG; detector mapping is post-selection audit labeling."
        ),
        "direct_detector_endpoint": (
            "Stop immediately after a mapped direct-detector action returns the accepted bug-detected observation."
        ),
        "termination_boundary": (
            "End at direct-detector observation, the first accepted non-target stop, or no available action within accepted budget, max-step, and finite-action bounds."
        ),
    }


_LIMITATIONS = (
    "The audit covers 60 fixed same-domain pairs and 41 fixed continuation candidates.",
    "The detector mapping is ground-truth-informed and unavailable to deployable policies.",
    "The repeated threshold suppression is model-internal and bounded by the accepted budget, max-step, and finite-action contract.",
    "The hand-authored pairs are non-IID and do not establish unseen-variant or second-domain generalization.",
    "The implementation depends on identity-guarded accepted private helpers.",
    "The artifact preserves checkpoint digests and reduced traces rather than complete posterior, RNG, or execution-context payloads.",
)
_NON_CLAIMS = (
    "The audit does not establish that the threshold causally produced a miss or is a policy defect.",
    "The audit does not recommend repeated threshold suppression in production.",
    "The audit does not rank policies or establish policy superiority, improvement, or deployability.",
    "The audit does not introduce a new, seventh, tuned, or oracle policy.",
    "The audit does not identify an optimal or shortest sequence, dynamic-programming ceiling, or general upper bound.",
    "The audit does not establish clean no-diff safety, second-domain validity, or unseen-variant generalization.",
    "The audit does not provide confidence intervals, significance tests, causal effects, or production performance estimates.",
)
_NOTES = (
    "P2e preserves all accepted P1b, P2a, P2b, P2c, and P2d inputs and result artifacts unchanged.",
    "Software, artifact identity, descriptive result, and public documentation acceptance remain separate.",
    "Unexpected but valid frozen outcomes are reported without tuning.",
)


def _build_valid_summary(
    inputs: Mapping[str, Any], rows: list[dict[str, Any]]
) -> dict[str, Any]:
    summary = {
        "schema_version": SCHEMA_VERSION,
        "analysis_phase": ANALYSIS_PHASE,
        "report_role": REPORT_ROLE,
        "validation_status": {"status": VALID_STATUS},
        "input_identity": _input_identity(inputs),
        "pre_outcome_freeze": _freeze(inputs),
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
        "documentation_acceptance": _pending_acceptance(
            "public_result_documentation"
        ),
        "limitations": list(_LIMITATIONS),
        "non_claims": list(_NON_CLAIMS),
        "notes": list(_NOTES),
    }
    return validate_audit_summary(summary)


def _invalid_summary(
    reason_code: str, *, input_identity: dict[str, Any] | None = None
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
        "documentation_acceptance": _pending_acceptance(
            "public_result_documentation"
        ),
        "non_claims": [
            "Invalid input or execution cannot support partial P2e rows, aggregates, policy-performance, causal, deployment, or acceptance claims."
        ],
    }
    return validate_audit_summary(summary)


def _exact_fields(value: Any, fields: tuple[str, ...], path: str) -> dict[str, Any]:
    if type(value) is not dict or tuple(value) != fields:
        raise P2EContinuationAuditError(
            f"{path}: fields missing, extra, or reordered"
        )
    return value


def _assert_exact(actual: Any, expected: Any, path: str) -> None:
    if type(actual) is not type(expected):
        raise P2EContinuationAuditError(f"{path}: type drifted")
    if type(expected) is dict:
        if tuple(actual) != tuple(expected):
            raise P2EContinuationAuditError(f"{path}: fields or order drifted")
        for key in expected:
            _assert_exact(actual[key], expected[key], f"{path}.{key}")
        return
    if type(expected) is list:
        if len(actual) != len(expected):
            raise P2EContinuationAuditError(f"{path}: list support drifted")
        for index, (left, right) in enumerate(zip(actual, expected, strict=True)):
            _assert_exact(left, right, f"{path}[{index}]")
        return
    if actual != expected:
        raise P2EContinuationAuditError(f"{path}: value drifted")


def _assert_safe(value: Any) -> None:
    if type(value) is dict:
        for child in value.values():
            _assert_safe(child)
    elif type(value) is list:
        for child in value:
            _assert_safe(child)
    elif type(value) is float and not math.isfinite(value):
        raise P2EContinuationAuditError("summary contains non-finite value")
    elif type(value) is str and _LOCAL_PATH_RE.search(value):
        raise P2EContinuationAuditError("summary contains private absolute path")


def _assert_digest(value: Any, path: str) -> None:
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise P2EContinuationAuditError(f"{path}: digest is malformed")


def _validate_residual_rows(value: Any) -> str | None:
    if type(value) is not list or len(value) != 4:
        raise P2EContinuationAuditError("residual predicate support drifted")
    for row, stop_id in zip(value, RESIDUAL_STOP_IDS, strict=True):
        _exact_fields(row, ("stop_id", "fired"), "residual predicate")
        _assert_exact(row["stop_id"], stop_id, "residual predicate ID")
        if type(row["fired"]) is not bool:
            raise P2EContinuationAuditError("residual predicate is not boolean")
    return next((row["stop_id"] for row in value if row["fired"]), None)


def _validate_continuation(
    value: Any,
    *,
    baseline: Mapping[str, Any],
    p2c_source: Mapping[str, Any],
    start_state_digest: str,
) -> None:
    _exact_fields(value, _CONTINUATION_FIELDS, "continuation")
    _assert_exact(value["suppressed_stop_id"], TARGET_STOP_ID, "suppressed stop")
    _assert_exact(value["suppression_mode"], SUPPRESSION_MODE, "suppression mode")
    detector_ids = list(p2c_source["direct_detecting_action_ids"])
    executed = list(p2c_source["executed_action_ids"])
    p2d_action = baseline["p2d_selected_action_id"]
    executed.append(p2d_action)
    start_step = baseline["p2d_post_action_step"]
    start_cost = baseline["p2d_post_action_cumulative_cost"]
    expected_initial = _feasible_detector_ids(
        type("State", (), {"executed_actions": executed})(),
        detector_ids,
        12 - start_cost,
    )
    _assert_exact(
        value["initial_feasible_direct_detector_ids"],
        expected_initial,
        "initial detector feasibility",
    )
    _assert_exact(
        value["initial_direct_detector_budget_feasible"],
        bool(expected_initial),
        "initial detector feasibility bool",
    )
    maximum = min(6 - start_step, len([item for item in ACTION_IDS if item not in executed]))
    _assert_exact(
        value["maximum_additional_action_count"], maximum, "maximum action bound"
    )
    decisions = value["decisions"]
    if type(decisions) is not list or not decisions:
        raise P2EContinuationAuditError("continuation decisions are empty")

    expected_state_before: str = start_state_digest
    actions = 0
    additional_cost = 0
    feasibility_history: list[bool] = []
    selected_detector_id: str | None = None
    selected_detector_index: int | None = None
    final_reason: str | None = None
    for index, decision in enumerate(decisions, start=1):
        _exact_fields(decision, _DECISION_FIELDS, f"decisions[{index - 1}]")
        _assert_exact(decision["decision_index"], index, "decision index")
        _assert_exact(
            decision["absolute_decision_step"],
            start_step + actions + 1,
            "absolute decision step",
        )
        _assert_exact(
            decision["additional_actions_executed_before"],
            actions,
            "additional actions before",
        )
        _assert_exact(
            decision["cumulative_additional_cost_before"],
            additional_cost,
            "additional cost before",
        )
        _assert_digest(decision["state_digest_before"], "state before")
        _assert_exact(
            decision["state_digest_before"], expected_state_before, "state chain"
        )
        _assert_exact(
            decision["cumulative_cost_before"],
            start_cost + additional_cost,
            "cumulative cost before",
        )
        _assert_exact(
            decision["remaining_budget_before"],
            12 - start_cost - additional_cost,
            "remaining budget before",
        )
        expected_feasible = _feasible_detector_ids(
            type("State", (), {"executed_actions": executed})(),
            detector_ids,
            decision["remaining_budget_before"],
        )
        _assert_exact(
            decision["feasible_direct_detector_ids"],
            expected_feasible,
            "decision detector feasibility",
        )
        _assert_exact(
            decision["direct_detector_budget_feasible"],
            bool(expected_feasible),
            "decision detector feasibility bool",
        )
        feasibility_history.append(bool(expected_feasible))
        _assert_exact(decision["suppressed_stop_id"], TARGET_STOP_ID, "decision target")
        residual_result = _validate_residual_rows(
            decision["residual_stop_predicates"]
        )
        _assert_exact(
            decision["residual_stop_result"], residual_result, "residual result"
        )

        action_id = decision["selected_action_id"]
        terminal = decision["terminal_after_decision"]
        if type(terminal) is not bool:
            raise P2EContinuationAuditError("terminal flag is not boolean")
        if residual_result is not None:
            expected_tail = {
                "selection_attempted": False,
                "selected_action_id": None,
                "selected_action_cost": None,
                "selected_action_is_direct_detector": None,
                "observation_bug_detected": None,
                "state_digest_after": None,
                "post_action_cumulative_cost": None,
                "post_action_step": None,
                "post_action_common_stop_result": None,
                "terminal_after_decision": True,
                "terminal_reason": residual_result,
            }
            for field, expected in expected_tail.items():
                _assert_exact(decision[field], expected, f"residual decision.{field}")
            final_reason = residual_result
        elif action_id is None:
            expected_tail = {
                "selection_attempted": True,
                "selected_action_id": None,
                "selected_action_cost": None,
                "selected_action_is_direct_detector": None,
                "observation_bug_detected": None,
                "state_digest_after": None,
                "post_action_cumulative_cost": None,
                "post_action_step": None,
                "post_action_common_stop_result": None,
                "terminal_after_decision": True,
                "terminal_reason": "no_available_actions",
            }
            for field, expected in expected_tail.items():
                _assert_exact(decision[field], expected, f"no-available.{field}")
            final_reason = "no_available_actions"
        else:
            if type(action_id) is not str or action_id not in ACTION_IDS:
                raise P2EContinuationAuditError("selected action is invalid")
            if action_id in executed:
                raise P2EContinuationAuditError("selected action was already executed")
            cost = P1B_ACTION_SPECS[action_id].cost
            if cost > decision["remaining_budget_before"]:
                raise P2EContinuationAuditError("selected action exceeds budget")
            direct = action_id in detector_ids
            _assert_exact(decision["selection_attempted"], True, "selection attempted")
            _assert_exact(decision["selected_action_cost"], cost, "selected cost")
            _assert_exact(
                decision["selected_action_is_direct_detector"], direct, "detector label"
            )
            _assert_exact(
                decision["observation_bug_detected"], direct, "observation detection"
            )
            _assert_digest(decision["state_digest_after"], "state after")
            actions += 1
            additional_cost += cost
            executed.append(action_id)
            _assert_exact(
                decision["post_action_cumulative_cost"],
                start_cost + additional_cost,
                "post-action cost",
            )
            _assert_exact(
                decision["post_action_step"], start_step + actions, "post-action step"
            )
            post_stop = decision["post_action_common_stop_result"]
            if post_stop is not None and post_stop not in p2c_audit.STOP_REASON_IDS[:-1]:
                raise P2EContinuationAuditError("post-action stop reason is invalid")
            expected_state_before = decision["state_digest_after"]
            if direct:
                _assert_exact(terminal, True, "detector terminal flag")
                _assert_exact(
                    decision["terminal_reason"],
                    "direct_detector_observed",
                    "detector terminal reason",
                )
                selected_detector_id = action_id
                selected_detector_index = actions
                final_reason = "direct_detector_observed"
            else:
                _assert_exact(terminal, False, "non-detector terminal flag")
                _assert_exact(
                    decision["terminal_reason"], None, "non-detector terminal reason"
                )
        if terminal:
            if index != len(decisions):
                raise P2EContinuationAuditError("terminal decision has later decisions")
        elif index == len(decisions):
            raise P2EContinuationAuditError("final decision is not terminal")

    if any(
        not earlier and later
        for earlier, later in zip(feasibility_history, feasibility_history[1:])
    ):
        raise P2EContinuationAuditError("detector feasibility changed false to true")
    selected = selected_detector_id is not None
    _assert_exact(value["terminal_reason"], final_reason, "terminal reason")
    expected_outcome = (
        "direct_detector_observed"
        if final_reason == "direct_detector_observed"
        else "terminated_without_direct_detector"
    )
    _assert_exact(value["terminal_outcome"], expected_outcome, "terminal outcome")
    _assert_exact(value["direct_detector_selected"], selected, "detector selected")
    _assert_exact(
        value["direct_detector_observation_detected"], selected, "detector observed"
    )
    _assert_exact(
        value["direct_detector_selected_additional_action_index"],
        selected_detector_index,
        "detector action index",
    )
    _assert_exact(
        value["direct_detector_selected_action_id"],
        selected_detector_id,
        "detector action ID",
    )
    _assert_exact(value["additional_action_count"], actions, "additional action count")
    _assert_exact(
        value["cumulative_additional_cost"], additional_cost, "additional cost"
    )
    _assert_exact(value["final_step"], start_step + actions, "final step")
    _assert_exact(
        value["final_cumulative_cost"], start_cost + additional_cost, "final cost"
    )
    _assert_exact(
        value["final_remaining_budget"], 12 - start_cost - additional_cost, "final budget"
    )
    if not expected_initial:
        category = "initially_infeasible"
    elif selected:
        category = "initially_feasible_selected_direct_detector"
    elif not all(feasibility_history):
        category = "initially_feasible_became_infeasible_before_selection"
    else:
        category = "initially_feasible_through_non_detector_termination"
    _assert_exact(value["detector_feasibility_category"], category, "feasibility category")
    if actions > maximum or start_step + actions > 6 or start_cost + additional_cost > 12:
        raise P2EContinuationAuditError("accepted continuation bound exceeded")
    _assert_exact(
        value["continuation_trace_digest"],
        _canonical_digest(decisions),
        "continuation trace digest",
    )


def _validate_row(
    row: Any,
    index: int,
    source_row: Mapping[str, Any],
    p2c_source: Mapping[str, Any],
) -> None:
    _exact_fields(row, _ROW_FIELDS, f"pair_results[{index - 1}]")
    _assert_exact(row["pair_index"], index, "pair index")
    for field in ("variant_id", "bucket_id", "policy_id"):
        _assert_exact(row[field], source_row[field], field)
    source_digest = _canonical_digest(source_row)
    _assert_exact(row["p2d_source_row_sha256"], source_digest, "P2d source digest")
    _assert_exact(
        row["replayed_p2d_row_sha256"], source_digest, "replayed P2d digest"
    )
    _assert_exact(
        row["input_identity_checks"],
        {field: True for field in _INPUT_CHECK_FIELDS},
        "input checks",
    )
    classification = _classification(source_row)
    _assert_exact(row["classification"], classification, "classification")
    _assert_exact(row["p2d_replay_agreement"], True, "P2d replay agreement")
    candidate = classification == "continuation_candidate"
    for field in (
        "p2e_start_state_digest",
        "p2e_start_rng_state_digest",
        "p2e_start_execution_context_digest",
    ):
        if candidate:
            _assert_digest(row[field], field)
        else:
            _assert_exact(row[field], None, field)
    expected_baseline = _baseline(source_row)
    _assert_exact(row["baseline"], expected_baseline, "baseline")
    if candidate:
        _validate_continuation(
            row["continuation"],
            baseline=expected_baseline,
            p2c_source=p2c_source,
            start_state_digest=row["p2e_start_state_digest"],
        )
    else:
        _assert_exact(row["continuation"], None, "continuation separation")
    _assert_exact(
        row["row_consistency_checks"],
        {field: True for field in _ROW_CHECK_FIELDS},
        "row checks",
    )
    if _EXPECTED_PAIR_RESULT_DIGESTS:
        if len(_EXPECTED_PAIR_RESULT_DIGESTS) != 60:
            raise P2EContinuationAuditError("authoritative row digest support drifted")
        _assert_exact(
            _canonical_digest(row),
            _EXPECTED_PAIR_RESULT_DIGESTS[index - 1],
            "authoritative pair digest",
        )


def validate_audit_summary(summary: Any) -> dict[str, Any]:
    if type(summary) is not dict:
        raise P2EContinuationAuditError("summary must be an object")
    _assert_safe(summary)
    validation = summary.get("validation_status")
    status = validation.get("status") if type(validation) is dict else None
    if status == INVALID_STATUS:
        _exact_fields(summary, _INVALID_TOP_FIELDS, "summary")
        _assert_exact(summary["schema_version"], SCHEMA_VERSION, "schema")
        _assert_exact(summary["analysis_phase"], ANALYSIS_PHASE, "phase")
        _assert_exact(summary["report_role"], REPORT_ROLE, "role")
        _assert_exact(
            summary["validation_status"], {"status": INVALID_STATUS}, "status"
        )
        codes = summary["reason_codes"]
        if type(codes) is not list or not codes or len(codes) != len(set(codes)):
            raise P2EContinuationAuditError("invalid reason-code payload is malformed")
        if any(type(code) is not str or code not in INVALID_REASON_CODES for code in codes):
            raise P2EContinuationAuditError("invalid reason code is unsupported")
        if [code for code in INVALID_REASON_CODES if code in codes] != codes:
            raise P2EContinuationAuditError("invalid reason-code order drifted")
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
                "Invalid input or execution cannot support partial P2e rows, aggregates, policy-performance, causal, deployment, or acceptance claims."
            ],
            "invalid non-claims",
        )
        return summary
    if status != VALID_STATUS:
        raise P2EContinuationAuditError("summary status is invalid")

    _exact_fields(summary, _VALID_TOP_FIELDS, "summary")
    _assert_exact(summary["schema_version"], SCHEMA_VERSION, "schema")
    _assert_exact(summary["analysis_phase"], ANALYSIS_PHASE, "phase")
    _assert_exact(summary["report_role"], REPORT_ROLE, "role")
    _assert_exact(summary["validation_status"], {"status": VALID_STATUS}, "status")
    _assert_exact(summary["input_identity"], _expected_input_identity(), "input identity")
    _assert_exact(summary["pre_outcome_freeze"], _expected_freeze(), "freeze")
    _assert_exact(
        summary["execution_boundary"],
        _expected_execution_boundary(),
        "execution boundary",
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
    _assert_exact(summary["limitations"], list(_LIMITATIONS), "limitations")
    _assert_exact(summary["non_claims"], list(_NON_CLAIMS), "non-claims")
    _assert_exact(summary["notes"], list(_NOTES), "notes")

    p2d_summary = json.loads(_P2D_JSON_PATH.read_text(encoding="utf-8"))
    p2d_audit.validate_audit_summary(p2d_summary)
    p2c_summary = json.loads(p2d_audit._P2C_JSON_PATH.read_text(encoding="utf-8"))
    p2c_audit.validate_audit_summary(p2c_summary)
    rows = summary["pair_results"]
    if type(rows) is not list or len(rows) != 60:
        raise P2EContinuationAuditError("pair support is not exactly 60")
    for index, (row, p2d_row, p2c_row) in enumerate(
        zip(
            rows,
            p2d_summary["pair_results"],
            p2c_summary["pair_trajectories"],
            strict=True,
        ),
        start=1,
    ):
        _validate_row(row, index, p2d_row, p2c_row)
    aggregates = derive_aggregate_results(rows)
    _assert_exact(summary["aggregate_results"], aggregates, "aggregate results")
    overall = aggregates["overall"]
    _assert_exact(
        overall["classification_counts"],
        {
            "continuation_candidate": 41,
            "p2d_direct_detector_endpoint": 11,
            "p2d_not_applicable": 8,
        },
        "overall classification",
    )
    if sum(overall["candidate_terminal_reason_counts"].values()) != 41:
        raise P2EContinuationAuditError("candidate terminal partition drifted")
    if sum(overall["additional_action_count_distribution"].values()) != 41:
        raise P2EContinuationAuditError("action-count distribution drifted")
    if sum(overall["additional_cost_distribution"].values()) != 41:
        raise P2EContinuationAuditError("cost distribution drifted")
    if sum(overall["detector_feasibility_category_counts"].values()) != 41:
        raise P2EContinuationAuditError("feasibility partition drifted")
    validate_portable_value(summary, "p2e_summary")
    return summary


def _assert_same_run_identities(inputs: Mapping[str, Any]) -> None:
    """Fail closed if accepted inputs or current P2e files drift in one run."""

    post_rows, post_raw = _fresh_identity_snapshot()
    if post_rows != inputs["identity_rows"] or post_raw != inputs["raw_hashes"]:
        raise P2EContinuationAuditError("accepted input changed during execution")
    if _implementation_identity() != inputs["implementation_identity"]:
        raise P2EContinuationAuditError("P2e implementation identity changed")
    if _implementation_raw_snapshot() != inputs["implementation_raw_hashes"]:
        raise P2EContinuationAuditError("P2e implementation raw bytes changed")


def run_continuation_audit(
    *, event_log: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    """Run the frozen 60-pair replay and 41 bounded continuations."""

    events = event_log if event_log is not None else []
    events.append(
        {
            "event": "p2e_specification_frozen",
            "specification_sha256": SPECIFICATION_SHA256,
        }
    )
    events.append(
        {
            "event": "p2e_specification_review_accepted",
            "review_record_sha256": SPECIFICATION_REVIEW_RECORD_SHA256,
        }
    )
    try:
        inputs = _load_inputs()
    except Exception:  # noqa: BLE001 - fail closed before any continuation
        events.append(
            {
                "event": "p2e_preflight_failed",
                "reason_code": "accepted_input_identity_error",
            }
        )
        return _invalid_summary("accepted_input_identity_error")
    input_identity = _input_identity(inputs)
    events.append({"event": "p2e_identity_preflight_passed", "identity_count": 57})
    events.append(
        {
            "event": "p2e_original_replay_started",
            "pair_index": 1,
            "variant_id": BUGGY_VARIANT_IDS[0],
            "policy_id": FORMAL_POLICY_IDS[0],
        }
    )
    try:
        preflight = _preflight_checkpoints(inputs)
        events.append(
            {
                "event": "p2e_start_checkpoint_preflight_passed",
                "checkpoint_count": len(preflight),
            }
        )
        rows = _execute_all_pairs(inputs, preflight, events)
        events.append(
            {
                "event": "p2e_all_pairs_completed",
                "pair_count": len(rows),
                "continuation_candidate_count": len(preflight),
            }
        )
        _assert_same_run_identities(inputs)
        summary = _build_valid_summary(inputs, rows)
    except P2EContinuationAuditError as exc:
        events.append(
            {
                "event": "p2e_execution_failed",
                "reason_code": "continuation_contract_error",
                "diagnostic": str(exc),
            }
        )
        return _invalid_summary(
            "continuation_contract_error", input_identity=input_identity
        )
    except Exception:  # noqa: BLE001 - no partial outcome claims
        events.append(
            {
                "event": "p2e_execution_failed",
                "reason_code": "unexpected_audit_error",
            }
        )
        return _invalid_summary("unexpected_audit_error", input_identity=input_identity)
    events.append({"event": "p2e_summary_validated"})
    return summary


def record_artifacts_serialized(event_log: list[dict[str, Any]]) -> None:
    """Append the final event only after both versioned formats are written."""

    event_log.append({"event": "p2e_artifacts_serialized"})
