"""Patch feasibility and review-pending manifest helpers for P2a authoring."""

from __future__ import annotations

import hashlib
import json
import shutil
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
from typing import Any, Iterator

from bug_cause_inference.p1b.real_diff import (
    apply_unified_patch,
    changed_files_in_patch,
    changed_functions_in_patch,
    generated_checkout_imports,
)
from bug_cause_inference.p2a.adequacy import (
    BENCHMARK_ID,
    BUGGY_BUCKET_IDS,
    CLEAN_STRESS_FAMILY_IDS,
    COVERAGE_GAP_REGISTRY_VERSION,
    DATASET_SCHEMA_VERSION,
    TRUSTED_REFERENCE_REGISTRY_VERSION,
    canonical_digest,
    canonical_json,
    coverage_gap_registry_digest,
    trusted_reference_registry_digest,
    validate_portable_value,
)
from bug_cause_inference.p2a.candidate_oracles import (
    ORACLE_DEFINITION_SCHEMA_VERSION,
    oracle_definition_digest,
    oracle_definition_payload,
    run_oracle,
)
from bug_cause_inference.p2a.candidates import (
    BUGGY_CANDIDATE_METADATA,
    BUGGY_CANDIDATES,
    CANDIDATE_IDS,
    CLEAN_CANDIDATE_METADATA,
    CLEAN_CANDIDATES,
    PATCH_OPERATION_SCHEMA_VERSION,
    CandidateDefinition,
    canonical_patch_operation_digest,
    canonical_patch_operation_identity,
)
from bug_cause_inference.p2a.freeze import candidate_manifest_digest


AUTHORING_MANIFEST_SCHEMA_VERSION = "p2a_candidate_authoring_manifest.v2"
AUTHORING_STATUS = "review_pending"
AUTHORING_MANIFEST_PATH = (
    "src/bug_cause_inference/p2a/artifacts/candidates/authoring_manifest.json"
)

_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
_BASELINE_ROOT = (
    _REPOSITORY_ROOT
    / "src"
    / "bug_cause_inference"
    / "p1b"
    / "artifacts"
    / "real_diff"
    / "baseline"
)
_TOP_LEVEL_FIELDS = (
    "schema_version",
    "status",
    "patch_operation_schema_version",
    "oracle_definition_schema_version",
    "dataset_identity",
    "trusted_reference_registry_identity",
    "coverage_gap_registry_identity",
    "candidate_manifest_digest",
    "variant_ids",
    "buggy_bucket_membership",
    "clean_family_membership",
    "candidates",
)
_CANDIDATE_FIELDS = (
    "variant_id",
    "cohort_kind",
    "primary_taxonomy_id",
    "patch_path",
    "patch_sha256",
    "patch_operation_schema_version",
    "patch_operation_digest",
    "changed_files",
    "changed_functions",
    "oracle_ids",
    "oracle_definition_schema_version",
    "oracle_definition_digest",
    "baseline_ground_truth_status",
    "candidate_ground_truth_status",
    "oracle_statuses",
)


class CandidateAuthoringError(ValueError):
    """Raised when authored ground truth or artifact identity is inconsistent."""


