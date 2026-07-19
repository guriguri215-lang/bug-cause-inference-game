"""Accepted benign-diff clean paired continuation audit.

P2g replays the exact five accepted P2a clean patches under the six frozen
formal policies.  Each input-policy pair has an accepted normal-control arm
and a paired arm that suppresses only ``no_bug_probability_threshold`` at
every pre-action decision.  The result is fixed-input, analysis-only,
model-internal, non-causal, and non-deployable.
"""

from __future__ import annotations

import hashlib
import json
import random
import shutil
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from types import ModuleType
from typing import Any

from bug_cause_inference.p1b import policies as p1b_policies
from bug_cause_inference.p1b.actions import P1B_ACTION_SPECS
from bug_cause_inference.p1b.real_diff import (
    apply_unified_patch,
    generated_checkout_imports,
)
from bug_cause_inference.p2a import evaluation as p2a_evaluation
from bug_cause_inference.p2a.adequacy import validate_portable_value
from bug_cause_inference.p2a.candidate_oracles import run_oracle
from bug_cause_inference.p2a.candidates import candidate_by_id
from bug_cause_inference.p2f import no_diff_clean_audit as p2f_audit
from bug_cause_inference.p2e import continuation_audit as p2e_audit


SCHEMA_VERSION = "p2g_accepted_benign_diff_clean_paired_continuation_audit.v1"
ANALYSIS_PHASE = "P2g"
AUDIT_ID = "p2g_accepted_benign_diff_clean_paired_continuation_audit_v1"
REPORT_ROLE = "analysis_only_fixed_input_benign_diff_clean_boundary"
VALID_STATUS = "valid"

BASE_COMMIT = "550f519c91d30558084f2ef40b340af3afcfffc3"
BASE_TREE = "9fd3ee3955d43983daac094b55a36b39cb9261e8"
SPECIFICATION_SHA256_LF = "464e6b70735f8b95887a95f6987c5ca73ca9cede52dd893b00ccf7ed9cc58632"
SPECIFICATION_REVIEW_SHA256_LF = "bb5046dd3859cb540cc08b4d4e4af396588186307d748c78dd9e9efb992f41d5"

FORMAL_POLICY_IDS = p2f_audit.FORMAL_POLICY_IDS
ARM_IDS = p2f_audit.ARM_IDS
ACTION_IDS = p2f_audit.ACTION_IDS
TARGET_STOP_ID = p2f_audit.TARGET_STOP_ID
RESIDUAL_STOP_IDS = p2f_audit.RESIDUAL_STOP_IDS
STOP_REASON_IDS = p2f_audit.STOP_REASON_IDS

INPUT_IDS = tuple(f"P2A-CLEAN-{index:03d}" for index in range(1, 6))
EXPECTED_CONTROL_COSTS = dict(
    zip(FORMAL_POLICY_IDS, (3, 3, 3, 5, 2, 2), strict=True)
)

IMPLEMENTATION_PATHS = (
    "src/bug_cause_inference/p2g/__init__.py",
    "src/bug_cause_inference/p2g/benign_diff_clean_audit.py",
    "src/bug_cause_inference/p2g/reports.py",
    "tests/test_p2g_benign_diff_clean_audit.py",
    "tests/test_p2g_reports.py",
)

# This is the immutable identity that was externally frozen before the first
# valid P2g outcome.  Corrective validator work is tracked as a separate
# current implementation identity and must not rewrite artifact provenance.
HISTORICAL_FIRST_OUTCOME_IMPLEMENTATION_IDENTITY = {
    "src/bug_cause_inference/p2g/__init__.py": "cd9678425da62a0e2d9db430479569640a0ab4bf58ffae7f513c48381cb8cbcd",
    "src/bug_cause_inference/p2g/benign_diff_clean_audit.py": "5fcd01726d67f4518d61690dc5383a5456cd06cf2cec69aa1c6a2fff7c7a6fb9",
    "src/bug_cause_inference/p2g/reports.py": "b4c29bba4859868ac60dfed044ba90424daa8498e2a1249d542ddce6afac0001",
    "tests/test_p2g_benign_diff_clean_audit.py": "681bfe12886745df3b5e85ad676f1f1b72cb6f5224589f7355fcfcdb4887575a",
    "tests/test_p2g_reports.py": "0c05ca91ab2b94bb3f0060d8147b6a5ea690e1a8f16c1e6f7deb032faf5e16be",
}

