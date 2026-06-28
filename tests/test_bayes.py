from bug_cause_inference.bayes import update, uniform_prior
from bug_cause_inference.models import Observation


def test_bayesian_update_is_normalized():
    observations = [
        Observation("failing_test", "empty_or_edge_input_failure", "edge input fails"),
        Observation("boundary_result", "boundary_probe_fails", "boundary probe fails"),
    ]
    posterior = update(uniform_prior(), observations)

    assert abs(sum(posterior.values()) - 1.0) < 1e-9
    assert all(value > 0.0 for value in posterior.values())
    assert max(posterior, key=posterior.get) == "boundary_condition"