def _exact_fields(value: Any, fields: tuple[str, ...], path: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise CandidateAuthoringError(f"{path}: expected an object")
    missing = [field for field in fields if field not in value]
    unknown = [field for field in value if field not in fields]
    if missing:
        raise CandidateAuthoringError(f"{path}.{missing[0]}: missing field")
    if unknown:
        raise CandidateAuthoringError(f"{path}.{unknown[0]}: unknown field")
    return value


def repository_path(relative_path: str) -> Path:
    parsed = PurePosixPath(relative_path)
    if parsed.is_absolute() or ".." in parsed.parts:
        raise CandidateAuthoringError("artifact path must be repository-relative")
    target = _REPOSITORY_ROOT.joinpath(*parsed.parts)
    resolved = target.resolve()
    root = _REPOSITORY_ROOT.resolve()
    if resolved != root and root not in resolved.parents:
        raise CandidateAuthoringError("artifact path escapes the repository")
    return target


def patch_text(candidate: CandidateDefinition) -> str:
    text = repository_path(candidate.patch_path).read_text(encoding="utf-8")
    if not text.strip():
        raise CandidateAuthoringError(f"{candidate.variant_id}: patch must be non-empty")
    return text


@contextmanager
def _candidate_modules(candidate: CandidateDefinition) -> Iterator[dict[str, Any]]:
    with TemporaryDirectory(prefix="p2a-candidate-") as temporary:
        tree_root = Path(temporary) / "baseline"
        shutil.copytree(_BASELINE_ROOT, tree_root)
        apply_unified_patch(tree_root, patch_text(candidate))
        with generated_checkout_imports(tree_root) as modules:
            yield modules


@contextmanager
def _baseline_modules() -> Iterator[dict[str, Any]]:
    with generated_checkout_imports(_BASELINE_ROOT) as modules:
        yield modules


def _run(candidate: CandidateDefinition, *, patched: bool) -> list[dict[str, Any]]:
    context = _candidate_modules(candidate) if patched else _baseline_modules()
    with context as modules:
        return [
            {
                "oracle_id": oracle_id,
                "status": "pass" if result.passed else "fail",
                "expected": result.expected,
                "actual": result.actual,
            }
            for oracle_id in candidate.oracle_ids
            for result in (run_oracle(oracle_id, modules),)
        ]


def author_candidate(candidate: CandidateDefinition) -> dict[str, Any]:
    text = patch_text(candidate)
    operation_digest = canonical_patch_operation_digest(candidate.patch_path)
    operation_identity = canonical_patch_operation_identity(candidate.patch_path)
    if candidate.metadata["patch_semantic_fingerprint"] != operation_identity:
        raise CandidateAuthoringError(
            f"{candidate.variant_id}: patch semantic fingerprint differs from artifact"
        )
    if (
        candidate.metadata["core_fingerprint"]["normalized_patch_operation"]
        != operation_identity
    ):
        raise CandidateAuthoringError(
            f"{candidate.variant_id}: normalized patch operation differs from artifact"
        )
    files = changed_files_in_patch(text)
    functions = changed_functions_in_patch(text, tree_root=_BASELINE_ROOT)
    if files != candidate.metadata["changed_files"]:
        raise CandidateAuthoringError(
            f"{candidate.variant_id}: patch files differ from metadata"
        )
    if functions != candidate.metadata["changed_functions"]:
        raise CandidateAuthoringError(
            f"{candidate.variant_id}: patch functions differ from metadata"
        )
    baseline = _run(candidate, patched=False)
    patched = _run(candidate, patched=True)
    if any(item["status"] != "pass" for item in baseline):
        raise CandidateAuthoringError(
            f"{candidate.variant_id}: canonical baseline ground truth failed"
        )
    if candidate.cohort_kind == "buggy":
        if not any(item["status"] == "fail" for item in patched):
            raise CandidateAuthoringError(
                f"{candidate.variant_id}: buggy patch did not fail its oracle"
            )
        candidate_status = "required_fail_observed"
    else:
        if any(item["status"] != "pass" for item in patched):
            raise CandidateAuthoringError(
                f"{candidate.variant_id}: benign patch failed a no-bug oracle"
            )
        candidate_status = "all_pass"
    return {
        "variant_id": candidate.variant_id,
        "cohort_kind": candidate.cohort_kind,
        "primary_taxonomy_id": (
            candidate.metadata["primary_bucket"]
            if candidate.cohort_kind == "buggy"
            else candidate.metadata["clean_stress_family_id"]
        ),
        "patch_path": candidate.patch_path,
        "patch_sha256": hashlib.sha256(
            repository_path(candidate.patch_path).read_bytes()
        ).hexdigest(),
        "patch_operation_schema_version": PATCH_OPERATION_SCHEMA_VERSION,
        "patch_operation_digest": operation_digest,
        "changed_files": files,
        "changed_functions": functions,
        "oracle_ids": list(candidate.oracle_ids),
        "oracle_definition_schema_version": ORACLE_DEFINITION_SCHEMA_VERSION,
        "oracle_definition_digest": oracle_definition_digest(
            oracle_definition_payload(candidate.oracle_ids)
        ),
        "baseline_ground_truth_status": "all_pass",
        "candidate_ground_truth_status": candidate_status,
        "oracle_statuses": [
            {
                "oracle_id": oracle_id,
                "baseline_status": baseline_item["status"],
                "candidate_status": patched_item["status"],
            }
            for oracle_id, baseline_item, patched_item in zip(
                candidate.oracle_ids, baseline, patched, strict=True
            )
        ],
    }


def build_authoring_manifest() -> dict[str, Any]:
    evidence = [
        author_candidate(candidate)
        for candidate in (*BUGGY_CANDIDATES, *CLEAN_CANDIDATES)
    ]
    manifest = {
        "schema_version": AUTHORING_MANIFEST_SCHEMA_VERSION,
        "status": AUTHORING_STATUS,
        "patch_operation_schema_version": PATCH_OPERATION_SCHEMA_VERSION,
        "oracle_definition_schema_version": ORACLE_DEFINITION_SCHEMA_VERSION,
        "dataset_identity": {
            "schema_version": DATASET_SCHEMA_VERSION,
            "benchmark_id": BENCHMARK_ID,
        },
        "trusted_reference_registry_identity": {
            "registry_version": TRUSTED_REFERENCE_REGISTRY_VERSION,
            "registry_digest": trusted_reference_registry_digest(),
        },
        "coverage_gap_registry_identity": {
            "registry_version": COVERAGE_GAP_REGISTRY_VERSION,
            "registry_digest": coverage_gap_registry_digest(),
        },
        "candidate_manifest_digest": candidate_manifest_digest(
            BUGGY_CANDIDATE_METADATA, CLEAN_CANDIDATE_METADATA
        ),
        "variant_ids": list(CANDIDATE_IDS),
        "buggy_bucket_membership": [
            {
                "bucket_id": bucket,
                "candidate_ids": [
                    item.variant_id
                    for item in BUGGY_CANDIDATES
                    if item.metadata["primary_bucket"] == bucket
                ],
            }
            for bucket in BUGGY_BUCKET_IDS
        ],
        "clean_family_membership": [
            {
                "family_id": family,
                "candidate_ids": [
                    item.variant_id
                    for item in CLEAN_CANDIDATES
                    if item.metadata["clean_stress_family_id"] == family
                ],
            }
            for family in CLEAN_STRESS_FAMILY_IDS
        ],
        "candidates": evidence,
    }
    validate_portable_value(manifest, "authoring_manifest")
    return manifest


def authoring_manifest_digest(manifest: Any | None = None) -> str:
    validated = validate_authoring_manifest(
        build_authoring_manifest() if manifest is None else manifest
    )
    return canonical_digest(validated)


def validate_authoring_manifest(manifest: Any) -> dict[str, Any]:
    value = _exact_fields(manifest, _TOP_LEVEL_FIELDS, "authoring_manifest")
    validate_portable_value(value, "authoring_manifest")
    if value["schema_version"] != AUTHORING_MANIFEST_SCHEMA_VERSION:
        raise CandidateAuthoringError("authoring_manifest.schema_version: wrong version")
    if value["status"] != AUTHORING_STATUS:
        raise CandidateAuthoringError("authoring_manifest.status: expected review_pending")
    forbidden_freeze_fields = {
        "freeze_timestamp",
        "freeze_digest",
        "policy_identity",
        "settings_identity",
        "metric_identity",
        "serializer_identity",
        "accepted",
        "valid_for_evaluation",
    }
    if set(value) & forbidden_freeze_fields:
        raise CandidateAuthoringError("official freeze fields are forbidden")
    for index, candidate in enumerate(value["candidates"]):
        _exact_fields(candidate, _CANDIDATE_FIELDS, f"authoring_manifest.candidates[{index}]")
    expected = build_authoring_manifest()
    if canonical_json(value) != canonical_json(expected):
        raise CandidateAuthoringError(
            "authoring manifest differs from validated metadata, artifact, or oracle evidence"
        )
    return expected


def load_tracked_authoring_manifest() -> dict[str, Any]:
    path = repository_path(AUTHORING_MANIFEST_PATH)
    value = json.loads(path.read_text(encoding="utf-8"))
    return validate_authoring_manifest(value)


def serialized_authoring_manifest() -> str:
    return json.dumps(
        build_authoring_manifest(),
        ensure_ascii=False,
        indent=2,
        allow_nan=False,
    ) + "\n"
