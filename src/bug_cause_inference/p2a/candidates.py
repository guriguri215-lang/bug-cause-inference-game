"""Declarative outcome-free P2a candidate cohort for authoring review."""

from __future__ import annotations

import ast
import shutil
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
from typing import Any

from bug_cause_inference.p1b.real_diff import (
    RealDiffArtifactError,
    apply_unified_patch,
    changed_files_in_patch,
)
from bug_cause_inference.p2a.adequacy import (
    MATERIAL_DIMENSION_IDS,
    TRUSTED_REFERENCE_REGISTRY,
    canonical_digest,
    core_fingerprint_distance,
    validate_candidate_cohort,
)


PATCH_OPERATION_SCHEMA_VERSION = "p2a_patch_operation.v1"

_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
_BASELINE_ROOT = (
    _REPOSITORY_ROOT
    / "src"
    / "bug_cause_inference"
    / "p1b"
    / "artifacts"
    / "real_diff"
    / "baseline"
)
_LEGACY_PATCH_ROOT = (
    _REPOSITORY_ROOT
    / "src"
    / "bug_cause_inference"
    / "p1b"
    / "artifacts"
    / "real_diff"
    / "patches"
)
_PRESERVED_CALLEE_IDS = {
    "any",
    "bool",
    "dict",
    "float",
    "int",
    "len",
    "list",
    "max",
    "min",
    "round",
    "sum",
}
_PRESERVED_ATTRIBUTE_IDS = {
    "append",
    "get",
    "items",
    "quantize",
    "strip",
    "upper",
}


class CandidatePatchSemanticError(ValueError):
    """Raised when a patch cannot receive a unique artifact-derived identity."""


def _repository_path(relative_path: str) -> Path:
    parsed = PurePosixPath(relative_path)
    if parsed.is_absolute() or ".." in parsed.parts:
        raise CandidatePatchSemanticError("patch path must be repository-relative")
    path = _REPOSITORY_ROOT.joinpath(*parsed.parts)
    resolved = path.resolve()
    root = _REPOSITORY_ROOT.resolve()
    if resolved != root and root not in resolved.parents:
        raise CandidatePatchSemanticError("patch path escapes repository root")
    if not path.is_file():
        raise CandidatePatchSemanticError(f"patch artifact does not exist: {relative_path}")
    return path


def _constant_kind(value: Any) -> str:
    if value is None:
        return "none"
    if type(value) is bool:
        return "bool"
    if type(value) is int:
        return "number"
    if type(value) is float:
        return "number"
    if type(value) is str:
        return "string"
    if type(value) is bytes:
        return "bytes"
    raise CandidatePatchSemanticError(
        f"unsupported AST literal type: {type(value).__name__}"
    )


def _normalized_identifier(value: str, *, attribute: bool = False) -> str:
    preserved = _PRESERVED_ATTRIBUTE_IDS if attribute else _PRESERVED_CALLEE_IDS
    return value if value in preserved else "IDENTIFIER"


def _normalize_ast(node: ast.AST) -> dict[str, Any]:
    if isinstance(node, ast.Dict):
        return {"node": "literal_mapping"}
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)) and all(
        isinstance(item, ast.Constant) for item in node.elts
    ):
        return {"node": f"literal_{type(node).__name__.lower()}"}
    result: dict[str, Any] = {"node": type(node).__name__}
    for field, value in ast.iter_fields(node):
        if field == "ctx":
            continue
        if isinstance(value, ast.AST):
            result[field] = _normalize_ast(value)
        elif isinstance(value, list):
            result[field] = [
                _normalize_ast(item) if isinstance(item, ast.AST) else item
                for item in value
            ]
        elif isinstance(node, ast.Constant) and field == "value":
            result[field] = _constant_kind(value)
        elif isinstance(node, ast.Name) and field == "id":
            result[field] = _normalized_identifier(value)
        elif isinstance(node, ast.Attribute) and field == "attr":
            result[field] = _normalized_identifier(value, attribute=True)
        elif isinstance(node, (ast.arg, ast.FunctionDef, ast.AsyncFunctionDef)) and field in {
            "arg",
            "name",
        }:
            result[field] = "IDENTIFIER"
        else:
            result[field] = value
    return result


