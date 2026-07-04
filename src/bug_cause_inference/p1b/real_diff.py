"""P1b real-diff artifact generator and validator."""

from __future__ import annotations

import argparse
import ast
import importlib
import json
import re
import shutil
import sys
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from types import ModuleType
from typing import Any

from bug_cause_inference.p1b.dataset import load_p1b_variants


ARTIFACT_ROOT = Path(__file__).resolve().parent / "artifacts" / "real_diff"
MANIFEST_FILENAME = "manifest.json"
CHECKOUT_MODULE_NAMES = ("config", "discounts", "shipping", "inventory", "cart")
FORBIDDEN_MANIFEST_FIELDS = {
    "true_cause_category",
    "target_location",
    "fix_intent_category",
    "primary_discovery_action",
    "secondary_discovery_actions",
    "distractor_locations",
}
FORBIDDEN_SOURCE_TOKENS = ("P1B-BUG", "P1B-CLEAN", "variant_id")


class RealDiffArtifactError(ValueError):
    """Raised when a real-diff artifact cannot be generated or validated."""


@dataclass(frozen=True)
class _PatchHunk:
    old_start: int
    old_count: int
    section: str
    lines: tuple[str, ...]


@dataclass(frozen=True)
class _FilePatch:
    path: str
    hunks: tuple[_PatchHunk, ...]


@dataclass(frozen=True)
class _FunctionSpan:
    name: str
    start: int
    end: int


_HUNK_RE = re.compile(
    r"^@@ -(?P<old_start>\d+)(?:,(?P<old_count>\d+))? "
    r"\+(?P<new_start>\d+)(?:,(?P<new_count>\d+))? @@(?: (?P<section>.*))?$"
)
_FUNCTION_SECTION_RE = re.compile(r"\b(?:async\s+def|def)\s+(?P<name>[A-Za-z_]\w*)\s*\(")


def _artifact_root(artifact_root: Path | None = None) -> Path:
    return artifact_root or ARTIFACT_ROOT


def _manifest_path(artifact_root: Path | None = None) -> Path:
    return _artifact_root(artifact_root) / MANIFEST_FILENAME


def load_real_diff_manifest(artifact_root: Path | None = None) -> dict[str, Any]:
    """Load the P1b real-diff manifest."""

    return json.loads(_manifest_path(artifact_root).read_text(encoding="utf-8"))


def _iter_mapping_keys(value: Any) -> Iterator[str]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from _iter_mapping_keys(child)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_mapping_keys(item)


def _validate_relative_posix_path(path: str) -> None:
    parsed = PurePosixPath(path)
    if parsed.is_absolute() or not parsed.parts or ".." in parsed.parts:
        raise RealDiffArtifactError(f"Unsafe artifact path: {path!r}")


