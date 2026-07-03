"""Execution-grounded P1b action harness.

This module deliberately accepts only ``variant_id`` when running checkout
probes. It must not read true cause, target location, or fix-intent metadata;
those labels are reserved for evaluation.
"""

from __future__ import annotations

import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

from bug_cause_inference.p1b.checkout import cart, config, discounts, inventory, shipping
from bug_cause_inference.p1b.dataset import LOCATION_CANDIDATES
from bug_cause_inference.p1b.models import P1BObservation


CHECKOUT_MODULE_PREFIX = "bug_cause_inference.p1b.checkout."
LOCATION_CANDIDATE_SET = set(LOCATION_CANDIDATES)

CAUSE_HINT_BY_TAG = {
    "boundary_failure": "boundary_condition",
    "null_exception": "missing_null_handling",
    "missing_key_exception": "missing_null_handling",
    "config_matrix_failure": "configuration_environment",
    "config_parse_exception": "configuration_environment",
    "state_invariant_failure": "state_order_dependence",
    "idempotency_failure": "state_order_dependence",
    "stale_state_failure": "state_order_dependence",
    "spec_rule_failure": "specification_mismatch",
}

CAUSE_HINT_WEIGHT = 3.0
FIX_INTENT_HINT_WEIGHT = 2.5
FAILING_FUNCTION_WEIGHT = 1.8
STACK_FUNCTION_WEIGHT = 2.2


@dataclass(frozen=True)
class ExecutionTestCase:
    test_id: str
    group: str
    expected: Any
    runner: Callable[[str], Any]
    reproduction_input: str
    evidence_tags: tuple[str, ...]
    fix_intent_hints: tuple[str, ...] = ()


@dataclass
class P1BExecutionContext:
    test_results: list[dict[str, Any]] = field(default_factory=list)

    def record(self, results: list[dict[str, Any]]) -> None:
        self.test_results.extend(results)

    def failed_results(self) -> list[dict[str, Any]]:
        return [result for result in self.test_results if not result["passed"]]


def _unique(items: Iterator[str] | list[str] | tuple[str, ...]) -> list[str]:
    return sorted(set(items))


def _normalize_checkout_function(module_name: str, function_name: str) -> str | None:
    if not module_name.startswith(CHECKOUT_MODULE_PREFIX):
        return None
    short_module = module_name.removeprefix(CHECKOUT_MODULE_PREFIX)
    if not short_module or "." in short_module:
        return None
    candidate = f"{short_module}.{function_name}"
    if candidate not in LOCATION_CANDIDATE_SET:
        return None
    return candidate


@contextmanager
def _checkout_function_trace() -> Iterator[list[str]]:
    calls: list[str] = []
    previous_trace = sys.gettrace()

    def tracer(frame: Any, event: str, arg: Any) -> Any:
        if event == "call":
            function = _normalize_checkout_function(
                frame.f_globals.get("__name__", ""),
                frame.f_code.co_name,
            )
            if function:
                calls.append(function)
        return tracer

    sys.settrace(tracer)
    try:
        yield calls
    finally:
        sys.settrace(previous_trace)


def _stack_functions_from_exception(exc: BaseException) -> list[str]:
    functions: list[str] = []
    traceback = exc.__traceback__
    while traceback is not None:
        frame = traceback.tb_frame
        function = _normalize_checkout_function(frame.f_globals.get("__name__", ""), frame.f_code.co_name)
        if function:
            functions.append(function)
        traceback = traceback.tb_next
    return _unique(functions)


def _run_test_case(test_case: ExecutionTestCase, variant_id: str) -> dict[str, Any]:
    exception_type: str | None = None
    stack_functions: list[str] = []
    with _checkout_function_trace() as calls:
        try:
            actual = test_case.runner(variant_id)
        except Exception as exc:  # noqa: BLE001 - benchmark observation payload
            actual = f"{type(exc).__name__}: {exc}"
            exception_type = type(exc).__name__
            stack_functions = _stack_functions_from_exception(exc)
    passed = exception_type is None and actual == test_case.expected
    return {
        "test_id": test_case.test_id,
        "group": test_case.group,
        "passed": passed,
        "expected": test_case.expected,
        "actual": actual,
        "exception_type": exception_type,
        "reproduction_input": test_case.reproduction_input,
        "executed_functions": _unique(calls),
        "stack_functions": stack_functions,
        "evidence_tags": list(test_case.evidence_tags),
        "fix_intent_hints": list(test_case.fix_intent_hints),
    }


