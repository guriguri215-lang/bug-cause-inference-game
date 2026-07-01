from bug_cause_inference.p1b.actions import P1B_ACTION_SPECS, run_action
from bug_cause_inference.p1b.dataset import get_variant


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


def test_p1b_action_costs_match_spec():
    assert {action: spec.cost for action, spec in P1B_ACTION_SPECS.items()} == EXPECTED_COSTS


def test_p1b_bug_012_observes_string_threshold_type_error():
    variant = get_variant("P1B-BUG-012")

    observation = run_action(variant, "run_config_matrix_tests")

    assert observation.bug_detected
    assert observation.observation_type == "exception_trace"
    assert observation.exception_type == "TypeError"
    assert "FREE_SHIPPING_THRESHOLD" in observation.summary


def test_p1b_clean_action_returns_no_bug_evidence():
    variant = get_variant("P1B-CLEAN-021")

    observation = run_action(variant, "run_boundary_tests")

    assert not observation.bug_detected
    assert observation.no_bug_evidence
    assert observation.observation_type == "clean_test_pass"

