from __future__ import annotations

import ast
import inspect
import subprocess
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path

import pytest

from bug_cause_inference.p2a.adequacy import (
    ACTION_TEST_CATALOG_VERSION,
    ADAPTER_CONTRACT_VERSION,
    ANALYSIS_PHASE,
    APPROVED_ACTION_IDS,
    BENCHMARK_ID,
    BUGGY_BUCKET_IDS,
    BUGGY_VARIANT_NAMESPACE,
    CLEAN_FAMILY_TO_ADJACENT_BUCKET,
    CLEAN_STRESS_FAMILY_IDS,
    CLEAN_VARIANT_NAMESPACE,
    COVERAGE_GAP_REGISTRY,
    DATASET_SCHEMA_VERSION,
    REPORT_SCHEMA_VERSION,
    TRUSTED_REFERENCE_REGISTRY,
    TRUSTED_REFERENCE_REGISTRY_VERSION,
    AdequacyValidationError,
    ReasonCode,
    canonical_digest,
    clean_family_definitions,
    coverage_gap_registry_digest,
    core_fingerprint_distance,
    trusted_reference_by_id,
    trusted_reference_registry_digest,
    validate_candidate_cohort,
    validate_candidate_metadata,
    validate_coverage_gap_registry,
    validate_taxonomy_identity,
    validate_trusted_reference_registry,
)


def _fingerprint(seed: str) -> dict[str, object]:
    oracle_id = f"synthetic.oracle.{seed}"
    return {
        "spec_rule": f"candidate rule {seed}",
        "causal_mechanism": f"candidate mechanism {seed}",
        "target_function_set": [f"checkout.{seed}.target"],
        "trigger_shape": f"candidate trigger {seed}",
        "observable_behavior": f"candidate observable {seed}",
        "oracle_outcome_vector": [{"oracle_id": oracle_id, "expected_outcome": "fail"}],
        "normalized_patch_operation": f"replace candidate operation {seed}",
        "interaction_depth": f"synthetic_depth_{seed}",
    }


def synthetic_not_admitted_bug_candidate(bucket: str, index: int) -> dict[str, object]:
    seed = f"{BUGGY_BUCKET_IDS.index(bucket) + 1}-{index}"
    nearest = trusted_reference_by_id("P1B-BUG-001")
    fingerprint = _fingerprint(seed)
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
        "interaction_depth": fingerprint["interaction_depth"],
        "fix_intent_category": "synthetic_fix_intent",
        "difficulty": "synthetic",
        "nearest_legacy_or_admitted_variant_id": "P1B-BUG-001",
        "material_difference_dimensions": ["spec/mechanism", "target_function_set"],
        "diversity_rationale": "Synthetic fixture differs in reviewed rule and target dimensions.",
        "core_fingerprint": fingerprint,
        "nearest_reference_core_fingerprint": deepcopy(nearest.core_fingerprint),
        "nearest_reference_core_fingerprint_digest": nearest.core_fingerprint_digest,
    }


def synthetic_not_admitted_clean_candidate(family_id: str, index: int = 1) -> dict[str, object]:
    family_order = CLEAN_STRESS_FAMILY_IDS.index(family_id) + 1
    seed = f"clean-{family_order}-{index}"
    nearest = trusted_reference_by_id("P1B-CLEAN-021")
    fingerprint = _fingerprint(seed)
    fingerprint["oracle_outcome_vector"] = [
        {"oracle_id": f"synthetic.no_bug.{seed}", "expected_outcome": "pass"}
    ]
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
        "interaction_depth": fingerprint["interaction_depth"],
        "nearest_legacy_or_admitted_clean_variant_id": "P1B-CLEAN-021",
        "material_difference_dimensions": ["spec/mechanism", "target_function_set"],
        "diversity_rationale": "Synthetic fixture differs in reviewed rule and touched-function dimensions.",
        "core_fingerprint": fingerprint,
        "nearest_reference_core_fingerprint": deepcopy(nearest.core_fingerprint),
        "nearest_reference_core_fingerprint_digest": nearest.core_fingerprint_digest,
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


_OUTCOME_QUALIFIED_MATRIX_IDENTIFIERS = (
    "policy outcome matrix",
    "outcome matrix",
    "policy_outcome_matrix",
)


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


@pytest.mark.parametrize("action_id", APPROVED_ACTION_IDS)
def test_each_approved_existing_action_id_is_valid_for_buggy_action_mapping(
    action_id: str,
):
    candidate = synthetic_not_admitted_bug_candidate(BUGGY_BUCKET_IDS[0], 1)
    candidate["action_mapping"] = action_id
    validated = validate_candidate_metadata(candidate, cohort_kind="buggy")
    assert validated["action_mapping"] == action_id


