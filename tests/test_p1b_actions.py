import pytest

from bug_cause_inference.p1b.actions import P1B_ACTION_SPECS, run_action
from bug_cause_inference.p1b.dataset import get_variant, load_p1b_variants
from bug_cause_inference.p1b.execution import (
    P1BExecutionContext,
    _coverage_counts_from_results,
    _coverage_suspicion_from_results,
)
from bug_cause_inference.p1b.reports import build_p1b_report, p1b_report_to_markdown


EXPECTED_COSTS = {
    "run_smoke_tests": 1,
    "run_boundary_tests": 2,
    "run_null_missing_tests": 2,
    "run_config_matrix_tests": 3,
    "run_state_sequence_tests": 4,
    "run_property_search": 5,
    "inspect_traceback": 1,
    "inspect_coverage_spectrum": 3,
    "inspect_recent_diff": 2,
    "inspect_spec_clause": 2,
}

BUGGY_VARIANTS = [variant for variant in load_p1b_variants() if variant.is_buggy]
CLEAN_VARIANTS = [variant for variant in load_p1b_variants() if not variant.is_buggy]
EXECUTION_GROUNDED_TEST_ACTIONS = (
    "run_smoke_tests",
    "run_boundary_tests",
    "run_null_missing_tests",
    "run_config_matrix_tests",
    "run_state_sequence_tests",
    "run_property_search",
    "inspect_traceback",
    "inspect_spec_clause",
)
REQUIRED_TEST_RESULT_FIELDS = {
    "test_id",
    "group",
    "passed",
    "expected",
    "actual",
    "exception_type",
    "reproduction_input",
    "executed_functions",
    "evidence_tags",
}


def test_p1b_action_costs_match_spec():
    assert {action: spec.cost for action, spec in P1B_ACTION_SPECS.items()} == EXPECTED_COSTS


def test_p1b_bug_012_observes_string_threshold_type_error():
    variant = get_variant("P1B-BUG-012")

    observation = run_action(variant, "run_config_matrix_tests")

    assert observation.bug_detected
    assert observation.evidence_source == "metadata_synth"
    assert observation.test_results == []
    assert observation.observation_type == "exception_trace"
    assert observation.exception_type == "TypeError"
    assert "FREE_SHIPPING_THRESHOLD" in observation.summary


@pytest.mark.parametrize("variant", BUGGY_VARIANTS, ids=lambda variant: variant.variant_id)
def test_p1b_primary_discovery_action_detects_each_buggy_variant(variant):
    observation = run_action(variant, variant.primary_discovery_action)

    assert observation.bug_detected


@pytest.mark.parametrize("variant", CLEAN_VARIANTS, ids=lambda variant: variant.variant_id)
@pytest.mark.parametrize("action_id", tuple(P1B_ACTION_SPECS), ids=str)
def test_p1b_clean_variants_never_detect_bug_and_return_no_bug_evidence(variant, action_id):
    observation = run_action(variant, action_id)

    assert not observation.bug_detected
    assert observation.no_bug_evidence


def test_p1b_clean_action_returns_no_bug_evidence():
    variant = get_variant("P1B-CLEAN-021")

    observation = run_action(variant, "run_boundary_tests")

    assert not observation.bug_detected
    assert observation.no_bug_evidence
    assert observation.observation_type == "clean_test_pass"


@pytest.mark.parametrize("variant", BUGGY_VARIANTS, ids=lambda variant: variant.variant_id)
def test_p1b_execution_grounded_primary_action_detects_each_buggy_variant(variant):
    observation = run_action(
        variant,
        variant.primary_discovery_action,
        observation_mode="execution_grounded",
    )

    assert observation.bug_detected
    assert observation.evidence_source == "execution_grounded"
    assert observation.failed_test_ids
    assert observation.test_results
    assert observation.executed_functions
    assert REQUIRED_TEST_RESULT_FIELDS <= set(observation.test_results[0])


@pytest.mark.parametrize("variant", CLEAN_VARIANTS, ids=lambda variant: variant.variant_id)
@pytest.mark.parametrize("action_id", EXECUTION_GROUNDED_TEST_ACTIONS, ids=str)
def test_p1b_execution_grounded_clean_variants_do_not_detect_bug(variant, action_id):
    observation = run_action(variant, action_id, observation_mode="execution_grounded")

    assert not observation.bug_detected
    assert observation.no_bug_evidence
    assert observation.evidence_source == "execution_grounded"
    assert observation.test_results
    assert not observation.failed_test_ids