def _actual_smoke_checkout_quote_threshold(variant_id: str) -> dict[str, int]:
    cfg = config.load_config(variant_id=variant_id)
    items = [{"sku": "A100", "unit_price": 10000, "quantity": 1, "requires_shipping": True}]
    return cart.checkout_quote(items, {"region": "domestic"}, cfg, variant_id=variant_id)


def _actual_smoke_missing_coupon_noop(variant_id: str) -> dict[str, Any]:
    return discounts.apply_coupon({}, None, variant_id=variant_id)


def _actual_smoke_digital_shipping(variant_id: str) -> int:
    cfg = config.load_config(variant_id=variant_id)
    items = [{"sku": "D100", "unit_price": 1200, "quantity": 1, "requires_shipping": False}]
    return shipping.calculate_shipping(items, 1200, {"region": "domestic"}, cfg, variant_id=variant_id)


def _actual_smoke_preorder_reserve(variant_id: str) -> int:
    record = inventory.reserve_stock(
        {"sku": "PRE1", "on_hand": 0, "reserved": 0, "preorder": True},
        1,
        variant_id=variant_id,
    )
    return int(record["reserved"])


def _actual_free_shipping_exact_threshold(variant_id: str) -> bool:
    cfg = config.load_config(variant_id=variant_id)
    return shipping.free_shipping_eligible(10000, cfg, variant_id=variant_id)


def _actual_coupon_exact_minimum(variant_id: str) -> bool:
    return discounts.coupon_is_eligible(5000, "WELCOME500", variant_id=variant_id)


def _actual_quantity_upper_boundary(variant_id: str) -> int:
    items = cart.add_item([], "A100", 1200, 99, variant_id=variant_id)
    return int(items[0]["quantity"])


def _actual_tax_half_up_rounding(variant_id: str) -> int:
    return cart.calculate_tax(1995, 0.10, variant_id=variant_id)


def _actual_coupon_none_noop(variant_id: str) -> dict[str, Any]:
    return discounts.apply_coupon({}, None, variant_id=variant_id)


def _actual_missing_region_default(variant_id: str) -> int:
    cfg = config.load_config(variant_id=variant_id)
    return shipping.resolve_region_rate({}, cfg, variant_id=variant_id)


def _actual_none_cart_subtotal(variant_id: str) -> int:
    return cart.cart_subtotal(None, variant_id=variant_id)


def _actual_missing_reserved_defaults_zero(variant_id: str) -> int:
    record = inventory.reserve_stock({"sku": "A100", "on_hand": 3}, 1, variant_id=variant_id)
    return int(record["reserved"])


def _actual_missing_jp_tax_default(variant_id: str) -> float:
    cfg = config.load_config({"tax_rates": {"US": 0.07}}, variant_id=variant_id)
    return config.get_tax_rate(cfg, "JP", variant_id=variant_id)


def _actual_missing_feature_flag_no_stacking(variant_id: str) -> int:
    cfg = config.load_config({"feature_flags": {}}, variant_id=variant_id)
    return discounts.compute_discount(6000, "WELCOME500", member=True, config=cfg, variant_id=variant_id)


def _actual_region_alias_rate(variant_id: str) -> int:
    cfg = config.load_config(variant_id=variant_id)
    return shipping.resolve_region_rate({"region": "jp-okinawa"}, cfg, variant_id=variant_id)


def _actual_free_shipping_threshold_override(variant_id: str) -> bool:
    cfg = config.load_config({"FREE_SHIPPING_THRESHOLD": "9000"}, variant_id=variant_id)
    return shipping.free_shipping_eligible(10000, cfg, variant_id=variant_id)


def _actual_reserve_then_cancel(variant_id: str) -> int:
    record = {"sku": "A100", "on_hand": 5, "reserved": 0}
    reserved = inventory.reserve_stock(record, 2, variant_id=variant_id)
    cancelled = inventory.cancel_reservation(reserved, 2, variant_id=variant_id)
    return int(cancelled.get("reserved", 0))