def test_config_matrix_action_id_is_an_explicit_positive_control():
    assert "run_config_matrix_tests" in APPROVED_ACTION_IDS
    candidate = synthetic_not_admitted_bug_candidate(BUGGY_BUCKET_IDS[0], 1)
    candidate["action_mapping"] = "run_config_matrix_tests"
    assert validate_candidate_metadata(candidate, cohort_kind="buggy")["action_mapping"] == (
        "run_config_matrix_tests"
    )


@pytest.mark.parametrize(
    ("value", "reason"),
    [
        ("run_unreviewed_tests", ReasonCode.UNKNOWN_ACTION_ID),
        ("fixed_checklist", ReasonCode.FORMAL_POLICY_ID_FORBIDDEN),
        ("", ReasonCode.EMPTY_VALUE),
        (1, ReasonCode.WRONG_TYPE),
    ],
)
def test_action_mapping_rejects_unknown_policy_empty_and_wrong_type(
    value: object,
    reason: ReasonCode,
):
    candidate = synthetic_not_admitted_bug_candidate(BUGGY_BUCKET_IDS[0], 1)
    candidate["action_mapping"] = value
    _assert_reason(reason, validate_candidate_metadata, candidate, cohort_kind="buggy")


def test_matrix_identity_tokens_and_configuration_matrix_narrative_are_allowed():
    candidate = synthetic_not_admitted_bug_candidate(BUGGY_BUCKET_IDS[0], 1)
    candidate["action_test_catalog_ids"] = ["synthetic.catalog.configuration_matrix"]
    candidate["oracle_ids"] = ["synthetic.oracle.configuration_matrix"]
    candidate["core_fingerprint"]["oracle_outcome_vector"] = [
        {
            "oracle_id": "synthetic.oracle.configuration_matrix",
            "expected_outcome": "fail",
        }
    ]
    candidate["diversity_rationale"] = (
        "A configuration matrix is ordinary specification taxonomy evidence."
    )
    validated = validate_candidate_metadata(candidate, cohort_kind="buggy")
    assert validated["action_test_catalog_ids"] == [
        "synthetic.catalog.configuration_matrix"
    ]
    assert validated["oracle_ids"] == ["synthetic.oracle.configuration_matrix"]

    clean = synthetic_not_admitted_clean_candidate(CLEAN_STRESS_FAMILY_IDS[0])
    clean["no_bug_oracle_ids"] = ["synthetic.oracle.configuration_matrix"]
    clean["core_fingerprint"]["oracle_outcome_vector"] = [
        {
            "oracle_id": "synthetic.oracle.configuration_matrix",
            "expected_outcome": "pass",
        }
    ]
    validated_clean = validate_candidate_metadata(clean, cohort_kind="clean_stress")
    assert validated_clean["no_bug_oracle_ids"] == [
        "synthetic.oracle.configuration_matrix"
    ]


@pytest.mark.parametrize(
    "field_context",
    [
        "action_test_catalog_ids",
        "buggy_oracle_ids",
        "buggy_nested_oracle_id",
        "clean_no_bug_oracle_ids",
        "clean_nested_oracle_id",
    ],
)
@pytest.mark.parametrize(
    "outcome_identity",
    _OUTCOME_QUALIFIED_MATRIX_IDENTIFIERS,
)
def test_outcome_qualified_matrix_identity_is_rejected_at_candidate_boundary(
    field_context: str,
    outcome_identity: str,
):
    if field_context.startswith("clean_"):
        candidate = synthetic_not_admitted_clean_candidate(
            CLEAN_STRESS_FAMILY_IDS[0]
        )
        cohort_kind = "clean_stress"
    else:
        candidate = synthetic_not_admitted_bug_candidate(BUGGY_BUCKET_IDS[0], 1)
        cohort_kind = "buggy"

    if field_context == "action_test_catalog_ids":
        candidate["action_test_catalog_ids"] = [outcome_identity]
    elif field_context == "buggy_oracle_ids":
        candidate["oracle_ids"] = [outcome_identity]
    elif field_context == "buggy_nested_oracle_id":
        candidate["core_fingerprint"]["oracle_outcome_vector"][0][
            "oracle_id"
        ] = outcome_identity
    elif field_context == "clean_no_bug_oracle_ids":
        candidate["no_bug_oracle_ids"] = [outcome_identity]
    else:
        candidate["core_fingerprint"]["oracle_outcome_vector"][0][
            "oracle_id"
        ] = outcome_identity

    _assert_reason(
        ReasonCode.POLICY_OUTCOME_FIELD_FORBIDDEN,
        validate_candidate_metadata,
        candidate,
        cohort_kind=cohort_kind,
    )


