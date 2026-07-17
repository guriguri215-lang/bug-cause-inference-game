"""Outcome-free admission and authoring-manifest tests for actual P2a candidates."""

from __future__ import annotations

import ast
import copy
import difflib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from bug_cause_inference.p2a.adequacy import (
    BUGGY_BUCKET_IDS,
    CLEAN_STRESS_FAMILY_IDS,
    AdequacyValidationError,
    canonical_digest,
    coverage_gap_registry_digest,
    trusted_reference_registry_digest,
    validate_candidate_cohort,
)
from bug_cause_inference.p2a.candidate_authoring import (
    AUTHORING_MANIFEST_PATH,
    CandidateAuthoringError,
    author_candidate,
    authoring_manifest_digest,
    build_authoring_manifest,
    load_tracked_authoring_manifest,
    patch_text,
    repository_path,
    serialized_authoring_manifest,
    validate_authoring_manifest,
)
from bug_cause_inference.p2a.candidates import (
    ARTIFACT_PATCH_OPERATION_IDENTITIES,
    BUGGY_CANDIDATE_METADATA,
    BUGGY_CANDIDATES,
    CANDIDATE_IDS,
    CLEAN_CANDIDATE_METADATA,
    CLEAN_CANDIDATES,
    PATCH_OPERATION_SCHEMA_VERSION,
    CandidatePatchSemanticError,
    canonical_patch_operation_digest,
    canonical_patch_operation_identity,
    canonical_patch_operation_payload_from_text,
    validate_artifact_semantic_cohort,
)
from bug_cause_inference.p2a.freeze import (
    candidate_manifest_digest,
    candidate_manifest_payload,
)


EXPECTED_IDS = tuple(
    [f"P2A-BUG-{index:03d}" for index in range(1, 11)]
    + [f"P2A-CLEAN-{index:03d}" for index in range(1, 6)]
)

_FUNCTION_EDIT = (
    '    rates = config.get("tax_rates", {})\n',
    '    rates = config.get("tax_rates", DEFAULT_CONFIG["tax_rates"])\n',
)
_DEFAULT_CONFIG_BLOCK = '''DEFAULT_CONFIG: dict[str, Any] = {
    "tax_rates": {"JP": 0.10, "US": 0.07},
    "feature_flags": {"stack_member_and_coupon": False, "allow_preorder": True},
    "shipping_threshold": 10000,
    "region_rates": {"domestic": 800, "okinawa": 1600, "international": 3000},
    "region_defaults": {"missing": "domestic"},
    "region_aliases": {"okinawa": "okinawa", "jp-okinawa": "okinawa"},
}
'''


def _bug004_patch_with_module_replacements(
    *replacements: tuple[str, str],
) -> str:
    source = repository_path(
        "src/bug_cause_inference/p1b/artifacts/real_diff/baseline/checkout/config.py"
    ).read_text(encoding="utf-8")
    after = source.replace(*_FUNCTION_EDIT)
    assert after != source
    for before_text, after_text in replacements:
        assert after.count(before_text) == 1
        after = after.replace(before_text, after_text)
    return "".join(
        difflib.unified_diff(
            source.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile="a/checkout/config.py",
            tofile="b/checkout/config.py",
        )
    )


def test_actual_authored_candidate_ids_counts_and_stable_taxonomy_order() -> None:
    assert CANDIDATE_IDS == EXPECTED_IDS
    assert [item.metadata["primary_bucket"] for item in BUGGY_CANDIDATES] == [
        bucket for bucket in BUGGY_BUCKET_IDS for _ in range(2)
    ]
    assert [item.metadata["clean_stress_family_id"] for item in CLEAN_CANDIDATES] == list(
        CLEAN_STRESS_FAMILY_IDS
    )
    assert all(item.metadata["primary_bucket"] == "clean_false_positive" for item in CLEAN_CANDIDATES)


