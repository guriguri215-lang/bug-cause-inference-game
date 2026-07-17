"""Realize the reviewed P2a candidate cohort as an official freeze input.

This module binds authored candidates and outcome-free contracts only. It does
not run a policy, calculate a benchmark result, authorize evaluation, or
collect the current time. The freeze timestamp is always supplied by a caller.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any

from bug_cause_inference.p2a.adequacy import (
    ACTION_TEST_CATALOG_VERSION,
    ADAPTER_CONTRACT_VERSION,
    ANALYSIS_PHASE,
    APPROVED_ACTION_IDS,
    BENCHMARK_ID,
    BUGGY_BUCKET_IDS,
    COVERAGE_GAP_REGISTRY_VERSION,
    DATASET_SCHEMA_VERSION,
    REPORT_SCHEMA_VERSION,
    TRUSTED_REFERENCE_REGISTRY_VERSION,
    canonical_digest,
    canonical_json,
    clean_family_definitions,
    coverage_gap_registry_digest,
    trusted_reference_registry_digest,
    validate_portable_value,
)
from bug_cause_inference.p2a.candidate_authoring import (
    AUTHORING_MANIFEST_PATH,
    AUTHORING_MANIFEST_SCHEMA_VERSION,
    AUTHORING_STATUS,
    build_authoring_manifest,
    repository_path,
    serialized_authoring_manifest,
    validate_authoring_manifest,
)
from bug_cause_inference.p2a.candidate_oracles import (
    COMPARISON_SEMANTICS_VERSION,
    ORACLE_DEFINITION_SCHEMA_VERSION,
    oracle_definition_digest,
    oracle_definition_payload,
)
from bug_cause_inference.p2a.candidates import (
    BUGGY_CANDIDATE_METADATA,
    CANDIDATES,
    CLEAN_CANDIDATE_METADATA,
    PATCH_OPERATION_SCHEMA_VERSION,
)
from bug_cause_inference.p2a.freeze import (
    ARTIFACT_MANIFEST_SCHEMA_VERSION,
    FREEZE_DRAFT_SCHEMA_VERSION,
    METRIC_IDENTITY_VERSION,
    POLICY_IDENTITY_VERSION,
    SERIALIZER_IDENTITY_VERSION,
    SETTINGS_IDENTITY_VERSION,
    candidate_manifest_payload,
    validate_freeze_draft,
)


OFFICIAL_FREEZE_BUNDLE_SCHEMA_VERSION = "p2a_official_freeze_bundle.v1"
OFFICIAL_FREEZE_STATUS = "freeze_realized_pending_independent_review"
INDEPENDENT_REVIEW_GATE_VERSION = "p2a_frozen_dataset_independent_review.v1"
ARTIFACT_MANIFEST_PATH = (
    "src/bug_cause_inference/p2a/artifacts/freeze/artifact_manifest.json"
)
OFFICIAL_FREEZE_BUNDLE_PATH = (
    "src/bug_cause_inference/p2a/artifacts/freeze/official_freeze_bundle.json"
)

EXPECTED_CANDIDATE_MANIFEST_DIGEST = (
    "97c2d0c0379d69010195a4b7448137e566214d88638b0f7642ee59677389cd47"
)
EXPECTED_AUTHORING_MANIFEST_DIGEST = (
    "2a188d26c018beb0270fedfee5326a4a9e2f3c7435d8b6017cd76df13535746a"
)
EXPECTED_TRUSTED_REFERENCE_REGISTRY_DIGEST = (
    "e430974d39f7b137a0a2d0c754a43613a42a081cc4800ec2ca4a90b172e6d203"
)
EXPECTED_COVERAGE_GAP_REGISTRY_DIGEST = (
    "3e36bad4553da16ab3053fc0f976a5dad80d055422339add6a80df5b2c89ed15"
)
EXPECTED_LEGACY_RUNTIME_DIGEST = (
    "a7eede0058030e83b1552b71a83aff55596b16b03d05522e61375d32fa67987d"
)
EXPECTED_LEGACY_CATALOG_DIGEST = (
    "a62d0c6a11ae5f57cffa572bd06277d863e52df6a5367235a6a804adc8bc01dd"
)
EXPECTED_LEGACY_ARTIFACT_DIGEST = (
    "87f5fc00cde1cb8d02f4df7651b98c4e0e75ace833da82e256c29e1f90ad3d8c"
)

FORMAL_POLICY_IDS = (
    "fixed_checklist",
    "test_first",
    "coverage_first",
    "recent_diff_first",
    "cause_only_p1a_style",
    "expected_utility_per_cost",
)
EXCLUDED_POLICY_IDS = ("random_action", "state_sequence_guard")
STOP_PRECEDENCE = (
    "no_bug_probability_threshold",
    "bug_confidence_threshold",
    "budget_limit",
    "max_steps",
    "low_expected_utility",
)
BUGGY_RESULT_IDENTITIES = (
    "accepted_legacy_reference_buggy",
    "p2a_replayed_legacy_buggy",
    "expansion_only_buggy",
    "combined_versioned_buggy",
)
CLEAN_RESULT_IDENTITIES = (
    "accepted_legacy_reference_clean",
    "p2a_replayed_legacy_clean",
    "expansion_only_clean",
    "combined_versioned_clean",
)

_CASE_ACTION_BY_CANDIDATE = {
    "P2A-BUG-001": "run_boundary_tests",
    "P2A-BUG-002": "run_boundary_tests",
    "P2A-BUG-003": "run_null_missing_tests",
    "P2A-BUG-004": "run_null_missing_tests",
    "P2A-BUG-005": "run_config_matrix_tests",
    "P2A-BUG-006": "run_config_matrix_tests",
    "P2A-BUG-007": "run_state_sequence_tests",
    "P2A-BUG-008": "run_state_sequence_tests",
    "P2A-BUG-009": "inspect_spec_clause",
    "P2A-BUG-010": "inspect_spec_clause",
    "P2A-CLEAN-001": "run_boundary_tests",
    "P2A-CLEAN-002": "run_null_missing_tests",
    "P2A-CLEAN-003": "run_config_matrix_tests",
    "P2A-CLEAN-004": "run_state_sequence_tests",
    "P2A-CLEAN-005": "inspect_spec_clause",
}

# Declarative copies of the existing public P1b action contract. Keeping these
# values local prevents this freeze builder from importing an execution module.
_ACTION_SPECS = (
    (
        "run_smoke_tests",
        1,
        "test_failure",
        ("specification_mismatch", "missing_null_handling"),
        0.45,
        0.25,
    ),
    (
        "run_boundary_tests",
        2,
        "boundary_counterexample",
        ("boundary_condition",),
        0.70,
        0.45,
    ),
    (
        "run_null_missing_tests",
        2,
        "exception_trace",
        ("missing_null_handling",),
        0.70,
        0.55,
    ),
    (
        "run_config_matrix_tests",
        3,
        "config_counterexample",
        ("configuration_environment",),
        0.70,
        0.45,
    ),
    (
        "run_state_sequence_tests",
        4,
        "state_sequence_counterexample",
        ("state_order_dependence",),
        0.75,
        0.55,
    ),
    (
        "run_property_search",
        5,
        "property_counterexample",
        ("boundary_condition", "state_order_dependence", "specification_mismatch"),
        0.65,
        0.35,
    ),
    (
        "inspect_traceback",
        1,
        "exception_trace",
        ("missing_null_handling", "configuration_environment"),
        0.30,
        0.70,
    ),
    ("inspect_coverage_spectrum", 3, "coverage_suspicious_location", (), 0.15, 0.85),
    (
        "inspect_recent_diff",
        2,
        "recent_diff_signal",
        ("configuration_environment", "state_order_dependence", "boundary_condition"),
        0.20,
        0.55,
    ),
    (
        "inspect_spec_clause",
        2,
        "spec_clause_mismatch",
        ("specification_mismatch", "boundary_condition", "configuration_environment"),
        0.45,
        0.50,
    ),
)

_MINIMUM_REPORT_TOP_LEVEL_FIELDS = (
    "schema_version",
    "analysis_phase",
    "benchmark_id",
    "report_role",
    "observation_mode",
    "legacy_benchmark_identity",
    "dataset_identity",
    "adapter_identity",
    "action_test_catalog_identity",
    "freeze_identity",
    "validation_status",
    "dataset_summary",
    "cohort_definitions",
    "formal_strategy_ids",
    "excluded_policy_ids",
    "fixed_settings",
    "bucket_ids",
    "bucket_support_by_cohort",
    "clean_family_support_by_cohort",
    "reference_distribution_by_cohort",
    "primary_buggy_results_by_cohort",
    "clean_results_by_cohort",
    "secondary_metric_results_by_cohort",
    "sensitivity",
    "software_acceptance",
    "limitations",
    "non_claims",
    "notes",
)


class FreezeRealizationError(ValueError):
    """Raised when official freeze material is incomplete or inconsistent."""


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _serialized(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"


def _require_exact_fields(
    value: Any, fields: tuple[str, ...], path: str
) -> dict[str, Any]:
    if type(value) is not dict:
        raise FreezeRealizationError(f"{path}: expected an object")
    missing = [field for field in fields if field not in value]
    unknown = [field for field in value if field not in fields]
    if missing:
        raise FreezeRealizationError(f"{path}.{missing[0]}: missing field")
    if unknown:
        raise FreezeRealizationError(f"{path}.{unknown[0]}: unknown field")
    return value


def _assert_expected_identity(name: str, observed: str, expected: str) -> None:
    if observed != expected:
        raise FreezeRealizationError(
            f"{name}: expected accepted digest {expected}, observed {observed}"
        )


def _authoring_source() -> tuple[dict[str, Any], bytes, str]:
    tracked_path = repository_path(AUTHORING_MANIFEST_PATH)
    tracked_bytes = tracked_path.read_bytes()
    try:
        tracked_value = json.loads(tracked_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FreezeRealizationError(
            "tracked authoring manifest is not canonical UTF-8 JSON"
        ) from exc
    generated = build_authoring_manifest()
    validate_authoring_manifest(tracked_value)
    if canonical_json(tracked_value) != canonical_json(generated):
        raise FreezeRealizationError("tracked authoring manifest differs semantically")
    generated_bytes = serialized_authoring_manifest().encode("utf-8")
    if tracked_bytes != generated_bytes:
        raise FreezeRealizationError("tracked authoring manifest differs byte-for-byte")
    digest = canonical_digest(generated)
    _assert_expected_identity(
        "authoring_manifest_digest", digest, EXPECTED_AUTHORING_MANIFEST_DIGEST
    )
    return generated, tracked_bytes, digest


def build_artifact_manifest() -> dict[str, Any]:
    """Build the portable official artifact manifest from reviewed inputs."""

    authoring, authoring_bytes, authoring_digest = _authoring_source()
    candidate_payload = candidate_manifest_payload(
        BUGGY_CANDIDATE_METADATA, CLEAN_CANDIDATE_METADATA
    )
    candidate_digest = canonical_digest(candidate_payload)
    _assert_expected_identity(
        "candidate_manifest_digest",
        candidate_digest,
        EXPECTED_CANDIDATE_MANIFEST_DIGEST,
    )
    trusted_digest = trusted_reference_registry_digest()
    coverage_digest = coverage_gap_registry_digest()
    _assert_expected_identity(
        "trusted_reference_registry_digest",
        trusted_digest,
        EXPECTED_TRUSTED_REFERENCE_REGISTRY_DIGEST,
    )
    _assert_expected_identity(
        "coverage_gap_registry_digest",
        coverage_digest,
        EXPECTED_COVERAGE_GAP_REGISTRY_DIGEST,
    )

    metadata_by_id = {
        item["variant_id"]: item
        for item in candidate_payload["buggy_candidates"]
        + candidate_payload["clean_candidates"]
    }
    evidence_by_id = {item["variant_id"]: item for item in authoring["candidates"]}
    candidate_artifacts = []
    for candidate in CANDIDATES:
        evidence = evidence_by_id[candidate.variant_id]
        patch_bytes = repository_path(evidence["patch_path"]).read_bytes()
        patch_digest = _sha256_bytes(patch_bytes)
        if patch_digest != evidence["patch_sha256"]:
            raise FreezeRealizationError(
                f"{candidate.variant_id}: raw patch SHA-256 differs from authoring manifest"
            )
        oracle_records = oracle_definition_payload(list(candidate.oracle_ids))
        observed_oracle_digest = oracle_definition_digest(oracle_records)
        if observed_oracle_digest != evidence["oracle_definition_digest"]:
            raise FreezeRealizationError(
                f"{candidate.variant_id}: oracle definition digest differs from authoring manifest"
            )
        candidate_artifacts.append(
            {
                "variant_id": candidate.variant_id,
                "cohort_kind": evidence["cohort_kind"],
                "primary_taxonomy_id": evidence["primary_taxonomy_id"],
                "metadata": metadata_by_id[candidate.variant_id],
                "patch_identity": {
                    "path": evidence["patch_path"],
                    "raw_sha256": patch_digest,
                    "operation_schema_version": evidence[
                        "patch_operation_schema_version"
                    ],
                    "operation_digest": evidence["patch_operation_digest"],
                    "changed_files": evidence["changed_files"],
                    "changed_functions": evidence["changed_functions"],
                },
                "oracle_identity": {
                    "oracle_ids": evidence["oracle_ids"],
                    "definition_schema_version": evidence[
                        "oracle_definition_schema_version"
                    ],
                    "comparison_semantics_version": COMPARISON_SEMANTICS_VERSION,
                    "definition_digest": observed_oracle_digest,
                    "definition_records": oracle_records,
                    "baseline_ground_truth_status": evidence[
                        "baseline_ground_truth_status"
                    ],
                    "candidate_ground_truth_status": evidence[
                        "candidate_ground_truth_status"
                    ],
                    "oracle_statuses": evidence["oracle_statuses"],
                },
            }
        )

    manifest = {
        "schema_version": ARTIFACT_MANIFEST_SCHEMA_VERSION,
        "dataset_identity": {
            "schema_version": DATASET_SCHEMA_VERSION,
            "benchmark_id": BENCHMARK_ID,
            "candidate_manifest_digest": candidate_digest,
        },
        "authoring_manifest_identity": {
            "schema_version": AUTHORING_MANIFEST_SCHEMA_VERSION,
            "status": AUTHORING_STATUS,
            "path": AUTHORING_MANIFEST_PATH,
            "canonical_digest": authoring_digest,
            "raw_sha256": _sha256_bytes(authoring_bytes),
            "python_generated_semantic_agreement": True,
            "python_generated_byte_agreement": True,
        },
        "trusted_reference_registry_identity": {
            "registry_version": TRUSTED_REFERENCE_REGISTRY_VERSION,
            "registry_digest": trusted_digest,
        },
        "coverage_gap_registry_identity": {
            "registry_version": COVERAGE_GAP_REGISTRY_VERSION,
            "registry_digest": coverage_digest,
        },
        "cohort_identity": {
            "variant_ids": candidate_payload["variant_ids"],
            "variant_count": len(candidate_payload["variant_ids"]),
            "buggy_count": len(candidate_payload["buggy_candidates"]),
            "clean_count": len(candidate_payload["clean_candidates"]),
            "buggy_bucket_ids": list(BUGGY_BUCKET_IDS),
            "clean_family_definitions": clean_family_definitions(),
        },
        "patch_operation_schema_version": PATCH_OPERATION_SCHEMA_VERSION,
        "oracle_definition_schema_version": ORACLE_DEFINITION_SCHEMA_VERSION,
        "comparison_semantics_version": COMPARISON_SEMANTICS_VERSION,
        "candidates": candidate_artifacts,
    }
    validate_portable_value(manifest, "artifact_manifest")
    return manifest


def artifact_manifest_digest(manifest: Any | None = None) -> str:
    value = (
        build_artifact_manifest()
        if manifest is None
        else validate_artifact_manifest(manifest)
    )
    return canonical_digest(value)


def validate_artifact_manifest(manifest: Any) -> dict[str, Any]:
    validate_portable_value(manifest, "artifact_manifest")
    expected = build_artifact_manifest()
    if canonical_json(manifest) != canonical_json(expected):
        raise FreezeRealizationError(
            "artifact_manifest: differs from accepted authoring, patch, metadata, or oracle input"
        )
    return expected


def serialized_artifact_manifest() -> str:
    return _serialized(build_artifact_manifest())


def _action_specs_payload() -> list[dict[str, Any]]:
    if tuple(item[0] for item in _ACTION_SPECS) != APPROVED_ACTION_IDS:
        raise FreezeRealizationError(
            "approved action stable order differs from P2a contract"
        )
    return [
        {
            "action_id": action_id,
            "cost": cost,
            "observation_type": observation_type,
            "strong_causes": list(strong_causes),
            "discovery_power": discovery_power,
            "location_power": location_power,
        }
        for (
            action_id,
            cost,
            observation_type,
            strong_causes,
            discovery_power,
            location_power,
        ) in _ACTION_SPECS
    ]


def _adapter_payload(artifact_digest: str) -> dict[str, Any]:
    return {
        "contract_version": ADAPTER_CONTRACT_VERSION,
        "semantics": {
            "source": "isolated canonical baseline plus one frozen patch",
            "module_namespace": "isolated generated module namespace",
            "provenance": "repository-relative frozen artifact identity",
            "variant_id_hidden_selector_allowed": False,
            "candidate_id_hidden_selector_allowed": False,
        },
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
        "candidate_contracts": {
            "patch_operation_schema_version": PATCH_OPERATION_SCHEMA_VERSION,
            "oracle_definition_schema_version": ORACLE_DEFINITION_SCHEMA_VERSION,
            "comparison_semantics_version": COMPARISON_SEMANTICS_VERSION,
            "artifact_manifest_digest": artifact_digest,
        },
    }


def _catalog_payload(artifact_manifest: dict[str, Any]) -> dict[str, Any]:
    cases = []
    for candidate in artifact_manifest["candidates"]:
        action_id = _CASE_ACTION_BY_CANDIDATE[candidate["variant_id"]]
        for oracle_record in candidate["oracle_identity"]["definition_records"]:
            cases.append(
                {
                    "candidate_id": candidate["variant_id"],
                    "oracle_id": oracle_record["oracle_id"],
                    "action_id": action_id,
                    "oracle_definition": oracle_record,
                }
            )
    return {
        "catalog_version": ACTION_TEST_CATALOG_VERSION,
        "application_scope": "same stable catalog for every frozen cohort candidate",
        "variant_specific_hidden_selection_allowed": False,
        "candidate_ids": artifact_manifest["cohort_identity"]["variant_ids"],
        "approved_action_specs": _action_specs_payload(),
        "case_order": "candidate stable order then oracle stable order",
        "case_count": len(cases),
        "cases": cases,
    }


def _policy_payload() -> dict[str, Any]:
    return {
        "identity_version": POLICY_IDENTITY_VERSION,
        "formal_policy_ids": list(FORMAL_POLICY_IDS),
        "excluded_policy_ids": list(EXCLUDED_POLICY_IDS),
        "accepted_runtime_digest": EXPECTED_LEGACY_RUNTIME_DIGEST,
        "implementation_executed_for_identity": False,
    }


def _settings_payload() -> dict[str, Any]:
    return {
        "identity_version": SETTINGS_IDENTITY_VERSION,
        "settings": {
            "budget_limit": 12,
            "max_steps": 6,
            "failure_cost": 14,
            "bug_presence_threshold": 0.75,
            "no_bug_probability_threshold": 0.8,
            "location_top1_threshold": 0.5,
            "cause_top1_threshold": 0.6,
            "min_expected_utility_per_cost": 0.03,
            "rng_seed": 0,
        },
        "stop_precedence": list(STOP_PRECEDENCE),
    }


def _metric_payload() -> dict[str, Any]:
    return {
        "identity_version": METRIC_IDENTITY_VERSION,
        "contract_scope": "outcome-free predeclared benchmark metric contract",
        "buggy_result_identities": list(BUGGY_RESULT_IDENTITIES),
        "clean_result_identities": list(CLEAN_RESULT_IDENTITIES),
        "primary_buggy_contract": {
            "primary_identity": "expansion_only_buggy",
            "descriptive_identity": "combined_versioned_buggy",
            "bucket_ids": list(BUGGY_BUCKET_IDS),
            "metrics": ["discovery_rate", "discovery_loss"],
            "discovery_loss_definition": "1 - discovered / eligible_support",
        },
        "reference_distribution": {
            "kind": "uniform_over_buckets_then_uniform_within_bucket",
            "bucket_weight": {"numerator": 1, "denominator": 5},
            "within_bucket_weight": "1 / eligible support in that bucket and cohort",
            "variant_pooled_primary_weighting_allowed": False,
            "worst_bucket_rule": "exact maximum over five unweighted bucket cells",
        },
        "secondary_buggy_metrics": {
            "metric_ids": [
                "cost_to_first_failure",
                "location_top3_loss",
                "cause_top1_loss",
                "fix_intent_top1_loss",
                "wrong_cause_high_confidence_rate",
                "mean_investigation_cost",
            ],
            "added_to_discovery_loss": False,
            "cost_to_first_failure_miss_penalty": 14,
        },
        "clean_separation": {
            "excluded_from_buggy_matrix": True,
            "excluded_from_restricted_pure_result": True,
            "excluded_from_reference_average": True,
            "metrics": [
                "false_positive_numerator_denominator_rate",
                "false_positive_ids",
                "mean_investigation_cost",
                "no_bug_stop_numerator_denominator_rate",
            ],
        },
        "lovo": {
            "interpretation": "descriptive influence analysis only",
            "policy_rerun_allowed": False,
            "buggy_target": "expansion_only_buggy variants only",
            "buggy_projections": [
                "expansion_only_buggy_minus_v",
                "combined_versioned_buggy_minus_v",
            ],
            "buggy_recompute_scope": [
                "affected bucket numerator denominator rate loss",
                "five-cell worst bucket and IDs",
                "uniform-bucket reference average",
                "average-to-worst gap",
                "restricted-pure security loss and policy ties",
                "min max exact delta and extreme expansion variant IDs",
            ],
            "buggy_non_recompute_scope": [
                "accepted legacy reference",
                "P2a replay identity",
                "secondary metric matrices",
                "clean metrics",
                "adapter catalog and policy outcomes",
            ],
            "clean_target": "expansion_only_clean variants only",
            "clean_projections": [
                "expansion_only_clean_minus_v",
                "combined_versioned_clean_minus_v",
            ],
            "clean_recompute_scope": [
                "false-positive numerator denominator rate",
                "mean investigation cost",
                "no-bug stop numerator denominator rate",
                "min max baseline delta and extreme expansion variant IDs",
            ],
            "clean_non_recompute_scope": [
                "accepted legacy reference",
                "P2a replay identity",
                "buggy metrics",
                "restricted-pure result",
                "secondary metric matrices",
            ],
        },
        "explicitly_excluded": [
            "confidence intervals",
            "bootstrap",
            "significance testing",
            "combined profile",
            "new policy",
            "second domain",
            "mixed strategy",
            "Nash",
            "regret",
        ],
        "calculated_during_freeze": False,
    }


def _serializer_payload() -> dict[str, Any]:
    return {
        "identity_version": SERIALIZER_IDENTITY_VERSION,
        "report_schema_version": REPORT_SCHEMA_VERSION,
        "analysis_phase": ANALYSIS_PHASE,
        "source_model": "future single validated summary",
        "formats": ["json", "markdown"],
        "encoding": "UTF-8",
        "newline_terminated": True,
        "stable_field_key_list_order": True,
        "finite_typed_values_only": True,
        "absolute_or_local_paths_allowed": False,
        "minimum_top_level_fields": list(_MINIMUM_REPORT_TOP_LEVEL_FIELDS),
        "buggy_result_identities": list(BUGGY_RESULT_IDENTITIES),
        "clean_result_identities": list(CLEAN_RESULT_IDENTITIES),
        "existing_cli_defaults_or_help_changed": False,
        "serializer_implemented_in_this_slice": False,
    }


def build_contract_payloads(
    artifact_manifest: Any | None = None,
) -> dict[str, dict[str, Any]]:
    """Return all six strict outcome-free payloads in official stable order."""

    artifact = (
        build_artifact_manifest()
        if artifact_manifest is None
        else validate_artifact_manifest(artifact_manifest)
    )
    return _contract_payloads_for_validated_artifact(artifact)


def _contract_payloads_for_validated_artifact(
    artifact: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    artifact_digest = canonical_digest(artifact)
    payloads = {
        "adapter": _adapter_payload(artifact_digest),
        "catalog": _catalog_payload(artifact),
        "policy": _policy_payload(),
        "settings": _settings_payload(),
        "metric": _metric_payload(),
        "serializer": _serializer_payload(),
    }
    validate_portable_value(payloads, "contract_payloads")
    return payloads


def validate_contract_payloads(
    payloads: Any,
    artifact_manifest: Any | None = None,
) -> dict[str, dict[str, Any]]:
    artifact = (
        build_artifact_manifest()
        if artifact_manifest is None
        else validate_artifact_manifest(artifact_manifest)
    )
    expected = _contract_payloads_for_validated_artifact(artifact)
    validate_portable_value(payloads, "contract_payloads")
    if canonical_json(payloads) != canonical_json(expected):
        raise FreezeRealizationError(
            "contract_payloads: differs from the predeclared outcome-free contract"
        )
    return expected


def contract_identities(payloads: Any) -> dict[str, dict[str, str]]:
    fields = {
        "adapter": ("contract_version", ADAPTER_CONTRACT_VERSION),
        "catalog": ("catalog_version", ACTION_TEST_CATALOG_VERSION),
        "policy": ("identity_version", POLICY_IDENTITY_VERSION),
        "settings": ("identity_version", SETTINGS_IDENTITY_VERSION),
        "metric": ("identity_version", METRIC_IDENTITY_VERSION),
        "serializer": ("identity_version", SERIALIZER_IDENTITY_VERSION),
    }
    value = _require_exact_fields(payloads, tuple(fields), "contract_payloads")
    identities = {}
    for name, (version_field, expected_version) in fields.items():
        payload = value[name]
        if type(payload) is not dict or payload.get(version_field) != expected_version:
            raise FreezeRealizationError(f"contract_payloads.{name}: wrong version")
        identities[name] = {
            version_field: expected_version,
            "digest": canonical_digest(payload),
        }
    return identities


def build_official_draft(
    freeze_timestamp: str,
    artifact_manifest: Any | None = None,
    payloads: Any | None = None,
) -> dict[str, Any]:
    artifact = (
        build_artifact_manifest()
        if artifact_manifest is None
        else validate_artifact_manifest(artifact_manifest)
    )
    contracts = (
        build_contract_payloads(artifact)
        if payloads is None
        else (validate_contract_payloads(deepcopy(payloads), artifact))
    )
    identities = contract_identities(contracts)
    candidate_payload = candidate_manifest_payload(
        BUGGY_CANDIDATE_METADATA, CLEAN_CANDIDATE_METADATA
    )
    draft = {
        "draft_schema_version": FREEZE_DRAFT_SCHEMA_VERSION,
        "dataset_identity": {
            "schema_version": DATASET_SCHEMA_VERSION,
            "benchmark_id": BENCHMARK_ID,
            "candidate_manifest_digest": canonical_digest(candidate_payload),
        },
        "artifact_identity": {
            "schema_version": ARTIFACT_MANIFEST_SCHEMA_VERSION,
            "artifact_manifest_digest": canonical_digest(artifact),
        },
        "adapter_identity": identities["adapter"],
        "catalog_identity": identities["catalog"],
        "policy_identity": identities["policy"],
        "settings_identity": identities["settings"],
        "metric_identity": identities["metric"],
        "serializer_identity": identities["serializer"],
        "coverage_registry_identity": {
            "registry_version": COVERAGE_GAP_REGISTRY_VERSION,
            "registry_digest": coverage_gap_registry_digest(),
        },
        "trusted_reference_registry_identity": {
            "registry_version": TRUSTED_REFERENCE_REGISTRY_VERSION,
            "registry_digest": trusted_reference_registry_digest(),
        },
        "freeze_timestamp": freeze_timestamp,
        "buggy_bucket_ids": list(BUGGY_BUCKET_IDS),
        "clean_family_definitions": clean_family_definitions(),
        "variant_ids": candidate_payload["variant_ids"],
        "buggy_candidates": candidate_payload["buggy_candidates"],
        "clean_candidates": candidate_payload["clean_candidates"],
    }
    validate_freeze_draft(draft)
    return draft


def realize_official_freeze(freeze_timestamp: str) -> dict[str, Any]:
    """Apply accepted draft validation and return a review-pending bundle."""

    artifact = build_artifact_manifest()
    artifact_digest = canonical_digest(artifact)
    payloads = build_contract_payloads(artifact)
    identities = contract_identities(payloads)
    draft = build_official_draft(freeze_timestamp, artifact, payloads)
    validation = validate_freeze_draft(draft)
    freeze_payload = {
        "freeze_timestamp": freeze_timestamp,
        "validated_official_draft": draft,
        "draft_validation": {
            "status": validation.status,
            "draft_digest": validation.draft_digest,
            "candidate_manifest_digest": validation.candidate_manifest_digest,
            "variant_count": validation.variant_count,
            "buggy_count": validation.buggy_count,
            "clean_count": validation.clean_count,
        },
        "candidate_authoring_manifest_identity": {
            "path": AUTHORING_MANIFEST_PATH,
            "schema_version": AUTHORING_MANIFEST_SCHEMA_VERSION,
            "status": AUTHORING_STATUS,
            "digest": EXPECTED_AUTHORING_MANIFEST_DIGEST,
        },
        "artifact_manifest_identity": {
            "path": ARTIFACT_MANIFEST_PATH,
            "schema_version": ARTIFACT_MANIFEST_SCHEMA_VERSION,
            "digest": artifact_digest,
        },
        "outcome_free_contracts": {
            name: {"identity": identities[name], "payload": payloads[name]}
            for name in payloads
        },
        "accepted_input_identities": {
            "candidate_manifest_digest": EXPECTED_CANDIDATE_MANIFEST_DIGEST,
            "trusted_reference_registry_digest": (
                EXPECTED_TRUSTED_REFERENCE_REGISTRY_DIGEST
            ),
            "coverage_gap_registry_digest": EXPECTED_COVERAGE_GAP_REGISTRY_DIGEST,
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
        },
        "provenance": {
            "candidate_policy_outcome_observed": False,
            "evaluation_authorized": False,
        },
        "independent_review_gate": {
            "gate_version": INDEPENDENT_REVIEW_GATE_VERSION,
            "required": True,
            "status": "pending",
        },
    }
    validate_portable_value(freeze_payload, "freeze_payload")
    return {
        "schema_version": OFFICIAL_FREEZE_BUNDLE_SCHEMA_VERSION,
        "status": OFFICIAL_FREEZE_STATUS,
        "freeze_payload": freeze_payload,
        "official_freeze_digest": canonical_digest(freeze_payload),
    }


def validate_official_freeze_bundle(bundle: Any) -> dict[str, Any]:
    value = _require_exact_fields(
        bundle,
        (
            "schema_version",
            "status",
            "freeze_payload",
            "official_freeze_digest",
        ),
        "official_freeze_bundle",
    )
    validate_portable_value(value, "official_freeze_bundle")
    if value["schema_version"] != OFFICIAL_FREEZE_BUNDLE_SCHEMA_VERSION:
        raise FreezeRealizationError(
            "official_freeze_bundle.schema_version: wrong version"
        )
    if value["status"] != OFFICIAL_FREEZE_STATUS:
        raise FreezeRealizationError("official_freeze_bundle.status: wrong status")
    freeze_payload = value["freeze_payload"]
    if (
        type(freeze_payload) is not dict
        or type(freeze_payload.get("freeze_timestamp")) is not str
    ):
        raise FreezeRealizationError(
            "official_freeze_bundle.freeze_payload.freeze_timestamp: missing caller value"
        )
    observed_digest = canonical_digest(freeze_payload)
    if value["official_freeze_digest"] != observed_digest:
        raise FreezeRealizationError(
            "official_freeze_bundle.official_freeze_digest: payload digest mismatch"
        )
    expected = realize_official_freeze(freeze_payload["freeze_timestamp"])
    if canonical_json(value) != canonical_json(expected):
        raise FreezeRealizationError(
            "official_freeze_bundle: differs from validated official freeze input"
        )
    return expected


def serialized_official_freeze_bundle(freeze_timestamp: str) -> str:
    return _serialized(realize_official_freeze(freeze_timestamp))


def load_tracked_artifact_manifest() -> dict[str, Any]:
    path = repository_path(ARTIFACT_MANIFEST_PATH)
    value = json.loads(path.read_text(encoding="utf-8"))
    validated = validate_artifact_manifest(value)
    if path.read_bytes() != serialized_artifact_manifest().encode("utf-8"):
        raise FreezeRealizationError("tracked artifact manifest differs byte-for-byte")
    return validated


def load_tracked_official_freeze_bundle() -> dict[str, Any]:
    path = repository_path(OFFICIAL_FREEZE_BUNDLE_PATH)
    value = json.loads(path.read_text(encoding="utf-8"))
    validated = validate_official_freeze_bundle(value)
    expected_bytes = serialized_official_freeze_bundle(
        value["freeze_payload"]["freeze_timestamp"]
    ).encode("utf-8")
    if path.read_bytes() != expected_bytes:
        raise FreezeRealizationError(
            "tracked official freeze bundle differs byte-for-byte"
        )
    return validated
