from __future__ import annotations

import copy
import json
from fractions import Fraction

import pytest

import bug_cause_inference.p1d.p1d3a_evaluation as p1d3a_evaluation
from bug_cause_inference.p1b.policies import P1B_POLICIES
from bug_cause_inference.p1d.p1d3a_evaluation import (
    P1D3A_BUCKET_IDS,
    P1D3A_COST_PROFILE_IDS,
    P1D3A_FORMAL_STRATEGY_IDS,
    P1D3A_SECONDARY_METRIC_IDS,
    build_p1d3a_source,
    build_p1d3a_summary,
    p1d3a_summary_to_json,
    p1d3a_summary_to_markdown,
)


@pytest.fixture(scope="module")
def source():
    return build_p1d3a_source()


@pytest.fixture(scope="module")
def summary(source):
    return build_p1d3a_summary(source)


def test_source_builder_uses_exact_six_and_execution_grounded(monkeypatch):
    calls = []

    def fake_evaluate_p1c(**kwargs):
        calls.append(kwargs)
        return {"sentinel": True}

    monkeypatch.setattr("bug_cause_inference.p1d.p1d3a_evaluation.evaluate_p1c", fake_evaluate_p1c)
    assert build_p1d3a_source() == {"sentinel": True}
    assert calls == [{"policies": P1D3A_FORMAL_STRATEGY_IDS, "observation_mode": "execution_grounded"}]
    assert P1B_POLICIES == ("random_action", *P1D3A_FORMAL_STRATEGY_IDS)
    assert "random_action" not in P1D3A_FORMAL_STRATEGY_IDS
    assert "state_sequence_guard" not in P1D3A_FORMAL_STRATEGY_IDS


def test_fixed_family_contract_and_distinct_identity(summary):
    assert list(summary)[:6] == [
        "schema_version", "analysis_phase", "game_family_id", "benchmark_id",
        "report_role", "observation_mode",
    ]
    assert summary["schema_version"] == "p1d3a_g1_cost_profile_family_report.v1"
    assert summary["formal_strategy_ids"] == list(P1D3A_FORMAL_STRATEGY_IDS)
    assert summary["bucket_ids"] == list(P1D3A_BUCKET_IDS)
    assert summary["cost_profile_ids"] == list(P1D3A_COST_PROFILE_IDS)
    assert summary["excluded_policy_ids"] == ["state_sequence_guard"]
    assert summary["diagnostic_only_policy_ids"] == ["random_action"]
    assert summary["dataset_summary"]["buggy_variant_count"] == 20
    assert summary["dataset_summary"]["clean_variant_count"] == 5
    assert summary["validation_status"]["primary_cell_count"] == 120
    assert not any("cross_profile" in key for key in summary)


def test_four_primary_matrices_have_complete_evidence_and_exact_solutions(summary):
    assert tuple(summary["results_by_profile"]) == P1D3A_COST_PROFILE_IDS
    allowed = {0.0, 0.25, 0.5, 0.75, 1.0}
    for profile_id, result in summary["results_by_profile"].items():
        matrix = result["primary_discovery_loss_matrix"]
        assert matrix["cell_count"] == 30
        exact_worst = {}
        for policy in P1D3A_FORMAL_STRATEGY_IDS:
            cells = matrix["cells_by_policy"][policy]
            losses = []
            for bucket in P1D3A_BUCKET_IDS:
                cell = cells[bucket]
                support = cell["support_variant_ids"]
                discovered = cell["discovered_variant_ids"]
                missed = cell["missed_variant_ids"]
                assert cell["profile_id"] == profile_id
                assert cell["variant_denominator"] == 4
                assert len(support) == 4
                assert discovered == [item for item in support if item in set(discovered)]
                assert missed == [item for item in support if item in set(missed)]
                assert not set(discovered) & set(missed)
                assert set(discovered) | set(missed) == set(support)
                assert cell["discovered_numerator"] == len(discovered)
                assert cell["discovery_rate"] == float(Fraction(len(discovered), 4))
                assert cell["discovery_loss"] == float(Fraction(len(missed), 4))
                assert cell["discovery_loss"] in allowed
                losses.append(Fraction(len(missed), 4))
            exact_worst[policy] = max(losses)
            row = result["restricted_pure_solution"]["by_policy"][policy]
            assert row["worst_bucket_loss"] == float(max(losses))
            assert row["reference_average_loss"] == float(sum(losses, start=Fraction()) / 5)
            assert row["average_to_worst_gap"] == float(max(losses) - sum(losses, start=Fraction()) / 5)
        security = min(exact_worst.values())
        solution = result["restricted_pure_solution"]
        assert solution["restricted_pure_security_loss"] == float(security)
        assert solution["restricted_pure_security_policies"] == [
            policy for policy in P1D3A_FORMAL_STRATEGY_IDS if exact_worst[policy] == security
        ]


