from __future__ import annotations

import ast
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path

import pytest

from bug_cause_inference.p2a.adequacy import (
    ACTION_TEST_CATALOG_VERSION,
    ADAPTER_CONTRACT_VERSION,
    ANALYSIS_PHASE,
    BENCHMARK_ID,
    BUGGY_BUCKET_IDS,
    BUGGY_VARIANT_NAMESPACE,
    CLEAN_FAMILY_TO_ADJACENT_BUCKET,
    CLEAN_STRESS_FAMILY_IDS,
    CLEAN_VARIANT_NAMESPACE,
    COVERAGE_GAP_REGISTRY,
    DATASET_SCHEMA_VERSION,
    REPORT_SCHEMA_VERSION,
    AdequacyValidationError,
    ReasonCode,
    clean_family_definitions,
    coverage_gap_registry_digest,
    validate_candidate_cohort,
    validate_candidate_metadata,
    validate_coverage_gap_registry,
    validate_taxonomy_identity,
)


def _fingerprint(seed: str) -> dict[str, object]:
    return {
        "spec_rule": f"candidate rule {seed}",
        "causal_mechanism": f"candidate mechanism {seed}",
        "target_function_set": [f"checkout.{seed}.target"],
        "trigger_shape": f"candidate trigger {seed}",
        "observable_behavior": f"candidate observable {seed}",
        "oracle_outcome_vector": [f"candidate-oracle-{seed}:fail"],
        "normalized_patch_operation": f"replace candidate operation {seed}",
        "interaction_depth": "cross_function",
    }


def _nearest_fingerprint(seed: str) -> dict[str, object]:
    return {
        "spec_rule": f"legacy rule {seed}",
        "causal_mechanism": f"legacy mechanism {seed}",
        "target_function_set": [f"checkout.{seed}.legacy"],
        "trigger_shape": f"legacy trigger {seed}",
        "observable_behavior": f"legacy observable {seed}",
        "oracle_outcome_vector": [f"legacy-oracle-{seed}:fail"],
        "normalized_patch_operation": f"replace legacy operation {seed}",
        "interaction_depth": "single_function",
    }


def synthetic_not_admitted_bug_candidate(bucket: str, index: int) -> dict[str, object]:
    seed = f"{BUGGY_BUCKET_IDS.index(bucket) + 1}-{index}"
    return {
        "variant_id": f"P2A-BUG-SYNTHETIC-{BUGGY_BUCKET_IDS.index(bucket) + 1:02d}-{index:02d}",
        "cohort": "buggy_expansion",
        "domain": "checkout_pricing",
        "spec_area": f"synthetic spec area {seed}",
        "primary_bucket": bucket,
        "is_buggy": True,
        "cause_category": f"synthetic cause {seed}",
        "target_module": "checkout/synthetic.py",
        "target_functions": [f"checkout.synthetic.target_{seed}"],
        "trigger_shape": f"synthetic trigger {seed}",
        "expected_behavior": f"synthetic expected {seed}",
        "actual_behavior": f"synthetic actual {seed}",
        "oracle_ids": [f"synthetic.oracle.{seed}"],
        "action_test_catalog_ids": [f"synthetic.case.{seed}"],
        "action_mapping": "run_boundary_tests",
        "observable_signature": f"synthetic observable {seed}",
        "patch_semantic_fingerprint": f"synthetic patch {seed}",
        "changed_files": ["checkout/synthetic.py"],
        "changed_functions": [f"checkout.synthetic.target_{seed}"],
        "interaction_depth": "cross_function",
        "fix_intent_category": "synthetic_fix_intent",
        "difficulty": "synthetic",
        "nearest_legacy_or_admitted_variant_id": "P1B-BUG-001",
        "material_difference_dimensions": ["spec/mechanism", "target_function_set"],
        "diversity_rationale": "Synthetic fixture differs in reviewed rule and target dimensions.",
        "core_fingerprint": _fingerprint(seed),
        "nearest_reference_core_fingerprint": _nearest_fingerprint(seed),
    }