@pytest.mark.parametrize(
    "outcome_text",
    [
        "policy outcome matrix",
        "outcome matrix",
        "policy_outcome_matrix",
        "matrix cell",
    ],
)
def test_policy_result_matrix_narrative_is_rejected(outcome_text: str):
    candidate = synthetic_not_admitted_bug_candidate(BUGGY_BUCKET_IDS[0], 1)
    candidate["diversity_rationale"] = f"Narrative embeds {outcome_text}."
    _assert_reason(
        ReasonCode.POLICY_OUTCOME_FIELD_FORBIDDEN,
        validate_candidate_metadata,
        candidate,
        cohort_kind="buggy",
    )


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
    current = deepcopy(candidate["nearest_reference_core_fingerprint"])
    current["trigger_shape"] = "different candidate trigger"
    current["normalized_patch_operation"] = "different candidate patch"
    candidate["core_fingerprint"] = current
    candidate["interaction_depth"] = current["interaction_depth"]
    candidate["oracle_ids"] = [item["oracle_id"] for item in current["oracle_outcome_vector"]]
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
    candidate["core_fingerprint"]["normalized_patch_operation"] = candidate["nearest_reference_core_fingerprint"]["normalized_patch_operation"]
    _assert_reason(ReasonCode.SAME_NORMALIZED_PATCH, validate_candidate_metadata, candidate, cohort_kind="buggy")


def test_same_target_trigger_oracle_is_rejected_with_specific_reason():
    candidate = synthetic_not_admitted_bug_candidate(BUGGY_BUCKET_IDS[0], 1)
    nearest = candidate["nearest_reference_core_fingerprint"]
    current = candidate["core_fingerprint"]
    for field in ("target_function_set", "trigger_shape", "oracle_outcome_vector"):
        current[field] = deepcopy(nearest[field])
    candidate["oracle_ids"] = [item["oracle_id"] for item in current["oracle_outcome_vector"]]
    candidate["material_difference_dimensions"] = ["spec/mechanism", "observable/oracle_outcome"]
    _assert_reason(ReasonCode.SAME_TARGET_TRIGGER_ORACLE, validate_candidate_metadata, candidate, cohort_kind="buggy")


def test_trusted_reference_registry_is_exact_ordered_and_digest_bound():
    references = validate_trusted_reference_registry()
    assert len(references) == 25
    assert [item.variant_id for item in references] == [
        *(f"P1B-BUG-{index:03d}" for index in range(1, 21)),
        *(f"P1B-CLEAN-{index:03d}" for index in range(21, 26)),
    ]
    assert [item.cohort_kind for item in references].count("buggy") == 20
    assert [item.cohort_kind for item in references].count("clean_stress") == 5
    assert TRUSTED_REFERENCE_REGISTRY_VERSION == "p2a_trusted_reference_registry.v1"
    assert trusted_reference_registry_digest() == (
        "e430974d39f7b137a0a2d0c754a43613a42a081cc4800ec2ca4a90b172e6d203"
    )
    assert all(item.core_fingerprint_digest == canonical_digest(item.core_fingerprint) for item in references)


@pytest.mark.parametrize("stable_order", [True, 1.0, "1"])
def test_trusted_reference_stable_order_requires_strict_int(stable_order: object):
    registry = [asdict(item) for item in TRUSTED_REFERENCE_REGISTRY]
    registry[0]["stable_order"] = stable_order
    _assert_reason(ReasonCode.WRONG_TYPE, validate_trusted_reference_registry, registry)


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("variant_id", True, ReasonCode.WRONG_TYPE),
        ("variant_id", 1, ReasonCode.WRONG_TYPE),
        ("variant_id", "", ReasonCode.EMPTY_VALUE),
        ("cohort_kind", False, ReasonCode.WRONG_TYPE),
        ("cohort_kind", 1, ReasonCode.WRONG_TYPE),
        ("cohort_kind", "", ReasonCode.EMPTY_VALUE),
    ],
)
def test_trusted_reference_id_and_cohort_require_nonempty_strict_strings(
    field: str,
    value: object,
    reason: ReasonCode,
):
    registry = [asdict(item) for item in TRUSTED_REFERENCE_REGISTRY]
    registry[0][field] = value
    _assert_reason(reason, validate_trusted_reference_registry, registry)