def _edit_context(ancestors: tuple[str, ...], current: ast.AST, field: str) -> list[str]:
    return [*ancestors, type(current).__name__, field][-3:]


def _ast_edits(
    before: Any,
    after: Any,
    *,
    ancestors: tuple[str, ...] = (),
    field_name: str = "root",
) -> list[dict[str, Any]]:
    if type(before) is not type(after):
        return [
            {
                "kind": "replace_node",
                "context": list(ancestors[-2:]),
                "before": _normalize_ast(before) if isinstance(before, ast.AST) else before,
                "after": _normalize_ast(after) if isinstance(after, ast.AST) else after,
            }
        ]
    if isinstance(before, ast.AST):
        edits: list[dict[str, Any]] = []
        next_ancestors = (*ancestors, type(before).__name__)
        for field in before._fields:
            if field == "ctx":
                continue
            edits.extend(
                _ast_edits(
                    getattr(before, field),
                    getattr(after, field),
                    ancestors=next_ancestors,
                    field_name=field,
                )
            )
        return edits
    if isinstance(before, list):
        if len(before) != len(after):
            return [
                {
                    "kind": "replace_sequence",
                    "context": [*ancestors, field_name][-3:],
                    "before": [
                        _normalize_ast(item) if isinstance(item, ast.AST) else item
                        for item in before
                    ],
                    "after": [
                        _normalize_ast(item) if isinstance(item, ast.AST) else item
                        for item in after
                    ],
                }
            ]
        edits: list[dict[str, Any]] = []
        for left, right in zip(before, after, strict=True):
            edits.extend(
                _ast_edits(
                    left,
                    right,
                    ancestors=ancestors,
                    field_name=field_name,
                )
            )
        return edits
    if before == after:
        return []
    context = [*ancestors, field_name][-3:]
    parent = ancestors[-1] if ancestors else ""
    if parent == "Constant" and field_name == "value":
        return [
            {
                "kind": "replace_literal",
                "context": context,
                "before": _constant_kind(before),
                "after": _constant_kind(after),
            }
        ]
    if field_name in {"id", "arg", "name", "attr"}:
        attribute = field_name == "attr"
        return [
            {
                "kind": "replace_identifier",
                "context": context,
                "before": _normalized_identifier(str(before), attribute=attribute),
                "after": _normalized_identifier(str(after), attribute=attribute),
            }
        ]
    return [
        {
            "kind": "replace_scalar",
            "context": context,
            "before": before,
            "after": after,
        }
    ]


