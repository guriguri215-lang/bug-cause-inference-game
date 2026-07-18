from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from types import SimpleNamespace

import pytest

from bug_cause_inference.p2a import compatibility as p2a_compatibility
from bug_cause_inference.p2a import evaluation as p2a_evaluation
from bug_cause_inference.p2b import solvability_ceiling as ceiling


@pytest.fixture(scope="module")
def diagnostic():
    event_log: list[dict[str, object]] = []
    summary = ceiling.run_fixed_catalog_diagnostic(event_log=event_log)
    assert summary["validation_status"] == {"status": "valid", "reason_codes": []}
    return summary, event_log


def test_pre_diagnostic_gate_fixes_all_accepted_identities() -> None:
    inputs = ceiling._load_validated_inputs()
    identity = ceiling._input_identity(inputs)
    assert identity["merged_base_commit"] == ceiling.MERGE_COMMIT
    assert identity["accepted_p2a_head"] == ceiling.ACCEPTED_P2A_HEAD
    assert identity["dataset_counts"] == {"total": 15, "buggy": 10, "clean": 5}
    assert identity["catalog_case_count"] == 24
    assert identity["candidate_manifest_digest"] == ceiling.EXPECTED_CANDIDATE_MANIFEST_DIGEST
    assert identity["artifact_manifest_digest"] == ceiling.EXPECTED_ARTIFACT_MANIFEST_DIGEST
    assert identity["official_freeze_digest"] == ceiling.EXPECTED_OFFICIAL_FREEZE_DIGEST
    assert identity["saved_outcome_snapshot_digest"] == ceiling.EXPECTED_SAVED_OUTCOME_DIGEST
    assert identity["accepted_p2a_summary_digest"] == ceiling.EXPECTED_P2A_SUMMARY_DIGEST
    assert identity["accepted_file_hash_mode"] == (
        "sha256_after_crlf_to_lf_normalization"
    )
    assert identity["legacy_compatibility"]["matched_pair_count"] == 150
    assert identity["legacy_compatibility"]["mismatch_count"] == 0
    assert tuple(inputs["bucket_by_variant"].values()) == (
        "boundary_precision",
        "boundary_precision",
        "missing_optional_input",
        "missing_optional_input",
        "config_normalization",
        "config_normalization",
        "state_sequence",
        "state_sequence",
        "spec_semantics",
        "spec_semantics",
    )


def test_diagnostic_runs_exact_catalog_only_and_records_boundary(diagnostic) -> None:
    summary, events = diagnostic
    assert [item["event"] for item in events] == [
        "p2b_pre_diagnostic_gate_passed",
        "p2b_catalog_case_execution_started",
        "p2b_catalog_case_execution_completed",
        "p2b_summary_validated",
    ]
    assert events[1] == {
        "event": "p2b_catalog_case_execution_started",
        "variant_id": "P2A-BUG-001",
        "case_id": "P2A-BUG-001::boundary.quantity_zero_rejected",
    }
    assert events[2]["case_evaluation_count"] == 240
    boundary = summary["execution_boundary"]
    assert boundary["catalog_case_evaluation_count"] == 240
    assert boundary["policy_outcome_runner_executed"] is False
    assert boundary["compatibility_runner_executed"] is False
    assert boundary["p2a_evaluation_runner_executed"] is False
    assert boundary["working_tree_raw_pre_post_match"] is True
    assert boundary["summary_observed_event_ids"] == [
        item["event"] for item in events[:3]
    ]
    assert boundary["required_post_summary_event_ids"] == [
        "p2b_summary_validated",
        "p2b_artifacts_serialized",
    ]


def test_every_variant_has_exact_ordered_24_case_audit_and_digest(diagnostic) -> None:
    summary, _ = diagnostic
    expected_ids = [
        f"{case['candidate_id']}::{case['oracle_id']}"
        for case in ceiling._load_validated_inputs()["catalog"]["cases"]
    ]
    for variant in summary["variant_diagnostics"]:
        rows = variant["catalog_case_results"]
        assert len(rows) == variant["catalog_case_support_count"] == 24
        assert [row["case_id"] for row in rows] == expected_ids
        assert all(tuple(row) == ceiling._CASE_RESULT_FIELDS for row in rows)
        assert all(type(row["passed"]) is bool for row in rows)
        assert ceiling.canonical_rows_digest(rows) == variant["case_results_digest"]
        expected_detecting = {
            action_id: [
                row["case_id"]
                for row in rows
                if row["action_id"] == action_id and not row["passed"]
            ]
            for action_id in ceiling.ACTION_IDS
        }
        assert variant["detecting_cases_by_action"] == expected_detecting
        assert variant["detecting_action_ids"] == [
            action_id for action_id in ceiling.ACTION_IDS if expected_detecting[action_id]
        ]


