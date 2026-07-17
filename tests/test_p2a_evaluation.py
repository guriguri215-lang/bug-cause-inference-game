from __future__ import annotations

import ast
import inspect
import json
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
from textwrap import dedent

import pytest

from bug_cause_inference.p2a import evaluation, reports
from bug_cause_inference.p2a.adequacy import canonical_digest


@pytest.fixture(scope="module")
def frozen_gate():
    return evaluation.validate_pre_outcome_gate(run_compatibility=False)


@pytest.fixture()
def gate_stub(monkeypatch, frozen_gate):
    calls = []

    def validate(*, run_compatibility=True):
        calls.append(run_compatibility)
        return deepcopy(frozen_gate)

    monkeypatch.setattr(evaluation, "validate_pre_outcome_gate", validate)
    return calls


@pytest.fixture(scope="module")
def synthetic():
    return evaluation.make_synthetic_outcomes()


@pytest.fixture()
def summary(frozen_gate, synthetic, gate_stub):
    legacy, expansion = deepcopy(synthetic)
    result = evaluation.build_versioned_summary(legacy, expansion, gate=frozen_gate)
    assert result["validation_status"]["status"] == "valid"
    assert gate_stub == [False]
    return result


def _assert_invalid(result):
    assert result["validation_status"]["status"] == "invalid_inconclusive"
    assert result["primary_buggy_results_by_cohort"] == {}
    assert result["clean_results_by_cohort"] == {}
    assert result["secondary_metric_results_by_cohort"] == {}
    assert result["sensitivity"] == {}
    assert result["software_acceptance"] == {
        "status": "invalid_inconclusive",
        "accepted": False,
    }
    assert result["limitations"] == []
    assert result["notes"] == []


def _reordered(mapping):
    return {key: mapping[key] for key in reversed(mapping)}


def _gate_mutation_cases():
    cases = [
        "top_missing",
        "top_unknown",
        "top_reordered",
        "status_missing",
        "status_unknown",
        "status_type",
        "authorization_missing",
        "authorization_unknown",
        "authorization_reordered",
        "authorization_source",
        "freeze_timestamp",
        "official_draft_digest",
        "official_freeze_digest",
        "artifact_manifest_digest",
        "contract_missing",
        "contract_unknown",
        "contract_reordered",
        "candidate_manifest_digest",
        "authoring_manifest_digest",
        "trusted_reference_registry_digest",
        "coverage_gap_registry_digest",
        "dataset_missing",
        "dataset_unknown",
        "dataset_reordered",
        "catalog_value",
        "catalog_type",
        "compatibility_missing",
        "compatibility_unknown",
        "compatibility_reordered",
        "compatibility_status",
        "accepted_hash_missing",
        "accepted_hash_unknown",
        "accepted_hash_reordered",
    ]
    authorization = evaluation._canonical_gate_identity()["external_authorization_transition"]
    cases.extend(f"authorization_value:{field}" for field in tuple(authorization)[1:])
    cases.extend(f"authorization_type:{field}" for field in tuple(authorization)[1:])
    contracts = evaluation._canonical_gate_identity()["contract_digests"]
    cases.extend(f"contract_name:{field}" for field in contracts)
    cases.extend(f"contract_value:{field}" for field in contracts)
    cases.extend(f"dataset_value:{field}" for field in ("total", "buggy", "clean"))
    cases.extend(f"dataset_type:{field}" for field in ("total", "buggy", "clean"))
    count_fields = (
        "expected_pair_count",
        "observed_pair_count",
        "matched_pair_count",
        "mismatch_count",
    )
    cases.extend(f"compatibility_value:{field}" for field in count_fields)
    cases.extend(f"compatibility_type:{field}" for field in count_fields)
    cases.extend(
        f"compatibility_digest:{field}"
        for field in ("runtime_digest", "catalog_digest", "artifact_digest")
    )
    hashes = evaluation._canonical_gate_identity()["accepted_four_file_sha256"]
    cases.extend(f"accepted_hash_path:{field}" for field in hashes)
    cases.extend(f"accepted_hash_value:{field}" for field in hashes)
    return cases


GATE_MUTATION_CASES = _gate_mutation_cases()


