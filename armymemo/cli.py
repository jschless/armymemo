from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tempfile

from .benchmarking import benchmark_renderers
from .comparison import compare_pdfs
from .compiler import TypstCompiler
from .corpus import generate_corpus
from .parser import parse_file
from .review_pack import generate_review_pack, list_review_packs
from .review import review_document
from .renderers.typst import render_typst_source


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="armymemo")
    subparsers = parser.add_subparsers(dest="command", required=True)

    render_parser = subparsers.add_parser("render", help="Render a memo to Typst source or PDF")
    render_parser.add_argument("input", help="Path to AMD or MemoDoc input")
    render_parser.add_argument("--output", required=True, help="Output file path")
    render_parser.add_argument(
        "--source-only",
        action="store_true",
        help="Write Typst source instead of compiling a PDF",
    )

    compare_parser = subparsers.add_parser("compare", help="Compare two PDFs")
    compare_parser.add_argument("reference_pdf")
    compare_parser.add_argument("candidate_pdf")

    corpus_parser = subparsers.add_parser("corpus", help="Generate seeded sample memos")
    corpus_parser.add_argument("output_dir")
    corpus_parser.add_argument("--seed", type=int, default=7)
    corpus_parser.add_argument("--count", type=int, default=24)
    corpus_parser.add_argument("--format", choices=["memodoc", "amd"], default="memodoc")

    review_pack_parser = subparsers.add_parser(
        "review-pack",
        help="Generate a curated PDF bundle for visual review",
    )
    review_pack_parser.add_argument("output_dir")
    review_pack_parser.add_argument(
        "--pack",
        choices=list_review_packs(),
        default="representative_5",
        help="Named review pack to generate",
    )

    review_parser = subparsers.add_parser("review", help="Review memo structure and rendered PDF cues")
    review_parser.add_argument("input", help="Path to AMD or MemoDoc input")
    review_parser.add_argument("--pdf", help="Existing PDF to review")
    review_parser.add_argument(
        "--render",
        action="store_true",
        help="Render the input with Typst before running PDF-backed review checks",
    )
    review_parser.add_argument("--json", action="store_true", help="Emit review results as JSON")

    benchmark_parser = subparsers.add_parser("benchmark", help="Benchmark Typst rendering")
    benchmark_parser.add_argument("inputs", nargs="+", help="Input memo files to benchmark")
    benchmark_parser.add_argument("--iterations", type=int, default=3)
    benchmark_parser.add_argument("--json", action="store_true", help="Emit benchmark report as JSON")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "render":
        return _render(args)
    if args.command == "compare":
        return _compare(args)
    if args.command == "corpus":
        return _corpus(args)
    if args.command == "review-pack":
        return _review_pack(args)
    if args.command == "review":
        return _review(args)
    if args.command == "benchmark":
        return _benchmark(args)
    raise AssertionError(f"Unhandled command: {args.command}")


def _render(args: argparse.Namespace) -> int:
    document = parse_file(args.input)
    output_path = Path(args.output)
    source = render_typst_source(document)
    if args.source_only:
        output_path.write_text(source, encoding="utf-8")
        return 0
    TypstCompiler().compile_source(source, output_path)
    return 0


def _compare(args: argparse.Namespace) -> int:
    result = compare_pdfs(args.reference_pdf, args.candidate_pdf)
    if result.passed:
        print(
            f"PDFs matched across {result.reference_page_count} pages "
            f"and {result.compared_lines} extracted lines."
        )
        return 0
    print("PDF comparison failed:")
    for message in result.messages:
        print(f"- {message}")
    return 1


def _corpus(args: argparse.Namespace) -> int:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for case in generate_corpus(seed=args.seed, count=args.count):
        suffix = ".mdoc" if args.format == "memodoc" else ".Amd"
        path = output_dir / f"{case.name}{suffix}"
        content = case.document.to_memodoc() if args.format == "memodoc" else case.document.to_amd()
        path.write_text(content, encoding="utf-8")
    print(f"Wrote {args.count} memo inputs to {output_dir}")
    return 0


def _review_pack(args: argparse.Namespace) -> int:
    generated = generate_review_pack(args.output_dir, pack_name=args.pack)
    print(f"Wrote {len(generated)} review PDFs and README.md to {args.output_dir}")
    return 0


def _review(args: argparse.Namespace) -> int:
    document = parse_file(args.input)
    pdf_source = args.pdf
    if pdf_source is None and args.render:
        with tempfile.TemporaryDirectory(prefix="armymemo-review-") as temp_dir_name:
            output_path = Path(temp_dir_name) / "review.pdf"
            TypstCompiler().compile_source(render_typst_source(document), output_path)
            report = review_document(document, pdf_source=output_path)
    else:
        report = review_document(document, pdf_source=pdf_source)

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(f"passed={report.passed} executed={report.executed_rules} failed={report.failed_rules} skipped={report.skipped_rules}")
        for finding in report.findings:
            print(f"[{finding.status}] {finding.rule_id}: {finding.message}")
    return 0 if report.passed else 1


def _benchmark(args: argparse.Namespace) -> int:
    report = benchmark_renderers(args.inputs, iterations=args.iterations)
    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
        return 0

    for case in report.cases:
        print(case.case_name)
        for engine in case.engines:
            if engine.error:
                print(f"  {engine.engine}: error={engine.error}")
                continue
            print(
                f"  {engine.engine}: parse={engine.parse_seconds:.4f}s "
                f"source={engine.source_seconds:.4f}s "
                f"compile={engine.compile_seconds:.4f}s "
                f"total={engine.total_seconds:.4f}s"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