def test_actual_authored_metadata_passes_accepted_cohort_validator() -> None:
    buggy, clean = validate_candidate_cohort(
        [copy.deepcopy(item.metadata) for item in BUGGY_CANDIDATES],
        [copy.deepcopy(item.metadata) for item in CLEAN_CANDIDATES],
    )
    assert buggy == BUGGY_CANDIDATE_METADATA
    assert clean == CLEAN_CANDIDATE_METADATA
    assert trusted_reference_registry_digest() == (
        "e430974d39f7b137a0a2d0c754a43613a42a081cc4800ec2ca4a90b172e6d203"
    )


def test_actual_candidate_artifact_and_ground_truth_feasibility_without_policy_execution() -> None:
    evidence = [author_candidate(item) for item in (*BUGGY_CANDIDATES, *CLEAN_CANDIDATES)]
    assert len(evidence) == 15
    for candidate, item in zip((*BUGGY_CANDIDATES, *CLEAN_CANDIDATES), evidence, strict=True):
        assert patch_text(candidate).strip()
        assert item["patch_path"] == candidate.patch_path
        assert len(item["patch_sha256"]) == 64
        assert item["changed_files"] == candidate.metadata["changed_files"]
        assert item["changed_functions"] == candidate.metadata["changed_functions"]
        assert item["baseline_ground_truth_status"] == "all_pass"
        if candidate.cohort_kind == "buggy":
            assert item["candidate_ground_truth_status"] == "required_fail_observed"
            assert any(row["candidate_status"] == "fail" for row in item["oracle_statuses"])
        else:
            assert item["candidate_ground_truth_status"] == "all_pass"
            assert all(row["candidate_status"] == "pass" for row in item["oracle_statuses"])


def test_patch_paths_are_relative_existing_and_bound_to_exact_hashes() -> None:
    manifest = build_authoring_manifest()
    for candidate, evidence in zip(
        (*BUGGY_CANDIDATES, *CLEAN_CANDIDATES), manifest["candidates"], strict=True
    ):
        path = repository_path(candidate.patch_path)
        assert path.is_file()
        assert not Path(candidate.patch_path).is_absolute()
        assert evidence["patch_sha256"] == __import__("hashlib").sha256(
            path.read_bytes()
        ).hexdigest()


def test_candidate_manifest_payload_and_digest_are_deterministic() -> None:
    first = candidate_manifest_payload(BUGGY_CANDIDATE_METADATA, CLEAN_CANDIDATE_METADATA)
    second = candidate_manifest_payload(
        copy.deepcopy(BUGGY_CANDIDATE_METADATA), copy.deepcopy(CLEAN_CANDIDATE_METADATA)
    )
    assert first == second
    assert len(candidate_manifest_digest(BUGGY_CANDIDATE_METADATA, CLEAN_CANDIDATE_METADATA)) == 64


def test_review_pending_manifest_is_tracked_newline_terminated_and_semantically_exact() -> None:
    tracked_path = repository_path(AUTHORING_MANIFEST_PATH)
    raw = tracked_path.read_text(encoding="utf-8")
    assert raw.endswith("\n")
    assert raw == serialized_authoring_manifest()
    loaded = load_tracked_authoring_manifest()
    assert loaded == build_authoring_manifest()
    assert loaded["status"] == "review_pending"
    assert loaded["coverage_gap_registry_identity"]["registry_digest"] == coverage_gap_registry_digest()
    assert len(authoring_manifest_digest(loaded)) == 64
    assert loaded["patch_operation_schema_version"] == PATCH_OPERATION_SCHEMA_VERSION


@pytest.mark.parametrize(
    ("mutation", "value"),
    [
        ("status", "frozen"),
        ("status", "accepted"),
        ("status", "valid_for_evaluation"),
        ("schema_version", "wrong"),
        ("candidate_manifest_digest", "0" * 64),
    ],
)
def test_manifest_rejects_wrong_status_version_or_digest(mutation: str, value: str) -> None:
    manifest = build_authoring_manifest()
    manifest[mutation] = value
    with pytest.raises(CandidateAuthoringError):
        validate_authoring_manifest(manifest)


