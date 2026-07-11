from copy import deepcopy
from fractions import Fraction

from bug_cause_inference.p1d import p1d2_evaluation


def _fabricated_candidate_outcomes(summary, *, discovered):
    outcomes = []
    for bucket, variant_ids in summary["dataset_summary"]["bucket_membership"].items():
        for variant_id in variant_ids:
            base = {
                "variant_id": variant_id,
                "policy": p1d2_evaluation.P1D2_CANDIDATE_STRATEGY_ID,
                "primary_bucket": bucket,
                "is_buggy": bucket != "clean_false_positive",
                "stop_reason": "fabricated_fixture",
                "bug_presence_posterior": 0.5,
                "executed_action_ids": ["run_smoke_tests"],
            }
            if bucket == "clean_false_positive":
                base.update(
                    {
                        "false_positive": False,
                        "clean_no_bug_stop": True,
                        "clean_investigation_cost": 1,
                    }
                )
            else:
                base.update(
                    {
                        "discovered_within_budget": discovered,
                        "first_failure_cost_penalized": 1 if discovered else 14,
                        "location_top3_hit": discovered,
                        "cause_top1_hit": discovered,
                        "fix_intent_top1_hit": discovered,
                        "wrong_cause_high_confidence": False,
                        "investigation_cost": 1,
                    }
                )
            outcomes.append(base)
    return outcomes


def test_p1d2_formal_sets_are_six_baselines_plus_one_candidate():
    assert p1d2_evaluation.P1D2_FORMAL_STRATEGY_IDS == (
        "fixed_checklist",
        "test_first",
        "coverage_first",
        "recent_diff_first",
        "cause_only_p1a_style",
        "expected_utility_per_cost",
        "state_sequence_guard",
    )
    assert "random_action" not in p1d2_evaluation.P1D2_FORMAL_STRATEGY_IDS


def test_p1d1_hash_and_accepted_rows_validate_before_candidate_interpretation(
    p1d1_source_and_summary,
):
    _, baseline = p1d1_source_and_summary
    validation = p1d2_evaluation.validate_p1d1_baseline(baseline)
    assert validation["status"] == "valid"
    assert validation["observed_hashes"] == validation["accepted_hashes"]
    assert all(validation["checks"].values())


def test_p1d2_fabricated_supported_summary_has_exact_7_by_5_primary_matrix(
    p1d1_source_and_summary,
):
    _, baseline = p1d1_source_and_summary
    outcomes = _fabricated_candidate_outcomes(baseline, discovered=True)
    summary = p1d2_evaluation.build_p1d2_summary(baseline, outcomes)
    matrix = summary["g0_discovery_loss_matrix"]

    assert matrix["row_policy_ids"] == list(
        p1d2_evaluation.P1D2_FORMAL_STRATEGY_IDS
    )
    assert matrix["formal_cell_count"] == 35
    assert sum(len(row) for row in matrix["cells_by_policy"].values()) == 35
    for policy in summary["formal_strategy_ids"]:
        for bucket in summary["bucket_ids"]:
            cell = matrix["cells_by_policy"][policy][bucket]
            assert cell["variant_denominator"] == 4
            assert len(cell["diagnostic_variant_ids"]) == 4
            assert cell["discovery_loss"] in {0, 0.25, 0.5, 0.75, 1}
    assert summary["hypothesis_outcome"]["status"] == "supported"
    assert summary["software_acceptance"]["status"] == "accepted"


def test_p1d2_valid_fabricated_negative_result_is_not_supported_but_accepted(
    p1d1_source_and_summary,
):
    _, baseline = p1d1_source_and_summary
    outcomes = _fabricated_candidate_outcomes(baseline, discovered=False)
    summary = p1d2_evaluation.build_p1d2_summary(baseline, outcomes)

    assert summary["hypothesis_outcome"]["status"] == "not_supported"
    assert summary["software_acceptance"]["status"] == "accepted"
    assert summary["software_acceptance"]["faithful_negative_result_is_acceptable"]
    assert (
        summary["restricted_pure_comparison"][
            "candidate_worst_bucket_discovery_loss"
        ]
        == 1.0
    )


def test_p1d2_classification_uses_strict_exact_comparison():
    assert p1d2_evaluation.classify_p1d2_outcome(
        baseline_valid=True,
        contract_valid=True,
        candidate_outcomes_valid=True,
        candidate_worst_loss=Fraction(3, 4),
    ) == ("supported", "accepted")
    assert p1d2_evaluation.classify_p1d2_outcome(
        baseline_valid=True,
        contract_valid=True,
        candidate_outcomes_valid=True,
        candidate_worst_loss=Fraction(1, 1),
    ) == ("not_supported", "accepted")
    assert p1d2_evaluation.classify_p1d2_outcome(
        baseline_valid=False,
        contract_valid=True,
        candidate_outcomes_valid=True,
        candidate_worst_loss=Fraction(0),
    ) == ("invalid_inconclusive", "rejected")


