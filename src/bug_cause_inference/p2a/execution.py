"""P2a-only patch-grounded execution for the frozen P1b legacy catalog."""

from __future__ import annotations

import importlib
import inspect
import itertools
import shutil
import sys
import tempfile
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from types import FunctionType, ModuleType
from typing import Any

from bug_cause_inference.p1b import execution as p1b_execution
from bug_cause_inference.p1b.actions import P1B_ACTION_SPECS
from bug_cause_inference.p1b.dataset import LOCATION_CANDIDATES
from bug_cause_inference.p1b.models import P1BObservation
from bug_cause_inference.p1b.real_diff import generate_real_diff_checkout_tree


LEGACY_CATALOG_MODE = "legacy"
_LOCATION_CANDIDATE_SET = set(LOCATION_CANDIDATES)
_MODULE_NAMES = ("cart", "config", "discounts", "inventory", "shipping")
_IMPORT_LOCK = threading.RLock()
_NAMESPACE_COUNTER = itertools.count()


class PatchGroundedAdapterError(RuntimeError):
    """Raised when an isolated legacy checkout tree cannot be executed safely."""


class _GeneratedModuleAdapter:
    """Accept the legacy ``variant_id`` keyword without exposing it to generated code."""

    def __init__(self, module: ModuleType) -> None:
        self._module = module
        self._wrapped: dict[str, Any] = {}

    def __getattr__(self, name: str) -> Any:
        value = getattr(self._module, name)
        if not callable(value):
            return value
        if name not in self._wrapped:
            def call(*args: Any, __value: Any = value, **kwargs: Any) -> Any:
                kwargs.pop("variant_id", None)
                return __value(*args, **kwargs)

            self._wrapped[name] = call
        return self._wrapped[name]


def legacy_catalog_contract() -> dict[str, Any]:
    """Return the ordered, type-preserving legacy catalog contract input."""

    cases: list[dict[str, Any]] = []
    for test_id, test_case in p1b_execution.TEST_CASES.items():
        cases.append(
            {
                "test_id": test_id,
                "declared_test_id": test_case.test_id,
                "group": test_case.group,
                "expected": test_case.expected,
                "runner_input_semantics": "single_variant_id_selects_artifact_only",
                "runner_name": test_case.runner.__name__,
                "runner_signature": str(inspect.signature(test_case.runner)),
                "runner_source": inspect.getsource(test_case.runner).replace("\r\n", "\n"),
                "reproduction_input": test_case.reproduction_input,
                "evidence_tags": test_case.evidence_tags,
                "fix_intent_hints": test_case.fix_intent_hints,
            }
        )
    return {
        "catalog_mode": LEGACY_CATALOG_MODE,
        "cases": cases,
        "action_mapping": [
            {"action_id": action_id, "case_ids": case_ids}
            for action_id, case_ids in p1b_execution.ACTION_TEST_CASE_IDS.items()
        ],
        "traceback_probe_ids": p1b_execution.TRACEBACK_PROBE_IDS,
    }


def _normalize_generated_function(module_name: str, prefix: str, function_name: str) -> str | None:
    if not module_name.startswith(prefix):
        return None
    short_module = module_name.removeprefix(prefix)
    if not short_module or "." in short_module:
        return None
    candidate = f"{short_module}.{function_name}"
    return candidate if candidate in _LOCATION_CANDIDATE_SET else None


