"""Standalone Army memo library with Typst rendering and review tools."""

from .benchmarking import (
    BenchmarkReport,
    CaseBenchmark,
    EngineBenchmark,
    benchmark_renderers,
)
from .comparison import ComparisonResult, ComparisonTolerance, compare_pdfs
from .compiler import TypstBinaryManager, TypstCompiler
from .corpus import CorpusCase, generate_corpus
from .document import BodyItem, MemoDocument, Recipient, TableBlock
from .parser import parse_file, parse_text
from .renderers.typst import render_typst_pdf, render_typst_source
from .review import (
    ReviewFinding,
    ReviewReport,
    review_document,
    review_rendered_document,
)
from .review_pack import generate_review_pack, list_review_packs

__all__ = [
    "BenchmarkReport",
    "BodyItem",
    "CaseBenchmark",
    "ComparisonResult",
    "ComparisonTolerance",
    "CorpusCase",
    "EngineBenchmark",
    "MemoDocument",
    "Recipient",
    "ReviewFinding",
    "ReviewReport",
    "TableBlock",
    "TypstBinaryManager",
    "TypstCompiler",
    "benchmark_renderers",
    "compare_pdfs",
    "generate_corpus",
    "generate_review_pack",
    "list_review_packs",
    "parse_file",
    "parse_text",
    "render_typst_pdf",
    "render_typst_source",
    "review_document",
    "review_rendered_document",
]