def _function_nodes(
    module: ast.Module,
) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    nodes = [
        node
        for node in ast.walk(module)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    if len({node.name for node in nodes}) != len(nodes):
        raise CandidatePatchSemanticError("duplicate function name is ambiguous")
    return {node.name: node for node in nodes}


class _ChangedFunctionMask(ast.NodeTransformer):
    def __init__(self, function_name: str) -> None:
        self.function_name = function_name

    def _mask(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> ast.Expr | ast.FunctionDef | ast.AsyncFunctionDef:
        if node.name != self.function_name:
            return self.generic_visit(node)
        return ast.Expr(value=ast.Constant(value="P2A_CHANGED_FUNCTION_SUBTREE"))

    def visit_FunctionDef(  # noqa: N802 - ast.NodeTransformer API
        self, node: ast.FunctionDef
    ) -> ast.Expr | ast.FunctionDef:
        return self._mask(node)

    def visit_AsyncFunctionDef(  # noqa: N802 - ast.NodeTransformer API
        self, node: ast.AsyncFunctionDef
    ) -> ast.Expr | ast.AsyncFunctionDef:
        return self._mask(node)


def _module_semantics_without_function(
    module: ast.Module, function_name: str
) -> str:
    masked = _ChangedFunctionMask(function_name).visit(module)
    return ast.dump(masked, include_attributes=False)


def canonical_patch_operation_payload_from_text(text: str) -> dict[str, Any]:
    """Derive a portable semantic edit identity directly from unified patch bytes."""

    if type(text) is not str or not text.strip():
        raise CandidatePatchSemanticError("patch text must be non-empty")
    try:
        files = changed_files_in_patch(text)
    except RealDiffArtifactError as exc:
        raise CandidatePatchSemanticError(
            f"unsupported unified patch transformation: {exc}"
        ) from exc
    if len(files) != 1:
        raise CandidatePatchSemanticError(
            "patch semantic identity supports exactly one changed file and function"
        )
    source_path = _BASELINE_ROOT.joinpath(*PurePosixPath(files[0]).parts)
    before_source = source_path.read_text(encoding="utf-8")
    with TemporaryDirectory(prefix="p2a-patch-operation-") as temporary:
        tree = Path(temporary) / "baseline"
        shutil.copytree(_BASELINE_ROOT, tree)
        try:
            apply_unified_patch(tree, text)
        except RealDiffArtifactError as exc:
            raise CandidatePatchSemanticError(
                f"unsupported unified patch transformation: {exc}"
            ) from exc
        after_source = tree.joinpath(*PurePosixPath(files[0]).parts).read_text(
            encoding="utf-8"
        )
    before_module = ast.parse(before_source)
    after_module = ast.parse(after_source)
    before_nodes = _function_nodes(before_module)
    after_nodes = _function_nodes(after_module)
    if before_nodes.keys() != after_nodes.keys():
        raise CandidatePatchSemanticError("function addition or removal is unsupported")
    changed = [
        name
        for name in before_nodes
        if ast.dump(before_nodes[name], include_attributes=False)
        != ast.dump(after_nodes[name], include_attributes=False)
    ]
    if len(changed) != 1:
        raise CandidatePatchSemanticError(
            "patch semantic identity requires exactly one actual changed function"
        )
    changed_function = changed[0]
    if _module_semantics_without_function(
        before_module, changed_function
    ) != _module_semantics_without_function(after_module, changed_function):
        raise CandidatePatchSemanticError(
            "patch contains semantic AST edits outside the changed function"
        )
    before = before_nodes[changed_function]
    after = after_nodes[changed_function]
    edits = _ast_edits(before, after)
    if not edits:
        raise CandidatePatchSemanticError("patch has no supported semantic AST edit")
    return {
        "schema_version": PATCH_OPERATION_SCHEMA_VERSION,
        "operation_kind": "python_ast_edit_sequence",
        "edits": edits,
    }


@lru_cache(maxsize=None)
def canonical_patch_operation_payload(patch_path: str) -> dict[str, Any]:
    """Derive a portable semantic edit identity from an actual unified patch."""

    text = _repository_path(patch_path).read_text(encoding="utf-8")
    return canonical_patch_operation_payload_from_text(text)


def canonical_patch_operation_digest(patch_path: str) -> str:
    return canonical_digest(canonical_patch_operation_payload(patch_path))


def canonical_patch_operation_identity(patch_path: str) -> str:
    return f"{PATCH_OPERATION_SCHEMA_VERSION}:{canonical_patch_operation_digest(patch_path)}"


@dataclass(frozen=True)
class CandidateDefinition:
    variant_id: str
    cohort_kind: str
    patch_path: str
    oracle_ids: tuple[str, ...]
    metadata: dict[str, Any]


_BUGGY_ROWS = (
    (
        "P2A-BUG-001", "boundary_precision", "Cart item quantity validation", "boundary_condition",
        "cart", ("cart.validate_item",), "quantity is zero", "Quantity zero is rejected.",
        "Quantity zero is accepted.", "ValueError at the strict positive lower boundary.",
        "tighten_positive_quantity_guard", "medium", "run_boundary_tests",
        ("boundary.quantity_zero_rejected",), "Item quantity must be strictly positive.",
        "lower-bound weakening", "accept zero instead of rejecting it", "single_function",
    ),
    (
        "P2A-BUG-002", "boundary_precision", "Cart item quantity validation", "boundary_condition",
        "cart", ("cart.validate_item",), "quantity is one above 99", "Quantity 100 is rejected.",
        "Quantity 100 is accepted.", "Missing ValueError above the inclusive maximum.",
        "restore_quantity_maximum", "medium", "run_boundary_tests",
        ("boundary.quantity_over_max_rejected",), "Quantity 99 is the inclusive maximum.",
        "upper-bound expansion", "raise the accepted maximum from 99 to 100", "single_function",
    ),
    (
        "P2A-BUG-003", "missing_optional_input", "Region default configuration", "missing_null_handling",
        "config", ("config.get_region_defaults",), "region_defaults key is absent", "Domestic fallback mapping is returned.",
        "KeyError is raised.", "Exception from an optional mapping accessor.",
        "restore_optional_region_default", "easy", "run_null_missing_tests",
        ("missing.region_defaults_domestic",), "Absent region defaults retain the domestic fallback.",
        "required optional mapping", "replace defaulted mapping lookup with direct indexing", "single_function",
    ),
    (
        "P2A-BUG-004", "missing_optional_input", "Absent tax-rate configuration", "missing_null_handling",
        "config", ("config.get_tax_rate",), "tax_rates mapping is absent for a US lookup", "The reviewed absence fallback 0.0 is returned.",
        "The global configured US rate 0.07 is returned.", "Wrong scalar fallback from an absent optional mapping.",
        "restore_absent_tax_rate_fallback", "medium", "run_null_missing_tests",
        ("missing.tax_rates_absent_us_zero",), "Absent US tax-rate configuration uses the reviewed zero fallback.",
        "implicit global default substitution", "replace empty absence sentinel with global configured mapping", "single_function",
    ),
    (
        "P2A-BUG-005", "config_normalization", "Tax-rate representation", "configuration_environment",
        "config", ("config.get_tax_rate",), "explicit fractional rate is represented as a string", "The configured fractional rate is returned.",
        "The rate is truncated to zero.", "Configured 0.07 becomes 0.0 after coercion.",
        "preserve_fractional_config_value", "medium", "run_config_matrix_tests",
        ("config.explicit_fractional_tax_rate",), "Explicit numeric rate representations retain their fractional value.",
        "lossy numeric coercion", "coerce through integer before float conversion", "single_function",
    ),
    (
        "P2A-BUG-006", "config_normalization", "Shipping-threshold override", "configuration_environment",
        "config", ("config.load_config",), "threshold override is the numeric string 9500", "The exact normalized value 9500 is stored.",
        "The value is quantized to 10000.", "Normalized threshold differs from its supplied value.",
        "preserve_exact_threshold_override", "hard", "run_config_matrix_tests",
        ("config.threshold_override_exact_value",), "Threshold normalization does not quantize an exact numeric value.",
        "lossy threshold quantization", "round parsed threshold to the nearest thousand", "single_function",
    ),
    (
        "P2A-BUG-007", "state_sequence", "Reservation cancellation invariant", "state_order_dependence",
        "inventory", ("inventory.cancel_reservation",), "cancel quantity exceeds reserved quantity", "Reserved count clamps at zero.",
        "Reserved count becomes negative.", "Negative reservation state after over-cancellation.",
        "clamp_reservation_floor", "medium", "run_state_sequence_tests",
        ("state.over_cancel_clamps_reserved_zero",), "Reservation state cannot be negative.",
        "unbounded reversal", "remove zero floor from reservation cancellation", "multi_step",
    ),
    (
        "P2A-BUG-008", "state_sequence", "Coupon state preservation", "state_order_dependence",
        "discounts", ("discounts.apply_coupon",), "coupon transition follows unrelated session state", "Coupon application preserves unrelated state.",
        "Unrelated session state is discarded.", "State projection loses a pre-existing session field.",
        "preserve_cart_state_transition", "hard", "run_state_sequence_tests",
        ("state.coupon_preserves_unrelated_state",), "State transitions preserve fields outside coupon state.",
        "destructive state projection", "return coupon state without merging the prior mapping", "multi_step",
    ),
    (
        "P2A-BUG-009", "spec_semantics", "Unknown-region shipping fallback", "specification_mismatch",
        "shipping", ("shipping.resolve_region_rate",), "address contains an unrecognized region", "Reviewed domestic fallback rate is used.",
        "International rate is used.", "Unknown region produces the wrong documented fallback fee.",
        "restore_domestic_unknown_region_fallback", "medium", "inspect_spec_clause",
        ("spec.unknown_region_uses_domestic_rate",), "Unknown shipping regions use the reviewed domestic fallback.",
        "fallback category substitution", "replace domestic fallback with international fallback", "cross_function",
    ),
    (
        "P2A-BUG-010", "spec_semantics", "Non-stacking discount choice", "specification_mismatch",
        "discounts", ("discounts.compute_discount",), "member and coupon discounts are both eligible while stacking is disabled", "The larger eligible discount is applied.",
        "The smaller eligible discount is applied.", "Non-stacking order receives 300 instead of 500.",
        "restore_best_nonstacking_discount", "medium", "inspect_spec_clause",
        ("spec.nonstacking_chooses_larger_discount",), "Non-stacking selects the larger eligible discount.",
        "selection extremum reversal for alternatives", "replace maximum alternative with minimum alternative", "cross_function",
    ),
)


_CLEAN_ROWS = (
    (
        "P2A-CLEAN-001", "boundary_adjacent_valid_behavior", 1, "boundary_precision",
        "Quantity upper-bound validation", "Local extraction beside an inclusive maximum comparison.",
        "A new maximum variable beside rejection logic can resemble a boundary fix.",
        "Quantities 99 and 100 retain their accepted and rejected behavior.",
        "Boundary oracle evidence at and above the maximum.",
        "Extracting the reviewed maximum literal into a local does not alter comparison semantics.",
        ("cart.validate_item",), ("clean.boundary_max_accepted", "clean.boundary_over_max_rejected"),
        "The maximum quantity remains inclusive at 99.", "benign boundary constant extraction",
        "extract maximum quantity local while preserving comparison", "single_function",
    ),
    (
        "P2A-CLEAN-002", "optional_input_valid_absence", 2, "missing_optional_input",
        "Optional region aliases", "Local extraction around an absent-to-empty mapping default.",
        "Recent alias accessor changes can resemble missing-key handling.",
        "Absent aliases remain empty and returned mappings remain isolated copies.",
        "Absence and copy-isolation oracle evidence.",
        "Naming the optional alias mapping before copying preserves default and isolation behavior.",
        ("config.get_region_aliases",), ("clean.optional_alias_copy_isolated", "clean.optional_aliases_absent_empty"),
        "Optional alias absence is an empty isolated mapping.", "benign optional mapping extraction",
        "extract optional alias mapping before defensive copy", "single_function",
    ),
    (
        "P2A-CLEAN-003", "config_equivalent_normalization", 3, "config_normalization",
        "Equivalent tax-rate representations", "Configured value extracted inside the unchanged membership branch.",
        "Changing configuration lookup shape can resemble normalization drift.",
        "String fractional, explicit zero, present None, and absent tax rates retain exact membership semantics.",
        "Value, expected-exception, and regional absence-fallback oracle evidence.",
        "The local is assigned only after membership succeeds, preserving present None exceptions and regional absence fallbacks.",
        ("config.get_tax_rate",), (
            "clean.config_absent_jp_fallback",
            "clean.config_absent_us_fallback",
            "clean.config_explicit_zero_rate",
            "clean.config_present_none_jp_raises",
            "clean.config_present_none_us_raises",
            "clean.config_string_rate_equivalence",
        ),
        "Tax-rate membership distinguishes a present value, including None, from absence.", "benign configured value extraction",
        "extract configured rate while preserving presence semantics", "single_function",
    ),
    (
        "P2A-CLEAN-004", "valid_state_sequence", 4, "state_sequence",
        "Repeated coupon transition", "Boolean local extracted from idempotence membership check.",
        "A repeated transition and new branch local can resemble an idempotence repair.",
        "Repeated coupon application remains idempotent and preserves unrelated state.",
        "Repeat and state-preservation oracle evidence.",
        "The extracted membership result drives the identical append condition.",
        ("discounts.apply_coupon",), ("clean.state_coupon_idempotent", "clean.state_coupon_preserves_session"),
        "Repeated coupon application is a valid idempotent transition.", "benign transition predicate extraction",
        "extract coupon membership predicate without changing transition", "multi_step",
    ),
    (
        "P2A-CLEAN-005", "nonintuitive_spec_conformance", 5, "spec_semantics",
        "BOGO cheapest-eligible rule", "Intermediate names expose an intentionally non-maximal selection rule.",
        "Choosing the cheapest item can appear counterintuitive beside higher prices.",
        "The cheapest eligible item remains the discount and ineligible items remain excluded.",
        "Cheapest-selection and eligibility-filter oracle evidence.",
        "Renaming the filtered price list and selected minimum preserves the explicit rule.",
        ("discounts.apply_bogo_discount",), ("clean.spec_bogo_ignores_ineligible", "clean.spec_bogo_selects_cheapest"),
        "BOGO explicitly selects the cheapest eligible item.", "benign explicit selection naming",
        "name eligible prices and selected minimum without changing selection", "single_function",
    ),
)


def _fingerprint(
    *,
    spec_rule: str,
    mechanism: str,
    targets: tuple[str, ...],
    trigger: str,
    observable: str,
    oracle_ids: tuple[str, ...],
    expected_outcome: str,
    patch_operation: str,
    interaction_depth: str,
) -> dict[str, Any]:
    return {
        "spec_rule": spec_rule,
        "causal_mechanism": mechanism,
        "target_function_set": sorted(targets),
        "trigger_shape": trigger,
        "observable_behavior": observable,
        "oracle_outcome_vector": [
            {"oracle_id": oracle_id, "expected_outcome": expected_outcome}
            for oracle_id in sorted(oracle_ids)
        ],
        "normalized_patch_operation": patch_operation,
        "interaction_depth": interaction_depth,
    }


def _actual_dimensions(current: dict[str, Any], nearest: dict[str, Any]) -> list[str]:
    dimensions: set[str] = set()
    if current["spec_rule"] != nearest["spec_rule"] or current["causal_mechanism"] != nearest["causal_mechanism"]:
        dimensions.add("spec/mechanism")
    if current["target_function_set"] != nearest["target_function_set"]:
        dimensions.add("target_function_set")
    if current["trigger_shape"] != nearest["trigger_shape"]:
        dimensions.add("trigger_shape")
    if current["observable_behavior"] != nearest["observable_behavior"] or current["oracle_outcome_vector"] != nearest["oracle_outcome_vector"]:
        dimensions.add("observable/oracle_outcome")
    if current["normalized_patch_operation"] != nearest["normalized_patch_operation"]:
        dimensions.add("normalized_patch_operation")
    if current["interaction_depth"] != nearest["interaction_depth"]:
        dimensions.add("interaction_depth")
    return [item for item in MATERIAL_DIMENSION_IDS if item in dimensions]


def _nearest(
    fingerprint: dict[str, Any],
    cohort_kind: str,
    prior: list[tuple[str, dict[str, Any], str]],
) -> tuple[str, dict[str, Any], str]:
    pool = [
        (item.variant_id, item.core_fingerprint, item.core_fingerprint_digest)
        for item in TRUSTED_REFERENCE_REGISTRY
        if item.cohort_kind == cohort_kind
    ] + prior
    return min(pool, key=lambda item: core_fingerprint_distance(fingerprint, item[1]))


def _build_buggy() -> list[CandidateDefinition]:
    definitions: list[CandidateDefinition] = []
    prior: list[tuple[str, dict[str, Any], str]] = []
    for row in _BUGGY_ROWS:
        (
            variant_id, bucket, spec_area, cause, target_module, targets, trigger,
            expected, actual, observable, fix_intent, difficulty, action_mapping,
            oracle_ids, spec_rule, mechanism, _author_patch_description, depth,
        ) = row
        patch_path = (
            f"src/bug_cause_inference/p2a/artifacts/candidates/patches/{variant_id}.patch"
        )
        patch_operation = canonical_patch_operation_identity(patch_path)
        fingerprint = _fingerprint(
            spec_rule=spec_rule,
            mechanism=mechanism,
            targets=targets,
            trigger=trigger,
            observable=observable,
            oracle_ids=oracle_ids,
            expected_outcome="fail",
            patch_operation=patch_operation,
            interaction_depth=depth,
        )
        nearest_id, nearest_fp, nearest_digest = _nearest(fingerprint, "buggy", prior)
        changed_file = f"checkout/{target_module}.py"
        metadata = {
            "variant_id": variant_id,
            "cohort": "buggy_expansion",
            "domain": "checkout_pricing",
            "spec_area": spec_area,
            "primary_bucket": bucket,
            "is_buggy": True,
            "cause_category": cause,
            "target_module": target_module,
            "target_functions": sorted(targets),
            "trigger_shape": trigger,
            "expected_behavior": expected,
            "actual_behavior": actual,
            "oracle_ids": sorted(oracle_ids),
            "action_test_catalog_ids": sorted(oracle_ids),
            "action_mapping": action_mapping,
            "observable_signature": observable,
            "patch_semantic_fingerprint": patch_operation,
            "changed_files": [changed_file],
            "changed_functions": sorted(targets),
            "interaction_depth": depth,
            "fix_intent_category": fix_intent,
            "difficulty": difficulty,
            "nearest_legacy_or_admitted_variant_id": nearest_id,
            "material_difference_dimensions": _actual_dimensions(fingerprint, nearest_fp),
            "diversity_rationale": "The specification mechanism and deterministic oracle shape differ materially from the computed nearest reference.",
            "core_fingerprint": fingerprint,
            "nearest_reference_core_fingerprint": nearest_fp,
            "nearest_reference_core_fingerprint_digest": nearest_digest,
        }
        definitions.append(
            CandidateDefinition(
                variant_id,
                "buggy",
                patch_path,
                tuple(sorted(oracle_ids)),
                metadata,
            )
        )
        prior.append((variant_id, fingerprint, canonical_digest(fingerprint)))
    return definitions


def _build_clean() -> list[CandidateDefinition]:
    definitions: list[CandidateDefinition] = []
    prior: list[tuple[str, dict[str, Any], str]] = []
    for row in _CLEAN_ROWS:
        (
            variant_id, family, order, adjacent, spec_area, stress, confusing,
            expected, evidence, rationale, targets, oracle_ids, spec_rule,
            mechanism, _author_patch_description, depth,
        ) = row
        patch_path = (
            f"src/bug_cause_inference/p2a/artifacts/candidates/patches/{variant_id}.patch"
        )
        patch_operation = canonical_patch_operation_identity(patch_path)
        fingerprint = _fingerprint(
            spec_rule=spec_rule,
            mechanism=mechanism,
            targets=targets,
            trigger=stress,
            observable=expected,
            oracle_ids=oracle_ids,
            expected_outcome="pass",
            patch_operation=patch_operation,
            interaction_depth=depth,
        )
        nearest_id, nearest_fp, nearest_digest = _nearest(fingerprint, "clean_stress", prior)
        target_module = targets[0].split(".", 1)[0]
        metadata = {
            "variant_id": variant_id,
            "cohort": "clean_stress_expansion",
            "domain": "checkout_pricing",
            "spec_area": spec_area,
            "primary_bucket": "clean_false_positive",
            "is_buggy": False,
            "clean_stress_family_id": family,
            "clean_stress_family_order": order,
            "adjacent_buggy_bucket_id": adjacent,
            "stress_mechanism": stress,
            "confusing_signal": confusing,
            "expected_clean_behavior": expected,
            "no_bug_oracle_ids": sorted(oracle_ids),
            "recommended_no_bug_evidence": evidence,
            "benign_diff_rationale": rationale,
            "patch_semantic_fingerprint": patch_operation,
            "changed_files": [f"checkout/{target_module}.py"],
            "changed_functions": sorted(targets),
            "interaction_depth": depth,
            "nearest_legacy_or_admitted_clean_variant_id": nearest_id,
            "material_difference_dimensions": _actual_dimensions(fingerprint, nearest_fp),
            "diversity_rationale": "The benign stress mechanism and full no-bug oracle vector differ materially from the computed nearest clean reference.",
            "core_fingerprint": fingerprint,
            "nearest_reference_core_fingerprint": nearest_fp,
            "nearest_reference_core_fingerprint_digest": nearest_digest,
        }
        definitions.append(
            CandidateDefinition(
                variant_id,
                "clean_stress",
                patch_path,
                tuple(sorted(oracle_ids)),
                metadata,
            )
        )
        prior.append((variant_id, fingerprint, canonical_digest(fingerprint)))
    return definitions


def validate_artifact_semantic_cohort(
    buggy_candidates: tuple[CandidateDefinition, ...],
    clean_candidates: tuple[CandidateDefinition, ...],
) -> dict[str, dict[str, str]]:
    """Reject semantic operation clones against legacy and prior cohort artifacts."""

    identities: dict[str, dict[str, str]] = {"buggy": {}, "clean_stress": {}}
    for index in range(1, 26):
        variant_id = (
            f"P1B-BUG-{index:03d}" if index <= 20 else f"P1B-CLEAN-{index:03d}"
        )
        cohort_kind = "buggy" if index <= 20 else "clean_stress"
        path = _LEGACY_PATCH_ROOT / f"{variant_id}.patch"
        relative = path.relative_to(_REPOSITORY_ROOT).as_posix()
        identities[cohort_kind][variant_id] = canonical_patch_operation_identity(
            relative
        )
    for cohort_kind, candidates in (
        ("buggy", buggy_candidates),
        ("clean_stress", clean_candidates),
    ):
        observed = identities[cohort_kind]
        for candidate in candidates:
            identity = canonical_patch_operation_identity(candidate.patch_path)
            duplicate = next(
                (variant_id for variant_id, value in observed.items() if value == identity),
                None,
            )
            if duplicate is not None:
                raise CandidatePatchSemanticError(
                    f"{candidate.variant_id}: semantic patch operation duplicates {duplicate}"
                )
            if candidate.metadata["patch_semantic_fingerprint"] != identity:
                raise CandidatePatchSemanticError(
                    f"{candidate.variant_id}: patch fingerprint is not artifact-derived"
                )
            if (
                candidate.metadata["core_fingerprint"]["normalized_patch_operation"]
                != identity
            ):
                raise CandidatePatchSemanticError(
                    f"{candidate.variant_id}: normalized operation is not artifact-derived"
                )
            observed[candidate.variant_id] = identity
    return identities


BUGGY_CANDIDATES = tuple(_build_buggy())
CLEAN_CANDIDATES = tuple(_build_clean())
ARTIFACT_PATCH_OPERATION_IDENTITIES = validate_artifact_semantic_cohort(
    BUGGY_CANDIDATES,
    CLEAN_CANDIDATES,
)
BUGGY_CANDIDATE_METADATA, CLEAN_CANDIDATE_METADATA = validate_candidate_cohort(
    [item.metadata for item in BUGGY_CANDIDATES],
    [item.metadata for item in CLEAN_CANDIDATES],
)
CANDIDATES = BUGGY_CANDIDATES + CLEAN_CANDIDATES
CANDIDATE_IDS = tuple(item.variant_id for item in CANDIDATES)


def candidate_by_id(variant_id: str) -> CandidateDefinition:
    for candidate in CANDIDATES:
        if candidate.variant_id == variant_id:
            return candidate
    raise KeyError(variant_id)
