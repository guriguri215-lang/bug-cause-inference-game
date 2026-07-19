"""Canonical no-diff clean paired continuation audit.

P2f executes one exact clean baseline under the accepted six deterministic
policies.  Each policy has an accepted normal-control arm and a paired arm
that suppresses only ``no_bug_probability_threshold`` at every pre-action
decision.  The audit is fixed-input, analysis-only, model-internal,
non-causal, and non-deployable.
"""

from __future__ import annotations

import hashlib
import importlib
import itertools
import json
import math
import random
import shutil
import sys
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from types import ModuleType
from typing import Any

from bug_cause_inference.p1b import execution as p1b_execution
from bug_cause_inference.p1b import policies as p1b_policies
from bug_cause_inference.p1b.actions import P1B_ACTION_SPECS
from bug_cause_inference.p1b.dataset import LOCATION_CANDIDATES
from bug_cause_inference.p1b.models import (
    P1B_CAUSE_CATEGORIES,
    P1B_FIX_INTENT_CATEGORIES,
    P1BObservation,
    P1BSettings,
    rank_distribution,
    uniform_distribution,
)
from bug_cause_inference.p2a import evaluation as p2a_evaluation
from bug_cause_inference.p2a import execution as p2a_execution
from bug_cause_inference.p2a.adequacy import validate_portable_value
from bug_cause_inference.p2e import continuation_audit as p2e_audit


SCHEMA_VERSION = "p2f_canonical_no_diff_clean_paired_continuation_audit.v1"
ANALYSIS_PHASE = "P2f"
AUDIT_ID = "p2f_canonical_no_diff_clean_paired_continuation_audit_v1"
REPORT_ROLE = "analysis_only_fixed_input_clean_boundary"
VALID_STATUS = "valid"

BASE_COMMIT = "8daeb427be82e4596382911335fdb9c0b85be27f"
BASE_TREE = "f81aaaa268d835552cb1ab2b8cc3b0e4555f4fe8"
SPECIFICATION_SHA256 = (
    "70f8583eb9748ac6230e915336ad18e601aecdbcc55715f48780308fddc0ed6e"
)
SPECIFICATION_REVIEW_RECORD_SHA256 = (
    "0a2f4db60359d951f3ac7b2e764ec597d58b0d497b76be7165c57559adcb570a"
)

INPUT_ID = "P2F-NODIFF-001"
BASELINE_ID = "p1b_checkout_clean_v1"
BASELINE_MANIFEST_SHA256_LF = (
    "7740415235971faa8b990fcff31184f25a1445d82a6320815d42d6d9fa069c41"
)
INPUT_IDENTITY_CONTRACT_DIGEST = (
    "aca567fb7048aac2b6349a6383ec0aa601ceedde504724e4c75ddbf1e8729d0a"
)
P2E_INPUT_IDENTITY_CONTRACT_DIGEST = p2e_audit.IDENTITY_CONTRACT_DIGEST
BASELINE_CASE_ID_DIGEST = (
    "6a3b54794479c4c9d33de752cee77617a5a6f56f40334aba0ff8341b63edb8d5"
)
INITIAL_RNG_SEED = 6205

FORMAL_POLICY_IDS = (
    "fixed_checklist",
    "test_first",
    "coverage_first",
    "recent_diff_first",
    "cause_only_p1a_style",
    "expected_utility_per_cost",
)
ARM_IDS = ("normal_control", "target_suppressed_continuation")
ACTION_IDS = tuple(P1B_ACTION_SPECS)
TARGET_STOP_ID = "no_bug_probability_threshold"
RESIDUAL_STOP_IDS = (
    "bug_confidence_threshold",
    "budget_limit",
    "max_steps",
    "low_expected_utility",
)
STOP_REASON_IDS = (
    TARGET_STOP_ID,
    *RESIDUAL_STOP_IDS,
    "no_available_actions",
)
BASELINE_CASE_IDS = (
    "smoke.checkout_quote_threshold",
    "smoke.missing_coupon_noop",
    "smoke.digital_shipping",
    "smoke.preorder_reserve",
    "boundary.free_shipping_exact_threshold",
    "boundary.coupon_exact_minimum",
    "boundary.quantity_upper_boundary",
    "boundary.tax_half_up_rounding",
    "null_missing.coupon_none_noop",
    "null_missing.missing_region_default",
    "null_missing.none_cart_subtotal",
    "null_missing.missing_reserved_defaults_zero",
    "config.missing_jp_tax_default",
    "config.missing_feature_flag_no_stacking",
    "config.region_alias_rate",
    "config.free_shipping_threshold_override",
    "state.reserve_then_cancel",
    "state.double_coupon_idempotency",
    "state.removed_item_releases_reservation",
    "state.quote_after_cart_mutation",
    "property.free_shipping_boundary_vector",
    "property.coupon_idempotency",
    "property.total_consistency",
    "property.bogo_cheapest_rule",
    "property.preorder_reservation",
    "spec.discount_before_tax",
    "spec.bogo_cheapest_rule",
    "spec.digital_only_shipping",
    "spec.preorder_reservation",
)

BASELINE_FILE_ROWS = (
    ("checkout/__init__.py", 67, "41234f3dc364631d4c77ac22af1f07de9099314b0e69551ef0300b00df4f6ae5"),
    ("checkout/cart.py", 2290, "350cd07ed621cc22ba78e5915d4e956123e75d7246858f3502cfe9a7f9092e93"),
    ("checkout/config.py", 1749, "548a57f4ecd3f85e922fc62901d4b5a3a0c9f33cf6da6c3a15137f3dab83c231"),
    ("checkout/discounts.py", 1746, "4900a6cd8a14c87d2b2a66dfa6bb0017adfdfdd9513f3c08d1104612ec945ea2"),
    ("checkout/inventory.py", 883, "a62be8ae4c24b43adfc38da8e9c695483cfe80230102fc3dde55225bfc9b00b9"),
    ("checkout/shipping.py", 1179, "f0549311d9b41d298185a366ac92943b9b62eef75cc768fcccdc4fa0a380b439"),
)

IMPLEMENTATION_PATHS = (
    "src/bug_cause_inference/p2f/__init__.py",
    "src/bug_cause_inference/p2f/no_diff_clean_audit.py",
    "src/bug_cause_inference/p2f/reports.py",
    "tests/test_p2f_no_diff_clean_audit.py",
    "tests/test_p2f_reports.py",
)
FROZEN_IMPLEMENTATION_FILE_SHA256_LF = {
    "src/bug_cause_inference/p2f/__init__.py": "f04b73866e041663a582a3447987096b8bb57ccf55eb35544ef9a3caef13de37",
    "src/bug_cause_inference/p2f/no_diff_clean_audit.py": "d9f20ce7b7160771ab24df5585b3a854f0d523decef68f58e6d7e68e609e3ddc",
    "src/bug_cause_inference/p2f/reports.py": "aef7abf588ac1c68436a9e08cd30514474ee244069164c5ddfa998b1699836c5",
    "tests/test_p2f_no_diff_clean_audit.py": "3958740a6beda8421caf0b02665685791ca8abf21478725d1da843a033b54a5a",
    "tests/test_p2f_reports.py": "711160041d1f56bf514cfec2799e758694068b30aa6ec0c78a9916bcc9003f53",
}