def _mutate_gate(canonical, case):
    gate = deepcopy(canonical)
    kind, _, field = case.partition(":")
    if kind in {"top_missing", "status_missing"}:
        gate.pop("status")
    elif kind == "top_unknown":
        gate["unknown"] = True
    elif kind == "top_reordered":
        gate = _reordered(gate)
    elif kind == "status_unknown":
        gate["status"] = "valid"
    elif kind == "status_type":
        gate["status"] = False
    elif kind == "authorization_missing":
        gate["external_authorization_transition"].pop("source")
    elif kind == "authorization_unknown":
        gate["external_authorization_transition"]["unknown"] = True
    elif kind == "authorization_reordered":
        gate["external_authorization_transition"] = _reordered(
            gate["external_authorization_transition"]
        )
    elif kind == "authorization_source":
        gate["external_authorization_transition"]["source"] = "untrusted"
    elif kind == "authorization_value":
        gate["external_authorization_transition"][field] = not (
            gate["external_authorization_transition"][field]
        )
    elif kind == "authorization_type":
        gate["external_authorization_transition"][field] = 1
    elif kind in {
        "freeze_timestamp",
        "official_draft_digest",
        "official_freeze_digest",
        "artifact_manifest_digest",
        "candidate_manifest_digest",
        "authoring_manifest_digest",
        "trusted_reference_registry_digest",
        "coverage_gap_registry_digest",
    }:
        gate[kind] = "0" * 64
    elif kind == "contract_missing":
        gate["contract_digests"].pop("adapter")
    elif kind == "contract_unknown":
        gate["contract_digests"]["unknown"] = "0" * 64
    elif kind == "contract_reordered":
        gate["contract_digests"] = _reordered(gate["contract_digests"])
    elif kind == "contract_name":
        gate["contract_digests"] = {
            (f"{key}_mutated" if key == field else key): value
            for key, value in gate["contract_digests"].items()
        }
    elif kind == "contract_value":
        gate["contract_digests"][field] = "f" * 64
    elif kind == "dataset_missing":
        gate["dataset_counts"].pop("total")
    elif kind == "dataset_unknown":
        gate["dataset_counts"]["unknown"] = 0
    elif kind == "dataset_reordered":
        gate["dataset_counts"] = _reordered(gate["dataset_counts"])
    elif kind == "dataset_value":
        gate["dataset_counts"][field] += 1
    elif kind == "dataset_type":
        gate["dataset_counts"][field] = str(gate["dataset_counts"][field])
    elif kind == "catalog_value":
        gate["catalog_case_count"] = 25
    elif kind == "catalog_type":
        gate["catalog_case_count"] = "24"
    elif kind == "compatibility_missing":
        gate["legacy_compatibility"].pop("status")
    elif kind == "compatibility_unknown":
        gate["legacy_compatibility"]["unknown"] = True
    elif kind == "compatibility_reordered":
        gate["legacy_compatibility"] = _reordered(gate["legacy_compatibility"])
    elif kind == "compatibility_status":
        gate["legacy_compatibility"]["status"] = "invalid"
    elif kind == "compatibility_value":
        gate["legacy_compatibility"][field] += 1
    elif kind == "compatibility_type":
        gate["legacy_compatibility"][field] = str(
            gate["legacy_compatibility"][field]
        )
    elif kind == "compatibility_digest":
        gate["legacy_compatibility"][field] = "0" * 64
    elif kind == "accepted_hash_missing":
        gate["accepted_four_file_sha256"].pop(next(iter(gate["accepted_four_file_sha256"])))
    elif kind == "accepted_hash_unknown":
        gate["accepted_four_file_sha256"]["unknown"] = "0" * 64
    elif kind == "accepted_hash_reordered":
        gate["accepted_four_file_sha256"] = _reordered(
            gate["accepted_four_file_sha256"]
        )
    elif kind == "accepted_hash_path":
        gate["accepted_four_file_sha256"] = {
            (f"{key}.mutated" if key == field else key): value
            for key, value in gate["accepted_four_file_sha256"].items()
        }
    elif kind == "accepted_hash_value":
        gate["accepted_four_file_sha256"][field] = "0" * 64
    else:  # pragma: no cover - mutation table is closed above
        raise AssertionError(case)
    return gate