def validate_real_diff_manifest_schema(manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    """Validate the manifest shape without reading ground-truth labels."""

    manifest = load_real_diff_manifest() if manifest is None else manifest
    forbidden = sorted(set(_iter_mapping_keys(manifest)) & FORBIDDEN_MANIFEST_FIELDS)
    if forbidden:
        raise RealDiffArtifactError(f"Manifest contains forbidden metadata fields: {forbidden}")

    required_top_level = {"schema_version", "baseline_id", "baseline_root", "patch_root", "variants"}
    missing = sorted(required_top_level - set(manifest))
    if missing:
        raise RealDiffArtifactError(f"Manifest is missing required fields: {missing}")
    if manifest["schema_version"] != 1:
        raise RealDiffArtifactError(f"Unsupported manifest schema_version: {manifest['schema_version']!r}")
    if not isinstance(manifest["variants"], list):
        raise RealDiffArtifactError("Manifest variants must be a list.")

    _validate_relative_posix_path(manifest["baseline_root"])
    _validate_relative_posix_path(manifest["patch_root"])

    required_variant_fields = {"variant_id", "patch_path", "expected_changed_files", "review_note"}
    seen_variant_ids: set[str] = set()
    for index, entry in enumerate(manifest["variants"]):
        if not isinstance(entry, dict):
            raise RealDiffArtifactError(f"Manifest variant entry {index} must be an object.")
        unexpected = sorted(set(entry) - required_variant_fields)
        if unexpected:
            raise RealDiffArtifactError(f"Manifest variant {index} has unexpected fields: {unexpected}")
        missing_entry_fields = sorted(required_variant_fields - set(entry))
        if missing_entry_fields:
            raise RealDiffArtifactError(f"Manifest variant {index} is missing fields: {missing_entry_fields}")
        variant_id = entry["variant_id"]
        if not isinstance(variant_id, str) or not variant_id:
            raise RealDiffArtifactError(f"Manifest variant {index} has invalid variant_id.")
        if variant_id in seen_variant_ids:
            raise RealDiffArtifactError(f"Duplicate manifest variant_id: {variant_id}")
        seen_variant_ids.add(variant_id)
        if not isinstance(entry["patch_path"], str):
            raise RealDiffArtifactError(f"{variant_id} patch_path must be a string.")
        _validate_relative_posix_path(entry["patch_path"])
        if not isinstance(entry["expected_changed_files"], list) or not all(
            isinstance(item, str) for item in entry["expected_changed_files"]
        ):
            raise RealDiffArtifactError(f"{variant_id} expected_changed_files must be a string list.")
        for changed_file in entry["expected_changed_files"]:
            _validate_relative_posix_path(changed_file)
        if not isinstance(entry["review_note"], str) or not entry["review_note"]:
            raise RealDiffArtifactError(f"{variant_id} review_note must be a non-empty string.")

    return manifest


def _manifest_entry_by_id(manifest: dict[str, Any], variant_id: str) -> dict[str, Any]:
    for entry in manifest["variants"]:
        if entry["variant_id"] == variant_id:
            return entry
    raise RealDiffArtifactError(f"Unknown real-diff variant_id: {variant_id}")


def _normalize_patch_path(path: str) -> str:
    if path.startswith("a/") or path.startswith("b/"):
        path = path[2:]
    _validate_relative_posix_path(path)
    if not path.startswith("checkout/"):
        raise RealDiffArtifactError(f"Patch path must stay under checkout/: {path!r}")
    return path


def _parse_unified_patch(patch_text: str) -> tuple[_FilePatch, ...]:
    lines = patch_text.splitlines()
    file_patches: list[_FilePatch] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith("diff --git ") or not line:
            index += 1
            continue
        if not line.startswith("--- "):
            raise RealDiffArtifactError(f"Expected unified diff file header, got: {line!r}")

        index += 1
        if index >= len(lines) or not lines[index].startswith("+++ "):
            raise RealDiffArtifactError("Unified diff is missing +++ file header.")
        path = _normalize_patch_path(lines[index][4:].strip())
        index += 1

        hunks: list[_PatchHunk] = []
        while index < len(lines):
            line = lines[index]
            if line.startswith("diff --git ") or line.startswith("--- "):
                break
            match = _HUNK_RE.match(line)
            if not match:
                raise RealDiffArtifactError(f"Expected unified diff hunk header, got: {line!r}")
            old_start = int(match.group("old_start"))
            old_count = int(match.group("old_count") or "1")
            section = match.group("section") or ""
            index += 1
            hunk_lines: list[str] = []
            while index < len(lines):
                hunk_line = lines[index]
                if hunk_line.startswith("@@ ") or hunk_line.startswith("--- ") or hunk_line.startswith("diff --git "):
                    break
                if hunk_line == r"\ No newline at end of file":
                    index += 1
                    continue
                if not hunk_line or hunk_line[0] not in {" ", "-", "+"}:
                    raise RealDiffArtifactError(f"Invalid unified diff hunk line: {hunk_line!r}")
                hunk_lines.append(hunk_line)
                index += 1
            hunks.append(
                _PatchHunk(
                    old_start=old_start,
                    old_count=old_count,
                    section=section,
                    lines=tuple(hunk_lines),
                )
            )
        file_patches.append(_FilePatch(path=path, hunks=tuple(hunks)))
    if not file_patches:
        raise RealDiffArtifactError("Patch contains no file changes.")
    return tuple(file_patches)


def changed_files_in_patch(patch_text: str) -> list[str]:
    """Return changed files listed by a unified diff."""

    return sorted({file_patch.path for file_patch in _parse_unified_patch(patch_text)})


def _function_spans(source_text: str) -> list[_FunctionSpan]:
    tree = ast.parse(source_text)
    spans: list[_FunctionSpan] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            spans.append(
                _FunctionSpan(
                    name=node.name,
                    start=node.lineno,
                    end=getattr(node, "end_lineno", node.lineno),
                )
            )
    return spans


def _module_name_from_patch_path(patch_path: str) -> str | None:
    parsed = PurePosixPath(patch_path)
    if parsed.suffix != ".py" or parsed.name == "__init__.py":
        return None
    parts = parsed.parts
    if len(parts) < 2 or parts[0] != "checkout":
        return None
    return ".".join((*parts[1:-1], parsed.stem))


def _hunk_old_line_range(hunk: _PatchHunk) -> tuple[int, int]:
    old_count = max(hunk.old_count, 1)
    return hunk.old_start, hunk.old_start + old_count - 1


def _ranges_overlap(left: tuple[int, int], right: tuple[int, int]) -> bool:
    return left[0] <= right[1] and right[0] <= left[1]


def changed_functions_in_patch(patch_text: str, *, tree_root: Path | None = None) -> list[str]:
    """Return checkout functions whose source spans overlap a unified diff."""

    root = tree_root or ARTIFACT_ROOT / "baseline"
    changed_functions: set[str] = set()
    for file_patch in _parse_unified_patch(patch_text):
        module_name = _module_name_from_patch_path(file_patch.path)
        if module_name is None:
            continue
        source_path = _checkout_file_path(root, file_patch.path)
        spans = _function_spans(source_path.read_text(encoding="utf-8"))
        for hunk in file_patch.hunks:
            hunk_range = _hunk_old_line_range(hunk)
            matched = False
            for span in spans:
                if _ranges_overlap(hunk_range, (span.start, span.end)):
                    changed_functions.add(f"{module_name}.{span.name}")
                    matched = True
            if not matched:
                section_match = _FUNCTION_SECTION_RE.search(hunk.section)
                if section_match:
                    changed_functions.add(f"{module_name}.{section_match.group('name')}")
    return sorted(changed_functions)


def diff_excerpt(patch_text: str, *, max_lines: int = 16) -> str:
    """Return a compact excerpt for observation payloads and reports."""

    return "\n".join(patch_text.strip("\n").splitlines()[:max_lines])


def inspect_real_diff_artifact(
    variant_id: str,
    *,
    artifact_root: Path | None = None,
    max_excerpt_lines: int = 16,
) -> dict[str, Any]:
    """Return observation-ready data for one real-diff variant artifact."""

    root = _artifact_root(artifact_root)
    manifest = validate_real_diff_manifest_schema(load_real_diff_manifest(root))
    entry = _manifest_entry_by_id(manifest, variant_id)
    patch_path = root / entry["patch_path"]
    patch_text = patch_path.read_text(encoding="utf-8")
    changed_files = changed_files_in_patch(patch_text)
    _validate_patch_expected_files(entry, changed_files)
    return {
        "variant_id": variant_id,
        "patch_path": entry["patch_path"],
        "changed_files": changed_files,
        "changed_functions": changed_functions_in_patch(patch_text, tree_root=root / "baseline"),
        "diff_excerpt": diff_excerpt(patch_text, max_lines=max_excerpt_lines),
    }


def _checkout_file_path(tree_root: Path, patch_path: str) -> Path:
    _validate_relative_posix_path(patch_path)
    target = tree_root / Path(*PurePosixPath(patch_path).parts)
    resolved_root = tree_root.resolve()
    resolved_target = target.resolve()
    if resolved_root != resolved_target and resolved_root not in resolved_target.parents:
        raise RealDiffArtifactError(f"Patch target escapes generated tree: {patch_path!r}")
    return target


def _old_hunk_lines(hunk: _PatchHunk) -> list[str]:
    return [line[1:] for line in hunk.lines if line.startswith((" ", "-"))]


def _matches_at(lines: list[str], index: int, expected: list[str]) -> bool:
    if index < 0 or index + len(expected) > len(lines):
        return False
    return lines[index : index + len(expected)] == expected


def _find_hunk_index(original_lines: list[str], source_index: int, hunk: _PatchHunk) -> int:
    old_lines = _old_hunk_lines(hunk)
    expected_index = hunk.old_start - 1
    if _matches_at(original_lines, expected_index, old_lines) and expected_index >= source_index:
        return expected_index
    if not old_lines:
        return max(expected_index, source_index)
    candidates = [
        index
        for index in range(source_index, len(original_lines) - len(old_lines) + 1)
        if _matches_at(original_lines, index, old_lines)
    ]
    if len(candidates) == 1:
        return candidates[0]
    raise RealDiffArtifactError(f"Hunk context did not match uniquely; candidates={candidates}")


def _apply_file_patch(tree_root: Path, file_patch: _FilePatch) -> None:
    target = _checkout_file_path(tree_root, file_patch.path)
    if not target.exists():
        raise RealDiffArtifactError(f"Patch target does not exist: {file_patch.path}")
    original_lines = target.read_text(encoding="utf-8").splitlines()
    output_lines: list[str] = []
    source_index = 0

    for hunk in file_patch.hunks:
        hunk_index = _find_hunk_index(original_lines, source_index, hunk)
        if hunk_index < source_index:
            raise RealDiffArtifactError(f"Overlapping hunk in {file_patch.path}")
        output_lines.extend(original_lines[source_index:hunk_index])
        source_index = hunk_index
        for hunk_line in hunk.lines:
            marker = hunk_line[0]
            content = hunk_line[1:]
            if marker == " ":
                if source_index >= len(original_lines) or original_lines[source_index] != content:
                    raise RealDiffArtifactError(f"Context mismatch applying {file_patch.path}: {content!r}")
                output_lines.append(content)
                source_index += 1
            elif marker == "-":
                if source_index >= len(original_lines) or original_lines[source_index] != content:
                    raise RealDiffArtifactError(f"Removal mismatch applying {file_patch.path}: {content!r}")
                source_index += 1
            elif marker == "+":
                output_lines.append(content)
    output_lines.extend(original_lines[source_index:])
    target.write_text("\n".join(output_lines) + "\n", encoding="utf-8")


def apply_unified_patch(tree_root: Path, patch_text: str) -> list[str]:
    """Apply a small unified diff to a generated checkout tree."""

    file_patches = _parse_unified_patch(patch_text)
    for file_patch in file_patches:
        _apply_file_patch(tree_root, file_patch)
    return sorted({file_patch.path for file_patch in file_patches})


def _scan_source_tree_for_forbidden_tokens(tree_root: Path) -> list[str]:
    findings: list[str] = []
    for path in sorted(tree_root.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        for token in FORBIDDEN_SOURCE_TOKENS:
            if token in text:
                findings.append(f"{path.relative_to(tree_root).as_posix()}: {token}")
    return findings


@contextmanager
def generated_checkout_imports(tree_root: Path) -> Iterator[dict[str, ModuleType]]:
    """Temporarily import generated checkout modules from ``tree_root``."""

    module_names = ["checkout", *(f"checkout.{name}" for name in CHECKOUT_MODULE_NAMES)]
    saved_modules = {name: sys.modules[name] for name in module_names if name in sys.modules}
    original_sys_path = list(sys.path)
    for name in module_names:
        sys.modules.pop(name, None)
    sys.path.insert(0, str(tree_root))
    try:
        imported = {name: importlib.import_module(f"checkout.{name}") for name in CHECKOUT_MODULE_NAMES}
        yield imported
    finally:
        for name in module_names:
            sys.modules.pop(name, None)
        sys.modules.update(saved_modules)
        sys.path[:] = original_sys_path


def _assert_generated_checkout_importable(tree_root: Path) -> None:
    with generated_checkout_imports(tree_root):
        return


def _validate_manifest_variant_ids(manifest: dict[str, Any]) -> None:
    manifest_ids = {entry["variant_id"] for entry in manifest["variants"]}
    dataset_ids = {variant.variant_id for variant in load_p1b_variants()}
    if manifest_ids != dataset_ids:
        missing = sorted(dataset_ids - manifest_ids)
        extra = sorted(manifest_ids - dataset_ids)
        raise RealDiffArtifactError(f"Manifest variant IDs differ from dataset. missing={missing}, extra={extra}")


def _validate_patch_expected_files(entry: dict[str, Any], changed_files: list[str]) -> None:
    expected = sorted(entry["expected_changed_files"])
    if changed_files != expected:
        raise RealDiffArtifactError(
            f"{entry['variant_id']} changed files {changed_files} do not match manifest expected {expected}"
        )


def generate_real_diff_checkout_tree(
    variant_id: str,
    destination: Path,
    *,
    artifact_root: Path | None = None,
    manifest: dict[str, Any] | None = None,
) -> Path:
    """Generate one variant checkout tree under ``destination``."""

    root = _artifact_root(artifact_root)
    manifest = validate_real_diff_manifest_schema(load_real_diff_manifest(root) if manifest is None else manifest)
    entry = _manifest_entry_by_id(manifest, variant_id)
    baseline_source = root / manifest["baseline_root"]
    if not baseline_source.exists():
        raise RealDiffArtifactError(f"Baseline source tree does not exist: {baseline_source}")

    destination.mkdir(parents=True, exist_ok=True)
    checkout_destination = destination / "checkout"
    if checkout_destination.exists():
        raise RealDiffArtifactError(f"Generated checkout tree already exists: {checkout_destination}")
    shutil.copytree(baseline_source, checkout_destination)

    patch_path = root / entry["patch_path"]
    patch_text = patch_path.read_text(encoding="utf-8")
    changed_files = apply_unified_patch(destination, patch_text)
    _validate_patch_expected_files(entry, changed_files)
    return destination


def _validate_real_diff_artifacts_in_work_root(
    work_root: Path,
    *,
    artifact_root: Path | None = None,
) -> dict[str, Any]:
    root = _artifact_root(artifact_root)
    manifest = validate_real_diff_manifest_schema(load_real_diff_manifest(root))
    _validate_manifest_variant_ids(manifest)

    baseline_root = root / manifest["baseline_root"]
    baseline_findings = _scan_source_tree_for_forbidden_tokens(baseline_root)
    if baseline_findings:
        raise RealDiffArtifactError(f"Baseline source contains forbidden tokens: {baseline_findings}")

    validated_variants: list[dict[str, Any]] = []
    for entry in manifest["variants"]:
        variant_root = work_root / entry["variant_id"]
        generated_root = generate_real_diff_checkout_tree(
            entry["variant_id"],
            variant_root,
            artifact_root=root,
            manifest=manifest,
        )
        source_findings = _scan_source_tree_for_forbidden_tokens(generated_root)
        if source_findings:
            raise RealDiffArtifactError(
                f"{entry['variant_id']} generated source contains forbidden tokens: {source_findings}"
            )
        _assert_generated_checkout_importable(generated_root)
        patch_text = (root / entry["patch_path"]).read_text(encoding="utf-8")
        changed_files = changed_files_in_patch(patch_text)
        _validate_patch_expected_files(entry, changed_files)
        validated_variants.append(
            {
                "variant_id": entry["variant_id"],
                "patch_path": entry["patch_path"],
                "changed_files": changed_files,
            }
        )

    return {
        "schema_version": manifest["schema_version"],
        "baseline_id": manifest["baseline_id"],
        "variant_count": len(validated_variants),
        "validated_variants": validated_variants,
    }


def validate_real_diff_artifacts(
    *,
    artifact_root: Path | None = None,
    work_root: Path | None = None,
) -> dict[str, Any]:
    """Validate all P1b real-diff artifacts and generated checkout modules."""

    if work_root is not None:
        work_root.mkdir(parents=True, exist_ok=True)
        return _validate_real_diff_artifacts_in_work_root(work_root, artifact_root=artifact_root)
    with tempfile.TemporaryDirectory(prefix="p1b-real-diff-") as temporary:
        return _validate_real_diff_artifacts_in_work_root(Path(temporary), artifact_root=artifact_root)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate or validate P1b real-diff checkout artifacts.")
    parser.add_argument("--validate", action="store_true", help="Validate every real-diff artifact.")
    parser.add_argument("--variant-id", help="Variant ID to generate.")
    parser.add_argument("--output", type=Path, help="Destination directory for one generated checkout tree.")
    parser.add_argument("--work-root", type=Path, help="Optional validation work directory.")
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.validate:
        summary = validate_real_diff_artifacts(work_root=args.work_root)
        print(json.dumps(summary, indent=2), end="\n")
        return
    if args.variant_id and args.output:
        generated = generate_real_diff_checkout_tree(args.variant_id, args.output)
        print(str(generated))
        return
    parser.error("Use --validate or provide both --variant-id and --output.")


if __name__ == "__main__":
    main()
