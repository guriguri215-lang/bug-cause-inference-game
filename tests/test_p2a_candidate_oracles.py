"""Direct deterministic oracle tests; these never run candidate policies."""

from __future__ import annotations

import copy

import pytest

from bug_cause_inference.p2a.candidate_authoring import (
    _baseline_modules,
    _candidate_modules,
    author_candidate,
)
from bug_cause_inference.p2a.candidate_oracles import (
    COMPARISON_SEMANTICS_VERSION,
    ORACLE_DEFINITION_SCHEMA_VERSION,
    ORACLE_DEFINITIONS,
    OracleDefinitionError,
    oracle_definition_digest,
    oracle_definition_payload,
    run_oracle,
    run_oracle_record,
    typed_value,
    validate_oracle_definition_record,
)
from bug_cause_inference.p2a.candidates import BUGGY_CANDIDATES, CLEAN_CANDIDATES


def test_actual_buggy_ground_truth_has_baseline_pass_and_patched_required_fail() -> None:
    results = [author_candidate(candidate) for candidate in BUGGY_CANDIDATES]
    assert len(results) == 10
    assert all(item["baseline_ground_truth_status"] == "all_pass" for item in results)
    assert all(item["candidate_ground_truth_status"] == "required_fail_observed" for item in results)


def test_actual_clean_no_bug_suites_pass_before_and_after_benign_patch() -> None:
    results = [author_candidate(candidate) for candidate in CLEAN_CANDIDATES]
    assert len(results) == 5
    assert all(item["baseline_ground_truth_status"] == "all_pass" for item in results)
    assert all(item["candidate_ground_truth_status"] == "all_pass" for item in results)
    assert all(
        row["baseline_status"] == row["candidate_status"] == "pass"
        for item in results
        for row in item["oracle_statuses"]
    )


def test_all_authored_oracle_ids_have_unique_deterministic_definitions() -> None:
    oracle_ids = [
        oracle_id
        for candidate in (*BUGGY_CANDIDATES, *CLEAN_CANDIDATES)
        for oracle_id in candidate.oracle_ids
    ]
    assert len(oracle_ids) == len(set(oracle_ids))
    assert set(oracle_ids) <= set(ORACLE_DEFINITIONS)
    assert all(ORACLE_DEFINITIONS[item].specification_rule for item in oracle_ids)
    assert all(
        ORACLE_DEFINITIONS[item].record["schema_version"]
        == ORACLE_DEFINITION_SCHEMA_VERSION
        for item in oracle_ids
    )


@pytest.mark.parametrize(
    ("oracle_id", "expected"),
    [
        ("clean.config_present_none_us_raises", "builtins.TypeError"),
        ("clean.config_present_none_jp_raises", "builtins.TypeError"),
        ("clean.config_absent_us_fallback", typed_value(0.0)),
        ("clean.config_absent_jp_fallback", typed_value(0.10)),
        ("clean.config_explicit_zero_rate", typed_value(0.0)),
        ("clean.config_string_rate_equivalence", typed_value(0.07)),
    ],
)
def test_clean_config_membership_reproductions_match_baseline_and_patch(
    oracle_id: str, expected: object
) -> None:
    candidate = CLEAN_CANDIDATES[2]
    with _baseline_modules() as baseline_modules:
        baseline = run_oracle(oracle_id, baseline_modules)
    with _candidate_modules(candidate) as patched_modules:
        patched = run_oracle(oracle_id, patched_modules)
    assert baseline.passed and patched.passed
    assert baseline.actual == patched.actual
    if type(expected) is str:
        assert baseline.actual == expected


def _record(oracle_id: str) -> dict[str, object]:
    return copy.deepcopy(ORACLE_DEFINITIONS[oracle_id].record)


def _digest(record: dict[str, object]) -> str:
    return oracle_definition_digest([record])


def _raw_string(value: str) -> dict[str, object]:
    return {"type": "str", "value": value}


def test_bug005_input_and_expected_joint_mutation_changes_definition_identity_with_same_statuses() -> None:
    original = _record("config.explicit_fractional_tax_rate")
    mutated = copy.deepcopy(original)
    input_mapping = mutated["steps"][0]["positional_args"][0]
    input_mapping["entries"][0]["value"]["entries"][0]["value"]["value"] = "0.08"
    mutated["expectation"]["expected"]["value"] = 0.08
    assert _digest(original) != _digest(mutated)
    candidate = BUGGY_CANDIDATES[4]
    with _baseline_modules() as baseline_modules:
        baseline = run_oracle_record(mutated, baseline_modules)
    with _candidate_modules(candidate) as patched_modules:
        patched = run_oracle_record(mutated, patched_modules)
    assert baseline.passed
    assert not patched.passed