_P2E_APPEND = (
    ("p2e_init_source", "src/bug_cause_inference/p2e/__init__.py", "bed9dc32d78fd419c34929a425d09800e53b536792dec16bac8c2eec398b98ff"),
    ("p2e_continuation_source", "src/bug_cause_inference/p2e/continuation_audit.py", "ffada38b510ed782e819751dbbc3ec9ec6e0cd2b4204a9be873f1c412f007947"),
    ("p2e_reports_source", "src/bug_cause_inference/p2e/reports.py", "48477174f16ad1caeaedfe5c5b165bb6c45a0c743592faaa46ea2dc2d1eb7566"),
    ("p2e_continuation_tests", "tests/test_p2e_continuation_audit.py", "8e539426ed28a8b8d7c5ba9a8636731a7e843425b853f2161899ba73252f93b0"),
    ("p2e_reports_tests", "tests/test_p2e_reports.py", "db658f234edef11ebf43a125e46eb2c657b06a7e44ea633631fe5d1c8067ee67"),
    ("p2e_json", "src/bug_cause_inference/p2e/artifacts/p2e_bounded_threshold_relaxation_continuation_audit_v1.json", "28af62b91f2a25ee4cb8f7aa4cef8186d6976863ae1fd8f0ac17f1d067befb61"),
    ("p2e_markdown", "src/bug_cause_inference/p2e/artifacts/p2e_bounded_threshold_relaxation_continuation_audit_v1.md", "a99e72e4334d76a74a5fb6c5a1e8b7c9d13975758d14238f178348c0fa135174"),
    ("p1b_real_diff_manifest", "src/bug_cause_inference/p1b/artifacts/real_diff/manifest.json", BASELINE_MANIFEST_SHA256_LF),
)

_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
_BASELINE_ROOT = _REPOSITORY_ROOT / "src/bug_cause_inference/p1b/artifacts/real_diff/baseline/checkout"
_MANIFEST_PATH = _REPOSITORY_ROOT / "src/bug_cause_inference/p1b/artifacts/real_diff/manifest.json"
_MODULE_NAMES = ("cart", "config", "discounts", "inventory", "shipping")
_NAMESPACE_COUNTER = itertools.count()

_TRAJECTORY_FIELDS = (
    "canonical_row_index", "pair_index", "input_id", "baseline_id",
    "policy_id", "arm_id", "input_identity_checks", "initial_state",
    "initial_state_digest", "initial_rng_state_digest",
    "initial_execution_context_digest", "initial_baseline_copy_digest",
    "settings_digest", "catalog_digest", "policy_digest", "decision_events",
    "selected_action_ids", "observations", "action_costs", "cumulative_cost",
    "action_count", "suppression_count", "first_divergence_checkpoint",
    "terminal_reason", "final_state", "final_state_digest",
    "final_rng_state_digest", "final_execution_context_digest",
    "final_bug_presence_posterior", "false_positive",
    "execution_failure_observed", "bug_detected_observation",
    "normal_no_bug_stop", "safe_non_bug_terminal",
    "empty_diff_observation_count", "trajectory_digest",
    "row_consistency_checks",
)
_DECISION_FIELDS = (
    "decision_index", "state_digest_before", "rng_state_digest_before",
    "execution_context_digest_before", "remaining_budget_before",
    "available_action_ids", "action_scores", "evaluated_stop_predicates",
    "target_predicate_value", "target_suppressed",
    "suppression_event_index", "residual_stop_result", "selection_attempted",
    "selected_action_id", "selected_action_cost", "observation",
    "state_digest_after", "rng_state_digest_after",
    "execution_context_digest_after", "terminal_after_decision",
    "terminal_reason",
)

_LIMITATIONS = (
    "The evidence covers one exact canonical no-diff clean baseline only.",
    "The twelve trajectories are six paired policy comparisons, not independent programs or replicates.",
    "The intervention is model-internal and is not a deployable policy.",
)
_NON_CLAIMS = (
    "The audit does not establish general clean safety or a population false-positive rate.",
    "The audit does not establish a threshold or policy defect, improvement, ranking, or recommendation.",
    "The audit does not combine P2e buggy benefit with P2f clean cost into a payoff or causal effect.",
    "The audit does not establish optimality, external validity, production readiness, or deployability.",
)


class P2FAuditError(ValueError):
    """Raised when the frozen P2f contract or a result is invalid."""


