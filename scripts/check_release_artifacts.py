#!/usr/bin/env python3
"""Fail-closed validation for the repository's wheel and sdist boundary."""

from __future__ import annotations

import argparse
import base64
import binascii
import csv
import hashlib
import io
import json
import re
import stat
import sys
import tarfile
import unicodedata
import zipfile
from dataclasses import dataclass
from email import policy
from email.parser import BytesParser
from pathlib import Path, PurePosixPath
from typing import Iterable


BOUNDARY_ID = "repository_only_p2_research_evidence_v1"
PROJECT_NAME = "bug-cause-inference-game"
NORMALIZED_NAME = "bug_cause_inference_game"
VERSION = "0.1.0"
SDIST_ROOT = f"{NORMALIZED_NAME}-{VERSION}"
DIST_INFO = f"{NORMALIZED_NAME}-{VERSION}.dist-info"
EGG_INFO = f"src/{NORMALIZED_NAME}.egg-info"
SUMMARY = "A Bayesian active bug investigation prototype for synthetic bug-cause cases."
REPOSITORY_URL = "https://github.com/guriguri215-lang/bug-cause-inference-game"

ROOT_MODULES = (
    "__init__.py",
    "analysis.py",
    "bayes.py",
    "cli.py",
    "evaluation.py",
    "likelihoods.py",
    "models.py",
    "policies.py",
    "reports.py",
    "synthetic_cases.py",
)
P1B_MODULES = (
    "__init__.py",
    "actions.py",
    "dataset.py",
    "evaluation.py",
    "execution.py",
    "models.py",
    "policies.py",
    "real_diff.py",
    "reports.py",
)
P1B_CHECKOUT_MODULES = (
    "__init__.py",
    "cart.py",
    "config.py",
    "discounts.py",
    "inventory.py",
    "shipping.py",
)
P1C_MODULES = ("__init__.py", "evaluation.py", "labels.py")
P1D_MODULES = (
    "__init__.py",
    "evaluation.py",
    "p1d2_evaluation.py",
    "p1d3a_evaluation.py",
    "p1d3b_evaluation.py",
)
P1B_BASELINE_MODULES = P1B_CHECKOUT_MODULES
P1B_PATCHES = tuple(
    [f"P1B-BUG-{index:03d}.patch" for index in range(1, 21)]
    + [f"P1B-CLEAN-{index:03d}.patch" for index in range(21, 26)]
)

WHEEL_METADATA_MEMBERS = frozenset(
    {
        f"{DIST_INFO}/licenses/LICENSE",
        f"{DIST_INFO}/METADATA",
        f"{DIST_INFO}/WHEEL",
        f"{DIST_INFO}/entry_points.txt",
        f"{DIST_INFO}/top_level.txt",
        f"{DIST_INFO}/RECORD",
    }
)
SDIST_ROOT_FILES = frozenset(
    {"LICENSE", "MANIFEST.in", "PKG-INFO", "README.md", "pyproject.toml", "setup.cfg"}
)
SDIST_EGG_INFO_FILES = frozenset(
    {
        f"{EGG_INFO}/PKG-INFO",
        f"{EGG_INFO}/SOURCES.txt",
        f"{EGG_INFO}/dependency_links.txt",
        f"{EGG_INFO}/entry_points.txt",
        f"{EGG_INFO}/top_level.txt",
    }
)

FORBIDDEN_SEGMENTS = frozenset(
    {
        ".aws",
        ".cache",
        ".config",
        ".git",
        ".github",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".ssh",
        ".tox",
        ".venv",
        "__pycache__",
        "appdata",
        "build",
        "claude_review",
        "credentials",
        "devlog",
        "dist",
        "docs",
        "examples",
        "home",
        "secrets",
        "temp",
        "tests",
        "tmp",
        "users",
        "venv",
    }
)
PRIVATE_SUFFIXES = (".env", ".key", ".p12", ".pem")
WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:")
P2_SEGMENT = re.compile(r"^p2[a-h]$", re.IGNORECASE)


class ArtifactBoundaryError(ValueError):
    """Raised when a built artifact violates the distribution contract."""


