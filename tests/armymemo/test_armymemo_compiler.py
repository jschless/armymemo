from __future__ import annotations

import tarfile
from io import BytesIO
from pathlib import Path

import pytest

from armymemo.compiler import DEFAULT_TYPST_VERSION, TypstBinaryManager, TypstCompiler
from armymemo.exceptions import TypstNotFoundError


def test_typst_binary_manager_defaults_to_validated_version():
    assert TypstBinaryManager().version == DEFAULT_TYPST_VERSION == "0.14.2"


def test_compile_file_uses_source_parent_as_typst_root(tmp_path, monkeypatch):
    source_path = tmp_path / "document.typ"
    source_path.write_text("= test", encoding="utf-8")
    output_path = tmp_path / "document.pdf"

    compiler = TypstCompiler()

    monkeypatch.setattr(
        compiler.binary_manager,
        "resolve_binary",
        lambda *, auto_install=True: Path("/usr/bin/typst"),
    )

    captured: dict[str, object] = {}

    class Result:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run(command, **kwargs):
        captured["command"] = command
        output_path.write_bytes(b"%PDF-1.4\n")
        return Result()

    monkeypatch.setattr("armymemo.compiler.subprocess.run", fake_run)

    compiler.compile_file(source_path, output_path)

    assert captured["command"][3] == str(source_path.parent.resolve())


def test_extract_archive_safely_rejects_path_traversal(tmp_path):
    archive_path = tmp_path / "typst.tar.xz"
    with tarfile.open(archive_path, mode="w:xz") as archive:
        payload = b"bad"
        info = tarfile.TarInfo("../escape")
        info.size = len(payload)
        archive.addfile(info, BytesIO(payload))

    manager = TypstBinaryManager()
    with tarfile.open(archive_path, mode="r:xz") as archive, pytest.raises(TypstNotFoundError):
        manager._extract_archive_safely(archive, tmp_path / "install")


def test_extract_archive_safely_rejects_symlinks(tmp_path):
    archive_path = tmp_path / "typst.tar.xz"
    with tarfile.open(archive_path, mode="w:xz") as archive:
        info = tarfile.TarInfo("typst-link")
        info.type = tarfile.SYMTYPE
        info.linkname = "typst"
        archive.addfile(info)

    manager = TypstBinaryManager()
    with tarfile.open(archive_path, mode="r:xz") as archive, pytest.raises(TypstNotFoundError):
        manager._extract_archive_safely(archive, tmp_path / "install")
