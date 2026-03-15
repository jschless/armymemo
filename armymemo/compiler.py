from __future__ import annotations

import os
import platform
import shutil
import stat
import subprocess
import tarfile
import tempfile
import urllib.request
from pathlib import Path

from .exceptions import TypstCompileError, TypstNotFoundError
from .renderers.typst import RESOURCE_DIR as TYPST_RESOURCE_DIR

DEFAULT_TYPST_VERSION = "0.14.2"


class TypstBinaryManager:
    """Resolve or provision a pinned Typst binary for supported platforms."""

    def __init__(
        self,
        *,
        version: str | None = None,
        cache_dir: str | Path | None = None,
    ) -> None:
        self.version = version or os.environ.get("ARMYMEMO_TYPST_VERSION", DEFAULT_TYPST_VERSION)
        self.cache_dir = Path(cache_dir or Path.home() / ".cache" / "armymemo" / "typst")

    def resolve_binary(self, *, auto_install: bool = True) -> Path:
        env_binary = os.environ.get("ARMYMEMO_TYPST_BIN")
        if env_binary:
            path = Path(env_binary).expanduser()
            if path.exists():
                return path

        discovered = shutil.which("typst")
        if discovered:
            return Path(discovered)

        cached_binary = self._cached_binary_path()
        if cached_binary.exists():
            return cached_binary

        if not auto_install:
            raise TypstNotFoundError(
                "Typst was not found in PATH and no cached binary is available"
            )

        return self.install()

    def install(self) -> Path:
        target = self._target_triple()
        url = (
            f"https://github.com/typst/typst/releases/download/v{self.version}/"
            f"typst-{target}.tar.xz"
        )
        install_dir = self.cache_dir / self.version / target
        install_dir.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory(prefix="armymemo-typst-download-") as temp_dir_name:
            archive_path = Path(temp_dir_name) / "typst.tar.xz"
            urllib.request.urlretrieve(url, archive_path)
            with tarfile.open(archive_path, mode="r:xz") as archive:
                self._extract_archive_safely(archive, install_dir)

        binary = self._find_installed_binary(install_dir, target)
        if binary is None:
            raise TypstNotFoundError(f"Downloaded Typst archive did not contain a binary: {url}")
        binary.chmod(binary.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        return binary

    def _cached_binary_path(self) -> Path:
        target = self._target_triple()
        install_dir = self.cache_dir / self.version / target
        direct_binary = install_dir / "typst"
        if direct_binary.exists():
            return direct_binary
        nested_binary = self._find_installed_binary(install_dir, target)
        if nested_binary is None:
            return direct_binary
        return nested_binary

    def _target_triple(self) -> str:
        system = platform.system()
        machine = platform.machine().lower()
        if system == "Darwin":
            if machine in {"arm64", "aarch64"}:
                return "aarch64-apple-darwin"
            if machine in {"x86_64", "amd64"}:
                return "x86_64-apple-darwin"
        if system == "Linux":
            if machine in {"x86_64", "amd64"}:
                return "x86_64-unknown-linux-musl"
            if machine in {"arm64", "aarch64"}:
                return "aarch64-unknown-linux-musl"
        raise TypstNotFoundError(
            f"Auto-install is only supported on macOS and Linux; found {system} {machine}"
        )

    def _extract_archive_safely(self, archive: tarfile.TarFile, install_dir: Path) -> None:
        install_root = install_dir.resolve()
        for member in archive.getmembers():
            if member.issym() or member.islnk():
                raise TypstNotFoundError("Refusing to extract Typst archive containing links")
            member_path = (install_root / member.name).resolve()
            if install_root != member_path and install_root not in member_path.parents:
                raise TypstNotFoundError("Refusing to extract Typst archive outside the install directory")
        archive.extractall(install_root)

    def _find_installed_binary(self, install_dir: Path, target: str) -> Path | None:
        expected_binary = install_dir / f"typst-{target}" / "typst"
        if expected_binary.exists():
            return expected_binary

        for candidate in install_dir.rglob("typst"):
            if install_dir.resolve() in candidate.resolve().parents:
                return candidate
        return None


class TypstCompiler:
    def __init__(self, binary_manager: TypstBinaryManager | None = None) -> None:
        self.binary_manager = binary_manager or TypstBinaryManager()

    def compile_source(
        self,
        source: str,
        output_path: str | Path,
        *,
        auto_install: bool = True,
        timeout: int = 90,
    ) -> Path:
        with tempfile.TemporaryDirectory(prefix="armymemo-typst-") as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            source_path = temp_dir / "document.typ"
            source_path.write_text(source, encoding="utf-8")
            resource_logo = TYPST_RESOURCE_DIR / "DA_LOGO.png"
            if resource_logo.exists():
                shutil.copy2(resource_logo, temp_dir / "DA_LOGO.png")
            return self.compile_file(
                source_path,
                output_path,
                auto_install=auto_install,
                timeout=timeout,
            )

    def compile_file(
        self,
        source_path: str | Path,
        output_path: str | Path,
        *,
        root_dir: str | Path | None = None,
        auto_install: bool = True,
        timeout: int = 90,
    ) -> Path:
        binary = self.binary_manager.resolve_binary(auto_install=auto_install)
        source_path = Path(source_path).resolve()
        output_path = Path(output_path).resolve()
        root_path = Path(root_dir).resolve() if root_dir is not None else source_path.parent.resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        command = [
            str(binary),
            "compile",
            "--root",
            str(root_path),
            str(source_path),
            str(output_path),
        ]
        result = subprocess.run(
            command,
            cwd=source_path.parent,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout,
        )
        if result.returncode != 0:
            raise TypstCompileError(result.stderr or result.stdout or "Typst compilation failed")
        if not output_path.exists():
            raise TypstCompileError("Typst reported success but no PDF was created")
        return output_path