@dataclass(frozen=True)
class WheelAudit:
    path: Path
    sha256: str
    members: frozenset[str]
    comparable_bytes: dict[str, bytes]


@dataclass(frozen=True)
class SdistAudit:
    path: Path
    sha256: str
    file_members: frozenset[str]
    directory_members: frozenset[str]


def _fail(message: str) -> None:
    raise ArtifactBoundaryError(message)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


def expected_source_members(root: Path) -> frozenset[str]:
    """Return the exact source/data files allowed in advertised distributions."""

    members = {
        *(f"src/bug_cause_inference/{name}" for name in ROOT_MODULES),
        *(f"src/bug_cause_inference/p1b/{name}" for name in P1B_MODULES),
        *(f"src/bug_cause_inference/p1b/checkout/{name}" for name in P1B_CHECKOUT_MODULES),
        *(f"src/bug_cause_inference/p1c/{name}" for name in P1C_MODULES),
        *(f"src/bug_cause_inference/p1d/{name}" for name in P1D_MODULES),
        "src/bug_cause_inference/p1b/artifacts/real_diff/manifest.json",
        *(
            f"src/bug_cause_inference/p1b/artifacts/real_diff/baseline/checkout/{name}"
            for name in P1B_BASELINE_MODULES
        ),
        *(
            f"src/bug_cause_inference/p1b/artifacts/real_diff/patches/{name}"
            for name in P1B_PATCHES
        ),
    }
    if len(members) != 65:
        _fail(f"internal source contract count changed: expected 65, got {len(members)}")
    for relative in sorted(members):
        path = root / relative
        if path.is_symlink() or not path.is_file():
            _fail(f"required source member is missing or not a regular file: {relative}")
    return frozenset(members)


def expected_wheel_payload(root: Path) -> frozenset[str]:
    return frozenset(
        member.removeprefix("src/") for member in expected_source_members(root)
    )


def expected_sdist_files(root: Path) -> frozenset[str]:
    relative = set(expected_source_members(root))
    relative.update(SDIST_ROOT_FILES)
    relative.update(SDIST_EGG_INFO_FILES)
    return frozenset(f"{SDIST_ROOT}/{member}" for member in relative)


def _expected_directories(files: Iterable[str]) -> frozenset[str]:
    directories: set[str] = set()
    for member in files:
        for parent in PurePosixPath(member).parents:
            value = parent.as_posix()
            if value == ".":
                break
            directories.add(value)
    return frozenset(directories)


def validate_member_names(names: Iterable[str], *, artifact: str) -> tuple[str, ...]:
    """Validate normalized POSIX names, duplicates, collisions, and private paths."""

    observed: set[str] = set()
    folded: dict[str, str] = {}
    ordered: list[str] = []
    for name in names:
        if not name or "\x00" in name:
            _fail(f"{artifact}: empty or NUL-containing member name")
        if "\\" in name:
            _fail(f"{artifact}: backslash is not a normalized POSIX separator: {name!r}")
        if name.startswith("/") or WINDOWS_DRIVE.match(name):
            _fail(f"{artifact}: absolute member path: {name!r}")
        if name.endswith("/"):
            _fail(f"{artifact}: non-normalized trailing slash: {name!r}")
        path = PurePosixPath(name)
        if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
            _fail(f"{artifact}: unsafe member path: {name!r}")
        normalized = unicodedata.normalize("NFKC", name).casefold()
        if name in observed:
            _fail(f"{artifact}: duplicate member: {name!r}")
        if normalized in folded:
            _fail(
                f"{artifact}: case/Unicode collision: {folded[normalized]!r} and {name!r}"
            )
        observed.add(name)
        folded[normalized] = name
        ordered.append(name)

        for part in path.parts:
            lowered = unicodedata.normalize("NFKC", part).casefold()
            if lowered in FORBIDDEN_SEGMENTS:
                _fail(f"{artifact}: forbidden local/private segment {part!r}: {name!r}")
            if P2_SEGMENT.fullmatch(lowered):
                _fail(f"{artifact}: repository-only P2 package leaked: {name!r}")
            if lowered.startswith(".") or lowered.endswith(PRIVATE_SUFFIXES):
                _fail(f"{artifact}: hidden/private-looking member: {name!r}")
    return tuple(ordered)