def test_immutable_freeze_and_external_authorization_transition_are_separate(frozen_gate):
    assert tuple(frozen_gate) == evaluation._GATE_FIELDS
    evaluation.validate_canonical_gate_identity(frozen_gate)
    assert frozen_gate["freeze_timestamp"] == "2026-07-17T12:34:56Z"
    assert frozen_gate["dataset_counts"] == {"total": 15, "buggy": 10, "clean": 5}
    assert frozen_gate["catalog_case_count"] == 24
    assert frozen_gate["legacy_compatibility"]["matched_pair_count"] == 150
    transition = frozen_gate["external_authorization_transition"]
    assert transition["p2a_b_implementation_prompt_approved"] is True
    assert transition["bundle_provenance_remains_evaluation_authorized_false"] is True
    assert transition["repository_authorization_artifact_required"] is False


@pytest.mark.parametrize("case", GATE_MUTATION_CASES)
def test_exact_gate_mutation_matrix_fails_closed(
    frozen_gate, synthetic, gate_stub, case
):
    legacy, expansion = deepcopy(synthetic)
    result = evaluation.build_versioned_summary(
        legacy,
        expansion,
        gate=_mutate_gate(frozen_gate, case),
    )
    _assert_invalid(result)
    assert gate_stub == [False]
    json_text = reports.p2a_summary_to_json(result)
    markdown = reports.p2a_summary_to_markdown(result)
    assert json.loads(json_text)["validation_status"]["status"] == "invalid_inconclusive"
    assert "No partial matrix" in markdown


def test_review_125_all_zero_freeze_and_all_f_metric_reproduction_fails_closed(
    frozen_gate, synthetic, gate_stub
):
    gate = deepcopy(frozen_gate)
    gate["official_freeze_digest"] = "0" * 64
    gate["contract_digests"]["metric"] = "f" * 64
    result = evaluation.build_versioned_summary(*deepcopy(synthetic), gate=gate)
    _assert_invalid(result)
    assert "implementation_conformant" not in reports.p2a_summary_to_json(result)
    assert gate_stub == [False]


@pytest.mark.parametrize("mode", ["failure", "different"])
def test_current_immutable_validation_is_mandatory_even_with_canonical_supplied_gate(
    monkeypatch, frozen_gate, synthetic, mode
):
    if mode == "failure":
        def fail(*, run_compatibility=True):
            raise evaluation.P2AEvaluationError("current immutable dependency failed")

        monkeypatch.setattr(evaluation, "validate_pre_outcome_gate", fail)
    else:
        current = deepcopy(frozen_gate)
        current["official_freeze_digest"] = "0" * 64
        monkeypatch.setattr(
            evaluation,
            "validate_pre_outcome_gate",
            lambda **_: deepcopy(current),
        )
    _assert_invalid(
        evaluation.build_versioned_summary(*deepcopy(synthetic), gate=frozen_gate)
    )


def test_four_buggy_and_clean_identities_are_exact_ordered_and_non_aliasing(summary):
    buggy = summary["primary_buggy_results_by_cohort"]
    clean = summary["clean_results_by_cohort"]
    assert tuple(buggy) == evaluation.BUGGY_IDENTITIES
    assert tuple(clean) == evaluation.CLEAN_IDENTITIES
    assert len({id(value) for value in buggy.values()}) == 4
    assert len({id(value) for value in clean.values()}) == 4
    assert buggy["expansion_only_buggy"]["report_role"] == "primary"
    assert buggy["combined_versioned_buggy"]["report_role"] == "descriptive"
    assert clean["expansion_only_clean"]["formal_buggy_game_membership"] == "excluded"


def test_combined_is_replay_plus_expansion_only_and_reference_is_not_an_input(summary):
    buggy = summary["primary_buggy_results_by_cohort"]
    clean = summary["clean_results_by_cohort"]
    assert buggy["combined_versioned_buggy"]["arithmetic_sources"] == [
        "p2a_replayed_legacy_buggy",
        "expansion_only_buggy",
    ]
    assert clean["combined_versioned_clean"]["arithmetic_sources"] == [
        "p2a_replayed_legacy_clean",
        "expansion_only_clean",
    ]
    for bucket in evaluation.BUGGY_BUCKET_IDS:
        assert buggy["combined_versioned_buggy"]["support_by_bucket"][bucket] == (
            buggy["p2a_replayed_legacy_buggy"]["support_by_bucket"][bucket]
            + buggy["expansion_only_buggy"]["support_by_bucket"][bucket]
        )
    assert not any(
        result["accepted_legacy_reference_used_as_arithmetic_input"]
        for result in (*buggy.values(), *clean.values())
    )


