from __future__ import annotations

from pathlib import Path

from bug_cause_inference.p1b.actions import P1B_ACTION_SPECS
from bug_cause_inference.p1b.dataset import get_variant
from bug_cause_inference.p1b.execution import ACTION_TEST_CASE_IDS, TEST_CASES, P1BExecutionContext
from bug_cause_inference.p1b.real_diff import FORBIDDEN_SOURCE_TOKENS
from bug_cause_inference.p2a.compatibility import (
    EXPECTED_LEGACY_CATALOG_DIGEST,
    canonical_digest,
)
from bug_cause_inference.p2a.execution import (
    isolated_legacy_checkout,
    legacy_catalog_contract,
    run_patch_grounded_legacy_action,
)


def test_legacy_catalog_contract_fixes_case_and_action_order_with_stable_digest():
    contract = legacy_catalog_contract()

    assert contract["catalog_mode"] == "legacy"
    assert [case["test_id"] for case in contract["cases"]] == list(TEST_CASES)
    assert [row["action_id"] for row in contract["action_mapping"]] == list(
        ACTION_TEST_CASE_IDS
    )
    assert all(case["test_id"] == case["declared_test_id"] for case in contract["cases"])
    assert all(case["runner_input_semantics"] == "single_variant_id_selects_artifact_only" for case in contract["cases"])
    assert canonical_digest(contract) == EXPECTED_LEGACY_CATALOG_DIGEST


def test_patch_grounded_tree_uses_private_namespace_and_is_removed(tmp_path: Path):
    work_root = tmp_path / "adapter"
    with isolated_legacy_checkout("P1B-BUG-001", work_root=work_root) as (modules, prefix):
        assert prefix.startswith("_p2a_generated_")
        assert prefix.endswith(".checkout.")
        assert all(module.__name__.startswith(prefix) for module in modules.values())
        generated_sources = [
            path.read_text(encoding="utf-8")
            for path in sorted(work_root.rglob("*.py"))
        ]
        for source in generated_sources:
            for token in FORBIDDEN_SOURCE_TOKENS:
                assert token not in source

    assert list(work_root.iterdir()) == []


def test_generated_runner_absorbs_call_interface_without_variant_hidden_input(tmp_path: Path):
    variant_id = "P1B-BUG-001"
    context = P1BExecutionContext()
    with isolated_legacy_checkout(variant_id, work_root=tmp_path / "adapter") as (modules, prefix):
        observation = run_patch_grounded_legacy_action(
            variant_id=variant_id,
            action_id="run_boundary_tests",
            context=context,
            modules=modules,
            module_prefix=prefix,
        )

    assert observation.cost == P1B_ACTION_SPECS["run_boundary_tests"].cost
    assert observation.evidence_source == "p2a_patch_grounded_legacy_catalog"
    assert observation.failed_test_ids == ["boundary.free_shipping_exact_threshold"]
    assert observation.test_results[0]["expected"] is True
    assert observation.test_results[0]["actual"] is False
    assert "shipping.free_shipping_eligible" in observation.failing_executed_functions
    assert not any(prefix in value for value in observation.executed_functions)


def test_patch_grounded_context_preserves_cached_coverage_and_traceback_semantics(tmp_path: Path):
    variant = get_variant("P1B-BUG-007")
    context = P1BExecutionContext()
    with isolated_legacy_checkout(variant.variant_id, work_root=tmp_path / "adapter") as (modules, prefix):
        run_patch_grounded_legacy_action(
            variant_id=variant.variant_id,
            action_id="run_null_missing_tests",
            context=context,
            modules=modules,
            module_prefix=prefix,
        )
        traceback = run_patch_grounded_legacy_action(
            variant_id=variant.variant_id,
            action_id="inspect_traceback",
            context=context,
            modules=modules,
            module_prefix=prefix,
        )
        coverage = run_patch_grounded_legacy_action(
            variant_id=variant.variant_id,
            action_id="inspect_coverage_spectrum",
            context=context,
            modules=modules,
            module_prefix=prefix,
        )

    assert traceback.failure_found is False
    assert traceback.exception_type == "TypeError"
    assert traceback.failed_test_ids == ["null_missing.none_cart_subtotal"]
    assert coverage.failed_test_ids == ["null_missing.none_cart_subtotal"]
    assert coverage.coverage_counts["cart.cart_subtotal"]["failed"] == 1


def test_recent_diff_keeps_relative_provenance_and_policy_visible_location_signal(tmp_path: Path):
    variant_id = "P1B-BUG-001"
    with isolated_legacy_checkout(variant_id, work_root=tmp_path / "adapter") as (modules, prefix):
        observation = run_patch_grounded_legacy_action(
            variant_id=variant_id,
            action_id="inspect_recent_diff",
            context=P1BExecutionContext(),
            modules=modules,
            module_prefix=prefix,
        )

    assert observation.diff_artifact_path == "patches/P1B-BUG-001.patch"
    assert observation.changed_files == ["checkout/shipping.py"]
    assert observation.changed_functions == ["shipping.free_shipping_eligible"]
    assert observation.location_scores == {"shipping.free_shipping_eligible": 4.0}
    assert not Path(observation.diff_artifact_path).is_absolute()