def _validate_zip_info(info: zipfile.ZipInfo, *, artifact: str) -> None:
    if info.is_dir():
        _fail(f"{artifact}: wheel must not contain directory entries: {info.filename!r}")
    if info.flag_bits & 0x1:
        _fail(f"{artifact}: encrypted ZIP member: {info.filename!r}")
    mode = (info.external_attr >> 16) & 0xFFFF
    if stat.S_IFMT(mode) == stat.S_IFLNK:
        _fail(f"{artifact}: symlink ZIP member: {info.filename!r}")
    if mode & 0o111:
        _fail(f"{artifact}: executable ZIP member: {info.filename!r}")


def _validate_tar_info(info: tarfile.TarInfo, *, artifact: str) -> None:
    if not (info.isfile() or info.isdir()):
        _fail(f"{artifact}: link/device/FIFO member is forbidden: {info.name!r}")
    if info.isfile() and info.mode & 0o111:
        _fail(f"{artifact}: executable tar member: {info.name!r}")


def _metadata_headers(data: bytes, *, artifact: str, root: Path) -> dict[str, object]:
    message = BytesParser(policy=policy.default).parsebytes(data)
    exact_single = {
        "Metadata-Version": "2.4",
        "Name": PROJECT_NAME,
        "Version": VERSION,
        "Summary": SUMMARY,
        "Author": "gurig",
        "License-Expression": "MIT",
        "Requires-Python": ">=3.10",
        "Description-Content-Type": "text/markdown",
    }
    for header, expected in exact_single.items():
        values = message.get_all(header, [])
        if values != [expected]:
            _fail(f"{artifact}: {header} must be exactly {expected!r}, got {values!r}")

    expected_multi = {
        "Project-URL": [f"Repository, {REPOSITORY_URL}"],
        "License-File": ["LICENSE"],
        "Dynamic": ["license-file"],
        "Classifier": [
            "Development Status :: 3 - Alpha",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3.10",
            "Topic :: Software Development :: Testing",
        ],
    }
    for header, expected in expected_multi.items():
        values = message.get_all(header, [])
        if values != expected:
            _fail(f"{artifact}: unexpected {header} values: {values!r}")
    if message.get_all("Requires-Dist", []):
        _fail(f"{artifact}: unexpected runtime dependencies in metadata")

    normalized_data = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    _, separator, body = normalized_data.partition(b"\n\n")
    if not separator:
        _fail(f"{artifact}: metadata has no header/body separator")
    expected_readme = (root / "README.md").read_bytes()
    normalized_readme = expected_readme.replace(b"\r\n", b"\n").replace(
        b"\r", b"\n"
    )
    if body.rstrip(b"\n") != normalized_readme.rstrip(b"\n"):
        _fail(f"{artifact}: embedded README differs from repository README.md")
    return {
        "name": message["Name"],
        "version": message["Version"],
        "requires_python": message["Requires-Python"],
        "repository_url": message.get_all("Project-URL", [])[0],
        "license": message["License-Expression"],
    }


def _validate_wheel_metadata(
    archive: zipfile.ZipFile, *, artifact: str, root: Path
) -> dict[str, object]:
    metadata = _metadata_headers(
        archive.read(f"{DIST_INFO}/METADATA"), artifact=artifact, root=root
    )
    wheel_message = BytesParser(policy=policy.default).parsebytes(
        archive.read(f"{DIST_INFO}/WHEEL")
    )
    if wheel_message.get_all("Wheel-Version", []) != ["1.0"]:
        _fail(f"{artifact}: Wheel-Version must be 1.0")
    generators = wheel_message.get_all("Generator", [])
    if len(generators) != 1 or not generators[0].startswith("setuptools ("):
        _fail(f"{artifact}: unexpected wheel generator: {generators!r}")
    if wheel_message.get_all("Root-Is-Purelib", []) != ["true"]:
        _fail(f"{artifact}: Root-Is-Purelib must be true")
    if wheel_message.get_all("Tag", []) != ["py3-none-any"]:
        _fail(f"{artifact}: wheel tag must be exactly py3-none-any")

    entry_points = archive.read(f"{DIST_INFO}/entry_points.txt").decode("utf-8")
    expected_entry_points = (
        "[console_scripts]\n"
        "bug-cause-inference = bug_cause_inference.cli:main\n"
    )
    if entry_points.replace("\r\n", "\n") != expected_entry_points:
        _fail(f"{artifact}: console entry point contract changed")
    if archive.read(f"{DIST_INFO}/top_level.txt") != b"bug_cause_inference\n":
        _fail(f"{artifact}: top_level.txt contract changed")
    if archive.read(f"{DIST_INFO}/licenses/LICENSE") != (root / "LICENSE").read_bytes():
        _fail(f"{artifact}: LICENSE bytes differ from repository LICENSE")
    return metadata


