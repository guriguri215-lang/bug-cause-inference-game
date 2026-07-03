"""Fixed P1b injected-bug variant metadata."""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from bug_cause_inference.p1b.models import P1B_CAUSE_CATEGORIES, P1B_FIX_INTENT_CATEGORIES, P1BVariant


LOCATION_CANDIDATES = (
    "cart.add_item",
    "cart.validate_item",
    "cart.cart_subtotal",
    "cart.calculate_tax",
    "cart.calculate_total",
    "cart.checkout_quote",
    "cart.remove_item",
    "cart.item_requires_shipping",
    "discounts.apply_coupon",
    "discounts.coupon_is_eligible",
    "discounts.compute_discount",
    "discounts.apply_bogo_discount",
    "shipping.resolve_region_rate",
    "shipping.free_shipping_eligible",
    "shipping.calculate_shipping",
    "inventory.reserve_stock",
    "inventory.cancel_reservation",
    "inventory.sync_after_cart_update",
    "config.get_tax_rate",
    "config.get_feature_flag",
    "config.load_config",
    "config.get_shipping_threshold",
    "config.get_region_defaults",
    "config.get_region_aliases",
)


def _bug(
    variant_id: str,
    true_cause_category: str,
    target_module: str,
    target_function: str,
    line_span_hint: str,
    bug_summary: str,
    trigger_condition: str,
    failing_input_or_sequence: str,
    expected_behavior: str,
    actual_behavior: str,
    fix_intent_category: str,
    fix_intent_description: str,
    difficulty: str,
    primary_discovery_action: str,
    secondary_discovery_actions: tuple[str, ...],
    observable_signals: str,
    distractor_locations: tuple[str, ...],
) -> P1BVariant:
    if fix_intent_category not in P1B_FIX_INTENT_CATEGORIES:
        raise ValueError(f"Unknown fix-intent category: {fix_intent_category}")
    return P1BVariant(
        variant_id=variant_id,
        is_buggy=True,
        true_cause_category=true_cause_category,
        target_module=target_module,
        target_function=target_function,
        line_span_hint=line_span_hint,
        bug_summary=bug_summary,
        trigger_condition=trigger_condition,
        failing_input_or_sequence=failing_input_or_sequence,
        expected_behavior=expected_behavior,
        actual_behavior=actual_behavior,
        fix_intent_category=fix_intent_category,
        fix_intent_description=fix_intent_description,
        difficulty=difficulty,
        primary_discovery_action=primary_discovery_action,
        secondary_discovery_actions=secondary_discovery_actions,
        observable_signals=observable_signals,
        distractor_locations=distractor_locations,
    )


def _clean(
    variant_id: str,
    covered_spec_area: str,
    expected_clean_behavior: str,
    confusing_signals: str,
    why_false_positive_might_happen: str,
    recommended_no_bug_evidence: str,
) -> P1BVariant:
    return P1BVariant(
        variant_id=variant_id,
        is_buggy=False,
        covered_spec_area=covered_spec_area,
        expected_clean_behavior=expected_clean_behavior,
        confusing_signals=confusing_signals,
        why_false_positive_might_happen=why_false_positive_might_happen,
        recommended_no_bug_evidence=recommended_no_bug_evidence,
    )