def test_current_four_matrix_numeric_outcomes_remain_fixed(summary):
    first_four = [0.0, 0.75, 1.0, 1.0, 0.5]
    default_last_two = [0.75, 0.0, 0.75, 1.0, 0.5]
    trace_last_two = [0.75, 0.75, 1.0, 1.0, 0.0]
    for profile_id, result in summary["results_by_profile"].items():
        matrix = result["primary_discovery_loss_matrix"]["cells_by_policy"]
        rows = [
            [matrix[policy][bucket]["discovery_loss"] for bucket in P1D3A_BUCKET_IDS]
            for policy in P1D3A_FORMAL_STRATEGY_IDS
        ]
        assert rows[:4] == [first_four] * 4
        assert rows[4:] == [
            trace_last_two if profile_id == "trace_access_expensive" else default_last_two
        ] * 2
        solution = result["restricted_pure_solution"]
        assert solution["restricted_pure_security_loss"] == 1.0
        assert solution["restricted_pure_security_policies"] == list(
            P1D3A_FORMAL_STRATEGY_IDS
        )


def test_g0_deltas_clean_secondary_and_mixed_are_separate(summary):
    for result in summary["results_by_profile"].values():
        comparison = result["g0_same_policy_comparison"]
        assert comparison["comparison_scope"] == "same_policy_descriptive_discovery_loss_only"
        clean = result["clean_false_positive_stress"]
        assert clean["formal_game_membership"] == "excluded"
        assert len(clean["clean_variant_ids"]) == 5
        assert tuple(result["secondary_metric_matrices"]) == P1D3A_SECONDARY_METRIC_IDS
        first_failure = result["secondary_metric_matrices"]["cost_to_first_failure"]
        assert first_failure["failure_cost"] == 14
        assert first_failure["missed_buggy_variant_penalty"] == 14
        for metric in result["secondary_metric_matrices"].values():
            assert metric["used_in_restricted_pure_solution"] is False
            assert tuple(metric["values_by_policy"]) == P1D3A_FORMAL_STRATEGY_IDS
    assert summary["mixed_solution"] == {
        "computed": False,
        "reason": "mixed solver is outside the P1d3a initial slice",
    }


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value.update(observation_mode="metadata_synth"),
        lambda value: value["policies_evaluated"].append("random_action"),
        lambda value: value["observation_cost_stress"]["profiles"].reverse(),
        lambda value: value["observation_cost_stress"]["profiles"][0]["overlay"].update(inspect_traceback=3),
        lambda value: value["dataset"]["bucket_sizes"]["boundary_precision"]["variant_ids"].reverse(),
        lambda value: value["observation_cost_stress"]["results_by_profile"]["trace_access_expensive"]["raw_variant_worst_cases_by_policy"]["fixed_checklist"]["missed_bug_variant_ids"].append("P1B-BUG-006"),
        lambda value: value["observation_cost_stress"]["results_by_profile"]["trace_access_expensive"]["bucket_metrics_by_policy"]["fixed_checklist"]["boundary_precision"].update(bucket_bug_discovery_rate=0.5),
        lambda value: value["observation_cost_stress"]["results_by_profile"]["trace_access_expensive"]["bucket_metrics_by_policy"]["fixed_checklist"]["boundary_precision"].pop("bucket_cause_top1_accuracy"),
    ],
)
def test_invalid_sources_fail_closed_before_partial_report(source, mutate):
    invalid = copy.deepcopy(source)
    mutate(invalid)
    with pytest.raises(ValueError):
        build_p1d3a_summary(invalid)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value["observation_cost_stress"]["results_by_profile"]["trace_access_expensive"]["raw_variant_worst_cases_by_policy"]["fixed_checklist"]["location_top3_miss_variant_ids"].append("P1B-BUG-001"),
        lambda value: value["observation_cost_stress"]["results_by_profile"]["trace_access_expensive"]["bucket_metrics_by_policy"]["fixed_checklist"]["boundary_precision"].update(bucket_location_top3_accuracy=0.75),
        lambda value: value["observation_cost_stress"]["results_by_profile"]["trace_access_expensive"]["bucket_metrics_by_policy"]["fixed_checklist"]["boundary_precision"].update(bucket_cost_to_first_failure=14.1),
        lambda value: value["observation_cost_stress"]["results_by_profile"]["trace_access_expensive"]["aggregate_metrics_by_policy"]["fixed_checklist"].update(mean_investigation_cost=5.25),
        lambda value: value["observation_cost_stress"]["results_by_profile"]["trace_access_expensive"]["bucket_metrics_by_policy"]["fixed_checklist"]["clean_false_positive"].update(clean_variant_count=4),
        lambda value: value["observation_cost_stress"]["results_by_profile"]["trace_access_expensive"]["bucket_metrics_by_policy"]["fixed_checklist"]["clean_false_positive"].update(bucket_mean_investigation_cost=3.1),
        lambda value: value["observation_cost_stress"]["results_by_profile"]["trace_access_expensive"]["clean_false_positive_stress_by_policy"]["fixed_checklist"].update(clean_no_bug_stop_rate=0.3),
        lambda value: value["observation_cost_stress"].update(report_role="diagnostic"),
        lambda value: value["settings"].update(max_steps=5),
        lambda value: value["observation_cost_stress"]["profiles"][0]["effective_costs_by_action"].update(inspect_traceback=3),
    ],
)
def test_secondary_clean_cost_and_context_source_drift_fail_closed(source, mutate):
    invalid = copy.deepcopy(source)
    mutate(invalid)
    with pytest.raises(ValueError):
        build_p1d3a_summary(invalid)


