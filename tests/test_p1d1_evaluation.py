import json
from copy import deepcopy
from fractions import Fraction

import pytest

from bug_cause_inference.p1d.evaluation import (
    P1D1_BUCKET_IDS,
    P1D1_DIAGNOSTIC_ONLY_POLICY_IDS,
    P1D1_FORMAL_STRATEGY_IDS,
    p1d1_summary_to_json,
    p1d1_summary_to_markdown,
)
from bug_cause_inference.p1d import evaluation as p1d1_evaluation


EXPECTED_FORMAL_POLICIES = (
    "fixed_checklist",
    "test_first",
    "coverage_first",
    "recent_diff_first",
    "cause_only_p1a_style",
    "expected_utility_per_cost",
)
EXPECTED_BUCKETS = (
    "boundary_precision",
    "missing_optional_input",
    "config_normalization",
    "state_sequence",
    "spec_semantics",
)


def test_p1d1_builder_uses_existing_execution_grounded_p1c_path(
    monkeypatch,
    p1d1_source_and_summary,
):
    source, expected_summary = p1d1_source_and_summary
    call = {}

    def fake_evaluate_p1c(*, policies, observation_mode):
        call.update(policies=policies, observation_mode=observation_mode)
        return source

    monkeypatch.setattr(p1d1_evaluation, "evaluate_p1c", fake_evaluate_p1c)

    assert p1d1_evaluation.build_p1d1_summary() == expected_summary
    assert call == {
        "policies": EXPECTED_FORMAL_POLICIES,
        "observation_mode": "execution_grounded",
    }


def test_p1d1_falsey_explicit_source_does_not_fall_back(monkeypatch):
    called = False

    def fake_evaluate_p1c(*, policies, observation_mode):
        nonlocal called
        called = True
        raise AssertionError("falsey explicit input must not trigger fallback evaluation")

    monkeypatch.setattr(p1d1_evaluation, "evaluate_p1c", fake_evaluate_p1c)

    with pytest.raises(ValueError, match="execution_grounded"):
        p1d1_evaluation.build_p1d1_summary({})

    assert called is False


def test_p1d1_accepts_current_and_json_round_tripped_p1c_sources(
    p1d1_source_and_summary,
):
    source, expected_summary = p1d1_source_and_summary
    round_tripped_source = json.loads(json.dumps(source))

    assert p1d1_evaluation.build_p1d1_summary(source) == expected_summary
    assert p1d1_evaluation.build_p1d1_summary(round_tripped_source) == expected_summary


@pytest.mark.parametrize(
    ("case", "message"),
    (
        ("swapped_buckets", "membership or order"),
        ("duplicate", "exactly once"),
        ("missing", "exactly once"),
        ("extra", "exactly once"),
        ("cross_bucket", "across buckets"),
        ("unstable_order", "membership or order"),
    ),
)
def test_p1d1_rejects_invalid_fixed_dataset_membership(
    case,
    message,
    p1d1_source_and_summary,
):
    source = deepcopy(p1d1_source_and_summary[0])
    buckets = source["dataset"]["bucket_sizes"]
    boundary = buckets["boundary_precision"]["variant_ids"]
    missing_optional = buckets["missing_optional_input"]["variant_ids"]

    if case == "swapped_buckets":
        boundary[0], missing_optional[0] = missing_optional[0], boundary[0]
    elif case == "duplicate":
        boundary[1] = boundary[0]
    elif case == "missing":
        boundary.pop()
    elif case == "extra":
        boundary.append("P1B-BUG-999")
    elif case == "cross_bucket":
        missing_optional[0] = boundary[0]
    elif case == "unstable_order":
        boundary[0], boundary[1] = boundary[1], boundary[0]

    with pytest.raises(ValueError, match=message):
        p1d1_evaluation.build_p1d1_summary(source)


