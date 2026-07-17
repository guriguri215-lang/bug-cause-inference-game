from __future__ import annotations

import hashlib
from copy import deepcopy
from dataclasses import replace

import pytest

from bug_cause_inference.p1b import execution as p1b_execution
from bug_cause_inference.p1b import policies as p1b_policies
from bug_cause_inference.p1b.actions import P1B_ACTION_SPECS
from bug_cause_inference.p1b.dataset import get_variant, load_p1b_variants
from bug_cause_inference.p1b.models import P1BSettings
from bug_cause_inference.p1d import p1d2_evaluation, p1d3a_evaluation, p1d3b_evaluation
from bug_cause_inference.p1d.evaluation import (
    P1D1_FORMAL_STRATEGY_IDS,
    p1d1_summary_to_json,
    p1d1_summary_to_markdown,
)
from bug_cause_inference.p2a import compatibility as p2a_compatibility
from bug_cause_inference.p2a.compatibility import (
    CompatibilityMismatch,
    EXPECTED_LEGACY_ARTIFACT_DIGEST,
    EXPECTED_LEGACY_CATALOG_DIGEST,
    EXPECTED_LEGACY_RUNTIME_DIGEST,
    FORMAL_SIX_POLICY_IDS,
    LEGACY_VARIANT_IDS,
    LegacyCompatibilityError,
    assert_canonical_runs_equal,
    canonical_digest,
    canonical_run_projection,
    current_contract_digests,
    expected_legacy_pairs,
    run_legacy_exact_compatibility,
    validate_exact_pair_coverage,
    validate_frozen_legacy_contracts,
    validate_canonical_path_boundary,
)


CHECKOUT_RUNTIME_PATHS = (
    "p1b/checkout/__init__.py",
    "p1b/checkout/cart.py",
    "p1b/checkout/config.py",
    "p1b/checkout/discounts.py",
    "p1b/checkout/inventory.py",
    "p1b/checkout/shipping.py",
)
LOCAL_PATH_CASES = (
    r"C:\Users\name\tree\cart.py",
    r"\\server\share\tree\cart.py",
    "file:///C:/Users/name/tree/cart.py",
    "file:///home/name/tree/cart.py",
    "/home/name/tree/cart.py",
)


@pytest.fixture(scope="session")
def compatibility_report():
    return run_legacy_exact_compatibility()


@pytest.fixture
def canonical_run():
    variant = get_variant("P1B-BUG-001")
    settings = P1BSettings()
    result = p1b_policies.run_p1b_investigation(
        variant,
        policy="recent_diff_first",
        settings=settings,
        observation_mode="execution_grounded",
    )
    return canonical_run_projection(variant, result, settings)


@pytest.fixture
def diagnostic_run():
    variant = get_variant("P1B-BUG-007")
    settings = P1BSettings()
    result = p1b_policies.run_p1b_investigation(
        variant,
        policy="fixed_checklist",
        settings=settings,
        observation_mode="execution_grounded",
    )
    return canonical_run_projection(variant, result, settings)


def _rejects_mutation(original, mutated):
    with pytest.raises(LegacyCompatibilityError):
        assert_canonical_runs_equal(
            original,
            mutated,
            variant_id=original["variant_id"],
            policy=original["policy"],
        )


def test_all_25_by_6_runs_are_exactly_covered_and_matched(compatibility_report):
    assert compatibility_report.status == "valid"
    assert compatibility_report.expected_pair_count == 150
    assert compatibility_report.observed_pair_count == 150
    assert compatibility_report.matched_pair_count == 150
    assert compatibility_report.mismatch_count == 0
    assert compatibility_report.variant_ids == LEGACY_VARIANT_IDS
    assert compatibility_report.policy_ids == FORMAL_SIX_POLICY_IDS
    assert compatibility_report.generated_paths_in_identity is False