def _actual_double_coupon_idempotency(variant_id: str) -> list[str]:
    state: dict[str, Any] = {}
    state = discounts.apply_coupon(state, "WELCOME500", variant_id=variant_id)
    state = discounts.apply_coupon(state, "WELCOME500", variant_id=variant_id)
    return list(state.get("applied_coupons", []))


def _actual_removed_item_releases_reservation(variant_id: str) -> int:
    record = {"sku": "A100", "on_hand": 1, "reserved": 1}
    synced = inventory.sync_after_cart_update(record, 1, variant_id=variant_id)
    return int(synced.get("reserved", 0))


def _actual_quote_after_cart_mutation(variant_id: str) -> dict[str, int]:
    cfg = config.load_config(variant_id=variant_id)
    items = [
        {"sku": "A100", "unit_price": 6000, "quantity": 1, "requires_shipping": True},
        {"sku": "B200", "unit_price": 5000, "quantity": 1, "requires_shipping": True},
    ]
    return cart.checkout_quote(items, {"region": "domestic"}, cfg, variant_id=variant_id)


def _actual_free_shipping_boundary_vector(variant_id: str) -> list[bool]:
    cfg = config.load_config(variant_id=variant_id)
    return [
        shipping.free_shipping_eligible(subtotal, cfg, variant_id=variant_id)
        for subtotal in (9999, 10000, 10001)
    ]


def _actual_discount_before_tax_total(variant_id: str) -> int:
    cfg = config.load_config(variant_id=variant_id)
    items = [{"sku": "A100", "unit_price": 10000, "quantity": 1, "requires_shipping": True}]
    return cart.calculate_total(items, "WELCOME500", member=False, region="JP", config=cfg, variant_id=variant_id)


def _actual_bogo_cheapest_rule(variant_id: str) -> int:
    items = [
        {"sku": "A100", "unit_price": 1000, "quantity": 1, "bogo_eligible": True},
        {"sku": "B200", "unit_price": 2500, "quantity": 1, "bogo_eligible": True},
    ]
    return discounts.apply_bogo_discount(items, variant_id=variant_id)


def _actual_digital_only_shipping_rule(variant_id: str) -> int:
    cfg = config.load_config(variant_id=variant_id)
    items = [{"sku": "D100", "unit_price": 1500, "quantity": 1, "requires_shipping": False}]
    return shipping.calculate_shipping(items, 1500, {"region": "domestic"}, cfg, variant_id=variant_id)


def _actual_preorder_reservation_rule(variant_id: str) -> int:
    record = inventory.reserve_stock(
        {"sku": "PRE1", "on_hand": 0, "reserved": 0, "preorder": True},
        1,
        variant_id=variant_id,
    )
    return int(record["reserved"])


