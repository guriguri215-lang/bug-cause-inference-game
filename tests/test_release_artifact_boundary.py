from __future__ import annotations

import base64
import csv
import hashlib
import io
import stat
import tarfile
import zipfile
from pathlib import Path

import pytest

from scripts import check_release_artifacts as checker


def _metadata_bytes(root: Path) -> bytes:
    headers = [
        "Metadata-Version: 2.4",
        "Name: bug-cause-inference-game",
        "Version: 0.1.0",
        "Summary: A Bayesian active bug investigation prototype for synthetic bug-cause cases.",
        "Author: gurig",
        "License-Expression: MIT",
        (
            "Project-URL: Repository, "
            "https://github.com/guriguri215-lang/bug-cause-inference-game"
        ),
        "Classifier: Development Status :: 3 - Alpha",
        "Classifier: Programming Language :: Python :: 3",
        "Classifier: Programming Language :: Python :: 3.10",
        "Classifier: Topic :: Software Development :: Testing",
        "Requires-Python: >=3.10",
        "Description-Content-Type: text/markdown",
        "License-File: LICENSE",
        "Dynamic: license-file",
    ]
    readme = (root / "README.md").read_text(encoding="utf-8").rstrip("\n")
    return ("\n".join(headers) + "\n\n" + readme + "\n").encode()


def _wheel_payload(root: Path) -> dict[str, bytes]:
    payload = {
        member.removeprefix("src/"): (root / member).read_bytes()
        for member in checker.expected_source_members(root)
    }
    metadata = _metadata_bytes(root)
    payload.update(
        {
            f"{checker.DIST_INFO}/licenses/LICENSE": (root / "LICENSE").read_bytes(),
            f"{checker.DIST_INFO}/METADATA": metadata,
            f"{checker.DIST_INFO}/WHEEL": (
                b"Wheel-Version: 1.0\n"
                b"Generator: setuptools (83.0.0)\n"
                b"Root-Is-Purelib: true\n"
                b"Tag: py3-none-any\n\n"
            ),
            f"{checker.DIST_INFO}/entry_points.txt": (
                b"[console_scripts]\n"
                b"bug-cause-inference = bug_cause_inference.cli:main\n"
            ),
            f"{checker.DIST_INFO}/top_level.txt": b"bug_cause_inference\n",
        }
    )
    return payload


def _record_bytes(
    payload: dict[str, bytes],
    *,
    corrupt: bool = False,
    hash_suffix: bytes = b"",
) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    for name in sorted(payload):
        digest = base64.urlsafe_b64encode(hashlib.sha256(payload[name]).digest()).rstrip(
            b"="
        )
        if corrupt and name.endswith("/METADATA"):
            digest = base64.urlsafe_b64encode(bytes(32)).rstrip(b"=")
        if hash_suffix and name.endswith("/METADATA"):
            digest += hash_suffix
        writer.writerow([name, f"sha256={digest.decode()}", len(payload[name])])
    writer.writerow([f"{checker.DIST_INFO}/RECORD", "", ""])
    return stream.getvalue().encode()


def _write_wheel(
    path: Path,
    root: Path,
    *,
    corrupt_record: bool = False,
    record_hash_suffix: bytes = b"",
) -> None:
    payload = _wheel_payload(root)
    payload[f"{checker.DIST_INFO}/RECORD"] = _record_bytes(
        payload, corrupt=corrupt_record, hash_suffix=record_hash_suffix
    )
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(payload.items()):
            archive.writestr(name, data)


def _sdist_payload(root: Path) -> dict[str, bytes]:
    metadata = _metadata_bytes(root)
    relative_files = {
        member.removeprefix(f"{checker.SDIST_ROOT}/")
        for member in checker.expected_sdist_files(root)
    }
    sources = sorted(relative_files - {"PKG-INFO", "setup.cfg"})
    payload = {
        member: (root / member).read_bytes()
        for member in checker.expected_source_members(root)
    }
    for member in ("LICENSE", "MANIFEST.in", "README.md", "pyproject.toml"):
        payload[member] = (root / member).read_bytes()
    payload.update(
        {
            "PKG-INFO": metadata,
            "setup.cfg": b"[egg_info]\ntag_build = \ntag_date = 0\n\n",
            f"{checker.EGG_INFO}/PKG-INFO": metadata,
            f"{checker.EGG_INFO}/SOURCES.txt": (
                ("\n".join(sources) + "\n").encode()
            ),
            f"{checker.EGG_INFO}/dependency_links.txt": b"\n",
            f"{checker.EGG_INFO}/entry_points.txt": (
                b"[console_scripts]\n"
                b"bug-cause-inference = bug_cause_inference.cli:main\n"
            ),
            f"{checker.EGG_INFO}/top_level.txt": b"bug_cause_inference\n",
        }
    )
    return payload


def _write_sdist(path: Path, root: Path) -> None:
    payload = {
        f"{checker.SDIST_ROOT}/{relative}": data
        for relative, data in _sdist_payload(root).items()
    }
    directories = checker._expected_directories(payload)
    with tarfile.open(path, "w:gz") as archive:
        for name in sorted(directories, key=lambda value: (value.count("/"), value)):
            info = tarfile.TarInfo(name)
            info.type = tarfile.DIRTYPE
            info.mode = 0o755
            archive.addfile(info)
        for name, data in sorted(payload.items()):
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mode = 0o644
            archive.addfile(info, io.BytesIO(data))