def _validate_record(archive: zipfile.ZipFile, *, artifact: str) -> None:
    record_name = f"{DIST_INFO}/RECORD"
    rows = list(
        csv.reader(
            io.StringIO(
                archive.read(record_name).decode("utf-8"), newline=""
            )
        )
    )
    if any(len(row) != 3 for row in rows):
        _fail(f"{artifact}: RECORD must have exactly three columns per row")
    paths = [row[0] for row in rows]
    validate_member_names(paths, artifact=f"{artifact} RECORD")
    if set(paths) != set(archive.namelist()):
        _fail(f"{artifact}: RECORD member set differs from wheel member set")
    for path, encoded_hash, encoded_size in rows:
        if path == record_name:
            if encoded_hash or encoded_size:
                _fail(f"{artifact}: RECORD self-row hash and size must be empty")
            continue
        data = archive.read(path)
        if not encoded_hash.startswith("sha256="):
            _fail(f"{artifact}: RECORD uses a non-SHA-256 hash for {path!r}")
        token = encoded_hash.removeprefix("sha256=")
        if re.fullmatch(r"[A-Za-z0-9_-]{43}", token) is None:
            _fail(f"{artifact}: invalid RECORD hash encoding for {path!r}")
        try:
            observed_hash = base64.b64decode(
                token + "=", altchars=b"-_", validate=True
            )
        except (ValueError, binascii.Error) as error:
            raise ArtifactBoundaryError(
                f"{artifact}: invalid RECORD hash encoding for {path!r}"
            ) from error
        canonical_token = base64.urlsafe_b64encode(observed_hash).rstrip(b"=").decode(
            "ascii"
        )
        if len(observed_hash) != hashlib.sha256().digest_size or canonical_token != token:
            _fail(f"{artifact}: invalid RECORD hash encoding for {path!r}")
        if observed_hash != hashlib.sha256(data).digest():
            _fail(f"{artifact}: RECORD hash mismatch for {path!r}")
        if encoded_size != str(len(data)):
            _fail(f"{artifact}: RECORD size mismatch for {path!r}")


def check_wheel(path: Path, *, root: Path) -> WheelAudit:
    path = path.resolve()
    if not path.is_file():
        _fail(f"wheel does not exist: {path}")
    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            names = validate_member_names(
                (info.filename for info in infos), artifact=f"wheel {path.name}"
            )
            for info in infos:
                _validate_zip_info(info, artifact=f"wheel {path.name}")

            expected_payload = expected_wheel_payload(root)
            expected = expected_payload | WHEEL_METADATA_MEMBERS
            if set(names) != expected:
                missing = sorted(expected - set(names))
                unexpected = sorted(set(names) - expected)
                _fail(
                    f"wheel {path.name}: member contract mismatch; "
                    f"missing={missing!r}, unexpected={unexpected!r}"
                )
            if len(names) != 71:
                _fail(f"wheel {path.name}: expected 71 files, got {len(names)}")

            for member in sorted(expected_payload):
                source = root / "src" / member
                if archive.read(member) != source.read_bytes():
                    _fail(f"wheel {path.name}: payload bytes differ for {member!r}")
            _validate_wheel_metadata(archive, artifact=f"wheel {path.name}", root=root)
            _validate_record(archive, artifact=f"wheel {path.name}")
            comparable = {
                name: archive.read(name)
                for name in names
                if name != f"{DIST_INFO}/RECORD"
            }
    except (OSError, zipfile.BadZipFile, KeyError, UnicodeError) as error:
        raise ArtifactBoundaryError(f"cannot validate wheel {path}: {error}") from error
    return WheelAudit(
        path=path,
        sha256=_sha256_file(path),
        members=frozenset(names),
        comparable_bytes=comparable,
    )