@pytest.mark.parametrize("mutation", ["id", "order", "fingerprint", "digest"])
def test_trusted_reference_registry_mutation_is_rejected(mutation: str):
    registry = [asdict(item) for item in TRUSTED_REFERENCE_REGISTRY]
    if mutation == "id":
        registry[0]["variant_id"] = "P1B-BUG-999"
    elif mutation == "order":
        registry[0], registry[1] = registry[1], registry[0]
    elif mutation == "fingerprint":
        registry[0]["core_fingerprint"]["spec_rule"] = "fabricated reviewed rule"
    else:
        registry[0]["core_fingerprint_digest"] = "0" * 64
    with pytest.raises(AdequacyValidationError) as exc_info:
        validate_trusted_reference_registry(registry)
    assert exc_info.value.issue.code in {
        ReasonCode.TRUSTED_REFERENCE_REGISTRY_MISMATCH.value,
        ReasonCode.REFERENCE_DIGEST_MISMATCH.value,
    }


def test_reference_id_fingerprint_and_digest_must_bind_to_one_identity():
    candidate = synthetic_not_admitted_bug_candidate(BUGGY_BUCKET_IDS[0], 1)
    other = trusted_reference_by_id("P1B-BUG-002")
    candidate["nearest_reference_core_fingerprint"] = deepcopy(other.core_fingerprint)
    candidate["nearest_reference_core_fingerprint_digest"] = other.core_fingerprint_digest
    _assert_reason(
        ReasonCode.REFERENCE_FINGERPRINT_MISMATCH,
        validate_candidate_metadata,
        candidate,
        cohort_kind="buggy",
    )
    candidate = synthetic_not_admitted_bug_candidate(BUGGY_BUCKET_IDS[0], 1)
    candidate["nearest_reference_core_fingerprint_digest"] = "0" * 64
    _assert_reason(
        ReasonCode.REFERENCE_DIGEST_MISMATCH,
        validate_candidate_metadata,
        candidate,
        cohort_kind="buggy",
    )


@pytest.mark.parametrize(
    ("reference_id", "reason"),
    [
        ("P1B-BUG-999", ReasonCode.UNKNOWN_REFERENCE),
        ("P1B-CLEAN-021", ReasonCode.WRONG_REFERENCE_COHORT),
        ("self", ReasonCode.SELF_REFERENCE),
        ("P2A-BUG-UNVALIDATED-PRIOR", ReasonCode.UNKNOWN_REFERENCE),
    ],
)
def test_standalone_unknown_wrong_cohort_self_and_unvalidated_references_are_rejected(
    reference_id,
    reason,
):
    candidate = synthetic_not_admitted_bug_candidate(BUGGY_BUCKET_IDS[0], 1)
    candidate["nearest_legacy_or_admitted_variant_id"] = (
        candidate["variant_id"] if reference_id == "self" else reference_id
    )
    _assert_reason(
        reason,
        validate_candidate_metadata,
        candidate,
        cohort_kind="buggy",
    )


def test_cohort_forward_and_wrong_cohort_references_keep_distinct_reason_codes():
    buggy, clean = synthetic_not_admitted_cohort()
    buggy[0]["nearest_legacy_or_admitted_variant_id"] = buggy[1]["variant_id"]
    _assert_reason(ReasonCode.FORWARD_REFERENCE, validate_candidate_cohort, buggy, clean)

    buggy, clean = synthetic_not_admitted_cohort()
    clean[0]["nearest_legacy_or_admitted_clean_variant_id"] = buggy[0]["variant_id"]
    _assert_reason(
        ReasonCode.WRONG_REFERENCE_COHORT,
        validate_candidate_cohort,
        buggy,
        clean,
    )


def test_public_standalone_validator_has_no_admitted_reference_injection_path():
    parameters = inspect.signature(validate_candidate_metadata).parameters
    assert "admitted_references" not in parameters
    assert "candidate_ids" not in parameters
    fabricated = synthetic_not_admitted_bug_candidate(BUGGY_BUCKET_IDS[0], 1)
    fabricated_fingerprint = deepcopy(fabricated["core_fingerprint"])
    fabricated_fingerprint["spec_rule"] = "fabricated near-reference rule"
    fabricated_fingerprint["target_function_set"] = [
        "checkout.synthetic.fabricated_reference"
    ]
    fabricated_fingerprint["normalized_patch_operation"] = (
        "replace fabricated near-reference operation"
    )
    fabricated["nearest_legacy_or_admitted_variant_id"] = (
        "P2A-BUG-FABRICATED-REF"
    )
    fabricated["nearest_reference_core_fingerprint"] = fabricated_fingerprint
    fabricated["nearest_reference_core_fingerprint_digest"] = canonical_digest(
        fabricated_fingerprint
    )
    fabricated_reference = {
        "variant_id": "P2A-BUG-FABRICATED-REF",
        "core_fingerprint": fabricated_fingerprint,
    }
    _assert_reason(
        ReasonCode.UNKNOWN_REFERENCE,
        validate_candidate_metadata,
        fabricated,
        cohort_kind="buggy",
    )
    with pytest.raises(TypeError):
        validate_candidate_metadata(
            fabricated,
            cohort_kind="buggy",
            admitted_references=[fabricated_reference],
        )