def synthetic_not_admitted_clean_candidate(family_id: str, index: int = 1) -> dict[str, object]:
    family_order = CLEAN_STRESS_FAMILY_IDS.index(family_id) + 1
    seed = f"clean-{family_order}-{index}"
    return {
        "variant_id": f"P2A-CLEAN-SYNTHETIC-{family_order:02d}-{index:02d}",
        "cohort": "clean_stress_expansion",
        "domain": "checkout_pricing",
        "spec_area": f"synthetic clean area {seed}",
        "primary_bucket": "clean_false_positive",
        "is_buggy": False,
        "clean_stress_family_id": family_id,
        "clean_stress_family_order": family_order,
        "adjacent_buggy_bucket_id": CLEAN_FAMILY_TO_ADJACENT_BUCKET[family_id],
        "stress_mechanism": f"synthetic clean stress {seed}",
        "confusing_signal": f"synthetic confusing signal {seed}",
        "expected_clean_behavior": f"synthetic clean behavior {seed}",
        "no_bug_oracle_ids": [f"synthetic.no_bug.{seed}"],
        "recommended_no_bug_evidence": f"synthetic no-bug evidence {seed}",
        "benign_diff_rationale": f"synthetic benign diff {seed}",
        "patch_semantic_fingerprint": f"synthetic benign patch {seed}",
        "changed_files": ["checkout/synthetic_clean.py"],
        "changed_functions": [f"checkout.synthetic_clean.touched_{seed}"],
        "interaction_depth": "cross_function",
        "nearest_legacy_or_admitted_clean_variant_id": "P1B-CLEAN-021",
        "material_difference_dimensions": ["spec/mechanism", "target_function_set"],
        "diversity_rationale": "Synthetic fixture differs in reviewed rule and touched-function dimensions.",
        "core_fingerprint": _fingerprint(seed),
        "nearest_reference_core_fingerprint": _nearest_fingerprint(seed),
    }


def synthetic_not_admitted_cohort() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    buggy = [
        synthetic_not_admitted_bug_candidate(bucket, index)
        for bucket in BUGGY_BUCKET_IDS
        for index in (1, 2)
    ]
    clean = [synthetic_not_admitted_clean_candidate(family_id) for family_id in CLEAN_STRESS_FAMILY_IDS]
    return buggy, clean


def _assert_reason(code: ReasonCode, callable_obj, *args, **kwargs) -> None:
    with pytest.raises(AdequacyValidationError) as exc_info:
        callable_obj(*args, **kwargs)
    assert exc_info.value.issue.code == code.value


def test_identity_constants_are_exact_pre_authoring_inputs():
    assert DATASET_SCHEMA_VERSION == "p2a_same_domain_dataset.v1"
    assert BENCHMARK_ID == "p2a_checkout_pricing_same_domain_expansion_v1"
    assert BUGGY_VARIANT_NAMESPACE == "P2A-BUG-*"
    assert CLEAN_VARIANT_NAMESPACE == "P2A-CLEAN-*"
    assert ADAPTER_CONTRACT_VERSION == "p2a_patch_grounded_adapter.v1"
    assert ACTION_TEST_CATALOG_VERSION == "p2a_action_test_catalog.v1"
    assert REPORT_SCHEMA_VERSION == "p2a_benchmark_evidence_expansion_report.v1"
    assert ANALYSIS_PHASE == "p2a_benchmark_evidence_expansion_report"


def test_exact_taxonomy_identity_accepts_only_controlling_order_and_mapping():
    validate_taxonomy_identity(list(BUGGY_BUCKET_IDS), clean_family_definitions())


@pytest.mark.parametrize(
    ("mutation", "reason"),
    [
        (lambda ids: ids[:-1], ReasonCode.MISSING_BUCKET),
        (lambda ids: [*ids[:-1], "unknown_bucket"], ReasonCode.UNKNOWN_BUCKET),
        (lambda ids: [ids[1], ids[0], *ids[2:]], ReasonCode.REORDERED_BUCKET),
    ],
)
def test_missing_unknown_or_reordered_buggy_bucket_is_rejected(mutation, reason):
    _assert_reason(reason, validate_taxonomy_identity, mutation(list(BUGGY_BUCKET_IDS)), clean_family_definitions())


@pytest.mark.parametrize("kind", ["missing", "unknown", "reordered", "wrong_mapping"])
def test_missing_unknown_reordered_or_mapped_clean_family_is_rejected(kind: str):
    definitions = clean_family_definitions()
    expected = {
        "missing": ReasonCode.MISSING_CLEAN_FAMILY,
        "unknown": ReasonCode.UNKNOWN_CLEAN_FAMILY,
        "reordered": ReasonCode.REORDERED_CLEAN_FAMILY,
        "wrong_mapping": ReasonCode.WRONG_ADJACENT_BUCKET,
    }[kind]
    if kind == "missing":
        definitions.pop()
    elif kind == "unknown":
        definitions[-1]["family_id"] = "unknown_family"
    elif kind == "reordered":
        definitions[0], definitions[1] = definitions[1], definitions[0]
    else:
        definitions[0]["adjacent_buggy_bucket_id"] = "spec_semantics"
    _assert_reason(expected, validate_taxonomy_identity, list(BUGGY_BUCKET_IDS), definitions)


