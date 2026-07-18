"""Ground-truth-informed fixed-catalog solvability ceiling for accepted P2a.

The diagnostic is deliberately non-deployable.  It exhaustively applies the
accepted frozen catalog to each accepted P2a buggy patch, then compares the
resulting direct detection certificates with saved P2a policy outcomes.  It
does not run a policy, alter the accepted catalog, or update P2a evidence.
"""

from __future__ import annotations

import hashlib
import json
import math
from contextlib import contextmanager
from copy import deepcopy
from fractions import Fraction
from functools import lru_cache
from pathlib import Path, PurePosixPath
from typing import Any, Iterator, Mapping

from bug_cause_inference.p1b.actions import P1B_ACTION_SPECS
from bug_cause_inference.p1b.dataset import LOCATION_CANDIDATES
from bug_cause_inference.p1b.models import (
    P1B_CAUSE_CATEGORIES,
    P1B_FIX_INTENT_CATEGORIES,
    P1BSettings,
    uniform_distribution,
)
from bug_cause_inference.p1b import policies as p1b_policies
from bug_cause_inference.p2a import evaluation as p2a_evaluation
from bug_cause_inference.p2a.adequacy import (
    BUGGY_BUCKET_IDS,
    canonical_digest as p2a_canonical_digest,
    validate_portable_value,
)
from bug_cause_inference.p2a.candidate_authoring import (
    _candidate_modules,
    load_tracked_authoring_manifest,
)
from bug_cause_inference.p2a.candidate_oracles import run_oracle_record
from bug_cause_inference.p2a.candidates import (
    BUGGY_CANDIDATES,
    CANDIDATES,
    CandidateDefinition,
)
from bug_cause_inference.p2a.freeze_realization import (
    load_tracked_artifact_manifest,
    load_tracked_official_freeze_bundle,
)
from bug_cause_inference.p2a.reports import (
    summary_from_markdown as p2a_summary_from_markdown,
    validate_report_summary as validate_p2a_report_summary,
)


SCHEMA_VERSION = "p2b_fixed_catalog_solvability_ceiling.v1"
ANALYSIS_PHASE = "p2b_fixed_catalog_solvability_ceiling"
REPORT_ROLE = "analysis_only_ground_truth_informed_non_deployable_diagnostic"
VALID_STATUS = "valid"
INVALID_STATUS = "invalid_inconclusive"