def test_previously_validated_same_cohort_candidate_can_be_the_bound_nearest():
    buggy, clean = synthetic_not_admitted_cohort()
    first = buggy[0]
    second = buggy[1]
    current = deepcopy(first["core_fingerprint"])
    current["spec_rule"] = "synthetic admitted-nearest rule"
    current["target_function_set"] = ["checkout.synthetic.admitted_nearest"]
    current["normalized_patch_operation"] = "replace admitted-nearest operation"
    second["core_fingerprint"] = current
    second["interaction_depth"] = current["interaction_depth"]
    second["oracle_ids"] = [item["oracle_id"] for item in current["oracle_outcome_vector"]]
    second["nearest_legacy_or_admitted_variant_id"] = first["variant_id"]
    second["nearest_reference_core_fingerprint"] = deepcopy(first["core_fingerprint"])
    second["nearest_reference_core_fingerprint_digest"] = canonical_digest(first["core_fingerprint"])
    validated, _ = validate_candidate_cohort(buggy, clean)
    assert validated[1]["nearest_legacy_or_admitted_variant_id"] == first["variant_id"]
    assert validated[1]["nearest_reference_core_fingerprint"] == validated[0]["core_fingerprint"]
    assert validated[1]["nearest_reference_core_fingerprint_digest"] == canonical_digest(
        validated[0]["core_fingerprint"]
    )


def test_global_duplicate_scan_rejects_duplicate_hidden_by_far_reference_claim():
    candidate = synthetic_not_admitted_bug_candidate(BUGGY_BUCKET_IDS[0], 1)
    duplicate = trusted_reference_by_id("P1B-BUG-002")
    candidate["core_fingerprint"] = deepcopy(duplicate.core_fingerprint)
    candidate["interaction_depth"] = duplicate.core_fingerprint["interaction_depth"]
    candidate["oracle_ids"] = [item["oracle_id"] for item in duplicate.core_fingerprint["oracle_outcome_vector"]]
    _assert_reason(
        ReasonCode.EXACT_CORE_FINGERPRINT_DUPLICATE,
        validate_candidate_metadata,
        candidate,
        cohort_kind="buggy",
    )


def test_computed_nearest_mismatch_is_rejected_and_ties_use_trusted_order():
    candidate = synthetic_not_admitted_bug_candidate(BUGGY_BUCKET_IDS[0], 1)
    near = trusted_reference_by_id("P1B-BUG-002")
    current = deepcopy(near.core_fingerprint)
    current["spec_rule"] = "near second legacy rule"
    current["target_function_set"] = ["discounts.near_second"]
    current["normalized_patch_operation"] = "replace near-second operation"
    candidate["core_fingerprint"] = current
    candidate["interaction_depth"] = current["interaction_depth"]
    candidate["oracle_ids"] = [item["oracle_id"] for item in current["oracle_outcome_vector"]]
    _assert_reason(
        ReasonCode.NEAREST_REFERENCE_MISMATCH,
        validate_candidate_metadata,
        candidate,
        cohort_kind="buggy",
    )

    tied = synthetic_not_admitted_bug_candidate(BUGGY_BUCKET_IDS[0], 1)
    distances = [
        core_fingerprint_distance(tied["core_fingerprint"], reference.core_fingerprint)
        for reference in validate_trusted_reference_registry()
        if reference.cohort_kind == "buggy"
    ]
    assert len(set(distances)) == 1
    assert validate_candidate_metadata(tied, cohort_kind="buggy")["nearest_legacy_or_admitted_variant_id"] == "P1B-BUG-001"


def test_resolved_nearest_with_one_material_dimension_is_rejected():
    candidate = synthetic_not_admitted_bug_candidate(BUGGY_BUCKET_IDS[0], 1)
    nearest = trusted_reference_by_id("P1B-BUG-001")
    current = deepcopy(nearest.core_fingerprint)
    current["spec_rule"] = "only one changed rule"
    candidate["core_fingerprint"] = current
    candidate["interaction_depth"] = current["interaction_depth"]
    candidate["oracle_ids"] = [item["oracle_id"] for item in current["oracle_outcome_vector"]]
    candidate["material_difference_dimensions"] = ["spec/mechanism", "target_function_set"]
    _assert_reason(
        ReasonCode.INSUFFICIENT_MATERIAL_DIFFERENCE,
        validate_candidate_metadata,
        candidate,
        cohort_kind="buggy",
    )


