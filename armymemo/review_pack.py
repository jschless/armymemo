from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .examples import read_packaged_example
from .parser import parse_text
from .renderers.typst import render_typst_pdf


@dataclass(frozen=True, slots=True)
class ReviewPackItem:
    slug: str
    example_file: str
    description: str


REVIEW_PACKS: dict[str, tuple[ReviewPackItem, ...]] = {
    "representative_5": (
        ReviewPackItem(
            slug="01-basic_mfr",
            example_file="basic_mfr.Amd",
            description="Memorandum for Record baseline: letterhead, subject, numbered body, signature.",
        ),
        ReviewPackItem(
            slug="02-memo_for",
            example_file="memo_for.Amd",
            description="Single-recipient MEMORANDUM FOR layout and route block spacing.",
        ),
        ReviewPackItem(
            slug="03-memo_multi_for",
            example_file="memo_multi_for.Amd",
            description="Multi-recipient routing and wrapped address handling.",
        ),
        ReviewPackItem(
            slug="04-memo_thru",
            example_file="memo_thru.Amd",
            description="THRU routing format and subject/body transition.",
        ),
        ReviewPackItem(
            slug="05-long_memo",
            example_file="long_memo.Amd",
            description="Continuation-page header, page number, and long-body behavior.",
        ),
    ),
}


def list_review_packs() -> list[str]:
    return sorted(REVIEW_PACKS)


def generate_review_pack(
    output_dir: str | Path,
    *,
    pack_name: str = "representative_5",
) -> list[Path]:
    if pack_name not in REVIEW_PACKS:
        supported = ", ".join(list_review_packs())
        raise ValueError(f"Unknown review pack '{pack_name}'. Supported packs: {supported}")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    generated: list[Path] = []
    manifest_lines = [
        f"# Review Pack: {pack_name}",
        "",
        "This directory is intended for human visual review of representative Army memo shapes.",
        "",
    ]

    for item in REVIEW_PACKS[pack_name]:
        pdf_path = output_path / f"{item.slug}.pdf"
        render_typst_pdf(parse_text(read_packaged_example(item.example_file)), pdf_path)
        generated.append(pdf_path)
        manifest_lines.extend(
            [
                f"- `{pdf_path.name}`",
                f"  Source: packaged example `{item.example_file}`",
                f"  Purpose: {item.description}",
            ]
        )

    manifest_path = output_path / "README.md"
    manifest_path.write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")
    return generated
