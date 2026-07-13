from __future__ import annotations

import copy
import json
from fractions import Fraction

import pytest

import bug_cause_inference.p1d.p1d3b_evaluation as module
from bug_cause_inference.p1b.policies import P1B_POLICIES
from bug_cause_inference.p1d.p1d3b_evaluation import (
    P1D3B_BUCKET_IDS,
    P1D3B_FORMAL_STRATEGY_IDS,
    P1D3B_PROFILE_IDS,
    P1D3B_SECONDARY_METRIC_IDS,
    build_p1d3b_source,
    build_p1d3b_summary,
    p1d3b_summary_to_json,
    p1d3b_summary_to_markdown,
    validate_p1d3b_summary,
)


@pytest.fixture(scope="module")
def source():
    return build_p1d3b_source()


@pytest.fixture(scope="module")
def summary(source):
    return build_p1d3b_summary(source)


def test_source_builder_is_explicit_exact_six_execution_grounded(monkeypatch):
    calls = []

    def fake(**kwargs):
        calls.append(kwargs)
        return {"sentinel": True}

    monkeypatch.setattr(module, "evaluate_p1c", fake)
    assert build_p1d3b_source() == {"sentinel": True}
    assert calls == [{
        "policies": P1D3B_FORMAL_STRATEGY_IDS,
        "observation_mode": "execution_grounded",
    }]
    assert P1B_POLICIES == ("random_action", *P1D3B_FORMAL_STRATEGY_IDS)
    assert "random_action" not in P1D3B_FORMAL_STRATEGY_IDS
    assert "state_sequence_guard" not in P1D3B_FORMAL_STRATEGY_IDS


def test_distinct_identity_and_exhaustive_top_level_order(summary):
    assert list(summary) == list(module._TOP_KEYS)
    assert summary["schema_version"] == "p1d3b_g1_dropout_delay_profile_family_report.v1"
    assert summary["game_family_id"] == "p1d3b_g1_dropout_delay_profile_conditioned_execution_grounded_v1"
    assert summary["dropout_delay_profile_ids"] == list(P1D3B_PROFILE_IDS)
    assert summary["formal_strategy_ids"] == list(P1D3B_FORMAL_STRATEGY_IDS)
    assert summary["excluded_policy_ids"] == ["state_sequence_guard"]
    assert summary["diagnostic_only_policy_ids"] == ["random_action"]
    assert summary["dataset_summary"]["primary_cell_count_total"] == 120


def test_p1c9_profiles_and_source_projection_are_exact(source, summary):
    stress = source["observation_dropout_delay_stress"]
    assert list(stress) == list(module._STRESS_KEYS)
    assert [p["profile_id"] for p in stress["profiles"]] == list(P1D3B_PROFILE_IDS)
    assert [p["perturbation_type"] for p in stress["profiles"]] == [
        "dropout", "delay", "dropout", "delay",
    ]
    projection = module._projection(stress)
    encoded = module._projection_bytes(projection)
    assert not encoded.endswith(b"\n")
    assert json.loads(encoded) == projection
    assert list(projection) == list(module._PROJECTION_FIELDS)
    assert module._sha256_bytes(encoded) == summary["retrospective_analysis"]["source_public_projection_sha256"]
    assert len(summary["retrospective_analysis"]["source_public_projection_sha256"]) == 64


@pytest.mark.parametrize("duplicate", [
    "profile_vs_baseline_gap_by_policy",
    "recovery_diagnostics_by_policy",
    "clean_false_positive_stress_by_policy",
])
def test_duplicate_objects_pass_recursive_order_and_type_exactness(source, duplicate):
    stress = source["observation_dropout_delay_stress"]
    for profile in P1D3B_PROFILE_IDS:
        assert module._ordered_exact(
            stress[duplicate][profile], stress["results_by_profile"][profile][duplicate]
        )


@pytest.mark.parametrize("mutation", ["missing", "extra", "reorder", "type", "value"])
def test_duplicate_objects_fail_closed_on_all_drift_classes(source, mutation):
    changed = copy.deepcopy(source)
    stress = changed["observation_dropout_delay_stress"]
    stress["recovery_diagnostics_by_policy"] = copy.deepcopy(
        stress["recovery_diagnostics_by_policy"]
    )
    duplicate = stress["recovery_diagnostics_by_policy"][P1D3B_PROFILE_IDS[0]]
    policy = P1D3B_FORMAL_STRATEGY_IDS[0]
    row = duplicate[policy]
    if mutation == "missing":
        row.pop(next(iter(row)))
    elif mutation == "extra":
        row["unexpected"] = None
    elif mutation == "reorder":
        duplicate[policy] = {key: row[key] for key in reversed(row)}
    elif mutation == "type":
        row["source_observation_count"] = float(row["source_observation_count"])
    else:
        row["source_observation_count"] += 1
    with pytest.raises(ValueError, match="duplicate equality"):
        build_p1d3b_summary(changed)