def test_single_execution_semantics_mutations_change_definition_digest() -> None:
    original = _record("config.explicit_fractional_tax_rate")
    mutations = []

    call_target = copy.deepcopy(original)
    call_target["steps"][0]["target"] = "checkout.config.get_region_defaults"
    mutations.append(call_target)

    positional = copy.deepcopy(original)
    positional["steps"][0]["positional_args"][1] = typed_value("JP")
    mutations.append(positional)

    expected = copy.deepcopy(original)
    expected["expectation"]["expected"] = typed_value(0.08)
    mutations.append(expected)

    comparison = copy.deepcopy(original)
    comparison["expectation"]["comparison"]["kind"] = "typed_inequality"
    mutations.append(comparison)

    keyword_original = _record("spec.nonstacking_chooses_larger_discount")
    keyword = copy.deepcopy(keyword_original)
    keyword["steps"][0]["keyword_args"]["member"] = typed_value(False)
    assert _digest(keyword_original) != _digest(keyword)

    exception_original = _record("boundary.quantity_zero_rejected")
    exception = copy.deepcopy(exception_original)
    exception["expectation"]["exception"]["name"] = "TypeError"
    assert _digest(exception_original) != _digest(exception)

    for mutation in mutations:
        assert _digest(original) != _digest(mutation)


def test_composite_step_order_is_strict_and_extraction_semantics_are_bound() -> None:
    original = _record("clean.state_coupon_idempotent")
    reordered = copy.deepcopy(original)
    reordered["steps"][0], reordered["steps"][1] = (
        reordered["steps"][1],
        reordered["steps"][0],
    )
    with pytest.raises(OracleDefinitionError, match="earlier step"):
        validate_oracle_definition_record(reordered)
    extraction = copy.deepcopy(original)
    extraction["steps"][2]["path"] = [typed_value("session")]
    assert _digest(original) != _digest(extraction)


def test_semantically_equal_mapping_insertion_order_has_same_definition_digest() -> None:
    original = _record("spec.nonstacking_chooses_larger_discount")
    reordered = {key: original[key] for key in reversed(original)}
    reordered["steps"][0]["keyword_args"] = {
        key: reordered["steps"][0]["keyword_args"][key]
        for key in reversed(reordered["steps"][0]["keyword_args"])
    }
    assert _digest(original) == _digest(reordered)


def test_typed_value_and_oracle_order_preserve_execution_identity() -> None:
    assert typed_value(0) != typed_value(0.0)
    assert typed_value([1]) != typed_value((1,))
    ids = ["clean.config_absent_us_fallback", "clean.config_explicit_zero_rate"]
    assert oracle_definition_digest(oracle_definition_payload(ids)) != oracle_definition_digest(
        oracle_definition_payload(list(reversed(ids)))
    )


@pytest.mark.parametrize(
    "mutation",
    [
        "unknown_field",
        "missing_field",
        "wrong_type",
        "absolute_path",
        "callable_repr",
    ],
)
def test_oracle_schema_rejects_unknown_missing_wrong_and_nonportable_values(
    mutation: str,
) -> None:
    record = _record("config.explicit_fractional_tax_rate")
    if mutation == "unknown_field":
        record["unknown"] = "x"
    elif mutation == "missing_field":
        del record["invocation_kind"]
    elif mutation == "wrong_type":
        record["steps"] = "call"
    elif mutation == "absolute_path":
        record["steps"][0]["positional_args"][1] = _raw_string("C:/local/input")
    else:
        record["steps"][0]["positional_args"][1] = _raw_string(
            "<function <lambda> at 0x1234>"
        )
    with pytest.raises(OracleDefinitionError):
        validate_oracle_definition_record(record)


@pytest.mark.parametrize(
    "identity",
    [
        "C:/Users/example/input",
        "/home/example/input",
        r"\\server\share\input",
        "file:///C:/Users/example/input",
        "file:///home/example/input",
        "file://server/share/input",
    ],
)
def test_oracle_schema_rejects_absolute_local_identities_in_typed_arguments(
    identity: str,
) -> None:
    record = _record("config.explicit_fractional_tax_rate")
    record["steps"][0]["positional_args"][1] = _raw_string(identity)
    with pytest.raises(OracleDefinitionError, match="absolute local identity"):
        validate_oracle_definition_record(record)


