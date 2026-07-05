from bug_cause_inference.p1b.dataset import load_p1b_variants
from bug_cause_inference.p1b.policies import P1B_POLICIES
from bug_cause_inference.p1c.evaluation import (
    HEADLINE_KEYS,
    RAW_WORST_CASE_KEYS,
    evaluate_p1c,
    p1c_evaluation_to_markdown,
)


def test_p1c_default_evaluation_uses_execution_grounded_and_all_policies():
    summary = evaluate_p1c()

    assert summary["analysis_phase"] == "p1c1_analysis_only_worst_case_report"
    assert summary["observation_mode"] == "execution_grounded"
    assert tuple(summary["policies_evaluated"]) == P1B_POLICIES


def test_p1c_headline_summary_contains_required_keys():
    summary = evaluate_p1c(policies=("expected_utility_per_cost",))
    headline = summary["headline_worst_case_summary"]["expected_utility_per_cost"]

    assert set(HEADLINE_KEYS) <= set(headline)
    for key in HEADLINE_KEYS:
        assert "value" in headline[key]
        assert "bucket_ids" in headline[key]


def test_p1c_raw_worst_case_lists_are_present_and_use_valid_variant_ids():
    summary = evaluate_p1c(policies=("expected_utility_per_cost",))
    valid_ids = {variant.variant_id for variant in load_p1b_variants()}
    raw = summary["raw_variant_worst_cases"]["expected_utility_per_cost"]

    assert set(RAW_WORST_CASE_KEYS) <= set(raw)
    for key in RAW_WORST_CASE_KEYS:
        assert set(raw[key]) <= valid_ids


def test_p1c_markdown_states_analysis_scope_and_primary_mode():
    markdown = p1c_evaluation_to_markdown(evaluate_p1c(policies=("expected_utility_per_cost",)))

    assert "P1c" in markdown
    assert "analysis-only" in markdown
    assert "execution_grounded" in markdown
    assert "does not add new variants" in markdown
    assert "does not" in markdown
    assert "formal game-theoretic guarantee" in markdown
    assert "minimax-optimal" not in markdown