TEST_CASES: dict[str, ExecutionTestCase] = {
    "smoke.checkout_quote_threshold": ExecutionTestCase(
        "smoke.checkout_quote_threshold",
        "smoke",
        {"subtotal": 10000, "shipping": 0, "total": 10000},
        _actual_smoke_checkout_quote_threshold,
        "checkout_quote one physical item at subtotal 10000, domestic address.",
        ("boundary_failure", "spec_rule_failure"),
        ("change_comparison",),
    ),
    "smoke.missing_coupon_noop": ExecutionTestCase(
        "smoke.missing_coupon_noop",
        "smoke",
        {},
        _actual_smoke_missing_coupon_noop,
        "apply_coupon({}, None).",
        ("null_exception",),
        ("add_missing_value_guard",),
    ),
    "smoke.digital_shipping": ExecutionTestCase(
        "smoke.digital_shipping",
        "smoke",
        0,
        _actual_smoke_digital_shipping,
        "calculate_shipping for a digital-only domestic cart.",
        ("spec_rule_failure",),
        ("add_spec_exception_rule",),
    ),
    "smoke.preorder_reserve": ExecutionTestCase(
        "smoke.preorder_reserve",
        "smoke",
        1,
        _actual_smoke_preorder_reserve,
        "reserve_stock preorder SKU with zero on-hand stock.",
        ("spec_rule_failure", "state_invariant_failure"),
        ("add_spec_exception_rule",),
    ),
    "boundary.free_shipping_exact_threshold": ExecutionTestCase(
        "boundary.free_shipping_exact_threshold",
        "boundary",
        True,
        _actual_free_shipping_exact_threshold,
        "free_shipping_eligible subtotal=10000.",
        ("boundary_failure",),
        ("change_comparison",),
    ),
    "boundary.coupon_exact_minimum": ExecutionTestCase(
        "boundary.coupon_exact_minimum",
        "boundary",
        True,
        _actual_coupon_exact_minimum,
        "coupon_is_eligible subtotal=5000, coupon WELCOME500.",
        ("boundary_failure",),
        ("change_comparison",),
    ),
    "boundary.quantity_upper_boundary": ExecutionTestCase(
        "boundary.quantity_upper_boundary",
        "boundary",
        99,
        _actual_quantity_upper_boundary,
        "add_item quantity=99.",
        ("boundary_failure",),
        ("change_comparison",),
    ),
    "boundary.tax_half_up_rounding": ExecutionTestCase(
        "boundary.tax_half_up_rounding",
        "boundary",
        200,
        _actual_tax_half_up_rounding,
        "calculate_tax amount=1995, tax_rate=0.10.",
        ("boundary_failure",),
        ("change_comparison",),
    ),
    "null_missing.coupon_none_noop": ExecutionTestCase(
        "null_missing.coupon_none_noop",
        "null_missing",
        {},
        _actual_coupon_none_noop,
        "apply_coupon({}, None).",
        ("null_exception",),
        ("add_missing_value_guard",),
    ),
    "null_missing.missing_region_default": ExecutionTestCase(
        "null_missing.missing_region_default",
        "null_missing",
        800,
        _actual_missing_region_default,
        "resolve_region_rate with an address missing region.",
        ("missing_key_exception",),
        ("add_missing_value_guard",),
    ),
    "null_missing.none_cart_subtotal": ExecutionTestCase(
        "null_missing.none_cart_subtotal",
        "null_missing",
        0,
        _actual_none_cart_subtotal,
        "cart_subtotal(None).",
        ("null_exception",),
        ("add_missing_value_guard",),
    ),
    "null_missing.missing_reserved_defaults_zero": ExecutionTestCase(
        "null_missing.missing_reserved_defaults_zero",
        "null_missing",
        1,
        _actual_missing_reserved_defaults_zero,
        "reserve_stock({'sku': 'A100', 'on_hand': 3}, 1).",
        ("missing_key_exception",),
        ("add_missing_value_guard",),
    ),
    "config.missing_jp_tax_default": ExecutionTestCase(
        "config.missing_jp_tax_default",
        "config_matrix",
        0.10,
        _actual_missing_jp_tax_default,
        "get_tax_rate for JP when tax_rates omits JP.",
        ("config_matrix_failure",),
        ("fix_config_default",),
    ),
    "config.missing_feature_flag_no_stacking": ExecutionTestCase(
        "config.missing_feature_flag_no_stacking",
        "config_matrix",
        500,
        _actual_missing_feature_flag_no_stacking,
        "compute_discount with missing stack_member_and_coupon flag.",
        ("config_matrix_failure",),
        ("fix_config_default",),
    ),
    "config.region_alias_rate": ExecutionTestCase(
        "config.region_alias_rate",
        "config_matrix",
        1600,
        _actual_region_alias_rate,
        "resolve_region_rate with jp-okinawa alias.",
        ("config_matrix_failure",),
        ("normalize_config_or_input",),
    ),
    "config.free_shipping_threshold_override": ExecutionTestCase(
        "config.free_shipping_threshold_override",
        "config_matrix",
        True,
        _actual_free_shipping_threshold_override,
        "load_config FREE_SHIPPING_THRESHOLD='9000' then compare subtotal 10000.",
        ("config_parse_exception",),
        ("normalize_config_or_input",),
    ),
    "state.reserve_then_cancel": ExecutionTestCase(
        "state.reserve_then_cancel",
        "state_sequence",
        0,
        _actual_reserve_then_cancel,
        "reserve_stock(A100, 2) then cancel_reservation(A100, 2).",
        ("state_invariant_failure",),
        ("fix_state_transition",),
    ),
    "state.double_coupon_idempotency": ExecutionTestCase(
        "state.double_coupon_idempotency",
        "state_sequence",
        ["WELCOME500"],
        _actual_double_coupon_idempotency,
        "apply_coupon({}, 'WELCOME500') twice.",
        ("idempotency_failure",),
        ("make_operation_idempotent",),
    ),
    "state.removed_item_releases_reservation": ExecutionTestCase(
        "state.removed_item_releases_reservation",
        "state_sequence",
        0,
        _actual_removed_item_releases_reservation,
        "sync_after_cart_update({'reserved': 1}, removed_quantity=1).",
        ("state_invariant_failure",),
        ("fix_state_transition",),
    ),
    "state.quote_after_cart_mutation": ExecutionTestCase(
        "state.quote_after_cart_mutation",
        "state_sequence",
        {"subtotal": 11000, "shipping": 0, "total": 11000},
        _actual_quote_after_cart_mutation,
        "checkout_quote two physical items totaling 11000.",
        ("stale_state_failure",),
        ("recompute_stale_state",),
    ),
    "property.free_shipping_boundary_vector": ExecutionTestCase(
        "property.free_shipping_boundary_vector",
        "property",
        [False, True, True],
        _actual_free_shipping_boundary_vector,
        "free_shipping_eligible for subtotals 9999, 10000, 10001.",
        ("boundary_failure",),
        ("change_comparison",),
    ),
    "property.coupon_idempotency": ExecutionTestCase(
        "property.coupon_idempotency",
        "property",
        ["WELCOME500"],
        _actual_double_coupon_idempotency,
        "apply_coupon({}, 'WELCOME500') twice.",
        ("idempotency_failure",),
        ("make_operation_idempotent",),
    ),
    "property.total_consistency": ExecutionTestCase(
        "property.total_consistency",
        "property",
        10450,
        _actual_discount_before_tax_total,
        "calculate_total subtotal=10000, coupon WELCOME500, region JP.",
        ("spec_rule_failure",),
        ("align_calculation_order_with_spec",),
    ),
    "property.bogo_cheapest_rule": ExecutionTestCase(
        "property.bogo_cheapest_rule",
        "property",
        1000,
        _actual_bogo_cheapest_rule,
        "apply_bogo_discount on prices 1000 and 2500.",
        ("spec_rule_failure",),
        ("align_selection_rule_with_spec",),
    ),
    "property.preorder_reservation": ExecutionTestCase(
        "property.preorder_reservation",
        "property",
        1,
        _actual_preorder_reservation_rule,
        "reserve_stock preorder SKU with zero on-hand stock.",
        ("spec_rule_failure", "state_invariant_failure"),
        ("add_spec_exception_rule",),
    ),
    "spec.discount_before_tax": ExecutionTestCase(
        "spec.discount_before_tax",
        "spec_clause",
        10450,
        _actual_discount_before_tax_total,
        "calculate_total subtotal=10000, coupon WELCOME500, region JP.",
        ("spec_rule_failure",),
        ("align_calculation_order_with_spec",),
    ),
    "spec.bogo_cheapest_rule": ExecutionTestCase(
        "spec.bogo_cheapest_rule",
        "spec_clause",
        1000,
        _actual_bogo_cheapest_rule,
        "apply_bogo_discount on prices 1000 and 2500.",
        ("spec_rule_failure",),
        ("align_selection_rule_with_spec",),
    ),
    "spec.digital_only_shipping": ExecutionTestCase(
        "spec.digital_only_shipping",
        "spec_clause",
        0,
        _actual_digital_only_shipping_rule,
        "calculate_shipping for a digital-only domestic cart.",
        ("spec_rule_failure",),
        ("add_spec_exception_rule",),
    ),
    "spec.preorder_reservation": ExecutionTestCase(
        "spec.preorder_reservation",
        "spec_clause",
        1,
        _actual_preorder_reservation_rule,
        "reserve_stock preorder SKU with zero on-hand stock.",
        ("spec_rule_failure", "state_invariant_failure"),
        ("add_spec_exception_rule",),
    ),
}


