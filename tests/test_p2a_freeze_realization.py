from __future__ import annotations

import ast
import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from bug_cause_inference.p1b.actions import P1B_ACTION_SPECS
from bug_cause_inference.p2a import freeze_realization as fr
from bug_cause_inference.p2a.adequacy import (
    APPROVED_ACTION_IDS,
    BUGGY_BUCKET_IDS,
    CLEAN_STRESS_FAMILY_IDS,
    ReasonCode,
    canonical_digest,
    clean_family_definitions,
)
from bug_cause_inference.p2a.candidate_authoring import (
    AUTHORING_MANIFEST_PATH,
    repository_path,
)
from bug_cause_inference.p2a.candidate_oracles import oracle_definition_digest
from bug_cause_inference.p2a.candidates import CANDIDATE_IDS
from bug_cause_inference.p2a.freeze import validate_freeze_draft


FREEZE_TIMESTAMP = "2026-07-17T12:34:56Z"
EXPECTED_CASE_ACTION_BY_CANDIDATE = {
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


@pytest.fixture(scope="module")
def artifact_manifest() -> dict[str, Any]:
    return fr.build_artifact_manifest()


@pytest.fixture(scope="module")
def contract_payloads(artifact_manifest: dict[str, Any]) -> dict[str, Any]:
    return fr.build_contract_payloads(artifact_manifest)


@pytest.fixture(scope="module")
def official_bundle() -> dict[str, Any]:
    return fr.realize_official_freeze(FREEZE_TIMESTAMP)


def _json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    ).encode("utf-8")


def _walk(value: Any):
    yield value
    if type(value) is dict:
        for key, child in value.items():
            yield key
            yield from _walk(child)
    elif type(value) is list:
        for child in value:
            yield from _walk(child)


def test_accepted_base_file_hashes_are_exact() -> None:
    expected = {
        "src/bug_cause_inference/p2a/adequacy.py": (
            "bdef79f373a6398fa6756f1b77661b4dbd394d5470ea5ca84b80e0286ea6d400"
        ),
        "src/bug_cause_inference/p2a/freeze.py": (
            "ec03b5ed7c7f1e3297d00cbb93680b1d2712656f445b074e7568883cc05eaad1"
        ),
        "tests/test_p2a_adequacy.py": (
            "49bf9e9a1d9177bfecc2a0b51ddeab64c2d52c5c31c513e4618fcd6f18b50f6d"
        ),
        "tests/test_p2a_freeze.py": (
            "2664bfc1a88141d9f0bef1933d318367bee7abc9917195c168e1353f965399e9"
        ),
    }
    for path, digest in expected.items():
        assert hashlib.sha256(repository_path(path).read_bytes()).hexdigest() == digest


def test_artifact_manifest_binds_exact_accepted_cohort(
    artifact_manifest: dict[str, Any],
) -> None:
    assert artifact_manifest["schema_version"] == "p2a_artifact_manifest.v1"
    assert artifact_manifest["dataset_identity"] == {
        "schema_version": "p2a_same_domain_dataset.v1",
        "benchmark_id": "p2a_checkout_pricing_same_domain_expansion_v1",
        "candidate_manifest_digest": fr.EXPECTED_CANDIDATE_MANIFEST_DIGEST,
    }
    cohort = artifact_manifest["cohort_identity"]
    assert cohort["variant_ids"] == list(CANDIDATE_IDS)
    assert (cohort["variant_count"], cohort["buggy_count"], cohort["clean_count"]) == (
        15,
        10,
        5,
    )
    assert cohort["buggy_bucket_ids"] == list(BUGGY_BUCKET_IDS)
    assert cohort["clean_family_definitions"] == clean_family_definitions()
    assert [
        item["primary_taxonomy_id"] for item in artifact_manifest["candidates"][:10]
    ] == [bucket for bucket in BUGGY_BUCKET_IDS for _ in range(2)]
    assert [
        item["primary_taxonomy_id"] for item in artifact_manifest["candidates"][10:]
    ] == list(CLEAN_STRESS_FAMILY_IDS)
    assert all(
        item["metadata"]["primary_bucket"] == "clean_false_positive"
        for item in artifact_manifest["candidates"][10:]
    )
    adjacent_by_family = {
        item["family_id"]: item["adjacent_buggy_bucket_id"]
        for item in clean_family_definitions()
    }
    assert all(
        item["metadata"]["adjacent_buggy_bucket_id"]
        == adjacent_by_family[item["primary_taxonomy_id"]]
        for item in artifact_manifest["candidates"][10:]
    )


