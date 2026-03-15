from __future__ import annotations

from importlib.resources import files
from pathlib import Path

_EXAMPLES_PACKAGE = "armymemo.resources.examples"


def list_packaged_examples() -> list[str]:
    root = files(_EXAMPLES_PACKAGE)
    return sorted(
        entry.name
        for entry in root.iterdir()
        if entry.is_file() and entry.name.endswith((".Amd", ".mdoc"))
    )


def has_packaged_example(name: str) -> bool:
    return _example_traversable(name) is not None


def read_packaged_example(name: str) -> str:
    resource = _example_traversable(name)
    if resource is None:
        supported = ", ".join(list_packaged_examples())
        raise FileNotFoundError(f"Unknown packaged example '{name}'. Supported examples: {supported}")
    return resource.read_text(encoding="utf-8")


def example_basename(candidate: str | Path) -> str:
    return Path(candidate).name


def _example_traversable(name: str):
    normalized = example_basename(name)
    if not normalized:
        return None
    root = files(_EXAMPLES_PACKAGE)
    candidate = root / normalized
    if candidate.is_file():
        return candidate
    return None