def test_default_seven_source_and_projection_reorder_are_rejected(source):
    defaulted = copy.deepcopy(source)
    defaulted["policies_evaluated"] = ["random_action", *P1D3B_FORMAL_STRATEGY_IDS]
    with pytest.raises(ValueError, match="exact-six"):
        build_p1d3b_summary(defaulted)
    reordered = copy.deepcopy(source)
    stress = reordered["observation_dropout_delay_stress"]
    reordered["observation_dropout_delay_stress"] = {
        key: stress[key] for key in reversed(stress)
    }
    with pytest.raises(ValueError, match="reordered"):
        build_p1d3b_summary(reordered)


def test_projection_numeric_type_value_and_report_digest_drift_are_rejected(source, summary):
    for replacement in (0, 0.350001):
        changed = copy.deepcopy(source)
        stress = changed["observation_dropout_delay_stress"]
        stress["results_by_profile"] = copy.deepcopy(stress["results_by_profile"])
        profile = P1D3B_PROFILE_IDS[0]
        policy = P1D3B_FORMAL_STRATEGY_IDS[0]
        stress["results_by_profile"][profile]["aggregate_metrics_by_policy"][policy][
            "bug_discovery_rate_within_budget"
        ] = replacement
        with pytest.raises(ValueError, match="projection identity"):
            build_p1d3b_summary(changed)
    changed_summary = copy.deepcopy(summary)
    changed_summary["retrospective_analysis"]["source_public_projection_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="digest"):
        p1d3b_summary_to_json(changed_summary)


def test_four_complete_primary_matrices_evidence_and_exact_solutions(summary):
    assert tuple(summary["results_by_profile"]) == P1D3B_PROFILE_IDS
    allowed = {0.0, 0.25, 0.5, 0.75, 1.0}
    count = 0
    for profile_id, result in summary["results_by_profile"].items():
        matrix = result["primary_discovery_loss_matrix"]
        exact_worst = {}
        for policy in P1D3B_FORMAL_STRATEGY_IDS:
            losses = []
            for bucket in P1D3B_BUCKET_IDS:
                cell = matrix["cells_by_policy"][policy][bucket]
                support = cell["support_variant_ids"]
                discovered = cell["discovered_variant_ids"]
                missed = cell["missed_variant_ids"]
                assert len(support) == 4
                assert discovered == [x for x in support if x in set(discovered)]
                assert missed == [x for x in support if x in set(missed)]
                assert not set(discovered) & set(missed)
                assert set(discovered) | set(missed) == set(support)
                assert cell["discovery_rate"] == float(Fraction(len(discovered), 4))
                assert cell["discovery_loss"] == float(Fraction(len(missed), 4))
                assert cell["discovery_loss"] in allowed
                assert cell["evidence_source"]["evidence_availability"] == "public_complete_buggy_missed_variant_ids"
                losses.append(Fraction(len(missed), 4))
                count += 1
            exact_worst[policy] = max(losses)
        solution = result["restricted_pure_solution"]
        security = min(exact_worst.values())
        assert solution["restricted_pure_security_loss"] == float(security)
        assert solution["restricted_pure_security_policies"] == [
            p for p in P1D3B_FORMAL_STRATEGY_IDS if exact_worst[p] == security
        ]
    assert count == 120


def test_current_profile_conditioned_numeric_outcomes_are_fixed(summary):
    first = [0.0, 0.75, 1.0, 1.0, 0.5]
    last = [0.75, 0.0, 0.75, 1.0, 0.5]
    recent_diff = [0.0, 0.75, 0.0, 1.0, 0.5]
    for profile_id, result in summary["results_by_profile"].items():
        matrix = result["primary_discovery_loss_matrix"]["cells_by_policy"]
        rows = {
            policy: [matrix[policy][bucket]["discovery_loss"] for bucket in P1D3B_BUCKET_IDS]
            for policy in P1D3B_FORMAL_STRATEGY_IDS
        }
        assert [rows[p] for p in P1D3B_FORMAL_STRATEGY_IDS[:3]] == [first] * 3
        assert rows["recent_diff_first"] == (
            recent_diff if profile_id == "recent_diff_signal_delay" else first
        )
        assert [rows[p] for p in P1D3B_FORMAL_STRATEGY_IDS[-2:]] == [last] * 2
        solution = result["restricted_pure_solution"]
        assert solution["restricted_pure_security_loss"] == 1.0
        assert solution["restricted_pure_security_policies"] == list(P1D3B_FORMAL_STRATEGY_IDS)


def test_g0_deltas_are_same_policy_and_no_cross_profile_result(summary):
    for result in summary["results_by_profile"].values():
        comparison = result["g0_same_policy_comparison"]
        assert list(comparison) == [
            "comparison_role", "metric_id", "cell_deltas_by_policy",
            "reference_average_deltas_by_policy", "worst_bucket_loss_deltas_by_policy",
            "g0_worst_bucket_ids_by_policy", "profile_worst_bucket_ids_by_policy",
        ]
        assert tuple(comparison["cell_deltas_by_policy"]) == P1D3B_FORMAL_STRATEGY_IDS
    assert not any("ranking" in key or "winner" in key for key in summary)


def test_secondary_recovery_and_clean_source_identity_boundaries(summary):
    for result in summary["results_by_profile"].values():
        secondary = result["secondary_metric_matrices"]
        assert [item["metric_id"] for item in secondary] == list(P1D3B_SECONDARY_METRIC_IDS)
        for matrix in secondary:
            assert matrix["used_in_restricted_pure_solution"] is False
            for policy in P1D3B_FORMAL_STRATEGY_IDS:
                for bucket in P1D3B_BUCKET_IDS:
                    identity = matrix["source_values_by_policy"][policy][bucket]
                    assert list(identity) == [
                        "source_path", "source_field", "source_value", "evidence_availability"
                    ]
                    assert identity["evidence_availability"] == "not_exposed_by_p1c9"
        for row in result["recovery_diagnostics_by_policy"].values():
            assert list(row)[-1] == "source_identity_by_field"
            assert list(row["source_identity_by_field"]) == list(module._RECOVERY_FIXED_KEYS)
            for identity in row["source_identity_by_field"].values():
                assert identity["evidence_availability"] == "not_exposed_by_p1c9"
        for row in result["clean_false_positive_stress"].values():
            identity = row["source_identity_by_field"]
            assert list(identity) == list(module._CLEAN_IDENTITY_KEYS)
            assert identity["diagnostic_variant_ids"]["evidence_availability"] == "public_diagnostic_variant_ids"
            assert identity["clean_bucket_mean_investigation_cost"]["evidence_availability"] == "not_exposed_by_p1c9"
            assert identity["clean_no_bug_stop_rate"]["evidence_availability"] == "not_exposed_by_p1c9"


@pytest.mark.parametrize("target", ["secondary", "recovery", "clean"])
def test_source_identity_drift_is_rejected_before_serialization(summary, target):
    changed = copy.deepcopy(summary)
    result = changed["results_by_profile"][P1D3B_PROFILE_IDS[0]]
    policy = P1D3B_FORMAL_STRATEGY_IDS[0]
    if target == "secondary":
        identity = result["secondary_metric_matrices"][0]["source_values_by_policy"][policy][P1D3B_BUCKET_IDS[0]]
        identity["evidence_availability"] = "invented_variant_evidence"
    elif target == "recovery":
        identity = result["recovery_diagnostics_by_policy"][policy]["source_identity_by_field"]
        identity["source_observation_count"]["source_value"] += 1
    else:
        identity = result["clean_false_positive_stress"][policy]["source_identity_by_field"]
        identity["clean_no_bug_stop_rate"]["evidence_availability"] = "public_diagnostic_variant_ids"
    with pytest.raises(ValueError, match="identity"):
        p1d3b_summary_to_json(changed)


def test_serializers_are_deterministic_newline_terminated_and_same_summary(summary):
    json_one = p1d3b_summary_to_json(summary)
    markdown_one = p1d3b_summary_to_markdown(summary)
    assert json_one == p1d3b_summary_to_json(summary)
    assert markdown_one == p1d3b_summary_to_markdown(summary)
    assert json_one.endswith("\n") and markdown_one.endswith("\n")
    assert json.loads(json_one) == summary
    for profile in P1D3B_PROFILE_IDS:
        assert profile in markdown_one
    assert summary["retrospective_analysis"]["source_public_projection_sha256"] in markdown_one


def test_partial_or_reordered_report_cannot_serialize(summary):
    missing = copy.deepcopy(summary)
    missing.pop("software_acceptance")
    with pytest.raises(ValueError):
        p1d3b_summary_to_json(missing)
    reordered = {key: summary[key] for key in reversed(summary)}
    with pytest.raises(ValueError):
        p1d3b_summary_to_markdown(reordered)
    changed = copy.deepcopy(summary)
    changed["mixed_solution"]["computed"] = True
    with pytest.raises(ValueError):
        validate_p1d3b_summary(changed)


def test_mixed_combined_and_acceptance_are_explicit_and_performance_independent(summary):
    assert summary["mixed_solution"] == {
        "computed": False, "status": "not_computed", "reason": "outside_p1d3b_scope"
    }
    assert summary["combined_interaction"] == {
        "computed": False, "status": "not_computed",
        "reason": "requires_separate_future_design_review",
    }
    assert summary["software_acceptance"]["status"] == "accepted"
    assert summary["software_acceptance"]["performance_independent"] is True


def _assert_both_serializers_reject(summary):
    for serializer in (p1d3b_summary_to_json, p1d3b_summary_to_markdown):
        with pytest.raises(ValueError):
            serializer(summary)


def _at(value, path):
    for key in path:
        value = value[key]
    return value


_P = P1D3B_PROFILE_IDS[0]
_POL = P1D3B_FORMAL_STRATEGY_IDS[0]
_B = P1D3B_BUCKET_IDS[0]


@pytest.mark.parametrize("path", [
    ("retrospective_analysis",),
    ("public_boundary",),
    ("g0_reference_identity",),
    ("p1d2_immutable_context",),
    ("p1d3a_immutable_separate_context",),
    ("validation_status",),
    ("dataset_summary",),
    ("fixed_settings",),
    ("default_action_specifications", 0),
    ("formal_strategy_ids",),
    ("excluded_policy_ids",),
    ("diagnostic_only_policy_ids",),
    ("bucket_ids",),
    ("bucket_support",),
    ("bucket_support", _B),
    ("clean_support",),
    ("dropout_delay_profile_ids",),
    ("dropout_delay_profiles", 0),
    ("information_structure",),
    ("loss_definition",),
    ("reference_distribution",),
    ("results_by_profile",),
    ("results_by_profile", _P),
    ("results_by_profile", _P, "primary_discovery_loss_matrix"),
    ("results_by_profile", _P, "primary_discovery_loss_matrix", "cells_by_policy", _POL, _B),
    ("results_by_profile", _P, "primary_discovery_loss_matrix", "cells_by_policy", _POL, _B, "evidence_source"),
    ("results_by_profile", _P, "restricted_pure_solution"),
    ("results_by_profile", _P, "restricted_pure_solution", "by_policy", _POL),
    ("results_by_profile", _P, "g0_same_policy_comparison"),
    ("results_by_profile", _P, "g0_same_policy_comparison", "cell_deltas_by_policy", _POL),
    ("results_by_profile", _P, "secondary_metric_matrices", 0),
    ("results_by_profile", _P, "secondary_metric_matrices", 0, "source_values_by_policy", _POL, _B),
    ("results_by_profile", _P, "secondary_metric_matrices", 0, "values_by_policy", _POL),
    ("results_by_profile", _P, "secondary_metric_matrices", 0, "evidence_boundary"),
    ("results_by_profile", _P, "recovery_diagnostics_by_policy", _POL),
    ("results_by_profile", _P, "recovery_diagnostics_by_policy", _POL, "source_identity_by_field"),
    ("results_by_profile", _P, "clean_false_positive_stress", _POL),
    ("results_by_profile", _P, "clean_false_positive_stress", _POL, "source_identity_by_field"),
    ("results_by_profile", _P, "profile_validation_status"),
    ("mixed_solution",),
    ("combined_interaction",),
    ("software_acceptance",),
    ("limitations",),
    ("non_claims",),
    ("notes",),
])
@pytest.mark.parametrize("mutation", ["missing", "extra", "reorder", "wrong_container"])
def test_exhaustive_nested_schema_order_and_container_mutations_fail_closed(
    summary, path, mutation
):
    changed = copy.deepcopy(summary)
    target = _at(changed, path)
    if mutation == "wrong_container":
        parent = _at(changed, path[:-1]) if path[:-1] else changed
        key = path[-1]
        parent[key] = [] if isinstance(target, dict) else {}
    elif isinstance(target, dict):
        first = next(iter(target))
        if mutation == "missing":
            target.pop(first)
        elif mutation == "extra":
            target["unexpected_contract_field"] = None
        else:
            replacement = {key: target[key] for key in reversed(target)}
            parent = _at(changed, path[:-1]) if path[:-1] else changed
            parent[path[-1]] = replacement
    else:
        if mutation == "missing":
            target.pop(0)
        elif mutation == "extra":
            target.append({"unexpected_contract_field": None})
        else:
            if len(target) > 1:
                target.reverse()
            else:
                target.append(copy.deepcopy(target[0]))
    _assert_both_serializers_reject(changed)


@pytest.mark.parametrize("path,replacement", [
    (("dataset_summary", "buggy_variant_count"), 20.0),
    (("fixed_settings", "budget_limit"), 20.0),
    (("reference_distribution", "weights_by_bucket", _B), 1),
    (("results_by_profile", _P, "primary_discovery_loss_matrix", "cells_by_policy", _POL, _B, "discovery_rate"), 0),
    (("results_by_profile", _P, "primary_discovery_loss_matrix", "cells_by_policy", _POL, _B, "discovery_loss"), float("nan")),
    (("results_by_profile", _P, "restricted_pure_solution", "by_policy", _POL, "worst_bucket_loss"), float("inf")),
    (("results_by_profile", _P, "g0_same_policy_comparison", "reference_average_deltas_by_policy", _POL), 1),
    (("results_by_profile", _P, "secondary_metric_matrices", 0, "values_by_policy", _POL, _B), None),
    (("results_by_profile", _P, "recovery_diagnostics_by_policy", _POL, "source_observation_count"), 0.0),
    (("results_by_profile", _P, "clean_false_positive_stress", _POL, "diagnostic_variant_ids"), None),
    (("results_by_profile", _P, "profile_validation_status", "primary_cell_count"), 30.0),
])
def test_scalar_type_domain_and_arithmetic_mutations_fail_closed(summary, path, replacement):
    changed = copy.deepcopy(summary)
    parent = _at(changed, path[:-1])
    parent[path[-1]] = replacement
    _assert_both_serializers_reject(changed)


@pytest.mark.parametrize("identity_path", [
    ("results_by_profile", _P, "primary_discovery_loss_matrix", "cells_by_policy", _POL, _B, "evidence_source"),
    ("results_by_profile", _P, "secondary_metric_matrices", 0, "source_values_by_policy", _POL, _B),
    ("results_by_profile", _P, "recovery_diagnostics_by_policy", _POL, "source_identity_by_field", "source_observation_count"),
    ("results_by_profile", _P, "clean_false_positive_stress", _POL, "source_identity_by_field", "diagnostic_variant_ids"),
])
@pytest.mark.parametrize("field,replacement", [
    ("source_path", "wrong.path"),
    ("source_field", "wrong_field"),
    ("evidence_availability", "wrong_availability"),
])
def test_all_source_identity_families_reject_identity_drift(
    summary, identity_path, field, replacement
):
    changed = copy.deepcopy(summary)
    _at(changed, identity_path)[field] = replacement
    _assert_both_serializers_reject(changed)


def test_report_and_source_identity_value_simultaneous_drift_is_rejected(summary):
    changed = copy.deepcopy(summary)
    matrix = changed["results_by_profile"][_P]["secondary_metric_matrices"][0]
    identity = matrix["source_values_by_policy"][_POL][_B]
    identity["source_value"] = 13
    matrix["values_by_policy"][_POL][_B] = 13
    _assert_both_serializers_reject(changed)


def test_immutable_prior_phase_builders_and_evaluators_are_never_called(
    source, monkeypatch
):
    def forbidden(*args, **kwargs):
        raise AssertionError("immutable prior-phase evaluator/builder was invoked")

    for name in ("_run_candidate_once", "_candidate_variant_outcome", "build_p1d2_summary"):
        monkeypatch.setattr(module.p1d2_evaluation, name, forbidden)
    for name in (
        "evaluate_p1c", "build_p1d3a_source", "build_p1d3a_summary",
        "p1d3a_summary_to_json", "p1d3a_summary_to_markdown",
    ):
        monkeypatch.setattr(module.p1d3a_evaluation, name, forbidden)
    module._current_canonical_summary.cache_clear()
    fresh = build_p1d3b_summary(source)
    validate_p1d3b_summary(fresh)
    assert p1d3b_summary_to_json(fresh).endswith("\n")
    assert p1d3b_summary_to_markdown(fresh).endswith("\n")


def test_markdown_normalized_complete_audit_object_agrees_with_summary(summary):
    markdown = p1d3b_summary_to_markdown(summary)
    serialized = p1d3b_summary_to_json(summary)
    marker = "## Normalized Complete Audit Object"
    audit = markdown.split(marker, 1)[1].split("```json\n", 1)[1].split("\n```", 1)[0]
    audit_object = json.loads(audit)
    json_object = json.loads(serialized)
    assert module._ordered_exact(audit_object, json_object)
    assert module._ordered_exact(audit_object, summary)
    assert all(str(value) in audit for value in module._TOP_KEYS)


@pytest.mark.parametrize("replacement", [20.0, True, None, "20"])
def test_recursive_exact_agreement_rejects_scalar_coercion(replacement):
    left = {"outer": {"value": 20}}
    right = {"outer": {"value": replacement}}
    assert not module._ordered_exact(left, right)


def test_recursive_exact_agreement_rejects_mapping_and_container_reorder():
    left = {"outer": {"first": 1, "second": [2, None]}}
    reordered = {"outer": {"second": [2, None], "first": 1}}
    wrong_container = {"outer": {"first": 1, "second": (2, None)}}
    assert not module._ordered_exact(left, reordered)
    assert not module._ordered_exact(left, wrong_container)


def _first_numeric_slot(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if type(item) in (int, float):
                return value, key
            found = _first_numeric_slot(item)
            if found is not None:
                return found
    if isinstance(value, list):
        for index, item in enumerate(value):
            if type(item) in (int, float):
                return value, index
            found = _first_numeric_slot(item)
            if found is not None:
                return found
    return None


@pytest.mark.parametrize("family", [
    "profile_vs_baseline_gap_by_policy",
    "recovery_diagnostics_by_policy",
    "clean_false_positive_stress_by_policy",
])
@pytest.mark.parametrize("mutation", [
    "profile_reorder", "policy_reorder", "nested_reorder", "missing", "extra",
    "numeric_coercion", "wrong_scalar_container", "one_sided_drift",
])
def test_all_duplicate_families_reject_every_required_drift(source, family, mutation):
    changed = copy.deepcopy(source)
    stress = changed["observation_dropout_delay_stress"]
    duplicate = stress[family]
    profile = _P
    policy = _POL
    row = duplicate[profile][policy]
    if mutation == "profile_reorder":
        stress[family] = {key: duplicate[key] for key in reversed(duplicate)}
    elif mutation == "policy_reorder":
        duplicate[profile] = {
            key: duplicate[profile][key] for key in reversed(duplicate[profile])
        }
    elif mutation == "nested_reorder":
        duplicate[profile][policy] = {key: row[key] for key in reversed(row)}
    elif mutation == "missing":
        row.pop(next(iter(row)))
    elif mutation == "extra":
        row["unexpected_contract_field"] = None
    elif mutation == "wrong_scalar_container":
        row[next(iter(row))] = {}
    else:
        parent, key = _first_numeric_slot(row)
        if mutation == "numeric_coercion":
            parent[key] = float(parent[key]) if type(parent[key]) is int else int(parent[key])
        else:
            parent[key] += 1
    with pytest.raises(ValueError):
        build_p1d3b_summary(changed)


@pytest.mark.parametrize("mutation", [
    "missing_field", "extra_field", "top_reorder", "nested_reorder",
    "numeric_type", "numeric_value", "nan", "infinity",
])
def test_projection_contract_rejects_required_drift(source, mutation):
    changed = copy.deepcopy(source)
    stress = changed["observation_dropout_delay_stress"]
    if mutation == "missing_field":
        stress.pop("notes")
    elif mutation == "extra_field":
        stress["unexpected_contract_field"] = None
    elif mutation == "top_reorder":
        changed["observation_dropout_delay_stress"] = {
            key: stress[key] for key in reversed(stress)
        }
    elif mutation == "nested_reorder":
        profiles = stress["profiles"]
        profiles[0] = {key: profiles[0][key] for key in reversed(profiles[0])}
    else:
        row = stress["results_by_profile"][_P]["aggregate_metrics_by_policy"][_POL]
        key = "bug_discovery_rate_within_budget"
        if mutation == "numeric_type":
            row[key] = int(row[key])
        elif mutation == "numeric_value":
            row[key] += 0.01
        elif mutation == "nan":
            row[key] = float("nan")
        else:
            row[key] = float("inf")
    with pytest.raises((ValueError, TypeError)):
        build_p1d3b_summary(changed)


@pytest.mark.parametrize("context_name,field,replacement", [
    ("p1d2", "candidate_discovery_loss_row", [0.5, 0.0, 0.75, 1.0, 0.5]),
    ("p1d2", "candidate_worst_bucket_discovery_loss", 0.75),
    ("p1d2", "candidate_worst_bucket_ids", ["spec_semantics"]),
    ("p1d2", "expanded_restricted_pure_security_loss", 0.75),
    ("p1d2", "expanded_restricted_pure_security_policies", ["state_sequence_guard"]),
    ("p1d2", "hypothesis_outcome", "supported"),
    ("p1d2", "software_acceptance", "rejected"),
    ("p1d3a", "reviewed_json_sha256", "0" * 64),
    ("p1d3a", "reviewed_markdown_sha256", "0" * 64),
    ("p1d3a", "accepted_clean_projection_sha256", "0" * 64),
    ("p1d3a", "profile_count", 3),
    ("p1d3a", "primary_cell_count", 119),
    ("p1d3a", "restricted_pure_security_loss_by_profile", {
        "trace_access_expensive": 0.75,
        "sequence_reproduction_expensive": 1.0,
        "localization_evidence_expensive": 1.0,
        "targeted_reproduction_expensive": 1.0,
    }),
    ("p1d3a", "restricted_pure_security_policies_by_profile", {
        profile_id: ["fixed_checklist"]
        for profile_id in module._P1D3A_COST_PROFILE_IDS
    }),
    ("p1d3a", "separation_rule", "invoked_or_copied"),
])
def test_immutable_projection_drift_is_rejected_before_canonical_cache_initialization(
    source, monkeypatch, context_name, field, replacement
):
    context = (
        module._P1D2_IMMUTABLE_CONTEXT
        if context_name == "p1d2"
        else module._P1D3A_IMMUTABLE_CONTEXT
    )
    module._current_canonical_summary.cache_clear()
    monkeypatch.setitem(context, field, replacement)
    with pytest.raises(ValueError, match="immutable projection drifted"):
        build_p1d3b_summary(source)
    assert module._current_canonical_summary.cache_info().currsize == 0


@pytest.mark.parametrize("index", range(10))
@pytest.mark.parametrize("mutation", ["missing", "extra", "reorder", "coercion", "domain"])
def test_every_default_action_specification_rejects_mandatory_mutations(
    summary, index, mutation
):
    changed = copy.deepcopy(summary)
    action = changed["default_action_specifications"][index]
    if mutation == "missing":
        action.pop("location_power")
    elif mutation == "extra":
        action["unexpected_contract_field"] = None
    elif mutation == "reorder":
        changed["default_action_specifications"][index] = {
            key: action[key] for key in reversed(action)
        }
    elif mutation == "coercion":
        action["cost"] = float(action["cost"])
    else:
        action["discovery_power"] = 2.0
    _assert_both_serializers_reject(changed)


@pytest.mark.parametrize("profile_id", P1D3B_PROFILE_IDS)
@pytest.mark.parametrize("policy", P1D3B_FORMAL_STRATEGY_IDS)
@pytest.mark.parametrize("bucket", P1D3B_BUCKET_IDS)
def test_every_g0_cell_delta_rejects_arithmetic_drift(
    summary, profile_id, policy, bucket
):
    changed = copy.deepcopy(summary)
    changed["results_by_profile"][profile_id]["g0_same_policy_comparison"][
        "cell_deltas_by_policy"
    ][policy][bucket] += 0.25
    _assert_both_serializers_reject(changed)


@pytest.mark.parametrize("profile_id", P1D3B_PROFILE_IDS)
@pytest.mark.parametrize("policy", P1D3B_FORMAL_STRATEGY_IDS)
@pytest.mark.parametrize("field", [
    "worst_bucket_loss", "worst_bucket_ids", "reference_average_loss",
    "average_to_worst_gap",
])
def test_every_solution_row_field_rejects_drift(summary, profile_id, policy, field):
    changed = copy.deepcopy(summary)
    row = changed["results_by_profile"][profile_id]["restricted_pure_solution"][
        "by_policy"
    ][policy]
    row[field] = ["boundary_precision"] if field == "worst_bucket_ids" else 0.25
    _assert_both_serializers_reject(changed)


@pytest.mark.parametrize("profile_id", P1D3B_PROFILE_IDS)
@pytest.mark.parametrize("field", [
    "restricted_pure_security_loss", "restricted_pure_security_policies",
])
def test_every_profile_security_value_and_tie_rejects_drift(summary, profile_id, field):
    changed = copy.deepcopy(summary)
    solution = changed["results_by_profile"][profile_id]["restricted_pure_solution"]
    solution[field] = 0.75 if field.endswith("loss") else ["fixed_checklist"]
    _assert_both_serializers_reject(changed)


@pytest.mark.parametrize("profile_id", P1D3B_PROFILE_IDS)
@pytest.mark.parametrize("metric_index", range(6))
@pytest.mark.parametrize("mutation", [
    "metadata", "source_field", "transform", "pre_transform", "output",
    "evidence_boundary",
])
def test_all_twenty_four_secondary_matrices_reject_contract_drift(
    summary, profile_id, metric_index, mutation
):
    changed = copy.deepcopy(summary)
    matrix = changed["results_by_profile"][profile_id]["secondary_metric_matrices"][
        metric_index
    ]
    if mutation == "metadata":
        matrix["direction"] = "higher_is_better"
    elif mutation == "source_field":
        matrix["source_p1c9_metric"] = "wrong_field"
    elif mutation == "transform":
        matrix["transform"] = "one_minus" if matrix["transform"] == "identity" else "identity"
    elif mutation == "pre_transform":
        matrix["source_values_by_policy"][_POL][_B]["source_value"] = 0.125
    elif mutation == "output":
        matrix["values_by_policy"][_POL][_B] = 0.125
    else:
        matrix["evidence_boundary"]["reconstruction_permitted"] = True
    _assert_both_serializers_reject(changed)


@pytest.mark.parametrize("family", ["primary", "secondary", "recovery", "clean"])
@pytest.mark.parametrize("mutation", [
    "wrong_path", "wrong_field", "wrong_value", "wrong_availability",
    "reorder", "missing", "extra", "report_only", "identity_only",
    "simultaneous_valid_domain",
])
def test_every_identity_family_rejects_full_negative_matrix(summary, family, mutation):
    changed = copy.deepcopy(summary)
    result = changed["results_by_profile"][_P]
    if family == "primary":
        report = result["primary_discovery_loss_matrix"]["cells_by_policy"][_POL][_B]
        identity = report["evidence_source"]
        report_field = "discovery_loss"
    elif family == "secondary":
        matrix = result["secondary_metric_matrices"][0]
        report = matrix["values_by_policy"][_POL]
        identity = matrix["source_values_by_policy"][_POL][_B]
        report_field = _B
    elif family == "recovery":
        report = result["recovery_diagnostics_by_policy"][_POL]
        identity = report["source_identity_by_field"]["source_observation_count"]
        report_field = "source_observation_count"
    else:
        report = result["clean_false_positive_stress"][_POL]
        identity = report["source_identity_by_field"]["false_positive_rate_on_clean_cases"]
        report_field = "false_positive_rate_on_clean_cases"
    if mutation == "wrong_path":
        identity["source_path"] = "wrong.path"
    elif mutation == "wrong_field":
        identity["source_field"] = "wrong_field"
    elif mutation == "wrong_value":
        identity["source_value"] = "wrong_value"
    elif mutation == "wrong_availability":
        identity["evidence_availability"] = "wrong_availability"
    elif mutation == "reorder":
        replacement = {key: identity[key] for key in reversed(identity)}
        identity.clear()
        identity.update(replacement)
    elif mutation == "missing":
        identity.pop("source_path")
    elif mutation == "extra":
        identity["unexpected_contract_field"] = None
    elif mutation == "report_only":
        report[report_field] = 0.25
    elif mutation == "identity_only":
        identity["source_value"] = 0.25
    else:
        report[report_field] = 0.25
        identity["source_value"] = 0.25
    _assert_both_serializers_reject(changed)


@pytest.mark.parametrize("replacement", [True, None, "20", float("nan"), float("inf")])
def test_boolean_null_string_nonfinite_coercions_fail_closed(summary, replacement):
    changed = copy.deepcopy(summary)
    changed["dataset_summary"]["buggy_variant_count"] = replacement
    _assert_both_serializers_reject(changed)


@pytest.mark.parametrize("field", [
    "discovered_numerator", "discovery_rate", "discovery_loss",
    "support_variant_ids", "discovered_variant_ids", "missed_variant_ids",
])
def test_primary_numerator_rate_loss_and_partition_drift_fail_closed(summary, field):
    changed = copy.deepcopy(summary)
    cell = changed["results_by_profile"][_P]["primary_discovery_loss_matrix"][
        "cells_by_policy"
    ][_POL][_B]
    if field.endswith("variant_ids"):
        cell[field] = (
            []
            if cell[field]
            else [cell["support_variant_ids"][0]]
        )
    elif field == "discovered_numerator":
        cell[field] = 5
    else:
        cell[field] = 0.125
    _assert_both_serializers_reject(changed)


@pytest.mark.parametrize("field", module._RECOVERY_FIXED_KEYS)
def test_recovery_counts_rates_nulls_and_partitions_fail_closed(summary, field):
    changed = copy.deepcopy(summary)
    row = changed["results_by_profile"][_P]["recovery_diagnostics_by_policy"][_POL]
    row[field] = "invalid"
    _assert_both_serializers_reject(changed)


@pytest.mark.parametrize("field", module._CLEAN_IDENTITY_KEYS)
def test_clean_five_identities_order_availability_and_values_fail_closed(summary, field):
    changed = copy.deepcopy(summary)
    identities = changed["results_by_profile"][_P]["clean_false_positive_stress"][
        _POL
    ]["source_identity_by_field"]
    identities[field]["evidence_availability"] = "wrong_availability"
    _assert_both_serializers_reject(changed)


@pytest.mark.parametrize("profile_id", P1D3B_PROFILE_IDS)
@pytest.mark.parametrize("policy", P1D3B_FORMAL_STRATEGY_IDS)
@pytest.mark.parametrize("field", [
    "reference_average_deltas_by_policy",
    "worst_bucket_loss_deltas_by_policy",
    "g0_worst_bucket_ids_by_policy",
    "profile_worst_bucket_ids_by_policy",
])
def test_all_g0_policy_deltas_and_both_worst_bucket_id_mappings_fail_closed(
    summary, profile_id, policy, field
):
    changed = copy.deepcopy(summary)
    mapping = changed["results_by_profile"][profile_id]["g0_same_policy_comparison"][
        field
    ]
    mapping[policy] = (
        ["boundary_precision"] if field.endswith("ids_by_policy") else 0.25
    )
    _assert_both_serializers_reject(changed)


@pytest.mark.parametrize("profile_id", P1D3B_PROFILE_IDS)
@pytest.mark.parametrize("field", [
    "status", "profile_id", "primary_cell_count", "secondary_matrix_count",
    "recovery_policy_count", "clean_policy_count", "errors",
])
def test_all_profile_validation_rows_fail_closed(summary, profile_id, field):
    changed = copy.deepcopy(summary)
    status = changed["results_by_profile"][profile_id]["profile_validation_status"]
    status[field] = ["unexpected"] if field == "errors" else "invalid"
    _assert_both_serializers_reject(changed)


@pytest.mark.parametrize("profile_id", P1D3B_PROFILE_IDS)
@pytest.mark.parametrize("policy", P1D3B_FORMAL_STRATEGY_IDS)
@pytest.mark.parametrize("family", [
    "recovery_diagnostics_by_policy", "clean_false_positive_stress",
])
def test_recovery_and_clean_conditional_note_position_is_fixed(
    summary, profile_id, policy, family
):
    changed = copy.deepcopy(summary)
    row = changed["results_by_profile"][profile_id][family][policy]
    note_fields = [field for field in ("note", "delayed_evidence_note") if field in row]
    if note_fields:
        note = note_fields[0]
        keys = list(row)
        keys.remove(note)
        keys.insert(0, note)
        changed["results_by_profile"][profile_id][family][policy] = {
            key: row[key] for key in keys
        }
    else:
        row["note"] = "unexpected"
    _assert_both_serializers_reject(changed)


@pytest.mark.parametrize("module_name,constant,replacement", [
    ("p1d2", "P1D2_SCHEMA_VERSION", "drifted"),
    ("p1d2", "P1D2_ANALYSIS_PHASE", "drifted"),
    ("p1d2", "P1D2_GAME_ID", "drifted"),
    ("p1d2", "P1D2_BENCHMARK_ID", "drifted"),
    ("p1d2", "P1D2_CANDIDATE_STRATEGY_ID", "drifted"),
    ("p1d2", "P1D2_FORMAL_STRATEGY_IDS", ()),
    ("p1d2", "P1D2_BUCKET_IDS", ()),
    ("p1d3a", "P1D3A_SCHEMA_VERSION", "drifted"),
    ("p1d3a", "P1D3A_ANALYSIS_PHASE", "drifted"),
    ("p1d3a", "P1D3A_GAME_FAMILY_ID", "drifted"),
    ("p1d3a", "P1D3A_FORMAL_STRATEGY_IDS", ()),
    ("p1d3a", "P1D3A_BUCKET_IDS", ()),
    ("p1d3a", "P1D3A_COST_PROFILE_IDS", ()),
])
def test_current_prior_phase_module_identity_constants_are_preflighted(
    source, monkeypatch, module_name, constant, replacement
):
    prior_module = (
        module.p1d2_evaluation
        if module_name == "p1d2"
        else module.p1d3a_evaluation
    )
    monkeypatch.setattr(prior_module, constant, replacement)
    with pytest.raises(ValueError, match="immutable module contract drifted"):
        build_p1d3b_summary(source)