def test_serializers_are_deterministic_newline_terminated_and_fail_closed(summary):
    data_json = p1d3a_summary_to_json(summary)
    data_markdown = p1d3a_summary_to_markdown(summary)
    assert data_json == p1d3a_summary_to_json(summary)
    assert data_markdown == p1d3a_summary_to_markdown(summary)
    assert data_json.endswith("\n") and data_markdown.endswith("\n")
    assert json.loads(data_json) == summary
    for profile_id in P1D3A_COST_PROFILE_IDS:
        assert profile_id in data_markdown
    assert "state_sequence_guard" in data_markdown
    invalid = copy.deepcopy(summary)
    invalid["validation_status"]["status"] = "invalid_inconclusive"
    with pytest.raises(ValueError):
        p1d3a_summary_to_json(invalid)
    with pytest.raises(ValueError):
        p1d3a_summary_to_markdown(invalid)
    invalid_cell = copy.deepcopy(summary)
    invalid_cell["results_by_profile"]["trace_access_expensive"]["primary_discovery_loss_matrix"]["cells_by_policy"]["fixed_checklist"]["boundary_precision"]["discovery_loss"] = 0.25
    with pytest.raises(ValueError):
        p1d3a_summary_to_json(invalid_cell)
    with pytest.raises(ValueError):
        p1d3a_summary_to_markdown(invalid_cell)


def _assert_both_serializers_reject(summary, mutate):
    invalid = copy.deepcopy(summary)
    mutate(invalid)
    with pytest.raises(ValueError):
        p1d3a_summary_to_json(invalid)
    with pytest.raises(ValueError):
        p1d3a_summary_to_markdown(invalid)