_TRAJECTORY_FIELDS = (
    "canonical_row_index", "pair_index", "input_id", "clean_family",
    "policy_id", "arm_id", "patch_sha256", "patched_checkout_digest",
    "initial_state", "initial_state_digest", "initial_rng_state_digest",
    "initial_execution_context_digest", "decision_events",
    "selected_action_ids", "observations", "action_costs", "cumulative_cost",
    "action_count", "suppression_count", "first_divergence_checkpoint",
    "terminal_reason", "final_state", "final_state_digest",
    "final_rng_state_digest", "final_execution_context_digest",
    "final_bug_presence_posterior", "false_positive",
    "execution_failure_observed", "bug_detected_observation",
    "normal_no_bug_stop", "benign_diff_observation_count", "trajectory_digest",
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
_OBSERVATION_FIELDS = (
    "action_id", "bug_detected", "cause_scores", "changed_files",
    "changed_functions", "cost", "coverage_counts", "coverage_suspicion",
    "diff_artifact_path", "diff_excerpt", "evidence_source", "exception_type",
    "executed_functions", "failed_test_ids", "failing_executed_functions",
    "failure_found", "fix_intent_scores", "location_scores", "no_bug_evidence",
    "observation_type", "passed_test_ids", "passing_executed_functions",
    "reproduction_input", "stack_functions", "summary", "test_results",
)
_TEST_RESULT_FIELDS = (
    "action_id", "actual", "evidence_tags", "exception_type",
    "executed_functions", "expected", "fix_intent_hints", "group", "passed",
    "reproduction_input", "stack_functions", "test_id",
)
EXPECTED_PATCHED_CHECKOUT_DIGESTS = {
    "P2A-CLEAN-001": "a7ed07329713644bbc1db6bb37666ec9a1f34635530e1fe3427eece82487455c",
    "P2A-CLEAN-002": "63a3d97b5266c241d15fce64b8960156960902c6279b52421af91418a0010a1f",
    "P2A-CLEAN-003": "d04389f8a9596b320010a5c0f676c4b691d7d11534460b9838178883708e6a94",
    "P2A-CLEAN-004": "e7ebc7bb5b5f9b1caf2c2b6ebd8a5e5aa188cb2af249aa72f3c42c32398823ad",
    "P2A-CLEAN-005": "5edb66a0a37d00c7d04f3b3be368faca0826bd3931bb3811e0c3c7f4f7c4a187",
}

DEPENDENCY_SHA256_LF = {
    "src/bug_cause_inference/p1b/actions.py": "cb191a6834f75e87835a2f9b3e164b2e05b48a6168a515455be57680f3d738fe",
    "src/bug_cause_inference/p1b/policies.py": "b039dff408f4fa26f6de86ffe1924fad6dd652c68092bcc08e59e8aa478e4ecd",
    "src/bug_cause_inference/p1b/execution.py": "820847852f623f91870c824c5218bf5a0c20643868f99131b40c63413b992a91",
    "src/bug_cause_inference/p1b/models.py": "895a9be33fd8502b8532554c4ca12b92db86b08a3074b54a8233d7ee25104fde",
    "src/bug_cause_inference/p2a/candidates.py": "47e0bfccff06819efc66384d9528be0828ca95943f63498bca1eb6aed68f6351",
    "src/bug_cause_inference/p2a/candidate_authoring.py": "c5a8f6801901d535c2bbde61603aa4de66c9d6ccc2005c30e13592733ae46701",
    "src/bug_cause_inference/p2a/execution.py": "24398546c684c9d2bc265c4c1bbe4f9752a603c6c5622bc7c74d2b333558b6f6",
    "src/bug_cause_inference/p2a/evaluation.py": "02db9095416885f865229f13ba52d2c7e1d794fac07b5cc2e1651d6593866785",
    "src/bug_cause_inference/p2a/artifacts/candidates/authoring_manifest.json": "ccf05cd8c4179ee2b84b68dffa1d576e59f717e4fd314a4cccb0136d9ffb7e3b",
    "src/bug_cause_inference/p2a/artifacts/freeze/artifact_manifest.json": "ff519a4f5bd7985e0b8f3929fcaa0ded3bd98f742e52bb85d7866f21a2cf1b0d",
    "src/bug_cause_inference/p2a/artifacts/freeze/official_freeze_bundle.json": "8a5197288c60329af2667fba8c541edd39ccc068b3ecf6393afdaddf8ebdb5a4",
    "src/bug_cause_inference/p2a/artifacts/evaluation/p2a_benchmark_evidence_expansion_v1.json": "d7e69fa62513f5bbae22d570e39b841401f5110b6cd1e45701c53393eb0ef3df",
    "src/bug_cause_inference/p2f/no_diff_clean_audit.py": "66d3c70c138fe44873be5cd63140aea157f1753f681cfaa9ed7fc179b7ccf1cc",
    "src/bug_cause_inference/p2f/reports.py": "aef7abf588ac1c68436a9e08cd30514474ee244069164c5ddfa998b1699836c5",
    "src/bug_cause_inference/p2f/artifacts/p2f_canonical_no_diff_clean_paired_continuation_audit_v1.json": "f0ffbddb24cd500144ea0b52958b3ae51d81e2b895ff8b89faf3da504a871000",
}

INPUT_CONTRACTS = (
    {
        "input_id": "P2A-CLEAN-001",
        "clean_family": "boundary_adjacent_valid_behavior",
        "patch_path": "src/bug_cause_inference/p2a/artifacts/candidates/patches/P2A-CLEAN-001.patch",
        "patch_sha256": "c0a1b7d75e313d91ec0653ddd361f926e1f69ad5025e78878e80aa114c8e3caa",
        "changed_files": ["checkout/cart.py"],
        "changed_functions": ["cart.validate_item"],
        "post_image_sha256_lf": "240ca5bf56ca093dbd173a8acf0538f00458e0cc2628acaeddb1ace0c57681d1",
        "oracle_ids": ["clean.boundary_max_accepted", "clean.boundary_over_max_rejected"],
    },
    {
        "input_id": "P2A-CLEAN-002",
        "clean_family": "optional_input_valid_absence",
        "patch_path": "src/bug_cause_inference/p2a/artifacts/candidates/patches/P2A-CLEAN-002.patch",
        "patch_sha256": "ef17bf8a5eb330d52e7ef9b122c4b574b01141bf23d15b6bc90fefa25ddd39f1",
        "changed_files": ["checkout/config.py"],
        "changed_functions": ["config.get_region_aliases"],
        "post_image_sha256_lf": "8f01cb00755d44a5b1b787ae1d268017bce5f8adb7aa2f55bead1e0f68918bd4",
        "oracle_ids": ["clean.optional_alias_copy_isolated", "clean.optional_aliases_absent_empty"],
    },
    {
        "input_id": "P2A-CLEAN-003",
        "clean_family": "config_equivalent_normalization",
        "patch_path": "src/bug_cause_inference/p2a/artifacts/candidates/patches/P2A-CLEAN-003.patch",
        "patch_sha256": "2ab2975d1537a7ea841ca2744515020f12d914b8a88668c967bcd664d64adea9",
        "changed_files": ["checkout/config.py"],
        "changed_functions": ["config.get_tax_rate"],
        "post_image_sha256_lf": "be83ce7d182e509888d0807865d8de1f9d6b7279c750f0d6ca83f25413e51780",
        "oracle_ids": [
            "clean.config_absent_jp_fallback", "clean.config_absent_us_fallback",
            "clean.config_explicit_zero_rate", "clean.config_present_none_jp_raises",
            "clean.config_present_none_us_raises", "clean.config_string_rate_equivalence",
        ],
    },
    {
        "input_id": "P2A-CLEAN-004",
        "clean_family": "valid_state_sequence",
        "patch_path": "src/bug_cause_inference/p2a/artifacts/candidates/patches/P2A-CLEAN-004.patch",
        "patch_sha256": "eb614f960d83f19a7ddccfc4f7162397f008c42dd2e2089cb3c09753c468b65d",
        "changed_files": ["checkout/discounts.py"],
        "changed_functions": ["discounts.apply_coupon"],
        "post_image_sha256_lf": "9b22eccc0e2a838f38b43fee861bbf0d6ab2cb6d6f8121c62cb53009fe1a6046",
        "oracle_ids": ["clean.state_coupon_idempotent", "clean.state_coupon_preserves_session"],
    },
    {
        "input_id": "P2A-CLEAN-005",
        "clean_family": "nonintuitive_spec_conformance",
        "patch_path": "src/bug_cause_inference/p2a/artifacts/candidates/patches/P2A-CLEAN-005.patch",
        "patch_sha256": "b78e400beeffcd5a9a9c84bf39c25f3b67a4b2c03eb41605700806b9331c8778",
        "changed_files": ["checkout/discounts.py"],
        "changed_functions": ["discounts.apply_bogo_discount"],
        "post_image_sha256_lf": "7c6b8442c9b7d2484f36806993541f48a6448bb29d3c03d5faad888911796804",
        "oracle_ids": ["clean.spec_bogo_ignores_ineligible", "clean.spec_bogo_selects_cheapest"],
    },
)

_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
_BASELINE_ROOT = _REPOSITORY_ROOT / "src/bug_cause_inference/p1b/artifacts/real_diff/baseline"
_ARTIFACT_MANIFEST_PATH = _REPOSITORY_ROOT / "src/bug_cause_inference/p2a/artifacts/freeze/artifact_manifest.json"
_FREEZE_BUNDLE_PATH = _REPOSITORY_ROOT / "src/bug_cause_inference/p2a/artifacts/freeze/official_freeze_bundle.json"

_LIMITATIONS = (
    "The evidence covers exactly five accepted, hand-authored, same-domain benign-diff clean inputs.",
    "The thirty pairs cross five inputs with six policies and are not independent programs or replicates.",
    "The intervention is model-internal and is not a deployable policy.",
)
_NON_CLAIMS = (
    "The audit does not establish general or unseen clean safety or a population false-positive rate.",
    "The audit does not establish threshold causality, a policy defect, improvement, ranking, or recommendation.",
    "The audit does not combine P2e, P2f, and P2g into a payoff, utility, or causal effect.",
    "The audit does not establish inference, external validity, optimality, deployability, or production readiness.",
)


class P2GAuditError(ValueError):
    """Raised when the frozen P2g contract is violated."""


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode()).hexdigest()


