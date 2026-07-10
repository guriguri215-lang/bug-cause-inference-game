import pytest

from bug_cause_inference.p1c.evaluation import evaluate_p1c
from bug_cause_inference.p1d.evaluation import P1D1_FORMAL_STRATEGY_IDS, build_p1d1_summary


@pytest.fixture(scope="session")
def p1d1_source_and_summary():
    source = evaluate_p1c(
        policies=P1D1_FORMAL_STRATEGY_IDS,
        observation_mode="execution_grounded",
    )
    return source, build_p1d1_summary(source)
