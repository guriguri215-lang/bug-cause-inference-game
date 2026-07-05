"""P1c labels for existing P1b variants.

The labels in this module implement the P1c0 specification without adding new
variants or changing P1b dataset metadata.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from typing import Any

from bug_cause_inference.p1b.dataset import load_p1b_variants
from bug_cause_inference.p1b.models import P1BVariant


BUGGY_PRIMARY_BUCKETS = (
    "boundary_precision",
    "missing_optional_input",
    "config_normalization",
    "state_sequence",
    "spec_semantics",
)
PRIMARY_BUCKETS = BUGGY_PRIMARY_BUCKETS + ("clean_false_positive",)


@dataclass(frozen=True)
class P1CVariantLabel:
    variant_id: str
    primary_bucket: str
    existing_difficulty: str
    stress_labels: tuple[str, ...]
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["stress_labels"] = list(self.stress_labels)
        return data


P1C_VARIANT_LABELS: dict[str, P1CVariantLabel] = {
    "P1B-BUG-001": P1CVariantLabel(
        "P1B-BUG-001",
        "boundary_precision",
        "easy",
        ("exact_threshold", "shipping_boundary"),
        "Threshold equality should be caught by boundary tests.",
    ),
    "P1B-BUG-002": P1CVariantLabel(
        "P1B-BUG-002",
        "boundary_precision",
        "easy",
        ("exact_threshold", "coupon_boundary"),
        "Minimum-spend equality should be caught by boundary tests.",
    ),
    "P1B-BUG-003": P1CVariantLabel(
        "P1B-BUG-003",
        "boundary_precision",
        "medium",
        ("upper_boundary", "input_validation"),
        "Upper bound is valid but may look like validation failure.",
    ),
    "P1B-BUG-004": P1CVariantLabel(
        "P1B-BUG-004",
        "boundary_precision",
        "hard",
        ("rounding_precision", "small_numeric_delta"),
        "One-yen rounding errors are easy to miss or mis-rank.",
    ),
    "P1B-BUG-005": P1CVariantLabel(
        "P1B-BUG-005",
        "missing_optional_input",
        "easy",
        ("missing_optional_value", "exception_trace"),
        "Missing coupon produces a direct exception signal.",
    ),
    "P1B-BUG-006": P1CVariantLabel(
        "P1B-BUG-006",
        "missing_optional_input",
        "easy",
        ("missing_payload_key", "default_fallback"),
        "Missing region should fall back to domestic defaults.",
    ),
    "P1B-BUG-007": P1CVariantLabel(
        "P1B-BUG-007",
        "missing_optional_input",
        "medium",
        ("missing_collection", "exception_trace"),
        "items=None resembles an empty-cart edge case.",
    ),
    "P1B-BUG-008": P1CVariantLabel(
        "P1B-BUG-008",
        "missing_optional_input",
        "medium",
        ("missing_record_field", "inventory_only"),
        "Missing reserved is local to inventory data shape.",
    ),
    "P1B-BUG-009": P1CVariantLabel(
        "P1B-BUG-009",
        "config_normalization",
        "medium",
        ("missing_config_default", "stale_default"),
        "Absent tax config falls back to a stale value.",
    ),
    "P1B-BUG-010": P1CVariantLabel(
        "P1B-BUG-010",
        "config_normalization",
        "medium",
        ("missing_feature_flag", "semantic_default"),
        "Conservative feature-flag default is reversed.",
    ),
    "P1B-BUG-011": P1CVariantLabel(
        "P1B-BUG-011",
        "config_normalization",
        "hard",
        ("alias_normalization", "region_edge_case"),
        "Alias handling can be confused with normal region behavior.",
    ),
    "P1B-BUG-012": P1CVariantLabel(
        "P1B-BUG-012",
        "config_normalization",
        "hard",
        ("type_normalization", "exception_trace"),
        "String override causes a type error during comparison.",
    ),
    "P1B-BUG-013": P1CVariantLabel(
        "P1B-BUG-013",
        "state_sequence",
        "easy",
        ("state_reversal", "single_sequence"),
        "Cancel should reverse reservation state.",
    ),
    "P1B-BUG-014": P1CVariantLabel(
        "P1B-BUG-014",
        "state_sequence",
        "medium",
        ("idempotence", "repeated_operation"),
        "Repeated coupon application creates duplicate state.",
    ),
    "P1B-BUG-015": P1CVariantLabel(
        "P1B-BUG-015",
        "state_sequence",
        "hard",
        ("stale_reservation", "coverage_ambiguity"),
        "Cart removal and inventory sync interact across functions.",
    ),
    "P1B-BUG-016": P1CVariantLabel(
        "P1B-BUG-016",
        "state_sequence",
        "hard",
        ("stale_quote", "cross_module_state"),
        "Quote state can become stale across cart, shipping, and discounts.",
    ),
    "P1B-BUG-017": P1CVariantLabel(
        "P1B-BUG-017",
        "spec_semantics",
        "medium",
        ("calculation_order", "tax_discount_order"),
        "Spec says discount before tax.",
    ),
    "P1B-BUG-018": P1CVariantLabel(
        "P1B-BUG-018",
        "spec_semantics",
        "medium",
        ("selection_rule", "bogo_semantics"),
        "BOGO chooses the wrong eligible item.",
    ),
    "P1B-BUG-019": P1CVariantLabel(
        "P1B-BUG-019",
        "spec_semantics",
        "easy",
        ("spec_exception", "digital_only_shipping"),
        "Digital-only carts should bypass shipping.",
    ),
    "P1B-BUG-020": P1CVariantLabel(
        "P1B-BUG-020",
        "spec_semantics",
        "hard",
        ("spec_exception", "state_spec_overlap"),
        "Preorder behavior can look like stock-state failure.",
    ),
    "P1B-CLEAN-021": P1CVariantLabel(
        "P1B-CLEAN-021",
        "clean_false_positive",
        "n/a",
        ("clean_boundary", "recent_diff_distractor"),
        "Boundary and recent-diff signals are present but correct.",
    ),
    "P1B-CLEAN-022": P1CVariantLabel(
        "P1B-CLEAN-022",
        "clean_false_positive",
        "n/a",
        ("clean_null_missing", "near_buggy_area"),
        "Null/missing behavior is correct in a module with buggy neighbors.",
    ),
    "P1B-CLEAN-023": P1CVariantLabel(
        "P1B-CLEAN-023",
        "clean_false_positive",
        "n/a",
        ("clean_config", "documented_behavior_change"),
        "Config differences may look like environment bugs.",
    ),
    "P1B-CLEAN-024": P1CVariantLabel(
        "P1B-CLEAN-024",
        "clean_false_positive",
        "n/a",
        ("clean_state_sequence", "trace_noise"),
        "Multi-step traces are noisy but invariant-preserving.",
    ),
    "P1B-CLEAN-025": P1CVariantLabel(
        "P1B-CLEAN-025",
        "clean_false_positive",
        "n/a",
        ("clean_rounding", "intermediate_numeric_noise"),
        "Intermediate rounding values are confusing but final totals are correct.",
    ),
}


def validate_p1c_variant_labels(variants: list[P1BVariant] | tuple[P1BVariant, ...] | None = None) -> None:
    """Raise ValueError if P1c labels do not exactly cover P1b variants."""

    variants = list(load_p1b_variants() if variants is None else variants)
    variant_ids = {variant.variant_id for variant in variants}
    label_ids = set(P1C_VARIANT_LABELS)
    missing = sorted(variant_ids - label_ids)
    extra = sorted(label_ids - variant_ids)
    errors: list[str] = []
    if missing:
        errors.append(f"missing labels for P1b variants: {missing}")
    if extra:
        errors.append(f"labels without P1b variants: {extra}")

    by_id = {variant.variant_id: variant for variant in variants}
    for variant_id, label in P1C_VARIANT_LABELS.items():
        if label.primary_bucket not in PRIMARY_BUCKETS:
            errors.append(f"{variant_id} has unknown primary_bucket {label.primary_bucket!r}")
        variant = by_id.get(variant_id)
        if variant is None:
            continue
        if variant.is_buggy and label.primary_bucket == "clean_false_positive":
            errors.append(f"{variant_id} is buggy but labeled clean_false_positive")
        if not variant.is_buggy and label.primary_bucket != "clean_false_positive":
            errors.append(f"{variant_id} is clean but labeled {label.primary_bucket!r}")
        if variant.is_buggy and variant.difficulty != label.existing_difficulty:
            errors.append(
                f"{variant_id} difficulty mismatch: P1b={variant.difficulty!r}, "
                f"P1c={label.existing_difficulty!r}"
            )

    if errors:
        raise ValueError("P1c variant label validation failed: " + "; ".join(errors))


def load_p1c_variant_labels(
    variants: list[P1BVariant] | tuple[P1BVariant, ...] | None = None,
) -> dict[str, P1CVariantLabel]:
    validate_p1c_variant_labels(variants)
    return dict(P1C_VARIANT_LABELS)


def p1c_variant_labels_to_dict(
    variants: list[P1BVariant] | tuple[P1BVariant, ...] | None = None,
) -> dict[str, dict[str, Any]]:
    labels = load_p1c_variant_labels(variants)
    return {variant_id: labels[variant_id].to_dict() for variant_id in sorted(labels)}


def bucket_size_summary(
    variants: list[P1BVariant] | tuple[P1BVariant, ...] | None = None,
) -> dict[str, dict[str, Any]]:
    variants = list(load_p1b_variants() if variants is None else variants)
    labels = load_p1c_variant_labels(variants)
    by_id = {variant.variant_id: variant for variant in variants}
    bucket_counts = Counter(label.primary_bucket for label in labels.values())
    summary: dict[str, dict[str, Any]] = {}
    for bucket in PRIMARY_BUCKETS:
        variant_ids = sorted(
            variant_id for variant_id, label in labels.items() if label.primary_bucket == bucket
        )
        summary[bucket] = {
            "variant_count": bucket_counts[bucket],
            "buggy_variants": sum(1 for variant_id in variant_ids if by_id[variant_id].is_buggy),
            "clean_variants": sum(1 for variant_id in variant_ids if not by_id[variant_id].is_buggy),
            "variant_ids": variant_ids,
        }
    return summary