def test_frozen_contract_digests_cover_catalog_runtime_and_artifacts(compatibility_report):
    assert current_contract_digests() == {
        "catalog_digest": EXPECTED_LEGACY_CATALOG_DIGEST,
        "runtime_digest": EXPECTED_LEGACY_RUNTIME_DIGEST,
        "artifact_digest": EXPECTED_LEGACY_ARTIFACT_DIGEST,
    }
    assert compatibility_report.catalog_digest == EXPECTED_LEGACY_CATALOG_DIGEST
    assert compatibility_report.runtime_digest == EXPECTED_LEGACY_RUNTIME_DIGEST
    assert compatibility_report.artifact_digest == EXPECTED_LEGACY_ARTIFACT_DIGEST


def test_runtime_contract_includes_checkout_sources_exactly_once_in_stable_order():
    source_paths = [
        row["path"]
        for row in p2a_compatibility._runtime_contract()["source_hashes"]
    ]
    checkout_paths = [path for path in source_paths if path.startswith("p1b/checkout/")]

    assert tuple(checkout_paths) == CHECKOUT_RUNTIME_PATHS
    assert all(source_paths.count(path) == 1 for path in CHECKOUT_RUNTIME_PATHS)
    assert all("\\" not in path and not path.startswith("/") for path in source_paths)


def test_checkout_source_hash_drift_fails_public_gate_before_execution_with_invalid_report(
    monkeypatch,
):
    original_hash = p2a_compatibility._normalized_text_hash

    def drift_one_checkout_hash(path):
        if path.as_posix().endswith("/p1b/checkout/cart.py"):
            return "0" * 64
        return original_hash(path)

    def execution_must_not_start(*args, **kwargs):
        raise AssertionError("adapter execution started before runtime validation")

    monkeypatch.setattr(
        p2a_compatibility,
        "_normalized_text_hash",
        drift_one_checkout_hash,
    )
    monkeypatch.setattr(
        p2a_compatibility,
        "isolated_legacy_checkout",
        execution_must_not_start,
    )

    with pytest.raises(LegacyCompatibilityError, match="runtime_digest") as error:
        run_legacy_exact_compatibility()

    report = error.value.report
    assert report is not None
    assert report.status == "invalid"
    assert report.observed_pair_count == 0
    assert report.matched_pair_count == 0
    assert report.runtime_digest != EXPECTED_LEGACY_RUNTIME_DIGEST
    assert report.catalog_digest == EXPECTED_LEGACY_CATALOG_DIGEST
    assert report.artifact_digest == EXPECTED_LEGACY_ARTIFACT_DIGEST


def test_diagnostic_digest_is_separate_and_exact_for_every_projected_step(canonical_run):
    for step in canonical_run["steps"]:
        assert step["diagnostic_digest"] == canonical_digest(step["diagnostic_cases"])


def test_presentation_provenance_fields_are_excluded_but_recent_diff_signal_is_retained(canonical_run):
    recent_diff = next(
        step for step in canonical_run["steps"] if step["selected_action"] == "inspect_recent_diff"
    )
    observation = recent_diff["observation"]
    assert not {
        "summary",
        "evidence_source",
        "diff_artifact_path",
        "diff_excerpt",
    } & set(observation)
    assert observation["location_scores"]
    assert observation["changed_files"]
    assert observation["changed_functions"]


@pytest.mark.parametrize("raw_path", LOCAL_PATH_CASES)
@pytest.mark.parametrize("placement", ("key", "value"))
def test_local_absolute_path_categories_are_rejected_from_nested_canonical_identity(
    raw_path,
    placement,
):
    nested = (
        {raw_path: "safe"}
        if placement == "key"
        else {"safe": f"artifact={raw_path};source=canonical"}
    )
    with pytest.raises(LegacyCompatibilityError, match="Absolute local path"):
        validate_canonical_path_boundary({"outer": [("inner", nested)]})


def test_relative_canonical_provenance_paths_are_accepted():
    validate_canonical_path_boundary(
        {
            "artifact": "p1b/artifacts/real_diff/patches/P1B-BUG-001.patch",
            "changed": ["checkout/cart.py", ("checkout/shipping.py",)],
        }
    )


