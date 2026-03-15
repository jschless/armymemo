from __future__ import annotations

from dataclasses import dataclass, field
from io import BytesIO
from itertools import zip_longest
from pathlib import Path
import re

import pdfplumber


@dataclass(slots=True)
class ExtractedLine:
    text: str
    x_start: float
    x_end: float
    y_pos: float
    y_end: float
    page: int

    @property
    def x_center(self) -> float:
        return round((self.x_start + self.x_end) / 2, 1)


@dataclass(slots=True)
class PageGeometry:
    page: int
    width: float
    height: float
    x_min: float
    x_max: float
    y_min: float
    y_max: float


@dataclass(slots=True)
class ExtractedLayout:
    lines: list[ExtractedLine] = field(default_factory=list)
    pages: list[PageGeometry] = field(default_factory=list)

    @property
    def page_count(self) -> int:
        return len(self.pages)


@dataclass(slots=True)
class ComparisonTolerance:
    x_tolerance: float = 2.0
    y_tolerance: float = 2.0
    bbox_tolerance: float = 4.0
    max_reported_errors: int = 20
    normalize_whitespace: bool = True


@dataclass(slots=True)
class ComparisonResult:
    passed: bool
    messages: list[str]
    reference_page_count: int
    candidate_page_count: int
    compared_lines: int


def compare_pdfs(
    reference_pdf: str | Path | bytes,
    candidate_pdf: str | Path | bytes,
    tolerance: ComparisonTolerance | None = None,
) -> ComparisonResult:
    tolerance = tolerance or ComparisonTolerance()
    return compare_layouts(
        extract_layout(reference_pdf),
        extract_layout(candidate_pdf),
        tolerance=tolerance,
    )


def compare_layouts(
    reference: ExtractedLayout,
    candidate: ExtractedLayout,
    *,
    tolerance: ComparisonTolerance | None = None,
) -> ComparisonResult:
    tolerance = tolerance or ComparisonTolerance()
    messages: list[str] = []

    if reference.page_count != candidate.page_count:
        messages.append(
            f"Page count mismatch: expected {reference.page_count}, got {candidate.page_count}"
        )

    for expected, actual in zip_longest(reference.pages, candidate.pages):
        if expected is None or actual is None:
            continue
        for label, expected_value, actual_value in [
            ("x_min", expected.x_min, actual.x_min),
            ("x_max", expected.x_max, actual.x_max),
            ("y_min", expected.y_min, actual.y_min),
            ("y_max", expected.y_max, actual.y_max),
        ]:
            if abs(expected_value - actual_value) > tolerance.bbox_tolerance:
                messages.append(
                    f"Page {expected.page + 1} geometry mismatch for {label}: "
                    f"{expected_value:.1f} vs {actual_value:.1f}"
                )

    compared_lines = 0
    for index, pair in enumerate(zip_longest(reference.lines, candidate.lines), start=1):
        expected, actual = pair
        if expected is None or actual is None:
            messages.append("Line count mismatch between reference and candidate PDFs")
            break
        compared_lines += 1
        if expected.page != actual.page:
            messages.append(
                f"Line {index} moved to a different page: expected page {expected.page + 1}, "
                f"got page {actual.page + 1}"
            )
        expected_text = _normalize(expected.text, tolerance.normalize_whitespace)
        actual_text = _normalize(actual.text, tolerance.normalize_whitespace)
        if expected_text != actual_text:
            messages.append(
                f"Line {index} text mismatch: expected '{expected_text}', got '{actual_text}'"
            )
        if abs(expected.x_start - actual.x_start) > tolerance.x_tolerance:
            messages.append(
                f"Line {index} x-position drifted by {abs(expected.x_start - actual.x_start):.1f}pt"
            )
        if abs(expected.y_pos - actual.y_pos) > tolerance.y_tolerance:
            messages.append(
                f"Line {index} y-position drifted by {abs(expected.y_pos - actual.y_pos):.1f}pt"
            )
        if len(messages) >= tolerance.max_reported_errors:
            break

    return ComparisonResult(
        passed=not messages,
        messages=messages[: tolerance.max_reported_errors],
        reference_page_count=reference.page_count,
        candidate_page_count=candidate.page_count,
        compared_lines=compared_lines,
    )


def extract_layout(source: str | Path | bytes) -> ExtractedLayout:
    layout = ExtractedLayout()
    pdf_stream: BytesIO | str
    if isinstance(source, bytes):
        pdf_stream = BytesIO(source)
    else:
        pdf_stream = str(source)

    with pdfplumber.open(pdf_stream) as pdf:
        for page_number, page in enumerate(pdf.pages):
            chars = page.chars or []
            lines_by_y: dict[float, list[dict]] = {}
            min_x = float("inf")
            max_x = float("-inf")
            min_y = float("inf")
            max_y = float("-inf")
            for char in chars:
                x0 = float(char.get("x0", 0))
                x1 = float(char.get("x1", 0))
                top = float(char.get("top", 0))
                bottom = float(char.get("bottom", 0))
                min_x = min(min_x, x0)
                max_x = max(max_x, x1)
                min_y = min(min_y, top)
                max_y = max(max_y, bottom)
                y_key = round(top / 2) * 2
                lines_by_y.setdefault(y_key, []).append(char)

            if min_x != float("inf"):
                layout.pages.append(
                    PageGeometry(
                        page=page_number,
                        width=round(float(page.width), 1),
                        height=round(float(page.height), 1),
                        x_min=round(min_x, 1),
                        x_max=round(max_x, 1),
                        y_min=round(min_y, 1),
                        y_max=round(max_y, 1),
                    )
                )

            for y_key in sorted(lines_by_y):
                line_chars = sorted(lines_by_y[y_key], key=lambda item: float(item.get("x0", 0)))
                text = "".join(str(char.get("text", "")) for char in line_chars)
                layout.lines.append(
                    ExtractedLine(
                        text=text,
                        x_start=round(float(line_chars[0].get("x0", 0)), 1),
                        x_end=round(float(line_chars[-1].get("x1", 0)), 1),
                        y_pos=round(float(y_key), 1),
                        y_end=round(max(float(char.get("bottom", 0)) for char in line_chars), 1),
                        page=page_number,
                    )
                )
    return layout


def _normalize(text: str, normalize_whitespace: bool) -> str:
    if not normalize_whitespace:
        return text
    compact = re.sub(r"\s+", "", text)
    return compact.strip()