def test_p1d2_baseline_drift_fails_closed_before_candidate_execution(
    p1d1_source_and_summary,
    monkeypatch,
):
    _, accepted = p1d1_source_and_summary
    drifted = deepcopy(accepted)
    drifted["g0_discovery_loss_matrix"]["cells_by_policy"]["fixed_checklist"][
        "boundary_precision"
    ]["discovered_numerator"] = 3

    def fail_run():
        raise AssertionError("candidate must not execute after baseline drift")

    monkeypatch.setattr(p1d2_evaluation, "_run_candidate_once", fail_run)
    summary = p1d2_evaluation.build_p1d2_summary(drifted)
    assert summary["baseline_validation"]["status"] == "invalid"
    assert summary["hypothesis_outcome"]["status"] == "invalid_inconclusive"
    assert summary["software_acceptance"]["status"] == "rejected"


def test_p1d2_missing_baseline_cell_fails_closed_without_serializer_crash(
    p1d1_source_and_summary,
    monkeypatch,
):
    _, accepted = p1d1_source_and_summary
    incomplete = deepcopy(accepted)
    del incomplete["g0_discovery_loss_matrix"]["cells_by_policy"]["fixed_checklist"][
        "boundary_precision"
    ]
    monkeypatch.setattr(
        p1d2_evaluation,
        "_run_candidate_once",
        lambda: (_ for _ in ()).throw(
            AssertionError("candidate must not execute after a missing baseline cell")
        ),
    )

    summary = p1d2_evaluation.build_p1d2_summary(incomplete)

    assert summary["hypothesis_outcome"]["status"] == "invalid_inconclusive"
    assert summary["software_acceptance"]["status"] == "rejected"


def test_p1d2_hidden_information_contract_violation_fails_closed(
    p1d1_source_and_summary,
    monkeypatch,
):
    _, accepted = p1d1_source_and_summary
    monkeypatch.setattr(
        p1d2_evaluation,
        "_validate_candidate_contract",
        lambda: {
            "status": "invalid",
            "checks": {"execution_context_excluded": False},
            "hidden_information_policy_input": True,
        },
    )
    monkeypatch.setattr(
        p1d2_evaluation,
        "_run_candidate_once",
        lambda: (_ for _ in ()).throw(
            AssertionError("candidate must not execute after hidden-information leakage")
        ),
    )

    summary = p1d2_evaluation.build_p1d2_summary(accepted)

    assert summary["hypothesis_outcome"]["status"] == "invalid_inconclusive"
    assert summary["software_acceptance"]["status"] == "rejected"


def test_p1d2_candidate_support_drift_is_invalid_and_separate_outputs_remain_bounded(
    p1d1_source_and_summary,
):
    _, baseline = p1d1_source_and_summary
    outcomes = _fabricated_candidate_outcomes(baseline, discovered=True)[:-1]
    summary = p1d2_evaluation.build_p1d2_summary(baseline, outcomes)
    assert summary["hypothesis_outcome"]["status"] == "invalid_inconclusive"
    assert summary["software_acceptance"]["status"] == "rejected"


def test_p1d2_clean_secondary_mixed_and_diagnostic_boundaries(
    p1d1_source_and_summary,
):
    _, baseline = p1d1_source_and_summary
    summary = p1d2_evaluation.build_p1d2_summary(
        baseline,
        _fabricated_candidate_outcomes(baseline, discovered=False),
    )
    assert "clean_false_positive" not in summary["bucket_ids"]
    assert summary["clean_false_positive_stress"]["formal_game_membership"] == (
        "excluded"
    )
    assert tuple(summary["secondary_metric_matrices"]) == (
        "cost_to_first_failure",
        "location_top3_loss",
        "cause_top1_loss",
        "fix_intent_top1_loss",
        "wrong_cause_high_confidence_rate",
        "mean_investigation_cost",
    )
    assert summary["secondary_metric_matrices"]["cost_to_first_failure"][
        "missed_buggy_variant_penalty"
    ] == 14
    assert summary["mixed_solution"]["computed"] is False
    assert summary["diagnostic_reports"]["random_action"]["computed"] is False
    assert "random_action" not in summary["g0_discovery_loss_matrix"][
        "cells_by_policy"
    ]


def test_p1d2_ids_serializers_and_cell_evidence_are_distinct_and_stable(
    p1d1_source_and_summary,
):
    _, baseline = p1d1_source_and_summary
    summary = p1d2_evaluation.build_p1d2_summary(
        baseline,
        _fabricated_candidate_outcomes(baseline, discovered=True),
    )
    assert summary["schema_version"] != baseline["schema_version"]
    assert summary["analysis_phase"] != baseline["analysis_phase"]
    assert summary["game_id"] != baseline["game_id"]
    serialized = p1d2_evaluation.p1d2_summary_to_json(summary)
    markdown = p1d2_evaluation.p1d2_summary_to_markdown(summary)
    assert serialized.endswith("\n")
    assert "# P1d2 Preregistered State-Sequence-Guard Evaluation" in markdown
    assert "Exact Cell Evidence" in markdown
    assert "Six Separate Secondary Matrices" in markdown
    assert "mixed_solution.computed: false" in markdown