@pytest.mark.parametrize("raw_path", LOCAL_PATH_CASES)
def test_embedded_local_paths_are_redacted_from_comparator_diagnostics(
    canonical_run,
    raw_path,
):
    changed = deepcopy(canonical_run)
    changed["final_run"]["reproduction_input"] = (
        f"artifact={raw_path};source=adapter"
    )

    with pytest.raises(LegacyCompatibilityError) as error:
        assert_canonical_runs_equal(
            canonical_run,
            changed,
            variant_id=canonical_run["variant_id"],
            policy=canonical_run["policy"],
        )

    mismatch = error.value.mismatch
    assert mismatch is not None
    assert mismatch.adapter_value == "<redacted-local-path>"
    assert raw_path not in str(error.value)
    assert raw_path not in repr(mismatch.current_value)
    assert raw_path not in repr(mismatch.adapter_value)


@pytest.mark.parametrize("raw_path", LOCAL_PATH_CASES)
def test_nested_local_path_keys_are_redacted_from_comparator_diagnostics(raw_path):
    current = {"nested": {"safe-key": {"value": 1}}}
    adapter = {"nested": {f"artifact={raw_path}": {"value": 1}}}

    with pytest.raises(LegacyCompatibilityError) as error:
        assert_canonical_runs_equal(
            current,
            adapter,
            variant_id="P1B-BUG-001",
            policy="fixed_checklist",
        )

    mismatch = error.value.mismatch
    assert mismatch is not None
    assert raw_path not in str(error.value)
    assert raw_path not in repr(mismatch.current_value)
    assert raw_path not in repr(mismatch.adapter_value)
    assert mismatch.adapter_value == ["<redacted-local-path>"]


@pytest.mark.parametrize("raw_path", LOCAL_PATH_CASES)
def test_local_path_in_comparator_field_path_is_redacted(raw_path):
    current = {"nested": {raw_path: {"value": 1}}}
    adapter = {"nested": {raw_path: {"value": 2}}}

    with pytest.raises(LegacyCompatibilityError) as error:
        assert_canonical_runs_equal(
            current,
            adapter,
            variant_id="P1B-BUG-001",
            policy="fixed_checklist",
        )

    mismatch = error.value.mismatch
    assert mismatch is not None
    assert mismatch.field_path == "<redacted-local-path>"
    assert raw_path not in str(error.value)


def test_canonical_path_rejection_from_public_gate_has_safe_invalid_report(
    monkeypatch,
):
    raw_path = r"C:\Users\name\generated\checkout.py"

    def reject_projection(*args, **kwargs):
        validate_canonical_path_boundary(
            {"nested": [f"artifact={raw_path};source=adapter"]}
        )

    monkeypatch.setattr(
        p2a_compatibility,
        "canonical_run_projection",
        reject_projection,
    )

    with pytest.raises(LegacyCompatibilityError) as error:
        run_legacy_exact_compatibility()

    report = error.value.report
    assert report is not None
    assert report.status == "invalid"
    assert report.observed_pair_count == 0
    assert raw_path not in str(error.value)
    assert raw_path not in repr(report)


@pytest.mark.parametrize("mutation", ("remove", "add", "rename"))
def test_observation_single_field_shape_mutations_fail_closed(canonical_run, mutation):
    changed = deepcopy(canonical_run)
    observation = changed["steps"][0]["observation"]
    if mutation == "remove":
        observation.pop("failure_found")
    elif mutation == "add":
        observation["unexpected"] = False
    else:
        observation["failure_seen"] = observation.pop("failure_found")
    _rejects_mutation(canonical_run, changed)


@pytest.mark.parametrize("mutation", ("value", "type"))
def test_single_scalar_value_and_type_mutations_fail_closed(canonical_run, mutation):
    changed = deepcopy(canonical_run)
    observation = changed["steps"][0]["observation"]
    observation["cost"] = observation["cost"] + 1 if mutation == "value" else float(observation["cost"])
    _rejects_mutation(canonical_run, changed)