@pytest.mark.parametrize(
    "unexpected_variant_id",
    ("P1B-BUG-999", "P1B-BUG-001"),
    ids=("extra_id", "cross_bucket_duplicate"),
)
def test_p1d1_rejects_unexpected_dataset_bucket_key(
    unexpected_variant_id,
    p1d1_source_and_summary,
):
    source = deepcopy(p1d1_source_and_summary[0])
    original_buckets = deepcopy(source["dataset"]["bucket_sizes"])
    original_counts = (
        source["dataset"]["total_variants"],
        source["dataset"]["buggy_variants"],
        source["dataset"]["clean_variants"],
    )
    source["dataset"]["bucket_sizes"]["unexpected_bucket"] = {
        "variant_count": 1,
        "buggy_variants": 1,
        "clean_variants": 0,
        "variant_ids": [unexpected_variant_id],
    }

    assert source["dataset"]["total_variants"] == original_counts[0]
    assert source["dataset"]["buggy_variants"] == original_counts[1]
    assert source["dataset"]["clean_variants"] == original_counts[2]
    assert {
        bucket: details
        for bucket, details in source["dataset"]["bucket_sizes"].items()
        if bucket != "unexpected_bucket"
    } == original_buckets
    with pytest.raises(ValueError, match="fixed bucket key set") as exc_info:
        p1d1_evaluation.build_p1d1_summary(source)

    assert "unexpected_bucket" in str(exc_info.value)


def test_p1d1_rejects_missing_dataset_bucket_key(p1d1_source_and_summary):
    source = deepcopy(p1d1_source_and_summary[0])
    source["dataset"]["bucket_sizes"].pop("clean_false_positive")

    with pytest.raises(ValueError, match="fixed bucket key set") as exc_info:
        p1d1_evaluation.build_p1d1_summary(source)

    assert "clean_false_positive" in str(exc_info.value)


@pytest.mark.parametrize(
    ("case", "policy"),
    (
        ("duplicate", "fixed_checklist"),
        ("missing", "test_first"),
        ("extra", "coverage_first"),
    ),
)
def test_p1d1_rejects_non_exact_policy_outcome_coverage(
    case,
    policy,
    p1d1_source_and_summary,
):
    source = deepcopy(p1d1_source_and_summary[0])
    outcomes = source["per_variant_outcomes"][policy]

    if case == "duplicate":
        outcomes[1] = deepcopy(outcomes[0])
    elif case == "missing":
        outcomes.pop()
    elif case == "extra":
        extra = deepcopy(outcomes[0])
        extra["variant_id"] = "P1B-BUG-999"
        outcomes.append(extra)

    with pytest.raises(ValueError, match="each fixed variant exactly once"):
        p1d1_evaluation.build_p1d1_summary(source)


@pytest.mark.parametrize("policy", EXPECTED_FORMAL_POLICIES)
def test_p1d1_rejects_wrong_outcome_bucket_for_every_formal_policy(
    policy,
    p1d1_source_and_summary,
):
    source = deepcopy(p1d1_source_and_summary[0])
    source["per_variant_outcomes"][policy][0]["primary_bucket"] = (
        "missing_optional_input"
    )

    with pytest.raises(ValueError, match="must use bucket"):
        p1d1_evaluation.build_p1d1_summary(source)


@pytest.mark.parametrize(
    ("policy", "variant_id", "wrong_flag"),
    (
        ("cause_only_p1a_style", "P1B-BUG-001", False),
        ("expected_utility_per_cost", "P1B-CLEAN-021", True),
    ),
)
def test_p1d1_rejects_wrong_outcome_buggy_semantics(
    policy,
    variant_id,
    wrong_flag,
    p1d1_source_and_summary,
):
    source = deepcopy(p1d1_source_and_summary[0])
    outcome = next(
        item
        for item in source["per_variant_outcomes"][policy]
        if item["variant_id"] == variant_id
    )
    outcome["is_buggy"] = wrong_flag

    with pytest.raises(ValueError, match="is_buggy semantics"):
        p1d1_evaluation.build_p1d1_summary(source)