def test_exact_reachability_and_minimum_cost_result(diagnostic) -> None:
    summary, _ = diagnostic
    assert summary["overall_diagnostic"]["catalog_unreachable_variant_ids"] == []
    assert summary["overall_diagnostic"][
        "catalog_reachable_not_budget_feasible_variant_ids"
    ] == []
    assert summary["overall_diagnostic"]["catalog_reachable_variant_ids"] == list(
        ceiling.BUGGY_VARIANT_IDS
    )
    assert summary["overall_diagnostic"]["budget_feasible_variant_ids"] == list(
        ceiling.BUGGY_VARIANT_IDS
    )
    assert summary["overall_diagnostic"]["catalog_reachability_rate"]["fraction"] == "1/1"
    assert summary["overall_diagnostic"]["ceiling_discovery_rate"]["fraction"] == "1/1"
    assert summary["overall_diagnostic"]["ceiling_discovery_loss"]["fraction"] == "0/1"
    assert {
        row["variant_id"]: row["minimum_detecting_cost"]
        for row in summary["variant_diagnostics"]
    } == {
        "P2A-BUG-001": 2,
        "P2A-BUG-002": 2,
        "P2A-BUG-003": 2,
        "P2A-BUG-004": 2,
        "P2A-BUG-005": 3,
        "P2A-BUG-006": 3,
        "P2A-BUG-007": 4,
        "P2A-BUG-008": 4,
        "P2A-BUG-009": 2,
        "P2A-BUG-010": 2,
    }
    fourth = summary["variant_diagnostics"][3]
    assert fourth["detecting_action_ids"] == [
        "run_null_missing_tests",
        "run_config_matrix_tests",
    ]
    assert fourth["ceiling_witness_action_id"] == "run_null_missing_tests"


def test_saved_policy_comparison_is_exact_and_ceiling_is_not_a_policy(diagnostic) -> None:
    summary, _ = diagnostic
    assert tuple(summary["formal_policy_ids"]) == ceiling.FORMAL_POLICY_IDS
    assert "ceiling" not in " ".join(summary["formal_policy_ids"])
    assert "restricted_pure_result" not in summary
    for policy_id in ceiling.FORMAL_POLICY_IDS[:4]:
        row = summary["policy_comparison"][policy_id]["overall"]
        assert len(row["saved_discovered_variant_ids"]) == 2
        assert row["saved_policy_discovery_rate"]["fraction"] == "1/5"
        assert row["ceiling_gap"]["fraction"] == "4/5"
        assert len(
            row["classification_variant_ids"]["catalog_reachable_policy_missed"]
        ) == 8
    for policy_id in ceiling.FORMAL_POLICY_IDS[4:]:
        row = summary["policy_comparison"][policy_id]["overall"]
        assert row["saved_discovered_variant_ids"] == []
        assert row["saved_policy_discovery_rate"]["fraction"] == "0/1"
        assert row["ceiling_gap"]["fraction"] == "1/1"
        assert len(
            row["classification_variant_ids"]["catalog_reachable_policy_missed"]
        ) == 10


def test_budget_classification_and_zero_support_are_fail_closed() -> None:
    assert (
        ceiling._classify(
            catalog_reachable=True,
            budget_feasible=False,
            policy_discovered=False,
        )
        == "catalog_reachable_not_budget_feasible"
    )
    assert (
        ceiling._classify(
            catalog_reachable=False,
            budget_feasible=False,
            policy_discovered=False,
        )
        == "catalog_unreachable"
    )
    with pytest.raises(ceiling.P2BDiagnosticError, match="contradicts"):
        ceiling._classify(
            catalog_reachable=True,
            budget_feasible=False,
            policy_discovered=True,
        )
    undefined = ceiling._ratio(
        0, 0, undefined_reason="no_budget_feasible_support"
    )
    assert undefined["decimal"] is None
    assert undefined["undefined_reason"] == "no_budget_feasible_support"