def test_authoring_manifest_and_all_patch_oracle_identities_are_exact(
    artifact_manifest: dict[str, Any],
) -> None:
    identity = artifact_manifest["authoring_manifest_identity"]
    assert identity["canonical_digest"] == fr.EXPECTED_AUTHORING_MANIFEST_DIGEST
    assert identity["python_generated_semantic_agreement"] is True
    assert identity["python_generated_byte_agreement"] is True
    assert identity["status"] == "review_pending"
    assert repository_path(AUTHORING_MANIFEST_PATH).read_bytes() == (
        repository_path(AUTHORING_MANIFEST_PATH)
        .read_text(encoding="utf-8")
        .encode("utf-8")
    )
    for candidate in artifact_manifest["candidates"]:
        patch = candidate["patch_identity"]
        assert (
            hashlib.sha256(repository_path(patch["path"]).read_bytes()).hexdigest()
            == patch["raw_sha256"]
        )
        oracle = candidate["oracle_identity"]
        assert [
            record["oracle_id"] for record in oracle["definition_records"]
        ] == oracle["oracle_ids"]
        assert (
            oracle_definition_digest(oracle["definition_records"])
            == oracle["definition_digest"]
        )


def test_registry_and_compatibility_identities_remain_exact(
    artifact_manifest: dict[str, Any], official_bundle: dict[str, Any]
) -> None:
    assert artifact_manifest["trusted_reference_registry_identity"][
        "registry_digest"
    ] == (fr.EXPECTED_TRUSTED_REFERENCE_REGISTRY_DIGEST)
    assert artifact_manifest["coverage_gap_registry_identity"]["registry_digest"] == (
        fr.EXPECTED_COVERAGE_GAP_REGISTRY_DIGEST
    )
    compatibility = official_bundle["freeze_payload"]["accepted_input_identities"][
        "legacy_compatibility"
    ]
    assert compatibility == {
        "status": "valid",
        "expected_pair_count": 150,
        "observed_pair_count": 150,
        "matched_pair_count": 150,
        "mismatch_count": 0,
        "runtime_digest": fr.EXPECTED_LEGACY_RUNTIME_DIGEST,
        "catalog_digest": fr.EXPECTED_LEGACY_CATALOG_DIGEST,
        "artifact_digest": fr.EXPECTED_LEGACY_ARTIFACT_DIGEST,
    }


def test_tracked_artifact_manifest_is_semantic_and_byte_exact(
    artifact_manifest: dict[str, Any],
) -> None:
    path = repository_path(fr.ARTIFACT_MANIFEST_PATH)
    assert json.loads(path.read_text(encoding="utf-8")) == artifact_manifest
    assert path.read_bytes() == _json_bytes(artifact_manifest)


def test_contract_payload_versions_and_digests_are_recomputable(
    contract_payloads: dict[str, Any], official_bundle: dict[str, Any]
) -> None:
    identities = fr.contract_identities(contract_payloads)
    expected_versions = {
        "adapter": ("contract_version", "p2a_patch_grounded_adapter.v1"),
        "catalog": ("catalog_version", "p2a_action_test_catalog.v1"),
        "policy": ("identity_version", "p2a_policy_registry_identity.v1"),
        "settings": ("identity_version", "p2a_fixed_settings_identity.v1"),
        "metric": ("identity_version", "p2a_metric_contract_identity.v1"),
        "serializer": ("identity_version", "p2a_serializer_contract_identity.v1"),
    }
    frozen = official_bundle["freeze_payload"]["outcome_free_contracts"]
    for name, (field, version) in expected_versions.items():
        assert contract_payloads[name][field] == version
        assert identities[name]["digest"] == canonical_digest(contract_payloads[name])
        assert frozen[name] == {
            "identity": identities[name],
            "payload": contract_payloads[name],
        }


