from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import textwrap

from ..document import BodyItem, MemoDocument, Recipient, TableBlock
from ..inline import render_typst_inline
from ..rules import load_rulebook

RESOURCE_DIR = Path(__file__).resolve().parents[1] / "resources"
TEMPLATE_DIR = RESOURCE_DIR / "typst"
TEMPLATE_FILES = [
    TEMPLATE_DIR / "config.typ",
    TEMPLATE_DIR / "primitives.typ",
    TEMPLATE_DIR / "frontmatter.typ",
    TEMPLATE_DIR / "body.typ",
    TEMPLATE_DIR / "backmatter.typ",
    TEMPLATE_DIR / "armymemo.typ",
]


@dataclass(frozen=True, slots=True)
class TypstMarkup:
    source: str


def render_typst_source(document: MemoDocument, logo_path: str | Path | None = None) -> str:
    logo = Path(logo_path) if logo_path is not None else Path("DA_LOGO.png")
    template = _compose_template()
    memo = _build_template_model(document)
    rulebook = load_rulebook()
    lines = [
        f"#let rulebook = {_serialize_typst_value(rulebook)}",
        template,
        "",
        f"#let memo = {_serialize_typst_value(memo)}",
        f"#let memo_logo_path = {_serialize_typst_value(logo.as_posix())}",
        "#render_memo(memo, logo_path: memo_logo_path)",
        "",
    ]
    return "\n".join(lines)


def render_typst_pdf(document: MemoDocument, output_path: str | Path) -> Path:
    from ..compiler import TypstCompiler

    compiler = TypstCompiler()
    return compiler.compile_source(render_typst_source(document), output_path)


def _compose_template() -> str:
    sections: list[str] = []
    for path in TEMPLATE_FILES:
        body = path.read_text(encoding="utf-8").rstrip()
        sections.append(f"// {path.name}\n{body}")
    return "\n\n".join(sections)


def _build_template_model(document: MemoDocument) -> dict[str, object]:
    signature_lines = [
        _markup(document.author_name.upper()),
        _markup(f"{document.author_rank}, {document.author_branch}"),
    ]
    if document.author_title:
        signature_lines.append(_markup(document.author_title))

    return {
        "unit_name": _markup(document.unit_name),
        "unit_street_address": _markup(document.unit_street_address),
        "unit_city_state_zip": _markup(document.unit_city_state_zip),
        "office_symbol": _markup(document.office_symbol),
        "todays_date": _optional_markup(document.todays_date),
        "subject": _markup(document.subject),
        "suspense_date": _optional_markup(document.suspense_date),
        "route_paragraphs": _route_paragraphs(document),
        "body": _body_nodes(document.body),
        "authority": _optional_markup(
            f"{document.authority.rstrip(':').upper()}:"
            if document.authority
            else None
        ),
        "signature_lines": signature_lines,
        "enclosure_label": _enclosure_label(document.enclosures),
        "enclosure_entries": _enclosure_entries(document.enclosures),
        "distros": [_markup(value) for value in document.distros],
        "cfs": [_markup(value) for value in document.cfs],
    }


def _body_nodes(nodes: list[BodyItem | TableBlock], depth: int = 0) -> list[dict[str, object]]:
    rendered: list[dict[str, object]] = []
    item_number = 0
    for node in nodes:
        if isinstance(node, TableBlock):
            normalized_rows = node.normalized_rows()
            cells = [_markup(header) for header in node.headers]
            cells.extend(_markup(cell) for row in normalized_rows for cell in row)
            rendered.append(
                {
                    "kind": "table",
                    "column_count": len(node.headers),
                    "cells": cells,
                }
            )
            continue

        item_number += 1
        rendered.append(
                {
                    "kind": "item",
                    "label": _markup(_item_label(depth, item_number)),
                    "first_line_indent_pt": _indent_for_depth(depth),
                    "continuation_indent_pt": _continuation_indent(depth),
                    "paragraphs": [_markup(paragraph) for paragraph in node.paragraphs],
                    "children": _body_nodes(node.children, depth + 1),
                }
            )
    return rendered


