from bug_cause_inference.likelihoods import ACTION_SPECS, CAUSES, EVIDENCE_LIKELIHOODS, validate_likelihood_table


def test_likelihood_table_has_all_categories():
    validate_likelihood_table()
    expected = set(CAUSES)
    for row in EVIDENCE_LIKELIHOODS.values():
        assert set(row) == expected


def test_eight_investigation_actions_are_defined():
    assert len(ACTION_SPECS) == 8