def test_synthetic_not_admitted_metadata_and_count_envelope_are_valid():
    buggy, clean = synthetic_not_admitted_cohort()
    validated_buggy, validated_clean = validate_candidate_cohort(buggy, clean)
    assert len(validated_buggy) == 10
    assert len(validated_clean) == 5


@pytest.mark.parametrize(
    ("field", "reason"),
    [
        ("oracle_ids", ReasonCode.MISSING_FIELD),
        ("patch_semantic_fingerprint", ReasonCode.MISSING_FIELD),
        ("core_fingerprint", ReasonCode.MISSING_FIELD),
        ("diversity_rationale", ReasonCode.MISSING_FIELD),
    ],
)
def test_required_buggy_oracle_fingerprint_and_diversity_fields_are_enforced(field, reason):
    candidate = synthetic_not_admitted_bug_candidate(BUGGY_BUCKET_IDS[0], 1)
    candidate.pop(field)
    _assert_reason(reason, validate_candidate_metadata, candidate, cohort_kind="buggy")


def test_required_clean_no_bug_oracle_field_is_enforced():
    candidate = synthetic_not_admitted_clean_candidate(CLEAN_STRESS_FAMILY_IDS[0])
    candidate.pop("no_bug_oracle_ids")
    _assert_reason(
        ReasonCode.MISSING_FIELD,
        validate_candidate_metadata,
        candidate,
        cohort_kind="clean_stress",
    )


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("cause_category", "bug cause", ReasonCode.CLEAN_BUG_GROUND_TRUTH_FORBIDDEN),
        ("fault_location", "checkout.synthetic", ReasonCode.CLEAN_BUG_GROUND_TRUTH_FORBIDDEN),
        ("actual_behavior", "fault", ReasonCode.CLEAN_BUG_GROUND_TRUTH_FORBIDDEN),
        ("fix_intent_category", "fix", ReasonCode.CLEAN_BUG_GROUND_TRUTH_FORBIDDEN),
        ("unknown_metadata", "x", ReasonCode.UNKNOWN_FIELD),
        ("policy_trace", [], ReasonCode.POLICY_OUTCOME_FIELD_FORBIDDEN),
    ],
)
def test_clean_bug_ground_truth_unknown_and_policy_outcome_fields_are_rejected(field, value, reason):
    candidate = synthetic_not_admitted_clean_candidate(CLEAN_STRESS_FAMILY_IDS[0])
    candidate[field] = value
    _assert_reason(reason, validate_candidate_metadata, candidate, cohort_kind="clean_stress")


def test_policy_outcome_material_hidden_in_an_allowlisted_text_value_is_rejected():
    candidate = synthetic_not_admitted_bug_candidate(BUGGY_BUCKET_IDS[0], 1)
    candidate["diversity_rationale"] = "copied from selected_action evidence"
    _assert_reason(
        ReasonCode.POLICY_OUTCOME_FIELD_FORBIDDEN,
        validate_candidate_metadata,
        candidate,
        cohort_kind="buggy",
    )


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("primary_bucket", "boundary_precision", ReasonCode.PRIMARY_BUCKET_MISMATCH),
        ("is_buggy", True, ReasonCode.BUGGY_FLAG_MISMATCH),
        ("cohort", "buggy_expansion", ReasonCode.COHORT_MISMATCH),
        ("domain", "other_domain", ReasonCode.DOMAIN_MISMATCH),
        ("variant_id", "P2A-BUG-SYNTHETIC-X", ReasonCode.NAMESPACE_MISMATCH),
    ],
)
def test_clean_identity_contradictions_fail_closed(field, value, reason):
    candidate = synthetic_not_admitted_clean_candidate(CLEAN_STRESS_FAMILY_IDS[0])
    candidate[field] = value
    _assert_reason(reason, validate_candidate_metadata, candidate, cohort_kind="clean_stress")


def test_p1b_namespace_collision_and_duplicate_candidate_ids_are_rejected():
    candidate = synthetic_not_admitted_bug_candidate(BUGGY_BUCKET_IDS[0], 1)
    candidate["variant_id"] = "P1B-BUG-001"
    _assert_reason(ReasonCode.NAMESPACE_COLLISION, validate_candidate_metadata, candidate, cohort_kind="buggy")
    buggy, clean = synthetic_not_admitted_cohort()
    buggy[1]["variant_id"] = buggy[0]["variant_id"]
    _assert_reason(ReasonCode.DUPLICATE_VARIANT_ID, validate_candidate_cohort, buggy, clean)