def test_synthetic_reachability_tie_and_budget_edges(diagnostic) -> None:
    summary, _ = diagnostic
    inputs = ceiling._load_validated_inputs()
    rows = deepcopy(summary["variant_diagnostics"][0]["catalog_case_results"])
    action_specs = deepcopy(inputs["catalog"]["approved_action_specs"])
    for row in rows:
        row["passed"] = True

    unreachable = ceiling._derive_detection_contract(
        case_rows=rows,
        action_specs=action_specs,
        budget_limit=5,
        max_steps=1,
        initial_common_stop=False,
    )
    assert unreachable["catalog_reachable"] is False
    assert unreachable["minimum_detecting_cost"] is None
    assert unreachable["budget_feasible"] is False

    distinct_actions = list(dict.fromkeys(row["action_id"] for row in rows))[:2]
    for action_id in distinct_actions:
        next(row for row in rows if row["action_id"] == action_id)["passed"] = False
        next(item for item in action_specs if item["action_id"] == action_id)["cost"] = 5
    tied = ceiling._derive_detection_contract(
        case_rows=rows,
        action_specs=action_specs,
        budget_limit=5,
        max_steps=1,
        initial_common_stop=False,
    )
    assert tied["catalog_reachable"] is True
    assert tied["minimum_detecting_cost"] == 5
    assert tied["minimum_cost_action_ids"] == distinct_actions
    assert tied["budget_feasible"] is True
    above_budget = ceiling._derive_detection_contract(
        case_rows=rows,
        action_specs=action_specs,
        budget_limit=4,
        max_steps=1,
        initial_common_stop=False,
    )
    assert above_budget["budget_feasible"] is False


def test_action_support_missing_duplicate_extra_and_reorder_are_rejected(
    diagnostic,
) -> None:
    summary, _ = diagnostic
    inputs = ceiling._load_validated_inputs()
    rows = deepcopy(summary["variant_diagnostics"][0]["catalog_case_results"])
    specs = deepcopy(inputs["catalog"]["approved_action_specs"])
    mutations = [
        specs[:-1],
        specs + [deepcopy(specs[-1])],
        specs[:-1] + [deepcopy(specs[0])],
        [specs[1], specs[0], *specs[2:]],
    ]
    for mutation in mutations:
        with pytest.raises(ceiling.P2BDiagnosticError, match="action specification"):
            ceiling._derive_detection_contract(
                case_rows=rows,
                action_specs=mutation,
                budget_limit=12,
                max_steps=8,
                initial_common_stop=False,
            )


def test_variant_policy_and_bucket_reordering_is_rejected(diagnostic) -> None:
    summary, _ = diagnostic
    for collection in ("variant_diagnostics", "formal_policy_ids", "bucket_ids"):
        changed = deepcopy(summary)
        values = changed[collection]
        values[0], values[1] = values[1], values[0]
        with pytest.raises(ceiling.P2BDiagnosticError):
            ceiling.validate_diagnostic_summary(changed)


def test_owned_oracle_mismatch_is_rejected(diagnostic) -> None:
    summary, _ = diagnostic
    inputs = ceiling._load_validated_inputs()
    rows = deepcopy(summary["variant_diagnostics"][0]["catalog_case_results"])
    for row in rows:
        row["passed"] = True
    with pytest.raises(ceiling.P2BDiagnosticError, match="owned oracle"):
        ceiling._variant_diagnostic(
            candidate=ceiling.BUGGY_CANDIDATES[0],
            bucket_id=inputs["bucket_by_variant"][ceiling.BUGGY_VARIANT_IDS[0]],
            case_rows=rows,
            catalog=inputs["catalog"],
            settings=inputs["settings"]["settings"],
            initial_common_stop=False,
            saved_outcomes={policy_id: False for policy_id in ceiling.FORMAL_POLICY_IDS},
        )