def _move_first_mapping_entry_to_end(mapping):
    first = next(iter(mapping))
    mapping[first] = mapping.pop(first)


def _drift_source_clean_mean_cost_consistently(value):
    profile_id = "trace_access_expensive"
    policy = "fixed_checklist"
    stress = value["observation_cost_stress"]
    result = stress["results_by_profile"][profile_id]
    bucket = result["bucket_metrics_by_policy"][policy]["clean_false_positive"]
    new_clean_mean = bucket["bucket_mean_investigation_cost"] + 0.2
    bucket["bucket_mean_investigation_cost"] = new_clean_mean
    aggregate = result["aggregate_metrics_by_policy"][policy]
    aggregate["mean_investigation_cost"] = round(
        aggregate["mean_investigation_cost"] + 0.04, 6
    )
    gap = result["profile_vs_baseline_gap_by_policy"][policy][
        "mean_investigation_cost"
    ]
    gap["profile_value"] = aggregate["mean_investigation_cost"]
    gap["gap"] = round(gap["profile_value"] - gap["baseline_value"], 6)
    clean = result["clean_false_positive_stress_by_policy"][policy]
    clean["clean_bucket_mean_investigation_cost"] = new_clean_mean
    stress["profile_vs_baseline_gap_by_policy"][profile_id][policy] = copy.deepcopy(
        result["profile_vs_baseline_gap_by_policy"][policy]
    )
    stress["clean_false_positive_stress_by_policy"][profile_id][policy] = copy.deepcopy(
        clean
    )


def _drift_source_clean_stop_rate_consistently(value):
    profile_id = "trace_access_expensive"
    policy = "fixed_checklist"
    stress = value["observation_cost_stress"]
    result = stress["results_by_profile"][profile_id]
    clean = result["clean_false_positive_stress_by_policy"][policy]
    clean["clean_no_bug_stop_rate"] = 0.8
    stress["clean_false_positive_stress_by_policy"][profile_id][policy] = copy.deepcopy(
        clean
    )


def _drift_summary_clean_value_and_source_identity(value):
    row = value["results_by_profile"]["trace_access_expensive"][
        "clean_false_positive_stress"
    ]["by_policy"]["fixed_checklist"]
    row["clean_mean_investigation_cost"] = 3.2
    row["clean_source_identity"]["clean_mean_investigation_cost"][
        "source_value"
    ] = 3.2


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value.update(report_role="headline_primary"),
        lambda value: value.update(observation_mode="metadata_synth"),
        lambda value: value["g0_reference_identity"].update(json_sha256="0" * 64),
        lambda value: value["p1d2_immutable_context"].update(hypothesis_outcome="supported"),
        lambda value: value["fixed_settings"].update(failure_cost=13),
        lambda value: value["cost_profiles"][0]["effective_costs_by_action"].update(inspect_traceback=3),
        lambda value: value["results_by_profile"]["trace_access_expensive"]["effective_costs_by_action"].update(inspect_traceback=3),
        lambda value: value["results_by_profile"]["trace_access_expensive"]["validation_status"].update(status="invalid"),
        lambda value: value["results_by_profile"]["trace_access_expensive"]["clean_false_positive_stress"]["by_policy"]["fixed_checklist"].update(clean_mean_investigation_cost=3.1),
        lambda value: value["results_by_profile"]["trace_access_expensive"]["clean_false_positive_stress"]["by_policy"]["fixed_checklist"].update(clean_no_bug_stop_rate=0.3),
        lambda value: value["results_by_profile"]["trace_access_expensive"]["secondary_metric_matrices"]["cause_top1_loss"].update(transform="identity"),
        lambda value: value["results_by_profile"]["trace_access_expensive"]["secondary_metric_matrices"]["cost_to_first_failure"].update(missed_buggy_variant_penalty=13),
        lambda value: value["results_by_profile"]["trace_access_expensive"]["secondary_metric_matrices"]["cause_top1_loss"]["source_values_by_policy"]["fixed_checklist"].update(boundary_precision=0.75),
        lambda value: value["results_by_profile"]["trace_access_expensive"]["secondary_metric_matrices"]["cause_top1_loss"]["values_by_policy"]["fixed_checklist"].update(boundary_precision=0.25),
        lambda value: value["notes"].pop(),
    ],
)
def test_serializers_reject_normative_context_profile_clean_and_secondary_drift(
    summary, mutate
):
    _assert_both_serializers_reject(summary, mutate)