def test_p1b_execution_grounded_observation_contains_test_and_trace_payload():
    variant = get_variant("P1B-BUG-001")

    observation = run_action(variant, "run_boundary_tests", observation_mode="execution_grounded")

    assert observation.evidence_source == "execution_grounded"
    assert "boundary.free_shipping_exact_threshold" in observation.failed_test_ids
    assert "shipping.free_shipping_eligible" in observation.failing_executed_functions
    assert observation.test_results[0]["expected"] is True
    assert observation.test_results[0]["actual"] is False
    assert "boundary_failure" in observation.test_results[0]["evidence_tags"]


def test_p1b_coverage_suspicion_uses_ochiai_counts():
    results = [
        {"test_id": "f1", "passed": False, "executed_functions": ["shipping.free_shipping_eligible", "cart.checkout_quote"]},
        {"test_id": "f2", "passed": False, "executed_functions": ["cart.checkout_quote"]},
        {"test_id": "p1", "passed": True, "executed_functions": ["shipping.free_shipping_eligible", "cart.checkout_quote"]},
        {"test_id": "p2", "passed": True, "executed_functions": ["discounts.compute_discount"]},
    ]

    counts = _coverage_counts_from_results(results)
    suspicion = _coverage_suspicion_from_results(results)

    assert counts["shipping.free_shipping_eligible"] == {"failed": 1, "passed": 1, "total_failed": 2}
    assert counts["cart.checkout_quote"] == {"failed": 2, "passed": 1, "total_failed": 2}
    assert counts["discounts.compute_discount"] == {"failed": 0, "passed": 1, "total_failed": 2}
    assert suspicion["shipping.free_shipping_eligible"] == pytest.approx(0.5)
    assert suspicion["cart.checkout_quote"] == pytest.approx(0.816497)
    assert "discounts.compute_discount" not in suspicion


def test_p1b_inspect_coverage_spectrum_uses_cached_execution_results():
    variant = get_variant("P1B-BUG-001")
    context = P1BExecutionContext()

    run_action(
        variant,
        "run_boundary_tests",
        observation_mode="execution_grounded",
        execution_context=context,
    )
    observation = run_action(
        variant,
        "inspect_coverage_spectrum",
        observation_mode="execution_grounded",
        execution_context=context,
    )

    assert observation.failed_test_ids == ["boundary.free_shipping_exact_threshold"]
    assert "boundary.quantity_upper_boundary" in observation.passed_test_ids
    assert {result["action_id"] for result in observation.test_results} == {"run_boundary_tests"}
    assert observation.coverage_suspicion["shipping.free_shipping_eligible"] == pytest.approx(1.0)
    assert observation.coverage_counts["shipping.free_shipping_eligible"] == {
        "failed": 1,
        "passed": 0,
        "total_failed": 1,
    }
    assert observation.location_scores["shipping.free_shipping_eligible"] == pytest.approx(11.0)


def test_p1b_passing_only_functions_are_not_raised_by_coverage_spectrum():
    variant = get_variant("P1B-BUG-001")
    context = P1BExecutionContext()

    run_action(
        variant,
        "run_boundary_tests",
        observation_mode="execution_grounded",
        execution_context=context,
    )
    observation = run_action(
        variant,
        "inspect_coverage_spectrum",
        observation_mode="execution_grounded",
        execution_context=context,
    )

    assert observation.coverage_counts["cart.add_item"] == {"failed": 0, "passed": 1, "total_failed": 1}
    assert "cart.add_item" not in observation.coverage_suspicion
    assert "cart.add_item" not in observation.location_scores


def test_p1b_markdown_report_shows_coverage_spectrum_when_inspected():
    report = build_p1b_report(
        get_variant("P1B-BUG-001"),
        policy="coverage_first",
        observation_mode="execution_grounded",
    )

    markdown = p1b_report_to_markdown(report)

    assert "## Coverage Spectrum" in markdown
    assert "| step | function | ochiai | failed | passed | total_failed |" in markdown
    assert "shipping.free_shipping_eligible" in markdown