def test_each_action_uses_a_fresh_candidate_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs = ceiling._load_validated_inputs()
    opened: list[str] = []

    @contextmanager
    def fake_modules(candidate):
        opened.append(candidate.variant_id)
        yield {}

    monkeypatch.setattr(ceiling, "_modules_for_action", fake_modules)
    monkeypatch.setattr(
        ceiling,
        "run_oracle_record",
        lambda oracle, modules: SimpleNamespace(passed=True),
    )
    rows = ceiling._execute_catalog_for_variant(
        ceiling.BUGGY_CANDIDATES[0], inputs["catalog"]
    )
    expected_context_count = len(
        {case["action_id"] for case in inputs["catalog"]["cases"]}
    )
    assert len(rows) == 24
    assert opened == [ceiling.BUGGY_VARIANT_IDS[0]] * expected_context_count


def test_fresh_post_execution_identity_drift_returns_no_partial_claims(
    diagnostic,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tracked, _ = diagnostic
    before = ceiling._load_validated_inputs()
    after = deepcopy(before)
    first_hash = next(iter(after["working_tree_hashes"]))
    after["working_tree_hashes"][first_hash] = "0" * 64
    loads = iter((before, after))
    monkeypatch.setattr(ceiling, "_load_validated_inputs", lambda: next(loads))
    rows_by_variant = {
        row["variant_id"]: deepcopy(row["catalog_case_results"])
        for row in tracked["variant_diagnostics"]
    }
    monkeypatch.setattr(
        ceiling,
        "_execute_catalog_for_variant",
        lambda candidate, catalog: rows_by_variant[candidate.variant_id],
    )
    events: list[dict[str, object]] = []
    invalid = ceiling.run_fixed_catalog_diagnostic(event_log=events)
    assert invalid["validation_status"]["status"] == ceiling.INVALID_STATUS
    assert invalid["reason_codes"] == ["P2BDiagnosticError"]
    assert "variant_diagnostics" not in invalid
    assert [row["event"] for row in events] == [
        "p2b_pre_diagnostic_gate_passed",
        "p2b_catalog_case_execution_started",
        "p2b_catalog_case_execution_completed",
    ]


@pytest.mark.parametrize(
    "execution_input_suffix",
    [
        "p2a/artifacts/candidates/patches/P2A-BUG-001.patch",
        "p1b/artifacts/real_diff/baseline/checkout/cart.py",
    ],
)
def test_execution_patch_and_baseline_drift_fail_before_cached_content(
    execution_input_suffix: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_hash_identity_file = ceiling._hash_identity_file
    matched = False

    def drift_one_execution_input(path):
        nonlocal matched
        portable = path.as_posix()
        if portable.endswith(execution_input_suffix):
            matched = True
            _, working_tree = real_hash_identity_file(path)
            return "0" * 64, working_tree
        return real_hash_identity_file(path)

    def forbidden_cache_lookup(*args, **kwargs):
        raise AssertionError("drifted execution input must fail before cache lookup")

    monkeypatch.setattr(
        ceiling, "_hash_identity_file", drift_one_execution_input
    )
    monkeypatch.setattr(
        ceiling, "_load_validated_input_content", forbidden_cache_lookup
    )
    with pytest.raises(ceiling.P2BDiagnosticError, match="accepted input drifted"):
        ceiling._load_validated_inputs()
    assert matched is True


def test_lf_canonical_identity_is_portable_but_raw_identity_is_exact() -> None:
    lf = b"first line\nsecond line\n"
    crlf = b"first line\r\nsecond line\r\n"
    lf_canonical, lf_raw = ceiling._identity_hashes(lf)
    crlf_canonical, crlf_raw = ceiling._identity_hashes(crlf)
    assert lf_canonical == crlf_canonical
    assert lf_raw != crlf_raw


def test_case_row_mutations_and_derived_summary_drift_are_rejected(diagnostic) -> None:
    summary, _ = diagnostic
    mutation = deepcopy(summary)
    rows = mutation["variant_diagnostics"][0]["catalog_case_results"]
    rows[0], rows[1] = rows[1], rows[0]
    mutation["variant_diagnostics"][0]["case_results_digest"] = ceiling.canonical_rows_digest(rows)
    with pytest.raises(ceiling.P2BDiagnosticError):
        ceiling.validate_diagnostic_summary(mutation)

    mutation = deepcopy(summary)
    mutation["variant_diagnostics"][0]["catalog_case_results"][0]["passed"] = 1
    with pytest.raises(ceiling.P2BDiagnosticError, match="exact bool"):
        ceiling.validate_diagnostic_summary(mutation)

    mutation = deepcopy(summary)
    mutation["overall_diagnostic"]["ceiling_discovery_loss"]["numerator"] = 1
    with pytest.raises(ceiling.P2BDiagnosticError, match="recomputation"):
        ceiling.validate_diagnostic_summary(mutation)


@pytest.mark.parametrize(
    ("collection", "mutation"),
    [
        ("variant_diagnostics", "missing"),
        ("variant_diagnostics", "duplicate"),
        ("variant_diagnostics", "extra"),
        ("formal_policy_ids", "missing"),
        ("formal_policy_ids", "duplicate"),
        ("formal_policy_ids", "extra"),
        ("bucket_ids", "missing"),
        ("bucket_ids", "duplicate"),
        ("bucket_ids", "extra"),
        ("action_specs", "missing"),
        ("action_specs", "duplicate"),
        ("action_specs", "extra"),
    ],
)
def test_missing_duplicate_and_extra_support_is_rejected(
    diagnostic, collection: str, mutation: str
) -> None:
    summary, _ = diagnostic
    changed = deepcopy(summary)
    values = changed[collection]
    if mutation == "missing":
        values.pop()
    elif mutation == "duplicate":
        values[-1] = deepcopy(values[0])
    else:
        values.append(deepcopy(values[0]))
    with pytest.raises(ceiling.P2BDiagnosticError):
        ceiling.validate_diagnostic_summary(changed)


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "extra"])
def test_missing_duplicate_and_extra_case_rows_are_rejected(
    diagnostic, mutation: str
) -> None:
    summary, _ = diagnostic
    changed = deepcopy(summary)
    rows = changed["variant_diagnostics"][0]["catalog_case_results"]
    if mutation == "missing":
        rows.pop()
    elif mutation == "duplicate":
        rows[-1] = deepcopy(rows[0])
    else:
        rows.append(deepcopy(rows[0]))
    changed["variant_diagnostics"][0]["case_results_digest"] = (
        ceiling.canonical_rows_digest(rows)
    )
    with pytest.raises(ceiling.P2BDiagnosticError):
        ceiling.validate_diagnostic_summary(changed)