@pytest.mark.parametrize(
    "field",
    ["freeze_timestamp", "freeze_digest", "policy_identity", "settings_identity", "metric_identity", "serializer_identity"],
)
def test_manifest_rejects_official_freeze_fields(field: str) -> None:
    manifest = build_authoring_manifest()
    manifest[field] = "forbidden"
    with pytest.raises(CandidateAuthoringError):
        validate_authoring_manifest(manifest)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("patch_path", "C:/local/candidate.patch"),
        ("patch_path", "tmp/generated/candidate.patch"),
        ("primary_taxonomy_id", "policy outcome matrix"),
        ("patch_sha256", "0" * 64),
        ("oracle_definition_digest", "0" * 64),
    ],
)
def test_manifest_rejects_path_outcome_and_artifact_identity_mutations(
    field: str, value: str
) -> None:
    manifest = build_authoring_manifest()
    manifest["candidates"][0][field] = value
    with pytest.raises((CandidateAuthoringError, AdequacyValidationError)):
        validate_authoring_manifest(manifest)


def test_manifest_rejects_candidate_and_oracle_order_mutation() -> None:
    manifest = build_authoring_manifest()
    manifest["candidates"][0], manifest["candidates"][1] = (
        manifest["candidates"][1],
        manifest["candidates"][0],
    )
    with pytest.raises(CandidateAuthoringError):
        validate_authoring_manifest(manifest)
    manifest = build_authoring_manifest()
    manifest["candidates"][10]["oracle_ids"].reverse()
    with pytest.raises(CandidateAuthoringError):
        validate_authoring_manifest(manifest)


def test_actual_cohort_rejects_wrong_or_missing_oracle_identity() -> None:
    buggy = copy.deepcopy([item.metadata for item in BUGGY_CANDIDATES])
    clean = copy.deepcopy([item.metadata for item in CLEAN_CANDIDATES])
    buggy[0]["oracle_ids"] = ["boundary.wrong"]
    with pytest.raises(AdequacyValidationError):
        validate_candidate_cohort(buggy, clean)
    buggy = copy.deepcopy([item.metadata for item in BUGGY_CANDIDATES])
    buggy[0]["oracle_ids"] = []
    with pytest.raises(AdequacyValidationError):
        validate_candidate_cohort(buggy, clean)


def test_actual_cohort_global_duplicate_scan_rejects_patch_clone() -> None:
    buggy = copy.deepcopy([item.metadata for item in BUGGY_CANDIDATES])
    clean = copy.deepcopy([item.metadata for item in CLEAN_CANDIDATES])
    buggy[1]["core_fingerprint"]["normalized_patch_operation"] = buggy[0][
        "core_fingerprint"
    ]["normalized_patch_operation"]
    with pytest.raises(AdequacyValidationError) as exc_info:
        validate_candidate_cohort(buggy, clean)
    assert exc_info.value.issue.code in {
        "same_normalized_patch",
        "nearest_reference_mismatch",
        "insufficient_material_difference",
    }


def test_actual_cohort_nearest_reference_digest_mutation_is_rejected() -> None:
    buggy = copy.deepcopy([item.metadata for item in BUGGY_CANDIDATES])
    buggy[0]["nearest_reference_core_fingerprint_digest"] = "0" * 64
    with pytest.raises(AdequacyValidationError) as exc_info:
        validate_candidate_cohort(buggy, copy.deepcopy([item.metadata for item in CLEAN_CANDIDATES]))
    assert exc_info.value.issue.code == "reference_digest_mismatch"


