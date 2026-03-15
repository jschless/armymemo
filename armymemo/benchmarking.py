from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

from .compiler import TypstBinaryManager, TypstCompiler
from .parser import parse_file
from .renderers.typst import render_typst_source


@dataclass(slots=True)
class EngineBenchmark:
    engine: str
    version: str | None
    parse_seconds: float
    source_seconds: float | None
    compile_seconds: float | None
    total_seconds: float | None
    error: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "engine": self.engine,
            "version": self.version,
            "parse_seconds": self.parse_seconds,
            "source_seconds": self.source_seconds,
            "compile_seconds": self.compile_seconds,
            "total_seconds": self.total_seconds,
            "error": self.error,
        }


@dataclass(slots=True)
class CaseBenchmark:
    case_name: str
    input_path: str
    engines: list[EngineBenchmark] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "case_name": self.case_name,
            "input_path": self.input_path,
            "engines": [engine.to_dict() for engine in self.engines],
        }


@dataclass(slots=True)
class BenchmarkReport:
    iterations: int
    cases: list[CaseBenchmark]

    def to_dict(self) -> dict[str, object]:
        return {
            "iterations": self.iterations,
            "cases": [case.to_dict() for case in self.cases],
        }


def benchmark_renderers(
    inputs: list[str | Path],
    *,
    iterations: int = 3,
) -> BenchmarkReport:
    cases: list[CaseBenchmark] = []
    versions = {"typst": _detect_typst_version()}

    for input_path in inputs:
        path = Path(input_path)
        case = CaseBenchmark(case_name=path.stem, input_path=str(path))
        for engine in ("typst",):
            case.engines.append(
                _benchmark_engine(
                    path,
                    engine=engine,
                    iterations=iterations,
                    version=versions[engine],
                )
            )
        cases.append(case)
    return BenchmarkReport(iterations=iterations, cases=cases)


def _benchmark_engine(
    input_path: Path,
    *,
    engine: str,
    iterations: int,
    version: str | None,
) -> EngineBenchmark:
    parse_samples: list[float] = []
    source_samples: list[float] = []
    compile_samples: list[float] = []

    try:
        with tempfile.TemporaryDirectory(prefix=f"armymemo-benchmark-{engine}-") as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            for iteration in range(iterations):
                started = time.perf_counter()
                document = parse_file(input_path)
                parse_samples.append(time.perf_counter() - started)

                started = time.perf_counter()
                source = render_typst_source(document)
                source_samples.append(time.perf_counter() - started)

                output_path = temp_dir / f"{input_path.stem}-{engine}-{iteration}.pdf"
                started = time.perf_counter()
                TypstCompiler().compile_source(source, output_path)
                compile_samples.append(time.perf_counter() - started)

    except Exception as exc:  # pragma: no cover - exercised in CLI/manual use
        return EngineBenchmark(
            engine=engine,
            version=version,
            parse_seconds=_average(parse_samples),
            source_seconds=_average(source_samples),
            compile_seconds=_average(compile_samples),
            total_seconds=None,
            error=str(exc),
        )

    parse_average = _average(parse_samples)
    source_average = _average(source_samples)
    compile_average = _average(compile_samples)
    return EngineBenchmark(
        engine=engine,
        version=version,
        parse_seconds=parse_average,
        source_seconds=source_average,
        compile_seconds=compile_average,
        total_seconds=parse_average + source_average + compile_average,
    )


def _average(samples: list[float]) -> float:
    if not samples:
        return 0.0
    return sum(samples) / len(samples)


def _detect_binary_version(binary: str) -> str | None:
    discovered = shutil.which(binary)
    if not discovered:
        return None
    try:
        result = subprocess.run(
            [discovered, "--version"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    output = (result.stdout or result.stderr or "").strip().splitlines()
    return output[0] if output else None


def _detect_typst_version() -> str | None:
    try:
        binary = TypstBinaryManager().resolve_binary(auto_install=False)
    except Exception:
        discovered = shutil.which("typst")
        if not discovered:
            return None
        binary = Path(discovered)
    return _detect_binary_version(str(binary))