def test_input_identity_and_case_digest_mutations_are_rejected(diagnostic) -> None:
    summary, _ = diagnostic
    identity = deepcopy(summary)
    identity["input_identity"]["accepted_p2a_summary_digest"] = "0" * 64
    with pytest.raises(ceiling.P2BDiagnosticError, match="input identity"):
        ceiling.validate_diagnostic_summary(identity)

    digest = deepcopy(summary)
    digest["variant_diagnostics"][0]["case_results_digest"] = "0" * 64
    with pytest.raises(ceiling.P2BDiagnosticError, match="digest mismatch"):
        ceiling.validate_diagnostic_summary(digest)


def test_invalid_summary_has_no_partial_claims_and_cannot_self_accept() -> None:
    invalid = ceiling.invalid_diagnostic_summary("synthetic_input_drift")
    assert invalid["validation_status"]["status"] == ceiling.INVALID_STATUS
    assert "variant_diagnostics" not in invalid
    assert "policy_comparison" not in invalid
    assert invalid["software_acceptance"]["accepted"] is False
    assert ceiling.validate_diagnostic_summary(invalid) == invalid
    invalid["software_acceptance"]["accepted"] = True
    with pytest.raises(ceiling.P2BDiagnosticError, match="self-accept"):
        ceiling.validate_diagnostic_summary(invalid)


def test_policy_compatibility_and_p2a_runners_are_not_needed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*args, **kwargs):
        raise AssertionError("policy/outcome/compatibility runner must not execute")

    monkeypatch.setattr(p2a_evaluation, "run_versioned_evaluation", forbidden)
    monkeypatch.setattr(p2a_evaluation, "_run_policy", forbidden)
    monkeypatch.setattr(p2a_compatibility, "run_legacy_exact_compatibility", forbidden)
    summary = ceiling.run_fixed_catalog_diagnostic()
    assert summary["validation_status"]["status"] == ceiling.VALID_STATUS