def test_buggy_unexpected_pass_and_clean_oracle_failure_are_rejected() -> None:
    benign_metadata = copy.deepcopy(BUGGY_CANDIDATES[0].metadata)
    benign_identity = canonical_patch_operation_identity(CLEAN_CANDIDATES[0].patch_path)
    benign_metadata["patch_semantic_fingerprint"] = benign_identity
    benign_metadata["core_fingerprint"]["normalized_patch_operation"] = benign_identity
    benign_buggy = replace(
        BUGGY_CANDIDATES[0],
        patch_path=CLEAN_CANDIDATES[0].patch_path,
        metadata=benign_metadata,
    )
    with pytest.raises(CandidateAuthoringError, match="buggy patch did not fail"):
        author_candidate(benign_buggy)
    faulty_metadata = copy.deepcopy(CLEAN_CANDIDATES[2].metadata)
    faulty_identity = canonical_patch_operation_identity(BUGGY_CANDIDATES[4].patch_path)
    faulty_metadata["patch_semantic_fingerprint"] = faulty_identity
    faulty_metadata["core_fingerprint"]["normalized_patch_operation"] = faulty_identity
    faulty_clean = replace(
        CLEAN_CANDIDATES[2],
        patch_path=BUGGY_CANDIDATES[4].patch_path,
        metadata=faulty_metadata,
    )
    with pytest.raises(CandidateAuthoringError, match="benign patch failed"):
        author_candidate(faulty_clean)


def test_actual_patch_semantics_bind_metadata_and_authoring_identity() -> None:
    manifest = build_authoring_manifest()
    for candidate, evidence in zip(
        (*BUGGY_CANDIDATES, *CLEAN_CANDIDATES), manifest["candidates"], strict=True
    ):
        identity = canonical_patch_operation_identity(candidate.patch_path)
        assert candidate.metadata["patch_semantic_fingerprint"] == identity
        assert candidate.metadata["core_fingerprint"]["normalized_patch_operation"] == identity
        assert evidence["patch_operation_schema_version"] == PATCH_OPERATION_SCHEMA_VERSION
        assert evidence["patch_operation_digest"] == canonical_patch_operation_digest(
            candidate.patch_path
        )


def test_key_default_accessor_clones_have_same_artifact_operation() -> None:
    region_defaults_clone = """--- a/checkout/config.py
+++ b/checkout/config.py
@@ -51 +51 @@
-    return dict(config.get(\"region_defaults\", {\"missing\": \"domestic\"}))
+    return dict(config[\"region_defaults\"])
"""
    region_aliases_clone = """--- a/checkout/config.py
+++ b/checkout/config.py
@@ -55 +55 @@
-    return dict(config.get(\"region_aliases\", {}))
+    return dict(config[\"region_aliases\"])
"""
    assert canonical_patch_operation_payload_from_text(
        region_defaults_clone
    ) == canonical_patch_operation_payload_from_text(region_aliases_clone)


def test_identifier_literal_only_mutation_does_not_change_operation_but_material_edit_does() -> None:
    direct_index = """--- a/checkout/config.py
+++ b/checkout/config.py
@@ -55 +55 @@
-    return dict(config.get(\"region_aliases\", {}))
+    return dict(config[\"region_aliases\"])
"""
    default_removal = """--- a/checkout/config.py
+++ b/checkout/config.py
@@ -55 +55 @@
-    return dict(config.get(\"region_aliases\", {}))
+    return dict(config.get(\"region_aliases\"))
"""
    assert canonical_digest(canonical_patch_operation_payload_from_text(direct_index)) != canonical_digest(
        canonical_patch_operation_payload_from_text(default_removal)
    )


def test_artifact_admission_rejects_trusted_and_prior_candidate_operation_clones() -> None:
    trusted_clone = replace(
        BUGGY_CANDIDATES[0],
        patch_path="src/bug_cause_inference/p1b/artifacts/real_diff/patches/P1B-BUG-001.patch",
    )
    with pytest.raises(CandidatePatchSemanticError, match="duplicates P1B-BUG-001"):
        validate_artifact_semantic_cohort((trusted_clone,), ())
    prose_only = copy.deepcopy(BUGGY_CANDIDATES[1].metadata)
    prose_only["diversity_rationale"] = "Different prose cannot change patch semantics."
    prior_clone = replace(
        BUGGY_CANDIDATES[1],
        patch_path=BUGGY_CANDIDATES[0].patch_path,
        metadata=prose_only,
    )
    with pytest.raises(CandidatePatchSemanticError, match="duplicates P2A-BUG-001"):
        validate_artifact_semantic_cohort((BUGGY_CANDIDATES[0], prior_clone), ())