def test_accepted_reference_rows_hashes_and_six_policy_tie_are_immutable(summary):
    accepted = summary["primary_buggy_results_by_cohort"]["accepted_legacy_reference_buggy"]
    assert accepted["accepted_reference_identity"]["json_sha256"] == (
        "d1e86525240485b615f61b6261ea239a57b7a7148bdee4a5857452cc84169bac"
    )
    assert accepted["accepted_reference_identity"]["markdown_sha256"] == (
        "9611e6cd8d3086a0b498a89278695f75c07ccdc9f840b6b3d00b14b0234f1dad"
    )
    rows = accepted["restricted_pure_result"]
    assert evaluation._fraction(rows["restricted_pure_security_loss"]) == 1
    assert tuple(rows["restricted_pure_security_policies"]) == evaluation.FORMAL_POLICY_IDS


def test_uniform_bucket_reference_uses_exact_one_fifth_and_rejects_variant_pooling(summary):
    result = summary["primary_buggy_results_by_cohort"]["expansion_only_buggy"]
    distribution = result["reference_distribution"]
    assert distribution["kind"] == "uniform_over_buckets_then_uniform_within_bucket"
    assert distribution["variant_pooled_primary_weighting"] is False
    assert all(evaluation._fraction(weight) == Fraction(1, 5) for weight in distribution["bucket_weights"].values())
    policy = evaluation.FORMAL_POLICY_IDS[0]
    losses = [
        evaluation._fraction(result["cells_by_policy"][policy][bucket]["discovery_loss"])
        for bucket in evaluation.BUGGY_BUCKET_IDS
    ]
    observed = evaluation._fraction(
        result["restricted_pure_result"]["by_policy"][policy]["reference_average_loss"]
    )
    assert observed == sum(losses, Fraction()) / 5


def test_unequal_support_fixture_2_3_4_2_3_differs_from_variant_pooled():
    supports = (2, 3, 4, 2, 3)
    outcomes = []
    for bucket_index, (bucket, count) in enumerate(
        zip(evaluation.BUGGY_BUCKET_IDS, supports, strict=True)
    ):
        for index in range(count):
            for policy in evaluation.FORMAL_POLICY_IDS:
                discovered = index < bucket_index % (count + 1)
                values = (
                    f"U-{bucket_index}-{index}", "unequal", policy, True, bucket, None,
                    discovered, 2 if discovered else 14, discovered, discovered, discovered,
                    False, 4, False, False,
                )
                outcomes.append(dict(zip(evaluation._OUTCOME_FIELDS, values, strict=True)))
    result = evaluation._buggy_result(
        "unequal_support", outcomes, report_role="fixture", arithmetic_sources=["fixture"]
    )
    policy = evaluation.FORMAL_POLICY_IDS[0]
    exact = evaluation._fraction(
        result["restricted_pure_result"]["by_policy"][policy]["reference_average_loss"]
    )
    cells = result["cells_by_policy"][policy]
    pooled = sum(
        evaluation._fraction(cells[bucket]["discovery_loss"]) * supports[index]
        for index, bucket in enumerate(evaluation.BUGGY_BUCKET_IDS)
    ) / sum(supports)
    assert exact != pooled


def test_secondary_metrics_remain_separate_and_use_miss_penalty_14(summary):
    secondary = summary["secondary_metric_results_by_cohort"]["expansion_only_buggy"]
    assert tuple(secondary["metric_ids"]) == evaluation.SECONDARY_METRIC_IDS
    assert secondary["failure_cost_for_missed_first_failure"] == 14
    assert secondary["added_to_discovery_loss"] is False
    assert secondary["used_in_restricted_pure_result"] is False


def _buggy_lovo_inputs(summary):
    results = summary["primary_buggy_results_by_cohort"]
    return (
        results["expansion_only_buggy"]["per_variant_outcomes"],
        results["combined_versioned_buggy"]["per_variant_outcomes"],
        results,
    )


def test_buggy_lovo_never_calls_full_buggy_result(monkeypatch, summary):
    monkeypatch.setattr(
        evaluation,
        "_buggy_result",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("full result called")),
    )
    result = evaluation._buggy_lovo(*_buggy_lovo_inputs(summary))
    assert len(result["projections"]) == 20