def test_markdown_contains_full_audit_contract(summary):
    markdown = p1d3a_summary_to_markdown(summary)
    for token in (
        "Benchmark: `p1b_injected_bug_benchmark`",
        "Report role: `retrospective_profile_conditioned_headline_primary`",
        "P1d2 expanded restricted-pure loss",
        "### Fixed settings",
        "`min_expected_utility_per_cost`: `0.03`",
        "strong causes=",
        "discovery power=",
        "location power=",
        "effective costs=",
        "unchanged actions use default=`true`",
        "G0 worst buckets=",
        "profile worst buckets=",
        "Source P1c metric: `bucket_cause_top1_accuracy`; transform: `one_minus`",
        "Failure cost and missed-variant penalty: `14` / `14`",
        "P1c source value -> reported lower-is-better value",
        "## Public boundary",
        "P1b location metrics are function-level only",
        "P1b real-diff artifacts are not real repository histories",
    ):
        assert token in markdown


def test_runtime_profile_overlay_pair_reorder_fails_closed(monkeypatch, source):
    profiles = copy.deepcopy(p1d3a_evaluation.P1C5_COST_PROFILES)
    _move_first_mapping_entry_to_end(profiles[0]["overlay"])
    monkeypatch.setattr(p1d3a_evaluation, "P1C5_COST_PROFILES", tuple(profiles))
    with pytest.raises(ValueError):
        build_p1d3a_summary(source)


def test_runtime_profile_object_field_reorder_fails_closed(monkeypatch, source):
    profiles = copy.deepcopy(p1d3a_evaluation.P1C5_COST_PROFILES)
    _move_first_mapping_entry_to_end(profiles[0])
    monkeypatch.setattr(p1d3a_evaluation, "P1C5_COST_PROFILES", tuple(profiles))
    with pytest.raises(ValueError):
        build_p1d3a_summary(source)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: _move_first_mapping_entry_to_end(
            value["observation_cost_stress"]["profiles"][0]
        ),
        lambda value: _move_first_mapping_entry_to_end(
            value["observation_cost_stress"]["profiles"][0]["overlay"]
        ),
        lambda value: _move_first_mapping_entry_to_end(
            value["observation_cost_stress"]["profiles"][0][
                "effective_costs_by_action"
            ]
        ),
        lambda value: _move_first_mapping_entry_to_end(
            value["dataset"]["bucket_sizes"]
        ),
        lambda value: value["dataset"]["bucket_sizes"]["boundary_precision"][
            "variant_ids"
        ].reverse(),
        lambda value: value["dataset"]["bucket_sizes"].pop("state_sequence"),
        lambda value: value["dataset"]["bucket_sizes"]["boundary_precision"][
            "variant_ids"
        ].__setitem__(0, "P1B-BUG-005"),
    ],
)
def test_source_nested_mapping_and_dataset_support_order_fail_closed(source, mutate):
    invalid = copy.deepcopy(source)
    mutate(invalid)
    with pytest.raises(ValueError):
        build_p1d3a_summary(invalid)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: _move_first_mapping_entry_to_end(value["bucket_support"]),
        lambda value: value["default_action_specifications"].append(
            value["default_action_specifications"].pop(0)
        ),
        lambda value: _move_first_mapping_entry_to_end(
            value["reference_distribution"]["bucket_probabilities"]
        ),
        lambda value: _move_first_mapping_entry_to_end(
            value["cost_profiles"][0]["overlay"]
        ),
        lambda value: _move_first_mapping_entry_to_end(
            value["cost_profiles"][0]["effective_costs_by_action"]
        ),
        lambda value: _move_first_mapping_entry_to_end(
            value["results_by_profile"]["trace_access_expensive"][
                "effective_costs_by_action"
            ]
        ),
        lambda value: _move_first_mapping_entry_to_end(value["dataset_summary"]),
        lambda value: value["dataset_summary"]["buggy_variant_ids"].reverse(),
        lambda value: _move_first_mapping_entry_to_end(
            value["default_action_specifications"][0]
        ),
    ],
)
def test_serializers_reject_same_value_nested_order_drift(summary, mutate):
    _assert_both_serializers_reject(summary, mutate)