@contextmanager
def _generated_function_trace(prefix: str) -> Iterator[list[str]]:
    calls: list[str] = []
    previous_trace = sys.gettrace()

    def tracer(frame: Any, event: str, arg: Any) -> Any:
        if event == "call":
            function = _normalize_generated_function(
                frame.f_globals.get("__name__", ""),
                prefix,
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


def _unique(values: list[str]) -> list[str]:
    return sorted(set(values))


def _stack_functions(exc: BaseException, prefix: str) -> list[str]:
    functions: list[str] = []
    traceback = exc.__traceback__
    while traceback is not None:
        frame = traceback.tb_frame
        function = _normalize_generated_function(
            frame.f_globals.get("__name__", ""),
            prefix,
            frame.f_code.co_name,
        )
        if function:
            functions.append(function)
        traceback = traceback.tb_next
    return _unique(functions)


def _adapt_runner(runner: Any, modules: dict[str, ModuleType]) -> Any:
    globals_copy = dict(runner.__globals__)
    globals_copy.update(
        {name: _GeneratedModuleAdapter(modules[name]) for name in _MODULE_NAMES}
    )
    adapted = FunctionType(
        runner.__code__,
        globals_copy,
        runner.__name__,
        runner.__defaults__,
        runner.__closure__,
    )
    adapted.__kwdefaults__ = runner.__kwdefaults__
    return adapted


def _run_test_case(
    test_case: p1b_execution.ExecutionTestCase,
    variant_id: str,
    modules: dict[str, ModuleType],
    module_prefix: str,
) -> dict[str, Any]:
    exception_type: str | None = None
    stack_functions: list[str] = []
    runner = _adapt_runner(test_case.runner, modules)
    with _generated_function_trace(module_prefix) as calls:
        try:
            actual = runner(variant_id)
        except Exception as exc:  # noqa: BLE001 - canonical benchmark observation
            actual = f"{type(exc).__name__}: {exc}"
            exception_type = type(exc).__name__
            stack_functions = _stack_functions(exc, module_prefix)
    passed = exception_type is None and type(actual) is type(test_case.expected) and actual == test_case.expected
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


def _recorded_results(
    *,
    action_id: str,
    variant_id: str,
    context: p1b_execution.P1BExecutionContext,
    modules: dict[str, ModuleType],
    module_prefix: str,
) -> list[dict[str, Any]]:
    results = [
        _run_test_case(
            p1b_execution.TEST_CASES[test_id],
            variant_id,
            modules,
            module_prefix,
        )
        for test_id in p1b_execution.ACTION_TEST_CASE_IDS[action_id]
    ]
    return context.record(action_id, results)


def run_patch_grounded_legacy_action(
    *,
    variant_id: str,
    action_id: str,
    context: p1b_execution.P1BExecutionContext,
    modules: dict[str, ModuleType],
    module_prefix: str,
) -> P1BObservation:
    """Run one legacy action against generated modules without ground-truth input."""

    spec = P1B_ACTION_SPECS[action_id]
    if action_id == "inspect_recent_diff":
        return p1b_execution._inspect_recent_diff(
            variant_id=variant_id,
            action_id=action_id,
            cost=spec.cost,
            observation_type=spec.observation_type,
        )
    if action_id == "inspect_coverage_spectrum":
        observation = p1b_execution._inspect_coverage_spectrum(
            action_id=action_id,
            cost=spec.cost,
            observation_type=spec.observation_type,
            context=context,
        )
        return replace(observation, evidence_source="p2a_patch_grounded_legacy_catalog")
    if action_id == "inspect_traceback":
        results = context.failed_results()
        recordable = False
        if not results:
            results = context.record(
                action_id,
                [
                    _run_test_case(
                        p1b_execution.TEST_CASES[test_id],
                        variant_id,
                        modules,
                        module_prefix,
                    )
                    for test_id in p1b_execution.TRACEBACK_PROBE_IDS
                ],
            )
            recordable = True
        observation = p1b_execution._observation_from_results(
            action_id=action_id,
            cost=spec.cost,
            observation_type=spec.observation_type,
            results=results,
            recordable=recordable,
        )
        return replace(observation, evidence_source="p2a_patch_grounded_legacy_catalog")
    if action_id not in p1b_execution.ACTION_TEST_CASE_IDS:
        raise PatchGroundedAdapterError(
            f"Action {action_id!r} is outside the frozen legacy catalog."
        )
    observation = p1b_execution._observation_from_results(
        action_id=action_id,
        cost=spec.cost,
        observation_type=spec.observation_type,
        results=_recorded_results(
            action_id=action_id,
            variant_id=variant_id,
            context=context,
            modules=modules,
            module_prefix=module_prefix,
        ),
    )
    return replace(observation, evidence_source="p2a_patch_grounded_legacy_catalog")


@contextmanager
def isolated_legacy_checkout(
    variant_id: str,
    *,
    work_root: Path | None = None,
) -> Iterator[tuple[dict[str, ModuleType], str]]:
    """Yield generated checkout modules imported under a private P2a namespace."""

    with _IMPORT_LOCK:
        temporary: tempfile.TemporaryDirectory[str] | None = None
        if work_root is None:
            temporary = tempfile.TemporaryDirectory(prefix="p2a-legacy-adapter-")
            root = Path(temporary.name)
        else:
            root = work_root
            root.mkdir(parents=True, exist_ok=True)
        namespace = f"_p2a_generated_{next(_NAMESPACE_COUNTER):08x}"
        destination = root / namespace
        module_prefix = f"{namespace}.checkout."
        try:
            generate_real_diff_checkout_tree(variant_id, destination)
            (destination / "__init__.py").write_text("", encoding="utf-8")
            sys.path.insert(0, str(root))
            modules = {
                name: importlib.import_module(f"{namespace}.checkout.{name}")
                for name in _MODULE_NAMES
            }
            yield modules, module_prefix
        finally:
            if str(root) in sys.path:
                sys.path.remove(str(root))
            for name in [key for key in sys.modules if key == namespace or key.startswith(f"{namespace}.")]:
                sys.modules.pop(name, None)
            importlib.invalidate_caches()
            if temporary is not None:
                temporary.cleanup()
            elif destination.exists():
                shutil.rmtree(destination)