def test_coverage_gap_registry_has_stable_ten_entry_identity_and_legacy_basis():
    entries = validate_coverage_gap_registry()
    assert len(entries) == 10
    assert [entry.stable_order for entry in entries] == list(range(1, 11))
    assert [entry.primary_bucket_or_clean_family_id for entry in entries[:5]] == list(BUGGY_BUCKET_IDS)
    assert [entry.primary_bucket_or_clean_family_id for entry in entries[5:]] == list(CLEAN_STRESS_FAMILY_IDS)
    assert len(coverage_gap_registry_digest()) == 64
    assert all(basis.repository_path.startswith("src/bug_cause_inference/p1b/") for entry in entries for basis in entry.source_basis)


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
    _assert_reason(ReasonCode.POLICY_OUTCOME_FIELD_FORBIDDEN, validate_coverage_gap_registry, registry)


def test_registry_absolute_source_basis_is_rejected():
    registry = [asdict(entry) for entry in COVERAGE_GAP_REGISTRY]
    registry[0]["source_basis"][0]["repository_path"] = "C:\\Users\\name\\legacy.py"
    _assert_reason(ReasonCode.REGISTRY_SOURCE_BASIS_INVALID, validate_coverage_gap_registry, registry)


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "cross_entry", "reordered"])
def test_registry_support_is_the_exact_stable_legacy_partition(mutation: str):
    registry = [asdict(entry) for entry in COVERAGE_GAP_REGISTRY]
    if mutation == "missing":
        registry[0]["legacy_support_ids"] = registry[0]["legacy_support_ids"][:-1]
    elif mutation == "duplicate":
        registry[0]["legacy_support_ids"] = (*registry[0]["legacy_support_ids"], registry[0]["legacy_support_ids"][-1])
    elif mutation == "cross_entry":
        first = list(registry[0]["legacy_support_ids"])
        second = list(registry[1]["legacy_support_ids"])
        first[-1], second[0] = second[0], first[-1]
        registry[0]["legacy_support_ids"] = tuple(first)
        registry[1]["legacy_support_ids"] = tuple(second)
    else:
        registry[0]["legacy_support_ids"] = tuple(reversed(registry[0]["legacy_support_ids"]))
    _assert_reason(
        ReasonCode.REGISTRY_LEGACY_SUPPORT_MISMATCH,
        validate_coverage_gap_registry,
        registry,
    )


@pytest.mark.parametrize(
    "field",
    [
        "legacy_coverage_summary",
        "gap_statement",
        "candidate_need_statement",
        "explicit_non_outcome_basis",
    ],
)
def test_registry_empty_narrative_evidence_is_rejected(field: str):
    registry = [asdict(entry) for entry in COVERAGE_GAP_REGISTRY]
    registry[0][field] = ""
    _assert_reason(ReasonCode.EMPTY_VALUE, validate_coverage_gap_registry, registry)


def test_registry_empty_or_duplicate_dimensions_and_sources_are_rejected():
    registry = [asdict(entry) for entry in COVERAGE_GAP_REGISTRY]
    registry[0]["gap_taxonomy_dimensions"] = ()
    _assert_reason(ReasonCode.EMPTY_VALUE, validate_coverage_gap_registry, registry)
    registry = [asdict(entry) for entry in COVERAGE_GAP_REGISTRY]
    registry[0]["gap_taxonomy_dimensions"] = (
        registry[0]["gap_taxonomy_dimensions"][0],
        registry[0]["gap_taxonomy_dimensions"][0],
    )
    _assert_reason(ReasonCode.REGISTRY_IDENTITY_MISMATCH, validate_coverage_gap_registry, registry)
    registry = [asdict(entry) for entry in COVERAGE_GAP_REGISTRY]
    registry[0]["source_basis"] = ()
    _assert_reason(ReasonCode.EMPTY_VALUE, validate_coverage_gap_registry, registry)
    registry = [asdict(entry) for entry in COVERAGE_GAP_REGISTRY]
    registry[0]["source_basis"] = (*registry[0]["source_basis"], deepcopy(registry[0]["source_basis"][0]))
    _assert_reason(ReasonCode.REGISTRY_SOURCE_BASIS_INVALID, validate_coverage_gap_registry, registry)


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("repository_path", "src/bug_cause_inference/p1b/not_real.py", ReasonCode.REGISTRY_SOURCE_BASIS_INVALID),
        ("repository_path", "src/bug_cause_inference/p1b/../p1c/labels.py", ReasonCode.REGISTRY_SOURCE_BASIS_INVALID),
        ("repository_path", "C:/repository/dataset.py", ReasonCode.ABSOLUTE_PATH_FORBIDDEN),
        ("repository_path", "src/bug_cause_inference/p1b", ReasonCode.REGISTRY_SOURCE_BASIS_INVALID),
        ("anchor", "P1B-BUG-*", ReasonCode.REGISTRY_SOURCE_BASIS_INVALID),
        ("anchor", "P1B-BUG-001..004", ReasonCode.REGISTRY_SOURCE_BASIS_INVALID),
    ],
)
def test_registry_source_path_and_anchor_mutations_are_rejected(field: str, value: str, reason: ReasonCode):
    registry = [asdict(entry) for entry in COVERAGE_GAP_REGISTRY]
    registry[0]["source_basis"][0][field] = value
    _assert_reason(reason, validate_coverage_gap_registry, registry)


