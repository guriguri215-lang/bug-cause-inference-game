"""Strict declarative ground-truth oracles for outcome-free P2a candidates."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from typing import Any, Mapping

from bug_cause_inference.p2a.adequacy import canonical_digest


ORACLE_DEFINITION_SCHEMA_VERSION = "p2a_ground_truth_oracle.v2"
COMPARISON_SEMANTICS_VERSION = "p2a_typed_comparison.v1"

_CALL_TARGETS = {
    "builtins.len",
    "checkout.cart.add_item",
    "checkout.cart.validate_item",
    "checkout.config.get_region_aliases",
    "checkout.config.get_region_defaults",
    "checkout.config.get_tax_rate",
    "checkout.config.load_config",
    "checkout.discounts.apply_bogo_discount",
    "checkout.discounts.apply_coupon",
    "checkout.discounts.compute_discount",
    "checkout.inventory.cancel_reservation",
    "checkout.shipping.resolve_region_rate",
}
_EXCEPTION_IDENTITIES = {
    ("builtins", "AttributeError"),
    ("builtins", "KeyError"),
    ("builtins", "TypeError"),
    ("builtins", "ValueError"),
}
_LOGICAL_ID_RE = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$")
_ABSOLUTE_LOCAL_IDENTITY_RE = re.compile(
    r"(?:[A-Za-z]:[\\/]|\\\\[^\\/\s]+[\\/][^\\/\s]+|\bfile://[^\s]+|"
    r"(?<![A-Za-z0-9_/\\])/(?!/)[^\s]+)",
    re.IGNORECASE,
)


class OracleDefinitionError(ValueError):
    """Raised when a declarative oracle is incomplete or non-portable."""


@dataclass(frozen=True)
class OracleResult:
    oracle_id: str
    passed: bool
    expected: str
    actual: str


@dataclass(frozen=True)
class OracleDefinition:
    oracle_id: str
    specification_rule: str
    record: dict[str, Any]


def _exact(value: Any, fields: tuple[str, ...], path: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise OracleDefinitionError(f"{path}: expected object")
    missing = [field for field in fields if field not in value]
    unknown = [field for field in value if field not in fields]
    if missing:
        raise OracleDefinitionError(f"{path}.{missing[0]}: missing field")
    if unknown:
        raise OracleDefinitionError(f"{path}.{unknown[0]}: unknown field")
    return value


def _string(value: Any, path: str) -> str:
    if type(value) is not str or not value:
        raise OracleDefinitionError(f"{path}: expected non-empty string")
    if "<function" in value or "<lambda" in value or " at 0x" in value:
        raise OracleDefinitionError(f"{path}: callable repr is not portable")
    if _ABSOLUTE_LOCAL_IDENTITY_RE.search(value):
        raise OracleDefinitionError(
            f"{path}: absolute local identity is forbidden"
        )
    return value


def typed_value(value: Any) -> dict[str, Any]:
    """Encode a Python value without collapsing runtime-significant types."""

    if value is None:
        return {"type": "none"}
    if type(value) is bool:
        return {"type": "bool", "value": value}
    if type(value) is int:
        return {"type": "int", "value": value}
    if type(value) is float:
        if not math.isfinite(value):
            raise OracleDefinitionError("typed value: non-finite float")
        return {"type": "float", "value": value}
    if type(value) is str:
        return {"type": "str", "value": _string(value, "typed value")}
    if type(value) in {list, tuple}:
        return {
            "type": "list" if type(value) is list else "tuple",
            "items": [typed_value(item) for item in value],
        }
    if type(value) is dict:
        entries = [
            {"key": typed_value(key), "value": typed_value(item)}
            for key, item in value.items()
        ]
        entries.sort(
            key=lambda item: json.dumps(
                item["key"], ensure_ascii=False, sort_keys=True, separators=(",", ":")
            )
        )
        return {"type": "mapping", "entries": entries}
    raise OracleDefinitionError(
        f"typed value: unsupported non-portable type {type(value).__name__}"
    )


def reference(step_id: str) -> dict[str, str]:
    return {"type": "reference", "step_id": step_id}


def _validate_typed(value: Any, path: str, *, allow_reference: bool) -> dict[str, Any]:
    if type(value) is not dict or type(value.get("type")) is not str:
        raise OracleDefinitionError(f"{path}: expected typed value record")
    kind = value["type"]
    if kind == "none":
        _exact(value, ("type",), path)
        return {"type": "none"}
    if kind in {"bool", "int", "float", "str"}:
        record = _exact(value, ("type", "value"), path)
        expected_type = {"bool": bool, "int": int, "float": float, "str": str}[kind]
        if type(record["value"]) is not expected_type:
            raise OracleDefinitionError(f"{path}.value: wrong scalar type")
        if kind == "float" and not math.isfinite(record["value"]):
            raise OracleDefinitionError(f"{path}.value: non-finite float")
        scalar = record["value"]
        if kind == "str":
            scalar = _string(scalar, f"{path}.value")
        return {"type": kind, "value": scalar}
    if kind in {"list", "tuple"}:
        record = _exact(value, ("type", "items"), path)
        if type(record["items"]) is not list:
            raise OracleDefinitionError(f"{path}.items: expected list")
        return {
            "type": kind,
            "items": [
                _validate_typed(item, f"{path}.items[{index}]", allow_reference=allow_reference)
                for index, item in enumerate(record["items"])
            ],
        }
    if kind == "mapping":
        record = _exact(value, ("type", "entries"), path)
        if type(record["entries"]) is not list:
            raise OracleDefinitionError(f"{path}.entries: expected list")
        entries = []
        for index, item in enumerate(record["entries"]):
            entry = _exact(item, ("key", "value"), f"{path}.entries[{index}]")
            key = _validate_typed(
                entry["key"], f"{path}.entries[{index}].key", allow_reference=False
            )
            if key["type"] not in {"bool", "int", "float", "str"}:
                raise OracleDefinitionError(f"{path}.entries[{index}].key: non-scalar key")
            entries.append(
                {
                    "key": key,
                    "value": _validate_typed(
                        entry["value"],
                        f"{path}.entries[{index}].value",
                        allow_reference=allow_reference,
                    ),
                }
            )
        entries.sort(
            key=lambda item: json.dumps(
                item["key"], ensure_ascii=False, sort_keys=True, separators=(",", ":")
            )
        )
        keys = [canonical_digest(item["key"]) for item in entries]
        if len(keys) != len(set(keys)):
            raise OracleDefinitionError(f"{path}.entries: duplicate mapping key")
        return {"type": "mapping", "entries": entries}
    if kind == "reference" and allow_reference:
        record = _exact(value, ("type", "step_id"), path)
        return {"type": "reference", "step_id": _string(record["step_id"], f"{path}.step_id")}
    raise OracleDefinitionError(f"{path}.type: unsupported typed value {kind!r}")


def _validate_step(value: Any, path: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise OracleDefinitionError(f"{path}: expected step object")
    operation = value.get("operation")
    if operation == "bind":
        record = _exact(value, ("step_id", "operation", "value"), path)
        return {
            "step_id": _string(record["step_id"], f"{path}.step_id"),
            "operation": "bind",
            "value": _validate_typed(record["value"], f"{path}.value", allow_reference=False),
        }
    if operation == "call":
        record = _exact(
            value,
            ("step_id", "operation", "target", "positional_args", "keyword_args"),
            path,
        )
        target = _string(record["target"], f"{path}.target")
        if target not in _CALL_TARGETS or not _LOGICAL_ID_RE.fullmatch(target):
            raise OracleDefinitionError(f"{path}.target: unknown logical call target")
        if type(record["positional_args"]) is not list or type(record["keyword_args"]) is not dict:
            raise OracleDefinitionError(f"{path}: call arguments have wrong type")
        keyword_args: dict[str, Any] = {}
        for key, item in sorted(record["keyword_args"].items()):
            if type(key) is not str or not key:
                raise OracleDefinitionError(
                    f"{path}.keyword_args: invalid keyword name"
                )
            portable_key = _string(key, f"{path}.keyword_args.<key>")
            keyword_args[portable_key] = _validate_typed(
                item,
                f"{path}.keyword_args.{portable_key}",
                allow_reference=True,
            )
        return {
            "step_id": _string(record["step_id"], f"{path}.step_id"),
            "operation": "call",
            "target": target,
            "positional_args": [
                _validate_typed(item, f"{path}.positional_args[{index}]", allow_reference=True)
                for index, item in enumerate(record["positional_args"])
            ],
            "keyword_args": keyword_args,
        }
    if operation == "extract":
        record = _exact(value, ("step_id", "operation", "source", "path"), path)
        if type(record["path"]) is not list or not record["path"]:
            raise OracleDefinitionError(f"{path}.path: expected non-empty list")
        return {
            "step_id": _string(record["step_id"], f"{path}.step_id"),
            "operation": "extract",
            "source": _validate_typed(record["source"], f"{path}.source", allow_reference=True),
            "path": [
                _validate_typed(item, f"{path}.path[{index}]", allow_reference=False)
                for index, item in enumerate(record["path"])
            ],
        }
    if operation == "set_item":
        record = _exact(value, ("step_id", "operation", "target", "path", "value"), path)
        if type(record["path"]) is not list or not record["path"]:
            raise OracleDefinitionError(f"{path}.path: expected non-empty list")
        return {
            "step_id": _string(record["step_id"], f"{path}.step_id"),
            "operation": "set_item",
            "target": _validate_typed(record["target"], f"{path}.target", allow_reference=True),
            "path": [
                _validate_typed(item, f"{path}.path[{index}]", allow_reference=False)
                for index, item in enumerate(record["path"])
            ],
            "value": _validate_typed(record["value"], f"{path}.value", allow_reference=True),
        }
    if operation == "collect":
        record = _exact(value, ("step_id", "operation", "container_type", "items"), path)
        if record["container_type"] not in {"list", "tuple"} or type(record["items"]) is not list:
            raise OracleDefinitionError(f"{path}: invalid collection step")
        return {
            "step_id": _string(record["step_id"], f"{path}.step_id"),
            "operation": "collect",
            "container_type": record["container_type"],
            "items": [
                _validate_typed(item, f"{path}.items[{index}]", allow_reference=True)
                for index, item in enumerate(record["items"])
            ],
        }
    raise OracleDefinitionError(f"{path}.operation: unsupported operation")


def _validate_expectation(value: Any, path: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise OracleDefinitionError(f"{path}: expected object")
    kind = value.get("kind")
    if kind == "value":
        record = _exact(value, ("kind", "step_id", "expected", "comparison"), path)
        comparison = _exact(record["comparison"], ("kind", "version"), f"{path}.comparison")
        if comparison["kind"] not in {"typed_equality", "typed_inequality"}:
            raise OracleDefinitionError(f"{path}.comparison.kind: unsupported value comparison")
        if comparison["version"] != COMPARISON_SEMANTICS_VERSION:
            raise OracleDefinitionError(f"{path}.comparison.version: wrong version")
        return {
            "kind": "value",
            "step_id": _string(record["step_id"], f"{path}.step_id"),
            "expected": _validate_typed(record["expected"], f"{path}.expected", allow_reference=False),
            "comparison": {
                "kind": comparison["kind"],
                "version": COMPARISON_SEMANTICS_VERSION,
            },
        }
    if kind == "exception":
        record = _exact(value, ("kind", "step_id", "exception", "comparison"), path)
        exception = _exact(record["exception"], ("module", "name"), f"{path}.exception")
        identity = (
            _string(exception["module"], f"{path}.exception.module"),
            _string(exception["name"], f"{path}.exception.name"),
        )
        if identity not in _EXCEPTION_IDENTITIES:
            raise OracleDefinitionError(f"{path}.exception: unsupported exception identity")
        comparison = _exact(record["comparison"], ("kind", "version"), f"{path}.comparison")
        if comparison["kind"] not in {"exception_exact_class", "exception_subclass"}:
            raise OracleDefinitionError(f"{path}.comparison.kind: unsupported exception comparison")
        if comparison["version"] != COMPARISON_SEMANTICS_VERSION:
            raise OracleDefinitionError(f"{path}.comparison.version: wrong version")
        return {
            "kind": "exception",
            "step_id": _string(record["step_id"], f"{path}.step_id"),
            "exception": {"module": identity[0], "name": identity[1]},
            "comparison": {
                "kind": comparison["kind"],
                "version": COMPARISON_SEMANTICS_VERSION,
            },
        }
    raise OracleDefinitionError(f"{path}.kind: unsupported expectation")


def validate_oracle_definition_record(value: Any, path: str = "oracle") -> dict[str, Any]:
    record = _exact(
        value,
        ("schema_version", "oracle_id", "specification_rule", "invocation_kind", "steps", "expectation"),
        path,
    )
    if record["schema_version"] != ORACLE_DEFINITION_SCHEMA_VERSION:
        raise OracleDefinitionError(f"{path}.schema_version: wrong version")
    if record["invocation_kind"] != "strict_step_plan":
        raise OracleDefinitionError(f"{path}.invocation_kind: wrong invocation kind")
    if type(record["steps"]) is not list or not record["steps"]:
        raise OracleDefinitionError(f"{path}.steps: expected non-empty list")
    steps = [
        _validate_step(item, f"{path}.steps[{index}]")
        for index, item in enumerate(record["steps"])
    ]
    step_ids = [item["step_id"] for item in steps]
    if len(step_ids) != len(set(step_ids)):
        raise OracleDefinitionError(f"{path}.steps: duplicate step_id")
    available: set[str] = set()
    for index, step in enumerate(steps):
        references = _step_reference_ids(step)
        unknown = references - available
        if unknown:
            raise OracleDefinitionError(
                f"{path}.steps[{index}]: reference must target an earlier step"
            )
        available.add(step["step_id"])
    expectation = _validate_expectation(record["expectation"], f"{path}.expectation")
    if expectation["step_id"] not in step_ids:
        raise OracleDefinitionError(f"{path}.expectation.step_id: unknown step")
    return {
        "schema_version": ORACLE_DEFINITION_SCHEMA_VERSION,
        "oracle_id": _string(record["oracle_id"], f"{path}.oracle_id"),
        "specification_rule": _string(record["specification_rule"], f"{path}.specification_rule"),
        "invocation_kind": "strict_step_plan",
        "steps": steps,
        "expectation": expectation,
    }


def _typed_reference_ids(value: Any) -> set[str]:
    if type(value) is dict:
        if value.get("type") == "reference":
            return {value["step_id"]}
        result: set[str] = set()
        for item in value.values():
            result.update(_typed_reference_ids(item))
        return result
    if type(value) is list:
        result: set[str] = set()
        for item in value:
            result.update(_typed_reference_ids(item))
        return result
    return set()


def _step_reference_ids(step: dict[str, Any]) -> set[str]:
    return _typed_reference_ids(
        {key: value for key, value in step.items() if key != "step_id"}
    )


def _value_expectation(step_id: str, expected: Any) -> dict[str, Any]:
    return {
        "kind": "value",
        "step_id": step_id,
        "expected": typed_value(expected),
        "comparison": {
            "kind": "typed_equality",
            "version": COMPARISON_SEMANTICS_VERSION,
        },
    }


def _exception_expectation(step_id: str, exception_name: str) -> dict[str, Any]:
    return {
        "kind": "exception",
        "step_id": step_id,
        "exception": {"module": "builtins", "name": exception_name},
        "comparison": {
            "kind": "exception_exact_class",
            "version": COMPARISON_SEMANTICS_VERSION,
        },
    }


def _call_step(
    step_id: str,
    target: str,
    *args: Any,
    keyword_args: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "step_id": step_id,
        "operation": "call",
        "target": target,
        "positional_args": [item if type(item) is dict and item.get("type") == "reference" else typed_value(item) for item in args],
        "keyword_args": {
            key: item if type(item) is dict and item.get("type") == "reference" else typed_value(item)
            for key, item in (keyword_args or {}).items()
        },
    }


def _definition(
    oracle_id: str,
    specification_rule: str,
    steps: list[dict[str, Any]],
    expectation: dict[str, Any],
) -> OracleDefinition:
    record = validate_oracle_definition_record(
        {
            "schema_version": ORACLE_DEFINITION_SCHEMA_VERSION,
            "oracle_id": oracle_id,
            "specification_rule": specification_rule,
            "invocation_kind": "strict_step_plan",
            "steps": steps,
            "expectation": expectation,
        }
    )
    return OracleDefinition(oracle_id, specification_rule, record)


ORACLE_DEFINITIONS: dict[str, OracleDefinition] = {
    "boundary.quantity_zero_rejected": _definition(
        "boundary.quantity_zero_rejected",
        "Item quantity must be strictly positive.",
        [_call_step("validate", "checkout.cart.validate_item", {"quantity": 0})],
        _exception_expectation("validate", "ValueError"),
    ),
    "boundary.quantity_over_max_rejected": _definition(
        "boundary.quantity_over_max_rejected",
        "Quantity 99 is the inclusive maximum; quantity 100 is invalid.",
        [_call_step("validate", "checkout.cart.validate_item", {"quantity": 100})],
        _exception_expectation("validate", "ValueError"),
    ),
    "config.explicit_fractional_tax_rate": _definition(
        "config.explicit_fractional_tax_rate",
        "An explicit numeric tax-rate representation retains its fractional value.",
        [_call_step("rate", "checkout.config.get_tax_rate", {"tax_rates": {"US": "0.07"}}, "US")],
        _value_expectation("rate", 0.07),
    ),
    "config.threshold_override_exact_value": _definition(
        "config.threshold_override_exact_value",
        "A numeric threshold override is normalized without changing its value.",
        [
            _call_step("config", "checkout.config.load_config", {"FREE_SHIPPING_THRESHOLD": "9500"}),
            {"step_id": "threshold", "operation": "extract", "source": reference("config"), "path": [typed_value("shipping_threshold")]},
        ],
        _value_expectation("threshold", 9500),
    ),
    "missing.region_aliases_default_empty": _definition(
        "missing.region_aliases_default_empty",
        "Absent optional region aliases are equivalent to an empty mapping.",
        [_call_step("aliases", "checkout.config.get_region_aliases", {})],
        _value_expectation("aliases", {}),
    ),
    "missing.region_defaults_domestic": _definition(
        "missing.region_defaults_domestic",
        "Absent optional region defaults retain the domestic fallback.",
        [_call_step("defaults", "checkout.config.get_region_defaults", {})],
        _value_expectation("defaults", {"missing": "domestic"}),
    ),
    "missing.tax_rates_absent_us_zero": _definition(
        "missing.tax_rates_absent_us_zero",
        "Absent US tax-rate configuration uses the reviewed zero fallback.",
        [_call_step("rate", "checkout.config.get_tax_rate", {}, "US")],
        _value_expectation("rate", 0.0),
    ),
    "spec.nonstacking_chooses_larger_discount": _definition(
        "spec.nonstacking_chooses_larger_discount",
        "When stacking is disabled, the larger eligible discount is applied.",
        [_call_step("discount", "checkout.discounts.compute_discount", 5000, "WELCOME500", keyword_args={"member": True, "config": {"feature_flags": {"stack_member_and_coupon": False}}})],
        _value_expectation("discount", 500),
    ),
    "spec.unknown_region_uses_domestic_rate": _definition(
        "spec.unknown_region_uses_domestic_rate",
        "An unrecognized shipping region uses the reviewed domestic fallback.",
        [
            _call_step("config", "checkout.config.load_config"),
            _call_step("rate", "checkout.shipping.resolve_region_rate", {"region": "unknown"}, reference("config")),
        ],
        _value_expectation("rate", 800),
    ),
    "state.coupon_preserves_unrelated_state": _definition(
        "state.coupon_preserves_unrelated_state",
        "Applying a coupon preserves unrelated cart state.",
        [
            _call_step("state", "checkout.discounts.apply_coupon", {"session": "keep", "applied_coupons": []}, "WELCOME500"),
            {"step_id": "session", "operation": "extract", "source": reference("state"), "path": [typed_value("session")]},
        ],
        _value_expectation("session", "keep"),
    ),
    "state.over_cancel_clamps_reserved_zero": _definition(
        "state.over_cancel_clamps_reserved_zero",
        "Cancelling more than reserved clamps the reservation count at zero.",
        [
            _call_step("state", "checkout.inventory.cancel_reservation", {"reserved": 1}, 2),
            {"step_id": "reserved", "operation": "extract", "source": reference("state"), "path": [typed_value("reserved")]},
        ],
        _value_expectation("reserved", 0),
    ),
    "clean.boundary_max_accepted": _definition(
        "clean.boundary_max_accepted",
        "The inclusive maximum quantity remains accepted.",
        [
            _call_step("cart", "checkout.cart.add_item", [], "SKU", 1, 99),
            _call_step("length", "builtins.len", reference("cart")),
        ],
        _value_expectation("length", 1),
    ),
    "clean.boundary_over_max_rejected": _definition(
        "clean.boundary_over_max_rejected",
        "A quantity above the inclusive maximum remains rejected.",
        [_call_step("add", "checkout.cart.add_item", [], "SKU", 1, 100)],
        _exception_expectation("add", "ValueError"),
    ),
    "clean.config_absent_jp_fallback": _definition(
        "clean.config_absent_jp_fallback",
        "An absent JP tax-rate mapping retains the reviewed 0.10 fallback.",
        [_call_step("rate", "checkout.config.get_tax_rate", {}, "JP")],
        _value_expectation("rate", 0.10),
    ),
    "clean.config_absent_us_fallback": _definition(
        "clean.config_absent_us_fallback",
        "An absent US tax-rate mapping retains the reviewed zero fallback.",
        [_call_step("rate", "checkout.config.get_tax_rate", {}, "US")],
        _value_expectation("rate", 0.0),
    ),
    "clean.config_explicit_zero_rate": _definition(
        "clean.config_explicit_zero_rate",
        "An explicitly configured zero tax rate remains distinguishable from absence.",
        [_call_step("rate", "checkout.config.get_tax_rate", {"tax_rates": {"US": 0}}, "US")],
        _value_expectation("rate", 0.0),
    ),
    "clean.config_present_none_jp_raises": _definition(
        "clean.config_present_none_jp_raises",
        "A present None JP tax rate is invalid and does not use the absence fallback.",
        [_call_step("rate", "checkout.config.get_tax_rate", {"tax_rates": {"JP": None}}, "JP")],
        _exception_expectation("rate", "TypeError"),
    ),
    "clean.config_present_none_us_raises": _definition(
        "clean.config_present_none_us_raises",
        "A present None US tax rate is invalid and does not use the absence fallback.",
        [_call_step("rate", "checkout.config.get_tax_rate", {"tax_rates": {"US": None}}, "US")],
        _exception_expectation("rate", "TypeError"),
    ),
    "clean.config_string_rate_equivalence": _definition(
        "clean.config_string_rate_equivalence",
        "Equivalent string and numeric tax-rate representations yield the same value.",
        [_call_step("rate", "checkout.config.get_tax_rate", {"tax_rates": {"US": "0.07"}}, "US")],
        _value_expectation("rate", 0.07),
    ),
    "clean.optional_alias_copy_isolated": _definition(
        "clean.optional_alias_copy_isolated",
        "Returned optional alias mappings are copies of configuration state.",
        [
            {"step_id": "source", "operation": "bind", "value": typed_value({"region_aliases": {"x": "domestic"}})},
            _call_step("aliases", "checkout.config.get_region_aliases", reference("source")),
            {"step_id": "mutation", "operation": "set_item", "target": reference("aliases"), "path": [typed_value("x")], "value": typed_value("changed")},
            {"step_id": "original", "operation": "extract", "source": reference("source"), "path": [typed_value("region_aliases")]},
            _call_step("fresh", "checkout.config.get_region_aliases", reference("source")),
            {"step_id": "observation", "operation": "collect", "container_type": "tuple", "items": [reference("original"), reference("fresh")]},
        ],
        _value_expectation("observation", ({"x": "domestic"}, {"x": "domestic"})),
    ),
    "clean.optional_aliases_absent_empty": _definition(
        "clean.optional_aliases_absent_empty",
        "Absent optional alias configuration remains an empty mapping.",
        [_call_step("aliases", "checkout.config.get_region_aliases", {})],
        _value_expectation("aliases", {}),
    ),
    "clean.spec_bogo_ignores_ineligible": _definition(
        "clean.spec_bogo_ignores_ineligible",
        "BOGO selection ignores items explicitly marked ineligible.",
        [_call_step("discount", "checkout.discounts.apply_bogo_discount", [{"unit_price": 100, "bogo_eligible": False}, {"unit_price": 400}, {"unit_price": 700}])],
        _value_expectation("discount", 400),
    ),
    "clean.spec_bogo_selects_cheapest": _definition(
        "clean.spec_bogo_selects_cheapest",
        "BOGO makes the cheapest eligible item free.",
        [_call_step("discount", "checkout.discounts.apply_bogo_discount", [{"unit_price": 700}, {"unit_price": 400}])],
        _value_expectation("discount", 400),
    ),
    "clean.state_coupon_idempotent": _definition(
        "clean.state_coupon_idempotent",
        "Repeating the same coupon transition is idempotent.",
        [
            _call_step("first", "checkout.discounts.apply_coupon", {"session": "keep", "applied_coupons": []}, "WELCOME500"),
            _call_step("second", "checkout.discounts.apply_coupon", reference("first"), "WELCOME500"),
            {"step_id": "applied", "operation": "extract", "source": reference("second"), "path": [typed_value("applied_coupons")]},
        ],
        _value_expectation("applied", ["WELCOME500"]),
    ),
    "clean.state_coupon_preserves_session": _definition(
        "clean.state_coupon_preserves_session",
        "A repeated coupon transition preserves unrelated session state.",
        [
            _call_step("first", "checkout.discounts.apply_coupon", {"session": "keep", "applied_coupons": []}, "WELCOME500"),
            _call_step("second", "checkout.discounts.apply_coupon", reference("first"), "WELCOME500"),
            {"step_id": "session", "operation": "extract", "source": reference("second"), "path": [typed_value("session")]},
        ],
        _value_expectation("session", "keep"),
    ),
}


def oracle_definition_payload(
    oracle_ids: tuple[str, ...] | list[str],
    *,
    definitions: Mapping[str, OracleDefinition] = ORACLE_DEFINITIONS,
) -> list[dict[str, Any]]:
    if type(oracle_ids) not in {tuple, list} or not oracle_ids:
        raise OracleDefinitionError("oracle_ids: expected non-empty ordered list")
    if len(oracle_ids) != len(set(oracle_ids)):
        raise OracleDefinitionError("oracle_ids: duplicate identity")
    records = []
    for index, oracle_id in enumerate(oracle_ids):
        if type(oracle_id) is not str or oracle_id not in definitions:
            raise OracleDefinitionError(f"oracle_ids[{index}]: unknown oracle")
        definition = definitions[oracle_id]
        record = validate_oracle_definition_record(
            definition.record, f"oracle_definitions[{index}]"
        )
        if record["oracle_id"] != oracle_id or definition.oracle_id != oracle_id:
            raise OracleDefinitionError(f"oracle_ids[{index}]: definition identity mismatch")
        if definition.specification_rule != record["specification_rule"]:
            raise OracleDefinitionError(f"oracle_ids[{index}]: specification mismatch")
        records.append(record)
    return records


def oracle_definition_digest(records: Any) -> str:
    if type(records) is not list or not records:
        raise OracleDefinitionError("oracle definition payload must be a non-empty list")
    validated = [
        validate_oracle_definition_record(item, f"oracle_definitions[{index}]")
        for index, item in enumerate(records)
    ]
    oracle_ids = [item["oracle_id"] for item in validated]
    if len(oracle_ids) != len(set(oracle_ids)):
        raise OracleDefinitionError("oracle definition payload has duplicate IDs")
    return canonical_digest(validated)


def _decode_typed(value: dict[str, Any], state: Mapping[str, Any]) -> Any:
    kind = value["type"]
    if kind == "none":
        return None
    if kind in {"bool", "int", "float", "str"}:
        return value["value"]
    if kind in {"list", "tuple"}:
        items = [_decode_typed(item, state) for item in value["items"]]
        return items if kind == "list" else tuple(items)
    if kind == "mapping":
        return {
            _decode_typed(item["key"], state): _decode_typed(item["value"], state)
            for item in value["entries"]
        }
    if kind == "reference":
        return state[value["step_id"]]
    raise OracleDefinitionError(f"cannot decode typed value {kind!r}")


def _resolve_target(target: str, modules: Mapping[str, Any]) -> Any:
    if target == "builtins.len":
        return len
    _, module_name, function_name = target.split(".", 2)
    return getattr(modules[module_name], function_name)


def _extract(source: Any, path: list[dict[str, Any]], state: Mapping[str, Any]) -> Any:
    current = source
    for item in path:
        current = current[_decode_typed(item, state)]
    return current


def _execute_step(step: dict[str, Any], modules: Mapping[str, Any], state: dict[str, Any]) -> Any:
    operation = step["operation"]
    if operation == "bind":
        return _decode_typed(step["value"], state)
    if operation == "call":
        return _resolve_target(step["target"], modules)(
            *[_decode_typed(item, state) for item in step["positional_args"]],
            **{key: _decode_typed(item, state) for key, item in step["keyword_args"].items()},
        )
    if operation == "extract":
        return _extract(_decode_typed(step["source"], state), step["path"], state)
    if operation == "set_item":
        target = _decode_typed(step["target"], state)
        parent = target
        for item in step["path"][:-1]:
            parent = parent[_decode_typed(item, state)]
        parent[_decode_typed(step["path"][-1], state)] = _decode_typed(step["value"], state)
        return target
    if operation == "collect":
        items = [_decode_typed(item, state) for item in step["items"]]
        return items if step["container_type"] == "list" else tuple(items)
    raise OracleDefinitionError(f"unsupported operation {operation!r}")


def _display_typed(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def run_oracle_record(record: Any, modules: Mapping[str, Any]) -> OracleResult:
    record = validate_oracle_definition_record(record)
    oracle_id = record["oracle_id"]
    expectation = record["expectation"]
    state: dict[str, Any] = {}
    for step in record["steps"]:
        try:
            state[step["step_id"]] = _execute_step(step, modules, state)
        except Exception as exc:  # noqa: BLE001 - exact exception identity is oracle data
            actual_identity = (type(exc).__module__, type(exc).__name__)
            if expectation["kind"] != "exception" or expectation["step_id"] != step["step_id"]:
                return OracleResult(
                    oracle_id,
                    False,
                    _display_typed(expectation.get("expected", {"type": "none"})),
                    f"{actual_identity[0]}.{actual_identity[1]}",
                )
            expected_identity = (
                expectation["exception"]["module"],
                expectation["exception"]["name"],
            )
            if expectation["comparison"]["kind"] == "exception_exact_class":
                passed = actual_identity == expected_identity
            else:
                expected_class = getattr(__import__(expected_identity[0]), expected_identity[1])
                passed = isinstance(exc, expected_class)
            return OracleResult(
                oracle_id,
                passed,
                ".".join(expected_identity),
                ".".join(actual_identity),
            )
    if expectation["kind"] == "exception":
        expected_identity = expectation["exception"]
        return OracleResult(
            oracle_id,
            False,
            f"{expected_identity['module']}.{expected_identity['name']}",
            "no exception",
        )
    actual = typed_value(state[expectation["step_id"]])
    expected = expectation["expected"]
    equal = actual == expected
    passed = equal if expectation["comparison"]["kind"] == "typed_equality" else not equal
    return OracleResult(
        oracle_id,
        passed,
        _display_typed(expected),
        _display_typed(actual),
    )


def run_oracle(oracle_id: str, modules: Mapping[str, Any]) -> OracleResult:
    definition = ORACLE_DEFINITIONS[oracle_id]
    return run_oracle_record(definition.record, modules)