@pytest.mark.parametrize("mutation", ("mapping_order", "list_order", "case_order"))
def test_mapping_list_and_case_order_mutations_fail_closed(diagnostic_run, mutation):
    changed = deepcopy(diagnostic_run)
    step = next(item for item in changed["steps"] if len(item["diagnostic_cases"]) >= 2)
    if mutation == "mapping_order":
        scores = step["observation"]["coverage_counts"]
        if len(scores) < 2:
            scores = step["prior_state"]["cause_posterior"]
        step_mapping = dict(reversed(list(scores.items())))
        if scores is step["observation"]["coverage_counts"]:
            step["observation"]["coverage_counts"] = step_mapping
        else:
            step["prior_state"]["cause_posterior"] = step_mapping
    elif mutation == "list_order":
        step["observation"]["executed_functions"].reverse()
    else:
        step["diagnostic_cases"][0], step["diagnostic_cases"][1] = (
            step["diagnostic_cases"][1],
            step["diagnostic_cases"][0],
        )
    _rejects_mutation(diagnostic_run, changed)


@pytest.mark.parametrize(
    "field",
    ("location_scores", "changed_files", "changed_functions"),
)
def test_recent_diff_location_and_changed_identity_mutations_fail_closed(canonical_run, field):
    changed = deepcopy(canonical_run)
    recent_diff = next(
        step for step in changed["steps"] if step["selected_action"] == "inspect_recent_diff"
    )
    value = recent_diff["observation"][field]
    if type(value) is dict:
        key = next(iter(value))
        value[key] += 1.0
    else:
        value[0] = f"mutated/{value[0]}"
    _rejects_mutation(canonical_run, changed)


@pytest.mark.parametrize(
    "mutation",
    ("expected", "actual", "passed", "case_id", "evidence_tag", "executed", "stack"),
)
def test_diagnostic_case_single_mutations_fail_closed(diagnostic_run, mutation):
    changed = deepcopy(diagnostic_run)
    step = next(item for item in changed["steps"] if item["diagnostic_cases"])
    case = step["diagnostic_cases"][0]
    if mutation == "expected":
        case["expected"] = {"mutated": True}
    elif mutation == "actual":
        case["actual"] = {"mutated": True}
    elif mutation == "passed":
        case["passed"] = not case["passed"]
    elif mutation == "case_id":
        case["test_id"] += ".mutated"
    elif mutation == "evidence_tag":
        case["evidence_tags"][0] += "_mutated"
    elif mutation == "executed":
        case["executed_functions"].append("cart.mutated")
    else:
        case["stack_functions"].append("cart.mutated")
    _rejects_mutation(diagnostic_run, changed)


@pytest.mark.parametrize(
    "mutation",
    ("score_value", "score_row_order", "feasible_order", "equal_score_tie_order"),
)
def test_action_score_feasibility_and_tie_order_mutations_fail_closed(canonical_run, mutation):
    changed = deepcopy(canonical_run)
    state = changed["steps"][0]["prior_state"]
    if mutation == "score_value":
        state["action_scores"][0]["expected_utility_per_cost"] += 0.000001
    elif mutation == "score_row_order":
        state["action_scores"][0], state["action_scores"][1] = (
            state["action_scores"][1],
            state["action_scores"][0],
        )
    elif mutation == "feasible_order":
        state["feasible_action_ids"][0], state["feasible_action_ids"][1] = (
            state["feasible_action_ids"][1],
            state["feasible_action_ids"][0],
        )
    else:
        changed["selection_order_contract"]["cause_only_tie_order"] = (
            "action_id_asc",
            "cost_asc",
            "cause_relevance_per_cost_desc",
        )
    _rejects_mutation(canonical_run, changed)


@pytest.mark.parametrize("mutation", ("stop_result", "stop_precedence"))
def test_stop_result_and_precedence_mutations_fail_closed(canonical_run, mutation):
    changed = deepcopy(canonical_run)
    if mutation == "stop_result":
        changed["terminal_state"]["common_stop_result"] = "max_steps"
    else:
        changed["stop_precedence"] = tuple(reversed(changed["stop_precedence"]))
    _rejects_mutation(canonical_run, changed)