def test_patch_semantic_canonicalization_fails_closed_on_ambiguous_transform() -> None:
    ambiguous = patch_text(BUGGY_CANDIDATES[0]) + patch_text(BUGGY_CANDIDATES[4])
    with pytest.raises(CandidatePatchSemanticError, match="exactly one changed file"):
        canonical_patch_operation_payload_from_text(ambiguous)
    unsupported = """--- a/checkout/config.py
+++ b/checkout/config.py
@@ -1 +1 @@
-\"\"\"Configuration helpers for the P1b real-diff artifact baseline.\"\"\"
+\"\"\"Configuration helpers for the reviewed artifact baseline.\"\"\"
"""
    with pytest.raises(CandidatePatchSemanticError, match="actual changed function"):
        canonical_patch_operation_payload_from_text(unsupported)
    with pytest.raises(CandidatePatchSemanticError, match="unsupported unified patch"):
        canonical_patch_operation_payload_from_text("not a unified patch")


def test_bug004_mixed_module_constant_reproduction_is_rejected_not_silently_identical() -> None:
    base = patch_text(BUGGY_CANDIDATES[3])
    assert canonical_digest(canonical_patch_operation_payload_from_text(base)) == (
        "36bc8209347d1232a67479936562981c705ffb3505087f22130650ca8a393024"
    )
    mixed = _bug004_patch_with_module_replacements(
        (
            '    "tax_rates": {"JP": 0.10, "US": 0.07},\n',
            '    "tax_rates": {"JP": 0.10, "US": 0.08},\n',
        )
    )
    with pytest.raises(
        CandidatePatchSemanticError, match="semantic AST edits outside"
    ):
        canonical_patch_operation_payload_from_text(mixed)


@pytest.mark.parametrize(
    "replacement",
    [
        (
            "DEFAULT_CONFIG: dict[str, Any] = {\n",
            "MODULE_SENTINEL = 1\n\nDEFAULT_CONFIG: dict[str, Any] = {\n",
        ),
        (_DEFAULT_CONFIG_BLOCK, ""),
        (
            "DEFAULT_CONFIG: dict[str, Any] = {\n",
            "REVIEW_DEFAULT_CONFIG: dict[str, Any] = {\n",
        ),
    ],
    ids=["assignment_addition", "assignment_removal", "assignment_change"],
)
def test_function_edit_with_module_assignment_edit_is_rejected(
    replacement: tuple[str, str],
) -> None:
    with pytest.raises(
        CandidatePatchSemanticError, match="semantic AST edits outside"
    ):
        canonical_patch_operation_payload_from_text(
            _bug004_patch_with_module_replacements(replacement)
        )


@pytest.mark.parametrize(
    "replacement",
    [
        (
            "from copy import deepcopy\n",
            "import decimal\n\nfrom copy import deepcopy\n",
        ),
        ("from copy import deepcopy\n", ""),
        ("from copy import deepcopy\n", "from copy import copy\n"),
    ],
    ids=["import_addition", "import_removal", "import_change"],
)
def test_function_edit_with_module_import_edit_is_rejected(
    replacement: tuple[str, str],
) -> None:
    with pytest.raises(
        CandidatePatchSemanticError, match="semantic AST edits outside"
    ):
        canonical_patch_operation_payload_from_text(
            _bug004_patch_with_module_replacements(replacement)
        )


@pytest.mark.parametrize(
    "replacement",
    [
        (
            '    "tax_rates": {"JP": 0.10, "US": 0.07},\n',
            '    "tax_rates": {"JP": 0.10, "US": 0.08},\n',
        ),
        (
            '    "feature_flags": {"stack_member_and_coupon": False, "allow_preorder": True},\n',
            '    "feature_flags": {"stack_member_and_coupon": False, "allow_preorder": [True]},\n',
        ),
        ('    "shipping_threshold": 10000,\n', '    "shipping_threshold": 11000,\n'),
    ],
    ids=["nested_mapping", "nested_list", "nested_scalar"],
)
def test_function_edit_with_nested_module_value_mutation_is_rejected(
    replacement: tuple[str, str],
) -> None:
    with pytest.raises(
        CandidatePatchSemanticError, match="semantic AST edits outside"
    ):
        canonical_patch_operation_payload_from_text(
            _bug004_patch_with_module_replacements(replacement)
        )