def _validate_sdist_metadata(
    archive: tarfile.TarFile, *, artifact: str, root: Path
) -> None:
    root_pkg_info = archive.extractfile(f"{SDIST_ROOT}/PKG-INFO")
    egg_pkg_info = archive.extractfile(f"{SDIST_ROOT}/{EGG_INFO}/PKG-INFO")
    if root_pkg_info is None or egg_pkg_info is None:
        _fail(f"{artifact}: PKG-INFO is not a regular file")
    root_bytes = root_pkg_info.read()
    egg_bytes = egg_pkg_info.read()
    if root_bytes != egg_bytes:
        _fail(f"{artifact}: root and egg-info PKG-INFO bytes differ")
    _metadata_headers(root_bytes, artifact=artifact, root=root)

    expected_text = {
        f"{SDIST_ROOT}/{EGG_INFO}/dependency_links.txt": "\n",
        f"{SDIST_ROOT}/{EGG_INFO}/entry_points.txt": (
            "[console_scripts]\n"
            "bug-cause-inference = bug_cause_inference.cli:main\n"
        ),
        f"{SDIST_ROOT}/{EGG_INFO}/top_level.txt": "bug_cause_inference\n",
        f"{SDIST_ROOT}/setup.cfg": (
            "[egg_info]\n"
            "tag_build = \n"
            "tag_date = 0\n\n"
        ),
    }
    for member, expected in expected_text.items():
        stream = archive.extractfile(member)
        if stream is None:
            _fail(f"{artifact}: metadata member is not a regular file: {member}")
        observed = stream.read().decode("utf-8").replace("\r\n", "\n")
        if observed != expected:
            _fail(f"{artifact}: metadata member contract changed: {member}")

    sources_member = f"{SDIST_ROOT}/{EGG_INFO}/SOURCES.txt"
    sources_stream = archive.extractfile(sources_member)
    if sources_stream is None:
        _fail(f"{artifact}: SOURCES.txt is not a regular file")
    source_lines = sources_stream.read().decode("utf-8").replace("\r\n", "\n").splitlines()
    validate_member_names(source_lines, artifact=f"{artifact} SOURCES.txt")
    all_files = expected_sdist_files(root)
    expected_lines = {
        member.removeprefix(f"{SDIST_ROOT}/")
        for member in all_files
        if member
        not in {
            f"{SDIST_ROOT}/PKG-INFO",
            f"{SDIST_ROOT}/setup.cfg",
        }
    }
    if set(source_lines) != expected_lines:
        missing = sorted(expected_lines - set(source_lines))
        unexpected = sorted(set(source_lines) - expected_lines)
        _fail(
            f"{artifact}: SOURCES.txt mismatch; "
            f"missing={missing!r}, unexpected={unexpected!r}"
        )