MERGE_COMMIT = "536485d8ea042f4e84be1980ca5f54f343da18f2"
ACCEPTED_P2A_HEAD = "2a2dcf05f98ab493c757f659c44b2248a3e3491f"
EXPECTED_CANDIDATE_MANIFEST_DIGEST = (
    "97c2d0c0379d69010195a4b7448137e566214d88638b0f7642ee59677389cd47"
)
EXPECTED_ARTIFACT_MANIFEST_DIGEST = (
    "674c3f56fbd2d4148a3e63367e4bba63ed7de634f5a219ec82a79a1c878a9544"
)
EXPECTED_OFFICIAL_FREEZE_DIGEST = (
    "d335f3f3a4731ee0f4d9b4648e2085eb9c687b7b2a3065d2b08eb2f65370cd9d"
)
EXPECTED_SAVED_OUTCOME_DIGEST = (
    "2a1b09b38de6b2e17943726508ebc1f6728290506165cfa263a78dbb57383755"
)
EXPECTED_P2A_SUMMARY_DIGEST = (
    "3dea5aaf38e1d9a46fd1a9ed973cb02c3fabf7ec933f2bb1c6df4f97446a9629"
)
EXPECTED_P2A_JSON_SHA256 = (
    "d7e69fa62513f5bbae22d570e39b841401f5110b6cd1e45701c53393eb0ef3df"
)
EXPECTED_P2A_MARKDOWN_SHA256 = (
    "017c5e3d9281e59e0b115a825a5f0e08f90a5e15a1e331514296adf443a2808a"
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
ACTION_IDS = tuple(P1B_ACTION_SPECS)
BUCKET_IDS = tuple(BUGGY_BUCKET_IDS)
BUGGY_VARIANT_IDS = tuple(candidate.variant_id for candidate in BUGGY_CANDIDATES)

P2A_JSON_RELATIVE_PATH = PurePosixPath(
    "src/bug_cause_inference/p2a/artifacts/evaluation/"
    "p2a_benchmark_evidence_expansion_v1.json"
)
P2A_MARKDOWN_RELATIVE_PATH = PurePosixPath(
    "src/bug_cause_inference/p2a/artifacts/evaluation/"
    "p2a_benchmark_evidence_expansion_v1.md"
)

_ACCEPTED_FILE_IDENTITIES = {
    "p1b_actions_source": (
        "src/bug_cause_inference/p1b/actions.py",
        "cb191a6834f75e87835a2f9b3e164b2e05b48a6168a515455be57680f3d738fe",
    ),
    "p1b_execution_source": (
        "src/bug_cause_inference/p1b/execution.py",
        "820847852f623f91870c824c5218bf5a0c20643868f99131b40c63413b992a91",
    ),
    "p1b_dataset_source": (
        "src/bug_cause_inference/p1b/dataset.py",
        "2c164076148d590c86893da4bfeaedfc82f09c4df5ef7f461c892d2438e17050",
    ),
    "p1b_models_source": (
        "src/bug_cause_inference/p1b/models.py",
        "895a9be33fd8502b8532554c4ca12b92db86b08a3074b54a8233d7ee25104fde",
    ),
    "p1b_policies_source": (
        "src/bug_cause_inference/p1b/policies.py",
        "b039dff408f4fa26f6de86ffe1924fad6dd652c68092bcc08e59e8aa478e4ecd",
    ),
    "p1b_real_diff_source": (
        "src/bug_cause_inference/p1b/real_diff.py",
        "b9b59a58ecf08a251e4281e3c7ffcd0f1b8f6b1707dbac6c98660b816593f4f4",
    ),
    "p2a_adequacy_source": (
        "src/bug_cause_inference/p2a/adequacy.py",
        "bdef79f373a6398fa6756f1b77661b4dbd394d5470ea5ca84b80e0286ea6d400",
    ),
    "p2a_candidate_authoring_source": (
        "src/bug_cause_inference/p2a/candidate_authoring.py",
        "c5a8f6801901d535c2bbde61603aa4de66c9d6ccc2005c30e13592733ae46701",
    ),
    "p2a_candidate_oracles_source": (
        "src/bug_cause_inference/p2a/candidate_oracles.py",
        "0361aefc33fd6a5d0be2dc8fc8e79e1ae290886568113f824598ccbe154c1732",
    ),
    "p2a_candidates_source": (
        "src/bug_cause_inference/p2a/candidates.py",
        "47e0bfccff06819efc66384d9528be0828ca95943f63498bca1eb6aed68f6351",
    ),
    "p2a_freeze_realization_source": (
        "src/bug_cause_inference/p2a/freeze_realization.py",
        "a8c1dea78ad1e592c8823219aa3e074b3284ec48eac722bc7979d993ff04db1b",
    ),
    "p2a_evaluation_source": (
        "src/bug_cause_inference/p2a/evaluation.py",
        "02db9095416885f865229f13ba52d2c7e1d794fac07b5cc2e1651d6593866785",
    ),
    "p2a_reports_source": (
        "src/bug_cause_inference/p2a/reports.py",
        "51c5b873a5562badbb4bc5653686c4b94f3cd7f7f2d2f03f37482c11f6d16992",
    ),
    "p2a_authoring_manifest": (
        "src/bug_cause_inference/p2a/artifacts/candidates/authoring_manifest.json",
        "ccf05cd8c4179ee2b84b68dffa1d576e59f717e4fd314a4cccb0136d9ffb7e3b",
    ),
    "p2a_artifact_manifest": (
        "src/bug_cause_inference/p2a/artifacts/freeze/artifact_manifest.json",
        "ff519a4f5bd7985e0b8f3929fcaa0ded3bd98f742e52bb85d7866f21a2cf1b0d",
    ),
    "p2a_official_freeze_bundle": (
        "src/bug_cause_inference/p2a/artifacts/freeze/official_freeze_bundle.json",
        "8a5197288c60329af2667fba8c541edd39ccc068b3ecf6393afdaddf8ebdb5a4",
    ),
    "p2a_evaluation_json": (
        P2A_JSON_RELATIVE_PATH.as_posix(),
        EXPECTED_P2A_JSON_SHA256,
    ),
    "p2a_evaluation_markdown": (
        P2A_MARKDOWN_RELATIVE_PATH.as_posix(),
        EXPECTED_P2A_MARKDOWN_SHA256,
    ),
}

_ACCEPTED_FILE_IDENTITIES.update(
    {
        "p2a_candidate_patch_bug_001": (
            "src/bug_cause_inference/p2a/artifacts/candidates/patches/P2A-BUG-001.patch",
            "fb828c07825746dab12831dc90504b4471894e4d24ae5381425e26a60d56ecb1",
        ),
        "p2a_candidate_patch_bug_002": (
            "src/bug_cause_inference/p2a/artifacts/candidates/patches/P2A-BUG-002.patch",
            "57168b75361ff6ca8039aa41a0326edc0136758dabb78329f8ddc2eaf3a10cea",
        ),
        "p2a_candidate_patch_bug_003": (
            "src/bug_cause_inference/p2a/artifacts/candidates/patches/P2A-BUG-003.patch",
            "68cdd7a8b9d5e1f4fac818d16fdcb7d12c999d40e2bd480d4b962449740c4a92",
        ),
        "p2a_candidate_patch_bug_004": (
            "src/bug_cause_inference/p2a/artifacts/candidates/patches/P2A-BUG-004.patch",
            "62e7bc6bc3f9855299f7413d3530373f13008a6658682285dbb44af2bfe4a2cf",
        ),
        "p2a_candidate_patch_bug_005": (
            "src/bug_cause_inference/p2a/artifacts/candidates/patches/P2A-BUG-005.patch",
            "8bcbc4fcdccd41ffd92fe27fa25a8f6a0d95a66770832b779c35fa837d62c147",
        ),
        "p2a_candidate_patch_bug_006": (
            "src/bug_cause_inference/p2a/artifacts/candidates/patches/P2A-BUG-006.patch",
            "095a4ecc21fb5408aceaf62f009e113ccaecff1bd81a2455ab3665bb8ef0cc87",
        ),
        "p2a_candidate_patch_bug_007": (
            "src/bug_cause_inference/p2a/artifacts/candidates/patches/P2A-BUG-007.patch",
            "85646fa091547497bc12f523a4f6f95d6cda5d07f63ec7b66327cdeda77f2c6f",
        ),
        "p2a_candidate_patch_bug_008": (
            "src/bug_cause_inference/p2a/artifacts/candidates/patches/P2A-BUG-008.patch",
            "7c11b70025dcfdef22898103a8656f2d8afa6d492403ac24c52c075967cb374c",
        ),
        "p2a_candidate_patch_bug_009": (
            "src/bug_cause_inference/p2a/artifacts/candidates/patches/P2A-BUG-009.patch",
            "68903ccc686878bdae8b73489596978006c2a422ed6ac17bbbb5d7db88c45030",
        ),
        "p2a_candidate_patch_bug_010": (
            "src/bug_cause_inference/p2a/artifacts/candidates/patches/P2A-BUG-010.patch",
            "843ec18c88a2fcfd45e8ea7a04c4c5302472b9856cc3fe3a0c5b793672eeffd7",
        ),
        "p2a_candidate_patch_clean_001": (
            "src/bug_cause_inference/p2a/artifacts/candidates/patches/P2A-CLEAN-001.patch",
            "c0a1b7d75e313d91ec0653ddd361f926e1f69ad5025e78878e80aa114c8e3caa",
        ),
        "p2a_candidate_patch_clean_002": (
            "src/bug_cause_inference/p2a/artifacts/candidates/patches/P2A-CLEAN-002.patch",
            "ef17bf8a5eb330d52e7ef9b122c4b574b01141bf23d15b6bc90fefa25ddd39f1",
        ),
        "p2a_candidate_patch_clean_003": (
            "src/bug_cause_inference/p2a/artifacts/candidates/patches/P2A-CLEAN-003.patch",
            "2ab2975d1537a7ea841ca2744515020f12d914b8a88668c967bcd664d64adea9",
        ),
        "p2a_candidate_patch_clean_004": (
            "src/bug_cause_inference/p2a/artifacts/candidates/patches/P2A-CLEAN-004.patch",
            "eb614f960d83f19a7ddccfc4f7162397f008c42dd2e2089cb3c09753c468b65d",
        ),
        "p2a_candidate_patch_clean_005": (
            "src/bug_cause_inference/p2a/artifacts/candidates/patches/P2A-CLEAN-005.patch",
            "b78e400beeffcd5a9a9c84bf39c25f3b67a4b2c03eb41605700806b9331c8778",
        ),
        "p1b_baseline_checkout_init": (
            "src/bug_cause_inference/p1b/artifacts/real_diff/baseline/checkout/__init__.py",
            "41234f3dc364631d4c77ac22af1f07de9099314b0e69551ef0300b00df4f6ae5",
        ),
        "p1b_baseline_checkout_cart": (
            "src/bug_cause_inference/p1b/artifacts/real_diff/baseline/checkout/cart.py",
            "350cd07ed621cc22ba78e5915d4e956123e75d7246858f3502cfe9a7f9092e93",
        ),
        "p1b_baseline_checkout_config": (
            "src/bug_cause_inference/p1b/artifacts/real_diff/baseline/checkout/config.py",
            "548a57f4ecd3f85e922fc62901d4b5a3a0c9f33cf6da6c3a15137f3dab83c231",
        ),
        "p1b_baseline_checkout_discounts": (
            "src/bug_cause_inference/p1b/artifacts/real_diff/baseline/checkout/discounts.py",
            "4900a6cd8a14c87d2b2a66dfa6bb0017adfdfdd9513f3c08d1104612ec945ea2",
        ),
        "p1b_baseline_checkout_inventory": (
            "src/bug_cause_inference/p1b/artifacts/real_diff/baseline/checkout/inventory.py",
            "a62be8ae4c24b43adfc38da8e9c695483cfe80230102fc3dde55225bfc9b00b9",
        ),
        "p1b_baseline_checkout_shipping": (
            "src/bug_cause_inference/p1b/artifacts/real_diff/baseline/checkout/shipping.py",
            "f0549311d9b41d298185a366ac92943b9b62eef75cc768fcccdc4fa0a380b439",
        ),
    }
)

_TOP_LEVEL_FIELDS = (
    "schema_version",
    "analysis_phase",
    "report_role",
    "validation_status",
    "input_identity",
    "execution_boundary",
    "dataset_summary",
    "formal_policy_ids",
    "excluded_policy_ids",
    "bucket_ids",
    "action_specs",
    "definitions",
    "variant_diagnostics",
    "bucket_diagnostics",
    "policy_comparison",
    "overall_diagnostic",
    "software_acceptance",
    "result_acceptance",
    "documentation_acceptance",
    "limitations",
    "non_claims",
    "notes",
)
_CASE_RESULT_FIELDS = ("case_id", "candidate_id", "action_id", "passed")
_VARIANT_FIELDS = (
    "variant_id",
    "bucket_id",
    "catalog_case_support_count",
    "catalog_case_results",
    "case_results_digest",
    "owned_oracle_case_ids",
    "owned_oracle_reachable",
    "detecting_action_ids",
    "detecting_cases_by_action",
    "minimum_detecting_cost",
    "minimum_cost_action_ids",
    "ceiling_witness_action_id",
    "initial_common_stop",
    "budget_feasible",
    "ceiling_discovered",
    "saved_policy_outcomes",
    "policy_classifications",
)
_INVALID_FIELDS = (
    "schema_version",
    "analysis_phase",
    "report_role",
    "validation_status",
    "reason_codes",
    "input_identity",
    "software_acceptance",
    "result_acceptance",
    "documentation_acceptance",
    "non_claims",
)


class P2BDiagnosticError(ValueError):
    """Raised when a P2b input or derived contract is invalid."""


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _repository_path(relative_path: str | PurePosixPath) -> Path:
    parsed = PurePosixPath(relative_path)
    if parsed.is_absolute() or ".." in parsed.parts:
        raise P2BDiagnosticError("input path must be repository-relative")
    root = _repository_root().resolve()
    target = root.joinpath(*parsed.parts).resolve()
    if target != root and root not in target.parents:
        raise P2BDiagnosticError("input path escapes the repository")
    return target


def _identity_hashes(data: bytes) -> tuple[str, str]:
    """Return portable LF-canonical and exact working-tree SHA-256 values."""

    canonical = data.replace(b"\r\n", b"\n")
    return hashlib.sha256(canonical).hexdigest(), hashlib.sha256(data).hexdigest()


def _hash_identity_file(path: Path) -> tuple[str, str]:
    return _identity_hashes(path.read_bytes())


def _json_bytes(value: Any, *, pretty: bool = False) -> bytes:
    if pretty:
        text = json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2)
    else:
        text = json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        )
    return text.encode("utf-8")