def test_catalog_has_exact_stable_cases_actions_and_action_specs(
    contract_payloads: dict[str, Any], artifact_manifest: dict[str, Any]
) -> None:
    catalog = contract_payloads["catalog"]
    expected_cases = []
    for candidate in artifact_manifest["candidates"]:
        action = EXPECTED_CASE_ACTION_BY_CANDIDATE[candidate["variant_id"]]
        for oracle_id in candidate["oracle_identity"]["oracle_ids"]:
            expected_cases.append((candidate["variant_id"], oracle_id, action))
    observed_cases = [
        (item["candidate_id"], item["oracle_id"], item["action_id"])
        for item in catalog["cases"]
    ]
    assert catalog["case_count"] == len(expected_cases) == 24
    assert observed_cases == expected_cases
    assert catalog["variant_specific_hidden_selection_allowed"] is False
    assert [item["action_id"] for item in catalog["approved_action_specs"]] == list(
        APPROVED_ACTION_IDS
    )
    for frozen, action_id in zip(
        catalog["approved_action_specs"], APPROVED_ACTION_IDS, strict=True
    ):
        live = P1B_ACTION_SPECS[action_id]
        assert frozen == {
            "action_id": action_id,
            "cost": live.cost,
            "observation_type": live.observation_type,
            "strong_causes": list(live.strong_causes),
            "discovery_power": live.discovery_power,
            "location_power": live.location_power,
        }


def test_catalog_duplicate_missing_and_reordered_cases_are_rejected(
    monkeypatch: pytest.MonkeyPatch,
    artifact_manifest: dict[str, Any],
    contract_payloads: dict[str, Any],
) -> None:
    monkeypatch.setattr(fr, "validate_artifact_manifest", lambda value: value)
    mutations = []
    duplicate = deepcopy(contract_payloads)
    duplicate["catalog"]["cases"][1] = deepcopy(duplicate["catalog"]["cases"][0])
    mutations.append(duplicate)
    missing = deepcopy(contract_payloads)
    missing["catalog"]["cases"].pop()
    missing["catalog"]["case_count"] -= 1
    mutations.append(missing)
    reordered = deepcopy(contract_payloads)
    reordered["catalog"]["cases"][0], reordered["catalog"]["cases"][1] = (
        reordered["catalog"]["cases"][1],
        reordered["catalog"]["cases"][0],
    )
    mutations.append(reordered)
    for mutation in mutations:
        with pytest.raises(fr.FreezeRealizationError, match="predeclared outcome-free"):
            fr.validate_contract_payloads(mutation, artifact_manifest)


def test_policy_settings_metric_and_serializer_contract_boundaries(
    contract_payloads: dict[str, Any],
) -> None:
    assert contract_payloads["policy"]["formal_policy_ids"] == list(
        fr.FORMAL_POLICY_IDS
    )
    assert contract_payloads["policy"]["excluded_policy_ids"] == [
        "random_action",
        "state_sequence_guard",
    ]
    assert contract_payloads["settings"]["settings"] == {
        "budget_limit": 12,
        "max_steps": 6,
        "failure_cost": 14,
        "bug_presence_threshold": 0.75,
        "no_bug_probability_threshold": 0.8,
        "location_top1_threshold": 0.5,
        "cause_top1_threshold": 0.6,
        "min_expected_utility_per_cost": 0.03,
        "rng_seed": 0,
    }
    assert contract_payloads["settings"]["stop_precedence"] == list(fr.STOP_PRECEDENCE)
    metric = contract_payloads["metric"]
    assert metric["buggy_result_identities"] == list(fr.BUGGY_RESULT_IDENTITIES)
    assert metric["clean_result_identities"] == list(fr.CLEAN_RESULT_IDENTITIES)
    assert metric["reference_distribution"]["bucket_weight"] == {
        "numerator": 1,
        "denominator": 5,
    }
    assert (
        metric["reference_distribution"]["variant_pooled_primary_weighting_allowed"]
        is False
    )
    assert metric["secondary_buggy_metrics"]["cost_to_first_failure_miss_penalty"] == 14
    assert metric["calculated_during_freeze"] is False
    serializer = contract_payloads["serializer"]
    assert serializer["report_schema_version"] == (
        "p2a_benchmark_evidence_expansion_report.v1"
    )
    assert serializer["serializer_implemented_in_this_slice"] is False
    assert serializer["formats"] == ["json", "markdown"]


def test_actual_official_draft_is_valid_and_exact(
    official_bundle: dict[str, Any],
) -> None:
    payload = official_bundle["freeze_payload"]
    result = validate_freeze_draft(payload["validated_official_draft"])
    assert result.status == "draft_valid"
    assert (result.variant_count, result.buggy_count, result.clean_count) == (15, 10, 5)
    assert result.candidate_manifest_digest == fr.EXPECTED_CANDIDATE_MANIFEST_DIGEST
    assert payload["draft_validation"] == {
        "status": result.status,
        "draft_digest": result.draft_digest,
        "candidate_manifest_digest": result.candidate_manifest_digest,
        "variant_count": 15,
        "buggy_count": 10,
        "clean_count": 5,
    }


