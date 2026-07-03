from collections import Counter

from bug_cause_inference.p1b.actions import P1B_ACTIONS
from bug_cause_inference.p1b.dataset import get_variant, load_p1b_variants, validate_p1b_dataset
from bug_cause_inference.p1b.models import P1B_FIX_INTENT_CATEGORIES


def test_p1b_dataset_has_20_buggy_and_5_clean_variants():
    variants = load_p1b_variants()

    assert len(variants) == 25
    assert sum(1 for variant in variants if variant.is_buggy) == 20
    assert sum(1 for variant in variants if not variant.is_buggy) == 5


def test_validate_p1b_dataset_accepts_current_variants():
    validate_p1b_dataset(load_p1b_variants(), action_ids=P1B_ACTIONS)


def test_p1b_buggy_categories_are_balanced():
    variants = [variant for variant in load_p1b_variants() if variant.is_buggy]
    counts = Counter(variant.true_cause_category for variant in variants)

    assert counts == {
        "boundary_condition": 4,
        "missing_null_handling": 4,
        "configuration_environment": 4,
        "state_order_dependence": 4,
        "specification_mismatch": 4,
    }


def test_p1b_fix_intent_categories_are_allowed_labels():
    for variant in load_p1b_variants():
        if variant.is_buggy:
            assert variant.fix_intent_category in P1B_FIX_INTENT_CATEGORIES


def test_p1b_bug_007_expected_items_none_is_empty_cart():
    variant = get_variant("P1B-BUG-007")

    assert variant.expected_behavior == "items=None is treated as an empty cart and returns subtotal 0."
    assert variant.fix_intent_category == "add_missing_value_guard"


def test_p1b_clean_variants_are_false_positive_targets():
    clean_variants = [variant for variant in load_p1b_variants() if not variant.is_buggy]

    assert clean_variants
    assert all(variant.recommended_no_bug_evidence for variant in clean_variants)
