"""Candidate-independent validation for a future P2a freeze draft.

The functions here validate and canonicalize caller-supplied draft material.
They do not author candidates, read policy results, collect the current time,
realize a freeze, or emit an accepted/evaluation-ready status.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from bug_cause_inference.p2a.adequacy import (
    ACTION_TEST_CATALOG_VERSION,
    ADAPTER_CONTRACT_VERSION,
    BENCHMARK_ID,
    BUGGY_BUCKET_IDS,
    COVERAGE_GAP_REGISTRY_VERSION,
    DATASET_SCHEMA_VERSION,
    POLICY_OUTCOME_FIELD_IDS,
    TRUSTED_REFERENCE_REGISTRY_VERSION,
    AdequacyValidationError,
    ReasonCode,
    ValidationIssue,
    canonical_digest,
    canonical_json,
    clean_family_definitions,
    coverage_gap_registry_digest,
    trusted_reference_registry_digest,
    validate_candidate_cohort,
    validate_portable_value,
    validate_sha256,
    validate_taxonomy_identity,
)


FREEZE_DRAFT_SCHEMA_VERSION = "p2a_freeze_draft.v1"
ARTIFACT_MANIFEST_SCHEMA_VERSION = "p2a_artifact_manifest.v1"
POLICY_IDENTITY_VERSION = "p2a_policy_registry_identity.v1"
SETTINGS_IDENTITY_VERSION = "p2a_fixed_settings_identity.v1"
METRIC_IDENTITY_VERSION = "p2a_metric_contract_identity.v1"
SERIALIZER_IDENTITY_VERSION = "p2a_serializer_contract_identity.v1"

_DRAFT_FIELD_IDS = (
    "draft_schema_version",
    "dataset_identity",
    "artifact_identity",
    "adapter_identity",
    "catalog_identity",
    "policy_identity",
    "settings_identity",
    "metric_identity",
    "serializer_identity",
    "coverage_registry_identity",
    "trusted_reference_registry_identity",
    "freeze_timestamp",
    "buggy_bucket_ids",
    "clean_family_definitions",
    "variant_ids",
    "buggy_candidates",
    "clean_candidates",
)
_IDENTITY_CONTRACTS = (
    (
        "dataset_identity",
        ("schema_version", "benchmark_id", "candidate_manifest_digest"),
        {"schema_version": DATASET_SCHEMA_VERSION, "benchmark_id": BENCHMARK_ID},
        "candidate_manifest_digest",
    ),
    (
        "artifact_identity",
        ("schema_version", "artifact_manifest_digest"),
        {"schema_version": ARTIFACT_MANIFEST_SCHEMA_VERSION},
        "artifact_manifest_digest",
    ),
    (
        "adapter_identity",
        ("contract_version", "digest"),
        {"contract_version": ADAPTER_CONTRACT_VERSION},
        "digest",
    ),
    (
        "catalog_identity",
        ("catalog_version", "digest"),
        {"catalog_version": ACTION_TEST_CATALOG_VERSION},
        "digest",
    ),
    (
        "policy_identity",
        ("identity_version", "digest"),
        {"identity_version": POLICY_IDENTITY_VERSION},
        "digest",
    ),
    (
        "settings_identity",
        ("identity_version", "digest"),
        {"identity_version": SETTINGS_IDENTITY_VERSION},
        "digest",
    ),
    (
        "metric_identity",
        ("identity_version", "digest"),
        {"identity_version": METRIC_IDENTITY_VERSION},
        "digest",
    ),
    (
        "serializer_identity",
        ("identity_version", "digest"),
        {"identity_version": SERIALIZER_IDENTITY_VERSION},
        "digest",
    ),
    (
        "coverage_registry_identity",
        ("registry_version", "registry_digest"),
        {"registry_version": COVERAGE_GAP_REGISTRY_VERSION},
        "registry_digest",
    ),
    (
        "trusted_reference_registry_identity",
        ("registry_version", "registry_digest"),
        {"registry_version": TRUSTED_REFERENCE_REGISTRY_VERSION},
        "registry_digest",
    ),
)


@dataclass(frozen=True)
class FreezeDraftValidationResult:
    status: str
    canonical_payload: str
    draft_digest: str
    candidate_manifest_digest: str
    variant_count: int
    buggy_count: int
    clean_count: int


def _fail(code: ReasonCode, path: str, message: str) -> None:
    raise AdequacyValidationError(ValidationIssue(code.value, path, message))


def _require_exact_fields(value: Any, fields: tuple[str, ...], path: str) -> dict[str, Any]:
    if type(value) is not dict:
        _fail(ReasonCode.WRONG_TYPE, path, "expected an object")
    keys = set(value)
    if keys & POLICY_OUTCOME_FIELD_IDS:
        _fail(
            ReasonCode.POLICY_OUTCOME_FIELD_FORBIDDEN,
            path,
            "policy-result material is outside the freeze draft schema",
        )
    missing = [field for field in fields if field not in value]
    if missing:
        _fail(ReasonCode.MISSING_FIELD, f"{path}.{missing[0]}", "required field is missing")
    unknown = [key for key in value if key not in fields]
    if unknown:
        _fail(ReasonCode.UNKNOWN_FIELD, f"{path}.{unknown[0]}", "field is not allowlisted")
    return value


def _validate_exact_version(value: Any, expected: str, path: str) -> None:
    if type(value) is not str or value != expected:
        _fail(ReasonCode.WRONG_VERSION, path, "identity version does not match the draft contract")


def _validate_timestamp(value: Any) -> str:
    if type(value) is not str:
        _fail(ReasonCode.WRONG_TYPE, "freeze_timestamp", "expected a caller-supplied UTC string")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        _fail(
            ReasonCode.WRONG_IDENTITY,
            "freeze_timestamp",
            "expected exact UTC form YYYY-MM-DDTHH:MM:SSZ",
        )
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        _fail(ReasonCode.WRONG_IDENTITY, "freeze_timestamp", "timestamp is not canonical UTC")
    return value


def candidate_manifest_payload(
    buggy_candidates: Any,
    clean_candidates: Any,
) -> dict[str, Any]:
    """Return the stable candidate-manifest digest input after adequacy validation."""

    buggy, clean = validate_candidate_cohort(buggy_candidates, clean_candidates)
    variant_ids = [item["variant_id"] for item in buggy + clean]
    return {
        "dataset_schema_version": DATASET_SCHEMA_VERSION,
        "benchmark_id": BENCHMARK_ID,
        "trusted_reference_registry_version": TRUSTED_REFERENCE_REGISTRY_VERSION,
        "trusted_reference_registry_digest": trusted_reference_registry_digest(),
        "variant_ids": variant_ids,
        "buggy_bucket_ids": list(BUGGY_BUCKET_IDS),
        "clean_family_definitions": clean_family_definitions(),
        "buggy_candidates": buggy,
        "clean_candidates": clean,
    }


def candidate_manifest_digest(
    buggy_candidates: Any,
    clean_candidates: Any,
) -> str:
    return canonical_digest(candidate_manifest_payload(buggy_candidates, clean_candidates))


def validate_freeze_draft(draft: Any) -> FreezeDraftValidationResult:
    """Validate a synthetic/future draft and return only a tooling-level result."""

    value = _require_exact_fields(draft, _DRAFT_FIELD_IDS, "draft")
    validate_portable_value(value, "draft")
    _validate_exact_version(
        value["draft_schema_version"],
        FREEZE_DRAFT_SCHEMA_VERSION,
        "draft.draft_schema_version",
    )
    canonical_identities: dict[str, dict[str, Any]] = {}
    for identity_name, fields, expected_versions, digest_field in _IDENTITY_CONTRACTS:
        identity = _require_exact_fields(value[identity_name], fields, f"draft.{identity_name}")
        for version_field, expected_version in expected_versions.items():
            _validate_exact_version(
                identity[version_field],
                expected_version,
                f"draft.{identity_name}.{version_field}",
            )
        validate_sha256(identity[digest_field], f"draft.{identity_name}.{digest_field}")
        canonical_identities[identity_name] = {field: identity[field] for field in fields}

    validate_taxonomy_identity(value["buggy_bucket_ids"], value["clean_family_definitions"])
    buggy, clean = validate_candidate_cohort(value["buggy_candidates"], value["clean_candidates"])
    expected_variant_ids = [item["variant_id"] for item in buggy + clean]
    if type(value["variant_ids"]) is not list or any(type(item) is not str for item in value["variant_ids"]):
        _fail(ReasonCode.WRONG_TYPE, "draft.variant_ids", "expected a list of strings")
    if len(set(value["variant_ids"])) != len(value["variant_ids"]):
        _fail(ReasonCode.DUPLICATE_VARIANT_ID, "draft.variant_ids", "variant IDs must be unique")
    if value["variant_ids"] != expected_variant_ids:
        _fail(ReasonCode.REORDERED_VARIANT_ID, "draft.variant_ids", "variant IDs must exactly match candidate stable order")

    manifest_payload = {
        "dataset_schema_version": DATASET_SCHEMA_VERSION,
        "benchmark_id": BENCHMARK_ID,
        "trusted_reference_registry_version": TRUSTED_REFERENCE_REGISTRY_VERSION,
        "trusted_reference_registry_digest": trusted_reference_registry_digest(),
        "variant_ids": expected_variant_ids,
        "buggy_bucket_ids": list(BUGGY_BUCKET_IDS),
        "clean_family_definitions": clean_family_definitions(),
        "buggy_candidates": buggy,
        "clean_candidates": clean,
    }
    observed_manifest_digest = canonical_digest(manifest_payload)
    if canonical_identities["dataset_identity"]["candidate_manifest_digest"] != observed_manifest_digest:
        _fail(
            ReasonCode.WRONG_DIGEST,
            "draft.dataset_identity.candidate_manifest_digest",
            "candidate manifest digest does not match the validated cohort",
        )
    expected_registry_digest = coverage_gap_registry_digest()
    if canonical_identities["coverage_registry_identity"]["registry_digest"] != expected_registry_digest:
        _fail(
            ReasonCode.WRONG_DIGEST,
            "draft.coverage_registry_identity.registry_digest",
            "coverage registry digest does not match the stable P2a registry",
        )
    expected_reference_registry_digest = trusted_reference_registry_digest()
    if (
        canonical_identities["trusted_reference_registry_identity"]["registry_digest"]
        != expected_reference_registry_digest
    ):
        _fail(
            ReasonCode.WRONG_DIGEST,
            "draft.trusted_reference_registry_identity.registry_digest",
            "trusted reference registry digest does not match the reviewed legacy contract",
        )
    freeze_timestamp = _validate_timestamp(value["freeze_timestamp"])

    canonical_value = {
        "draft_schema_version": FREEZE_DRAFT_SCHEMA_VERSION,
        **canonical_identities,
        "freeze_timestamp": freeze_timestamp,
        "buggy_bucket_ids": list(BUGGY_BUCKET_IDS),
        "clean_family_definitions": clean_family_definitions(),
        "variant_ids": expected_variant_ids,
        "buggy_candidates": buggy,
        "clean_candidates": clean,
    }
    payload = canonical_json(canonical_value)
    return FreezeDraftValidationResult(
        status="draft_valid",
        canonical_payload=payload,
        draft_digest=canonical_digest(canonical_value),
        candidate_manifest_digest=observed_manifest_digest,
        variant_count=len(expected_variant_ids),
        buggy_count=len(buggy),
        clean_count=len(clean),
    )