P1B_VARIANTS: tuple[P1BVariant, ...] = (
    _bug(
        "P1B-BUG-001",
        "boundary_condition",
        "shipping.py",
        "free_shipping_eligible",
        "shipping.py:L38-L52",
        "Free shipping threshold uses > instead of >=.",
        "Domestic order subtotal is exactly 10000.",
        "Cart subtotal 10000, region domestic, no coupon.",
        "Shipping fee is 0.",
        "Shipping fee is standard domestic fee.",
        "change_comparison",
        "Make the free-shipping threshold inclusive.",
        "easy",
        "run_boundary_tests",
        ("inspect_spec_clause", "inspect_recent_diff", "run_smoke_tests"),
        "Boundary counterexample at exactly 10000.",
        ("config.get_shipping_threshold", "cart.cart_subtotal"),
    ),
    _bug(
        "P1B-BUG-002",
        "boundary_condition",
        "discounts.py",
        "coupon_is_eligible",
        "discounts.py:L44-L61",
        "Coupon minimum-spend rule excludes the exact threshold.",
        "Coupon minimum is exactly met.",
        "Cart subtotal 5000, coupon WELCOME500.",
        "Coupon discount applies.",
        "Coupon is rejected as below minimum spend.",
        "change_comparison",
        "Use inclusive minimum-spend comparison.",
        "easy",
        "run_boundary_tests",
        ("inspect_spec_clause", "inspect_traceback"),
        "Failing test only at subtotal == min_spend.",
        ("cart.cart_subtotal", "config.load_config"),
    ),
    _bug(
        "P1B-BUG-003",
        "boundary_condition",
        "cart.py",
        "add_item",
        "cart.py:L27-L45",
        "Maximum allowed quantity rejects the valid upper boundary.",
        "Quantity is exactly the allowed maximum.",
        "add_item(sku='A100', unit_price=1200, quantity=99).",
        "Quantity 99 is accepted.",
        "Function raises ValueError or rejects the item.",
        "change_comparison",
        "Correct the max-quantity boundary check.",
        "medium",
        "run_boundary_tests",
        ("run_property_search", "inspect_traceback"),
        "Boundary failure at quantity == 99.",
        ("inventory.reserve_stock", "cart.validate_item"),
    ),
    _bug(
        "P1B-BUG-004",
        "boundary_condition",
        "cart.py",
        "calculate_tax",
        "cart.py:L86-L105",
        "Half-up rounding at .5 is implemented as truncation.",
        "Tax calculation produces a .5 fractional yen.",
        "Subtotal 1995, tax rate 0.10, no discounts.",
        "Tax rounds half-up to 200.",
        "Tax truncates to 199.",
        "change_comparison",
        "Apply the specified monetary rounding rule.",
        "hard",
        "run_boundary_tests",
        ("run_property_search", "inspect_spec_clause"),
        "Monetary rounding counterexample.",
        ("config.get_tax_rate", "discounts.compute_discount"),
    ),
    _bug(
        "P1B-BUG-005",
        "missing_null_handling",
        "discounts.py",
        "apply_coupon",
        "discounts.py:L20-L42",
        "coupon_code=None is normalized with .strip() and crashes.",
        "Checkout request has no coupon.",
        "Cart with one item, coupon_code=None.",
        "No coupon discount; checkout continues.",
        "AttributeError on None.strip.",
        "add_missing_value_guard",
        "Treat missing coupon as no-op before string normalization.",
        "easy",
        "run_null_missing_tests",
        ("inspect_traceback", "run_smoke_tests"),
        "Exception trace points to coupon normalization.",
        ("cart.calculate_total", "config.load_config"),
    ),
    _bug(
        "P1B-BUG-006",
        "missing_null_handling",
        "shipping.py",
        "resolve_region_rate",
        "shipping.py:L18-L36",
        "Missing region key raises instead of using default domestic shipping.",
        "Order payload omits region.",
        "Cart subtotal 2500, address has no region.",
        "Domestic rate is used.",
        "KeyError or None lookup failure.",
        "add_missing_value_guard",
        "Add default-region fallback and explicit validation.",
        "easy",
        "run_null_missing_tests",
        ("inspect_traceback", "run_config_matrix_tests"),
        "Missing-key exception or structured missing-key signal.",
        ("config.get_region_defaults", "cart.checkout_quote"),
    ),
    _bug(
        "P1B-BUG-007",
        "missing_null_handling",
        "cart.py",
        "cart_subtotal",
        "cart.py:L50-L66",
        "items=None is iterated as if it were a list.",
        "Caller passes items=None for an empty cart.",
        "cart_subtotal(None).",
        "items=None is treated as an empty cart and returns subtotal 0.",
        "TypeError: 'NoneType' is not iterable.",
        "add_missing_value_guard",
        "Normalize absent item list to an empty cart before iterating.",
        "medium",
        "run_null_missing_tests",
        ("inspect_traceback", "run_smoke_tests"),
        "Traceback in subtotal computation; empty list case passes.",
        ("discounts.compute_discount", "inventory.reserve_stock"),
    ),
    _bug(
        "P1B-BUG-008",
        "missing_null_handling",
        "inventory.py",
        "reserve_stock",
        "inventory.py:L32-L58",
        "Optional reserved field is assumed to exist.",
        "Inventory record lacks reserved.",
        "reserve_stock({'sku': 'A100', 'on_hand': 3}, quantity=1).",
        "Missing reserved is treated as 0.",
        "KeyError: 'reserved'.",
        "add_missing_value_guard",
        "Default missing reservation count to zero.",
        "medium",
        "run_null_missing_tests",
        ("inspect_traceback", "run_state_sequence_tests"),
        "Missing-key traceback; inventory-only failure.",
        ("cart.add_item", "config.load_config"),
    ),
    _bug(
        "P1B-BUG-009",
        "configuration_environment",
        "config.py",
        "get_tax_rate",
        "config.py:L12-L28",
        "JP tax fallback is stale when explicit config is absent.",
        "Runtime config omits tax_rate.jp.",
        "Region JP, subtotal 10000, config missing tax-rate entry.",
        "Tax rate defaults to current JP rate 0.10.",
        "Tax rate falls back to stale 0.08.",
        "fix_config_default",
        "Update or validate the tax-rate fallback.",
        "medium",
        "run_config_matrix_tests",
        ("inspect_recent_diff", "inspect_spec_clause"),
        "Config-matrix failure only when explicit key is missing.",
        ("cart.calculate_tax", "shipping.resolve_region_rate"),
    ),
    _bug(
        "P1B-BUG-010",
        "configuration_environment",
        "config.py",
        "get_feature_flag",
        "config.py:L30-L46",
        "Missing stack_member_and_coupon flag defaults to enabled.",
        "Feature flag is absent from config.",
        "Member customer with coupon; config lacks flag.",
        "Discounts do not stack unless flag is explicitly true.",
        "Member and coupon discounts stack.",
        "fix_config_default",
        "Default missing feature flag to the conservative value.",
        "medium",
        "run_config_matrix_tests",
        ("inspect_spec_clause", "inspect_recent_diff"),
        "Behavior flips under config matrix; no exception.",
        ("discounts.compute_discount", "cart.calculate_total"),
    ),
    _bug(
        "P1B-BUG-011",
        "configuration_environment",
        "shipping.py",
        "resolve_region_rate",
        "shipping.py:L18-L36",
        "Region alias okinawa falls through to domestic rate.",
        "Region alias appears instead of canonical region key.",
        "Region okinawa, subtotal 3000.",
        "Okinawa surcharge applies.",
        "Domestic shipping rate applies.",
        "normalize_config_or_input",
        "Normalize region aliases before rate lookup.",
        "hard",
        "run_config_matrix_tests",
        ("inspect_spec_clause", "run_property_search"),
        "Config counterexample for one region alias.",
        ("config.get_region_aliases", "cart.checkout_quote"),
    ),
    _bug(
        "P1B-BUG-012",
        "configuration_environment",
        "config.py",
        "load_config",
        "config.py:L48-L70",
        "Environment-like free-shipping threshold override is parsed as string.",
        "Threshold override is present in the config fixture.",
        "Config fixture has FREE_SHIPPING_THRESHOLD='9000', subtotal 10000.",
        "Numeric comparison grants free shipping.",
        "FREE_SHIPPING_THRESHOLD remains a string, and comparing it with numeric subtotal raises TypeError.",
        "normalize_config_or_input",
        "Parse and validate numeric config values.",
        "hard",
        "run_config_matrix_tests",
        ("inspect_traceback", "run_boundary_tests"),
        "Config override produces config_counterexample plus exception_trace.",
        ("shipping.free_shipping_eligible", "cart.cart_subtotal"),
    ),
    _bug(
        "P1B-BUG-013",
        "state_order_dependence",
        "inventory.py",
        "cancel_reservation",
        "inventory.py:L60-L82",
        "Cancelling a reservation does not restore stock.",
        "Reserve then cancel the same SKU.",
        "reserve_stock(A100, 2) then cancel_reservation(A100, 2).",
        "on_hand returns to original value.",
        "on_hand remains reduced.",
        "fix_state_transition",
        "Make cancellation reverse the reservation state transition.",
        "easy",
        "run_state_sequence_tests",
        ("inspect_coverage_spectrum", "inspect_recent_diff"),
        "State-sequence counterexample; single-call tests pass.",
        ("cart.remove_item", "inventory.reserve_stock"),
    ),
    _bug(
        "P1B-BUG-014",
        "state_order_dependence",
        "discounts.py",
        "apply_coupon",
        "discounts.py:L20-L42",
        "Applying a coupon twice accumulates duplicate discount state.",
        "Coupon action is repeated before checkout.",
        "apply_coupon(cart, 'WELCOME500') twice, then quote.",
        "Coupon is idempotent; discount applies once.",
        "Discount is applied twice.",
        "make_operation_idempotent",
        "Track applied coupon state or recompute discounts without mutation.",
        "medium",
        "run_state_sequence_tests",
        ("run_property_search", "inspect_spec_clause"),
        "Sequence failure; direct one-shot coupon test passes.",
        ("cart.checkout_quote", "discounts.compute_discount"),
    ),
    _bug(
        "P1B-BUG-015",
        "state_order_dependence",
        "inventory.py",
        "sync_after_cart_update",
        "inventory.py:L84-L108",
        "Removing an item from cart leaves reserved stock stale.",
        "Add item, reserve stock, remove item, then checkout another cart.",
        "add_item(A100, 1), reserve_stock, remove_item(A100), new reservation for A100.",
        "Removed item releases its reservation.",
        "New reservation sees stale reserved count and fails.",
        "fix_state_transition",
        "Synchronize cart removal with inventory reservation release.",
        "hard",
        "run_state_sequence_tests",
        ("inspect_coverage_spectrum", "inspect_recent_diff"),
        "Multi-step state counterexample; suspicious coverage in inventory sync.",
        ("cart.remove_item", "cart.add_item"),
    ),
    _bug(
        "P1B-BUG-016",
        "state_order_dependence",
        "cart.py",
        "checkout_quote",
        "cart.py:L116-L150",
        "Checkout quote caches subtotal before cart mutation and reuses stale state.",
        "Cart is updated between quote preparation and shipping calculation.",
        "Quote cart, add another item, then finalize quote.",
        "Final quote reflects current cart state.",
        "Shipping or discount uses stale subtotal.",
        "recompute_stale_state",
        "Recompute dependent totals after state changes or make quote immutable.",
        "hard",
        "run_state_sequence_tests",
        ("run_property_search", "inspect_coverage_spectrum"),
        "Failure depends on operation order; no exception.",
        ("shipping.calculate_shipping", "discounts.compute_discount"),
    ),
    _bug(
        "P1B-BUG-017",
        "specification_mismatch",
        "cart.py",
        "calculate_total",
        "cart.py:L86-L115",
        "Discount is applied after tax, but spec says discount before tax.",
        "Taxable discounted order.",
        "Subtotal 10000, coupon WELCOME500, tax region JP.",
        "Discount reduces taxable amount before tax.",
        "Tax is computed before discount.",
        "align_calculation_order_with_spec",
        "Reorder discount and tax calculation to match spec.",
        "medium",
        "inspect_spec_clause",
        ("run_smoke_tests", "run_boundary_tests"),
        "Spec-clause mismatch; expected and actual totals differ.",
        ("discounts.compute_discount", "config.get_tax_rate"),
    ),
    _bug(
        "P1B-BUG-018",
        "specification_mismatch",
        "discounts.py",
        "apply_bogo_discount",
        "discounts.py:L88-L118",
        "BOGO discount frees the most expensive item instead of the cheapest eligible item.",
        "BOGO coupon with differently priced eligible items.",
        "Items priced 1000 and 2500, coupon BOGO.",
        "Cheapest eligible item is free.",
        "Most expensive eligible item is free.",
        "align_selection_rule_with_spec",
        "Select the cheapest eligible item as specified.",
        "medium",
        "inspect_spec_clause",
        ("run_property_search", "run_smoke_tests"),
        "Spec mismatch visible in item-level discount trace.",
        ("cart.cart_subtotal", "discounts.coupon_is_eligible"),
    ),
    _bug(
        "P1B-BUG-019",
        "specification_mismatch",
        "shipping.py",
        "calculate_shipping",
        "shipping.py:L54-L82",
        "Digital-only carts are charged shipping when region is present.",
        "Cart contains only digital goods.",
        "Digital item, region domestic, no physical items.",
        "Shipping fee is 0.",
        "Standard shipping fee is charged.",
        "add_spec_exception_rule",
        "Add digital-only shipping exemption before region-rate calculation.",
        "easy",
        "inspect_spec_clause",
        ("run_smoke_tests", "run_config_matrix_tests"),
        "Spec clause says digital-only orders never ship.",
        ("cart.item_requires_shipping", "config.load_config"),
    ),
    _bug(
        "P1B-BUG-020",
        "specification_mismatch",
        "inventory.py",
        "reserve_stock",
        "inventory.py:L32-L58",
        "Preorder SKUs are rejected when stock is zero despite spec allowing backorder.",
        "SKU has preorder=True and on_hand=0.",
        "reserve_stock({'sku': 'PRE1', 'on_hand': 0, 'preorder': True}, 1).",
        "Reservation succeeds as preorder/backorder.",
        "Reservation fails as out of stock.",
        "add_spec_exception_rule",
        "Respect preorder/backorder rule in stock validation.",
        "hard",
        "inspect_spec_clause",
        ("run_state_sequence_tests", "run_config_matrix_tests"),
        "Spec mismatch; state sequence may suggest inventory bug.",
        ("config.get_feature_flag", "cart.add_item"),
    ),
    _clean(
        "P1B-CLEAN-021",
        "Free-shipping and threshold pricing.",
        "Subtotals below, at, and above the free-shipping threshold behave as specified.",
        "Recent changes in shipping.py and boundary tests around threshold code.",
        "A policy may over-weight recent diff or threshold complexity.",
        "Boundary tests pass at 9999, 10000, and 10001; spec and implementation agree.",
    ),
    _clean(
        "P1B-CLEAN-022",
        "Missing coupon and optional coupon fields.",
        "coupon_code=None, empty string, and absent coupon produce no discount and no exception.",
        "Null tests touch discounts.py, where several buggy variants live.",
        "A traceback-free null test may still increase suspicion if the model expects null bugs.",
        "Null/missing tests pass; no exception trace; discount remains zero.",
    ),
    _clean(
        "P1B-CLEAN-023",
        "Conservative default feature flags.",
        "Missing optional discount-stacking flag defaults to no stacking.",
        "Config matrix shows behavior changes when the flag is explicitly enabled.",
        "The behavior difference across configs may look like an environment bug.",
        "Absent flag equals explicit false, and explicit true is documented behavior.",
    ),
    _clean(
        "P1B-CLEAN-024",
        "Inventory reserve/cancel/reserve state sequence.",
        "Reserving, cancelling, and reserving again preserves inventory invariants.",
        "State-sequence tests produce many intermediate observations.",
        "Multi-step traces may look suspicious even when final invariant holds.",
        "Sequence tests pass; invariant log shows on_hand + reserved remains stable.",
    ),
    _clean(
        "P1B-CLEAN-025",
        "Tax, discount, and rounding interaction.",
        "Discount-before-tax and half-up rounding match the specification over representative carts.",
        "Rounding deltas of one yen can appear in intermediate calculations.",
        "Policies may mistake allowed intermediate fractional values for final-output error.",
        "Final totals match golden examples; spec inspection explains intermediate rounding.",
    ),
)