def _route_paragraphs(document: MemoDocument) -> list[dict[str, object]]:
    paragraphs: list[dict[str, object]] = []
    if not document.thru_recipients and not document.for_recipients:
        return [_route_paragraph("MEMORANDUM FOR RECORD", continuation_indent_pt=0, wrap_width=78, paragraph_gap_pt=20)]

    if document.thru_recipients:
        if len(document.thru_recipients) == 1:
            paragraphs.append(
                _route_paragraph(
                    f"MEMORANDUM THRU {_recipient_line(document.thru_recipients[0])}",
                    continuation_indent_pt=0,
                    wrap_width=72,
                    paragraph_gap_pt=20,
                )
            )
        else:
            paragraphs.append(
                _route_paragraph("MEMORANDUM THRU", continuation_indent_pt=0, wrap_width=72, paragraph_gap_pt=20)
            )
            for index, recipient in enumerate(document.thru_recipients):
                gap = 20 if index == len(document.thru_recipients) - 1 and document.for_recipients else 6
                paragraphs.append(
                    _route_paragraph(
                        _recipient_line(recipient),
                        continuation_indent_pt=18,
                        wrap_width=78,
                        paragraph_gap_pt=gap,
                    )
                )

    if document.for_recipients:
        if document.thru_recipients and len(document.for_recipients) == 1:
            paragraphs.append(
                _route_paragraph(
                    f"FOR {_recipient_line(document.for_recipients[0])}",
                    continuation_indent_pt=0,
                    wrap_width=78,
                    paragraph_gap_pt=20,
                )
            )
            return paragraphs

        if len(document.for_recipients) == 1:
            paragraphs.append(
                _route_paragraph(
                    f"MEMORANDUM FOR {_recipient_line(document.for_recipients[0])}",
                    continuation_indent_pt=18,
                    wrap_width=74,
                    paragraph_gap_pt=20,
                )
            )
            return paragraphs

        paragraphs.append(
            _route_paragraph(
                "FOR" if document.thru_recipients else "MEMORANDUM FOR",
                continuation_indent_pt=0,
                wrap_width=78,
                paragraph_gap_pt=20,
            )
        )
        for index, recipient in enumerate(document.for_recipients):
            paragraphs.append(
                _route_paragraph(
                    _recipient_line(recipient),
                    continuation_indent_pt=18,
                    wrap_width=78,
                    paragraph_gap_pt=20 if index == len(document.for_recipients) - 1 else 6,
                )
            )
    return paragraphs


def _route_paragraph(
    text: str,
    *,
    continuation_indent_pt: int,
    wrap_width: int,
    paragraph_gap_pt: int,
) -> dict[str, object]:
    wrapped = textwrap.wrap(
        text,
        width=wrap_width,
        break_long_words=False,
        break_on_hyphens=False,
    )
    return {
        "lines": [_markup(line) for line in wrapped],
        "continuation_indent_pt": continuation_indent_pt,
        "paragraph_gap_pt": paragraph_gap_pt,
    }


def _item_label(depth: int, index: int) -> str:
    if depth == 0:
        return f"{index}."
    if depth == 1:
        return f"{chr(96 + index)}."
    if depth == 2:
        return f"({index})"
    return f"({chr(96 + index)})"


def _indent_for_depth(depth: int) -> int:
    mapping = {
        0: 0,
        1: 20,
        2: 38,
        3: 38,
    }
    return mapping.get(depth, 56)


def _continuation_indent(depth: int) -> int:
    mapping = {
        0: 18,
        1: 38,
        2: 56,
        3: 56,
    }
    return mapping.get(depth, 74)


def _recipient_line(recipient: Recipient) -> str:
    return ", ".join(
        part
        for part in [recipient.name, recipient.street_address, recipient.city_state_zip]
        if part
    )


def _markup(text: str) -> TypstMarkup:
    return TypstMarkup(render_typst_inline(text))


def _optional_markup(text: str | None) -> TypstMarkup | None:
    if not text:
        return None
    return _markup(text)


def _enclosure_label(values: list[str]) -> TypstMarkup | None:
    if len(values) == 1:
        return _markup("Encl")
    if len(values) > 1:
        return _markup(f"{len(values)} Encls")
    return None


def _enclosure_entries(values: list[str]) -> list[TypstMarkup]:
    if len(values) <= 1:
        return [_markup(value) for value in values]
    return [_markup(f"{index}. {value}") for index, value in enumerate(values, start=1)]


def _serialize_typst_value(value: object) -> str:
    if value is None:
        return "none"
    if isinstance(value, TypstMarkup):
        return f"[{value.source}]"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return str(value)
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, list):
        if not value:
            return "()"
        items = ", ".join(_serialize_typst_value(item) for item in value)
        if len(value) == 1:
            items = f"{items},"
        return f"({items})"
    if isinstance(value, dict):
        items = ", ".join(
            f"{key}: {_serialize_typst_value(item)}" for key, item in value.items()
        )
        return f"({items})"
    raise TypeError(f"Unsupported Typst value: {value!r}")