@pytest.mark.parametrize(
    "mutate",
    [
        _drift_source_clean_mean_cost_consistently,
        _drift_source_clean_stop_rate_consistently,
    ],
)
def test_source_canonical_clean_anchor_rejects_arithmetically_consistent_valid_drift(
    source, mutate
):
    invalid = copy.deepcopy(source)
    mutate(invalid)
    with pytest.raises(ValueError):
        build_p1d3a_summary(invalid)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value["results_by_profile"]["trace_access_expensive"][
            "clean_false_positive_stress"
        ]["by_policy"]["fixed_checklist"].update(clean_mean_investigation_cost=3.2),
        lambda value: value["results_by_profile"]["trace_access_expensive"][
            "clean_false_positive_stress"
        ]["by_policy"]["fixed_checklist"].update(clean_no_bug_stop_rate=0.8),
        _drift_summary_clean_value_and_source_identity,
        lambda value: value["results_by_profile"]["trace_access_expensive"][
            "clean_false_positive_stress"
        ]["by_policy"]["fixed_checklist"]["clean_source_identity"][
            "clean_mean_investigation_cost"
        ].update(source_path="P1c wrong.path"),
        lambda value: value["results_by_profile"]["trace_access_expensive"][
            "clean_false_positive_stress"
        ]["by_policy"]["fixed_checklist"]["clean_source_identity"][
            "clean_no_bug_stop_rate"
        ].update(evidence_availability="variant_level"),
        lambda value: _move_first_mapping_entry_to_end(
            value["results_by_profile"]["trace_access_expensive"][
                "clean_false_positive_stress"
            ]["by_policy"]["fixed_checklist"]["clean_source_identity"]
        ),
        lambda value: _move_first_mapping_entry_to_end(
            value["results_by_profile"]["trace_access_expensive"][
                "clean_false_positive_stress"
            ]["by_policy"]["fixed_checklist"]["clean_source_identity"][
                "clean_mean_investigation_cost"
            ]
        ),
    ],
)
def test_serializers_reject_clean_source_value_identity_drift(summary, mutate):
    _assert_both_serializers_reject(summary, mutate)


@pytest.mark.parametrize(
    "field,value",
    [
        ("evidence_source", "P1c wrong evidence path"),
        ("reconstruction_rule", "trust the displayed rate"),
    ],
)
def test_serializers_reject_primary_provenance_drift(summary, field, value):
    _assert_both_serializers_reject(
        summary,
        lambda report: report["results_by_profile"]["trace_access_expensive"][
            "primary_discovery_loss_matrix"
        ]["cells_by_policy"]["fixed_checklist"]["boundary_precision"].update(
            {field: value}
        ),
    )


def test_markdown_exposes_primary_and_clean_source_contracts(summary):
    markdown = p1d3a_summary_to_markdown(summary)
    for token in (
        "evidence_source = `P1c raw_variant_worst_cases_by_policy.missed_bug_variant_ids`",
        "reconstruction_rule = `stable bucket support minus missed IDs; discovered and missed are disjoint and exhaustive`",
        "bucket_mean_investigation_cost`",
        "clean_no_bug_stop_rate`",
        "source value=`3`",
        "evidence availability=`not_exposed_by_p1c`",
    ):
        assert token in markdown
