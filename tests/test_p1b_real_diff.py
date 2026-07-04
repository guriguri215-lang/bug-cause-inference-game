from __future__ import annotations

from typing import Any

from bug_cause_inference.p1b.dataset import load_p1b_variants
from bug_cause_inference.p1b.real_diff import (
    ARTIFACT_ROOT,
    FORBIDDEN_MANIFEST_FIELDS,
    FORBIDDEN_SOURCE_TOKENS,
    changed_functions_in_patch,
    generate_real_diff_checkout_tree,
    generated_checkout_imports,
    inspect_real_diff_artifact,
    load_real_diff_manifest,
    validate_real_diff_artifacts,
    validate_real_diff_manifest_schema,
)


def _iter_keys(value: Any):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from _iter_keys(child)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_keys(item)


def _source_texts(root):
    return [path.read_text(encoding="utf-8") for path in sorted(root.rglob("*.py"))]


def test_p1b_real_diff_manifest_schema_excludes_ground_truth_metadata():
    manifest = validate_real_diff_manifest_schema(load_real_diff_manifest())

    keys = set(_iter_keys(manifest))
    assert not (keys & FORBIDDEN_MANIFEST_FIELDS)
    assert {entry["variant_id"] for entry in manifest["variants"]} == {
        variant.variant_id for variant in load_p1b_variants()
    }
    for entry in manifest["variants"]:
        assert set(entry) == {"variant_id", "patch_path", "expected_changed_files", "review_note"}


def test_p1b_real_diff_baseline_has_no_variant_branches():
    baseline_root = ARTIFACT_ROOT / "baseline" / "checkout"

    for text in _source_texts(baseline_root):
        for token in FORBIDDEN_SOURCE_TOKENS:
            assert token not in text


def test_p1b_real_diff_validator_applies_all_variant_patches(tmp_path):
    summary = validate_real_diff_artifacts(work_root=tmp_path / "real_diff_work")

    assert summary["variant_count"] == 25
    assert {item["variant_id"] for item in summary["validated_variants"]} == {
        variant.variant_id for variant in load_p1b_variants()
    }


def test_p1b_real_diff_extracts_changed_functions_from_patch():
    patch_text = (ARTIFACT_ROOT / "patches" / "P1B-BUG-001.patch").read_text(encoding="utf-8")

    assert changed_functions_in_patch(patch_text) == ["shipping.free_shipping_eligible"]


def test_p1b_real_diff_inspection_payload_uses_artifact_data_only():
    payload = inspect_real_diff_artifact("P1B-BUG-020")

    assert payload["patch_path"] == "patches/P1B-BUG-020.patch"
    assert payload["changed_files"] == ["checkout/inventory.py"]
    assert payload["changed_functions"] == ["inventory.reserve_stock"]
    assert "preorder" in payload["diff_excerpt"]


def test_p1b_real_diff_generated_tree_has_no_variant_branch_tokens(tmp_path):
    generated = generate_real_diff_checkout_tree("P1B-BUG-001", tmp_path / "bug_001")

    for text in _source_texts(generated / "checkout"):
        for token in FORBIDDEN_SOURCE_TOKENS:
            assert token not in text


def test_p1b_real_diff_generated_checkout_modules_are_importable(tmp_path):
    generated = generate_real_diff_checkout_tree("P1B-CLEAN-021", tmp_path / "clean_021")

    with generated_checkout_imports(generated) as modules:
        assert set(modules) == {"cart", "config", "discounts", "inventory", "shipping"}
        assert modules["config"].load_config()["shipping_threshold"] == 10000


def test_p1b_real_diff_buggy_patch_changes_representative_behavior(tmp_path):
    generated = generate_real_diff_checkout_tree("P1B-BUG-001", tmp_path / "bug_001")

    with generated_checkout_imports(generated) as modules:
        cfg = modules["config"].load_config()
        assert modules["shipping"].free_shipping_eligible(9999, cfg) is False
        assert modules["shipping"].free_shipping_eligible(10000, cfg) is False
        assert modules["shipping"].free_shipping_eligible(10001, cfg) is True


def test_p1b_real_diff_clean_patch_preserves_representative_behavior(tmp_path):
    generated = generate_real_diff_checkout_tree("P1B-CLEAN-021", tmp_path / "clean_021")

    with generated_checkout_imports(generated) as modules:
        cfg = modules["config"].load_config()
        assert [
            modules["shipping"].free_shipping_eligible(subtotal, cfg)
            for subtotal in (9999, 10000, 10001)
        ] == [False, True, True]