def canonical_rows_digest(rows: list[dict[str, Any]]) -> str:
    """Return the SHA-256 of canonical ordered case-result rows."""

    for index, row in enumerate(rows):
        if type(row) is not dict or tuple(row) != _CASE_RESULT_FIELDS:
            raise P2BDiagnosticError(f"catalog_case_results[{index}] has wrong fields")
        if type(row["passed"]) is not bool:
            raise P2BDiagnosticError(
                f"catalog_case_results[{index}].passed must be an exact bool"
            )
        for field in _CASE_RESULT_FIELDS[:-1]:
            if type(row[field]) is not str or not row[field]:
                raise P2BDiagnosticError(
                    f"catalog_case_results[{index}].{field} must be a non-empty string"
                )
    return hashlib.sha256(_json_bytes(rows)).hexdigest()


def _ratio(
    numerator: int,
    denominator: int,
    *,
    undefined_reason: str | None = None,
) -> dict[str, Any]:
    if type(numerator) is not int or type(denominator) is not int:
        raise P2BDiagnosticError("ratio counts must be exact integers")
    if numerator < 0 or denominator < 0 or numerator > denominator:
        raise P2BDiagnosticError("ratio counts are outside their support")
    if denominator == 0:
        if not undefined_reason:
            raise P2BDiagnosticError("zero-support ratio requires an undefined reason")
        return {
            "numerator": numerator,
            "denominator": denominator,
            "fraction": None,
            "decimal": None,
            "undefined_reason": undefined_reason,
        }
    value = Fraction(numerator, denominator)
    decimal = format(numerator / denominator, ".12g")
    return {
        "numerator": numerator,
        "denominator": denominator,
        "fraction": f"{value.numerator}/{value.denominator}",
        "decimal": decimal,
        "undefined_reason": None,
    }