@pytest.mark.parametrize("field", ("variant_id", "primary_bucket"))
def test_p1d1_rejects_variant_label_semantics(
    field,
    p1d1_source_and_summary,
):
    source = deepcopy(p1d1_source_and_summary[0])
    label = source["variant_labels"]["P1B-BUG-001"]
    label[field] = "P1B-BUG-002" if field == "variant_id" else "missing_optional_input"

    with pytest.raises(ValueError, match="source label"):
        p1d1_evaluation.build_p1d1_summary(source)


def test_p1d1_rejects_non_exact_variant_label_coverage(p1d1_source_and_summary):
    source = deepcopy(p1d1_source_and_summary[0])
    source["variant_labels"].pop("P1B-CLEAN-025")

    with pytest.raises(ValueError, match="variant_labels must exactly cover"):
        p1d1_evaluation.build_p1d1_summary(source)


@pytest.mark.parametrize(
    ("bucket", "field", "wrong_count"),
    (
        ("boundary_precision", "variant_count", 5),
        ("clean_false_positive", "buggy_variant_count", 1),
    ),
)
def test_p1d1_rejects_bucket_metric_support_count_mismatch(
    bucket,
    field,
    wrong_count,
    p1d1_source_and_summary,
):
    source = deepcopy(p1d1_source_and_summary[0])
    source["bucket_metrics"]["recent_diff_first"][bucket][field] = wrong_count

    with pytest.raises(ValueError, match="incorrect support counts"):
        p1d1_evaluation.build_p1d1_summary(source)


def test_p1d1_formal_sets_have_stable_order(p1d1_source_and_summary):
    _, summary = p1d1_source_and_summary

    assert P1D1_FORMAL_STRATEGY_IDS == EXPECTED_FORMAL_POLICIES
    assert P1D1_BUCKET_IDS == EXPECTED_BUCKETS
    assert summary["formal_strategy_ids"] == list(EXPECTED_FORMAL_POLICIES)
    assert summary["diagnostic_only_policy_ids"] == ["random_action"]
    assert P1D1_DIAGNOSTIC_ONLY_POLICY_IDS == ("random_action",)
    assert "random_action" not in summary["formal_strategy_ids"]
    assert summary["bucket_ids"] == list(EXPECTED_BUCKETS)
    assert "clean_false_positive" not in summary["bucket_ids"]


def test_p1d1_all_cells_are_exact_four_variant_aggregates(p1d1_source_and_summary):
    _, summary = p1d1_source_and_summary
    cells = summary["g0_discovery_loss_matrix"]["cells_by_policy"]

    assert sum(len(row) for row in cells.values()) == 30
    for policy in EXPECTED_FORMAL_POLICIES:
        for bucket in EXPECTED_BUCKETS:
            cell = cells[policy][bucket]
            numerator = cell["discovered_numerator"]
            assert cell["variant_denominator"] == 4
            assert cell["discovery_rate"] == float(Fraction(numerator, 4))
            assert cell["discovery_loss"] == float(Fraction(4 - numerator, 4))


def test_p1d1_cell_variant_lists_are_stable_disjoint_partitions(p1d1_source_and_summary):
    _, summary = p1d1_source_and_summary
    dataset = summary["dataset_summary"]
    cells = summary["g0_discovery_loss_matrix"]["cells_by_policy"]

    for policy in EXPECTED_FORMAL_POLICIES:
        for bucket in EXPECTED_BUCKETS:
            cell = cells[policy][bucket]
            support = dataset["bucket_membership"][bucket]
            assert cell["diagnostic_variant_ids"] == support
            assert cell["discovered_variant_ids"] == [
                variant_id
                for variant_id in support
                if variant_id not in cell["missed_variant_ids"]
            ]
            assert cell["missed_variant_ids"] == [
                variant_id
                for variant_id in support
                if variant_id not in cell["discovered_variant_ids"]
            ]
            assert set(cell["discovered_variant_ids"]).isdisjoint(cell["missed_variant_ids"])
            assert set(cell["discovered_variant_ids"] + cell["missed_variant_ids"]) == set(
                support
            )