def test_exact_repository_source_contract() -> None:
    root = checker.repository_root()

    source = checker.expected_source_members(root)
    wheel = checker.expected_wheel_payload(root) | checker.WHEEL_METADATA_MEMBERS
    sdist = checker.expected_sdist_files(root)

    assert len(source) == 65
    assert len(wheel) == 71
    assert len(sdist) == 76
    assert sum("/patches/" in member for member in source) == 25
    assert sum("/baseline/checkout/" in member for member in source) == 6
    assert sum(member.endswith("/manifest.json") for member in source) == 1
    assert not any("/p2" in member or member.startswith("tests/") for member in source)


@pytest.mark.parametrize(
    "name",
    [
        "/absolute/file.py",
        "C:/Users/private/file.py",
        "../outside.py",
        "safe/../../outside.py",
        r"safe\windows.py",
        "tests/test_hidden.py",
        "docs/release.md",
        "src/bug_cause_inference/p2h/reports.py",
        "tmp/build/output.py",
        "safe/.env",
        "safe/private.pem",
    ],
)
def test_member_name_validation_rejects_unsafe_or_forbidden_paths(name: str) -> None:
    with pytest.raises(checker.ArtifactBoundaryError):
        checker.validate_member_names([name], artifact="test")


@pytest.mark.parametrize(
    "names",
    [
        ["safe/file.py", "safe/file.py"],
        ["safe/File.py", "safe/file.py"],
        ["safe/Ｋ.py", "safe/K.py"],
    ],
)
def test_member_name_validation_rejects_duplicate_or_normalized_collision(
    names: list[str],
) -> None:
    with pytest.raises(checker.ArtifactBoundaryError):
        checker.validate_member_names(names, artifact="test")


def test_archive_type_and_mode_validation_is_fail_closed() -> None:
    symlink_zip = zipfile.ZipInfo("safe/link.py")
    symlink_zip.external_attr = (stat.S_IFLNK | 0o777) << 16
    with pytest.raises(checker.ArtifactBoundaryError, match="symlink"):
        checker._validate_zip_info(symlink_zip, artifact="test")

    executable_zip = zipfile.ZipInfo("safe/tool.py")
    executable_zip.external_attr = (stat.S_IFREG | 0o755) << 16
    with pytest.raises(checker.ArtifactBoundaryError, match="executable"):
        checker._validate_zip_info(executable_zip, artifact="test")

    symlink_tar = tarfile.TarInfo("safe/link.py")
    symlink_tar.type = tarfile.SYMTYPE
    with pytest.raises(checker.ArtifactBoundaryError, match="link/device/FIFO"):
        checker._validate_tar_info(symlink_tar, artifact="test")

    executable_tar = tarfile.TarInfo("safe/tool.py")
    executable_tar.type = tarfile.REGTYPE
    executable_tar.mode = 0o755
    with pytest.raises(checker.ArtifactBoundaryError, match="executable"):
        checker._validate_tar_info(executable_tar, artifact="test")


def test_synthetic_exact_wheel_and_sdist_pass(tmp_path: Path) -> None:
    root = checker.repository_root()
    wheel = tmp_path / "exact.whl"
    sdist = tmp_path / "exact.tar.gz"
    _write_wheel(wheel, root)
    _write_sdist(sdist, root)

    wheel_audit = checker.check_wheel(wheel, root=root)
    sdist_audit = checker.check_sdist(sdist, root=root)
    checker.compare_wheels(wheel_audit, wheel_audit)

    assert len(wheel_audit.members) == 71
    assert len(sdist_audit.file_members) == 76


def test_wheel_record_hash_mismatch_fails(tmp_path: Path) -> None:
    root = checker.repository_root()
    wheel = tmp_path / "bad-record.whl"
    _write_wheel(wheel, root, corrupt_record=True)

    with pytest.raises(checker.ArtifactBoundaryError, match="RECORD hash mismatch"):
        checker.check_wheel(wheel, root=root)


@pytest.mark.parametrize("suffix", [b"!!!!", b"="])
def test_wheel_record_noncanonical_hash_encoding_fails(
    tmp_path: Path, suffix: bytes
) -> None:
    root = checker.repository_root()
    wheel = tmp_path / "bad-record-encoding.whl"
    _write_wheel(wheel, root, record_hash_suffix=suffix)

    with pytest.raises(checker.ArtifactBoundaryError, match="invalid RECORD hash encoding"):
        checker.check_wheel(wheel, root=root)


def test_cli_requires_sdist_derived_wheel() -> None:
    with pytest.raises(SystemExit) as error:
        checker.build_parser().parse_args(["--wheel", "direct.whl", "--sdist", "source.tar.gz"])

    assert error.value.code == 2


def test_direct_and_sdist_derived_wheel_payload_mismatch_fails(
    tmp_path: Path,
) -> None:
    root = checker.repository_root()
    direct_path = tmp_path / "direct.whl"
    derived_path = tmp_path / "derived.whl"
    _write_wheel(direct_path, root)
    _write_wheel(derived_path, root)
    direct = checker.check_wheel(direct_path, root=root)
    derived = checker.check_wheel(derived_path, root=root)
    changed = dict(derived.comparable_bytes)
    changed["bug_cause_inference/models.py"] += b"\n"
    mutated = checker.WheelAudit(
        path=derived.path,
        sha256=derived.sha256,
        members=derived.members,
        comparable_bytes=changed,
    )

    with pytest.raises(checker.ArtifactBoundaryError, match="bytes differ"):
        checker.compare_wheels(direct, mutated)