ACTION_TEST_CASE_IDS: dict[str, tuple[str, ...]] = {
    "run_smoke_tests": (
        "smoke.checkout_quote_threshold",
        "smoke.missing_coupon_noop",
        "smoke.digital_shipping",
        "smoke.preorder_reserve",
    ),
    "run_boundary_tests": (
        "boundary.free_shipping_exact_threshold",
        "boundary.coupon_exact_minimum",
        "boundary.quantity_upper_boundary",
        "boundary.tax_half_up_rounding",
    ),
    "run_null_missing_tests": (
        "null_missing.coupon_none_noop",
        "null_missing.missing_region_default",
        "null_missing.none_cart_subtotal",
        "null_missing.missing_reserved_defaults_zero",
    ),
    "run_config_matrix_tests": (
        "config.missing_jp_tax_default",
        "config.missing_feature_flag_no_stacking",
        "config.region_alias_rate",
        "config.free_shipping_threshold_override",
    ),
    "run_state_sequence_tests": (
        "state.reserve_then_cancel",
        "state.double_coupon_idempotency",
        "state.removed_item_releases_reservation",
        "state.quote_after_cart_mutation",
    ),
    "run_property_search": (
        "property.free_shipping_boundary_vector",
        "property.coupon_idempotency",
        "property.total_consistency",
        "property.bogo_cheapest_rule",
        "property.preorder_reservation",
    ),
    "inspect_spec_clause": (
        "spec.discount_before_tax",
        "spec.bogo_cheapest_rule",
        "spec.digital_only_shipping",
        "spec.preorder_reservation",
    ),
}

