import pytest

from bug_cause_inference.p1b.actions import P1B_ACTION_SPECS, run_action
from bug_cause_inference.p1b.dataset import get_variant, load_p1b_variants


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
