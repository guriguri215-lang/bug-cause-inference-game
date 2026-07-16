from __future__ import annotations

import hashlib
from copy import deepcopy

import pytest

from bug_cause_inference.p2a.adequacy import (
    ACTION_TEST_CATALOG_VERSION,
    ADAPTER_CONTRACT_VERSION,
    BENCHMARK_ID,
    BUGGY_BUCKET_IDS,
    CLEAN_FAMILY_TO_ADJACENT_BUCKET,
    CLEAN_STRESS_FAMILY_IDS,
    COVERAGE_GAP_REGISTRY_VERSION,
    DATASET_SCHEMA_VERSION,
    AdequacyValidationError,
    ReasonCode,
    clean_family_definitions,
    coverage_gap_registry_digest,
)
from bug_cause_inference.p2a.freeze import (
    ARTIFACT_MANIFEST_SCHEMA_VERSION,
    FREEZE_DRAFT_SCHEMA_VERSION,
    METRIC_IDENTITY_VERSION,
    POLICY_IDENTITY_VERSION,
    SERIALIZER_IDENTITY_VERSION,
    SETTINGS_IDENTITY_VERSION,
    candidate_manifest_digest,
    validate_freeze_draft,
)


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _fingerprint(seed: str, *, legacy: bool = False) -> dict[str, object]:
    prefix = "legacy" if legacy else "candidate"
    return {
        "spec_rule": f"{prefix} rule {seed}",
        "causal_mechanism": f"{prefix} mechanism {seed}",
        "target_function_set": [f"checkout.{prefix}_{seed}.target"],
        "trigger_shape": f"{prefix} trigger {seed}",
        "observable_behavior": f"{prefix} observable {seed}",
        "oracle_outcome_vector": [f"{prefix}-oracle-{seed}:pass"],
        "normalized_patch_operation": f"replace {prefix} operation {seed}",
        "interaction_depth": "single_function" if legacy else "cross_function",
    }


def _synthetic_not_admitted_bug(bucket: str, index: int) -> dict[str, object]:
    bucket_order = BUGGY_BUCKET_IDS.index(bucket) + 1
    seed = f"bug-{bucket_order}-{index}"
    return {
        "variant_id": f"P2A-BUG-SYNTHETIC-{bucket_order:02d}-{index:02d}",
        "cohort": "buggy_expansion",
        "domain": "checkout_pricing",
        "spec_area": f"synthetic area {seed}",
        "primary_bucket": bucket,
        "is_buggy": True,
        "cause_category": f"synthetic cause {seed}",
        "target_module": "checkout/candidate_fixture.py",
        "target_functions": [f"checkout.candidate_fixture.target_{seed}"],
        "trigger_shape": f"synthetic trigger {seed}",
        "expected_behavior": f"synthetic expected {seed}",
        "actual_behavior": f"synthetic actual {seed}",
        "oracle_ids": [f"synthetic.oracle.{seed}"],
        "action_test_catalog_ids": [f"synthetic.case.{seed}"],
        "action_mapping": "run_boundary_tests",
        "observable_signature": f"synthetic signal {seed}",
        "patch_semantic_fingerprint": f"synthetic patch {seed}",
        "changed_files": ["checkout/candidate_fixture.py"],
        "changed_functions": [f"checkout.candidate_fixture.target_{seed}"],
        "interaction_depth": "cross_function",
        "fix_intent_category": "synthetic_fix",
        "difficulty": "synthetic",
        "nearest_legacy_or_admitted_variant_id": "P1B-BUG-001",
        "material_difference_dimensions": ["spec/mechanism", "target_function_set"],
        "diversity_rationale": f"synthetic rule and target differences {seed}",
        "core_fingerprint": _fingerprint(seed),
        "nearest_reference_core_fingerprint": _fingerprint(seed, legacy=True),
    }


def _synthetic_not_admitted_clean(family_id: str) -> dict[str, object]:
    family_order = CLEAN_STRESS_FAMILY_IDS.index(family_id) + 1
    seed = f"clean-{family_order}"
    return {
        "variant_id": f"P2A-CLEAN-SYNTHETIC-{family_order:02d}-01",
        "cohort": "clean_stress_expansion",
        "domain": "checkout_pricing",
        "spec_area": f"synthetic clean area {seed}",
        "primary_bucket": "clean_false_positive",
        "is_buggy": False,
        "clean_stress_family_id": family_id,
        "clean_stress_family_order": family_order,
        "adjacent_buggy_bucket_id": CLEAN_FAMILY_TO_ADJACENT_BUCKET[family_id],
        "stress_mechanism": f"synthetic stress {seed}",
        "confusing_signal": f"synthetic signal {seed}",
        "expected_clean_behavior": f"synthetic clean behavior {seed}",
        "no_bug_oracle_ids": [f"synthetic.no_bug.{seed}"],
        "recommended_no_bug_evidence": f"synthetic no-bug evidence {seed}",
        "benign_diff_rationale": f"synthetic benign diff {seed}",
        "patch_semantic_fingerprint": f"synthetic benign patch {seed}",
        "changed_files": ["checkout/clean_fixture.py"],
        "changed_functions": [f"checkout.clean_fixture.touched_{seed}"],
        "interaction_depth": "cross_function",
        "nearest_legacy_or_admitted_clean_variant_id": "P1B-CLEAN-021",
        "material_difference_dimensions": ["spec/mechanism", "target_function_set"],
        "diversity_rationale": f"synthetic clean rule and target differences {seed}",
        "core_fingerprint": _fingerprint(seed),
        "nearest_reference_core_fingerprint": _fingerprint(seed, legacy=True),
    }