TRACEBACK_PROBE_IDS = (
    "null_missing.coupon_none_noop",
    "null_missing.missing_region_default",
    "null_missing.none_cart_subtotal",
    "null_missing.missing_reserved_defaults_zero",
    "config.free_shipping_threshold_override",
)


def _test_results_for_action(action_id: str, variant_id: str) -> list[dict[str, Any]]:
    case_ids = ACTION_TEST_CASE_IDS[action_id]
    return [_run_test_case(TEST_CASES[test_id], variant_id) for test_id in case_ids]


def _aggregate_functions(results: list[dict[str, Any]], *, passed: bool | None = None) -> list[str]:
    filtered = results if passed is None else [result for result in results if result["passed"] is passed]
    return _unique(function for result in filtered for function in result["executed_functions"])


def _aggregate_stack_functions(results: list[dict[str, Any]]) -> list[str]:
    return _unique(function for result in results for function in result.get("stack_functions", []))


def _score_maps_from_results(
    results: list[dict[str, Any]],
) -> tuple[dict[str, float], dict[str, float], dict[str, float]]:
    cause_scores: dict[str, float] = {}
    location_scores: dict[str, float] = {}
    fix_intent_scores: dict[str, float] = {}
    failed_results = [result for result in results if not result["passed"]]
    for result in failed_results:
        for tag in result["evidence_tags"]:
            cause = CAUSE_HINT_BY_TAG.get(tag)
            if cause:
                cause_scores[cause] = max(cause_scores.get(cause, 1.0), CAUSE_HINT_WEIGHT)
        for hint in result["fix_intent_hints"]:
            fix_intent_scores[hint] = max(fix_intent_scores.get(hint, 1.0), FIX_INTENT_HINT_WEIGHT)
        for function in result["executed_functions"]:
            location_scores[function] = max(location_scores.get(function, 1.0), FAILING_FUNCTION_WEIGHT)
        for function in result.get("stack_functions", []):
            location_scores[function] = max(location_scores.get(function, 1.0), STACK_FUNCTION_WEIGHT)
    return cause_scores, location_scores, fix_intent_scores


def _coverage_suspicion_from_results(results: list[dict[str, Any]]) -> dict[str, float]:
    # B1 keeps this intentionally simple; Ochiai-style ranking belongs to B2.
    failed_results = [result for result in results if not result["passed"]]
    if not failed_results:
        return {}
    failing_functions = _aggregate_functions(failed_results)
    return {function: 1.0 for function in failing_functions}