def _hash_lf(path: Path) -> str:
    raw = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(raw).hexdigest()


def _hash_raw(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _path(relative: str) -> Path:
    target = _REPOSITORY_ROOT.joinpath(*Path(relative).parts)
    resolved = target.resolve()
    root = _REPOSITORY_ROOT.resolve()
    if resolved != root and root not in resolved.parents:
        raise P2GAuditError("repository-relative path escaped the repository")
    return target


def implementation_identity() -> dict[str, str]:
    return {path: _hash_lf(_path(path)) for path in IMPLEMENTATION_PATHS}


def dependency_identity() -> dict[str, str]:
    observed = {path: _hash_lf(_path(path)) for path in DEPENDENCY_SHA256_LF}
    if observed != DEPENDENCY_SHA256_LF:
        raise P2GAuditError("accepted P1b-P2f dependency identity drifted")
    return observed


def _raw_dependency_snapshot() -> dict[str, str]:
    paths = list(DEPENDENCY_SHA256_LF) + [row["patch_path"] for row in INPUT_CONTRACTS]
    return {path: _hash_raw(_path(path)) for path in paths}


def _input_contract(input_id: str) -> dict[str, Any]:
    try:
        return deepcopy(next(row for row in INPUT_CONTRACTS if row["input_id"] == input_id))
    except StopIteration as exc:
        raise P2GAuditError("input is outside the exact accepted five") from exc


def _artifact_candidates() -> dict[str, dict[str, Any]]:
    value = json.loads(_ARTIFACT_MANIFEST_PATH.read_text(encoding="utf-8"))
    return {row["variant_id"]: row for row in value["candidates"]}


def _validate_input_contracts() -> list[dict[str, Any]]:
    if tuple(row["input_id"] for row in INPUT_CONTRACTS) != INPUT_IDS:
        raise P2GAuditError("accepted clean input order drifted")
    artifacts = _artifact_candidates()
    for row in INPUT_CONTRACTS:
        candidate = candidate_by_id(row["input_id"])
        artifact = artifacts[row["input_id"]]
        if candidate.cohort_kind != "clean_stress":
            raise P2GAuditError("accepted input is not clean_stress")
        if candidate.metadata["clean_stress_family_id"] != row["clean_family"]:
            raise P2GAuditError("clean family drifted")
        if list(candidate.metadata["changed_files"]) != row["changed_files"]:
            raise P2GAuditError("changed file identity drifted")
        if list(candidate.metadata["changed_functions"]) != row["changed_functions"]:
            raise P2GAuditError("changed function identity drifted")
        if list(candidate.oracle_ids) != row["oracle_ids"]:
            raise P2GAuditError("clean oracle order drifted")
        if _hash_raw(_path(row["patch_path"])) != row["patch_sha256"]:
            raise P2GAuditError("accepted clean patch bytes drifted")
        patch = artifact["patch_identity"]
        if (
            patch["path"] != row["patch_path"]
            or patch["raw_sha256"] != row["patch_sha256"]
            or patch["changed_files"] != row["changed_files"]
            or patch["changed_functions"] != row["changed_functions"]
            or artifact["oracle_identity"]["candidate_ground_truth_status"] != "all_pass"
        ):
            raise P2GAuditError("accepted artifact input identity drifted")
    return deepcopy(list(INPUT_CONTRACTS))


def _validate_clean_validity_gate(gate: Any) -> dict[str, Any]:
    if type(gate) is not dict or set(gate) != {
        "input_count", "oracle_count", "passed_oracle_count", "inputs"
    }:
        raise P2GAuditError("clean validity gate schema drifted")
    expected_inputs = [
        {
            "input_id": contract["input_id"],
            "oracle_results": [
                {"oracle_id": oracle_id, "passed": True}
                for oracle_id in contract["oracle_ids"]
            ],
            "all_pass": True,
            "patched_checkout_digest": EXPECTED_PATCHED_CHECKOUT_DIGESTS[
                contract["input_id"]
            ],
        }
        for contract in INPUT_CONTRACTS
    ]
    if gate != {
        "input_count": 5,
        "oracle_count": 14,
        "passed_oracle_count": 14,
        "inputs": expected_inputs,
    }:
        raise P2GAuditError("clean validity gate result or support drifted")
    return gate


def _checkout_rows(root: Path) -> list[dict[str, str]]:
    return [
        {"path": f"checkout/{path.name}", "sha256_lf": _hash_lf(path)}
        for path in sorted((root / "checkout").glob("*.py"))
    ]


@contextmanager
def isolated_patched_checkout(
    input_id: str, work_root: Path
) -> Iterator[tuple[dict[str, ModuleType], str, str]]:
    """Materialize one accepted patch in a workspace-local isolated tree."""

    contract = _input_contract(input_id)
    root = work_root.resolve()
    if root.is_relative_to((_REPOSITORY_ROOT / "src").resolve()):
        raise P2GAuditError("work root must not be inside versioned source")
    tree = root / "tree"
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    try:
        shutil.copytree(_BASELINE_ROOT, tree)
        apply_unified_patch(tree, _path(contract["patch_path"]).read_text(encoding="utf-8"))
        expected = _checkout_rows(tree)
        changed_path = tree / contract["changed_files"][0]
        if _hash_lf(changed_path) != contract["post_image_sha256_lf"]:
            raise P2GAuditError("accepted patch post-image identity drifted")
        with generated_checkout_imports(tree) as modules:
            prefix = next(iter(modules.values())).__name__.rsplit(".", 1)[0] + "."
            yield modules, prefix, _digest(expected)
        if _checkout_rows(tree) != expected:
            raise P2GAuditError("isolated patched checkout drifted during execution")
    finally:
        if root.exists():
            shutil.rmtree(root)


def _clean_validity_gate(work_root: Path) -> dict[str, Any]:
    rows = []
    for index, input_id in enumerate(INPUT_IDS, start=1):
        contract = _input_contract(input_id)
        with isolated_patched_checkout(input_id, work_root / f"input-{index}") as (modules, _prefix, copy_digest):
            oracle_rows = [
                {"oracle_id": oracle_id, "passed": run_oracle(oracle_id, modules).passed}
                for oracle_id in contract["oracle_ids"]
            ]
        if not all(row["passed"] for row in oracle_rows):
            raise P2GAuditError("accepted clean validity gate failed")
        rows.append({
            "input_id": input_id,
            "oracle_results": oracle_rows,
            "all_pass": True,
            "patched_checkout_digest": copy_digest,
        })
    return {
        "input_count": 5,
        "oracle_count": sum(len(row["oracle_results"]) for row in rows),
        "passed_oracle_count": sum(sum(item["passed"] for item in row["oracle_results"]) for row in rows),
        "inputs": rows,
    }


def _freeze_bundle() -> dict[str, Any]:
    return json.loads(_FREEZE_BUNDLE_PATH.read_text(encoding="utf-8"))


def _truthful_diff_observation(input_id: str, artifact: dict[str, Any]):
    contract = _input_contract(input_id)
    base = p2a_evaluation._recent_diff_observation(input_id, candidate_artifact=artifact)
    patch_text = _path(contract["patch_path"]).read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not patch_text:
        raise P2GAuditError("truthful benign diff excerpt is empty")
    return replace(
        base,
        summary="inspect_recent_diff observed the accepted repository-relative benign patch identity.",
        evidence_source="p2g_accepted_p2a_patch_identity",
        diff_artifact_path=contract["patch_path"],
        changed_files=list(contract["changed_files"]),
        changed_functions=list(contract["changed_functions"]),
        diff_excerpt=patch_text,
    )


def _run_action(
    *, input_id: str, action_id: str, state: Any,
    modules: Mapping[str, ModuleType], cases_by_action: Mapping[str, list[dict[str, Any]]],
    artifact: dict[str, Any],
):
    if action_id == "inspect_recent_diff":
        observation = _truthful_diff_observation(input_id, artifact)
    else:
        observation = p2a_evaluation._run_frozen_action(
            variant_id=input_id,
            action_id=action_id,
            context=state.execution_context,
            modules=modules,
            cases_by_action=cases_by_action,
            candidate_artifact=artifact,
        )
    if observation.cost != P1B_ACTION_SPECS[action_id].cost:
        raise P2GAuditError("action cost drifted")
    if any(not result["passed"] for result in observation.test_results):
        raise P2GAuditError("valid clean trajectory executed a failing test")
    state.executed_actions.append(action_id)
    state.cumulative_cost += observation.cost
    state.current_step += 1
    state.bug_detected = state.bug_detected or observation.bug_detected
    state.bug_presence = p1b_policies._update_bug_presence(
        state.bug_presence, observation.bug_detected, observation.no_bug_evidence
    )
    state.cause_posterior = p2f_audit._portable_update_distribution(state.cause_posterior, observation.cause_scores)
    state.location_posterior = p2f_audit._portable_update_distribution(state.location_posterior, observation.location_scores)
    state.fix_intent_posterior = p2f_audit._portable_update_distribution(state.fix_intent_posterior, observation.fix_intent_scores)
    return observation


def _apply_recorded_observation(
    state: Any, action_id: str, observation: Mapping[str, Any]
) -> None:
    """Replay P2g's accepted state/context update from a recorded observation."""

    recorded = deepcopy(observation["test_results"])
    if action_id not in {
        "inspect_recent_diff",
        "inspect_coverage_spectrum",
        "inspect_traceback",
    }:
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
    state.cause_posterior = p2f_audit._portable_update_distribution(
        state.cause_posterior, observation["cause_scores"]
    )
    state.location_posterior = p2f_audit._portable_update_distribution(
        state.location_posterior, observation["location_scores"]
    )
    state.fix_intent_posterior = p2f_audit._portable_update_distribution(
        state.fix_intent_posterior, observation["fix_intent_scores"]
    )


def _run_trajectory(
    *, row_index: int, pair_index: int, input_id: str, policy_id: str,
    arm_id: str, modules: Mapping[str, ModuleType], copy_digest: str,
    cases_by_action: Mapping[str, list[dict[str, Any]]], artifact: dict[str, Any],
) -> dict[str, Any]:
    settings = p2f_audit._settings()
    state = p2f_audit._new_state()
    rng = random.Random(p1b_policies._stable_seed(input_id, settings.rng_seed))
    initial_state = p2f_audit._state_payload(state)
    initial_state_digest = p2f_audit._state_digest(state)
    initial_rng_digest = p2e_audit.rng_state_digest(rng)
    initial_context_digest = p2e_audit.execution_context_digest(state.execution_context)
    decisions: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    suppression_count = 0
    terminal_reason: str | None = None
    while terminal_reason is None:
        before_state = p2f_audit._state_digest(state)
        before_rng = p2e_audit.rng_state_digest(rng)
        before_context = p2e_audit.execution_context_digest(state.execution_context)
        remaining = settings.budget_limit - state.cumulative_cost
        available = p2f_audit._available_action_ids(state, remaining)
        scores = p1b_policies.score_actions(state, remaining)
        stop_rows, target_value, residual, projected_terminal = p2f_audit._stop_projection(
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
                **base, "selection_attempted": False, "selected_action_id": None,
                "selected_action_cost": None, "observation": None,
                "state_digest_after": before_state, "rng_state_digest_after": before_rng,
                "execution_context_digest_after": before_context,
                "terminal_after_decision": True, "terminal_reason": terminal_reason,
            })
            break
        action_id = p1b_policies.choose_action(policy_id, state, remaining, rng)
        if action_id is None:
            terminal_reason = "no_available_actions"
            decisions.append({
                **base, "selection_attempted": True, "selected_action_id": None,
                "selected_action_cost": None, "observation": None,
                "state_digest_after": before_state, "rng_state_digest_after": before_rng,
                "execution_context_digest_after": before_context,
                "terminal_after_decision": True, "terminal_reason": terminal_reason,
            })
            break
        if action_id not in available:
            raise P2GAuditError("selector returned unavailable action")
        observation = _run_action(
            input_id=input_id, action_id=action_id, state=state, modules=modules,
            cases_by_action=cases_by_action, artifact=artifact,
        )
        payload = observation.to_dict()
        observations.append(payload)
        decisions.append({
            **base, "selection_attempted": True, "selected_action_id": action_id,
            "selected_action_cost": observation.cost, "observation": payload,
            "state_digest_after": p2f_audit._state_digest(state),
            "rng_state_digest_after": p2e_audit.rng_state_digest(rng),
            "execution_context_digest_after": p2e_audit.execution_context_digest(state.execution_context),
            "terminal_after_decision": False, "terminal_reason": None,
        })
    false_positive = terminal_reason == "bug_confidence_threshold" or state.bug_presence >= settings.bug_presence_threshold
    execution_failure = any(not result["passed"] for obs in observations for result in obs["test_results"])
    contract = _input_contract(input_id)
    row = {
        "canonical_row_index": row_index,
        "pair_index": pair_index,
        "input_id": input_id,
        "clean_family": contract["clean_family"],
        "policy_id": policy_id,
        "arm_id": arm_id,
        "patch_sha256": contract["patch_sha256"],
        "patched_checkout_digest": copy_digest,
        "initial_state": initial_state,
        "initial_state_digest": initial_state_digest,
        "initial_rng_state_digest": initial_rng_digest,
        "initial_execution_context_digest": initial_context_digest,
        "decision_events": decisions,
        "selected_action_ids": list(state.executed_actions),
        "observations": observations,
        "action_costs": [P1B_ACTION_SPECS[item].cost for item in state.executed_actions],
        "cumulative_cost": state.cumulative_cost,
        "action_count": state.current_step,
        "suppression_count": suppression_count,
        "first_divergence_checkpoint": None,
        "terminal_reason": terminal_reason,
        "final_state": p2f_audit._state_payload(state),
        "final_state_digest": p2f_audit._state_digest(state),
        "final_rng_state_digest": p2e_audit.rng_state_digest(rng),
        "final_execution_context_digest": p2e_audit.execution_context_digest(state.execution_context),
        "final_bug_presence_posterior": state.bug_presence,
        "false_positive": false_positive,
        "execution_failure_observed": execution_failure,
        "bug_detected_observation": any(obs["bug_detected"] for obs in observations),
        "normal_no_bug_stop": arm_id == ARM_IDS[0] and terminal_reason == TARGET_STOP_ID,
        "benign_diff_observation_count": sum(obs["action_id"] == "inspect_recent_diff" for obs in observations),
        "trajectory_digest": "",
    }
    return row