def test_buggy_lovo_recomputes_one_bucket_per_projection_and_reuses_four_baseline_cells(
    monkeypatch, summary
):
    original = evaluation._buggy_bucket_cells
    calls = []

    def counted(outcomes, bucket, support):
        calls.append((bucket, tuple(support)))
        return original(outcomes, bucket, support)

    monkeypatch.setattr(evaluation, "_buggy_bucket_cells", counted)
    baselines = _buggy_lovo_inputs(summary)[2]
    before = deepcopy(baselines)
    result = evaluation._buggy_lovo(*_buggy_lovo_inputs(summary))
    assert len(calls) == 20
    assert baselines == before
    for projection in result["projections"]:
        baseline_id = (
            evaluation.BUGGY_IDENTITIES[2]
            if projection["projection_id"] == "expansion_only_buggy_minus_v"
            else evaluation.BUGGY_IDENTITIES[3]
        )
        affected = projection["affected_bucket_id"]
        for policy in evaluation.FORMAL_POLICY_IDS:
            for bucket in evaluation.BUGGY_BUCKET_IDS:
                if bucket != affected:
                    assert projection["five_cells_by_policy"][policy][bucket] == (
                        baselines[baseline_id]["cells_by_policy"][policy][bucket]
                    )


def test_buggy_lovo_uses_intentionally_distinct_unchanged_baseline_cell(summary):
    expansion, combined, baseline_results = _buggy_lovo_inputs(summary)
    baselines = deepcopy(baseline_results)
    policy = evaluation.FORMAL_POLICY_IDS[0]
    sentinel_bucket = evaluation.BUGGY_BUCKET_IDS[1]
    sentinel = baselines[evaluation.BUGGY_IDENTITIES[2]]["cells_by_policy"][policy][sentinel_bucket]
    sentinel["discovery_rate"] = evaluation._fraction_value(Fraction(2, 3))
    sentinel["discovery_loss"] = evaluation._fraction_value(Fraction(1, 3))
    result = evaluation._buggy_lovo(expansion, combined, baselines)
    projection = result["projections"][0]
    assert projection["affected_bucket_id"] != sentinel_bucket
    assert evaluation._fraction(
        projection["five_cells_by_policy"][policy][sentinel_bucket]["discovery_loss"]
    ) == Fraction(1, 3)
    losses = [
        evaluation._fraction(projection["five_cells_by_policy"][policy][bucket]["discovery_loss"])
        for bucket in evaluation.BUGGY_BUCKET_IDS
    ]
    assert evaluation._fraction(
        projection["derived_five_cell_result"]["by_policy"][policy]["reference_average_loss"]
    ) == sum(losses, Fraction()) / 5


def _assert_extrema_record(record, projections, variants, value_getter, delta_getter):
    assert tuple(record) == evaluation._EXTREMA_FIELDS
    values = {item["removed_variant_id"]: value_getter(item) for item in projections}
    deltas = {item["removed_variant_id"]: delta_getter(item) for item in projections}
    minimum_value, maximum_value = min(values.values()), max(values.values())
    minimum_delta, maximum_delta = min(deltas.values()), max(deltas.values())
    assert evaluation._fraction(record["minimum_projected_value"]) == minimum_value
    assert record["minimum_projected_value_variant_ids"] == [
        variant for variant in variants if values[variant] == minimum_value
    ]
    assert evaluation._fraction(record["maximum_projected_value"]) == maximum_value
    assert record["maximum_projected_value_variant_ids"] == [
        variant for variant in variants if values[variant] == maximum_value
    ]
    assert evaluation._fraction(record["minimum_baseline_delta"]) == minimum_delta
    assert record["minimum_baseline_delta_variant_ids"] == [
        variant for variant in variants if deltas[variant] == minimum_delta
    ]
    assert evaluation._fraction(record["maximum_baseline_delta"]) == maximum_delta
    assert record["maximum_baseline_delta_variant_ids"] == [
        variant for variant in variants if deltas[variant] == maximum_delta
    ]