def test_reordered_candidate_id_is_rejected():
    buggy, clean = synthetic_not_admitted_cohort()
    buggy[0], buggy[1] = buggy[1], buggy[0]
    _assert_reason(ReasonCode.REORDERED_VARIANT_ID, validate_candidate_cohort, buggy, clean)


@pytest.mark.parametrize("count", [1, 5])
def test_buggy_per_bucket_count_one_or_five_is_rejected(count: int):
    buggy, clean = synthetic_not_admitted_cohort()
    bucket = BUGGY_BUCKET_IDS[0]
    others = [item for item in buggy if item["primary_bucket"] != bucket]
    selected = [synthetic_not_admitted_bug_candidate(bucket, index) for index in range(1, count + 1)]
    if count == 1:
        others.append(synthetic_not_admitted_bug_candidate(BUGGY_BUCKET_IDS[1], 3))
    candidates = sorted(selected + others, key=lambda item: (BUGGY_BUCKET_IDS.index(item["primary_bucket"]), item["variant_id"]))
    _assert_reason(ReasonCode.BUGGY_BUCKET_COUNT, validate_candidate_cohort, candidates, clean)


@pytest.mark.parametrize("direction", ["under", "over"])
def test_buggy_total_under_or_over_is_rejected(direction: str):
    buggy, clean = synthetic_not_admitted_cohort()
    if direction == "under":
        buggy.pop()
    else:
        buggy = [
            synthetic_not_admitted_bug_candidate(bucket, index)
            for bucket in BUGGY_BUCKET_IDS
            for index in range(1, 6 if bucket == BUGGY_BUCKET_IDS[0] else 5)
        ]
    _assert_reason(ReasonCode.BUGGY_TOTAL_COUNT, validate_candidate_cohort, buggy, clean)


@pytest.mark.parametrize("count", [0, 3])
def test_clean_per_family_count_zero_or_three_is_rejected(count: int):
    buggy, clean = synthetic_not_admitted_cohort()
    family = CLEAN_STRESS_FAMILY_IDS[0]
    others = [item for item in clean if item["clean_stress_family_id"] != family]
    selected = [synthetic_not_admitted_clean_candidate(family, index) for index in range(1, count + 1)]
    if count == 0:
        others.append(synthetic_not_admitted_clean_candidate(CLEAN_STRESS_FAMILY_IDS[1], 2))
    candidates = sorted(selected + others, key=lambda item: (CLEAN_STRESS_FAMILY_IDS.index(item["clean_stress_family_id"]), item["variant_id"]))
    _assert_reason(ReasonCode.CLEAN_FAMILY_COUNT, validate_candidate_cohort, buggy, candidates)


@pytest.mark.parametrize("direction", ["under", "over"])
def test_clean_total_under_or_over_is_rejected(direction: str):
    buggy, clean = synthetic_not_admitted_cohort()
    if direction == "under":
        clean.pop()
    else:
        clean = [
            synthetic_not_admitted_clean_candidate(family, index)
            for family in CLEAN_STRESS_FAMILY_IDS
            for index in (1, 2)
        ]
        clean.append(synthetic_not_admitted_clean_candidate(CLEAN_STRESS_FAMILY_IDS[0], 3))
    _assert_reason(ReasonCode.CLEAN_TOTAL_COUNT, validate_candidate_cohort, buggy, clean)


def test_one_claimed_material_dimension_is_rejected():
    candidate = synthetic_not_admitted_bug_candidate(BUGGY_BUCKET_IDS[0], 1)
    candidate["material_difference_dimensions"] = ["spec/mechanism"]
    _assert_reason(ReasonCode.INSUFFICIENT_MATERIAL_DIFFERENCE, validate_candidate_metadata, candidate, cohort_kind="buggy")


def test_two_noncore_differences_with_zero_required_core_dimension_are_rejected():
    candidate = synthetic_not_admitted_bug_candidate(BUGGY_BUCKET_IDS[0], 1)
    nearest = deepcopy(candidate["core_fingerprint"])
    nearest["trigger_shape"] = "different legacy trigger"
    nearest["normalized_patch_operation"] = "different legacy patch"
    candidate["nearest_reference_core_fingerprint"] = nearest
    candidate["material_difference_dimensions"] = ["trigger_shape", "normalized_patch_operation"]
    _assert_reason(ReasonCode.MISSING_CORE_MATERIAL_DIFFERENCE, validate_candidate_metadata, candidate, cohort_kind="buggy")