def _synthetic_not_admitted_candidates() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    buggy = [
        _synthetic_not_admitted_bug(bucket, index)
        for bucket in BUGGY_BUCKET_IDS
        for index in (1, 2)
    ]
    clean = [_synthetic_not_admitted_clean(family_id) for family_id in CLEAN_STRESS_FAMILY_IDS]
    return buggy, clean


def _draft() -> dict[str, object]:
    buggy, clean = _synthetic_not_admitted_candidates()
    manifest_digest = candidate_manifest_digest(buggy, clean)
    return {
        "draft_schema_version": FREEZE_DRAFT_SCHEMA_VERSION,
        "dataset_identity": {
            "schema_version": DATASET_SCHEMA_VERSION,
            "benchmark_id": BENCHMARK_ID,
            "candidate_manifest_digest": manifest_digest,
        },
        "artifact_identity": {
            "schema_version": ARTIFACT_MANIFEST_SCHEMA_VERSION,
            "artifact_manifest_digest": _digest("synthetic artifact"),
        },
        "adapter_identity": {
            "contract_version": ADAPTER_CONTRACT_VERSION,
            "digest": _digest("synthetic adapter"),
        },
        "catalog_identity": {
            "catalog_version": ACTION_TEST_CATALOG_VERSION,
            "digest": _digest("synthetic catalog"),
        },
        "policy_identity": {
            "identity_version": POLICY_IDENTITY_VERSION,
            "digest": _digest("synthetic policy registry"),
        },
        "settings_identity": {
            "identity_version": SETTINGS_IDENTITY_VERSION,
            "digest": _digest("synthetic settings"),
        },
        "metric_identity": {
            "identity_version": METRIC_IDENTITY_VERSION,
            "digest": _digest("synthetic metric"),
        },
        "serializer_identity": {
            "identity_version": SERIALIZER_IDENTITY_VERSION,
            "digest": _digest("synthetic serializer"),
        },
        "coverage_registry_identity": {
            "registry_version": COVERAGE_GAP_REGISTRY_VERSION,
            "registry_digest": coverage_gap_registry_digest(),
        },
        "freeze_timestamp": "2000-01-01T00:00:00Z",
        "buggy_bucket_ids": list(BUGGY_BUCKET_IDS),
        "clean_family_definitions": clean_family_definitions(),
        "variant_ids": [item["variant_id"] for item in buggy + clean],
        "buggy_candidates": buggy,
        "clean_candidates": clean,
    }


def _assert_reason(code: ReasonCode, draft: dict[str, object]) -> None:
    with pytest.raises(AdequacyValidationError) as exc_info:
        validate_freeze_draft(draft)
    assert exc_info.value.issue.code == code.value


def test_synthetic_draft_validation_is_deterministic_and_never_claims_official_status():
    first = validate_freeze_draft(_draft())
    second = validate_freeze_draft(deepcopy(_draft()))
    assert first == second
    assert first.status == "draft_valid"
    assert first.variant_count == 15
    assert first.buggy_count == 10
    assert first.clean_count == 5
    assert len(first.draft_digest) == 64
    assert "frozen" not in first.status
    assert "accepted" not in first.status
    assert "valid_for_evaluation" not in first.status


def test_mapping_key_insertion_order_does_not_change_canonical_draft_identity():
    original = _draft()
    reversed_top = {key: original[key] for key in reversed(original)}
    reversed_top["dataset_identity"] = {
        key: original["dataset_identity"][key]
        for key in reversed(original["dataset_identity"])
    }
    assert validate_freeze_draft(original).draft_digest == validate_freeze_draft(reversed_top).draft_digest


def test_list_order_mutation_is_rejected_instead_of_normalized():
    draft = _draft()
    draft["variant_ids"][0], draft["variant_ids"][1] = draft["variant_ids"][1], draft["variant_ids"][0]
    _assert_reason(ReasonCode.REORDERED_VARIANT_ID, draft)


def test_list_container_type_and_scalar_type_mutations_are_rejected():
    draft = _draft()
    draft["buggy_bucket_ids"] = tuple(draft["buggy_bucket_ids"])
    _assert_reason(ReasonCode.WRONG_TYPE, draft)
    draft = _draft()
    draft["buggy_candidates"][0]["is_buggy"] = 1
    _assert_reason(ReasonCode.WRONG_TYPE, draft)