def test_buggy_lovo_complete_exact_value_delta_extrema_and_categorical_outputs(summary):
    lovo = summary["sensitivity"]["buggy_lovo"]
    variants = lovo["target_variant_ids"]
    for projection_id in lovo["projection_ids"]:
        projections = [item for item in lovo["projections"] if item["projection_id"] == projection_id]
        extrema = lovo["extremes"][projection_id]
        for policy in evaluation.FORMAL_POLICY_IDS:
            metrics = extrema["policy_metrics"][policy]
            assert tuple(metrics) == evaluation.BUGGY_LOVO_POLICY_METRIC_IDS
            getters = {
                "affected_cell_discovery_rate": (
                    lambda item: evaluation._fraction(item["affected_cells_by_policy"][policy]["discovery_rate"]),
                    lambda item: evaluation._fraction(item["affected_cell_deltas_by_policy"][policy]["discovery_rate_delta"]),
                ),
                "affected_cell_discovery_loss": (
                    lambda item: evaluation._fraction(item["affected_cells_by_policy"][policy]["discovery_loss"]),
                    lambda item: evaluation._fraction(item["affected_cell_deltas_by_policy"][policy]["discovery_loss_delta"]),
                ),
                "worst_bucket_loss": (
                    lambda item: evaluation._fraction(item["derived_five_cell_result"]["by_policy"][policy]["worst_bucket_loss"]),
                    lambda item: evaluation._fraction(item["derived_baseline_deltas_by_policy"][policy]["worst_bucket_delta"]),
                ),
                "reference_average_loss": (
                    lambda item: evaluation._fraction(item["derived_five_cell_result"]["by_policy"][policy]["reference_average_loss"]),
                    lambda item: evaluation._fraction(item["derived_baseline_deltas_by_policy"][policy]["reference_average_delta"]),
                ),
                "average_to_worst_gap": (
                    lambda item: evaluation._fraction(item["derived_five_cell_result"]["by_policy"][policy]["average_to_worst_gap"]),
                    lambda item: evaluation._fraction(item["derived_baseline_deltas_by_policy"][policy]["average_to_worst_gap_delta"]),
                ),
            }
            for metric, (value_getter, delta_getter) in getters.items():
                _assert_extrema_record(
                    metrics[metric], projections, variants, value_getter, delta_getter
                )
            for item in projections:
                row = item["derived_five_cell_result"]["by_policy"][policy]
                assert type(row["worst_bucket_ids"]) is list and row["worst_bucket_ids"]
        projection_metrics = extrema["projection_metrics"]
        assert tuple(projection_metrics) == evaluation.BUGGY_LOVO_PROJECTION_METRIC_IDS
        _assert_extrema_record(
            projection_metrics["restricted_pure_security_loss"],
            projections,
            variants,
            lambda item: evaluation._fraction(item["derived_five_cell_result"]["restricted_pure_security_loss"]),
            lambda item: evaluation._fraction(item["restricted_pure_security_loss_delta"]),
        )
        for item in projections:
            assert item["derived_five_cell_result"]["restricted_pure_security_policies"]


def test_clean_lovo_all_three_metrics_have_complete_exact_extrema(summary):
    lovo = summary["sensitivity"]["clean_lovo"]
    assert len(lovo["projections"]) == 10
    variants = lovo["target_variant_ids"]
    for projection_id in lovo["projection_ids"]:
        projections = [item for item in lovo["projections"] if item["projection_id"] == projection_id]
        for policy in evaluation.FORMAL_POLICY_IDS:
            metrics = lovo["extremes"][projection_id][policy]
            assert tuple(metrics) == evaluation.CLEAN_LOVO_METRIC_IDS
            for metric in evaluation.CLEAN_LOVO_METRIC_IDS:
                _assert_extrema_record(
                    metrics[metric],
                    projections,
                    variants,
                    lambda item, metric=metric: evaluation._fraction(item["rows_by_policy"][policy][metric]),
                    lambda item, metric=metric: evaluation._fraction(item["rows_by_policy"][policy][f"{metric}_delta"]),
                )


def test_extrema_helper_preserves_all_ties_and_distinct_minimum_maximum():
    variants = ["V3", "V1", "V4", "V2"]
    values = {"V3": Fraction(1), "V1": Fraction(0), "V4": Fraction(2), "V2": Fraction(0)}
    deltas = {"V3": Fraction(0), "V1": Fraction(-1), "V4": Fraction(1), "V2": Fraction(-1)}
    projections = [{"removed_variant_id": variant} for variant in variants]
    record = evaluation._extrema_record(
        projections,
        variants,
        lambda item: values[item["removed_variant_id"]],
        lambda item: deltas[item["removed_variant_id"]],
    )
    assert record["minimum_projected_value_variant_ids"] == ["V1", "V2"]
    assert record["maximum_projected_value_variant_ids"] == ["V4"]
    assert record["minimum_baseline_delta_variant_ids"] == ["V1", "V2"]
    assert record["maximum_baseline_delta_variant_ids"] == ["V4"]


