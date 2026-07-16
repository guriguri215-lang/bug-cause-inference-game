"""Outcome-free adequacy contracts for the P2a pre-authoring gate.

This module intentionally contains no policy runner, evaluator, report builder,
candidate artifact, or realized freeze.  Its registry is based only on the
legacy metadata, relative source/patch identity, and deterministic case/oracle
semantics reviewed for the current 25 variants.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from enum import Enum
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
)
# For clean rows, changed files/functions and the fingerprint target set are
# artifact provenance only; they do not identify a fault location or target.
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
    "matrix",
    "worst_bucket",
    "worst bucket",
    "false_positive_result",
    "false-positive result",
    "investigation_cost",
    "investigation cost",
    "policy_loss",
    "policy loss",
    "p1c_outcome",
    "p1d_outcome",
    "p1c",
    "p1d",
)


class ReasonCode(str, Enum):
    MISSING_FIELD = "missing_field"
    UNKNOWN_FIELD = "unknown_field"
    POLICY_OUTCOME_FIELD_FORBIDDEN = "policy_outcome_field_forbidden"
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
    source_basis: tuple[str, ...]
    explicit_non_outcome_basis: str


def _fail(code: ReasonCode, path: str, message: str) -> None:
    raise AdequacyValidationError(ValidationIssue(code.value, path, message))


def _require_exact_fields(value: Any, fields: tuple[str, ...], path: str) -> Mapping[str, Any]:
    if type(value) is not dict:
        _fail(ReasonCode.WRONG_TYPE, path, "expected an object")
    keys = set(value)
    outcome_keys = sorted(keys & POLICY_OUTCOME_FIELD_IDS)
    if outcome_keys:
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


def _require_string_list(value: Any, path: str, *, allow_empty: bool = False) -> list[str]:
    if type(value) is not list:
        _fail(ReasonCode.WRONG_TYPE, path, "expected a list")
    if not value and not allow_empty:
        _fail(ReasonCode.EMPTY_VALUE, path, "list must not be empty")
    for index, item in enumerate(value):
        _require_nonempty_string(item, f"{path}[{index}]")
    if len(set(value)) != len(value):
        _fail(ReasonCode.WRONG_IDENTITY, path, "list entries must be unique")
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
    if type(value) is list:
        for index, child in enumerate(value):
            validate_portable_value(child, f"{path}[{index}]")
        return
    if type(value) is tuple:
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
    _fail(
        ReasonCode.UNSUPPORTED_CANONICAL_TYPE,
        path,
        f"unsupported value type {type(value).__name__}",
    )


def _validate_no_outcome_material(value: Any, path: str) -> None:
    if type(value) is str:
        lowered = value.lower()
        if any(term in lowered for term in _REGISTRY_OUTCOME_TERMS):
            _fail(
                ReasonCode.POLICY_OUTCOME_FIELD_FORBIDDEN,
                path,
                "policy-result material is forbidden before candidate freeze",
            )
    elif type(value) in {list, tuple}:
        for index, child in enumerate(value):
            _validate_no_outcome_material(child, f"{path}[{index}]")
    elif type(value) is dict:
        for key, child in value.items():
            _validate_no_outcome_material(key, f"{path}.<key>")
            _validate_no_outcome_material(child, f"{path}.{key}")


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
            "items": [[_typed_node(key), _typed_node(child)] for key, child in value.items()],
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
    _require_string_list(fingerprint["target_function_set"], f"{path}.target_function_set")
    oracle_vector = fingerprint["oracle_outcome_vector"]
    if type(oracle_vector) is not list or not oracle_vector:
        _fail(ReasonCode.EMPTY_VALUE, f"{path}.oracle_outcome_vector", "oracle vector must be a non-empty list")
    validate_portable_value(oracle_vector, f"{path}.oracle_outcome_vector")
    return {field: fingerprint[field] for field in CORE_FINGERPRINT_FIELD_IDS}


def _actual_material_differences(current: Mapping[str, Any], nearest: Mapping[str, Any]) -> set[str]:
    differences: set[str] = set()
    if current["spec_rule"] != nearest["spec_rule"] or current["causal_mechanism"] != nearest["causal_mechanism"]:
        differences.add("spec/mechanism")
    if current["target_function_set"] != nearest["target_function_set"]:
        differences.add("target_function_set")
    if current["trigger_shape"] != nearest["trigger_shape"]:
        differences.add("trigger_shape")
    if (
        current["observable_behavior"] != nearest["observable_behavior"]
        or current["oracle_outcome_vector"] != nearest["oracle_outcome_vector"]
    ):
        differences.add("observable/oracle_outcome")
    if current["normalized_patch_operation"] != nearest["normalized_patch_operation"]:
        differences.add("normalized_patch_operation")
    if current["interaction_depth"] != nearest["interaction_depth"]:
        differences.add("interaction_depth")
    return differences


def _validate_diversity(metadata: Mapping[str, Any], path: str) -> tuple[dict[str, Any], dict[str, Any]]:
    dimensions = _require_string_list(
        metadata["material_difference_dimensions"],
        f"{path}.material_difference_dimensions",
    )
    unknown = [dimension for dimension in dimensions if dimension not in MATERIAL_DIMENSION_IDS]
    if unknown:
        _fail(ReasonCode.WRONG_IDENTITY, f"{path}.material_difference_dimensions", "unknown material dimension")
    dimension_set = set(dimensions)
    if "quota_padding" in dimension_set:
        _fail(ReasonCode.QUOTA_PADDING, f"{path}.material_difference_dimensions", "quota padding is not admissible")
    if dimension_set == {"bucket_or_family_label"}:
        _fail(
            ReasonCode.FAMILY_LABEL_ONLY_DUPLICATE,
            f"{path}.material_difference_dimensions",
            "a bucket/family label-only change is a duplicate",
        )
    rename_dimensions = {"identifier_or_literal", "sku_region_coupon", "prose", "bucket_or_family_label"}
    if dimension_set and dimension_set <= rename_dimensions:
        _fail(
            ReasonCode.RENAME_OR_LITERAL_ONLY,
            f"{path}.material_difference_dimensions",
            "identifier/literal/SKU/region/coupon/prose-only changes are not material",
        )
    current = _canonical_fingerprint(metadata["core_fingerprint"], f"{path}.core_fingerprint")
    nearest = _canonical_fingerprint(
        metadata["nearest_reference_core_fingerprint"],
        f"{path}.nearest_reference_core_fingerprint",
    )
    if current["normalized_patch_operation"] == nearest["normalized_patch_operation"]:
        _fail(
            ReasonCode.SAME_NORMALIZED_PATCH,
            f"{path}.core_fingerprint.normalized_patch_operation",
            "normalized patch operation matches the nearest reference",
        )
    if (
        current["target_function_set"] == nearest["target_function_set"]
        and current["trigger_shape"] == nearest["trigger_shape"]
        and current["oracle_outcome_vector"] == nearest["oracle_outcome_vector"]
    ):
        _fail(
            ReasonCode.SAME_TARGET_TRIGGER_ORACLE,
            f"{path}.core_fingerprint",
            "target, trigger, and oracle vector match the nearest reference",
        )
    actual = _actual_material_differences(current, nearest)
    claimed_actual = actual & dimension_set
    if len(actual) < 2 or len(claimed_actual) < 2:
        _fail(
            ReasonCode.INSUFFICIENT_MATERIAL_DIFFERENCE,
            f"{path}.material_difference_dimensions",
            "at least two evidenced material dimensions must differ",
        )
    if not (actual & dimension_set & set(CORE_MATERIAL_DIMENSION_IDS)):
        _fail(
            ReasonCode.MISSING_CORE_MATERIAL_DIFFERENCE,
            f"{path}.material_difference_dimensions",
            "at least one evidenced core material dimension must differ",
        )
    _require_nonempty_string(metadata["diversity_rationale"], f"{path}.diversity_rationale")
    return current, nearest


def validate_candidate_metadata(metadata: Any, *, cohort_kind: str, path: str = "candidate") -> dict[str, Any]:
    """Validate and return metadata in the stable schema field order."""

    if cohort_kind not in {"buggy", "clean_stress"}:
        _fail(ReasonCode.WRONG_IDENTITY, path, "unknown cohort kind")
    if type(metadata) is not dict:
        _fail(ReasonCode.WRONG_TYPE, path, "expected an object")
    if cohort_kind == "clean_stress":
        forbidden = sorted(set(metadata) & CLEAN_FORBIDDEN_BUG_GROUND_TRUTH_FIELDS)
        if forbidden:
            _fail(
                ReasonCode.CLEAN_BUG_GROUND_TRUTH_FORBIDDEN,
                f"{path}.{forbidden[0]}",
                "buggy cause/fault/fix ground truth is forbidden for clean candidates",
            )
    fields = BUGGY_METADATA_FIELD_IDS if cohort_kind == "buggy" else CLEAN_METADATA_FIELD_IDS
    value = _require_exact_fields(metadata, fields, path)
    validate_portable_value(value, path)
    _validate_no_outcome_material(value, path)
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
    _validate_diversity(value, path)
    if cohort_kind == "buggy":
        if value["cohort"] != BUGGY_COHORT_ID:
            _fail(ReasonCode.COHORT_MISMATCH, f"{path}.cohort", "wrong buggy cohort identity")
        if value["primary_bucket"] not in BUGGY_BUCKET_IDS:
            _fail(ReasonCode.UNKNOWN_BUCKET, f"{path}.primary_bucket", "unknown buggy bucket")
        if value["is_buggy"] is not True:
            _fail(ReasonCode.BUGGY_FLAG_MISMATCH, f"{path}.is_buggy", "buggy candidate must set is_buggy=true")
        for field in (
            "target_functions",
            "oracle_ids",
            "action_test_catalog_ids",
            "changed_files",
            "changed_functions",
        ):
            _require_string_list(value[field], f"{path}.{field}")
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
            _require_string_list(value[field], f"{path}.{field}")
    return {field: value[field] for field in fields}


def validate_taxonomy_identity(
    buggy_bucket_ids: Any,
    clean_family_definitions: Any,
) -> None:
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
    normalized: list[Mapping[str, Any]] = []
    for index, definition in enumerate(clean_family_definitions):
        normalized.append(_require_exact_fields(definition, family_fields, f"clean_family_definitions[{index}]"))
    ids = [definition["family_id"] for definition in normalized]
    unknown_families = [item for item in ids if item not in CLEAN_STRESS_FAMILY_IDS]
    if unknown_families:
        _fail(ReasonCode.UNKNOWN_CLEAN_FAMILY, "clean_family_definitions", "unknown clean family")
    missing_families = [item for item in CLEAN_STRESS_FAMILY_IDS if item not in ids]
    if missing_families:
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
        {
            "family_id": family_id,
            "order": index,
            "adjacent_buggy_bucket_id": CLEAN_FAMILY_TO_ADJACENT_BUCKET[family_id],
        }
        for index, family_id in enumerate(CLEAN_STRESS_FAMILY_IDS, start=1)
    ]


def validate_candidate_cohort(
    buggy_candidates: Any,
    clean_candidates: Any,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if type(buggy_candidates) is not list or type(clean_candidates) is not list:
        _fail(ReasonCode.WRONG_TYPE, "candidates", "buggy and clean candidates must be lists")
    buggy = [
        validate_candidate_metadata(item, cohort_kind="buggy", path=f"buggy_candidates[{index}]")
        for index, item in enumerate(buggy_candidates)
    ]
    clean = [
        validate_candidate_metadata(item, cohort_kind="clean_stress", path=f"clean_candidates[{index}]")
        for index, item in enumerate(clean_candidates)
    ]
    all_ids = [item["variant_id"] for item in buggy + clean]
    if len(set(all_ids)) != len(all_ids):
        _fail(ReasonCode.DUPLICATE_VARIANT_ID, "variant_ids", "candidate IDs must be globally unique")
    buggy_counts = Counter(item["primary_bucket"] for item in buggy)
    if len(buggy) < 10 or len(buggy) > 20:
        _fail(ReasonCode.BUGGY_TOTAL_COUNT, "buggy_candidates", "buggy total must be 10-20")
    for bucket in BUGGY_BUCKET_IDS:
        count = buggy_counts[bucket]
        if count < 2 or count > 4:
            _fail(ReasonCode.BUGGY_BUCKET_COUNT, f"buggy_counts.{bucket}", "each buggy bucket requires 2-4 candidates")
    clean_counts = Counter(item["clean_stress_family_id"] for item in clean)
    if len(clean) < 5 or len(clean) > 10:
        _fail(ReasonCode.CLEAN_TOTAL_COUNT, "clean_candidates", "clean total must be 5-10")
    for family_id in CLEAN_STRESS_FAMILY_IDS:
        count = clean_counts[family_id]
        if count < 1 or count > 2:
            _fail(ReasonCode.CLEAN_FAMILY_COUNT, f"clean_counts.{family_id}", "each clean family requires 1-2 candidates")
    expected_buggy = sorted(
        buggy,
        key=lambda item: (BUGGY_BUCKET_IDS.index(item["primary_bucket"]), item["variant_id"]),
    )
    expected_clean = sorted(
        clean,
        key=lambda item: (
            CLEAN_STRESS_FAMILY_IDS.index(item["clean_stress_family_id"]),
            item["variant_id"],
        ),
    )
    if [item["variant_id"] for item in buggy] != [item["variant_id"] for item in expected_buggy]:
        _fail(ReasonCode.REORDERED_VARIANT_ID, "buggy_candidates", "buggy candidates must use bucket-major then ID order")
    if [item["variant_id"] for item in clean] != [item["variant_id"] for item in expected_clean]:
        _fail(ReasonCode.REORDERED_VARIANT_ID, "clean_candidates", "clean candidates must use family-major then ID order")
    return buggy, clean


_NON_OUTCOME_BASIS = (
    "Derived only from reviewed legacy metadata, relative source/patch identity, "
    "and deterministic case/oracle semantics."
)


COVERAGE_GAP_REGISTRY: tuple[CoverageGapEntry, ...] = (
    CoverageGapEntry(
        "buggy.boundary_precision",
        "buggy",
        "boundary_precision",
        1,
        ("P1B-BUG-001", "P1B-BUG-002", "P1B-BUG-003", "P1B-BUG-004"),
        "Legacy support covers two inclusive thresholds, one valid upper bound, and half-up monetary rounding across shipping, discounts, and cart helpers.",
        ("spec_rule", "causal_mechanism", "target_function_set", "trigger_shape", "oracle_outcome_vector", "normalized_patch_operation"),
        "Coverage is concentrated in single-function scalar boundary comparisons or rounding operations with direct deterministic counterexamples.",
        "Future eligible shapes must add materially different boundary semantics or interaction structure without cloning the existing comparisons, literals, or rounding patch.",
        ("p1b/dataset.py#P1B-BUG-001..004", "p1b/artifacts/real_diff/patches/P1B-BUG-001.patch..P1B-BUG-004.patch", "p1b/execution.py#boundary.*"),
        _NON_OUTCOME_BASIS,
    ),
    CoverageGapEntry(
        "buggy.missing_optional_input",
        "buggy",
        "missing_optional_input",
        2,
        ("P1B-BUG-005", "P1B-BUG-006", "P1B-BUG-007", "P1B-BUG-008"),
        "Legacy support covers absent coupon, address region, item collection, and reservation field inputs in four target helpers.",
        ("optional_absence_shape", "causal_mechanism", "target_function_set", "exception_or_default_oracle", "normalized_patch_operation"),
        "Existing shapes are localized absent value/key/collection normalization cases, primarily exposed by direct exception or default-value oracles.",
        "Future eligible shapes must exercise a materially different optional-input contract, target set, observable behavior, or interaction depth rather than renaming an absent field.",
        ("p1b/dataset.py#P1B-BUG-005..008", "p1b/artifacts/real_diff/patches/P1B-BUG-005.patch..P1B-BUG-008.patch", "p1b/execution.py#null_missing.*"),
        _NON_OUTCOME_BASIS,
    ),
    CoverageGapEntry(
        "buggy.config_normalization",
        "buggy",
        "config_normalization",
        3,
        ("P1B-BUG-009", "P1B-BUG-010", "P1B-BUG-011", "P1B-BUG-012"),
        "Legacy support covers stale scalar fallback, conservative flag default, region alias lookup, and string-to-number override parsing.",
        ("config_representation", "default_semantics", "alias_or_type_normalization", "target_function_set", "oracle_outcome_vector"),
        "Existing shapes cover four direct lookup/default/normalization operations but not every materially distinct representation or multi-setting interaction.",
        "Future eligible shapes must add a distinct configuration equivalence, normalization, or default mechanism with independent oracle semantics and no clone of the four legacy patches.",
        ("p1b/dataset.py#P1B-BUG-009..012", "p1b/artifacts/real_diff/patches/P1B-BUG-009.patch..P1B-BUG-012.patch", "p1b/execution.py#config.*"),
        _NON_OUTCOME_BASIS,
    ),
    CoverageGapEntry(
        "buggy.state_sequence",
        "buggy",
        "state_sequence",
        4,
        ("P1B-BUG-013", "P1B-BUG-014", "P1B-BUG-015", "P1B-BUG-016"),
        "Legacy support covers reversal, repeat idempotence, cart-inventory release synchronization, and stale quote state sequences.",
        ("sequence_shape", "state_invariant", "interaction_depth", "target_function_set", "observable_behavior"),
        "Existing sequences span single-object and cross-helper state, but remain four fixed reserve/coupon/sync/quote interaction forms.",
        "Future eligible shapes must introduce a materially different valid state model, ordering mechanism, or invariant oracle without replaying the fixed legacy sequences.",
        ("p1b/dataset.py#P1B-BUG-013..016", "p1b/artifacts/real_diff/patches/P1B-BUG-013.patch..P1B-BUG-016.patch", "p1b/execution.py#state.*"),
        _NON_OUTCOME_BASIS,
    ),
    CoverageGapEntry(
        "buggy.spec_semantics",
        "buggy",
        "spec_semantics",
        5,
        ("P1B-BUG-017", "P1B-BUG-018", "P1B-BUG-019", "P1B-BUG-020"),
        "Legacy support covers calculation order, cheapest-item selection, digital-shipping exemption, and preorder reservation exception rules.",
        ("spec_rule", "causal_mechanism", "selection_or_exception_shape", "target_function_set", "oracle_outcome_vector"),
        "Existing shapes instantiate one ordering rule, one selection rule, and two explicit exception rules in the current checkout specification.",
        "Future eligible shapes must cover materially distinct specification semantics and oracle behavior without changing only products, regions, prose, or family labels.",
        ("p1b/dataset.py#P1B-BUG-017..020", "p1b/artifacts/real_diff/patches/P1B-BUG-017.patch..P1B-BUG-020.patch", "p1b/execution.py#spec.*"),
        _NON_OUTCOME_BASIS,
    ),
    CoverageGapEntry(
        "clean_stress.boundary_adjacent_valid_behavior",
        "clean_stress",
        "boundary_adjacent_valid_behavior",
        6,
        ("P1B-CLEAN-021",),
        "One benign shipping-threshold variable extraction preserves below/at/above threshold behavior verified by boundary-vector oracles.",
        ("clean_stress_mechanism", "boundary_rule", "benign_patch_operation", "no_bug_oracle_vector"),
        "Legacy clean support contains one local refactor adjacent to an inclusive shipping threshold.",
        "Future clean stress must preserve a materially different valid boundary behavior and benign provenance rather than repeat the same threshold or variable extraction.",
        ("p1b/dataset.py#P1B-CLEAN-021", "p1b/artifacts/real_diff/patches/P1B-CLEAN-021.patch", "p1b/execution.py#property.free_shipping_boundary_vector"),
        _NON_OUTCOME_BASIS,
    ),
    CoverageGapEntry(
        "clean_stress.optional_input_valid_absence",
        "clean_stress",
        "optional_input_valid_absence",
        7,
        ("P1B-CLEAN-022",),
        "One benign coupon-normalization naming refactor preserves None, empty, and absent-coupon no-op semantics.",
        ("clean_stress_mechanism", "optional_absence_shape", "benign_patch_operation", "no_bug_oracle_vector"),
        "Legacy clean support contains one coupon-specific optional-absence shape and local naming change.",
        "Future clean stress must preserve a different reviewed optional-absence contract with distinct observable evidence and no copied coupon normalization patch.",
        ("p1b/dataset.py#P1B-CLEAN-022", "p1b/artifacts/real_diff/patches/P1B-CLEAN-022.patch", "p1b/execution.py#null_missing.coupon_none_noop"),
        _NON_OUTCOME_BASIS,
    ),
    CoverageGapEntry(
        "clean_stress.config_equivalent_normalization",
        "clean_stress",
        "config_equivalent_normalization",
        8,
        ("P1B-CLEAN-023",),
        "One benign feature-flag lookup simplification preserves equivalence between an absent flag and explicit false.",
        ("clean_stress_mechanism", "config_equivalence", "benign_patch_operation", "no_bug_oracle_vector"),
        "Legacy clean support contains one conservative boolean-default equivalence shape.",
        "Future clean stress must preserve a materially different configuration representation or normalization equivalence and remain behavior-preserving.",
        ("p1b/dataset.py#P1B-CLEAN-023", "p1b/artifacts/real_diff/patches/P1B-CLEAN-023.patch", "p1b/execution.py#config.missing_feature_flag_no_stacking"),
        _NON_OUTCOME_BASIS,
    ),
    CoverageGapEntry(
        "clean_stress.valid_state_sequence",
        "clean_stress",
        "valid_state_sequence",
        9,
        ("P1B-CLEAN-024",),
        "One benign reservation-cancellation variable extraction preserves the reserve/cancel/reserve invariant.",
        ("clean_stress_mechanism", "valid_sequence_shape", "state_invariant", "benign_patch_operation", "no_bug_oracle_vector"),
        "Legacy clean support contains one reservation reversal sequence with a local variable extraction.",
        "Future clean stress must preserve a materially different valid reorder, repeat, idempotent, or no-op transition with a distinct invariant oracle.",
        ("p1b/dataset.py#P1B-CLEAN-024", "p1b/artifacts/real_diff/patches/P1B-CLEAN-024.patch", "p1b/execution.py#state.reserve_then_cancel"),
        _NON_OUTCOME_BASIS,
    ),
    CoverageGapEntry(
        "clean_stress.nonintuitive_spec_conformance",
        "clean_stress",
        "nonintuitive_spec_conformance",
        10,
        ("P1B-CLEAN-025",),
        "One benign tax variable extraction preserves discount-before-tax and half-up final-total semantics.",
        ("clean_stress_mechanism", "spec_rule", "intermediate_signal", "benign_patch_operation", "no_bug_oracle_vector"),
        "Legacy clean support contains one calculation-order and rounding interaction whose intermediate values may look surprising.",
        "Future clean stress must preserve a different explicit but nonintuitive specification rule with distinct benign provenance and deterministic no-bug evidence.",
        ("p1b/dataset.py#P1B-CLEAN-025", "p1b/artifacts/real_diff/patches/P1B-CLEAN-025.patch", "p1b/execution.py#spec.discount_before_tax"),
        _NON_OUTCOME_BASIS,
    ),
)


_REGISTRY_FIELD_IDS = tuple(CoverageGapEntry.__dataclass_fields__)
_EXPECTED_REGISTRY_IDS = tuple(
    [f"buggy.{bucket}" for bucket in BUGGY_BUCKET_IDS]
    + [f"clean_stress.{family_id}" for family_id in CLEAN_STRESS_FAMILY_IDS]
)


def _registry_entry_from_value(value: Any, index: int) -> CoverageGapEntry:
    if isinstance(value, CoverageGapEntry):
        return value
    mapping = _require_exact_fields(value, _REGISTRY_FIELD_IDS, f"registry[{index}]")
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
            source_basis=tuple(mapping["source_basis"]),
            explicit_non_outcome_basis=mapping["explicit_non_outcome_basis"],
        )
    except (KeyError, TypeError) as exc:
        _fail(ReasonCode.WRONG_TYPE, f"registry[{index}]", f"invalid registry field type: {type(exc).__name__}")
    raise AssertionError("unreachable")


def validate_coverage_gap_registry(registry: Sequence[Any] = COVERAGE_GAP_REGISTRY) -> tuple[CoverageGapEntry, ...]:
    if type(registry) not in {list, tuple}:
        _fail(ReasonCode.WRONG_TYPE, "registry", "expected a list or tuple")
    entries = tuple(_registry_entry_from_value(value, index) for index, value in enumerate(registry))
    ids = tuple(entry.gap_id for entry in entries)
    if ids != _EXPECTED_REGISTRY_IDS:
        _fail(ReasonCode.REGISTRY_IDENTITY_MISMATCH, "registry.gap_ids", "registry IDs are missing, unknown, duplicated, or reordered")
    for index, entry in enumerate(entries):
        path = f"registry[{index}]"
        if entry.stable_order != index + 1:
            _fail(ReasonCode.REGISTRY_IDENTITY_MISMATCH, f"{path}.stable_order", "stable order must be contiguous and exact")
        expected_kind = "buggy" if index < len(BUGGY_BUCKET_IDS) else "clean_stress"
        expected_taxonomy_id = (
            BUGGY_BUCKET_IDS[index]
            if expected_kind == "buggy"
            else CLEAN_STRESS_FAMILY_IDS[index - len(BUGGY_BUCKET_IDS)]
        )
        if entry.cohort_kind != expected_kind or entry.primary_bucket_or_clean_family_id != expected_taxonomy_id:
            _fail(ReasonCode.REGISTRY_IDENTITY_MISMATCH, path, "cohort/taxonomy identity mismatch")
        if not entry.legacy_support_ids or any(item not in LEGACY_VARIANT_IDS for item in entry.legacy_support_ids):
            _fail(ReasonCode.REGISTRY_LEGACY_SUPPORT_MISMATCH, f"{path}.legacy_support_ids", "support must reference only current legacy IDs")
        stable_support = tuple(item for item in LEGACY_VARIANT_IDS if item in entry.legacy_support_ids)
        if entry.legacy_support_ids != stable_support:
            _fail(ReasonCode.REGISTRY_LEGACY_SUPPORT_MISMATCH, f"{path}.legacy_support_ids", "legacy support IDs must use stable legacy order")
        if entry.explicit_non_outcome_basis != _NON_OUTCOME_BASIS:
            _fail(ReasonCode.REGISTRY_OUTCOME_LEAKAGE, f"{path}.explicit_non_outcome_basis", "non-outcome basis statement is not exact")
        for basis_index, basis in enumerate(entry.source_basis):
            if type(basis) is not str or not basis.startswith("p1b/"):
                _fail(ReasonCode.REGISTRY_SOURCE_BASIS_INVALID, f"{path}.source_basis[{basis_index}]", "source basis must be a repository-relative P1b reference")
            validate_portable_value(basis, f"{path}.source_basis[{basis_index}]")
        serialized = json.dumps(asdict(entry), ensure_ascii=False).lower()
        if any(term in serialized for term in _REGISTRY_OUTCOME_TERMS):
            _fail(ReasonCode.REGISTRY_OUTCOME_LEAKAGE, path, "registry text contains forbidden result material")
    return entries


def coverage_gap_registry_digest(registry: Sequence[Any] = COVERAGE_GAP_REGISTRY) -> str:
    entries = validate_coverage_gap_registry(registry)
    payload = [
        {field: getattr(entry, field) for field in _REGISTRY_FIELD_IDS}
        for entry in entries
    ]
    return canonical_digest(payload)