def _difference(first: dict[str, Any], second: dict[str, Any]) -> dict[str, Any]:
    if first["denominator"] == 0 or second["denominator"] == 0:
        return {
            "numerator": None,
            "denominator": None,
            "fraction": None,
            "decimal": None,
            "undefined_reason": "source_rate_undefined",
        }
    value = Fraction(first["numerator"], first["denominator"]) - Fraction(
        second["numerator"], second["denominator"]
    )
    return {
        "numerator": value.numerator,
        "denominator": value.denominator,
        "fraction": f"{value.numerator}/{value.denominator}",
        "decimal": format(float(value), ".12g"),
        "undefined_reason": None,
    }


def _exact_fields(value: Any, fields: tuple[str, ...], path: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise P2BDiagnosticError(f"{path}: expected object")
    if tuple(value) != fields:
        raise P2BDiagnosticError(f"{path}: missing, unknown, or reordered fields")
    return value


def _accepted_file_hash_snapshot() -> tuple[dict[str, str], dict[str, str]]:
    canonical_observed: dict[str, str] = {}
    working_tree_observed: dict[str, str] = {}
    for identity, (relative_path, expected) in _ACCEPTED_FILE_IDENTITIES.items():
        canonical, working_tree = _hash_identity_file(
            _repository_path(relative_path)
        )
        if canonical != expected:
            raise P2BDiagnosticError(f"accepted input drifted: {identity}")
        canonical_observed[identity] = canonical
        working_tree_observed[identity] = working_tree
    return canonical_observed, working_tree_observed


def _accepted_file_hashes() -> dict[str, str]:
    """Return portable accepted hashes after a fresh raw-byte snapshot."""

    return _accepted_file_hash_snapshot()[0]


def _validate_initial_common_stop(settings_payload: Mapping[str, Any]) -> bool:
    settings = P1BSettings(**settings_payload["settings"])
    state = p1b_policies._State(
        bug_presence=0.5,
        cause_posterior=uniform_distribution(P1B_CAUSE_CATEGORIES),
        location_posterior=uniform_distribution(LOCATION_CANDIDATES),
        fix_intent_posterior=uniform_distribution(P1B_FIX_INTENT_CATEGORIES),
        executed_actions=[],
        cumulative_cost=0,
        current_step=0,
        bug_detected=False,
        execution_context=None,
    )
    scores = p1b_policies.score_actions(state, settings.budget_limit)
    best = scores[0]["expected_utility_per_cost"] if scores else None
    return p1b_policies._check_stop(state, settings, best) is not None


def _load_validated_inputs() -> dict[str, Any]:
    """Freshly hash every accepted input, then reuse only hash-keyed parsed data."""

    accepted_hashes, working_tree_hashes = _accepted_file_hash_snapshot()
    parsed = deepcopy(
        _load_validated_input_content(
            tuple(accepted_hashes.items()),
            tuple(working_tree_hashes.items()),
        )
    )
    parsed["working_tree_hashes"] = working_tree_hashes
    return parsed


@lru_cache(maxsize=1)
def _load_validated_input_content(
    accepted_hash_items: tuple[tuple[str, str], ...],
    working_tree_hash_items: tuple[tuple[str, str], ...],
) -> dict[str, Any]:
    """Parse content cached by both canonical and exact working-tree hashes."""

    accepted_hashes = dict(accepted_hash_items)
    if tuple(dict(working_tree_hash_items)) != tuple(accepted_hashes):
        raise P2BDiagnosticError("working-tree identity support or order drifted")
    bundle = load_tracked_official_freeze_bundle()
    artifact = load_tracked_artifact_manifest()
    authoring = load_tracked_authoring_manifest()
    if bundle["official_freeze_digest"] != EXPECTED_OFFICIAL_FREEZE_DIGEST:
        raise P2BDiagnosticError("official freeze digest drifted")
    if (
        artifact["dataset_identity"]["candidate_manifest_digest"]
        != EXPECTED_CANDIDATE_MANIFEST_DIGEST
    ):
        raise P2BDiagnosticError("candidate manifest digest drifted")
    if (
        bundle["freeze_payload"]["artifact_manifest_identity"]["digest"]
        != EXPECTED_ARTIFACT_MANIFEST_DIGEST
    ):
        raise P2BDiagnosticError("artifact manifest digest drifted")
    if tuple(authoring["variant_ids"]) != tuple(
        candidate.variant_id for candidate in CANDIDATES
    ):
        raise P2BDiagnosticError("authoring manifest variant order drifted")

    json_path = _repository_path(P2A_JSON_RELATIVE_PATH)
    markdown_path = _repository_path(P2A_MARKDOWN_RELATIVE_PATH)
    p2a_summary = json.loads(json_path.read_text(encoding="utf-8"))
    validate_p2a_report_summary(p2a_summary)
    if p2a_canonical_digest(p2a_summary) != EXPECTED_P2A_SUMMARY_DIGEST:
        raise P2BDiagnosticError("accepted P2a summary digest drifted")
    if p2a_summary_from_markdown(markdown_path.read_text(encoding="utf-8")) != p2a_summary:
        raise P2BDiagnosticError("accepted P2a JSON/Markdown semantics drifted")
    _, expansion_outcomes = p2a_evaluation.saved_outcomes_from_report(p2a_summary)

    catalog = bundle["freeze_payload"]["outcome_free_contracts"]["catalog"][
        "payload"
    ]
    settings_payload = bundle["freeze_payload"]["outcome_free_contracts"][
        "settings"
    ]["payload"]
    policy_payload = bundle["freeze_payload"]["outcome_free_contracts"]["policy"][
        "payload"
    ]
    if len(catalog["cases"]) != 24:
        raise P2BDiagnosticError("frozen catalog must contain exactly 24 cases")
    if tuple(policy_payload["formal_policy_ids"]) != FORMAL_POLICY_IDS:
        raise P2BDiagnosticError("formal policy order drifted")
    if tuple(policy_payload["excluded_policy_ids"]) != EXCLUDED_POLICY_IDS:
        raise P2BDiagnosticError("excluded policy order drifted")
    if tuple(item["action_id"] for item in catalog["approved_action_specs"]) != ACTION_IDS:
        raise P2BDiagnosticError("action order drifted")
    for frozen, (action_id, spec) in zip(
        catalog["approved_action_specs"], P1B_ACTION_SPECS.items(), strict=True
    ):
        if frozen != {
            "action_id": action_id,
            "cost": spec.cost,
            "observation_type": spec.observation_type,
            "strong_causes": list(spec.strong_causes),
            "discovery_power": spec.discovery_power,
            "location_power": spec.location_power,
        }:
            raise P2BDiagnosticError("frozen action specification drifted")

    expected_pairs = [
        (variant_id, policy_id)
        for variant_id in BUGGY_VARIANT_IDS
        for policy_id in FORMAL_POLICY_IDS
    ]
    buggy_saved = [row for row in expansion_outcomes if row["is_buggy"]]
    if len(buggy_saved) != 60:
        raise P2BDiagnosticError("saved expansion buggy support is not 60")
    if [
        (row["variant_id"], row["policy_id"]) for row in buggy_saved
    ] != expected_pairs:
        raise P2BDiagnosticError("saved expansion buggy pair order drifted")

    candidate_by_id = {item["variant_id"]: item for item in artifact["candidates"]}
    if tuple(candidate_by_id)[: len(BUGGY_VARIANT_IDS)] != BUGGY_VARIANT_IDS:
        raise P2BDiagnosticError("artifact buggy candidate order drifted")
    bucket_by_variant = {
        variant_id: candidate_by_id[variant_id]["primary_taxonomy_id"]
        for variant_id in BUGGY_VARIANT_IDS
    }
    if tuple(dict.fromkeys(bucket_by_variant.values())) != BUCKET_IDS:
        raise P2BDiagnosticError("buggy bucket order drifted")
    if any(
        sum(bucket == target for bucket in bucket_by_variant.values()) != 2
        for target in BUCKET_IDS
    ):
        raise P2BDiagnosticError("buggy bucket support drifted")

    initial_common_stop = _validate_initial_common_stop(settings_payload)
    if initial_common_stop:
        raise P2BDiagnosticError("accepted initial common stop unexpectedly fires")
    return {
        "bundle": bundle,
        "artifact": artifact,
        "authoring": authoring,
        "catalog": catalog,
        "settings": settings_payload,
        "p2a_summary": p2a_summary,
        "buggy_saved_outcomes": buggy_saved,
        "bucket_by_variant": bucket_by_variant,
        "accepted_hashes": accepted_hashes,
        "initial_common_stop": initial_common_stop,
    }


def _input_identity(inputs: Mapping[str, Any]) -> dict[str, Any]:
    compatibility = inputs["bundle"]["freeze_payload"]["accepted_input_identities"][
        "legacy_compatibility"
    ]
    return {
        "merged_base_commit": MERGE_COMMIT,
        "accepted_p2a_head": ACCEPTED_P2A_HEAD,
        "dataset_schema_version": "p2a_same_domain_dataset.v1",
        "benchmark_id": "p2a_checkout_pricing_same_domain_expansion_v1",
        "candidate_manifest_digest": EXPECTED_CANDIDATE_MANIFEST_DIGEST,
        "artifact_manifest_digest": EXPECTED_ARTIFACT_MANIFEST_DIGEST,
        "official_freeze_digest": EXPECTED_OFFICIAL_FREEZE_DIGEST,
        "saved_outcome_snapshot_digest": EXPECTED_SAVED_OUTCOME_DIGEST,
        "accepted_p2a_summary_digest": EXPECTED_P2A_SUMMARY_DIGEST,
        "accepted_p2a_json_sha256": EXPECTED_P2A_JSON_SHA256,
        "accepted_p2a_markdown_sha256": EXPECTED_P2A_MARKDOWN_SHA256,
        "dataset_counts": {"total": 15, "buggy": 10, "clean": 5},
        "catalog_case_count": 24,
        "legacy_compatibility": deepcopy(compatibility),
        "accepted_file_hash_mode": "sha256_after_crlf_to_lf_normalization",
        "accepted_file_sha256": deepcopy(inputs["accepted_hashes"]),
    }


@contextmanager
def _modules_for_action(candidate: CandidateDefinition) -> Iterator[Mapping[str, Any]]:
    """Create a fresh patched module tree for one first-action counterfactual."""

    with _candidate_modules(candidate) as modules:
        yield modules


def _execute_catalog_for_variant(
    candidate: CandidateDefinition,
    catalog: Mapping[str, Any],
) -> list[dict[str, Any]]:
    rows_by_case: dict[str, dict[str, Any]] = {}
    cases = catalog["cases"]
    for action_id in ACTION_IDS:
        action_cases = [case for case in cases if case["action_id"] == action_id]
        if not action_cases:
            continue
        with _modules_for_action(candidate) as modules:
            for case in action_cases:
                result = run_oracle_record(case["oracle_definition"], modules)
                case_id = f"{case['candidate_id']}::{case['oracle_id']}"
                if case_id in rows_by_case:
                    raise P2BDiagnosticError("duplicate frozen catalog case ID")
                rows_by_case[case_id] = {
                    "case_id": case_id,
                    "candidate_id": case["candidate_id"],
                    "action_id": case["action_id"],
                    "passed": result.passed,
                }
    ordered_ids = [f"{case['candidate_id']}::{case['oracle_id']}" for case in cases]
    if set(rows_by_case) != set(ordered_ids) or len(rows_by_case) != 24:
        raise P2BDiagnosticError("catalog execution did not produce exact 24-case support")
    return [rows_by_case[case_id] for case_id in ordered_ids]


def _classify(
    *,
    catalog_reachable: bool,
    budget_feasible: bool,
    policy_discovered: bool,
) -> str:
    if policy_discovered and not budget_feasible:
        raise P2BDiagnosticError(
            "saved policy discovery contradicts one-step budget feasibility"
        )
    if not catalog_reachable:
        return "catalog_unreachable"
    if not budget_feasible:
        return "catalog_reachable_not_budget_feasible"
    if policy_discovered:
        return "catalog_reachable_policy_discovered"
    return "catalog_reachable_policy_missed"


def _derive_detection_contract(
    *,
    case_rows: list[dict[str, Any]],
    action_specs: list[dict[str, Any]],
    budget_limit: int,
    max_steps: int,
    initial_common_stop: bool,
) -> dict[str, Any]:
    """Derive reachability and one-step feasibility from audited case rows."""

    if type(budget_limit) is not int or type(max_steps) is not int:
        raise P2BDiagnosticError("budget and max steps must be exact integers")
    action_ids = [item.get("action_id") for item in action_specs]
    if tuple(action_ids) != ACTION_IDS or len(set(action_ids)) != len(ACTION_IDS):
        raise P2BDiagnosticError("action specification support or order drifted")
    action_costs: dict[str, int] = {}
    for item in action_specs:
        if type(item.get("cost")) is not int or item["cost"] < 0:
            raise P2BDiagnosticError("action cost must be a non-negative exact integer")
        action_costs[item["action_id"]] = item["cost"]
    detecting_by_action = {
        action_id: [
            row["case_id"]
            for row in case_rows
            if row["action_id"] == action_id and not row["passed"]
        ]
        for action_id in ACTION_IDS
    }
    detecting_actions = [
        action_id for action_id in ACTION_IDS if detecting_by_action[action_id]
    ]
    minimum_cost = (
        min(action_costs[action_id] for action_id in detecting_actions)
        if detecting_actions
        else None
    )
    minimum_actions = (
        [
            action_id
            for action_id in detecting_actions
            if action_costs[action_id] == minimum_cost
        ]
        if minimum_cost is not None
        else []
    )
    catalog_reachable = bool(detecting_actions)
    return {
        "detecting_cases_by_action": detecting_by_action,
        "detecting_action_ids": detecting_actions,
        "catalog_reachable": catalog_reachable,
        "minimum_detecting_cost": minimum_cost,
        "minimum_cost_action_ids": minimum_actions,
        "budget_feasible": bool(
            catalog_reachable
            and minimum_cost is not None
            and minimum_cost <= budget_limit
            and max_steps >= 1
            and not initial_common_stop
        ),
    }


def _variant_diagnostic(
    *,
    candidate: CandidateDefinition,
    bucket_id: str,
    case_rows: list[dict[str, Any]],
    catalog: Mapping[str, Any],
    settings: Mapping[str, Any],
    initial_common_stop: bool,
    saved_outcomes: Mapping[str, bool],
) -> dict[str, Any]:
    if len(case_rows) != 24 or len(catalog["cases"]) != 24:
        raise P2BDiagnosticError("variant case support is not exactly 24")
    expected_case_rows = [
        {
            "case_id": f"{case['candidate_id']}::{case['oracle_id']}",
            "candidate_id": case["candidate_id"],
            "action_id": case["action_id"],
        }
        for case in catalog["cases"]
    ]
    seen: set[str] = set()
    for index, (row, expected) in enumerate(
        zip(case_rows, expected_case_rows, strict=True)
    ):
        _exact_fields(row, _CASE_RESULT_FIELDS, f"catalog_case_results[{index}]")
        if {field: row[field] for field in expected} != expected:
            raise P2BDiagnosticError("catalog case identity or order drifted")
        if type(row["passed"]) is not bool:
            raise P2BDiagnosticError("catalog case passed must be exact bool")
        if row["case_id"] in seen:
            raise P2BDiagnosticError("duplicate catalog case result")
        seen.add(row["case_id"])

    detection = _derive_detection_contract(
        case_rows=case_rows,
        action_specs=list(catalog["approved_action_specs"]),
        budget_limit=settings["budget_limit"],
        max_steps=settings["max_steps"],
        initial_common_stop=initial_common_stop,
    )
    owned_case_ids = [
        row["case_id"] for row in case_rows if row["candidate_id"] == candidate.variant_id
    ]
    owned_reachable = any(
        row["candidate_id"] == candidate.variant_id and not row["passed"]
        for row in case_rows
    )
    if not owned_reachable:
        raise P2BDiagnosticError("accepted buggy owned oracle did not fail")
    classifications = {
        policy_id: _classify(
            catalog_reachable=detection["catalog_reachable"],
            budget_feasible=detection["budget_feasible"],
            policy_discovered=saved_outcomes[policy_id],
        )
        for policy_id in FORMAL_POLICY_IDS
    }
    return dict(
        zip(
            _VARIANT_FIELDS,
            (
                candidate.variant_id,
                bucket_id,
                len(case_rows),
                deepcopy(case_rows),
                canonical_rows_digest(case_rows),
                owned_case_ids,
                owned_reachable,
                detection["detecting_action_ids"],
                detection["detecting_cases_by_action"],
                detection["minimum_detecting_cost"],
                detection["minimum_cost_action_ids"],
                detection["minimum_cost_action_ids"][0]
                if detection["budget_feasible"]
                else None,
                initial_common_stop,
                detection["budget_feasible"],
                detection["budget_feasible"],
                dict(saved_outcomes),
                classifications,
            ),
            strict=True,
        )
    )


def _scope_diagnostic(
    variant_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    support = len(variant_rows)
    reachable = [row["variant_id"] for row in variant_rows if row["detecting_action_ids"]]
    feasible = [row["variant_id"] for row in variant_rows if row["budget_feasible"]]
    return {
        "support_variant_ids": [row["variant_id"] for row in variant_rows],
        "catalog_reachable_variant_ids": reachable,
        "catalog_unreachable_variant_ids": [
            row["variant_id"] for row in variant_rows if not row["detecting_action_ids"]
        ],
        "budget_feasible_variant_ids": feasible,
        "catalog_reachable_not_budget_feasible_variant_ids": [
            row["variant_id"]
            for row in variant_rows
            if row["detecting_action_ids"] and not row["budget_feasible"]
        ],
        "catalog_reachability_rate": _ratio(len(reachable), support),
        "ceiling_discovery_rate": _ratio(len(feasible), support),
        "ceiling_discovery_loss": _ratio(support - len(feasible), support),
        "minimum_detecting_cost_by_variant": {
            row["variant_id"]: row["minimum_detecting_cost"] for row in variant_rows
        },
    }


def _policy_scope_comparison(
    policy_id: str,
    variant_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    support = len(variant_rows)
    discovered = [
        row["variant_id"]
        for row in variant_rows
        if row["saved_policy_outcomes"][policy_id]
    ]
    feasible = [row for row in variant_rows if row["budget_feasible"]]
    missed_feasible = [
        row["variant_id"]
        for row in feasible
        if not row["saved_policy_outcomes"][policy_id]
    ]
    ceiling_rate = _ratio(len(feasible), support)
    policy_rate = _ratio(len(discovered), support)
    classifications = {
        classification: [
            row["variant_id"]
            for row in variant_rows
            if row["policy_classifications"][policy_id] == classification
        ]
        for classification in (
            "catalog_unreachable",
            "catalog_reachable_not_budget_feasible",
            "catalog_reachable_policy_discovered",
            "catalog_reachable_policy_missed",
        )
    }
    return {
        "support_variant_ids": [row["variant_id"] for row in variant_rows],
        "saved_discovered_variant_ids": discovered,
        "saved_missed_variant_ids": [
            row["variant_id"]
            for row in variant_rows
            if not row["saved_policy_outcomes"][policy_id]
        ],
        "classification_variant_ids": classifications,
        "saved_policy_discovery_rate": policy_rate,
        "ceiling_discovery_rate": ceiling_rate,
        "ceiling_gap": _difference(ceiling_rate, policy_rate),
        "budget_feasible_policy_miss_rate": _ratio(
            len(missed_feasible),
            len(feasible),
            undefined_reason="no_budget_feasible_support",
        ),
    }


def _build_valid_summary(
    inputs: Mapping[str, Any],
    rows_by_variant: Mapping[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    saved_by_pair = {
        (row["variant_id"], row["policy_id"]): row["discovered_within_budget"]
        for row in inputs["buggy_saved_outcomes"]
    }
    variants: list[dict[str, Any]] = []
    for candidate in BUGGY_CANDIDATES:
        case_rows = rows_by_variant.get(candidate.variant_id)
        if case_rows is None:
            raise P2BDiagnosticError("missing variant catalog results")
        variants.append(
            _variant_diagnostic(
                candidate=candidate,
                bucket_id=inputs["bucket_by_variant"][candidate.variant_id],
                case_rows=case_rows,
                catalog=inputs["catalog"],
                settings=inputs["settings"]["settings"],
                initial_common_stop=inputs["initial_common_stop"],
                saved_outcomes={
                    policy_id: saved_by_pair[(candidate.variant_id, policy_id)]
                    for policy_id in FORMAL_POLICY_IDS
                },
            )
        )
    if tuple(rows_by_variant) != BUGGY_VARIANT_IDS:
        raise P2BDiagnosticError("variant catalog result order or support drifted")

    by_bucket = {
        bucket_id: [row for row in variants if row["bucket_id"] == bucket_id]
        for bucket_id in BUCKET_IDS
    }
    bucket_diagnostics = {
        bucket_id: _scope_diagnostic(by_bucket[bucket_id]) for bucket_id in BUCKET_IDS
    }
    policy_comparison = {
        policy_id: {
            "overall": _policy_scope_comparison(policy_id, variants),
            "by_bucket": {
                bucket_id: _policy_scope_comparison(policy_id, by_bucket[bucket_id])
                for bucket_id in BUCKET_IDS
            },
        }
        for policy_id in FORMAL_POLICY_IDS
    }
    bucket_losses = [
        Fraction(
            bucket_diagnostics[bucket_id]["ceiling_discovery_loss"]["numerator"],
            bucket_diagnostics[bucket_id]["ceiling_discovery_loss"]["denominator"],
        )
        for bucket_id in BUCKET_IDS
    ]
    uniform_bucket_loss = sum(bucket_losses, Fraction(0, 1)) / len(BUCKET_IDS)
    overall = _scope_diagnostic(variants)
    overall["uniform_over_buckets_ceiling_loss"] = {
        "numerator": uniform_bucket_loss.numerator,
        "denominator": uniform_bucket_loss.denominator,
        "fraction": f"{uniform_bucket_loss.numerator}/{uniform_bucket_loss.denominator}",
        "decimal": format(float(uniform_bucket_loss), ".12g"),
        "undefined_reason": None,
    }
    summary = dict(
        zip(
            _TOP_LEVEL_FIELDS,
            (
                SCHEMA_VERSION,
                ANALYSIS_PHASE,
                REPORT_ROLE,
                {"status": VALID_STATUS, "reason_codes": []},
                _input_identity(inputs),
                {
                    "pre_diagnostic_gate_passed": True,
                    "catalog_case_evaluation_count": 240,
                    "expected_catalog_case_evaluation_count": 240,
                    "policy_outcome_runner_executed": False,
                    "compatibility_runner_executed": False,
                    "p2a_evaluation_runner_executed": False,
                    "working_tree_raw_pre_post_match": True,
                    "first_execution": "P2A-BUG-001::P2A-BUG-001::boundary.quantity_zero_rejected",
                    "summary_observed_event_ids": [
                        "p2b_pre_diagnostic_gate_passed",
                        "p2b_catalog_case_execution_started",
                        "p2b_catalog_case_execution_completed",
                    ],
                    "required_post_summary_event_ids": [
                        "p2b_summary_validated",
                        "p2b_artifacts_serialized",
                    ],
                },
                {
                    "accepted_total_count": 15,
                    "buggy_support_count": 10,
                    "clean_identity_only_count": 5,
                    "catalog_case_count": 24,
                    "saved_policy_outcome_count": 60,
                },
                list(FORMAL_POLICY_IDS),
                list(EXCLUDED_POLICY_IDS),
                list(BUCKET_IDS),
                deepcopy(inputs["catalog"]["approved_action_specs"]),
                {
                    "catalog_reachability": "at least one failed frozen catalog case mapped to an action",
                    "budget_feasible_ceiling": "ground-truth-informed minimum-cost direct detecting action chosen at step one within budget",
                    "policy_comparison": "saved accepted expansion-only outcome compared without policy rerun",
                    "classification_boundary": "reachable policy miss means selection/order/stop trajectory limitation under the fixed contract",
                },
                variants,
                bucket_diagnostics,
                policy_comparison,
                overall,
                {
                    "accepted": False,
                    "status": "pending_independent_implementation_review",
                },
                {
                    "accepted": False,
                    "status": "pending_separate_policy_management_decision",
                },
                {"accepted": False, "status": "not_included"},
                [
                    "The cohort is hand-authored, stratified, same-domain, and non-iid.",
                    "The one-step ceiling ignores multi-step context-dependent evidence.",
                    "The selector uses variant ground truth unavailable to deployable policies.",
                    "Saved P2a policy outcomes are reused without rerunning policies.",
                    "Clean safety behavior is outside the P2b primary diagnostic.",
                ],
                [
                    "This diagnostic is not a seventh formal policy or deployable strategy.",
                    "This diagnostic is not a general upper bound or policy-superiority result.",
                    "This diagnostic does not establish generalization, significance, causality, minimax, Nash, or regret claims.",
                    "Catalog-unreachable variants are retained in the accepted support.",
                    "Accepted P2a software, dataset, result, and documentation decisions are unchanged.",
                ],
                [
                    "P2b is an analysis-only, ground-truth-informed, non-deployable fixed-catalog diagnostic.",
                    "All rates are descriptive exact counts over the accepted fixed support.",
                ],
            ),
            strict=True,
        )
    )
    validate_portable_value(summary)
    return summary


def invalid_diagnostic_summary(
    *reason_codes: str,
    input_identity: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if not reason_codes or any(type(reason) is not str or not reason for reason in reason_codes):
        raise P2BDiagnosticError("invalid summary requires non-empty reason codes")
    summary = dict(
        zip(
            _INVALID_FIELDS,
            (
                SCHEMA_VERSION,
                ANALYSIS_PHASE,
                REPORT_ROLE,
                {"status": INVALID_STATUS},
                list(reason_codes),
                deepcopy(dict(input_identity or {})),
                {"accepted": False, "status": "invalid_inconclusive"},
                {"accepted": False, "status": "invalid_inconclusive"},
                {"accepted": False, "status": "not_included"},
                [
                    "No partial reachability, ceiling, policy comparison, or performance claim is valid."
                ],
            ),
            strict=True,
        )
    )
    validate_portable_value(summary)
    return summary


def validate_diagnostic_summary(summary: Any) -> dict[str, Any]:
    if type(summary) is not dict:
        raise P2BDiagnosticError("summary must be an object")
    validate_portable_value(summary)
    status = summary.get("validation_status", {}).get("status")
    if status == INVALID_STATUS:
        _exact_fields(summary, _INVALID_FIELDS, "summary")
        if summary["validation_status"] != {"status": INVALID_STATUS}:
            raise P2BDiagnosticError("invalid validation status schema drifted")
        if (
            type(summary["reason_codes"]) is not list
            or not summary["reason_codes"]
            or any(type(reason) is not str or not reason for reason in summary["reason_codes"])
        ):
            raise P2BDiagnosticError("invalid summary requires reason codes")
        expected_acceptance = {"accepted": False, "status": "invalid_inconclusive"}
        for acceptance in ("software_acceptance", "result_acceptance"):
            if summary[acceptance] != expected_acceptance:
                raise P2BDiagnosticError("invalid summary cannot self-accept")
        if summary["documentation_acceptance"] != {
            "accepted": False,
            "status": "not_included",
        }:
            raise P2BDiagnosticError("invalid documentation acceptance drifted")
        if summary["non_claims"] != [
            "No partial reachability, ceiling, policy comparison, or performance claim is valid."
        ]:
            raise P2BDiagnosticError("invalid summary non-claim drifted")
        return summary
    if status != VALID_STATUS:
        raise P2BDiagnosticError("summary status is neither valid nor invalid_inconclusive")
    _exact_fields(summary, _TOP_LEVEL_FIELDS, "summary")
    inputs = _load_validated_inputs()
    if summary["input_identity"] != _input_identity(inputs):
        raise P2BDiagnosticError("summary input identity drifted")
    variants = summary["variant_diagnostics"]
    if type(variants) is not list or len(variants) != 10:
        raise P2BDiagnosticError("variant diagnostics support drifted")
    rows_by_variant: dict[str, list[dict[str, Any]]] = {}
    for index, row in enumerate(variants):
        _exact_fields(row, _VARIANT_FIELDS, f"variant_diagnostics[{index}]")
        if row["variant_id"] in rows_by_variant:
            raise P2BDiagnosticError("duplicate variant diagnostic")
        if canonical_rows_digest(row["catalog_case_results"]) != row["case_results_digest"]:
            raise P2BDiagnosticError("case result digest mismatch")
        rows_by_variant[row["variant_id"]] = deepcopy(row["catalog_case_results"])
    expected = _build_valid_summary(inputs, rows_by_variant)
    if summary != expected:
        raise P2BDiagnosticError("summary differs from independent derived recomputation")
    return summary


def run_fixed_catalog_diagnostic(
    *, event_log: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    """Execute only the accepted fixed catalog and return a validated summary."""

    events = event_log if event_log is not None else []
    try:
        inputs = _load_validated_inputs()
    except Exception as exc:  # noqa: BLE001 - fail-closed public diagnostic boundary
        return invalid_diagnostic_summary(type(exc).__name__)
    events.append({"event": "p2b_pre_diagnostic_gate_passed"})
    events.append(
        {
            "event": "p2b_catalog_case_execution_started",
            "variant_id": BUGGY_VARIANT_IDS[0],
            "case_id": "P2A-BUG-001::boundary.quantity_zero_rejected",
        }
    )
    try:
        rows_by_variant = {
            candidate.variant_id: _execute_catalog_for_variant(candidate, inputs["catalog"])
            for candidate in BUGGY_CANDIDATES
        }
        events.append(
            {
                "event": "p2b_catalog_case_execution_completed",
                "variant_count": 10,
                "case_count_per_variant": 24,
                "case_evaluation_count": 240,
            }
        )
        post_inputs = _load_validated_inputs()
        if (
            _input_identity(post_inputs) != _input_identity(inputs)
            or post_inputs["working_tree_hashes"]
            != inputs["working_tree_hashes"]
        ):
            raise P2BDiagnosticError("accepted input identity changed during execution")
        summary = _build_valid_summary(post_inputs, rows_by_variant)
        validate_diagnostic_summary(summary)
    except Exception as exc:  # noqa: BLE001 - no partial claims after execution
        return invalid_diagnostic_summary(
            type(exc).__name__, input_identity=_input_identity(inputs)
        )
    events.append({"event": "p2b_summary_validated"})
    return summary


def record_artifacts_serialized(event_log: list[dict[str, Any]]) -> None:
    """Record the final in-memory event after both artifacts are serialized."""

    event_log.append({"event": "p2b_artifacts_serialized"})


def assert_finite_summary(summary: Mapping[str, Any]) -> None:
    """Defensive finite-value check used by artifact generation tests."""

    def walk(value: Any) -> Iterator[Any]:
        if type(value) is dict:
            for nested in value.values():
                yield from walk(nested)
        elif type(value) is list:
            for nested in value:
                yield from walk(nested)
        else:
            yield value

    for value in walk(summary):
        if type(value) is float and not math.isfinite(value):
            raise P2BDiagnosticError("summary contains a non-finite value")