@pytest.mark.parametrize("kind", ["legacy_metadata", "patch_artifact", "oracle_case_semantics"])
def test_registry_requires_all_three_source_kinds_for_exact_support(kind: str):
    registry = [asdict(entry) for entry in COVERAGE_GAP_REGISTRY]
    registry[0]["source_basis"] = tuple(
        source for source in registry[0]["source_basis"] if source["kind"] != kind
    )
    _assert_reason(ReasonCode.REGISTRY_SOURCE_BASIS_INVALID, validate_coverage_gap_registry, registry)


def test_registry_source_identity_support_mismatch_is_rejected():
    registry = [asdict(entry) for entry in COVERAGE_GAP_REGISTRY]
    registry[0]["source_basis"][0]["legacy_support_ids"] = ("P1B-BUG-002",)
    _assert_reason(ReasonCode.REGISTRY_SOURCE_BASIS_INVALID, validate_coverage_gap_registry, registry)


def test_registry_source_paths_are_tracked_existing_files_inside_repository():
    root = Path(__file__).resolve().parents[1]
    completed = subprocess.run(
        ["git", "-c", f"safe.directory={root.as_posix()}", "ls-files", "-z"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    tracked = set(completed.stdout.decode("utf-8").split("\0"))
    for entry in validate_coverage_gap_registry():
        for source in entry.source_basis:
            resolved = (root / source.repository_path).resolve()
            assert resolved.is_relative_to(root.resolve())
            assert resolved.is_file()
            assert source.repository_path in tracked


@pytest.mark.parametrize(
    "policy_id",
    [
        "fixed_checklist",
        "test_first",
        "coverage_first",
        "recent_diff_first",
        "cause_only_p1a_style",
        "expected_utility_per_cost",
        "random_action",
        "state_sequence_guard",
    ],
)
def test_formal_policy_ids_embedded_in_allowlisted_candidate_text_are_rejected(policy_id: str):
    candidate = synthetic_not_admitted_bug_candidate(BUGGY_BUCKET_IDS[0], 1)
    candidate["diversity_rationale"] = f"Long taxonomy narrative embeds {policy_id} as material."
    _assert_reason(
        ReasonCode.FORMAL_POLICY_ID_FORBIDDEN,
        validate_candidate_metadata,
        candidate,
        cohort_kind="buggy",
    )


@pytest.mark.parametrize(
    "outcome_text",
    [
        "clean false-positive rate = 0.0",
        "clean_false_positive_outcome: 0/5",
        "clean false positive 0%",
    ],
)
def test_clean_false_positive_result_encodings_are_rejected_at_candidate_and_registry_boundaries(outcome_text: str):
    candidate = synthetic_not_admitted_bug_candidate(BUGGY_BUCKET_IDS[0], 1)
    candidate["diversity_rationale"] = outcome_text
    _assert_reason(
        ReasonCode.CLEAN_FALSE_POSITIVE_OUTCOME_FORBIDDEN,
        validate_candidate_metadata,
        candidate,
        cohort_kind="buggy",
    )
    registry = [asdict(entry) for entry in COVERAGE_GAP_REGISTRY]
    registry[0]["gap_statement"] = outcome_text
    _assert_reason(
        ReasonCode.CLEAN_FALSE_POSITIVE_OUTCOME_FORBIDDEN,
        validate_coverage_gap_registry,
        registry,
    )


def test_exact_clean_primary_bucket_is_the_only_clean_false_positive_value_exception():
    candidate = synthetic_not_admitted_clean_candidate(CLEAN_STRESS_FAMILY_IDS[0])
    assert validate_candidate_metadata(candidate, cohort_kind="clean_stress")["primary_bucket"] == "clean_false_positive"
    candidate["recommended_no_bug_evidence"] = "clean false positive 0%"
    _assert_reason(
        ReasonCode.CLEAN_FALSE_POSITIVE_OUTCOME_FORBIDDEN,
        validate_candidate_metadata,
        candidate,
        cohort_kind="clean_stress",
    )


def test_outcome_material_in_list_and_nested_allowed_scalar_is_rejected():
    candidate = synthetic_not_admitted_bug_candidate(BUGGY_BUCKET_IDS[0], 1)
    candidate["action_test_catalog_ids"] = ["fixed_checklist"]
    _assert_reason(
        ReasonCode.FORMAL_POLICY_ID_FORBIDDEN,
        validate_candidate_metadata,
        candidate,
        cohort_kind="buggy",
    )
    candidate = synthetic_not_admitted_bug_candidate(BUGGY_BUCKET_IDS[0], 1)
    candidate["core_fingerprint"]["oracle_outcome_vector"][0]["oracle_id"] = "state_sequence_guard"
    _assert_reason(
        ReasonCode.FORMAL_POLICY_ID_FORBIDDEN,
        validate_candidate_metadata,
        candidate,
        cohort_kind="buggy",
    )


@pytest.mark.parametrize("mutation", ["unknown", "missing", "wrong_scalar", "wrong_container", "duplicate", "empty"])
def test_oracle_outcome_vector_has_strict_nested_schema(mutation: str):
    candidate = synthetic_not_admitted_bug_candidate(BUGGY_BUCKET_IDS[0], 1)
    vector = candidate["core_fingerprint"]["oracle_outcome_vector"]
    if mutation == "unknown":
        vector[0]["unknown"] = "not hashed"
        reason = ReasonCode.UNKNOWN_FIELD
    elif mutation == "missing":
        vector[0].pop("expected_outcome")
        reason = ReasonCode.MISSING_FIELD
    elif mutation == "wrong_scalar":
        vector[0]["expected_outcome"] = 1
        reason = ReasonCode.WRONG_TYPE
    elif mutation == "wrong_container":
        candidate["core_fingerprint"]["oracle_outcome_vector"] = {"oracle_id": "x"}
        reason = ReasonCode.WRONG_TYPE
    elif mutation == "duplicate":
        vector.append(deepcopy(vector[0]))
        reason = ReasonCode.WRONG_IDENTITY
    else:
        candidate["core_fingerprint"]["oracle_outcome_vector"] = []
        reason = ReasonCode.EMPTY_VALUE
    _assert_reason(reason, validate_candidate_metadata, candidate, cohort_kind="buggy")


def _normalized_import_modules(source: str, package: str = "bug_cause_inference.p2a") -> tuple[str, ...]:
    modules: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = package.split(".")[: -(node.level - 1) or None]
                module = ".".join([*base, *(node.module or "").split(".")]).strip(".")
            else:
                module = node.module or ""
            if module:
                modules.append(module)
                modules.extend(f"{module}.{alias.name}" for alias in node.names if alias.name != "*")
    normalized = []
    for module in modules:
        prefix = "bug_cause_inference."
        normalized.append(module[len(prefix) :] if module.startswith(prefix) else module)
    return tuple(normalized)


_FORBIDDEN_MODULES = (
    "p1b.execution",
    "p1b.policies",
    "p1b.evaluation",
    "p1c.evaluation",
    "p1d",
    "p2a.evaluation",
    "p2a.reports",
)


def _forbidden_imports(source: str) -> tuple[str, ...]:
    return tuple(
        module
        for module in _normalized_import_modules(source)
        if any(module == forbidden or module.startswith(f"{forbidden}.") for forbidden in _FORBIDDEN_MODULES)
    )


def test_adequacy_and_freeze_modules_have_no_forbidden_evaluation_dependency():
    root = Path(__file__).resolve().parents[1] / "src" / "bug_cause_inference" / "p2a"
    for filename in ("adequacy.py", "freeze.py"):
        assert _forbidden_imports((root / filename).read_text(encoding="utf-8")) == ()


@pytest.mark.parametrize(
    "source",
    [
        "import bug_cause_inference.p1b.execution",
        "import bug_cause_inference.p1b.execution as legacy_execution",
        "from bug_cause_inference.p1b.execution import run_action",
        "from bug_cause_inference.p1b import execution",
        "from ..p1b.execution import run_action",
        "from ..p1b import execution as legacy_execution",
    ],
)
def test_ast_sentinel_detects_exact_forbidden_p1b_execution_import_forms(source: str):
    assert _forbidden_imports(source)


def test_ast_sentinel_uses_exact_module_prefix_not_substring_coincidence():
    assert _forbidden_imports("import bug_cause_inference.p1b.execution_helpers") == ()