def check_sdist(path: Path, *, root: Path) -> SdistAudit:
    path = path.resolve()
    if not path.is_file():
        _fail(f"sdist does not exist: {path}")
    try:
        with tarfile.open(path, mode="r:*") as archive:
            infos = archive.getmembers()
            names = validate_member_names(
                (info.name for info in infos), artifact=f"sdist {path.name}"
            )
            for info in infos:
                _validate_tar_info(info, artifact=f"sdist {path.name}")
            file_names = frozenset(info.name for info in infos if info.isfile())
            directory_names = frozenset(info.name for info in infos if info.isdir())
            expected_files = expected_sdist_files(root)
            expected_directories = _expected_directories(expected_files)
            if file_names != expected_files:
                missing = sorted(expected_files - file_names)
                unexpected = sorted(file_names - expected_files)
                _fail(
                    f"sdist {path.name}: file contract mismatch; "
                    f"missing={missing!r}, unexpected={unexpected!r}"
                )
            if directory_names != expected_directories:
                missing = sorted(expected_directories - directory_names)
                unexpected = sorted(directory_names - expected_directories)
                _fail(
                    f"sdist {path.name}: directory contract mismatch; "
                    f"missing={missing!r}, unexpected={unexpected!r}"
                )
            if len(file_names) != 76:
                _fail(f"sdist {path.name}: expected 76 files, got {len(file_names)}")

            source_copies = {
                *(expected_source_members(root)),
                "LICENSE",
                "MANIFEST.in",
                "README.md",
                "pyproject.toml",
            }
            for relative in sorted(source_copies):
                stream = archive.extractfile(f"{SDIST_ROOT}/{relative}")
                if stream is None:
                    _fail(f"sdist {path.name}: source copy is not regular: {relative}")
                if stream.read() != (root / relative).read_bytes():
                    _fail(f"sdist {path.name}: source bytes differ for {relative!r}")
            _validate_sdist_metadata(
                archive, artifact=f"sdist {path.name}", root=root
            )
            if len(names) != len(file_names) + len(directory_names):
                _fail(f"sdist {path.name}: unsupported tar member type")
    except (OSError, tarfile.TarError, KeyError, UnicodeError) as error:
        raise ArtifactBoundaryError(f"cannot validate sdist {path}: {error}") from error
    return SdistAudit(
        path=path,
        sha256=_sha256_file(path),
        file_members=file_names,
        directory_members=directory_names,
    )


def compare_wheels(direct: WheelAudit, derived: WheelAudit) -> None:
    if direct.members != derived.members:
        _fail("direct and sdist-derived wheel member sets differ")
    if direct.comparable_bytes != derived.comparable_bytes:
        changed = sorted(
            name
            for name in direct.comparable_bytes
            if direct.comparable_bytes.get(name) != derived.comparable_bytes.get(name)
        )
        _fail(
            "direct and sdist-derived wheel payload/metadata bytes differ: "
            f"{changed!r}"
        )


def _summary(
    direct: WheelAudit, sdist: SdistAudit, derived: WheelAudit
) -> dict[str, object]:
    result: dict[str, object] = {
        "boundary": BOUNDARY_ID,
        "status": "pass",
        "p1b_baseline_python_files": len(P1B_BASELINE_MODULES),
        "p1b_manifest_files": 1,
        "p1b_patch_files": len(P1B_PATCHES),
        "sdist": {
            "file": sdist.path.name,
            "sha256": sdist.sha256,
            "files": len(sdist.file_members),
            "directories": len(sdist.directory_members),
        },
        "wheel": {
            "file": direct.path.name,
            "sha256": direct.sha256,
            "files": len(direct.members),
        },
    }
    result["sdist_derived_wheel"] = {
        "file": derived.path.name,
        "sha256": derived.sha256,
        "files": len(derived.members),
        "parity": "pass",
    }
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate the repository_only_p2_research_evidence_v1 wheel/sdist "
            "contract."
        )
    )
    parser.add_argument("--wheel", required=True, type=Path)
    parser.add_argument("--sdist", required=True, type=Path)
    parser.add_argument("--derived-wheel", required=True, type=Path)
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the passing summary as deterministic JSON.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = repository_root()
    try:
        direct = check_wheel(args.wheel, root=root)
        sdist = check_sdist(args.sdist, root=root)
        derived = check_wheel(args.derived_wheel, root=root)
        compare_wheels(direct, derived)
        result = _summary(direct, sdist, derived)
    except ArtifactBoundaryError as error:
        print(f"artifact boundary: FAIL: {error}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(
            "artifact boundary: PASS "
            f"({BOUNDARY_ID}; wheel={len(direct.members)} files; "
            f"sdist={len(sdist.file_members)} files/"
            f"{len(sdist.directory_members)} directories; "
            f"P1b data=1/{len(P1B_BASELINE_MODULES)}/{len(P1B_PATCHES)}"
            "; derived-wheel parity=pass"
            + ")"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
