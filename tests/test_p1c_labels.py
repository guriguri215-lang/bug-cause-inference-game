from bug_cause_inference.p1b.dataset import load_p1b_variants
from bug_cause_inference.p1c.labels import (
    BUGGY_PRIMARY_BUCKETS,
    P1C_VARIANT_LABELS,
    bucket_size_summary,
    validate_p1c_variant_labels,
)


def test_p1c_label_table_covers_all_p1b_variants_exactly():
    variants = load_p1b_variants()

    validate_p1c_variant_labels(variants)

    assert set(P1C_VARIANT_LABELS) == {variant.variant_id for variant in variants}
    assert len(P1C_VARIANT_LABELS) == 25


def test_p1c_bucket_sizes_match_p1c0_specification():
    summary = bucket_size_summary(load_p1b_variants())

    for bucket in BUGGY_PRIMARY_BUCKETS:
        assert summary[bucket]["variant_count"] == 4
        assert summary[bucket]["buggy_variants"] == 4
        assert summary[bucket]["clean_variants"] == 0
    assert summary["clean_false_positive"]["variant_count"] == 5
    assert summary["clean_false_positive"]["buggy_variants"] == 0
    assert summary["clean_false_positive"]["clean_variants"] == 5