def _observation_from_results(
    *,
    action_id: str,
    cost: int,
    observation_type: str,
    results: list[dict[str, Any]],
    recordable: bool = True,
) -> P1BObservation:
    failed_results = [result for result in results if not result["passed"]]
    passed_results = [result for result in results if result["passed"]]
    failed_test_ids = [result["test_id"] for result in failed_results]
    passed_test_ids = [result["test_id"] for result in passed_results]
    first_failure = failed_results[0] if failed_results else None
    first_exception = next((result for result in failed_results if result["exception_type"]), None)
    cause_scores, location_scores, fix_intent_scores = _score_maps_from_results(results)
    stack_functions = _aggregate_stack_functions(failed_results)
    if first_failure:
        summary = (
            f"{action_id} failed {len(failed_results)}/{len(results)} execution-grounded tests; "
            f"first failure {first_failure['test_id']} expected {first_failure['expected']!r} "
            f"and observed {first_failure['actual']!r}."
        )
    else:
        summary = f"{action_id} passed all {len(results)} execution-grounded tests."
    return P1BObservation(
        action_id=action_id,
        cost=cost,
        observation_type="exception_trace" if first_exception else observation_type,
        summary=summary,
        bug_detected=bool(failed_results),
        failure_found=bool(failed_results) and recordable,
        no_bug_evidence=not failed_results,
        reproduction_input=first_failure["reproduction_input"] if first_failure else None,
        exception_type=first_exception["exception_type"] if first_exception else None,
        cause_scores=cause_scores,
        location_scores=location_scores,
        fix_intent_scores=fix_intent_scores,
        evidence_source="execution_grounded",
        test_results=results,
        failed_test_ids=failed_test_ids,
        passed_test_ids=passed_test_ids,
        executed_functions=_aggregate_functions(results),
        failing_executed_functions=_aggregate_functions(results, passed=False),
        passing_executed_functions=_aggregate_functions(results, passed=True),
        stack_functions=stack_functions,
        coverage_suspicion=_coverage_suspicion_from_results(results),
    )


def _inspect_traceback(
    *,
    variant_id: str,
    action_id: str,
    cost: int,
    observation_type: str,
    context: P1BExecutionContext,
) -> P1BObservation:
    cached_failures = context.failed_results()
    if cached_failures:
        return _observation_from_results(
            action_id=action_id,
            cost=cost,
            observation_type=observation_type,
            results=cached_failures,
            recordable=False,
        )
    results = [_run_test_case(TEST_CASES[test_id], variant_id) for test_id in TRACEBACK_PROBE_IDS]
    context.record(results)
    return _observation_from_results(
        action_id=action_id,
        cost=cost,
        observation_type=observation_type,
        results=results,
    )


def _inspect_coverage_spectrum(
    *,
    action_id: str,
    cost: int,
    observation_type: str,
    context: P1BExecutionContext,
) -> P1BObservation:
    results = list(context.test_results)
    failed_results = [result for result in results if not result["passed"]]
    coverage_suspicion = _coverage_suspicion_from_results(results)
    location_scores = {function: 1.2 for function in coverage_suspicion}
    if failed_results:
        summary = (
            f"{action_id} summarized {len(failed_results)} cached failing execution tests. "
            "B1 stores the spectrum footing; Ochiai ranking is deferred to B2."
        )
    else:
        summary = (
            f"{action_id} found no cached failing execution tests. "
            "B1 coverage ranking is intentionally minimal until B2."
        )
    return P1BObservation(
        action_id=action_id,
        cost=cost,
        observation_type=observation_type,
        summary=summary,
        bug_detected=bool(failed_results),
        failure_found=False,
        no_bug_evidence=not failed_results,
        location_scores=location_scores,
        evidence_source="execution_grounded",
        test_results=results,
        failed_test_ids=[result["test_id"] for result in failed_results],
        passed_test_ids=[result["test_id"] for result in results if result["passed"]],
        executed_functions=_aggregate_functions(results),
        failing_executed_functions=_aggregate_functions(results, passed=False),
        passing_executed_functions=_aggregate_functions(results, passed=True),
        stack_functions=_aggregate_stack_functions(failed_results),
        coverage_suspicion=coverage_suspicion,
    )


def run_execution_grounded_action(
    *,
    variant_id: str,
    action_id: str,
    cost: int,
    observation_type: str,
    context: P1BExecutionContext | None = None,
) -> P1BObservation:
    context = context or P1BExecutionContext()
    if action_id == "inspect_traceback":
        return _inspect_traceback(
            variant_id=variant_id,
            action_id=action_id,
            cost=cost,
            observation_type=observation_type,
            context=context,
        )
    if action_id == "inspect_coverage_spectrum":
        return _inspect_coverage_spectrum(
            action_id=action_id,
            cost=cost,
            observation_type=observation_type,
            context=context,
        )
    if action_id not in ACTION_TEST_CASE_IDS:
        raise ValueError(f"Action {action_id!r} has no execution-grounded test registry.")
    results = _test_results_for_action(action_id, variant_id)
    context.record(results)
    return _observation_from_results(
        action_id=action_id,
        cost=cost,
        observation_type=observation_type,
        results=results,
    )