def test_p1d1_restricted_pure_result_recomputes_from_matrix(p1d1_source_and_summary):
    _, summary = p1d1_source_and_summary
    cells = summary["g0_discovery_loss_matrix"]["cells_by_policy"]
    solution = summary["restricted_pure_solution"]
    exact_worst = {}

    for policy in EXPECTED_FORMAL_POLICIES:
        losses = {
            bucket: Fraction(
                cells[policy][bucket]["variant_denominator"]
                - cells[policy][bucket]["discovered_numerator"],
                cells[policy][bucket]["variant_denominator"],
            )
            for bucket in EXPECTED_BUCKETS
        }
        worst = max(losses.values())
        average = sum(losses.values(), start=Fraction()) / len(EXPECTED_BUCKETS)
        exact_worst[policy] = worst
        row = solution["by_policy"][policy]
        assert row["worst_bucket_loss"] == float(worst)
        assert row["worst_bucket_ids"] == [
            bucket for bucket in EXPECTED_BUCKETS if losses[bucket] == worst
        ]
        assert row["reference_average_loss"] == float(average)
        assert row["average_to_worst_gap"] == float(worst - average)

    security_loss = min(exact_worst.values())
    assert solution["restricted_pure_security_loss"] == float(security_loss)
    assert solution["restricted_pure_security_policies"] == [
        policy for policy in EXPECTED_FORMAL_POLICIES if exact_worst[policy] == security_loss
    ]


def test_p1d1_current_formal_numeric_result_is_unchanged(p1d1_source_and_summary):
    _, summary = p1d1_source_and_summary
    cells = summary["g0_discovery_loss_matrix"]["cells_by_policy"]
    solution = summary["restricted_pure_solution"]
    first_row = [0.0, 0.75, 1.0, 1.0, 0.5]
    second_row = [0.75, 0.0, 0.75, 1.0, 0.5]

    for policy in EXPECTED_FORMAL_POLICIES[:4]:
        assert [cells[policy][bucket]["discovery_loss"] for bucket in EXPECTED_BUCKETS] == (
            first_row
        )
        assert solution["by_policy"][policy]["reference_average_loss"] == 0.65
        assert solution["by_policy"][policy]["average_to_worst_gap"] == 0.35
    for policy in EXPECTED_FORMAL_POLICIES[4:]:
        assert [cells[policy][bucket]["discovery_loss"] for bucket in EXPECTED_BUCKETS] == (
            second_row
        )
        assert solution["by_policy"][policy]["reference_average_loss"] == 0.6
        assert solution["by_policy"][policy]["average_to_worst_gap"] == 0.4

    assert solution["restricted_pure_security_loss"] == 1.0
    assert solution["restricted_pure_security_policies"] == list(EXPECTED_FORMAL_POLICIES)


def test_p1d1_mixed_solution_is_explicitly_not_computed(p1d1_source_and_summary):
    _, summary = p1d1_source_and_summary
    markdown = p1d1_summary_to_markdown(summary)

    assert summary["mixed_solution"] == {
        "computed": False,
        "reason": "mixed minimax solver not included in this P1d1 slice",
    }
    assert "mixed_minimax_value" not in summary["mixed_solution"]
    assert "investigator_distribution" not in summary["mixed_solution"]
    assert "Mixed solution: not computed" in markdown
    assert "Nash equilibrium result" not in markdown
    assert "minimax value:" not in markdown.lower()


def test_p1d1_clean_stress_is_separate(p1d1_source_and_summary):
    _, summary = p1d1_source_and_summary
    clean = summary["clean_false_positive_stress"]

    assert clean["formal_game_membership"] == "excluded"
    assert clean["clean_bucket_id"] == "clean_false_positive"
    assert len(clean["clean_variant_ids"]) == 5
    for row in clean["by_policy"].values():
        assert row["clean_variant_denominator"] == 5
        assert row["clean_false_positive_rate"] == pytest.approx(
            row["false_positive_numerator"] / 5
        )
    assert "clean_false_positive" not in summary["g0_discovery_loss_matrix"][
        "column_bucket_ids"
    ]