@pytest.mark.parametrize(
    "identity",
    [
        "C:/Users/example/input",
        "/home/example/input",
        r"\\server\share\input",
        "file:///C:/Users/example/input",
        "file:///home/example/input",
        "file://server/share/input",
    ],
)
def test_oracle_schema_rejects_embedded_absolute_local_identity_in_narrative(
    identity: str,
) -> None:
    record = _record("config.explicit_fractional_tax_rate")
    record["specification_rule"] = f"Reviewed input identity {identity} is forbidden."
    with pytest.raises(OracleDefinitionError, match="absolute local identity"):
        validate_oracle_definition_record(record)


@pytest.mark.parametrize(
    "context",
    [
        "keyword_key",
        "keyword_value",
        "nested_mapping_key",
        "nested_mapping_value",
        "list_item",
        "tuple_item",
        "step_id",
        "oracle_id",
        "logical_target",
        "expected_value",
        "expected_exception",
    ],
)
def test_absolute_file_uri_guard_reaches_every_declarative_string_context(
    context: str,
) -> None:
    uri = "file:///C:/Users/example/input"
    if context in {"keyword_key", "keyword_value"}:
        record = _record("spec.nonstacking_chooses_larger_discount")
        keyword_args = record["steps"][0]["keyword_args"]
        if context == "keyword_key":
            value = keyword_args.pop("member")
            keyword_args[uri] = value
        else:
            keyword_args["member"] = _raw_string(uri)
    elif context == "expected_exception":
        record = _record("boundary.quantity_zero_rejected")
        record["expectation"]["exception"]["name"] = uri
    else:
        record = _record("config.explicit_fractional_tax_rate")
        if context == "nested_mapping_key":
            record["steps"][0]["positional_args"][0]["entries"][0]["key"] = (
                _raw_string(uri)
            )
        elif context == "nested_mapping_value":
            record["steps"][0]["positional_args"][0]["entries"][0]["value"] = (
                _raw_string(uri)
            )
        elif context == "list_item":
            record["steps"][0]["positional_args"][1] = {
                "type": "list",
                "items": [_raw_string(uri)],
            }
        elif context == "tuple_item":
            record["steps"][0]["positional_args"][1] = {
                "type": "tuple",
                "items": [_raw_string(uri)],
            }
        elif context == "step_id":
            record["steps"][0]["step_id"] = uri
        elif context == "oracle_id":
            record["oracle_id"] = uri
        elif context == "logical_target":
            record["steps"][0]["target"] = uri
        elif context == "expected_value":
            record["expectation"]["expected"] = _raw_string(uri)
    with pytest.raises(OracleDefinitionError, match="absolute local identity"):
        validate_oracle_definition_record(record)


def test_oracle_schema_accepts_portable_logical_and_relative_string_identities() -> None:
    record = _record("config.explicit_fractional_tax_rate")
    record["specification_rule"] = (
        "Repository-relative checkout/config.py retains the reviewed logical value."
    )
    record["steps"][0]["positional_args"][1] = _raw_string(
        "logical/relative/input"
    )
    validated = validate_oracle_definition_record(record)
    assert validated["oracle_id"] == "config.explicit_fractional_tax_rate"
    assert validated["steps"][0]["target"] == "checkout.config.get_tax_rate"
    assert typed_value("portable/relative/identity") == _raw_string(
        "portable/relative/identity"
    )


def test_clean_none_exception_and_replacement_bug_full_semantics_are_digest_bound() -> None:
    none_record = ORACLE_DEFINITIONS["clean.config_present_none_jp_raises"].record
    assert none_record["expectation"]["kind"] == "exception"
    assert none_record["expectation"]["exception"] == {
        "module": "builtins",
        "name": "TypeError",
    }
    replacement = ORACLE_DEFINITIONS["missing.tax_rates_absent_us_zero"].record
    assert replacement["steps"][0]["target"] == "checkout.config.get_tax_rate"
    assert replacement["steps"][0]["positional_args"] == [
        typed_value({}),
        typed_value("US"),
    ]
    assert replacement["expectation"]["expected"] == typed_value(0.0)
    assert replacement["expectation"]["comparison"] == {
        "kind": "typed_equality",
        "version": COMPARISON_SEMANTICS_VERSION,
    }
