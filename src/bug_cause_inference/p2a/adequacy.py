"""Outcome-free adequacy contracts for the P2a pre-authoring gate.

This module intentionally contains no policy runner, evaluator, report builder,
candidate artifact, or realized freeze. Its registries are P2a-local reviewed
contracts derived from legacy metadata, patch identity, and oracle semantics.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from pathlib import PurePosixPath
from typing import Any


DATASET_SCHEMA_VERSION = "p2a_same_domain_dataset.v1"
BENCHMARK_ID = "p2a_checkout_pricing_same_domain_expansion_v1"
BUGGY_VARIANT_NAMESPACE = "P2A-BUG-*"
CLEAN_VARIANT_NAMESPACE = "P2A-CLEAN-*"
ADAPTER_CONTRACT_VERSION = "p2a_patch_grounded_adapter.v1"
ACTION_TEST_CATALOG_VERSION = "p2a_action_test_catalog.v1"
REPORT_SCHEMA_VERSION = "p2a_benchmark_evidence_expansion_report.v1"
ANALYSIS_PHASE = "p2a_benchmark_evidence_expansion_report"
DOMAIN_ID = "checkout_pricing"
BUGGY_COHORT_ID = "buggy_expansion"
CLEAN_COHORT_ID = "clean_stress_expansion"
CLEAN_PRIMARY_BUCKET_ID = "clean_false_positive"
COVERAGE_GAP_REGISTRY_VERSION = "p2a_coverage_gap_registry.v1"
TRUSTED_REFERENCE_REGISTRY_VERSION = "p2a_trusted_reference_registry.v1"

BUGGY_BUCKET_IDS = (
    "boundary_precision",
    "missing_optional_input",
    "config_normalization",
    "state_sequence",
    "spec_semantics",
)
CLEAN_STRESS_FAMILY_IDS = (
    "boundary_adjacent_valid_behavior",
    "optional_input_valid_absence",
    "config_equivalent_normalization",
    "valid_state_sequence",
    "nonintuitive_spec_conformance",
)
CLEAN_FAMILY_TO_ADJACENT_BUCKET = {
    "boundary_adjacent_valid_behavior": "boundary_precision",
    "optional_input_valid_absence": "missing_optional_input",
    "config_equivalent_normalization": "config_normalization",
    "valid_state_sequence": "state_sequence",
    "nonintuitive_spec_conformance": "spec_semantics",
}

LEGACY_VARIANT_IDS = tuple(
    [f"P1B-BUG-{index:03d}" for index in range(1, 21)]
    + [f"P1B-CLEAN-{index:03d}" for index in range(21, 26)]
)

CORE_FINGERPRINT_FIELD_IDS = (
    "spec_rule",
    "causal_mechanism",
    "target_function_set",
    "trigger_shape",
    "observable_behavior",
    "oracle_outcome_vector",
    "normalized_patch_operation",
    "interaction_depth",
)
ORACLE_OUTCOME_FIELD_IDS = ("oracle_id", "expected_outcome")
CORE_MATERIAL_DIMENSION_IDS = (
    "spec/mechanism",
    "target_function_set",
    "observable/oracle_outcome",
    "interaction_depth",
)
MATERIAL_DIMENSION_IDS = CORE_MATERIAL_DIMENSION_IDS + (
    "trigger_shape",
    "normalized_patch_operation",
    "artifact_provenance",
    "stress_mechanism",
    "identifier_or_literal",
    "sku_region_coupon",
    "prose",
    "bucket_or_family_label",
    "quota_padding",
)

BUGGY_METADATA_FIELD_IDS = (
    "variant_id",
    "cohort",
    "domain",
    "spec_area",
    "primary_bucket",
    "is_buggy",
    "cause_category",
    "target_module",
    "target_functions",
    "trigger_shape",
    "expected_behavior",
    "actual_behavior",
    "oracle_ids",
    "action_test_catalog_ids",
    "action_mapping",
    "observable_signature",
    "patch_semantic_fingerprint",
    "changed_files",
    "changed_functions",
    "interaction_depth",
    "fix_intent_category",
    "difficulty",
    "nearest_legacy_or_admitted_variant_id",
    "material_difference_dimensions",
    "diversity_rationale",
    "core_fingerprint",
    "nearest_reference_core_fingerprint",
    "nearest_reference_core_fingerprint_digest",
)
CLEAN_METADATA_FIELD_IDS = (
    "variant_id",
    "cohort",
    "domain",
    "spec_area",
    "primary_bucket",
    "is_buggy",
    "clean_stress_family_id",
    "clean_stress_family_order",
    "adjacent_buggy_bucket_id",
    "stress_mechanism",
    "confusing_signal",
    "expected_clean_behavior",
    "no_bug_oracle_ids",
    "recommended_no_bug_evidence",
    "benign_diff_rationale",
    "patch_semantic_fingerprint",
    "changed_files",
    "changed_functions",
    "interaction_depth",
    "nearest_legacy_or_admitted_clean_variant_id",
    "material_difference_dimensions",
    "diversity_rationale",
    "core_fingerprint",
    "nearest_reference_core_fingerprint",
    "nearest_reference_core_fingerprint_digest",
)
CLEAN_FORBIDDEN_BUG_GROUND_TRUTH_FIELDS = frozenset(
    {
        "cause",
        "cause_category",
        "buggy_cause",
        "fault_location",
        "fault_target",
        "target_module",
        "target_function",
        "target_functions_ground_truth",
        "faulty_behavior",
        "actual_behavior",
        "fix_intent",
        "fix_intent_category",
        "fix_intent_ground_truth",
    }
)
POLICY_OUTCOME_FIELD_IDS = frozenset(
    {
        "policy_id",
        "policy_trace",
        "posterior",
        "selected_action",
        "matrix_cell",
        "worst_bucket",
        "clean_false_positive_outcome",
        "false_positive_result",
        "investigation_cost",
        "policy_loss",
        "p1c_outcome",
        "p1d_outcome",
    }
)
FORMAL_POLICY_ID_TOKENS = (
    "fixed_checklist",
    "test_first",
    "coverage_first",
    "recent_diff_first",
    "cause_only_p1a_style",
    "expected_utility_per_cost",
    "random_action",
    "state_sequence_guard",
)
APPROVED_ACTION_IDS = (
    "run_smoke_tests",
    "run_boundary_tests",
    "run_null_missing_tests",
    "run_config_matrix_tests",
    "run_state_sequence_tests",
    "run_property_search",
    "inspect_traceback",
    "inspect_coverage_spectrum",
    "inspect_recent_diff",
    "inspect_spec_clause",
)

_BUG_ID_RE = re.compile(r"^P2A-BUG-[A-Z0-9][A-Z0-9-]*$")
_CLEAN_ID_RE = re.compile(r"^P2A-CLEAN-[A-Z0-9][A-Z0-9-]*$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ABSOLUTE_PATH_RE = re.compile(
    r"(?:[A-Za-z]:[\\/]|\\\\[^\\/\s]+[\\/][^\\/\s]+|\bfile://[^\s]+|(?<![A-Za-z0-9_/\\])/(?!/)[^\s]+)",
    re.IGNORECASE,
)
_FORBIDDEN_LOCAL_PATH_PARTS = frozenset(
    {".cache", ".pytest_cache", "__pycache__", "tmp", "temp", "generated", "generated_tree"}
)
_REGISTRY_OUTCOME_TERMS = (
    "policy_id",
    "policy id",
    "policy_trace",
    "policy trace",
    "posterior",
    "selected_action",
    "selected action",
    "matrix_cell",
    "matrix cell",
    "worst_bucket",
    "worst bucket",
    "investigation_cost",
    "investigation cost",
    "policy_loss",
    "policy loss",
    "p1c_outcome",
    "p1d_outcome",
    "p1c",
    "p1d",
)
_NARRATIVE_MATRIX_OUTCOME_TERMS = (
    "policy outcome matrix",
    "policy_outcome_matrix",
    "outcome matrix",
    "outcome_matrix",
    "matrix cell",
    "matrix_cell",
)
class ReasonCode(str, Enum):
    MISSING_FIELD = "missing_field"
    UNKNOWN_FIELD = "unknown_field"
    POLICY_OUTCOME_FIELD_FORBIDDEN = "policy_outcome_field_forbidden"
    FORMAL_POLICY_ID_FORBIDDEN = "formal_policy_id_forbidden"
    CLEAN_FALSE_POSITIVE_OUTCOME_FORBIDDEN = "clean_false_positive_outcome_forbidden"
    WRONG_TYPE = "wrong_type"
    EMPTY_VALUE = "empty_value"
    WRONG_IDENTITY = "wrong_identity"
    WRONG_VERSION = "wrong_version"
    MISSING_DIGEST = "missing_digest"
    WRONG_DIGEST = "wrong_digest"
    UNKNOWN_BUCKET = "unknown_bucket"
    MISSING_BUCKET = "missing_bucket"
    REORDERED_BUCKET = "reordered_bucket"
    UNKNOWN_CLEAN_FAMILY = "unknown_clean_family"
    MISSING_CLEAN_FAMILY = "missing_clean_family"
    REORDERED_CLEAN_FAMILY = "reordered_clean_family"
    WRONG_ADJACENT_BUCKET = "wrong_adjacent_bucket"
    BUGGY_BUCKET_COUNT = "buggy_bucket_count"
    BUGGY_TOTAL_COUNT = "buggy_total_count"
    CLEAN_FAMILY_COUNT = "clean_family_count"
    CLEAN_TOTAL_COUNT = "clean_total_count"
    NAMESPACE_COLLISION = "namespace_collision"
    NAMESPACE_MISMATCH = "namespace_mismatch"
    DUPLICATE_VARIANT_ID = "duplicate_variant_id"
    REORDERED_VARIANT_ID = "reordered_variant_id"
    COHORT_MISMATCH = "cohort_mismatch"
    DOMAIN_MISMATCH = "domain_mismatch"
    PRIMARY_BUCKET_MISMATCH = "primary_bucket_mismatch"
    BUGGY_FLAG_MISMATCH = "buggy_flag_mismatch"
    CLEAN_BUG_GROUND_TRUTH_FORBIDDEN = "clean_bug_ground_truth_forbidden"
    UNKNOWN_REFERENCE = "unknown_reference"
    WRONG_REFERENCE_COHORT = "wrong_reference_cohort"
    SELF_REFERENCE = "self_reference"
    FORWARD_REFERENCE = "forward_reference"
    REFERENCE_FINGERPRINT_MISMATCH = "reference_fingerprint_mismatch"
    REFERENCE_DIGEST_MISMATCH = "reference_digest_mismatch"
    NEAREST_REFERENCE_MISMATCH = "nearest_reference_mismatch"
    UNKNOWN_ACTION_ID = "unknown_action_id"
    EXACT_CORE_FINGERPRINT_DUPLICATE = "exact_core_fingerprint_duplicate"
    INSUFFICIENT_MATERIAL_DIFFERENCE = "insufficient_material_difference"
    MISSING_CORE_MATERIAL_DIFFERENCE = "missing_core_material_difference"
    RENAME_OR_LITERAL_ONLY = "rename_or_literal_only"
    SAME_NORMALIZED_PATCH = "same_normalized_patch"
    SAME_TARGET_TRIGGER_ORACLE = "same_target_trigger_oracle"
    FAMILY_LABEL_ONLY_DUPLICATE = "family_label_only_duplicate"
    QUOTA_PADDING = "quota_padding"
    ABSOLUTE_PATH_FORBIDDEN = "absolute_path_forbidden"
    LOCAL_TEMP_PATH_FORBIDDEN = "local_temp_path_forbidden"
    NON_FINITE_NUMBER = "non_finite_number"
    UNSUPPORTED_CANONICAL_TYPE = "unsupported_canonical_type"
    TRUSTED_REFERENCE_REGISTRY_MISMATCH = "trusted_reference_registry_mismatch"
    REGISTRY_IDENTITY_MISMATCH = "registry_identity_mismatch"
    REGISTRY_LEGACY_SUPPORT_MISMATCH = "registry_legacy_support_mismatch"
    REGISTRY_SOURCE_BASIS_INVALID = "registry_source_basis_invalid"
    REGISTRY_OUTCOME_LEAKAGE = "registry_outcome_leakage"


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    path: str
    message: str


class AdequacyValidationError(ValueError):
    """Fail-closed validation error carrying a stable reason code."""

    def __init__(self, issue: ValidationIssue) -> None:
        super().__init__(f"{issue.code} at {issue.path}: {issue.message}")
        self.issue = issue


@dataclass(frozen=True)
class TrustedReference:
    variant_id: str
    cohort_kind: str
    stable_order: int
    core_fingerprint: dict[str, Any]
    core_fingerprint_digest: str


@dataclass(frozen=True)
class _ValidatedCandidateReference:
    variant_id: str
    cohort_kind: str
    stable_order: int
    core_fingerprint: dict[str, Any]
    core_fingerprint_digest: str


@dataclass(frozen=True)
class CoverageSourceIdentity:
    kind: str
    repository_path: str
    anchor: str
    legacy_support_ids: tuple[str, ...]


@dataclass(frozen=True)
class CoverageGapEntry:
    gap_id: str
    cohort_kind: str
    primary_bucket_or_clean_family_id: str
    stable_order: int
    legacy_support_ids: tuple[str, ...]
    legacy_coverage_summary: str
    gap_taxonomy_dimensions: tuple[str, ...]
    gap_statement: str
    candidate_need_statement: str
    source_basis: tuple[CoverageSourceIdentity, ...]
    explicit_non_outcome_basis: str


def _fail(code: ReasonCode, path: str, message: str) -> None:
    raise AdequacyValidationError(ValidationIssue(code.value, path, message))


def _require_exact_fields(value: Any, fields: tuple[str, ...], path: str) -> Mapping[str, Any]:
    if type(value) is not dict:
        _fail(ReasonCode.WRONG_TYPE, path, "expected an object")
    keys = set(value)
    if keys & POLICY_OUTCOME_FIELD_IDS:
        _fail(
            ReasonCode.POLICY_OUTCOME_FIELD_FORBIDDEN,
            path,
            "policy-result material is outside the pre-authoring schema",
        )
    missing = [field for field in fields if field not in value]
    if missing:
        _fail(ReasonCode.MISSING_FIELD, f"{path}.{missing[0]}", "required field is missing")
    unknown = [key for key in value if key not in fields]
    if unknown:
        _fail(ReasonCode.UNKNOWN_FIELD, f"{path}.{unknown[0]}", "field is not allowlisted")
    return value


def _require_nonempty_string(value: Any, path: str) -> str:
    if type(value) is not str:
        _fail(ReasonCode.WRONG_TYPE, path, "expected a string")
    if not value.strip():
        _fail(ReasonCode.EMPTY_VALUE, path, "value must not be empty")
    return value


def _require_string_list(
    value: Any,
    path: str,
    *,
    allow_empty: bool = False,
    stable_order: bool = False,
) -> list[str]:
    if type(value) is not list:
        _fail(ReasonCode.WRONG_TYPE, path, "expected a list")
    if not value and not allow_empty:
        _fail(ReasonCode.EMPTY_VALUE, path, "list must not be empty")
    for index, item in enumerate(value):
        _require_nonempty_string(item, f"{path}[{index}]")
    if len(set(value)) != len(value):
        _fail(ReasonCode.WRONG_IDENTITY, path, "list entries must be unique")
    if stable_order and value != sorted(value):
        _fail(ReasonCode.WRONG_IDENTITY, path, "list entries must use Unicode code-point order")
    return list(value)


def _is_local_temporary_path(value: str) -> bool:
    if "/" not in value and "\\" not in value:
        return False
    parts = {part.lower() for part in re.split(r"[\\/]", value) if part}
    return bool(parts & _FORBIDDEN_LOCAL_PATH_PARTS)


def validate_portable_value(value: Any, path: str = "$") -> None:
    """Reject local paths, non-finite numbers, and non-JSON-like values recursively."""

    if value is None or type(value) in {bool, int}:
        return
    if type(value) is float:
        if not math.isfinite(value):
            _fail(ReasonCode.NON_FINITE_NUMBER, path, "NaN and Infinity are forbidden")
        return
    if type(value) is str:
        if _ABSOLUTE_PATH_RE.search(value):
            _fail(ReasonCode.ABSOLUTE_PATH_FORBIDDEN, path, "absolute local paths are forbidden")
        if _is_local_temporary_path(value):
            _fail(ReasonCode.LOCAL_TEMP_PATH_FORBIDDEN, path, "cache/temp/generated-tree paths are forbidden")
        return
    if type(value) in {list, tuple}:
        for index, child in enumerate(value):
            validate_portable_value(child, f"{path}[{index}]")
        return
    if type(value) is dict:
        for key, child in value.items():
            if type(key) is not str:
                _fail(ReasonCode.WRONG_TYPE, f"{path}.<key>", "object keys must be strings")
            validate_portable_value(key, f"{path}.<key>")
            validate_portable_value(child, f"{path}.{key}")
        return
    _fail(ReasonCode.UNSUPPORTED_CANONICAL_TYPE, path, f"unsupported value type {type(value).__name__}")


def _normalized_token_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")


def validate_outcome_free_value(
    value: Any,
    path: str,
    *,
    allow_clean_primary_bucket: bool = False,
    field_name: str | None = None,
) -> None:
    """Reject policy/result material without treating identifier tokens as prose."""

    if type(value) is str:
        lowered = value.casefold()
        normalized = _normalized_token_text(value)
        padded = f"_{normalized}_"
        for policy_id in FORMAL_POLICY_ID_TOKENS:
            if f"_{policy_id}_" in padded:
                _fail(
                    ReasonCode.FORMAL_POLICY_ID_FORBIDDEN,
                    path,
                    "formal or pre-freeze policy identity is forbidden in authoring data",
                )
        if "clean_false_positive" in normalized:
            allowed = allow_clean_primary_bucket and normalized == CLEAN_PRIMARY_BUCKET_ID
            if not allowed:
                _fail(
                    ReasonCode.CLEAN_FALSE_POSITIVE_OUTCOME_FORBIDDEN,
                    path,
                    "clean false-positive material is allowed only as the exact clean primary bucket taxonomy value",
                )
        if any(term in lowered for term in _REGISTRY_OUTCOME_TERMS):
            _fail(
                ReasonCode.POLICY_OUTCOME_FIELD_FORBIDDEN,
                path,
                "policy-result material is forbidden before candidate freeze",
            )
        if any(term in lowered for term in _NARRATIVE_MATRIX_OUTCOME_TERMS):
            _fail(
                ReasonCode.POLICY_OUTCOME_FIELD_FORBIDDEN,
                path,
                "policy-result matrix material is forbidden before candidate freeze",
            )
        return
    if type(value) in {list, tuple}:
        for index, child in enumerate(value):
            validate_outcome_free_value(
                child,
                f"{path}[{index}]",
                field_name=field_name,
            )
        return
    if type(value) is dict:
        for key, child in value.items():
            validate_outcome_free_value(key, f"{path}.<key>")
            child_allowance = allow_clean_primary_bucket and key == "primary_bucket"
            validate_outcome_free_value(
                child,
                f"{path}.{key}",
                allow_clean_primary_bucket=child_allowance,
                field_name=key,
            )


def _typed_node(value: Any) -> dict[str, Any]:
    validate_portable_value(value)
    if value is None:
        return {"type": "none", "value": None}
    if type(value) is bool:
        return {"type": "bool", "value": value}
    if type(value) is int:
        return {"type": "int", "value": str(value)}
    if type(value) is float:
        return {"type": "float", "value": repr(value)}
    if type(value) is str:
        return {"type": "str", "value": value}
    if type(value) is list:
        return {"type": "list", "items": [_typed_node(item) for item in value]}
    if type(value) is tuple:
        return {"type": "tuple", "items": [_typed_node(item) for item in value]}
    if type(value) is dict:
        return {
            "type": "dict",
            "items": [[_typed_node(key), _typed_node(value[key])] for key in sorted(value)],
        }
    raise AssertionError("validate_portable_value accepted an unsupported type")


def canonical_json(value: Any) -> str:
    return json.dumps(_typed_node(value), ensure_ascii=False, separators=(",", ":"))


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def validate_sha256(value: Any, path: str) -> str:
    if value is None or value == "":
        _fail(ReasonCode.MISSING_DIGEST, path, "SHA-256 digest is required")
    if type(value) is not str or _SHA256_RE.fullmatch(value) is None:
        _fail(ReasonCode.WRONG_DIGEST, path, "expected lowercase 64-character SHA-256")
    return value


def _canonical_oracle_vector(value: Any, path: str) -> list[dict[str, str]]:
    if type(value) is not list:
        _fail(ReasonCode.WRONG_TYPE, path, "oracle vector must be a list of records")
    if not value:
        _fail(ReasonCode.EMPTY_VALUE, path, "oracle vector must not be empty")
    records: list[dict[str, str]] = []
    for index, item in enumerate(value):
        record = _require_exact_fields(item, ORACLE_OUTCOME_FIELD_IDS, f"{path}[{index}]")
        oracle_id = _require_nonempty_string(record["oracle_id"], f"{path}[{index}].oracle_id")
        outcome = _require_nonempty_string(
            record["expected_outcome"],
            f"{path}[{index}].expected_outcome",
        )
        if outcome not in {"pass", "fail"}:
            _fail(ReasonCode.WRONG_IDENTITY, f"{path}[{index}].expected_outcome", "expected pass or fail")
        records.append({"oracle_id": oracle_id, "expected_outcome": outcome})
    oracle_ids = [record["oracle_id"] for record in records]
    if len(set(oracle_ids)) != len(oracle_ids):
        _fail(ReasonCode.WRONG_IDENTITY, path, "oracle IDs must be unique")
    if oracle_ids != sorted(oracle_ids):
        _fail(ReasonCode.WRONG_IDENTITY, path, "oracle records must use oracle-ID order")
    return records


def _canonical_fingerprint(value: Any, path: str) -> dict[str, Any]:
    fingerprint = _require_exact_fields(value, CORE_FINGERPRINT_FIELD_IDS, path)
    for field in (
        "spec_rule",
        "causal_mechanism",
        "trigger_shape",
        "observable_behavior",
        "normalized_patch_operation",
        "interaction_depth",
    ):
        _require_nonempty_string(fingerprint[field], f"{path}.{field}")
    targets = _require_string_list(
        fingerprint["target_function_set"],
        f"{path}.target_function_set",
        stable_order=True,
    )
    oracle_vector = _canonical_oracle_vector(
        fingerprint["oracle_outcome_vector"],
        f"{path}.oracle_outcome_vector",
    )
    return {
        "spec_rule": fingerprint["spec_rule"],
        "causal_mechanism": fingerprint["causal_mechanism"],
        "target_function_set": targets,
        "trigger_shape": fingerprint["trigger_shape"],
        "observable_behavior": fingerprint["observable_behavior"],
        "oracle_outcome_vector": oracle_vector,
        "normalized_patch_operation": fingerprint["normalized_patch_operation"],
        "interaction_depth": fingerprint["interaction_depth"],
    }


def _legacy_fingerprint(
    spec_rule: str,
    mechanism: str,
    target: str,
    trigger: str,
    observable: str,
    oracle_id: str,
    outcome: str,
    patch_operation: str,
    interaction_depth: str,
) -> dict[str, Any]:
    return {
        "spec_rule": spec_rule,
        "causal_mechanism": mechanism,
        "target_function_set": [target],
        "trigger_shape": trigger,
        "observable_behavior": observable,
        "oracle_outcome_vector": [{"oracle_id": oracle_id, "expected_outcome": outcome}],
        "normalized_patch_operation": patch_operation,
        "interaction_depth": interaction_depth,
    }


# Reviewed P1b metadata/patch/oracle semantics in exact legacy order.
_TRUSTED_REFERENCE_ROWS = (
    ("P1B-BUG-001", "buggy", "inclusive free-shipping threshold", "exclusive comparison", "shipping.free_shipping_eligible", "subtotal equals 10000", "standard fee instead of zero", "boundary.free_shipping_exact_threshold", "fail", "replace >= with >", "single_function"),
    ("P1B-BUG-002", "buggy", "inclusive coupon minimum", "exclusive comparison", "discounts.coupon_is_eligible", "subtotal equals coupon minimum", "coupon rejected", "boundary.coupon_exact_minimum", "fail", "replace >= with > for coupon minimum", "single_function"),
    ("P1B-BUG-003", "buggy", "quantity 99 is valid", "upper-bound rejection", "cart.add_item", "quantity equals 99", "valid item rejected", "boundary.quantity_upper_boundary", "fail", "replace > with >= for quantity", "single_function"),
    ("P1B-BUG-004", "buggy", "half-up monetary rounding", "integer truncation", "cart.calculate_tax", "tax has .5 fraction", "one-yen tax deficit", "boundary.tax_half_up_rounding", "fail", "replace half-up rounding with truncation", "single_function"),
    ("P1B-BUG-005", "buggy", "missing coupon is no-op", "unguarded string normalization", "discounts.apply_coupon", "coupon is None", "AttributeError", "null_missing.coupon_none_noop", "fail", "remove missing-coupon guard", "single_function"),
    ("P1B-BUG-006", "buggy", "missing region uses domestic default", "direct missing-key lookup", "shipping.resolve_region_rate", "region key absent", "KeyError", "null_missing.missing_region_default", "fail", "replace default region lookup with required key", "single_function"),
    ("P1B-BUG-007", "buggy", "missing items means empty cart", "iteration without normalization", "cart.cart_subtotal", "items is None", "TypeError", "null_missing.none_cart_subtotal", "fail", "remove absent-items normalization", "single_function"),
    ("P1B-BUG-008", "buggy", "missing reserved count means zero", "required reservation key", "inventory.reserve_stock", "reserved key absent", "KeyError", "null_missing.missing_reserved_defaults_zero", "fail", "replace default reservation lookup with required key", "single_function"),
    ("P1B-BUG-009", "buggy", "JP tax fallback is 0.10", "stale scalar default", "config.get_tax_rate", "JP tax key absent", "0.08 fallback", "config.missing_jp_tax_default", "fail", "replace JP default 0.10 with 0.08", "single_function"),
    ("P1B-BUG-010", "buggy", "missing stacking flag is false", "unsafe boolean default", "config.get_feature_flag", "flag absent", "discounts stack", "config.missing_feature_flag_no_stacking", "fail", "replace false flag default with true", "single_function"),
    ("P1B-BUG-011", "buggy", "region aliases normalize", "alias normalization removed", "shipping.resolve_region_rate", "okinawa alias", "domestic rate", "config.region_alias_rate", "fail", "remove region alias canonicalization", "single_function"),
    ("P1B-BUG-012", "buggy", "threshold override is numeric", "string override retained", "config.load_config", "string threshold override", "TypeError on comparison", "config.free_shipping_threshold_override", "fail", "remove numeric parsing for threshold", "single_function"),
    ("P1B-BUG-013", "buggy", "cancel reverses reservation", "incomplete reversal transition", "inventory.cancel_reservation", "reserve then cancel", "stock remains reduced", "state.reserve_then_cancel", "fail", "remove cancellation stock restoration", "multi_step"),
    ("P1B-BUG-014", "buggy", "coupon application is idempotent", "duplicate mutable state", "discounts.apply_coupon", "apply coupon twice", "discount applies twice", "state.double_coupon_idempotency", "fail", "allow duplicate coupon state entries", "multi_step"),
    ("P1B-BUG-015", "buggy", "cart removal releases reservation", "cross-helper state desynchronization", "inventory.sync_after_cart_update", "reserve remove then reserve", "stale reservation blocks stock", "state.removed_item_releases_reservation", "fail", "remove reservation release during sync", "cross_function"),
    ("P1B-BUG-016", "buggy", "quote reflects current cart", "stale cached items", "cart.checkout_quote", "mutate cart after quote preparation", "stale shipping or discount", "state.quote_after_cart_mutation", "fail", "use stale quote items for shipping", "cross_function"),
    ("P1B-BUG-017", "buggy", "discount precedes tax", "calculation order reversed", "cart.calculate_total", "taxable discounted order", "tax computed before discount", "spec.discount_before_tax", "fail", "move discount after tax", "cross_function"),
    ("P1B-BUG-018", "buggy", "BOGO frees cheapest item", "selection extremum reversed", "discounts.apply_bogo_discount", "two eligible prices", "most expensive item freed", "spec.bogo_cheapest_rule", "fail", "replace minimum selection with maximum", "single_function"),
    ("P1B-BUG-019", "buggy", "digital-only cart has no shipping", "exception rule removed", "shipping.calculate_shipping", "digital-only items with region", "shipping fee charged", "spec.digital_only_shipping", "fail", "remove digital-only exemption", "cross_function"),
    ("P1B-BUG-020", "buggy", "preorder permits zero-stock reservation", "exception rule removed", "inventory.reserve_stock", "preorder with zero stock", "reservation rejected", "spec.preorder_reservation", "fail", "remove preorder allowance", "single_function"),
    ("P1B-CLEAN-021", "clean_stress", "inclusive threshold remains valid", "benign threshold variable extraction", "shipping.free_shipping_eligible", "below at and above threshold", "specified shipping fees", "property.free_shipping_boundary_vector", "pass", "extract threshold eligibility variable", "single_function"),
    ("P1B-CLEAN-022", "clean_stress", "missing coupon remains no-op", "benign normalization rename", "discounts.apply_coupon", "None empty and absent coupon", "zero discount without exception", "null_missing.coupon_none_noop", "pass", "rename normalized coupon local", "single_function"),
    ("P1B-CLEAN-023", "clean_stress", "missing flag equals false", "benign default lookup simplification", "config.get_feature_flag", "absent explicit false and true", "documented flag behavior", "config.missing_feature_flag_no_stacking", "pass", "simplify conservative flag lookup", "single_function"),
    ("P1B-CLEAN-024", "clean_stress", "reserve cancel reserve preserves invariant", "benign cancellation variable extraction", "inventory.cancel_reservation", "reserve cancel reserve", "inventory invariant preserved", "state.reserve_then_cancel", "pass", "extract cancelled quantity local", "multi_step"),
    ("P1B-CLEAN-025", "clean_stress", "discount-before-tax with half-up total", "benign tax variable extraction", "cart.calculate_total", "representative discounted carts", "golden totals preserved", "spec.discount_before_tax", "pass", "extract final tax addition local", "cross_function"),
)


def _build_trusted_reference_registry() -> tuple[TrustedReference, ...]:
    references: list[TrustedReference] = []
    for order, row in enumerate(_TRUSTED_REFERENCE_ROWS, start=1):
        fingerprint = _legacy_fingerprint(*row[2:])
        references.append(
            TrustedReference(
                variant_id=row[0],
                cohort_kind=row[1],
                stable_order=order,
                core_fingerprint=fingerprint,
                core_fingerprint_digest=canonical_digest(fingerprint),
            )
        )
    return tuple(references)


TRUSTED_REFERENCE_REGISTRY = _build_trusted_reference_registry()
_TRUSTED_REFERENCE_FIELD_IDS = tuple(TrustedReference.__dataclass_fields__)


def _trusted_reference_from_value(value: Any, index: int) -> TrustedReference:
    if isinstance(value, TrustedReference):
        return value
    mapping = _require_exact_fields(value, _TRUSTED_REFERENCE_FIELD_IDS, f"trusted_references[{index}]")
    return TrustedReference(
        variant_id=mapping["variant_id"],
        cohort_kind=mapping["cohort_kind"],
        stable_order=mapping["stable_order"],
        core_fingerprint=mapping["core_fingerprint"],
        core_fingerprint_digest=mapping["core_fingerprint_digest"],
    )


def validate_trusted_reference_registry(
    registry: Sequence[Any] = TRUSTED_REFERENCE_REGISTRY,
) -> tuple[TrustedReference, ...]:
    if type(registry) not in {list, tuple}:
        _fail(ReasonCode.WRONG_TYPE, "trusted_references", "expected a list or tuple")
    references = tuple(_trusted_reference_from_value(value, index) for index, value in enumerate(registry))
    expected = _build_trusted_reference_registry()
    if len(references) != len(expected):
        _fail(ReasonCode.TRUSTED_REFERENCE_REGISTRY_MISMATCH, "trusted_references", "expected exact legacy 25 references")
    normalized: list[TrustedReference] = []
    for index, (reference, expected_reference) in enumerate(zip(references, expected, strict=True)):
        path = f"trusted_references[{index}]"
        variant_id = _require_nonempty_string(reference.variant_id, f"{path}.variant_id")
        cohort_kind = _require_nonempty_string(reference.cohort_kind, f"{path}.cohort_kind")
        if type(reference.stable_order) is not int:
            _fail(ReasonCode.WRONG_TYPE, f"{path}.stable_order", "expected an int")
        fingerprint = _canonical_fingerprint(reference.core_fingerprint, f"{path}.core_fingerprint")
        validate_outcome_free_value(fingerprint, f"{path}.core_fingerprint")
        validate_sha256(reference.core_fingerprint_digest, f"{path}.core_fingerprint_digest")
        if (
            variant_id != expected_reference.variant_id
            or cohort_kind != expected_reference.cohort_kind
            or reference.stable_order != index + 1
            or fingerprint != expected_reference.core_fingerprint
        ):
            _fail(ReasonCode.TRUSTED_REFERENCE_REGISTRY_MISMATCH, path, "reference ID/order/cohort/fingerprint differs from reviewed legacy identity")
        if reference.core_fingerprint_digest != canonical_digest(fingerprint):
            _fail(ReasonCode.REFERENCE_DIGEST_MISMATCH, f"{path}.core_fingerprint_digest", "fingerprint digest mismatch")
        normalized.append(
            TrustedReference(
                variant_id,
                cohort_kind,
                reference.stable_order,
                fingerprint,
                reference.core_fingerprint_digest,
            )
        )
    return tuple(normalized)


def trusted_reference_registry_digest(
    registry: Sequence[Any] = TRUSTED_REFERENCE_REGISTRY,
) -> str:
    references = validate_trusted_reference_registry(registry)
    payload = {
        "registry_version": TRUSTED_REFERENCE_REGISTRY_VERSION,
        "references": [
            {
                "variant_id": reference.variant_id,
                "cohort_kind": reference.cohort_kind,
                "stable_order": reference.stable_order,
                "core_fingerprint": reference.core_fingerprint,
                "core_fingerprint_digest": reference.core_fingerprint_digest,
            }
            for reference in references
        ],
    }
    return canonical_digest(payload)


def trusted_reference_by_id(variant_id: str) -> TrustedReference:
    for reference in _build_trusted_reference_registry():
        if reference.variant_id == variant_id:
            return reference
    raise KeyError(variant_id)


def _actual_material_differences(current: Mapping[str, Any], nearest: Mapping[str, Any]) -> set[str]:
    differences: set[str] = set()
    if current["spec_rule"] != nearest["spec_rule"] or current["causal_mechanism"] != nearest["causal_mechanism"]:
        differences.add("spec/mechanism")
    if current["target_function_set"] != nearest["target_function_set"]:
        differences.add("target_function_set")
    if current["trigger_shape"] != nearest["trigger_shape"]:
        differences.add("trigger_shape")
    if current["observable_behavior"] != nearest["observable_behavior"] or current["oracle_outcome_vector"] != nearest["oracle_outcome_vector"]:
        differences.add("observable/oracle_outcome")
    if current["normalized_patch_operation"] != nearest["normalized_patch_operation"]:
        differences.add("normalized_patch_operation")
    if current["interaction_depth"] != nearest["interaction_depth"]:
        differences.add("interaction_depth")
    return differences


def core_fingerprint_distance(first: Mapping[str, Any], second: Mapping[str, Any]) -> int:
    """Return deterministic Hamming distance over the fixed eight dimensions."""

    return sum(first[field] != second[field] for field in CORE_FINGERPRINT_FIELD_IDS)


def _reference_pool(
    cohort_kind: str,
    validated_references: Sequence[_ValidatedCandidateReference],
) -> list[tuple[str, dict[str, Any], str]]:
    pool = [
        (reference.variant_id, reference.core_fingerprint, reference.core_fingerprint_digest)
        for reference in _build_trusted_reference_registry()
        if reference.cohort_kind == cohort_kind
    ]
    pool.extend(
        (
            reference.variant_id,
            reference.core_fingerprint,
            reference.core_fingerprint_digest,
        )
        for reference in validated_references
        if reference.cohort_kind == cohort_kind
    )
    return pool


def _resolve_reference(
    metadata: Mapping[str, Any],
    *,
    cohort_kind: str,
    validated_references: Sequence[_ValidatedCandidateReference],
    candidate_ids: Sequence[Any],
    candidate_index: int | None,
    other_candidate_ids: Sequence[Any],
    path: str,
) -> tuple[dict[str, Any], str, list[tuple[str, dict[str, Any], str]]]:
    reference_field = (
        "nearest_legacy_or_admitted_variant_id"
        if cohort_kind == "buggy"
        else "nearest_legacy_or_admitted_clean_variant_id"
    )
    claimed_id = metadata[reference_field]
    if claimed_id == metadata["variant_id"]:
        _fail(ReasonCode.SELF_REFERENCE, f"{path}.{reference_field}", "candidate cannot reference itself")
    pool = _reference_pool(cohort_kind, validated_references)
    by_id = {item[0]: item for item in pool}
    all_trusted = {item.variant_id: item.cohort_kind for item in _build_trusted_reference_registry()}
    if claimed_id not in by_id:
        if claimed_id in all_trusted and all_trusted[claimed_id] != cohort_kind:
            _fail(ReasonCode.WRONG_REFERENCE_COHORT, f"{path}.{reference_field}", "reference belongs to the other cohort")
        if claimed_id in other_candidate_ids:
            _fail(ReasonCode.WRONG_REFERENCE_COHORT, f"{path}.{reference_field}", "admitted reference belongs to the other cohort")
        if claimed_id in candidate_ids and candidate_index is not None:
            claimed_index = list(candidate_ids).index(claimed_id)
            if claimed_index > candidate_index:
                _fail(ReasonCode.FORWARD_REFERENCE, f"{path}.{reference_field}", "reference has not yet been validated")
        _fail(ReasonCode.UNKNOWN_REFERENCE, f"{path}.{reference_field}", "reference is not trusted or previously validated")
    _, resolved_fingerprint, resolved_digest = by_id[claimed_id]
    supplied = _canonical_fingerprint(
        metadata["nearest_reference_core_fingerprint"],
        f"{path}.nearest_reference_core_fingerprint",
    )
    if supplied != resolved_fingerprint:
        _fail(ReasonCode.REFERENCE_FINGERPRINT_MISMATCH, f"{path}.nearest_reference_core_fingerprint", "caller fingerprint does not match resolved reference")
    supplied_digest = validate_sha256(
        metadata["nearest_reference_core_fingerprint_digest"],
        f"{path}.nearest_reference_core_fingerprint_digest",
    )
    if supplied_digest != resolved_digest:
        _fail(ReasonCode.REFERENCE_DIGEST_MISMATCH, f"{path}.nearest_reference_core_fingerprint_digest", "caller digest does not match resolved reference")
    return resolved_fingerprint, resolved_digest, pool


def _validate_diversity(
    metadata: Mapping[str, Any],
    *,
    cohort_kind: str,
    validated_references: Sequence[_ValidatedCandidateReference],
    candidate_ids: Sequence[Any],
    candidate_index: int | None,
    other_candidate_ids: Sequence[Any],
    path: str,
) -> tuple[dict[str, Any], dict[str, Any], str]:
    dimensions = _require_string_list(metadata["material_difference_dimensions"], f"{path}.material_difference_dimensions")
    unknown = [dimension for dimension in dimensions if dimension not in MATERIAL_DIMENSION_IDS]
    if unknown:
        _fail(ReasonCode.WRONG_IDENTITY, f"{path}.material_difference_dimensions", "unknown material dimension")
    dimension_set = set(dimensions)
    if "quota_padding" in dimension_set:
        _fail(ReasonCode.QUOTA_PADDING, f"{path}.material_difference_dimensions", "quota padding is not admissible")
    if dimension_set == {"bucket_or_family_label"}:
        _fail(ReasonCode.FAMILY_LABEL_ONLY_DUPLICATE, f"{path}.material_difference_dimensions", "a bucket/family label-only change is a duplicate")
    rename_dimensions = {"identifier_or_literal", "sku_region_coupon", "prose", "bucket_or_family_label"}
    if dimension_set and dimension_set <= rename_dimensions:
        _fail(ReasonCode.RENAME_OR_LITERAL_ONLY, f"{path}.material_difference_dimensions", "identifier/literal/SKU/region/coupon/prose-only changes are not material")
    current = _canonical_fingerprint(metadata["core_fingerprint"], f"{path}.core_fingerprint")
    resolved, resolved_digest, pool = _resolve_reference(
        metadata,
        cohort_kind=cohort_kind,
        validated_references=validated_references,
        candidate_ids=candidate_ids,
        candidate_index=candidate_index,
        other_candidate_ids=other_candidate_ids,
        path=path,
    )
    actual = _actual_material_differences(current, resolved)
    if len(actual) < 2 or len(actual & dimension_set) < 2:
        _fail(ReasonCode.INSUFFICIENT_MATERIAL_DIFFERENCE, f"{path}.material_difference_dimensions", "at least two evidenced material dimensions must differ")
    if not (actual & dimension_set & set(CORE_MATERIAL_DIMENSION_IDS)):
        _fail(ReasonCode.MISSING_CORE_MATERIAL_DIFFERENCE, f"{path}.material_difference_dimensions", "at least one evidenced core material dimension must differ")
    for reference_id, fingerprint, _ in pool:
        if current == fingerprint:
            _fail(ReasonCode.EXACT_CORE_FINGERPRINT_DUPLICATE, f"{path}.core_fingerprint", f"duplicates {reference_id}")
        if current["normalized_patch_operation"] == fingerprint["normalized_patch_operation"]:
            _fail(ReasonCode.SAME_NORMALIZED_PATCH, f"{path}.core_fingerprint.normalized_patch_operation", f"duplicates {reference_id}")
        if (
            current["target_function_set"] == fingerprint["target_function_set"]
            and current["trigger_shape"] == fingerprint["trigger_shape"]
            and current["oracle_outcome_vector"] == fingerprint["oracle_outcome_vector"]
        ):
            _fail(ReasonCode.SAME_TARGET_TRIGGER_ORACLE, f"{path}.core_fingerprint", f"duplicates {reference_id}")
    computed_nearest_id = min(pool, key=lambda item: core_fingerprint_distance(current, item[1]))[0]
    reference_field = (
        "nearest_legacy_or_admitted_variant_id"
        if cohort_kind == "buggy"
        else "nearest_legacy_or_admitted_clean_variant_id"
    )
    if metadata[reference_field] != computed_nearest_id:
        _fail(ReasonCode.NEAREST_REFERENCE_MISMATCH, f"{path}.{reference_field}", "claimed reference is not the computed nearest under stable tie order")
    _require_nonempty_string(metadata["diversity_rationale"], f"{path}.diversity_rationale")
    return current, resolved, resolved_digest


def validate_candidate_metadata(
    metadata: Any,
    *,
    cohort_kind: str,
    path: str = "candidate",
) -> dict[str, Any]:
    """Validate standalone metadata against reviewed legacy references only."""

    return _validate_candidate_metadata(
        metadata,
        cohort_kind=cohort_kind,
        path=path,
        validated_references=(),
        candidate_ids=(),
        candidate_index=None,
        other_candidate_ids=(),
    )


def _validate_candidate_metadata(
    metadata: Any,
    *,
    cohort_kind: str,
    path: str,
    validated_references: Sequence[_ValidatedCandidateReference],
    candidate_ids: Sequence[Any],
    candidate_index: int | None,
    other_candidate_ids: Sequence[Any],
) -> dict[str, Any]:
    """Validate metadata using only references created by this validation chain."""

    if cohort_kind not in {"buggy", "clean_stress"}:
        _fail(ReasonCode.WRONG_IDENTITY, path, "unknown cohort kind")
    if type(metadata) is not dict:
        _fail(ReasonCode.WRONG_TYPE, path, "expected an object")
    if cohort_kind == "clean_stress":
        forbidden = sorted(set(metadata) & CLEAN_FORBIDDEN_BUG_GROUND_TRUTH_FIELDS)
        if forbidden:
            _fail(ReasonCode.CLEAN_BUG_GROUND_TRUTH_FORBIDDEN, f"{path}.{forbidden[0]}", "buggy cause/fault/fix ground truth is forbidden for clean candidates")
    fields = BUGGY_METADATA_FIELD_IDS if cohort_kind == "buggy" else CLEAN_METADATA_FIELD_IDS
    value = _require_exact_fields(metadata, fields, path)
    validate_portable_value(value, path)
    validate_outcome_free_value(value, path, allow_clean_primary_bucket=cohort_kind == "clean_stress")
    for field in fields:
        if field in {
            "is_buggy",
            "clean_stress_family_order",
            "target_functions",
            "oracle_ids",
            "action_test_catalog_ids",
            "changed_files",
            "changed_functions",
            "no_bug_oracle_ids",
            "material_difference_dimensions",
            "core_fingerprint",
            "nearest_reference_core_fingerprint",
        }:
            continue
        _require_nonempty_string(value[field], f"{path}.{field}")
    variant_id = value["variant_id"]
    expected_re = _BUG_ID_RE if cohort_kind == "buggy" else _CLEAN_ID_RE
    if variant_id in LEGACY_VARIANT_IDS or variant_id.startswith("P1B-"):
        _fail(ReasonCode.NAMESPACE_COLLISION, f"{path}.variant_id", "P1B and P2A namespaces must be disjoint")
    if expected_re.fullmatch(variant_id) is None:
        _fail(ReasonCode.NAMESPACE_MISMATCH, f"{path}.variant_id", "variant ID does not match its cohort namespace")
    if value["domain"] != DOMAIN_ID:
        _fail(ReasonCode.DOMAIN_MISMATCH, f"{path}.domain", "candidate must remain in the checkout/pricing domain")
    if type(value["is_buggy"]) is not bool:
        _fail(ReasonCode.WRONG_TYPE, f"{path}.is_buggy", "expected a bool")
    current, resolved_reference, resolved_reference_digest = _validate_diversity(
        value,
        cohort_kind=cohort_kind,
        validated_references=validated_references,
        candidate_ids=candidate_ids,
        candidate_index=candidate_index,
        other_candidate_ids=other_candidate_ids,
        path=path,
    )
    if value["interaction_depth"] != current["interaction_depth"]:
        _fail(ReasonCode.WRONG_IDENTITY, f"{path}.interaction_depth", "metadata and core fingerprint interaction depth differ")
    if cohort_kind == "buggy":
        if value["cohort"] != BUGGY_COHORT_ID:
            _fail(ReasonCode.COHORT_MISMATCH, f"{path}.cohort", "wrong buggy cohort identity")
        if value["primary_bucket"] not in BUGGY_BUCKET_IDS:
            _fail(ReasonCode.UNKNOWN_BUCKET, f"{path}.primary_bucket", "unknown buggy bucket")
        if value["is_buggy"] is not True:
            _fail(ReasonCode.BUGGY_FLAG_MISMATCH, f"{path}.is_buggy", "buggy candidate must set is_buggy=true")
        for field in ("target_functions", "oracle_ids", "action_test_catalog_ids", "changed_files", "changed_functions"):
            _require_string_list(value[field], f"{path}.{field}", stable_order=True)
        action_mapping = _require_nonempty_string(value["action_mapping"], f"{path}.action_mapping")
        if action_mapping not in APPROVED_ACTION_IDS:
            _fail(
                ReasonCode.UNKNOWN_ACTION_ID,
                f"{path}.action_mapping",
                "action mapping must be one approved existing action ID",
            )
        if value["oracle_ids"] != [record["oracle_id"] for record in current["oracle_outcome_vector"]]:
            _fail(ReasonCode.WRONG_IDENTITY, f"{path}.oracle_ids", "oracle IDs must match the core outcome vector")
    else:
        if value["cohort"] != CLEAN_COHORT_ID:
            _fail(ReasonCode.COHORT_MISMATCH, f"{path}.cohort", "wrong clean cohort identity")
        if value["primary_bucket"] != CLEAN_PRIMARY_BUCKET_ID:
            _fail(ReasonCode.PRIMARY_BUCKET_MISMATCH, f"{path}.primary_bucket", "clean primary bucket must be clean_false_positive")
        if value["is_buggy"] is not False:
            _fail(ReasonCode.BUGGY_FLAG_MISMATCH, f"{path}.is_buggy", "clean candidate must set is_buggy=false")
        family_id = value["clean_stress_family_id"]
        if family_id not in CLEAN_STRESS_FAMILY_IDS:
            _fail(ReasonCode.UNKNOWN_CLEAN_FAMILY, f"{path}.clean_stress_family_id", "unknown clean family")
        if type(value["clean_stress_family_order"]) is not int:
            _fail(ReasonCode.WRONG_TYPE, f"{path}.clean_stress_family_order", "expected an int")
        expected_order = CLEAN_STRESS_FAMILY_IDS.index(family_id) + 1
        if value["clean_stress_family_order"] != expected_order:
            _fail(ReasonCode.REORDERED_CLEAN_FAMILY, f"{path}.clean_stress_family_order", "family order does not match the exact contract")
        if value["adjacent_buggy_bucket_id"] != CLEAN_FAMILY_TO_ADJACENT_BUCKET[family_id]:
            _fail(ReasonCode.WRONG_ADJACENT_BUCKET, f"{path}.adjacent_buggy_bucket_id", "adjacent bucket mapping is not exact")
        for field in ("no_bug_oracle_ids", "changed_files", "changed_functions"):
            _require_string_list(value[field], f"{path}.{field}", stable_order=True)
        if value["no_bug_oracle_ids"] != [record["oracle_id"] for record in current["oracle_outcome_vector"]]:
            _fail(ReasonCode.WRONG_IDENTITY, f"{path}.no_bug_oracle_ids", "no-bug oracle IDs must match the core outcome vector")
    canonical = {field: value[field] for field in fields}
    canonical["core_fingerprint"] = current
    canonical["nearest_reference_core_fingerprint"] = resolved_reference
    canonical["nearest_reference_core_fingerprint_digest"] = resolved_reference_digest
    return canonical


def validate_taxonomy_identity(buggy_bucket_ids: Any, clean_family_definitions: Any) -> None:
    if type(buggy_bucket_ids) is not list:
        _fail(ReasonCode.WRONG_TYPE, "buggy_bucket_ids", "expected a list")
    unknown = [item for item in buggy_bucket_ids if item not in BUGGY_BUCKET_IDS]
    if unknown:
        _fail(ReasonCode.UNKNOWN_BUCKET, "buggy_bucket_ids", "unknown buggy bucket")
    missing = [item for item in BUGGY_BUCKET_IDS if item not in buggy_bucket_ids]
    if missing:
        _fail(ReasonCode.MISSING_BUCKET, "buggy_bucket_ids", "one or more exact buggy buckets are missing")
    if tuple(buggy_bucket_ids) != BUGGY_BUCKET_IDS:
        _fail(ReasonCode.REORDERED_BUCKET, "buggy_bucket_ids", "buggy bucket order differs from the exact contract")
    if type(clean_family_definitions) is not list:
        _fail(ReasonCode.WRONG_TYPE, "clean_family_definitions", "expected a list")
    family_fields = ("family_id", "order", "adjacent_buggy_bucket_id")
    normalized = [
        _require_exact_fields(definition, family_fields, f"clean_family_definitions[{index}]")
        for index, definition in enumerate(clean_family_definitions)
    ]
    ids = [definition["family_id"] for definition in normalized]
    if [item for item in ids if item not in CLEAN_STRESS_FAMILY_IDS]:
        _fail(ReasonCode.UNKNOWN_CLEAN_FAMILY, "clean_family_definitions", "unknown clean family")
    if [item for item in CLEAN_STRESS_FAMILY_IDS if item not in ids]:
        _fail(ReasonCode.MISSING_CLEAN_FAMILY, "clean_family_definitions", "one or more exact clean families are missing")
    if tuple(ids) != CLEAN_STRESS_FAMILY_IDS:
        _fail(ReasonCode.REORDERED_CLEAN_FAMILY, "clean_family_definitions", "clean family order differs from the exact contract")
    for index, definition in enumerate(normalized):
        family_id = definition["family_id"]
        if type(definition["order"]) is not int or definition["order"] != index + 1:
            _fail(ReasonCode.REORDERED_CLEAN_FAMILY, f"clean_family_definitions[{index}].order", "family order is not exact")
        if definition["adjacent_buggy_bucket_id"] != CLEAN_FAMILY_TO_ADJACENT_BUCKET[family_id]:
            _fail(ReasonCode.WRONG_ADJACENT_BUCKET, f"clean_family_definitions[{index}].adjacent_buggy_bucket_id", "mapping is not exact")


def clean_family_definitions() -> list[dict[str, Any]]:
    return [
        {"family_id": family_id, "order": index, "adjacent_buggy_bucket_id": CLEAN_FAMILY_TO_ADJACENT_BUCKET[family_id]}
        for index, family_id in enumerate(CLEAN_STRESS_FAMILY_IDS, start=1)
    ]


def validate_candidate_cohort(
    buggy_candidates: Any,
    clean_candidates: Any,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if type(buggy_candidates) is not list or type(clean_candidates) is not list:
        _fail(ReasonCode.WRONG_TYPE, "candidates", "buggy and clean candidates must be lists")
    raw_buggy_ids = [item.get("variant_id") for item in buggy_candidates if type(item) is dict]
    raw_clean_ids = [item.get("variant_id") for item in clean_candidates if type(item) is dict]
    known_ids = [item for item in raw_buggy_ids + raw_clean_ids if type(item) is str]
    if len(set(known_ids)) != len(known_ids):
        _fail(
            ReasonCode.DUPLICATE_VARIANT_ID,
            "variant_ids",
            "candidate IDs must be globally unique before validation",
        )
    buggy: list[dict[str, Any]] = []
    buggy_references: list[_ValidatedCandidateReference] = []
    for index, item in enumerate(buggy_candidates):
        validated = _validate_candidate_metadata(
            item,
            cohort_kind="buggy",
            path=f"buggy_candidates[{index}]",
            validated_references=buggy_references,
            candidate_ids=raw_buggy_ids,
            candidate_index=index,
            other_candidate_ids=raw_clean_ids,
        )
        buggy.append(validated)
        buggy_references.append(
            _ValidatedCandidateReference(
                validated["variant_id"],
                "buggy",
                index + 1,
                validated["core_fingerprint"],
                canonical_digest(validated["core_fingerprint"]),
            )
        )
    clean: list[dict[str, Any]] = []
    clean_references: list[_ValidatedCandidateReference] = []
    for index, item in enumerate(clean_candidates):
        validated = _validate_candidate_metadata(
            item,
            cohort_kind="clean_stress",
            path=f"clean_candidates[{index}]",
            validated_references=clean_references,
            candidate_ids=raw_clean_ids,
            candidate_index=index,
            other_candidate_ids=raw_buggy_ids,
        )
        clean.append(validated)
        clean_references.append(
            _ValidatedCandidateReference(
                validated["variant_id"],
                "clean_stress",
                index + 1,
                validated["core_fingerprint"],
                canonical_digest(validated["core_fingerprint"]),
            )
        )
    all_ids = [item["variant_id"] for item in buggy + clean]
    if len(set(all_ids)) != len(all_ids):
        _fail(ReasonCode.DUPLICATE_VARIANT_ID, "variant_ids", "candidate IDs must be globally unique")
    buggy_counts = Counter(item["primary_bucket"] for item in buggy)
    if len(buggy) < 10 or len(buggy) > 20:
        _fail(ReasonCode.BUGGY_TOTAL_COUNT, "buggy_candidates", "buggy total must be 10-20")
    for bucket in BUGGY_BUCKET_IDS:
        if buggy_counts[bucket] < 2 or buggy_counts[bucket] > 4:
            _fail(ReasonCode.BUGGY_BUCKET_COUNT, f"buggy_counts.{bucket}", "each buggy bucket requires 2-4 candidates")
    clean_counts = Counter(item["clean_stress_family_id"] for item in clean)
    if len(clean) < 5 or len(clean) > 10:
        _fail(ReasonCode.CLEAN_TOTAL_COUNT, "clean_candidates", "clean total must be 5-10")
    for family_id in CLEAN_STRESS_FAMILY_IDS:
        if clean_counts[family_id] < 1 or clean_counts[family_id] > 2:
            _fail(ReasonCode.CLEAN_FAMILY_COUNT, f"clean_counts.{family_id}", "each clean family requires 1-2 candidates")
    expected_buggy = sorted(buggy, key=lambda item: (BUGGY_BUCKET_IDS.index(item["primary_bucket"]), item["variant_id"]))
    expected_clean = sorted(clean, key=lambda item: (CLEAN_STRESS_FAMILY_IDS.index(item["clean_stress_family_id"]), item["variant_id"]))
    if [item["variant_id"] for item in buggy] != [item["variant_id"] for item in expected_buggy]:
        _fail(ReasonCode.REORDERED_VARIANT_ID, "buggy_candidates", "buggy candidates must use bucket-major then ID order")
    if [item["variant_id"] for item in clean] != [item["variant_id"] for item in expected_clean]:
        _fail(ReasonCode.REORDERED_VARIANT_ID, "clean_candidates", "clean candidates must use family-major then ID order")
    return buggy, clean


_EXPECTED_GAP_SUPPORT = (
    ("P1B-BUG-001", "P1B-BUG-002", "P1B-BUG-003", "P1B-BUG-004"),
    ("P1B-BUG-005", "P1B-BUG-006", "P1B-BUG-007", "P1B-BUG-008"),
    ("P1B-BUG-009", "P1B-BUG-010", "P1B-BUG-011", "P1B-BUG-012"),
    ("P1B-BUG-013", "P1B-BUG-014", "P1B-BUG-015", "P1B-BUG-016"),
    ("P1B-BUG-017", "P1B-BUG-018", "P1B-BUG-019", "P1B-BUG-020"),
    ("P1B-CLEAN-021",),
    ("P1B-CLEAN-022",),
    ("P1B-CLEAN-023",),
    ("P1B-CLEAN-024",),
    ("P1B-CLEAN-025",),
)
_ORACLE_CASE_BY_LEGACY_ID = {
    row[0]: row[7] for row in _TRUSTED_REFERENCE_ROWS
}
_METADATA_PATH = "src/bug_cause_inference/p1b/dataset.py"
_ORACLE_PATH = "src/bug_cause_inference/p1b/execution.py"
_PATCH_PATH_PREFIX = "src/bug_cause_inference/p1b/artifacts/real_diff/patches"
_SOURCE_KIND_IDS = ("legacy_metadata", "patch_artifact", "oracle_case_semantics")


def _coverage_sources(support_ids: tuple[str, ...]) -> tuple[CoverageSourceIdentity, ...]:
    sources: list[CoverageSourceIdentity] = []
    for variant_id in support_ids:
        sources.extend(
            (
                CoverageSourceIdentity("legacy_metadata", _METADATA_PATH, variant_id, (variant_id,)),
                CoverageSourceIdentity("patch_artifact", f"{_PATCH_PATH_PREFIX}/{variant_id}.patch", variant_id, (variant_id,)),
                CoverageSourceIdentity("oracle_case_semantics", _ORACLE_PATH, _ORACLE_CASE_BY_LEGACY_ID[variant_id], (variant_id,)),
            )
        )
    return tuple(sources)


_NON_OUTCOME_BASIS = (
    "Derived only from reviewed legacy metadata, repository-relative patch identity, "
    "and deterministic case/oracle semantics."
)

_REGISTRY_TEXT = (
    (
        "Legacy support covers inclusive thresholds, a valid upper bound, and half-up monetary rounding.",
        ("spec_rule", "causal_mechanism", "target_function_set", "trigger_shape", "oracle_outcome_vector", "normalized_patch_operation"),
        "Coverage is concentrated in single-function scalar boundary comparisons or rounding operations with direct deterministic counterexamples.",
        "Future eligible shapes must add materially different boundary semantics or interaction structure without cloning existing comparisons, literals, or patches.",
    ),
    (
        "Legacy support covers absent coupon, region, item collection, and reservation-field inputs.",
        ("optional_absence_shape", "causal_mechanism", "target_function_set", "exception_or_default_oracle", "normalized_patch_operation"),
        "Existing shapes are localized absent-value, key, or collection normalization cases.",
        "Future eligible shapes must exercise a materially different optional-input contract, target set, observable behavior, or interaction depth.",
    ),
    (
        "Legacy support covers scalar fallback, conservative flag default, region alias lookup, and string-to-number parsing.",
        ("config_representation", "default_semantics", "alias_or_type_normalization", "target_function_set", "oracle_outcome_vector"),
        "Existing shapes cover four direct lookup, default, or normalization operations.",
        "Future eligible shapes must add a distinct configuration equivalence, normalization, or default mechanism with independent oracle semantics.",
    ),
    (
        "Legacy support covers reversal, repeat idempotence, release synchronization, and stale quote sequences.",
        ("sequence_shape", "state_invariant", "interaction_depth", "target_function_set", "observable_behavior"),
        "Existing sequences span single-object and cross-helper state in four fixed interaction forms.",
        "Future eligible shapes must introduce a materially different state model, ordering mechanism, or invariant oracle.",
    ),
    (
        "Legacy support covers calculation order, item selection, digital-shipping exemption, and preorder exception rules.",
        ("spec_rule", "causal_mechanism", "selection_or_exception_shape", "target_function_set", "oracle_outcome_vector"),
        "Existing shapes instantiate one ordering rule, one selection rule, and two explicit exception rules.",
        "Future eligible shapes must cover materially distinct specification semantics and oracle behavior.",
    ),
    (
        "One benign threshold variable extraction preserves below, at, and above-threshold behavior.",
        ("clean_stress_mechanism", "boundary_rule", "benign_patch_operation", "no_bug_oracle_vector"),
        "Legacy clean support contains one local refactor adjacent to an inclusive shipping threshold.",
        "Future clean stress must preserve a materially different valid boundary behavior and benign provenance.",
    ),
    (
        "One benign coupon-normalization rename preserves None, empty, and absent-coupon no-op semantics.",
        ("clean_stress_mechanism", "optional_absence_shape", "benign_patch_operation", "no_bug_oracle_vector"),
        "Legacy clean support contains one coupon-specific optional-absence shape.",
        "Future clean stress must preserve a different reviewed optional-absence contract with distinct evidence.",
    ),
    (
        "One benign feature-flag lookup simplification preserves absent and explicit-false equivalence.",
        ("clean_stress_mechanism", "config_equivalence", "benign_patch_operation", "no_bug_oracle_vector"),
        "Legacy clean support contains one conservative boolean-default equivalence shape.",
        "Future clean stress must preserve a materially different configuration representation or normalization equivalence.",
    ),
    (
        "One benign reservation-cancellation extraction preserves the reserve, cancel, reserve invariant.",
        ("clean_stress_mechanism", "valid_sequence_shape", "state_invariant", "benign_patch_operation", "no_bug_oracle_vector"),
        "Legacy clean support contains one reservation reversal sequence.",
        "Future clean stress must preserve a materially different valid reorder, repeat, idempotent, or no-op transition.",
    ),
    (
        "One benign tax extraction preserves discount-before-tax and half-up final-total semantics.",
        ("clean_stress_mechanism", "spec_rule", "intermediate_signal", "benign_patch_operation", "no_bug_oracle_vector"),
        "Legacy clean support contains one calculation-order and rounding interaction.",
        "Future clean stress must preserve a different explicit but nonintuitive specification rule.",
    ),
)


def _build_coverage_gap_registry() -> tuple[CoverageGapEntry, ...]:
    gap_ids = tuple([f"buggy.{item}" for item in BUGGY_BUCKET_IDS] + [f"clean_stress.{item}" for item in CLEAN_STRESS_FAMILY_IDS])
    taxonomy_ids = BUGGY_BUCKET_IDS + CLEAN_STRESS_FAMILY_IDS
    entries: list[CoverageGapEntry] = []
    for index, (gap_id, taxonomy_id, support, text) in enumerate(
        zip(gap_ids, taxonomy_ids, _EXPECTED_GAP_SUPPORT, _REGISTRY_TEXT, strict=True),
        start=1,
    ):
        entries.append(
            CoverageGapEntry(
                gap_id=gap_id,
                cohort_kind="buggy" if index <= 5 else "clean_stress",
                primary_bucket_or_clean_family_id=taxonomy_id,
                stable_order=index,
                legacy_support_ids=support,
                legacy_coverage_summary=text[0],
                gap_taxonomy_dimensions=text[1],
                gap_statement=text[2],
                candidate_need_statement=text[3],
                source_basis=_coverage_sources(support),
                explicit_non_outcome_basis=_NON_OUTCOME_BASIS,
            )
        )
    return tuple(entries)


COVERAGE_GAP_REGISTRY = _build_coverage_gap_registry()
_REGISTRY_FIELD_IDS = tuple(CoverageGapEntry.__dataclass_fields__)
_SOURCE_FIELD_IDS = tuple(CoverageSourceIdentity.__dataclass_fields__)
_EXPECTED_REGISTRY_IDS = tuple(entry.gap_id for entry in COVERAGE_GAP_REGISTRY)


def _source_identity_from_value(value: Any, path: str) -> CoverageSourceIdentity:
    if isinstance(value, CoverageSourceIdentity):
        return value
    mapping = _require_exact_fields(value, _SOURCE_FIELD_IDS, path)
    if type(mapping["legacy_support_ids"]) not in {list, tuple}:
        _fail(ReasonCode.WRONG_TYPE, f"{path}.legacy_support_ids", "expected a list or tuple")
    return CoverageSourceIdentity(
        mapping["kind"],
        mapping["repository_path"],
        mapping["anchor"],
        tuple(mapping["legacy_support_ids"]),
    )


def _registry_entry_from_value(value: Any, index: int) -> CoverageGapEntry:
    if isinstance(value, CoverageGapEntry):
        return value
    path = f"registry[{index}]"
    mapping = _require_exact_fields(value, _REGISTRY_FIELD_IDS, path)
    if type(mapping["source_basis"]) not in {list, tuple}:
        _fail(ReasonCode.WRONG_TYPE, f"{path}.source_basis", "expected a list or tuple")
    try:
        return CoverageGapEntry(
            gap_id=mapping["gap_id"],
            cohort_kind=mapping["cohort_kind"],
            primary_bucket_or_clean_family_id=mapping["primary_bucket_or_clean_family_id"],
            stable_order=mapping["stable_order"],
            legacy_support_ids=tuple(mapping["legacy_support_ids"]),
            legacy_coverage_summary=mapping["legacy_coverage_summary"],
            gap_taxonomy_dimensions=tuple(mapping["gap_taxonomy_dimensions"]),
            gap_statement=mapping["gap_statement"],
            candidate_need_statement=mapping["candidate_need_statement"],
            source_basis=tuple(
                _source_identity_from_value(item, f"{path}.source_basis[{source_index}]")
                for source_index, item in enumerate(mapping["source_basis"])
            ),
            explicit_non_outcome_basis=mapping["explicit_non_outcome_basis"],
        )
    except TypeError as exc:
        _fail(ReasonCode.WRONG_TYPE, path, f"invalid registry field type: {type(exc).__name__}")
    raise AssertionError("unreachable")


def _validate_source_identity(source: CoverageSourceIdentity, path: str) -> None:
    if source.kind not in _SOURCE_KIND_IDS:
        _fail(ReasonCode.REGISTRY_SOURCE_BASIS_INVALID, f"{path}.kind", "unknown source kind")
    repository_path = _require_nonempty_string(source.repository_path, f"{path}.repository_path")
    anchor = _require_nonempty_string(source.anchor, f"{path}.anchor")
    if "\\" in repository_path or PurePosixPath(repository_path).is_absolute() or ".." in PurePosixPath(repository_path).parts:
        _fail(ReasonCode.REGISTRY_SOURCE_BASIS_INVALID, f"{path}.repository_path", "path must be normalized repository-relative POSIX")
    if any(character in repository_path or character in anchor for character in "*?[]") or ".." in anchor:
        _fail(ReasonCode.REGISTRY_SOURCE_BASIS_INVALID, path, "wildcard/range/parent anchors are forbidden")
    if PurePosixPath(repository_path).as_posix() != repository_path or _is_local_temporary_path(repository_path):
        _fail(ReasonCode.REGISTRY_SOURCE_BASIS_INVALID, f"{path}.repository_path", "path is not normalized tracked-source identity")
    validate_portable_value(repository_path, f"{path}.repository_path")
    if not source.legacy_support_ids or len(set(source.legacy_support_ids)) != len(source.legacy_support_ids):
        _fail(ReasonCode.REGISTRY_SOURCE_BASIS_INVALID, f"{path}.legacy_support_ids", "support IDs must be non-empty and unique")
    if any(type(item) is not str or item not in LEGACY_VARIANT_IDS for item in source.legacy_support_ids):
        _fail(ReasonCode.REGISTRY_SOURCE_BASIS_INVALID, f"{path}.legacy_support_ids", "unknown legacy support ID")


def validate_coverage_gap_registry(
    registry: Sequence[Any] = COVERAGE_GAP_REGISTRY,
) -> tuple[CoverageGapEntry, ...]:
    if type(registry) not in {list, tuple}:
        _fail(ReasonCode.WRONG_TYPE, "registry", "expected a list or tuple")
    entries = tuple(_registry_entry_from_value(value, index) for index, value in enumerate(registry))
    if tuple(entry.gap_id for entry in entries) != _EXPECTED_REGISTRY_IDS:
        _fail(ReasonCode.REGISTRY_IDENTITY_MISMATCH, "registry.gap_ids", "registry IDs are missing, unknown, duplicated, or reordered")
    flattened: list[str] = []
    for index, entry in enumerate(entries):
        path = f"registry[{index}]"
        expected = COVERAGE_GAP_REGISTRY[index]
        for field in (
            "gap_id",
            "cohort_kind",
            "primary_bucket_or_clean_family_id",
            "legacy_coverage_summary",
            "gap_statement",
            "candidate_need_statement",
            "explicit_non_outcome_basis",
        ):
            _require_nonempty_string(getattr(entry, field), f"{path}.{field}")
        if type(entry.stable_order) is not int or entry.stable_order != index + 1:
            _fail(ReasonCode.REGISTRY_IDENTITY_MISMATCH, f"{path}.stable_order", "stable order must be contiguous and exact")
        if entry.cohort_kind != expected.cohort_kind or entry.primary_bucket_or_clean_family_id != expected.primary_bucket_or_clean_family_id:
            _fail(ReasonCode.REGISTRY_IDENTITY_MISMATCH, path, "cohort/taxonomy identity mismatch")
        if entry.legacy_support_ids != _EXPECTED_GAP_SUPPORT[index]:
            _fail(ReasonCode.REGISTRY_LEGACY_SUPPORT_MISMATCH, f"{path}.legacy_support_ids", "support must match the exact gap partition")
        flattened.extend(entry.legacy_support_ids)
        dimensions = list(entry.gap_taxonomy_dimensions)
        if not dimensions:
            _fail(ReasonCode.EMPTY_VALUE, f"{path}.gap_taxonomy_dimensions", "dimensions must not be empty")
        if any(type(item) is not str or not item.strip() for item in dimensions):
            _fail(ReasonCode.WRONG_TYPE, f"{path}.gap_taxonomy_dimensions", "dimensions must be non-empty strings")
        if len(set(dimensions)) != len(dimensions):
            _fail(ReasonCode.REGISTRY_IDENTITY_MISMATCH, f"{path}.gap_taxonomy_dimensions", "dimensions must be unique")
        if entry.gap_taxonomy_dimensions != expected.gap_taxonomy_dimensions:
            _fail(ReasonCode.REGISTRY_IDENTITY_MISMATCH, f"{path}.gap_taxonomy_dimensions", "dimension order is not the stable contract")
        if not entry.source_basis:
            _fail(ReasonCode.EMPTY_VALUE, f"{path}.source_basis", "source basis must not be empty")
        for source_index, source in enumerate(entry.source_basis):
            _validate_source_identity(source, f"{path}.source_basis[{source_index}]")
        if len(set(entry.source_basis)) != len(entry.source_basis):
            _fail(ReasonCode.REGISTRY_SOURCE_BASIS_INVALID, f"{path}.source_basis", "source identities must be unique")
        for kind in _SOURCE_KIND_IDS:
            supported = tuple(
                variant_id
                for variant_id in entry.legacy_support_ids
                if any(source.kind == kind and variant_id in source.legacy_support_ids for source in entry.source_basis)
            )
            if supported != entry.legacy_support_ids:
                _fail(ReasonCode.REGISTRY_SOURCE_BASIS_INVALID, f"{path}.source_basis", f"{kind} does not evidence the exact support set")
        if entry.source_basis != expected.source_basis:
            _fail(ReasonCode.REGISTRY_SOURCE_BASIS_INVALID, f"{path}.source_basis", "source identity/path/anchor/support differs from the exact allowlist")
        validate_outcome_free_value(
            {
                "legacy_coverage_summary": entry.legacy_coverage_summary,
                "gap_taxonomy_dimensions": entry.gap_taxonomy_dimensions,
                "gap_statement": entry.gap_statement,
                "candidate_need_statement": entry.candidate_need_statement,
                "source_basis": [
                    {
                        "kind": source.kind,
                        "repository_path": source.repository_path,
                        "anchor": source.anchor,
                        "legacy_support_ids": source.legacy_support_ids,
                    }
                    for source in entry.source_basis
                ],
                "explicit_non_outcome_basis": entry.explicit_non_outcome_basis,
            },
            path,
        )
        if entry.explicit_non_outcome_basis != _NON_OUTCOME_BASIS:
            _fail(ReasonCode.REGISTRY_OUTCOME_LEAKAGE, f"{path}.explicit_non_outcome_basis", "non-outcome basis statement is not exact")
    if tuple(flattened) != LEGACY_VARIANT_IDS or len(set(flattened)) != len(LEGACY_VARIANT_IDS):
        _fail(ReasonCode.REGISTRY_LEGACY_SUPPORT_MISMATCH, "registry.legacy_support_ids", "flattened support must be the exact stable 25-ID partition")
    return entries


def coverage_gap_registry_digest(
    registry: Sequence[Any] = COVERAGE_GAP_REGISTRY,
) -> str:
    entries = validate_coverage_gap_registry(registry)
    payload = {
        "registry_version": COVERAGE_GAP_REGISTRY_VERSION,
        "entries": [
            {
                "gap_id": entry.gap_id,
                "legacy_support_ids": entry.legacy_support_ids,
                "source_basis": [
                    {
                        "kind": source.kind,
                        "repository_path": source.repository_path,
                        "anchor": source.anchor,
                        "legacy_support_ids": source.legacy_support_ids,
                    }
                    for source in entry.source_basis
                ],
            }
            for entry in entries
        ],
    }
    return canonical_digest(payload)