@pytest.mark.parametrize(
    "timestamp",
    (
        None,
        "<user supplied UTC timestamp>",
        "2026-07-17T12:34:56+00:00",
        "2026-07-17 12:34:56Z",
        "2026-7-17T12:34:56Z",
    ),
)
def test_missing_placeholder_offset_and_noncanonical_timestamps_are_rejected(
    official_bundle: dict[str, Any], timestamp: Any
) -> None:
    draft = deepcopy(official_bundle["freeze_payload"]["validated_official_draft"])
    draft["freeze_timestamp"] = timestamp
    with pytest.raises(Exception) as error:
        validate_freeze_draft(draft)
    assert getattr(error.value, "issue", None) is not None
    assert error.value.issue.code in {
        ReasonCode.WRONG_TYPE.value,
        ReasonCode.WRONG_IDENTITY.value,
    }


def test_timestamp_changes_official_payload_digest(
    official_bundle: dict[str, Any],
) -> None:
    original = official_bundle["freeze_payload"]
    changed = deepcopy(original)
    changed["freeze_timestamp"] = "2026-07-17T12:34:57Z"
    assert canonical_digest(changed) != canonical_digest(original)


def test_contract_single_mutations_change_digest_and_are_rejected(
    monkeypatch: pytest.MonkeyPatch,
    artifact_manifest: dict[str, Any],
    contract_payloads: dict[str, Any],
) -> None:
    monkeypatch.setattr(fr, "validate_artifact_manifest", lambda value: value)
    paths = {
        "adapter": ("semantics", "source"),
        "catalog": ("application_scope",),
        "policy": ("accepted_runtime_digest",),
        "settings": ("settings", "budget_limit"),
        "metric": ("contract_scope",),
        "serializer": ("source_model",),
    }
    for name, path in paths.items():
        changed = deepcopy(contract_payloads)
        target = changed[name]
        for key in path[:-1]:
            target = target[key]
        old_digest = canonical_digest(changed[name])
        final = path[-1]
        target[final] = 13 if final == "budget_limit" else f"{target[final]} changed"
        assert canonical_digest(changed[name]) != old_digest
        with pytest.raises(fr.FreezeRealizationError, match="predeclared outcome-free"):
            fr.validate_contract_payloads(changed, artifact_manifest)


def test_candidate_patch_oracle_order_taxonomy_and_registry_mutations_change_identity(
    artifact_manifest: dict[str, Any],
) -> None:
    mutations = []
    candidate_metadata = deepcopy(artifact_manifest)
    candidate_metadata["candidates"][0]["metadata"]["expected_behavior"] += " changed"
    mutations.append(candidate_metadata)
    patch_hash = deepcopy(artifact_manifest)
    patch_hash["candidates"][0]["patch_identity"]["raw_sha256"] = "0" * 64
    mutations.append(patch_hash)
    oracle = deepcopy(artifact_manifest)
    oracle["candidates"][0]["oracle_identity"]["definition_records"][0][
        "specification_rule"
    ] += " changed"
    mutations.append(oracle)
    order = deepcopy(artifact_manifest)
    order["cohort_identity"]["variant_ids"][0:2] = reversed(
        order["cohort_identity"]["variant_ids"][0:2]
    )
    mutations.append(order)
    taxonomy = deepcopy(artifact_manifest)
    taxonomy["cohort_identity"]["buggy_bucket_ids"].reverse()
    mutations.append(taxonomy)
    registry = deepcopy(artifact_manifest)
    registry["coverage_gap_registry_identity"]["registry_digest"] = "0" * 64
    mutations.append(registry)
    original = canonical_digest(artifact_manifest)
    assert all(canonical_digest(mutation) != original for mutation in mutations)


def test_artifact_unknown_path_nonfinite_and_source_drift_are_rejected(
    artifact_manifest: dict[str, Any],
) -> None:
    unknown = deepcopy(artifact_manifest)
    unknown["unknown"] = True
    with pytest.raises(fr.FreezeRealizationError, match="differs from accepted"):
        fr.validate_artifact_manifest(unknown)
    absolute = deepcopy(artifact_manifest)
    absolute["candidates"][0]["patch_identity"]["path"] = "C:/local/patch.patch"
    with pytest.raises(Exception):
        fr.validate_artifact_manifest(absolute)
    nonfinite = deepcopy(artifact_manifest)
    nonfinite["cohort_identity"]["variant_count"] = float("nan")
    with pytest.raises(Exception):
        fr.validate_artifact_manifest(nonfinite)