def _canonical_digest(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, allow_nan=False, separators=(",", ":")
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def _result_digest(value: Any) -> str:
    """Hash result payloads independently of JSON object insertion order."""

    payload = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def _hash_file(path: Path) -> tuple[str, str]:
    raw = path.read_bytes()
    canonical = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(canonical).hexdigest(), hashlib.sha256(raw).hexdigest()


def _repository_path(relative_path: str) -> Path:
    path = Path(relative_path)
    if path.is_absolute() or ".." in path.parts:
        raise P2FAuditError("identity path must be repository-relative")
    resolved = (_REPOSITORY_ROOT / path).resolve()
    if not resolved.is_relative_to(_REPOSITORY_ROOT):
        raise P2FAuditError("identity path escapes repository")
    return resolved


def _identity_rows() -> list[dict[str, str]]:
    rows = deepcopy(p2e_audit._identity_rows())
    if len(rows) != 57 or p2e_audit.identity_contract_digest(rows) != P2E_INPUT_IDENTITY_CONTRACT_DIGEST:
        raise P2FAuditError("inherited P2e identity contract drifted")
    rows.extend(
        {"identity": identity, "path": path, "sha256_lf": sha256_lf}
        for identity, path, sha256_lf in _P2E_APPEND
    )
    if len(rows) != 65 or len({row["identity"] for row in rows}) != 65:
        raise P2FAuditError("65-file input identity support drifted")
    if _canonical_digest(rows) != INPUT_IDENTITY_CONTRACT_DIGEST:
        raise P2FAuditError("65-file input identity digest drifted")
    return rows


def _fresh_identity_snapshot() -> tuple[list[dict[str, str]], dict[str, str]]:
    rows = _identity_rows()
    raw: dict[str, str] = {}
    for row in rows:
        portable, exact = _hash_file(_repository_path(row["path"]))
        if portable != row["sha256_lf"]:
            raise P2FAuditError(f"accepted input drifted: {row['identity']}")
        raw[row["identity"]] = exact
    return rows, raw


def implementation_identity() -> dict[str, str]:
    return {path: _hash_file(_repository_path(path))[0] for path in IMPLEMENTATION_PATHS}


def _implementation_raw_snapshot() -> dict[str, str]:
    return {path: _hash_file(_repository_path(path))[1] for path in IMPLEMENTATION_PATHS}


def _baseline_rows(root: Path = _BASELINE_ROOT) -> list[dict[str, Any]]:
    files = sorted(path for path in root.iterdir() if path.is_file())
    observed = []
    for path in files:
        relative = f"checkout/{path.name}"
        portable, _ = _hash_file(path)
        observed.append({"path": relative, "sha256_lf": portable})
    expected = [
        {"path": path, "sha256_lf": digest}
        for path, _raw_size, digest in BASELINE_FILE_ROWS
    ]
    if observed != expected:
        raise P2FAuditError("canonical baseline file identity drifted")
    return [
        {"path": path, "raw_size": raw_size, "sha256_lf": digest}
        for path, raw_size, digest in BASELINE_FILE_ROWS
    ]


def _validate_manifest() -> dict[str, Any]:
    portable, _ = _hash_file(_MANIFEST_PATH)
    manifest = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
    if portable != BASELINE_MANIFEST_SHA256_LF:
        raise P2FAuditError("real-diff manifest identity drifted")
    if manifest.get("baseline_id") != BASELINE_ID or manifest.get("baseline_root") != "baseline/checkout":
        raise P2FAuditError("canonical baseline manifest fields drifted")
    return manifest


@contextmanager
def isolated_baseline_checkout(work_root: Path) -> Iterator[tuple[dict[str, ModuleType], str, str]]:
    """Copy and import the exact baseline without a patch or manifest variant."""

    root = work_root.resolve()
    if root.is_relative_to((_REPOSITORY_ROOT / "src").resolve()):
        raise P2FAuditError("work root must not be inside versioned source")
    root.mkdir(parents=True, exist_ok=True)
    namespace = f"_p2f_baseline_{next(_NAMESPACE_COUNTER):08x}"
    package_root = root / namespace
    checkout_root = package_root / "checkout"
    prefix = f"{namespace}.checkout."
    try:
        shutil.copytree(_BASELINE_ROOT, checkout_root)
        (package_root / "__init__.py").write_text("", encoding="utf-8", newline="\n")
        copy_rows = _baseline_rows(checkout_root)
        digest = _canonical_digest(copy_rows)
        sys.path.insert(0, str(root))
        modules = {
            name: importlib.import_module(f"{namespace}.checkout.{name}")
            for name in _MODULE_NAMES
        }
        yield modules, prefix, digest
        if _baseline_rows(checkout_root) != copy_rows:
            raise P2FAuditError("isolated baseline copy drifted during execution")
    finally:
        if str(root) in sys.path:
            sys.path.remove(str(root))
        for name in [key for key in sys.modules if key == namespace or key.startswith(f"{namespace}.")]:
            sys.modules.pop(name, None)
        importlib.invalidate_caches()
        if package_root.exists():
            shutil.rmtree(package_root)


def _baseline_validity_gate(work_root: Path) -> dict[str, Any]:
    if tuple(p1b_execution.TEST_CASES) != BASELINE_CASE_IDS:
        raise P2FAuditError("baseline execution-test catalog order drifted")
    if _canonical_digest(list(BASELINE_CASE_IDS)) != BASELINE_CASE_ID_DIGEST:
        raise P2FAuditError("baseline execution-test catalog digest drifted")
    with isolated_baseline_checkout(work_root) as (modules, prefix, copy_digest):
        results = [
            p2a_execution._run_test_case(
                p1b_execution.TEST_CASES[test_id], INPUT_ID, modules, prefix
            )
            for test_id in BASELINE_CASE_IDS
        ]
    failed = [row for row in results if not row["passed"]]
    if failed:
        raise P2FAuditError("canonical baseline validity gate failed")
    return {
        "catalog_case_count": 29,
        "executed_case_count": len(results),
        "passed_case_count": len(results) - len(failed),
        "failed_case_count": len(failed),
        "ordered_case_id_digest": BASELINE_CASE_ID_DIGEST,
        "baseline_copy_digest": copy_digest,
    }


def _settings() -> P1BSettings:
    return P1BSettings(**p2a_evaluation._FIXED_SETTINGS)


def _new_state() -> p1b_policies._State:
    return p1b_policies._State(
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


def _state_payload(state: p1b_policies._State) -> dict[str, Any]:
    return {
        "bug_presence": state.bug_presence,
        "cause_posterior": dict(state.cause_posterior),
        "location_posterior": dict(state.location_posterior),
        "fix_intent_posterior": dict(state.fix_intent_posterior),
        "executed_actions": list(state.executed_actions),
        "cumulative_cost": state.cumulative_cost,
        "current_step": state.current_step,
        "bug_detected": state.bug_detected,
    }


def _state_digest(state: p1b_policies._State) -> str:
    return _result_digest(_state_payload(state))


def _portable_update_distribution(
    prior: dict[str, float], weights: dict[str, float]
) -> dict[str, float]:
    """Apply the accepted update with Python-version-stable normalization."""

    combined = {
        label: probability * weights.get(label, 1.0)
        for label, probability in prior.items()
    }
    total = math.fsum(max(value, 0.0) for value in combined.values())
    if total <= 0:
        if not combined:
            return {}
        value = 1.0 / len(combined)
        return {key: value for key in combined}
    return {key: max(value, 0.0) / total for key, value in combined.items()}


def _truthful_no_diff_observation() -> P1BObservation:
    return P1BObservation(
        action_id="inspect_recent_diff",
        cost=2,
        observation_type="recent_diff_signal",
        summary=(
            "inspect_recent_diff observed the canonical baseline with no applied "
            "patch; changed files: none; changed functions: none."
        ),
        bug_detected=False,
        failure_found=False,
        no_bug_evidence=False,
        evidence_source="p2f_truthful_no_diff",
        diff_artifact_path=None,
        changed_files=[],
        changed_functions=[],
        diff_excerpt="",
    )


def _run_action(
    *, action_id: str, state: p1b_policies._State,
    modules: Mapping[str, ModuleType], prefix: str,
) -> P1BObservation:
    if action_id == "inspect_recent_diff":
        observation = _truthful_no_diff_observation()
    else:
        observation = p2a_execution.run_patch_grounded_legacy_action(
            variant_id=INPUT_ID,
            action_id=action_id,
            context=state.execution_context,
            modules=dict(modules),
            module_prefix=prefix,
        )
        observation = replace(observation, evidence_source="p2f_canonical_baseline")
    if observation.cost != P1B_ACTION_SPECS[action_id].cost:
        raise P2FAuditError("action cost drifted")
    if any(not row["passed"] for row in observation.test_results):
        raise P2FAuditError("executed canonical baseline test failed")
    state.executed_actions.append(action_id)
    state.cumulative_cost += observation.cost
    state.current_step += 1
    state.bug_detected = state.bug_detected or observation.bug_detected
    state.bug_presence = p1b_policies._update_bug_presence(
        state.bug_presence, observation.bug_detected, observation.no_bug_evidence
    )
    state.cause_posterior = _portable_update_distribution(
        state.cause_posterior, observation.cause_scores
    )
    state.location_posterior = _portable_update_distribution(
        state.location_posterior, observation.location_scores
    )
    state.fix_intent_posterior = _portable_update_distribution(
        state.fix_intent_posterior, observation.fix_intent_scores
    )
    return observation


def _apply_recorded_observation(
    state: p1b_policies._State,
    action_id: str,
    observation: Mapping[str, Any],
) -> None:
    """Replay the accepted state/context update from a recorded observation."""

    if action_id not in {"inspect_recent_diff", "inspect_coverage_spectrum"}:
        recorded = deepcopy(observation["test_results"])
        state.execution_context.test_results.extend(recorded)
        state.execution_context.action_results.setdefault(action_id, []).extend(recorded)
    state.executed_actions.append(action_id)
    state.cumulative_cost += observation["cost"]
    state.current_step += 1
    state.bug_detected = state.bug_detected or observation["bug_detected"]
    state.bug_presence = p1b_policies._update_bug_presence(
        state.bug_presence,
        observation["bug_detected"],
        observation["no_bug_evidence"],
    )
    state.cause_posterior = _portable_update_distribution(
        state.cause_posterior, observation["cause_scores"]
    )
    state.location_posterior = _portable_update_distribution(
        state.location_posterior, observation["location_scores"]
    )
    state.fix_intent_posterior = _portable_update_distribution(
        state.fix_intent_posterior, observation["fix_intent_scores"]
    )


def _stop_projection(
    state: p1b_policies._State, settings: P1BSettings,
    scores: list[dict[str, Any]], arm_id: str,
) -> tuple[list[dict[str, Any]], bool, str | None, str | None]:
    best = scores[0]["expected_utility_per_cost"] if scores else None
    cause_top = rank_distribution(state.cause_posterior)[0]
    location_top = rank_distribution(state.location_posterior)[0]
    target = 1.0 - state.bug_presence >= settings.no_bug_probability_threshold
    values = {
        TARGET_STOP_ID: target,
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
    suppressed = arm_id == ARM_IDS[1] and target
    rows = [
        {
            "stop_id": stop_id,
            "value": bool(values[stop_id]),
            "suppressed": stop_id == TARGET_STOP_ID and suppressed,
        }
        for stop_id in (TARGET_STOP_ID, *RESIDUAL_STOP_IDS)
    ]
    residual = next((stop_id for stop_id in RESIDUAL_STOP_IDS if values[stop_id]), None)
    if arm_id == ARM_IDS[0] and target:
        terminal = TARGET_STOP_ID
    else:
        terminal = residual
    return rows, target, residual, terminal


def _available_action_ids(state: p1b_policies._State, remaining: int) -> list[str]:
    return [
        action_id for action_id, spec in P1B_ACTION_SPECS.items()
        if action_id not in state.executed_actions and spec.cost <= remaining
    ]


def _run_trajectory(
    *, row_index: int, pair_index: int, policy_id: str, arm_id: str,
    modules: Mapping[str, ModuleType], prefix: str, baseline_copy_digest: str,
) -> dict[str, Any]:
    settings = _settings()
    state = _new_state()
    rng = random.Random(INITIAL_RNG_SEED)
    initial_state = _state_payload(state)
    initial_state_digest = _state_digest(state)
    initial_rng_digest = p2e_audit.rng_state_digest(rng)
    initial_context_digest = p2e_audit.execution_context_digest(state.execution_context)
    decisions: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    suppression_count = 0
    terminal_reason: str | None = None

    while terminal_reason is None:
        before_state = _state_digest(state)
        before_rng = p2e_audit.rng_state_digest(rng)
        before_context = p2e_audit.execution_context_digest(state.execution_context)
        remaining = settings.budget_limit - state.cumulative_cost
        available = _available_action_ids(state, remaining)
        scores = p1b_policies.score_actions(state, remaining)
        stop_rows, target_value, residual, projected_terminal = _stop_projection(
            state, settings, scores, arm_id
        )
        target_suppressed = arm_id == ARM_IDS[1] and target_value
        if target_suppressed:
            suppression_count += 1
        base = {
            "decision_index": len(decisions) + 1,
            "state_digest_before": before_state,
            "rng_state_digest_before": before_rng,
            "execution_context_digest_before": before_context,
            "remaining_budget_before": remaining,
            "available_action_ids": available,
            "action_scores": scores,
            "evaluated_stop_predicates": stop_rows,
            "target_predicate_value": target_value,
            "target_suppressed": target_suppressed,
            "suppression_event_index": suppression_count if target_suppressed else None,
            "residual_stop_result": residual,
        }
        if projected_terminal is not None:
            terminal_reason = projected_terminal
            decisions.append({
                **base,
                "selection_attempted": False,
                "selected_action_id": None,
                "selected_action_cost": None,
                "observation": None,
                "state_digest_after": before_state,
                "rng_state_digest_after": before_rng,
                "execution_context_digest_after": before_context,
                "terminal_after_decision": True,
                "terminal_reason": terminal_reason,
            })
            break
        action_id = p1b_policies.choose_action(policy_id, state, remaining, rng)
        if action_id is None:
            terminal_reason = "no_available_actions"
            decisions.append({
                **base,
                "selection_attempted": True,
                "selected_action_id": None,
                "selected_action_cost": None,
                "observation": None,
                "state_digest_after": before_state,
                "rng_state_digest_after": before_rng,
                "execution_context_digest_after": before_context,
                "terminal_after_decision": True,
                "terminal_reason": terminal_reason,
            })
            break
        if action_id not in available:
            raise P2FAuditError("selector returned unavailable action")
        observation = _run_action(
            action_id=action_id, state=state, modules=modules, prefix=prefix
        )
        observation_payload = observation.to_dict()
        observations.append(observation_payload)
        decisions.append({
            **base,
            "selection_attempted": True,
            "selected_action_id": action_id,
            "selected_action_cost": observation.cost,
            "observation": observation_payload,
            "state_digest_after": _state_digest(state),
            "rng_state_digest_after": p2e_audit.rng_state_digest(rng),
            "execution_context_digest_after": p2e_audit.execution_context_digest(state.execution_context),
            "terminal_after_decision": False,
            "terminal_reason": None,
        })

    if terminal_reason not in STOP_REASON_IDS:
        raise P2FAuditError("trajectory terminal reason is invalid")
    false_positive = (
        terminal_reason == "bug_confidence_threshold"
        or state.bug_presence >= settings.bug_presence_threshold
    )
    execution_failure = any(
        not result["passed"]
        for observation in observations
        for result in observation["test_results"]
    )
    bug_observed = any(observation["bug_detected"] for observation in observations)
    row = {
        "canonical_row_index": row_index,
        "pair_index": pair_index,
        "input_id": INPUT_ID,
        "baseline_id": BASELINE_ID,
        "policy_id": policy_id,
        "arm_id": arm_id,
        "input_identity_checks": {
            "accepted_65_file_contract": True,
            "manifest_and_baseline_identity": True,
            "baseline_validity_gate": True,
            "implementation_freeze_identity": True,
        },
        "initial_state": initial_state,
        "initial_state_digest": initial_state_digest,
        "initial_rng_state_digest": initial_rng_digest,
        "initial_execution_context_digest": initial_context_digest,
        "initial_baseline_copy_digest": baseline_copy_digest,
        "settings_digest": "b11fe4cff40728a9225e154de36a4d56420f6d387ae6acec8d2b87009d30b954",
        "catalog_digest": "07b41b4d61a8b63250f62bb01e49ecca38ee2ab9f8124ba9d6c03c0f87fb84bb",
        "policy_digest": "02a25101cd10cacc6ddb2717cedf1a29c08643e44609be9909735263ae216def",
        "decision_events": decisions,
        "selected_action_ids": list(state.executed_actions),
        "observations": observations,
        "action_costs": [P1B_ACTION_SPECS[item].cost for item in state.executed_actions],
        "cumulative_cost": state.cumulative_cost,
        "action_count": state.current_step,
        "suppression_count": suppression_count,
        "first_divergence_checkpoint": None,
        "terminal_reason": terminal_reason,
        "final_state": _state_payload(state),
        "final_state_digest": _state_digest(state),
        "final_rng_state_digest": p2e_audit.rng_state_digest(rng),
        "final_execution_context_digest": p2e_audit.execution_context_digest(state.execution_context),
        "final_bug_presence_posterior": state.bug_presence,
        "false_positive": false_positive,
        "execution_failure_observed": execution_failure,
        "bug_detected_observation": bug_observed,
        "normal_no_bug_stop": arm_id == ARM_IDS[0] and terminal_reason == TARGET_STOP_ID,
        "safe_non_bug_terminal": arm_id == ARM_IDS[1] and not false_positive,
        "empty_diff_observation_count": sum(
            observation["action_id"] == "inspect_recent_diff"
            for observation in observations
        ),
        "trajectory_digest": "",
        "row_consistency_checks": {
            "canonical_order": True,
            "bounded_nonrepeating_actions": True,
            "truthful_empty_diff": True,
            "baseline_tests_passed": not execution_failure,
            "false_positive_definition": True,
            "terminal_complete": True,
        },
    }
    return row


def _trajectory_digest(row: Mapping[str, Any]) -> str:
    projected = dict(row)
    projected.pop("trajectory_digest", None)
    return _result_digest(projected)


def _pair_prefix(row: Mapping[str, Any]) -> list[dict[str, Any]]:
    return list(row["decision_events"])


def _predicate_values(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Project predicate rows while excluding the arm-specific audit marker."""

    return [
        {"stop_id": row["stop_id"], "value": row["value"]}
        for row in rows
    ]


def _finish_pair(control: dict[str, Any], intervention: dict[str, Any]) -> dict[str, Any]:
    if any(
        control[field] != intervention[field]
        for field in (
            "initial_state_digest", "initial_rng_state_digest",
            "initial_execution_context_digest", "initial_baseline_copy_digest",
        )
    ):
        raise P2FAuditError("paired start checkpoint mismatch")
    left = _pair_prefix(control)
    right = _pair_prefix(intervention)
    divergence: int | None = None
    prefix_agreement = True
    if control["terminal_reason"] == TARGET_STOP_ID:
        divergence = len(left)
        if len(right) < divergence or left[: divergence - 1] != right[: divergence - 1]:
            prefix_agreement = False
        else:
            keys = (
                "decision_index", "state_digest_before", "rng_state_digest_before",
                "execution_context_digest_before", "remaining_budget_before",
                "available_action_ids", "action_scores",
                "target_predicate_value", "residual_stop_result",
            )
            prefix_agreement = all(
                left[divergence - 1][key] == right[divergence - 1][key]
                for key in keys
            )
            prefix_agreement = prefix_agreement and _predicate_values(
                left[divergence - 1]["evaluated_stop_predicates"]
            ) == _predicate_values(
                right[divergence - 1]["evaluated_stop_predicates"]
            )
            prefix_agreement = prefix_agreement and right[divergence - 1]["target_suppressed"] is True
    else:
        prefix_agreement = left == right
    if not prefix_agreement:
        raise P2FAuditError("paired prefix integrity failed")
    control["first_divergence_checkpoint"] = divergence
    intervention["first_divergence_checkpoint"] = divergence
    control["trajectory_digest"] = _trajectory_digest(control)
    intervention["trajectory_digest"] = _trajectory_digest(intervention)
    pair = {
        "pair_index": control["pair_index"],
        "input_id": INPUT_ID,
        "policy_id": control["policy_id"],
        "control_row_index": control["canonical_row_index"],
        "intervention_row_index": intervention["canonical_row_index"],
        "start_checkpoint_agreement": True,
        "prefix_agreement_before_control_terminal": prefix_agreement,
        "first_divergence_checkpoint": divergence,
        "first_divergence_is_exact_target_suppression": divergence is not None,
        "control_terminal_reason": control["terminal_reason"],
        "intervention_terminal_reason": intervention["terminal_reason"],
        "control_false_positive": control["false_positive"],
        "intervention_false_positive": intervention["false_positive"],
        "false_positive_delta": int(intervention["false_positive"]) - int(control["false_positive"]),
        "control_action_count": control["action_count"],
        "intervention_action_count": intervention["action_count"],
        "action_count_delta": intervention["action_count"] - control["action_count"],
        "control_cost": control["cumulative_cost"],
        "intervention_cost": intervention["cumulative_cost"],
        "cost_delta": intervention["cumulative_cost"] - control["cumulative_cost"],
        "control_selected_action_ids": control["selected_action_ids"],
        "intervention_selected_action_ids": intervention["selected_action_ids"],
        "suppression_count": intervention["suppression_count"],
        "pair_digest": "",
    }
    pair["pair_digest"] = _result_digest(
        {key: value for key, value in pair.items() if key != "pair_digest"}
    )
    return pair


def derive_aggregate_results(
    rows: list[dict[str, Any]], pairs: list[dict[str, Any]], gate: dict[str, Any]
) -> dict[str, Any]:
    by_arm: dict[str, Any] = {}
    for arm_id in ARM_IDS:
        arm_rows = [row for row in rows if row["arm_id"] == arm_id]
        by_arm[arm_id] = {
            "support_policy_count": len(arm_rows),
            "false_positive_count": sum(row["false_positive"] for row in arm_rows),
            "false_positive_ratio": {
                "numerator": sum(row["false_positive"] for row in arm_rows),
                "denominator": 6,
                "unit": "policies",
            },
            "execution_failure_count": sum(row["execution_failure_observed"] for row in arm_rows),
            "bug_detected_observation_count": sum(row["bug_detected_observation"] for row in arm_rows),
            "terminal_reason_counts": {
                reason: sum(row["terminal_reason"] == reason for row in arm_rows)
                for reason in STOP_REASON_IDS
            },
            "selected_action_counts": {
                action_id: sum(row["selected_action_ids"].count(action_id) for row in arm_rows)
                for action_id in ACTION_IDS
            },
        }
    aggregate = {
        "support": {"input_count": 1, "policy_count": 6, "arm_count": 2, "trajectory_count": 12, "pair_count": 6},
        "by_arm": by_arm,
        "by_policy": [
            {
                "policy_id": pair["policy_id"],
                "control_terminal_reason": pair["control_terminal_reason"],
                "intervention_terminal_reason": pair["intervention_terminal_reason"],
                "false_positive_delta": pair["false_positive_delta"],
                "action_count_delta": pair["action_count_delta"],
                "cost_delta": pair["cost_delta"],
                "suppression_count": pair["suppression_count"],
            }
            for pair in pairs
        ],
        "false_positive_delta_counts": {
            str(delta): sum(pair["false_positive_delta"] == delta for pair in pairs)
            for delta in (-1, 0, 1)
        },
        "suppression_count_distribution": {
            str(count): sum(pair["suppression_count"] == count for pair in pairs)
            for count in range(8)
        },
        "suppression_policy_ids": {
            "zero": [pair["policy_id"] for pair in pairs if pair["suppression_count"] == 0],
            "one": [pair["policy_id"] for pair in pairs if pair["suppression_count"] == 1],
            "multiple": [pair["policy_id"] for pair in pairs if pair["suppression_count"] > 1],
        },
        "pair_start_checkpoint_agreement": {"numerator": sum(pair["start_checkpoint_agreement"] for pair in pairs), "denominator": 6},
        "pair_prefix_agreement": {"numerator": sum(pair["prefix_agreement_before_control_terminal"] for pair in pairs), "denominator": 6},
        "empty_diff_observations": {
            "execution_count": sum(row["empty_diff_observation_count"] for row in rows),
            "empty_fields_agreement_count": sum(
                observation["changed_files"] == []
                and observation["changed_functions"] == []
                and observation["diff_artifact_path"] is None
                for row in rows for observation in row["observations"]
                if observation["action_id"] == "inspect_recent_diff"
            ),
        },
        "baseline_validity_gate": gate,
        "digests": {
            "trajectory_results_digest": _result_digest(rows),
            "pair_results_digest": _result_digest(pairs),
            "aggregate_results_digest": None,
            "input_contract_digest": INPUT_IDENTITY_CONTRACT_DIGEST,
            "baseline_identity_digest": _canonical_digest(_baseline_rows()),
            "canonical_summary_digest": None,
        },
    }
    core = deepcopy(aggregate)
    core["digests"]["aggregate_results_digest"] = None
    core["digests"]["canonical_summary_digest"] = None
    aggregate["digests"]["aggregate_results_digest"] = _result_digest(core)
    return aggregate


def _pending(scope: str) -> dict[str, str]:
    return {"scope": scope, "status": "pending_separate_external_acceptance"}


def _summary_digest(summary: Mapping[str, Any]) -> str:
    projected = deepcopy(summary)
    projected["aggregate_results"]["digests"]["canonical_summary_digest"] = None
    return _result_digest(projected)


def _expected_population() -> dict[str, Any]:
    return {
        "input_ids": [INPUT_ID],
        "baseline_id": BASELINE_ID,
        "policy_ids": list(FORMAL_POLICY_IDS),
        "arm_ids": list(ARM_IDS),
        "order": "input_major_policy_major_arm_minor",
        "trajectory_count": 12,
        "pair_count": 6,
        "independent_program_count": 1,
    }


def validate_audit_summary(summary: Any) -> dict[str, Any]:
    if type(summary) is not dict:
        raise P2FAuditError("summary must be an object")
    expected_top = {
        "schema_version", "analysis_phase", "audit_id", "report_role",
        "validation_status", "input_identity", "pre_outcome_freeze",
        "execution_boundary", "population", "definitions",
        "trajectory_results", "pair_results", "aggregate_results",
        "software_acceptance", "artifact_identity_acceptance",
        "result_acceptance", "documentation_acceptance", "limitations",
        "non_claims", "notes",
    }
    if set(summary) != expected_top:
        raise P2FAuditError("top-level schema fields drifted")
    if summary["schema_version"] != SCHEMA_VERSION or summary["analysis_phase"] != ANALYSIS_PHASE:
        raise P2FAuditError("schema or phase drifted")
    if summary["audit_id"] != AUDIT_ID or summary["report_role"] != REPORT_ROLE:
        raise P2FAuditError("audit identity drifted")
    if summary["validation_status"] != {"status": VALID_STATUS}:
        raise P2FAuditError("validation status drifted")
    rows, _ = _fresh_identity_snapshot()
    identity = summary["input_identity"]
    if identity != {
        "base_commit": BASE_COMMIT,
        "base_tree": BASE_TREE,
        "identity_rows": rows,
        "identity_contract_digest": INPUT_IDENTITY_CONTRACT_DIGEST,
        "baseline_file_rows": _baseline_rows(),
        "baseline_manifest_sha256_lf": BASELINE_MANIFEST_SHA256_LF,
        "implementation_file_sha256_lf": deepcopy(
            FROZEN_IMPLEMENTATION_FILE_SHA256_LF
        ),
    }:
        raise P2FAuditError("accepted input identity payload drifted")
    freeze = summary["pre_outcome_freeze"]
    if freeze != {
        "specification_sha256_lf": SPECIFICATION_SHA256,
        "specification_review_record_sha256_lf": SPECIFICATION_REVIEW_RECORD_SHA256,
        "implementation_file_sha256_lf": deepcopy(
            FROZEN_IMPLEMENTATION_FILE_SHA256_LF
        ),
        "first_outcome_executed_after_freeze": True,
    }:
        raise P2FAuditError("pre-outcome freeze payload drifted")
    if summary["execution_boundary"] != {
        "input_semantics": "exact canonical baseline with no patch",
        "control_semantics": "accepted normal stop/action/update loop",
        "intervention_semantics": "suppress only no_bug_probability_threshold at every pre-action decision",
        "baseline_validity_gate": "all 29 accepted execution tests must pass",
    }:
        raise P2FAuditError("execution boundary drifted")
    if summary["definitions"] != {
        "false_positive": "terminal bug_confidence_threshold OR final bug_presence_posterior >= 0.75",
        "execution_failure_observed": "any executed canonical baseline test or oracle failed",
        "bug_detected_observation": "any observation has bug_detected=true",
        "normal_no_bug_stop": "normal control terminates at no_bug_probability_threshold",
        "safe_non_bug_terminal": "intervention terminal without false positive; not a general safety claim",
    }:
        raise P2FAuditError("definitions drifted")
    if summary["population"] != _expected_population():
        raise P2FAuditError("population drifted")
    trajectory_rows = summary["trajectory_results"]
    if type(trajectory_rows) is not list or len(trajectory_rows) != 12:
        raise P2FAuditError("trajectory support is not exactly 12")
    for index, row in enumerate(trajectory_rows, start=1):
        if set(row) != set(_TRAJECTORY_FIELDS):
            raise P2FAuditError("trajectory fields drifted")
        policy = FORMAL_POLICY_IDS[(index - 1) // 2]
        arm = ARM_IDS[(index - 1) % 2]
        if (row["canonical_row_index"], row["pair_index"], row["policy_id"], row["arm_id"]) != (index, (index + 1) // 2, policy, arm):
            raise P2FAuditError("canonical trajectory order drifted")
        if row["input_id"] != INPUT_ID or row["baseline_id"] != BASELINE_ID:
            raise P2FAuditError("trajectory input identity drifted")
        if row["input_identity_checks"] != {
            "accepted_65_file_contract": True,
            "manifest_and_baseline_identity": True,
            "baseline_validity_gate": True,
            "implementation_freeze_identity": True,
        }:
            raise P2FAuditError("trajectory input checks drifted")
        if row["initial_state"] != _state_payload(_new_state()):
            raise P2FAuditError("trajectory initial state drifted")
        if row["initial_state_digest"] != _result_digest(row["initial_state"]):
            raise P2FAuditError("trajectory initial state digest drifted")
        expected_rng = p2e_audit.rng_state_digest(random.Random(INITIAL_RNG_SEED))
        expected_context = p2e_audit.execution_context_digest(
            p1b_execution.P1BExecutionContext()
        )
        if row["initial_rng_state_digest"] != expected_rng:
            raise P2FAuditError("trajectory initial RNG drifted")
        if row["initial_execution_context_digest"] != expected_context:
            raise P2FAuditError("trajectory initial execution context drifted")
        if row["initial_baseline_copy_digest"] != _canonical_digest(_baseline_rows()):
            raise P2FAuditError("trajectory baseline copy drifted")
        if (
            row["settings_digest"] != "b11fe4cff40728a9225e154de36a4d56420f6d387ae6acec8d2b87009d30b954"
            or row["catalog_digest"] != "07b41b4d61a8b63250f62bb01e49ecca38ee2ab9f8124ba9d6c03c0f87fb84bb"
            or row["policy_digest"] != "02a25101cd10cacc6ddb2717cedf1a29c08643e44609be9909735263ae216def"
        ):
            raise P2FAuditError("accepted settings, catalog, or policy digest drifted")
        if row["action_count"] != len(row["selected_action_ids"]) or row["action_count"] != len(row["observations"]):
            raise P2FAuditError("trajectory action count drifted")
        expected_costs = [P1B_ACTION_SPECS[action].cost for action in row["selected_action_ids"]]
        if row["action_costs"] != expected_costs or row["cumulative_cost"] != sum(expected_costs):
            raise P2FAuditError("trajectory action cost drifted")
        if len(set(row["selected_action_ids"])) != len(row["selected_action_ids"]):
            raise P2FAuditError("trajectory repeated an action")
        if row["cumulative_cost"] > 12 or row["action_count"] > 6:
            raise P2FAuditError("trajectory exceeded a bound")
        if row["terminal_reason"] not in STOP_REASON_IDS:
            raise P2FAuditError("trajectory terminal reason drifted")
        if row["false_positive"] != (
            row["terminal_reason"] == "bug_confidence_threshold"
            or row["final_bug_presence_posterior"] >= 0.75
        ):
            raise P2FAuditError("false-positive definition drifted")
        events = row["decision_events"]
        if type(events) is not list or not events or not events[-1]["terminal_after_decision"]:
            raise P2FAuditError("trajectory decision termination drifted")
        suppression_index = 0
        observation_index = 0
        previous_after = row["initial_state_digest"]
        replay_state = _new_state()
        replay_rng = random.Random(INITIAL_RNG_SEED)
        settings = _settings()
        for decision_index, event in enumerate(events, start=1):
            if set(event) != set(_DECISION_FIELDS) or event["decision_index"] != decision_index:
                raise P2FAuditError("decision schema or index drifted")
            if event["state_digest_before"] != previous_after:
                raise P2FAuditError("decision state chain drifted")
            if (
                event["state_digest_before"] != _state_digest(replay_state)
                or event["rng_state_digest_before"]
                != p2e_audit.rng_state_digest(replay_rng)
                or event["execution_context_digest_before"]
                != p2e_audit.execution_context_digest(replay_state.execution_context)
            ):
                raise P2FAuditError("decision checkpoint replay drifted")
            remaining = settings.budget_limit - replay_state.cumulative_cost
            expected_available = _available_action_ids(replay_state, remaining)
            expected_scores = p1b_policies.score_actions(replay_state, remaining)
            if event["remaining_budget_before"] != remaining:
                raise P2FAuditError("remaining budget projection drifted")
            if event["available_action_ids"] != expected_available:
                raise P2FAuditError("available-action completeness or order drifted")
            if event["action_scores"] != expected_scores:
                raise P2FAuditError("action-score completeness or order drifted")
            predicates = event["evaluated_stop_predicates"]
            if (
                type(predicates) is not list
                or [item.get("stop_id") for item in predicates]
                != [TARGET_STOP_ID, *RESIDUAL_STOP_IDS]
                or any(set(item) != {"stop_id", "value", "suppressed"} for item in predicates)
                or any(type(item["value"]) is not bool for item in predicates)
            ):
                raise P2FAuditError("evaluated stop predicates drifted")
            (
                expected_predicates,
                expected_target,
                expected_residual,
                expected_terminal,
            ) = _stop_projection(
                replay_state,
                settings,
                expected_scores,
                row["arm_id"],
            )
            if (
                predicates != expected_predicates
                or event["target_predicate_value"] is not expected_target
                or event["target_suppressed"]
                is not (row["arm_id"] == ARM_IDS[1] and expected_target)
                or event["residual_stop_result"] != expected_residual
            ):
                raise P2FAuditError("stop projection or suppression semantics drifted")
            if event["target_suppressed"]:
                suppression_index += 1
                if event["suppression_event_index"] != suppression_index or not event["target_predicate_value"]:
                    raise P2FAuditError("suppression index drifted")
            elif event["suppression_event_index"] is not None:
                raise P2FAuditError("non-suppression carried an index")
            action_id = event["selected_action_id"]
            if expected_terminal is not None:
                if (
                    event["selection_attempted"] is not False
                    or action_id is not None
                    or event["selected_action_cost"] is not None
                    or event["observation"] is not None
                    or event["terminal_after_decision"] is not True
                    or event["terminal_reason"] != expected_terminal
                ):
                    raise P2FAuditError("terminal decision truth table drifted")
                if any(
                    event[after] != event[before]
                    for after, before in (
                        ("state_digest_after", "state_digest_before"),
                        ("rng_state_digest_after", "rng_state_digest_before"),
                        (
                            "execution_context_digest_after",
                            "execution_context_digest_before",
                        ),
                    )
                ):
                    raise P2FAuditError("terminal checkpoint changed without action")
            elif action_id is None:
                if event["selected_action_cost"] is not None or event["observation"] is not None:
                    raise P2FAuditError("non-action nullable semantics drifted")
                if any(event[after] != event[before] for after, before in (
                    ("state_digest_after", "state_digest_before"),
                    ("rng_state_digest_after", "rng_state_digest_before"),
                    ("execution_context_digest_after", "execution_context_digest_before"),
                )):
                    raise P2FAuditError("terminal/no-action digest semantics drifted")
                if not event["terminal_after_decision"] or event["terminal_reason"] is None:
                    raise P2FAuditError("non-action terminal semantics drifted")
                if (
                    event["selection_attempted"] is not True
                    or event["terminal_reason"] != "no_available_actions"
                    or expected_available
                ):
                    raise P2FAuditError("no-available-actions truth table drifted")
            else:
                if event["selected_action_cost"] != P1B_ACTION_SPECS[action_id].cost or type(event["observation"]) is not dict:
                    raise P2FAuditError("selected-action payload drifted")
                if event["terminal_after_decision"] or event["terminal_reason"] is not None:
                    raise P2FAuditError("action terminated before next checkpoint")
                if event["selection_attempted"] is not True:
                    raise P2FAuditError("selected-action truth table drifted")
                if action_id not in event["available_action_ids"]:
                    raise P2FAuditError("selected action was unavailable")
                expected_action = p1b_policies.choose_action(
                    row["policy_id"], replay_state, remaining, replay_rng
                )
                if action_id != expected_action:
                    raise P2FAuditError("frozen policy selection drifted")
                if event["observation"] != row["observations"][observation_index]:
                    raise P2FAuditError("decision observation chain drifted")
                if action_id != row["selected_action_ids"][observation_index]:
                    raise P2FAuditError("decision selected-action chain drifted")
                _apply_recorded_observation(replay_state, action_id, event["observation"])
                if (
                    event["state_digest_after"] != _state_digest(replay_state)
                    or event["rng_state_digest_after"]
                    != p2e_audit.rng_state_digest(replay_rng)
                    or event["execution_context_digest_after"]
                    != p2e_audit.execution_context_digest(
                        replay_state.execution_context
                    )
                ):
                    raise P2FAuditError("post-action checkpoint replay drifted")
                observation_index += 1
            previous_after = event["state_digest_after"]
        if observation_index != len(row["observations"]):
            raise P2FAuditError("decision observation support drifted")
        if suppression_index != row["suppression_count"]:
            raise P2FAuditError("trajectory suppression count drifted")
        if row["final_state_digest"] != previous_after:
            raise P2FAuditError("final state digest drifted")
        if row["final_state_digest"] != _result_digest(row["final_state"]):
            raise P2FAuditError("final state payload drifted")
        if (
            row["final_state"]["executed_actions"] != row["selected_action_ids"]
            or row["final_state"]["cumulative_cost"] != row["cumulative_cost"]
            or row["final_state"]["current_step"] != row["action_count"]
            or row["final_state"]["bug_presence"] != row["final_bug_presence_posterior"]
        ):
            raise P2FAuditError("final state projection drifted")
        if (
            row["final_rng_state_digest"] != events[-1]["rng_state_digest_after"]
            or row["final_execution_context_digest"]
            != events[-1]["execution_context_digest_after"]
        ):
            raise P2FAuditError("final RNG or execution context drifted")
        for observation in row["observations"]:
            if any(not result["passed"] for result in observation["test_results"]):
                raise P2FAuditError("valid trajectory contains a failed test")
            if observation["action_id"] == "inspect_recent_diff" and observation != _truthful_no_diff_observation().to_dict():
                raise P2FAuditError("truthful no-diff observation drifted")
        if row["execution_failure_observed"]:
            raise P2FAuditError("valid clean trajectory records execution failure")
        if row["bug_detected_observation"] != any(
            observation["bug_detected"] for observation in row["observations"]
        ):
            raise P2FAuditError("bug-detected observation projection drifted")
        if row["normal_no_bug_stop"] != (
            row["arm_id"] == ARM_IDS[0] and row["terminal_reason"] == TARGET_STOP_ID
        ):
            raise P2FAuditError("normal no-bug stop projection drifted")
        if row["safe_non_bug_terminal"] != (
            row["arm_id"] == ARM_IDS[1] and not row["false_positive"]
        ):
            raise P2FAuditError("safe non-bug terminal projection drifted")
        if row["empty_diff_observation_count"] != sum(
            observation["action_id"] == "inspect_recent_diff"
            for observation in row["observations"]
        ):
            raise P2FAuditError("empty-diff observation count drifted")
        if row["row_consistency_checks"] != {
            "canonical_order": True,
            "bounded_nonrepeating_actions": True,
            "truthful_empty_diff": True,
            "baseline_tests_passed": True,
            "false_positive_definition": True,
            "terminal_complete": True,
        }:
            raise P2FAuditError("row consistency checks drifted")
        if row["trajectory_digest"] != _trajectory_digest(row):
            raise P2FAuditError("trajectory digest drifted")
    expected_pairs = []
    cloned_rows = deepcopy(trajectory_rows)
    for pair_index in range(6):
        expected_pairs.append(_finish_pair(cloned_rows[2 * pair_index], cloned_rows[2 * pair_index + 1]))
    if summary["pair_results"] != expected_pairs:
        raise P2FAuditError("pair results drifted")
    expected_aggregate = derive_aggregate_results(
        trajectory_rows, summary["pair_results"], summary["aggregate_results"]["baseline_validity_gate"]
    )
    expected_aggregate["digests"]["canonical_summary_digest"] = summary[
        "aggregate_results"
    ]["digests"]["canonical_summary_digest"]
    if summary["aggregate_results"] != expected_aggregate:
        raise P2FAuditError("aggregate results drifted")
    if summary["aggregate_results"]["baseline_validity_gate"] != {
        "catalog_case_count": 29,
        "executed_case_count": 29,
        "passed_case_count": 29,
        "failed_case_count": 0,
        "ordered_case_id_digest": BASELINE_CASE_ID_DIGEST,
        "baseline_copy_digest": _canonical_digest(_baseline_rows()),
    }:
        raise P2FAuditError("baseline validity gate payload drifted")
    for field, scope in (
        ("software_acceptance", "software_conformance"),
        ("artifact_identity_acceptance", "versioned_artifact_identity"),
        ("result_acceptance", "descriptive_result"),
        ("documentation_acceptance", "public_result_documentation"),
    ):
        if summary[field] != _pending(scope):
            raise P2FAuditError("acceptance field became self-accepting")
    if summary["limitations"] != list(_LIMITATIONS) or summary["non_claims"] != list(_NON_CLAIMS):
        raise P2FAuditError("claim boundary drifted")
    if summary["notes"] != [
        "P2a benign-diff clean evidence and P2e buggy continuation evidence are not pooled into this denominator.",
        "External review records, not this artifact, decide acceptance.",
    ]:
        raise P2FAuditError("notes drifted")
    if summary["aggregate_results"]["digests"]["canonical_summary_digest"] != _summary_digest(summary):
        raise P2FAuditError("canonical summary digest drifted")
    validate_portable_value(summary, "p2f_summary")
    return summary


def run_no_diff_clean_audit(
    *, expected_implementation_identity: Mapping[str, str], work_root: Path,
    event_log: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run the frozen first/fresh P2f audit under an external freeze identity."""

    events = event_log if event_log is not None else []
    events.extend([
        {"event": "p2f_specification_frozen", "sha256_lf": SPECIFICATION_SHA256},
        {"event": "p2f_specification_review_accepted", "sha256_lf": SPECIFICATION_REVIEW_RECORD_SHA256},
    ])
    expected = dict(expected_implementation_identity)
    implementation_before = implementation_identity()
    if tuple(expected) != IMPLEMENTATION_PATHS or expected != FROZEN_IMPLEMENTATION_FILE_SHA256_LF:
        raise P2FAuditError("implementation differs from external pre-outcome freeze")
    events.append({"event": "p2f_implementation_freeze_verified", "file_count": 5})
    _validate_manifest()
    baseline_rows = _baseline_rows()
    identity_rows, input_raw_before = _fresh_identity_snapshot()
    implementation_raw_before = _implementation_raw_snapshot()
    gate = _baseline_validity_gate(work_root / "baseline-gate")
    events.append({"event": "p2f_baseline_validity_gate_passed", "passed": 29, "total": 29})

    trajectories: list[dict[str, Any]] = []
    pairs: list[dict[str, Any]] = []
    row_index = 0
    for pair_index, policy_id in enumerate(FORMAL_POLICY_IDS, start=1):
        pair_rows = []
        for arm_id in ARM_IDS:
            row_index += 1
            with isolated_baseline_checkout(work_root / f"row-{row_index:02d}") as (modules, prefix, copy_digest):
                row = _run_trajectory(
                    row_index=row_index,
                    pair_index=pair_index,
                    policy_id=policy_id,
                    arm_id=arm_id,
                    modules=modules,
                    prefix=prefix,
                    baseline_copy_digest=copy_digest,
                )
            pair_rows.append(row)
        pair = _finish_pair(pair_rows[0], pair_rows[1])
        trajectories.extend(pair_rows)
        pairs.append(pair)
        events.append({"event": "p2f_pair_completed", "pair_index": pair_index, "policy_id": policy_id})

    aggregate = derive_aggregate_results(trajectories, pairs, gate)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "analysis_phase": ANALYSIS_PHASE,
        "audit_id": AUDIT_ID,
        "report_role": REPORT_ROLE,
        "validation_status": {"status": VALID_STATUS},
        "input_identity": {
            "base_commit": BASE_COMMIT,
            "base_tree": BASE_TREE,
            "identity_rows": identity_rows,
            "identity_contract_digest": INPUT_IDENTITY_CONTRACT_DIGEST,
            "baseline_file_rows": baseline_rows,
            "baseline_manifest_sha256_lf": BASELINE_MANIFEST_SHA256_LF,
            "implementation_file_sha256_lf": deepcopy(
                FROZEN_IMPLEMENTATION_FILE_SHA256_LF
            ),
        },
        "pre_outcome_freeze": {
            "specification_sha256_lf": SPECIFICATION_SHA256,
            "specification_review_record_sha256_lf": SPECIFICATION_REVIEW_RECORD_SHA256,
            "implementation_file_sha256_lf": deepcopy(
                FROZEN_IMPLEMENTATION_FILE_SHA256_LF
            ),
            "first_outcome_executed_after_freeze": True,
        },
        "execution_boundary": {
            "input_semantics": "exact canonical baseline with no patch",
            "control_semantics": "accepted normal stop/action/update loop",
            "intervention_semantics": "suppress only no_bug_probability_threshold at every pre-action decision",
            "baseline_validity_gate": "all 29 accepted execution tests must pass",
        },
        "population": _expected_population(),
        "definitions": {
            "false_positive": "terminal bug_confidence_threshold OR final bug_presence_posterior >= 0.75",
            "execution_failure_observed": "any executed canonical baseline test or oracle failed",
            "bug_detected_observation": "any observation has bug_detected=true",
            "normal_no_bug_stop": "normal control terminates at no_bug_probability_threshold",
            "safe_non_bug_terminal": "intervention terminal without false positive; not a general safety claim",
        },
        "trajectory_results": trajectories,
        "pair_results": pairs,
        "aggregate_results": aggregate,
        "software_acceptance": _pending("software_conformance"),
        "artifact_identity_acceptance": _pending("versioned_artifact_identity"),
        "result_acceptance": _pending("descriptive_result"),
        "documentation_acceptance": _pending("public_result_documentation"),
        "limitations": list(_LIMITATIONS),
        "non_claims": list(_NON_CLAIMS),
        "notes": [
            "P2a benign-diff clean evidence and P2e buggy continuation evidence are not pooled into this denominator.",
            "External review records, not this artifact, decide acceptance.",
        ],
    }
    summary["aggregate_results"]["digests"]["canonical_summary_digest"] = _summary_digest(summary)
    _, input_raw_after = _fresh_identity_snapshot()
    if input_raw_after != input_raw_before:
        raise P2FAuditError("accepted input raw bytes changed during execution")
    if implementation_identity() != implementation_before:
        raise P2FAuditError("implementation LF-normalized bytes changed during execution")
    if _implementation_raw_snapshot() != implementation_raw_before:
        raise P2FAuditError("implementation raw bytes changed during execution")
    validated = validate_audit_summary(summary)
    events.append({"event": "p2f_audit_validated", "trajectory_count": 12, "pair_count": 6})
    return validated


def record_artifacts_serialized(event_log: list[dict[str, Any]]) -> None:
    event_log.append({"event": "p2f_artifacts_serialized"})
