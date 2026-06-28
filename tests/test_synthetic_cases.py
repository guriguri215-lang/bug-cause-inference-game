from collections import Counter

from bug_cause_inference.likelihoods import CAUSES
from bug_cause_inference.synthetic_cases import DEFAULT_SEED, generate_synthetic_cases


def test_synthetic_cases_generate_50_cases():
    cases = generate_synthetic_cases(DEFAULT_SEED)

    assert len(cases) == 50
    assert Counter(case.true_cause for case in cases) == {cause: 10 for cause in CAUSES}
    assert all(len(case.initial_observations) == 2 for case in cases)
    assert all(len(case.available_investigations) == 8 for case in cases)