@pytest.mark.parametrize(
    "mutation",
    ("selected_action", "step", "prior_posterior", "updated_posterior", "final_outcome"),
)
def test_trace_state_and_final_outcome_mutations_fail_closed(canonical_run, mutation):
    changed = deepcopy(canonical_run)
    if mutation == "selected_action":
        changed["steps"][0]["selected_action"] = "run_property_search"
    elif mutation == "step":
        changed["steps"][0]["step"] = 2
    elif mutation == "prior_posterior":
        changed["steps"][0]["prior_state"]["bug_presence_posterior"] += 0.01
    elif mutation == "updated_posterior":
        changed["steps"][0]["updated_state"]["cause_posterior"]["boundary_condition"] += 0.01
    else:
        changed["p1c_compatible_outcome"]["investigation_cost"] += 1
    _rejects_mutation(canonical_run, changed)


@pytest.mark.parametrize("mutation", ("remove", "duplicate", "extra"))
def test_pair_coverage_remove_duplicate_and_extra_fail_closed(mutation):
    pairs = expected_legacy_pairs()
    if mutation == "remove":
        pairs.pop()
    elif mutation == "duplicate":
        pairs[-1] = pairs[0]
    else:
        pairs.append(("P1B-BUG-999", FORMAL_SIX_POLICY_IDS[0]))
    with pytest.raises(LegacyCompatibilityError, match="exactly 25 x 6 = 150"):
        validate_exact_pair_coverage(pairs)


def test_representative_trace_only_probe_is_rejected():
    with pytest.raises(LegacyCompatibilityError, match="exactly 25 x 6 = 150"):
        validate_exact_pair_coverage(expected_legacy_pairs()[:6])


def test_pair_coverage_failure_from_public_gate_has_invalid_report(monkeypatch):
    monkeypatch.setattr(
        p2a_compatibility,
        "validate_frozen_legacy_contracts",
        lambda digests=None: digests,
    )
    monkeypatch.setattr(p2a_compatibility, "load_p1b_variants", lambda: [])

    with pytest.raises(
        LegacyCompatibilityError,
        match="exactly 25 x 6 = 150",
    ) as error:
        run_legacy_exact_compatibility()

    report = error.value.report
    assert report is not None
    assert report.status == "invalid"
    assert report.expected_pair_count == 150
    assert report.observed_pair_count == 0
    assert report.matched_pair_count == 0


def test_comparator_mismatch_from_public_gate_preserves_details_and_invalid_report(
    monkeypatch,
):
    expected_mismatch = CompatibilityMismatch(
        variant_id="P1B-BUG-001",
        policy="fixed_checklist",
        step=1,
        action_id="run_boundary_tests",
        field_path="$.steps[0].observation.cost",
        current_value=2,
        adapter_value=3,
    )

    def reject_comparison(*args, **kwargs):
        raise LegacyCompatibilityError(
            "Legacy compatibility mismatch",
            mismatch=expected_mismatch,
        )

    monkeypatch.setattr(
        p2a_compatibility,
        "assert_canonical_runs_equal",
        reject_comparison,
    )

    with pytest.raises(LegacyCompatibilityError) as error:
        run_legacy_exact_compatibility()

    report = error.value.report
    assert report is not None
    assert report.status == "invalid"
    assert report.observed_pair_count == 1
    assert report.matched_pair_count == 0
    assert report.mismatch_count == 1
    assert error.value.mismatch == expected_mismatch
    assert report.mismatches == (expected_mismatch,)


@pytest.mark.parametrize("control_flow_error", (KeyboardInterrupt, SystemExit))
def test_public_gate_does_not_convert_process_control_exceptions(
    monkeypatch,
    control_flow_error,
):
    def interrupt():
        raise control_flow_error()

    monkeypatch.setattr(p2a_compatibility, "current_contract_digests", interrupt)

    with pytest.raises(control_flow_error):
        run_legacy_exact_compatibility()


def test_catalog_case_and_action_mapping_drift_fail_before_execution(monkeypatch):
    first_id = next(iter(p1b_execution.TEST_CASES))
    changed_cases = dict(p1b_execution.TEST_CASES)
    changed_cases[first_id] = replace(changed_cases[first_id], expected={"drift": True})
    monkeypatch.setattr(p1b_execution, "TEST_CASES", changed_cases)
    with pytest.raises(LegacyCompatibilityError, match="catalog_digest"):
        validate_frozen_legacy_contracts()