@pytest.mark.parametrize(
    "path_value",
    [
        "artifact=C:\\Users\\name\\tree\\cart.py",
        "artifact=\\\\server\\share\\tree\\cart.py",
        "artifact=file:///C:/Users/name/tree/cart.py",
        "artifact=file:///home/name/tree/cart.py",
        "artifact=/home/name/tree/cart.py",
    ],
)
def test_nested_drive_unc_file_uri_and_posix_absolute_paths_are_rejected(path_value: str):
    draft = _draft()
    draft["buggy_candidates"][0]["core_fingerprint"]["observable_behavior"] = path_value
    _assert_reason(ReasonCode.ABSOLUTE_PATH_FORBIDDEN, draft)


@pytest.mark.parametrize(
    "path_value",
    [
        "tmp/generated/checkout/cart.py",
        ".cache/p2a/tree.py",
        "build/__pycache__/tree.py",
    ],
)
def test_nested_cache_temp_and_generated_tree_paths_are_rejected(path_value: str):
    draft = _draft()
    draft["clean_candidates"][0]["changed_files"] = [path_value]
    _assert_reason(ReasonCode.LOCAL_TEMP_PATH_FORBIDDEN, draft)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_values_are_rejected_from_nested_canonical_input(value: float):
    draft = _draft()
    draft["buggy_candidates"][0]["core_fingerprint"]["oracle_outcome_vector"] = [value]
    _assert_reason(ReasonCode.NON_FINITE_NUMBER, draft)


def test_repository_relative_provenance_paths_are_allowed():
    result = validate_freeze_draft(_draft())
    assert result.status == "draft_valid"


@pytest.mark.parametrize(
    ("identity_name", "version_field"),
    [
        ("dataset_identity", "schema_version"),
        ("artifact_identity", "schema_version"),
        ("adapter_identity", "contract_version"),
        ("catalog_identity", "catalog_version"),
        ("policy_identity", "identity_version"),
        ("settings_identity", "identity_version"),
        ("metric_identity", "identity_version"),
        ("serializer_identity", "identity_version"),
        ("coverage_registry_identity", "registry_version"),
    ],
)
def test_wrong_identity_versions_are_rejected(identity_name: str, version_field: str):
    draft = _draft()
    draft[identity_name][version_field] = "wrong.v0"
    _assert_reason(ReasonCode.WRONG_VERSION, draft)


@pytest.mark.parametrize(
    ("identity_name", "digest_field"),
    [
        ("dataset_identity", "candidate_manifest_digest"),
        ("artifact_identity", "artifact_manifest_digest"),
        ("adapter_identity", "digest"),
        ("catalog_identity", "digest"),
        ("policy_identity", "digest"),
        ("settings_identity", "digest"),
        ("metric_identity", "digest"),
        ("serializer_identity", "digest"),
        ("coverage_registry_identity", "registry_digest"),
    ],
)
def test_missing_identity_digests_are_rejected(identity_name: str, digest_field: str):
    draft = _draft()
    draft[identity_name][digest_field] = ""
    _assert_reason(ReasonCode.MISSING_DIGEST, draft)


def test_wrong_candidate_manifest_and_registry_digests_are_rejected():
    draft = _draft()
    draft["dataset_identity"]["candidate_manifest_digest"] = _digest("wrong manifest")
    _assert_reason(ReasonCode.WRONG_DIGEST, draft)
    draft = _draft()
    draft["coverage_registry_identity"]["registry_digest"] = _digest("wrong registry")
    _assert_reason(ReasonCode.WRONG_DIGEST, draft)


@pytest.mark.parametrize("field", ["policy_trace", "posterior", "selected_action", "matrix_cell", "worst_bucket", "clean_false_positive_outcome"])
def test_policy_outcome_shaped_top_level_fields_are_rejected_by_allowlist(field: str):
    draft = _draft()
    draft[field] = "forbidden"
    _assert_reason(ReasonCode.POLICY_OUTCOME_FIELD_FORBIDDEN, draft)


def test_policy_outcome_shaped_candidate_metadata_is_rejected_by_allowlist():
    draft = _draft()
    draft["buggy_candidates"][0]["posterior"] = 0.9
    _assert_reason(ReasonCode.POLICY_OUTCOME_FIELD_FORBIDDEN, draft)


@pytest.mark.parametrize("timestamp", ["", "2000-01-01", "2000-01-01T00:00:00+00:00", "2000-13-01T00:00:00Z"])
def test_freeze_timestamp_is_caller_supplied_canonical_utc_only(timestamp: str):
    draft = _draft()
    draft["freeze_timestamp"] = timestamp
    _assert_reason(ReasonCode.WRONG_IDENTITY, draft)


def test_unknown_nested_identity_field_is_not_silently_hashed():
    draft = _draft()
    draft["metric_identity"]["unknown"] = "not canonical"
    _assert_reason(ReasonCode.UNKNOWN_FIELD, draft)
