"""Standalone Army memo library with Typst rendering and review tools."""

from .benchmarking import BenchmarkReport, CaseBenchmark, EngineBenchmark, benchmark_renderers
from .comparison import (
    ComparisonResult,
    ComparisonTolerance,
    ExtractedLayout,
    ExtractedLine,
    compare_layouts,
    compare_pdfs,
)
from .compiler import TypstBinaryManager, TypstCompiler
from .corpus import CorpusCase, generate_corpus
from .document import BodyItem, MemoDocument, Recipient, TableBlock
from .parser import parse_file, parse_text
from .rules import load_rule_inventory, load_rulebook, load_typst_layout_rules
from .review import (
    ReviewFeatures,
    ReviewFinding,
    ReviewReport,
    default_review_rules,
    extract_review_features,
    review_document,
)
from .renderers.typst import render_typst_pdf, render_typst_source

__all__ = [
    "BenchmarkReport",
    "BodyItem",
    "CaseBenchmark",
    "ComparisonResult",
    "ComparisonTolerance",
    "CorpusCase",
    "EngineBenchmark",
    "ExtractedLayout",
    "ExtractedLine",
    "MemoDocument",
    "Recipient",
    "ReviewFeatures",
    "ReviewFinding",
    "ReviewReport",
    "TableBlock",
    "TypstBinaryManager",
    "TypstCompiler",
    "benchmark_renderers",
    "compare_layouts",
    "compare_pdfs",
    "default_review_rules",
    "extract_review_features",
    "generate_corpus",
    "load_rule_inventory",
    "load_rulebook",
    "load_typst_layout_rules",
    "parse_file",
    "parse_text",
    "render_typst_pdf",
    "render_typst_source",
    "review_document",
]