def test_official_bundle_wrapper_digest_status_and_gates(
    official_bundle: dict[str, Any],
) -> None:
    assert official_bundle["schema_version"] == "p2a_official_freeze_bundle.v1"
    assert official_bundle["status"] == "freeze_realized_pending_independent_review"
    payload = official_bundle["freeze_payload"]
    assert official_bundle["official_freeze_digest"] == canonical_digest(payload)
    assert payload["provenance"] == {
        "candidate_policy_outcome_observed": False,
        "evaluation_authorized": False,
    }
    assert payload["independent_review_gate"] == {
        "gate_version": "p2a_frozen_dataset_independent_review.v1",
        "required": True,
        "status": "pending",
    }
    assert payload["draft_validation"]["status"] == "draft_valid"


def test_official_bundle_rejects_wrong_wrapper_digest_version_and_status(
    official_bundle: dict[str, Any],
) -> None:
    digest = deepcopy(official_bundle)
    digest["official_freeze_digest"] = "0" * 64
    with pytest.raises(fr.FreezeRealizationError, match="payload digest mismatch"):
        fr.validate_official_freeze_bundle(digest)
    version = deepcopy(official_bundle)
    version["schema_version"] = "p2a_official_freeze_bundle.v0"
    with pytest.raises(fr.FreezeRealizationError, match="wrong version"):
        fr.validate_official_freeze_bundle(version)
    status = deepcopy(official_bundle)
    status["status"] = "valid_for_evaluation"
    with pytest.raises(fr.FreezeRealizationError, match="wrong status"):
        fr.validate_official_freeze_bundle(status)


def test_official_bundle_actual_validation_succeeds(
    official_bundle: dict[str, Any],
) -> None:
    assert fr.validate_official_freeze_bundle(official_bundle) == official_bundle


def test_tracked_official_bundle_is_semantic_and_byte_exact(
    official_bundle: dict[str, Any],
) -> None:
    path = repository_path(fr.OFFICIAL_FREEZE_BUNDLE_PATH)
    assert json.loads(path.read_text(encoding="utf-8")) == official_bundle
    assert path.read_bytes() == _json_bytes(official_bundle)


def test_no_evaluation_claim_or_policy_outcome_material_leaks_into_candidate_inputs(
    artifact_manifest: dict[str, Any], official_bundle: dict[str, Any]
) -> None:
    forbidden_keys = {
        "policy_trace",
        "posterior",
        "selected_action",
        "cost_result",
        "matrix",
        "loss",
        "worst_bucket",
        "clean_false_positive_outcome",
        "review_accepted",
        "valid_for_evaluation",
        "evaluation_ready",
    }
    assert not (
        set(item for item in _walk(artifact_manifest) if type(item) is str)
        & forbidden_keys
    )
    payload = official_bundle["freeze_payload"]
    assert not (
        set(
            item
            for item in _walk(payload["validated_official_draft"])
            if type(item) is str
        )
        & forbidden_keys
    )
    assert official_bundle["status"] not in {
        "accepted",
        "review_accepted",
        "valid_for_evaluation",
        "evaluation_ready",
    }


def test_source_has_no_current_time_policy_runner_evaluator_or_report_dependency() -> (
    None
):
    source_path = Path(fr.__file__)
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imported = []
    attributes = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
        elif isinstance(node, ast.Attribute):
            attributes.append(node.attr)
    assert not any(name in {"datetime", "time"} for name in imported)
    assert not ({"now", "utcnow", "today"} & set(attributes))
    forbidden_modules = (
        "bug_cause_inference.p1b.execution",
        "bug_cause_inference.p1b.evaluation",
        "bug_cause_inference.p1b.policies",
        "bug_cause_inference.p1c",
        "bug_cause_inference.p1d",
        "bug_cause_inference.p2a.evaluation",
        "bug_cause_inference.p2a.reports",
    )
    assert not any(
        name == forbidden or name.startswith(f"{forbidden}.")
        for name in imported
        for forbidden in forbidden_modules
    )