def test_function_edit_with_module_comments_blank_lines_and_formatting_keeps_identity() -> None:
    formatted = _bug004_patch_with_module_replacements(
        (
            "DEFAULT_CONFIG: dict[str, Any] = {\n",
            "# Formatting-only review annotation.\n\nDEFAULT_CONFIG: dict[str, Any] = {\n",
        ),
        (
            '    "tax_rates": {"JP": 0.10, "US": 0.07},\n',
            '    "tax_rates": {\n        "JP": 0.10,\n        "US": 0.07,\n    },\n',
        ),
    )
    assert canonical_patch_operation_payload_from_text(
        formatted
    ) == canonical_patch_operation_payload_from_text(
        patch_text(BUGGY_CANDIDATES[3])
    )


def test_corrected_actual_cohort_passes_artifact_global_scan() -> None:
    identities = validate_artifact_semantic_cohort(
        BUGGY_CANDIDATES, CLEAN_CANDIDATES
    )
    assert identities == ARTIFACT_PATCH_OPERATION_IDENTITIES
    assert sum(len(cohort) for cohort in identities.values()) == 40


def test_bug004_replacement_is_outcome_free_wrong_default_value_not_keyerror_clone() -> None:
    candidate = BUGGY_CANDIDATES[3]
    assert candidate.variant_id == "P2A-BUG-004"
    assert candidate.metadata["primary_bucket"] == "missing_optional_input"
    assert candidate.metadata["target_functions"] == ["config.get_tax_rate"]
    assert candidate.metadata["trigger_shape"] == "tax_rates mapping is absent for a US lookup"
    assert candidate.metadata["expected_behavior"] == "The reviewed absence fallback 0.0 is returned."
    assert candidate.metadata["actual_behavior"] == "The global configured US rate 0.07 is returned."
    evidence = author_candidate(candidate)
    assert evidence["baseline_ground_truth_status"] == "all_pass"
    assert evidence["candidate_ground_truth_status"] == "required_fail_observed"


def test_candidate_modules_have_no_forbidden_evaluation_dependency() -> None:
    root = repository_path("src/bug_cause_inference/p2a")
    module_paths = [
        root / "candidates.py",
        root / "candidate_oracles.py",
        root / "candidate_authoring.py",
    ]
    forbidden = (
        "bug_cause_inference.p1c",
        "bug_cause_inference.p1d",
        "bug_cause_inference.p2a.evaluation",
        "bug_cause_inference.p2a.reports",
        "bug_cause_inference.p1b.policies",
    )
    for path in module_paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)
        assert not any(
            name == item or name.startswith(item + ".")
            for name in imported
            for item in forbidden
        )


def test_patch_and_oracle_sources_contain_no_variant_hidden_selector() -> None:
    oracle_source = repository_path(
        "src/bug_cause_inference/p2a/candidate_oracles.py"
    ).read_text(encoding="utf-8")
    assert "P2A-BUG-" not in oracle_source
    assert "P2A-CLEAN-" not in oracle_source
    for candidate in (*BUGGY_CANDIDATES, *CLEAN_CANDIDATES):
        text = patch_text(candidate)
        assert candidate.variant_id not in text
        assert "variant_id" not in text


def test_tracked_manifest_is_plain_json_without_nan_or_infinity() -> None:
    parsed = json.loads(repository_path(AUTHORING_MANIFEST_PATH).read_text(encoding="utf-8"))
    assert canonical_digest(parsed)
    assert "NaN" not in serialized_authoring_manifest()
    assert "Infinity" not in serialized_authoring_manifest()