def load_p1b_variants() -> list[P1BVariant]:
    return list(P1B_VARIANTS)


def validate_p1b_dataset(
    variants: list[P1BVariant] | tuple[P1BVariant, ...] | None = None,
    *,
    action_ids: Iterable[str],
) -> None:
    """Raise ValueError if the fixed P1b variant metadata is inconsistent."""

    variants = list(P1B_VARIANTS if variants is None else variants)
    action_id_set = set(action_ids)
    location_set = set(LOCATION_CANDIDATES)
    allowed_difficulties = {"easy", "medium", "hard"}
    errors: list[str] = []

    variant_ids = [variant.variant_id for variant in variants]
    duplicates = sorted(variant_id for variant_id, count in Counter(variant_ids).items() if count > 1)
    if duplicates:
        errors.append(f"Duplicate variant_id values: {duplicates}.")

    buggy_variants = [variant for variant in variants if variant.is_buggy]
    clean_variants = [variant for variant in variants if not variant.is_buggy]
    if len(buggy_variants) != 20:
        errors.append(f"Expected 20 buggy variants, found {len(buggy_variants)}.")
    if len(clean_variants) != 5:
        errors.append(f"Expected 5 clean variants, found {len(clean_variants)}.")

    category_counts = Counter(variant.true_cause_category for variant in buggy_variants)
    for category in P1B_CAUSE_CATEGORIES:
        if category_counts[category] != 4:
            errors.append(f"Expected 4 buggy variants for {category!r}, found {category_counts[category]}.")
    extra_categories = sorted(category for category in category_counts if category not in P1B_CAUSE_CATEGORIES)
    if extra_categories:
        errors.append(f"Unknown buggy cause categories: {extra_categories}.")

    buggy_required = (
        "true_cause_category",
        "target_module",
        "target_function",
        "line_span_hint",
        "bug_summary",
        "trigger_condition",
        "failing_input_or_sequence",
        "expected_behavior",
        "actual_behavior",
        "fix_intent_category",
        "fix_intent_description",
        "difficulty",
        "primary_discovery_action",
        "observable_signals",
    )
    clean_required = (
        "covered_spec_area",
        "expected_clean_behavior",
        "confusing_signals",
        "why_false_positive_might_happen",
        "recommended_no_bug_evidence",
    )

    for variant in buggy_variants:
        missing = [field for field in buggy_required if getattr(variant, field) is None]
        if missing:
            errors.append(f"{variant.variant_id} missing buggy fields: {missing}.")
        if variant.target_location not in location_set:
            errors.append(f"{variant.variant_id} target_location {variant.target_location!r} is not a candidate.")
        unknown_distractors = sorted(set(variant.distractor_locations) - location_set)
        if unknown_distractors:
            errors.append(f"{variant.variant_id} has unknown distractor locations: {unknown_distractors}.")
        if variant.primary_discovery_action not in action_id_set:
            errors.append(
                f"{variant.variant_id} primary_discovery_action {variant.primary_discovery_action!r} is unknown."
            )
        unknown_secondary = sorted(set(variant.secondary_discovery_actions) - action_id_set)
        if unknown_secondary:
            errors.append(f"{variant.variant_id} has unknown secondary discovery actions: {unknown_secondary}.")
        if variant.difficulty not in allowed_difficulties:
            errors.append(f"{variant.variant_id} has invalid difficulty {variant.difficulty!r}.")
        if variant.fix_intent_category not in P1B_FIX_INTENT_CATEGORIES:
            errors.append(f"{variant.variant_id} has invalid fix_intent_category {variant.fix_intent_category!r}.")

    for variant in clean_variants:
        missing = [field for field in clean_required if getattr(variant, field) is None]
        if missing:
            errors.append(f"{variant.variant_id} missing clean fields: {missing}.")

    if errors:
        raise ValueError("P1b dataset validation failed: " + " ".join(errors))


def get_variant(variant_id: str) -> P1BVariant:
    for variant in P1B_VARIANTS:
        if variant.variant_id == variant_id:
            return variant
    raise KeyError(f"Unknown P1b variant: {variant_id}")


def variants_to_json(variants: list[P1BVariant] | tuple[P1BVariant, ...]) -> str:
    return json.dumps([variant.to_dict() for variant in variants], indent=2) + "\n"


def save_variants(path: str | Path, variants: list[P1BVariant] | tuple[P1BVariant, ...] | None = None) -> None:
    Path(path).write_text(variants_to_json(list(variants or P1B_VARIANTS)), encoding="utf-8")


def load_variants_from_file(path: str | Path) -> list[P1BVariant]:
    data: list[dict[str, Any]] = json.loads(Path(path).read_text(encoding="utf-8"))
    return [P1BVariant.from_dict(item) for item in data]