@pytest.mark.parametrize("mutation", ["missing", "unknown", "identity", "nonfinite", "path"])
def test_invalid_or_incomplete_outcome_fails_closed_without_partial_claims(
    frozen_gate, synthetic, gate_stub, mutation
):
    legacy, expansion = deepcopy(synthetic)
    if mutation == "missing":
        expansion.pop()
    elif mutation == "unknown":
        expansion[0]["unknown"] = True
    elif mutation == "identity":
        expansion[0]["variant_id"] = "P2A-BUG-999"
    elif mutation == "nonfinite":
        expansion[0]["investigation_cost"] = float("nan")
    else:
        expansion[0]["taxonomy_id"] = "C:/local/private"
    _assert_invalid(
        evaluation.build_versioned_summary(legacy, expansion, gate=frozen_gate)
    )
    assert gate_stub == [False]


def test_saved_report_source_has_exact_outcome_snapshot_and_combined_equality():
    path = Path(
        "src/bug_cause_inference/p2a/artifacts/evaluation/"
        "p2a_benchmark_evidence_expansion_v1.json"
    )
    source = json.loads(path.read_text(encoding="utf-8"))
    legacy, expansion = evaluation.saved_outcomes_from_report(source)
    snapshot = {
        "source_report_schema_version": source["schema_version"],
        "formal_strategy_ids": list(evaluation.FORMAL_POLICY_IDS),
        "outcome_fields": list(evaluation._OUTCOME_FIELDS),
        "legacy_outcomes": legacy,
        "expansion_outcomes": expansion,
    }
    assert len(legacy) == 150
    assert len(expansion) == 90
    assert (legacy[0]["variant_id"], legacy[0]["policy_id"]) == (
        "P1B-BUG-001", "fixed_checklist"
    )
    assert (legacy[-1]["variant_id"], legacy[-1]["policy_id"]) == (
        "P1B-CLEAN-025", "expected_utility_per_cost"
    )
    assert (expansion[0]["variant_id"], expansion[0]["policy_id"]) == (
        "P2A-BUG-001", "fixed_checklist"
    )
    assert (expansion[-1]["variant_id"], expansion[-1]["policy_id"]) == (
        "P2A-CLEAN-005", "expected_utility_per_cost"
    )
    assert canonical_digest(snapshot) == evaluation.SAVED_OUTCOME_SNAPSHOT_DIGEST


def test_corrective_saved_report_rebuild_ast_and_runtime_never_call_runners(
    monkeypatch, gate_stub
):
    forbidden = {
        "run_versioned_evaluation",
        "_execute_all_outcomes",
        "_run_policy",
        "run_legacy_exact_compatibility",
        "make_synthetic_outcomes",
    }
    for function in (
        evaluation.saved_outcomes_from_report,
        evaluation.rebuild_versioned_summary_from_saved_report,
        evaluation.build_versioned_summary,
    ):
        tree = ast.parse(dedent(inspect.getsource(function)))
        called = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    called.add(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    called.add(node.func.attr)
        assert called.isdisjoint(forbidden)

    source_path = Path(
        "src/bug_cause_inference/p2a/artifacts/evaluation/"
        "p2a_benchmark_evidence_expansion_v1.json"
    )
    source = json.loads(source_path.read_text(encoding="utf-8"))

    def forbidden_call(*args, **kwargs):
        raise AssertionError("outcome/policy/compatibility runner called")

    for name in forbidden:
        monkeypatch.setattr(evaluation, name, forbidden_call)
    rebuilt = evaluation.rebuild_versioned_summary_from_saved_report(source)
    assert rebuilt["validation_status"]["status"] == "valid"
    assert reports.p2a_summary_to_json(rebuilt).endswith("\n")
    assert reports.p2a_summary_to_markdown(rebuilt).endswith("\n")
    assert gate_stub == [False]


def test_summary_contains_no_forbidden_study_expansion_fields(summary):
    forbidden = {
        "combined_profile", "confidence_interval", "bootstrap", "significance",
        "mixed_solution", "nash_solution", "regret",
    }
    stack = [summary]
    keys = set()
    while stack:
        value = stack.pop()
        if isinstance(value, dict):
            keys.update(value)
            stack.extend(value.values())
        elif isinstance(value, list):
            stack.extend(value)
    assert keys.isdisjoint(forbidden)