def test_p1d1_secondary_matrices_reuse_p1c_values_and_failure_penalty(
    p1d1_source_and_summary,
):
    source, summary = p1d1_source_and_summary
    secondary = summary["secondary_metric_matrices"]

    assert tuple(secondary) == (
        "cost_to_first_failure",
        "location_top3_loss",
        "cause_top1_loss",
        "fix_intent_top1_loss",
        "wrong_cause_high_confidence_rate",
        "mean_investigation_cost",
    )
    first_failure = secondary["cost_to_first_failure"]
    assert first_failure["failure_cost"] == 14
    assert first_failure["missed_buggy_variant_penalty"] == 14
    for policy in EXPECTED_FORMAL_POLICIES:
        outcomes = source["per_variant_outcomes"][policy]
        missed = [outcome for outcome in outcomes if outcome.get("discovered_within_budget") is False]
        assert missed
        assert all(outcome["first_failure_cost_penalized"] == 14 for outcome in missed)
        for bucket in EXPECTED_BUCKETS:
            assert first_failure["values_by_policy"][policy][bucket] == source[
                "bucket_metrics"
            ][policy][bucket]["bucket_cost_to_first_failure"]
            assert secondary["location_top3_loss"]["values_by_policy"][policy][bucket] == (
                pytest.approx(
                    1
                    - source["bucket_metrics"][policy][bucket][
                        "bucket_location_top3_accuracy"
                    ]
                )
            )
    assert all(
        matrix["used_in_restricted_pure_solution"] is False
        for matrix in secondary.values()
    )


def test_p1d1_metadata_synth_is_not_in_headline(p1d1_source_and_summary):
    _, summary = p1d1_source_and_summary

    assert summary["observation_mode"] == "execution_grounded"
    assert summary["report_role"] == "headline_primary"
    assert summary["diagnostic_reports"] == {}
    assert "metadata_synth" not in json.dumps(summary["g0_discovery_loss_matrix"])
    assert "metadata_synth" not in json.dumps(summary["restricted_pure_solution"])


def test_p1d1_json_and_markdown_are_auditable(p1d1_source_and_summary):
    _, summary = p1d1_source_and_summary
    loaded = json.loads(p1d1_summary_to_json(summary))
    markdown = p1d1_summary_to_markdown(summary)

    assert loaded == summary
    assert loaded["schema_version"] == "p1d1_finite_game_report.v1"
    assert {
        "schema_version",
        "analysis_phase",
        "game_id",
        "benchmark_id",
        "report_role",
        "observation_mode",
        "dataset_summary",
        "fixed_settings",
        "formal_strategy_ids",
        "diagnostic_only_policy_ids",
        "bucket_ids",
        "loss_definition",
        "reference_distribution",
        "g0_discovery_loss_matrix",
        "restricted_pure_solution",
        "mixed_solution",
        "clean_false_positive_stress",
        "secondary_metric_matrices",
        "diagnostic_reports",
        "non_claims",
        "notes",
    } == set(loaded)
    assert loaded["fixed_settings"]["budget_limit"] == 12
    assert loaded["fixed_settings"]["max_steps"] == 6
    assert loaded["fixed_settings"]["failure_cost"] == 14
    assert "seed_contract" in loaded["fixed_settings"]
    assert "# P1d1 Analysis-Only Finite-Game Report" in markdown
    assert "Cell Numerator/Denominator Evidence" in markdown
    assert "restricted_pure_security_loss" in markdown
    assert "Clean False-Positive Stress" in markdown
    assert "Secondary Metric Matrices" in markdown
    assert "failure_cost=14" in markdown
    assert "analysis-only" in markdown