@pytest.mark.parametrize(
    ("dimensions", "reason"),
    [
        (["identifier_or_literal", "prose"], ReasonCode.RENAME_OR_LITERAL_ONLY),
        (["bucket_or_family_label"], ReasonCode.FAMILY_LABEL_ONLY_DUPLICATE),
        (["quota_padding", "spec/mechanism"], ReasonCode.QUOTA_PADDING),
    ],
)
def test_rename_literal_family_label_and_quota_padding_are_rejected(dimensions, reason):
    candidate = synthetic_not_admitted_bug_candidate(BUGGY_BUCKET_IDS[0], 1)
    candidate["material_difference_dimensions"] = dimensions
    _assert_reason(reason, validate_candidate_metadata, candidate, cohort_kind="buggy")


def test_same_normalized_patch_is_rejected_with_specific_reason():
    candidate = synthetic_not_admitted_bug_candidate(BUGGY_BUCKET_IDS[0], 1)
    candidate["nearest_reference_core_fingerprint"]["normalized_patch_operation"] = candidate["core_fingerprint"]["normalized_patch_operation"]
    _assert_reason(ReasonCode.SAME_NORMALIZED_PATCH, validate_candidate_metadata, candidate, cohort_kind="buggy")


def test_same_target_trigger_oracle_is_rejected_with_specific_reason():
    candidate = synthetic_not_admitted_bug_candidate(BUGGY_BUCKET_IDS[0], 1)
    nearest = candidate["nearest_reference_core_fingerprint"]
    current = candidate["core_fingerprint"]
    for field in ("target_function_set", "trigger_shape", "oracle_outcome_vector"):
        nearest[field] = deepcopy(current[field])
    _assert_reason(ReasonCode.SAME_TARGET_TRIGGER_ORACLE, validate_candidate_metadata, candidate, cohort_kind="buggy")


def test_coverage_gap_registry_has_stable_ten_entry_identity_and_legacy_basis():
    entries = validate_coverage_gap_registry()
    assert len(entries) == 10
    assert [entry.stable_order for entry in entries] == list(range(1, 11))
    assert [entry.primary_bucket_or_clean_family_id for entry in entries[:5]] == list(BUGGY_BUCKET_IDS)
    assert [entry.primary_bucket_or_clean_family_id for entry in entries[5:]] == list(CLEAN_STRESS_FAMILY_IDS)
    assert len(coverage_gap_registry_digest()) == 64
    assert all(basis.startswith("p1b/") for entry in entries for basis in entry.source_basis)


@pytest.mark.parametrize("mutation", ["missing", "unknown", "reordered"])
def test_registry_missing_unknown_or_reordered_identity_is_rejected(mutation: str):
    registry = [asdict(entry) for entry in COVERAGE_GAP_REGISTRY]
    if mutation == "missing":
        registry.pop()
    elif mutation == "unknown":
        registry[-1]["gap_id"] = "clean_stress.unknown"
    else:
        registry[0], registry[1] = registry[1], registry[0]
    _assert_reason(ReasonCode.REGISTRY_IDENTITY_MISMATCH, validate_coverage_gap_registry, registry)


def test_registry_unknown_policy_field_and_allowed_field_outcome_text_are_rejected():
    registry = [asdict(entry) for entry in COVERAGE_GAP_REGISTRY]
    registry[0]["policy_trace"] = []
    _assert_reason(ReasonCode.POLICY_OUTCOME_FIELD_FORBIDDEN, validate_coverage_gap_registry, registry)
    registry = [asdict(entry) for entry in COVERAGE_GAP_REGISTRY]
    registry[0]["gap_statement"] = "posterior-shaped result material"
    _assert_reason(ReasonCode.REGISTRY_OUTCOME_LEAKAGE, validate_coverage_gap_registry, registry)


def test_registry_absolute_source_basis_is_rejected():
    registry = [asdict(entry) for entry in COVERAGE_GAP_REGISTRY]
    registry[0]["source_basis"] = ("C:\\Users\\name\\legacy.py",)
    _assert_reason(ReasonCode.REGISTRY_SOURCE_BASIS_INVALID, validate_coverage_gap_registry, registry)


def test_adequacy_and_freeze_modules_have_no_forbidden_evaluation_dependency():
    root = Path(__file__).resolve().parents[1] / "src" / "bug_cause_inference" / "p2a"
    forbidden = (
        "p1b.policies",
        "p1b.evaluation",
        "p1c.evaluation",
        "p1d",
        "p2a.evaluation",
        "p2a.reports",
    )
    for filename in ("adequacy.py", "freeze.py"):
        tree = ast.parse((root / filename).read_text(encoding="utf-8"))
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
        assert not any(token in imported for imported in imports for token in forbidden)