def test_catalog_action_mapping_order_drift_fails_before_execution(monkeypatch):
    items = list(p1b_execution.ACTION_TEST_CASE_IDS.items())
    items[0], items[1] = items[1], items[0]
    monkeypatch.setattr(p1b_execution, "ACTION_TEST_CASE_IDS", dict(items))
    with pytest.raises(LegacyCompatibilityError, match="catalog_digest"):
        validate_frozen_legacy_contracts()


def test_policy_registry_and_action_cost_drift_fail_before_execution(monkeypatch):
    monkeypatch.setattr(
        p1b_policies,
        "P1B_POLICIES",
        (p1b_policies.P1B_POLICIES[0], *reversed(FORMAL_SIX_POLICY_IDS)),
    )
    with pytest.raises(LegacyCompatibilityError, match="policy IDs/order"):
        validate_frozen_legacy_contracts()

    monkeypatch.undo()
    first_id = next(iter(P1B_ACTION_SPECS))
    monkeypatch.setitem(
        P1B_ACTION_SPECS,
        first_id,
        replace(P1B_ACTION_SPECS[first_id], cost=P1B_ACTION_SPECS[first_id].cost + 1),
    )
    with pytest.raises(LegacyCompatibilityError, match="runtime_digest"):
        validate_frozen_legacy_contracts()


def test_p1b_p1c_p1d_non_regression_sentinels(p1d1_source_and_summary):
    source, p1d1 = p1d1_source_and_summary
    variants = load_p1b_variants()
    assert len(variants) == 25
    assert sum(variant.is_buggy for variant in variants) == 20
    assert tuple(variant.variant_id for variant in variants) == LEGACY_VARIANT_IDS
    assert P1D1_FORMAL_STRATEGY_IDS == FORMAL_SIX_POLICY_IDS
    assert len(source["per_variant_outcomes"]) == 6
    assert all(len(rows) == 25 for rows in source["per_variant_outcomes"].values())
    assert p1d1["restricted_pure_solution"]["restricted_pure_security_loss"] == 1.0
    assert tuple(
        p1d1["restricted_pure_solution"]["restricted_pure_security_policies"]
    ) == FORMAL_SIX_POLICY_IDS
    assert hashlib.sha256(p1d1_summary_to_json(p1d1).encode()).hexdigest() == (
        "d1e86525240485b615f61b6261ea239a57b7a7148bdee4a5857452cc84169bac"
    )
    assert hashlib.sha256(p1d1_summary_to_markdown(p1d1).encode()).hexdigest() == (
        "9611e6cd8d3086a0b498a89278695f75c07ccdc9f840b6b3d00b14b0234f1dad"
    )

    p1d2 = p1d2_evaluation.build_p1d2_summary(p1d1)
    assert p1d2["hypothesis_outcome"]["status"] == "not_supported"
    assert p1d2["software_acceptance"]["status"] == "accepted"
    assert p1d3a_evaluation.P1D3A_GAME_FAMILY_ID != p1d3b_evaluation.P1D3B_GAME_FAMILY_ID
    assert p1d3a_evaluation.P1D3A_COST_PROFILE_IDS == (
        "trace_access_expensive",
        "sequence_reproduction_expensive",
        "localization_evidence_expensive",
        "targeted_reproduction_expensive",
    )
    assert p1d3b_evaluation.P1D3B_PROFILE_IDS == (
        "traceback_signal_dropout",
        "recent_diff_signal_delay",
        "coverage_signal_dropout",
        "sequence_reproduction_delay",
    )
    assert p1d3b_evaluation._P1D3A_IMMUTABLE_CONTEXT["reviewed_json_sha256"] == (
        "e60b07a3ff95df2fb97006f86a3dd8081151565466e12638f9742748495dcb71"
    )
    assert p1d3b_evaluation._P1D3A_IMMUTABLE_CONTEXT["reviewed_markdown_sha256"] == (
        "1367f81d6ebb7322e74ae8bf65f20cecc2475f52c3864d0122807c678af2368a"
    )
    assert p1d3b_evaluation._P1D3A_IMMUTABLE_CONTEXT["separation_rule"] == (
        "immutable_separate_not_invoked_or_copied"
    )