def _trajectory_digest(row: Mapping[str, Any]) -> str:
    value = dict(row)
    value.pop("trajectory_digest", None)
    return _digest(value)


def _finish_pair(control: dict[str, Any], intervention: dict[str, Any]) -> dict[str, Any]:
    for field in (
        "input_id", "policy_id", "initial_state_digest", "initial_rng_state_digest",
        "initial_execution_context_digest", "patched_checkout_digest",
    ):
        if control[field] != intervention[field]:
            raise P2GAuditError("paired start checkpoint mismatch")
    left = control["decision_events"]
    right = intervention["decision_events"]
    divergence: int | None = None
    if control["terminal_reason"] == TARGET_STOP_ID:
        divergence = len(left)
        if left[: divergence - 1] != right[: divergence - 1]:
            raise P2GAuditError("paired pre-target prefix mismatch")
        keys = (
            "decision_index", "state_digest_before", "rng_state_digest_before",
            "execution_context_digest_before", "remaining_budget_before",
            "available_action_ids", "action_scores", "target_predicate_value",
            "residual_stop_result",
        )
        if any(left[-1][key] != right[divergence - 1][key] for key in keys):
            raise P2GAuditError("paired target checkpoint mismatch")
        if not right[divergence - 1]["target_suppressed"]:
            raise P2GAuditError("first divergence is not target suppression")
    elif left != right or intervention["suppression_count"] != 0:
        raise P2GAuditError("non-target control did not have an exact paired arm")
    control["first_divergence_checkpoint"] = divergence
    intervention["first_divergence_checkpoint"] = divergence
    control["trajectory_digest"] = _trajectory_digest(control)
    intervention["trajectory_digest"] = _trajectory_digest(intervention)
    pair = {
        "pair_index": control["pair_index"],
        "input_id": control["input_id"],
        "policy_id": control["policy_id"],
        "control_row_index": control["canonical_row_index"],
        "intervention_row_index": intervention["canonical_row_index"],
        "start_checkpoint_agreement": True,
        "prefix_agreement_before_control_terminal": True,
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
    pair["pair_digest"] = _digest({key: value for key, value in pair.items() if key != "pair_digest"})
    return pair


def _axis(rows: list[dict[str, Any]], denominator: int, unit: str) -> dict[str, Any]:
    return {
        "trajectory_count": len(rows),
        "false_positive": {"numerator": sum(row["false_positive"] for row in rows), "denominator": denominator, "unit": unit},
        "execution_failure_count": sum(row["execution_failure_observed"] for row in rows),
        "bug_detected_observation_count": sum(row["bug_detected_observation"] for row in rows),
        "terminal_reason_counts": {reason: sum(row["terminal_reason"] == reason for row in rows) for reason in STOP_REASON_IDS},
        "action_count_distribution": {str(count): sum(row["action_count"] == count for row in rows) for count in range(7)},
        "cumulative_cost_distribution": {str(cost): sum(row["cumulative_cost"] == cost for row in rows) for cost in range(13)},
        "suppression_count_distribution": {str(count): sum(row["suppression_count"] == count for row in rows) for count in range(8)},
    }


def derive_aggregate_results(
    rows: list[dict[str, Any]], pairs: list[dict[str, Any]], gate: dict[str, Any]
) -> dict[str, Any]:
    by_arm = {arm: _axis([row for row in rows if row["arm_id"] == arm], 30, "trajectories") for arm in ARM_IDS}
    by_input = {
        input_id: {arm: _axis([row for row in rows if row["input_id"] == input_id and row["arm_id"] == arm], 6, "policies") for arm in ARM_IDS}
        for input_id in INPUT_IDS
    }
    by_policy = {
        policy: {arm: _axis([row for row in rows if row["policy_id"] == policy and row["arm_id"] == arm], 5, "inputs") for arm in ARM_IDS}
        for policy in FORMAL_POLICY_IDS
    }
    diff_observations = [
        obs for row in rows for obs in row["observations"]
        if obs["action_id"] == "inspect_recent_diff"
    ]
    aggregate = {
        "support": {"input_count": 5, "policy_count": 6, "arm_count": 2, "trajectory_count": 60, "pair_count": 30},
        "by_arm": by_arm,
        "by_input": by_input,
        "by_policy": by_policy,
        "paired_deltas": [{key: pair[key] for key in ("pair_index", "input_id", "policy_id", "false_positive_delta", "action_count_delta", "cost_delta", "suppression_count")} for pair in pairs],
        "pair_start_checkpoint_agreement": {"numerator": sum(pair["start_checkpoint_agreement"] for pair in pairs), "denominator": 30},
        "pair_prefix_agreement": {"numerator": sum(pair["prefix_agreement_before_control_terminal"] for pair in pairs), "denominator": 30},
        "benign_diff_observations": {
            "execution_count": len(diff_observations),
            "path_function_excerpt_agreement_count": sum(bool(obs["changed_files"] and obs["changed_functions"] and obs["diff_excerpt"] and obs["diff_artifact_path"]) for obs in diff_observations),
        },
        "clean_validity_gate": gate,
        "normal_control_replay_gate": {
            "expected_pair_count": 30,
            "matched_pair_count": sum(
                pair["control_false_positive"] is False
                and pair["control_terminal_reason"] == TARGET_STOP_ID
                and pair["control_cost"] == EXPECTED_CONTROL_COSTS[pair["policy_id"]]
                for pair in pairs
            ),
            "accepted_policy_costs": deepcopy(EXPECTED_CONTROL_COSTS),
        },
        "digests": {
            "input_contract_digest": _digest(list(INPUT_CONTRACTS)),
            "dependency_contract_digest": _digest(DEPENDENCY_SHA256_LF),
            "trajectory_results_digest": _digest(rows),
            "pair_results_digest": _digest(pairs),
            "aggregate_results_digest": None,
            "canonical_summary_digest": None,
        },
    }
    aggregate["digests"]["aggregate_results_digest"] = _digest(aggregate)
    return aggregate


def _population() -> dict[str, Any]:
    return {
        "input_ids": list(INPUT_IDS), "policy_ids": list(FORMAL_POLICY_IDS),
        "arm_ids": list(ARM_IDS), "order": "input_major_policy_major_arm_minor",
        "trajectory_count": 60, "pair_count": 30,
        "independent_program_count": None,
        "sampling_statement": "fixed same-domain hand-authored non-iid crossed support",
    }


def _pending(scope: str) -> dict[str, str]:
    return {"scope": scope, "status": "pending_separate_external_acceptance"}


def _summary_digest(summary: Mapping[str, Any]) -> str:
    value = deepcopy(summary)
    value["aggregate_results"]["digests"]["canonical_summary_digest"] = None
    return _digest(value)


def validate_audit_summary(summary: Any) -> dict[str, Any]:
    dependency_identity()
    contracts = _validate_input_contracts()
    if type(summary) is not dict:
        raise P2GAuditError("summary must be an object")
    expected_top = {
        "schema_version", "analysis_phase", "audit_id", "report_role",
        "validation_status", "input_identity", "pre_outcome_freeze",
        "execution_boundary", "population", "definitions", "trajectory_results",
        "pair_results", "aggregate_results", "software_acceptance",
        "artifact_identity_acceptance", "result_acceptance",
        "documentation_acceptance", "limitations", "non_claims", "notes",
    }
    if set(summary) != expected_top:
        raise P2GAuditError("top-level schema fields drifted")
    if (
        summary["schema_version"] != SCHEMA_VERSION
        or summary["analysis_phase"] != ANALYSIS_PHASE
        or summary["audit_id"] != AUDIT_ID
        or summary["report_role"] != REPORT_ROLE
        or summary["validation_status"] != {"status": VALID_STATUS}
    ):
        raise P2GAuditError("analysis identity drifted")
    if summary["population"] != _population():
        raise P2GAuditError("population or denominator drifted")
    identity = summary["input_identity"]
    if identity["base_commit"] != BASE_COMMIT or identity["base_tree"] != BASE_TREE:
        raise P2GAuditError("base identity drifted")
    if identity["input_contracts"] != contracts or identity["dependency_file_sha256_lf"] != DEPENDENCY_SHA256_LF:
        raise P2GAuditError("accepted input/dependency identity drifted")
    if (
        identity["input_contract_digest"] != _digest(contracts)
        or identity["dependency_contract_digest"] != _digest(DEPENDENCY_SHA256_LF)
    ):
        raise P2GAuditError("accepted input/dependency contract digest drifted")
    freeze = summary["pre_outcome_freeze"]
    if (
        freeze["specification_sha256_lf"] != SPECIFICATION_SHA256_LF
        or freeze["specification_review_sha256_lf"] != SPECIFICATION_REVIEW_SHA256_LF
        or freeze["implementation_file_sha256_lf"]
        != HISTORICAL_FIRST_OUTCOME_IMPLEMENTATION_IDENTITY
        or freeze["first_outcome_executed_after_freeze"] is not True
    ):
        raise P2GAuditError("external pre-outcome freeze payload drifted")
    rows = summary["trajectory_results"]
    if type(rows) is not list or len(rows) != 60:
        raise P2GAuditError("trajectory support is not exactly 60")
    gate = _validate_clean_validity_gate(
        summary["aggregate_results"]["clean_validity_gate"]
    )
    gate_by_input = {item["input_id"]: item for item in gate["inputs"]}
    for index, row in enumerate(rows, start=1):
        if set(row) != set(_TRAJECTORY_FIELDS):
            raise P2GAuditError("trajectory fields drifted")
        input_id = INPUT_IDS[(index - 1) // 12]
        within = (index - 1) % 12
        policy_id = FORMAL_POLICY_IDS[within // 2]
        arm_id = ARM_IDS[within % 2]
        if (
            row["canonical_row_index"] != index
            or row["pair_index"] != (index + 1) // 2
            or row["input_id"] != input_id
            or row["policy_id"] != policy_id
            or row["arm_id"] != arm_id
        ):
            raise P2GAuditError("canonical trajectory order drifted")
        contract = _input_contract(input_id)
        if row["clean_family"] != contract["clean_family"] or row["patch_sha256"] != contract["patch_sha256"]:
            raise P2GAuditError("trajectory input identity drifted")
        gate_row = gate_by_input[input_id]
        if row["patched_checkout_digest"] != gate_row["patched_checkout_digest"]:
            raise P2GAuditError("trajectory patched checkout identity drifted")
        initial_state = p2f_audit._state_payload(p2f_audit._new_state())
        if row["initial_state"] != initial_state or row["initial_state_digest"] != _digest(initial_state):
            raise P2GAuditError("trajectory initial state drifted")
        settings = p2f_audit._settings()
        initial_rng = random.Random(p1b_policies._stable_seed(input_id, settings.rng_seed))
        if row["initial_rng_state_digest"] != p2e_audit.rng_state_digest(initial_rng):
            raise P2GAuditError("trajectory initial RNG drifted")
        if row["initial_execution_context_digest"] != p2e_audit.execution_context_digest(p2f_audit._new_state().execution_context):
            raise P2GAuditError("trajectory initial execution context drifted")
        if row["action_count"] != len(row["selected_action_ids"]) or row["action_count"] != len(row["observations"]):
            raise P2GAuditError("action count drifted")
        costs = [P1B_ACTION_SPECS[action].cost for action in row["selected_action_ids"]]
        if row["action_costs"] != costs or row["cumulative_cost"] != sum(costs):
            raise P2GAuditError("action cost drifted")
        if len(set(row["selected_action_ids"])) != len(row["selected_action_ids"]):
            raise P2GAuditError("trajectory repeated an action")
        if row["cumulative_cost"] > 12 or row["action_count"] > 6 or row["terminal_reason"] not in STOP_REASON_IDS:
            raise P2GAuditError("trajectory bound or terminal drifted")
        expected_fp = row["terminal_reason"] == "bug_confidence_threshold" or row["final_bug_presence_posterior"] >= 0.75
        if row["false_positive"] is not expected_fp:
            raise P2GAuditError("false-positive definition drifted")
        if row["execution_failure_observed"]:
            raise P2GAuditError("valid clean trajectory contains an execution failure")
        events = row["decision_events"]
        if type(events) is not list or not events or not events[-1]["terminal_after_decision"]:
            raise P2GAuditError("trajectory decision termination drifted")
        replay_state = p2f_audit._new_state()
        replay_rng = random.Random(p1b_policies._stable_seed(input_id, settings.rng_seed))
        previous_after = row["initial_state_digest"]
        suppression_index = 0
        observation_index = 0
        for decision_index, event in enumerate(events, start=1):
            if set(event) != set(_DECISION_FIELDS) or event["decision_index"] != decision_index:
                raise P2GAuditError("decision schema or index drifted")
            if event["state_digest_before"] != previous_after:
                raise P2GAuditError("decision state chain drifted")
            if (
                event["state_digest_before"] != p2f_audit._state_digest(replay_state)
                or event["rng_state_digest_before"] != p2e_audit.rng_state_digest(replay_rng)
                or event["execution_context_digest_before"]
                != p2e_audit.execution_context_digest(replay_state.execution_context)
            ):
                raise P2GAuditError("decision checkpoint replay drifted")
            remaining = settings.budget_limit - replay_state.cumulative_cost
            expected_available = p2f_audit._available_action_ids(replay_state, remaining)
            expected_scores = p1b_policies.score_actions(replay_state, remaining)
            if event["remaining_budget_before"] != remaining:
                raise P2GAuditError("remaining budget projection drifted")
            if event["available_action_ids"] != expected_available:
                raise P2GAuditError("available-action completeness or order drifted")
            if event["action_scores"] != expected_scores:
                raise P2GAuditError("action-score completeness or order drifted")
            predicates = event["evaluated_stop_predicates"]
            if (
                type(predicates) is not list
                or [item.get("stop_id") for item in predicates]
                != [TARGET_STOP_ID, *RESIDUAL_STOP_IDS]
                or any(set(item) != {"stop_id", "value", "suppressed"} for item in predicates)
                or any(type(item["value"]) is not bool for item in predicates)
            ):
                raise P2GAuditError("evaluated stop predicates drifted")
            expected_predicates, expected_target, expected_residual, expected_terminal = p2f_audit._stop_projection(
                replay_state, settings, expected_scores, row["arm_id"]
            )
            if (
                predicates != expected_predicates
                or event["target_predicate_value"] is not expected_target
                or event["target_suppressed"]
                is not (row["arm_id"] == ARM_IDS[1] and expected_target)
                or event["residual_stop_result"] != expected_residual
            ):
                raise P2GAuditError("stop projection or suppression semantics drifted")
            if event["target_suppressed"]:
                suppression_index += 1
                if event["suppression_event_index"] != suppression_index:
                    raise P2GAuditError("suppression index drifted")
            elif event["suppression_event_index"] is not None:
                raise P2GAuditError("non-suppression carried an index")
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
                    raise P2GAuditError("terminal decision truth table drifted")
                if any(
                    event[after] != event[before]
                    for after, before in (
                        ("state_digest_after", "state_digest_before"),
                        ("rng_state_digest_after", "rng_state_digest_before"),
                        ("execution_context_digest_after", "execution_context_digest_before"),
                    )
                ):
                    raise P2GAuditError("terminal checkpoint changed without action")
            elif action_id is None:
                if (
                    event["selection_attempted"] is not True
                    or event["selected_action_cost"] is not None
                    or event["observation"] is not None
                    or event["terminal_after_decision"] is not True
                    or event["terminal_reason"] != "no_available_actions"
                    or expected_available
                ):
                    raise P2GAuditError("no-available-actions truth table drifted")
                if any(
                    event[after] != event[before]
                    for after, before in (
                        ("state_digest_after", "state_digest_before"),
                        ("rng_state_digest_after", "rng_state_digest_before"),
                        ("execution_context_digest_after", "execution_context_digest_before"),
                    )
                ):
                    raise P2GAuditError("no-action checkpoint changed")
            else:
                if (
                    event["selection_attempted"] is not True
                    or event["selected_action_cost"] != P1B_ACTION_SPECS[action_id].cost
                    or type(event["observation"]) is not dict
                    or event["terminal_after_decision"] is not False
                    or event["terminal_reason"] is not None
                    or action_id not in expected_available
                ):
                    raise P2GAuditError("selected-action truth table drifted")
                expected_action = p1b_policies.choose_action(
                    row["policy_id"], replay_state, remaining, replay_rng
                )
                if action_id != expected_action:
                    raise P2GAuditError("frozen policy selection drifted")
                if (
                    event["observation"] != row["observations"][observation_index]
                    or action_id != row["selected_action_ids"][observation_index]
                ):
                    raise P2GAuditError("decision observation/action chain drifted")
                _apply_recorded_observation(replay_state, action_id, event["observation"])
                if (
                    event["state_digest_after"] != p2f_audit._state_digest(replay_state)
                    or event["rng_state_digest_after"] != p2e_audit.rng_state_digest(replay_rng)
                    or event["execution_context_digest_after"]
                    != p2e_audit.execution_context_digest(replay_state.execution_context)
                ):
                    raise P2GAuditError("post-action checkpoint replay drifted")
                observation_index += 1
            previous_after = event["state_digest_after"]
        if observation_index != len(row["observations"]):
            raise P2GAuditError("decision observation support drifted")
        if suppression_index != row["suppression_count"]:
            raise P2GAuditError("trajectory suppression count drifted")
        if (
            row["final_state"] != p2f_audit._state_payload(replay_state)
            or row["final_state_digest"] != previous_after
            or row["final_state_digest"] != p2f_audit._state_digest(replay_state)
            or row["final_rng_state_digest"] != events[-1]["rng_state_digest_after"]
            or row["final_execution_context_digest"]
            != events[-1]["execution_context_digest_after"]
        ):
            raise P2GAuditError("final state/RNG/context projection drifted")
        if (
            row["final_bug_presence_posterior"] != replay_state.bug_presence
            or row["bug_detected_observation"]
            is not any(observation["bug_detected"] for observation in row["observations"])
            or row["normal_no_bug_stop"]
            is not (row["arm_id"] == ARM_IDS[0] and row["terminal_reason"] == TARGET_STOP_ID)
            or row["benign_diff_observation_count"]
            != sum(observation["action_id"] == "inspect_recent_diff" for observation in row["observations"])
        ):
            raise P2GAuditError("trajectory final projection drifted")
        for observation in row["observations"]:
            if set(observation) != set(_OBSERVATION_FIELDS):
                raise P2GAuditError("observation schema drifted")
            if observation["action_id"] not in ACTION_IDS:
                raise P2GAuditError("observation action identity drifted")
            if any(set(result) != set(_TEST_RESULT_FIELDS) for result in observation["test_results"]):
                raise P2GAuditError("test-result schema drifted")
            if any(
                result["action_id"] != observation["action_id"]
                or result["passed"] is not True
                for result in observation["test_results"]
            ):
                raise P2GAuditError("valid clean observation contains a failed result")
            if observation["action_id"] == "inspect_recent_diff":
                artifact = _artifact_candidates()[input_id]
                if observation != _truthful_diff_observation(input_id, artifact).to_dict():
                    raise P2GAuditError("truthful benign-diff observation drifted")
                if Path(observation["diff_artifact_path"]).is_absolute():
                    raise P2GAuditError("recent diff exposed an absolute path")
        if row["trajectory_digest"] != _trajectory_digest(row):
            raise P2GAuditError("trajectory digest drifted")
    expected_pairs = []
    cloned = deepcopy(rows)
    for index in range(30):
        expected_pairs.append(_finish_pair(cloned[2 * index], cloned[2 * index + 1]))
    if summary["pair_results"] != expected_pairs:
        raise P2GAuditError("paired results or prefix integrity drifted")
    expected_aggregate = derive_aggregate_results(rows, summary["pair_results"], gate)
    expected_aggregate["digests"]["canonical_summary_digest"] = summary["aggregate_results"]["digests"]["canonical_summary_digest"]
    if summary["aggregate_results"] != expected_aggregate:
        raise P2GAuditError("aggregate or denominator drifted")
    if summary["aggregate_results"]["normal_control_replay_gate"]["matched_pair_count"] != 30:
        raise P2GAuditError("accepted P2a normal-control replay drifted")
    if summary["aggregate_results"]["pair_start_checkpoint_agreement"] != {"numerator": 30, "denominator": 30}:
        raise P2GAuditError("paired start agreement drifted")
    if summary["aggregate_results"]["pair_prefix_agreement"] != {"numerator": 30, "denominator": 30}:
        raise P2GAuditError("paired prefix agreement drifted")
    for field, scope in (
        ("software_acceptance", "software_conformance"),
        ("artifact_identity_acceptance", "versioned_artifact_identity"),
        ("result_acceptance", "descriptive_result"),
        ("documentation_acceptance", "public_result_documentation"),
    ):
        if summary[field] != _pending(scope):
            raise P2GAuditError("artifact became self-accepting")
    if summary["limitations"] != list(_LIMITATIONS) or summary["non_claims"] != list(_NON_CLAIMS):
        raise P2GAuditError("claim boundary drifted")
    if summary["aggregate_results"]["digests"]["canonical_summary_digest"] != _summary_digest(summary):
        raise P2GAuditError("canonical summary digest drifted")
    validate_portable_value(summary, "p2g_summary")
    return summary


def run_benign_diff_clean_audit(
    *, expected_implementation_identity: Mapping[str, str], work_root: Path,
    event_log: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run the frozen first/fresh P2g audit under an external identity map."""

    events = event_log if event_log is not None else []
    expected = dict(expected_implementation_identity)
    if tuple(expected) != IMPLEMENTATION_PATHS or implementation_identity() != expected:
        raise P2GAuditError("implementation differs from external pre-outcome freeze")
    events.extend([
        {"event": "p2g_specification_frozen", "sha256_lf": SPECIFICATION_SHA256_LF},
        {"event": "p2g_specification_review_accepted", "sha256_lf": SPECIFICATION_REVIEW_SHA256_LF},
        {"event": "p2g_implementation_freeze_verified", "file_count": 5},
    ])
    implementation_before = implementation_identity()
    dependency_identity()
    contracts = _validate_input_contracts()
    raw_before = _raw_dependency_snapshot()
    gate = _clean_validity_gate(work_root / "clean-gate")
    events.append({"event": "p2g_clean_validity_gate_passed", "input_count": 5, "oracle_count": gate["oracle_count"]})
    bundle = _freeze_bundle()
    cases_by_action = p2a_evaluation._catalog_cases(bundle)
    artifacts = _artifact_candidates()
    rows: list[dict[str, Any]] = []
    pairs: list[dict[str, Any]] = []
    row_index = 0
    pair_index = 0
    for input_position, input_id in enumerate(INPUT_IDS, start=1):
        for policy_id in FORMAL_POLICY_IDS:
            pair_index += 1
            pair_rows = []
            for arm_id in ARM_IDS:
                row_index += 1
                with isolated_patched_checkout(input_id, work_root / f"row-{row_index:02d}") as (modules, _prefix, copy_digest):
                    row = _run_trajectory(
                        row_index=row_index, pair_index=pair_index, input_id=input_id,
                        policy_id=policy_id, arm_id=arm_id, modules=modules,
                        copy_digest=copy_digest, cases_by_action=cases_by_action,
                        artifact=artifacts[input_id],
                    )
                pair_rows.append(row)
            pair = _finish_pair(pair_rows[0], pair_rows[1])
            rows.extend(pair_rows)
            pairs.append(pair)
            events.append({"event": "p2g_pair_completed", "pair_index": pair_index, "input_position": input_position, "input_id": input_id, "policy_id": policy_id})
    aggregate = derive_aggregate_results(rows, pairs, gate)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "analysis_phase": ANALYSIS_PHASE,
        "audit_id": AUDIT_ID,
        "report_role": REPORT_ROLE,
        "validation_status": {"status": VALID_STATUS},
        "input_identity": {
            "base_commit": BASE_COMMIT, "base_tree": BASE_TREE,
            "input_contracts": contracts,
            "input_contract_digest": _digest(contracts),
            "dependency_file_sha256_lf": deepcopy(DEPENDENCY_SHA256_LF),
            "dependency_contract_digest": _digest(DEPENDENCY_SHA256_LF),
        },
        "pre_outcome_freeze": {
            "specification_sha256_lf": SPECIFICATION_SHA256_LF,
            "specification_review_sha256_lf": SPECIFICATION_REVIEW_SHA256_LF,
            "implementation_file_sha256_lf": deepcopy(
                HISTORICAL_FIRST_OUTCOME_IMPLEMENTATION_IDENTITY
            ),
            "first_outcome_executed_after_freeze": True,
        },
        "execution_boundary": {
            "input_semantics": "exact five accepted P2a benign non-empty-diff clean patches",
            "control_semantics": "accepted normal stop/action/update loop",
            "intervention_semantics": "suppress only no_bug_probability_threshold at every pre-action decision",
            "clean_validity_semantics": "all accepted input-specific clean oracles pass before policy trajectories",
        },
        "population": _population(),
        "definitions": {
            "false_positive": "terminal bug_confidence_threshold OR final bug_presence_posterior >= 0.75",
            "execution_failure_observed": "any executed frozen catalog result failed",
            "bug_detected_observation": "any observation has bug_detected=true",
            "normal_no_bug_stop": "normal control terminates at no_bug_probability_threshold",
            "truthful_benign_diff": "accepted non-empty repository-relative patch path, changed file/function, and excerpt",
        },
        "trajectory_results": rows,
        "pair_results": pairs,
        "aggregate_results": aggregate,
        "software_acceptance": _pending("software_conformance"),
        "artifact_identity_acceptance": _pending("versioned_artifact_identity"),
        "result_acceptance": _pending("descriptive_result"),
        "documentation_acceptance": _pending("public_result_documentation"),
        "limitations": list(_LIMITATIONS),
        "non_claims": list(_NON_CLAIMS),
        "notes": [
            "P2f no-diff rows and P2a buggy or P2e rows are not pooled into this denominator.",
            "External review records, not this artifact, decide acceptance.",
        ],
    }
    summary["aggregate_results"]["digests"]["canonical_summary_digest"] = _summary_digest(summary)
    if _raw_dependency_snapshot() != raw_before:
        raise P2GAuditError("accepted dependency raw bytes changed during execution")
    if implementation_identity() != implementation_before:
        raise P2GAuditError("P2g implementation changed during execution")
    validated = validate_audit_summary(summary)
    events.append({"event": "p2g_audit_validated", "trajectory_count": 60, "pair_count": 30})
    return validated


def record_artifacts_serialized(event_log: list[dict[str, Any]]) -> None:
    event_log.append({"event": "p2g_artifacts_serialized"})
