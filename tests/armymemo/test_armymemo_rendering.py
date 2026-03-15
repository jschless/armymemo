import re
from pathlib import Path

import pytest

from armymemo import parse_file, render_typst_pdf
from armymemo.comparison import extract_layout
from armymemo.document import BodyItem, MemoDocument, Recipient
from armymemo.renderers.typst import render_typst_source
from armymemo.review import review_document


@pytest.mark.integration
@pytest.mark.parametrize(
    "example_path",
    [
        "resources/examples/basic_mfr.Amd",
        "resources/examples/memo_for.Amd",
        "resources/examples/memo_multi_for.Amd",
        "resources/examples/memo_thru.Amd",
        "resources/examples/memo_extra_features.Amd",
    ],
)
def test_typst_renders_supported_examples(example_path, tmp_path):
    document = parse_file(example_path)
    stem = Path(example_path).stem
    typst_pdf = tmp_path / f"{stem}-typst.pdf"

    render_typst_pdf(document, typst_pdf)
    assert typst_pdf.exists()
    assert typst_pdf.stat().st_size > 0


@pytest.mark.integration
def test_typst_long_memo_has_continuation_header_and_page_numbers(tmp_path):
    document = parse_file("resources/examples/long_memo.Amd")
    typst_pdf = tmp_path / "long_memo-typst.pdf"

    render_typst_pdf(document, typst_pdf)

    report = review_document(document, pdf_source=typst_pdf)
    findings = {finding.rule_id: finding for finding in report.findings}

    assert findings["memo.continuation.heading"].passed, findings
    assert findings["memo.continuation.page_number"].passed, findings


def test_typst_source_escapes_email_references():
    document = parse_file("resources/examples/additional_duty_appointment.Amd")

    source = render_typst_source(document)

    assert "michael.j.jones\\@army.mil" in source


def test_typst_source_maps_bold_and_italic_markdown_to_distinct_typst_markup():
    document = parse_file("resources/examples/tutorial.Amd")

    source = render_typst_source(document)

    assert "*this will be bold*" in source
    assert "_this will be italicized_" in source


def test_typst_source_uses_quarter_inch_continuation_indent_for_single_for_line():
    document = MemoDocument(
        unit_name="4th Engineer Battalion",
        unit_street_address="588 Wetzel Road",
        unit_city_state_zip="Colorado Springs, CO 80904",
        office_symbol="ABC-DEF-GH",
        subject="Continuation Indent",
        body=[BodyItem(["This is a test memo."])],
        author_name="Jordan A. Carter",
        author_rank="CPT",
        author_branch="EN",
        author_title="Company Commander",
        for_recipients=[
            Recipient(
                name="Headquarters, Department of the Army Extremely Long Office Name",
                street_address="12345 Long Building Name Avenue",
                city_state_zip="Fort Example, NC 28310",
            )
        ],
    )

    source = render_typst_source(document)

    assert "continuation_indent_pt: 18" in source


@pytest.mark.integration
def test_typst_body_continuation_lines_return_to_left_margin(tmp_path):
    document = MemoDocument(
        unit_name="4th Engineer Battalion",
        unit_street_address="588 Wetzel Road",
        unit_city_state_zip="Colorado Springs, CO 80904",
        office_symbol="ABC-DEF-GH",
        subject="Body Continuation Margin",
        body=[
            BodyItem(
                [
                    (
                        "This paragraph is intentionally long so the body text wraps onto a second "
                        "line and demonstrates that continuation text returns to the left margin "
                        "instead of hanging underneath the paragraph label."
                    )
                ]
            )
        ],
        author_name="Jordan A. Carter",
        author_rank="CPT",
        author_branch="EN",
        author_title="Company Commander",
    )
    pdf_path = tmp_path / "body_continuation.pdf"

    render_typst_pdf(document, pdf_path)

    layout = extract_layout(pdf_path)
    body_lines = [
        line
        for line in layout.lines
        if line.page == 0 and line.x_start < 300 and line.y_pos > 200
    ]
    paragraph_start_index = next(
        index for index, line in enumerate(body_lines) if re.match(r"^1\.\S?", line.text.strip())
    )
    continuation_line = next(
        line
        for line in body_lines[paragraph_start_index + 1 :]
        if line.text.strip()
        and not re.match(r"^(\d+\.|[a-z]\.|\(\d+\)|\([a-z]\))\S?", line.text.strip(), re.I)
        and "JORDAN A. CARTER" not in line.text.upper()
    )

    assert abs(continuation_line.x_start - 72) <= 6, continuation_line


@pytest.mark.integration
def test_typst_nested_numbering_returns_to_top_level_indent_after_subitems(tmp_path):
    document = parse_file("resources/examples/long_memo.Amd")
    pdf_path = tmp_path / "long_memo_nested_indent.pdf"

    render_typst_pdf(document, pdf_path)

    layout = extract_layout(pdf_path)
    numbered_lines = [
        line
        for line in layout.lines
        if line.page == 0 and re.match(r"^(\d+\.|[a-z]\.)\S?", line.text.strip(), re.I)
    ]
    first_top_level = next(line for line in numbered_lines if re.match(r"^1\.\S?", line.text.strip()))
    first_subitem = next(line for line in numbered_lines if re.match(r"^a\.\S?", line.text.strip(), re.I))
    second_top_level = next(line for line in numbered_lines if re.match(r"^2\.\S?", line.text.strip()))

    assert abs(first_top_level.x_start - second_top_level.x_start) <= 4, numbered_lines
    assert first_subitem.x_start - first_top_level.x_start >= 16, numbered_lines


@pytest.mark.integration
def test_typst_signature_gap_is_close_to_four_blank_lines(tmp_path):
    document = parse_file("resources/examples/basic_mfr.Amd")
    pdf_path = tmp_path / "basic_mfr_signature_gap.pdf"

    render_typst_pdf(document, pdf_path)

    layout = extract_layout(pdf_path)
    last_body_line = next(
        line for line in reversed(layout.lines) if re.match(r"^3\.\S?", line.text.strip())
    )
    signature_line = next(
        line for line in layout.lines if "PHILIP K. DICK" in line.text.upper()
    )
    gap = signature_line.y_pos - last_body_line.y_pos

    assert 60 <= gap <= 72, gap


@pytest.mark.integration
def test_tutorial_keeps_final_paragraph_with_signature_block(tmp_path):
    document = parse_file("resources/examples/tutorial.Amd")
    pdf_path = tmp_path / "tutorial.pdf"

    render_typst_pdf(document, pdf_path)

    layout = extract_layout(pdf_path)
    signature_name = next(
        line for line in layout.lines if "SARAH M. JOHNSON" in line.text.upper()
    )
    signature_rank = next(
        line for line in layout.lines if "CPT, MI" in line.text.upper()
    )
    signature_title = next(
        line for line in layout.lines if "COMPANY COMMANDER" in line.text.upper()
    )
    point_of_contact_lines = [
        line
        for line in layout.lines
        if "POINT OF CONTACT" in line.text.upper()
        or "sarah.m.johnson@army.mil" in line.text
    ]

    assert signature_name.page == signature_rank.page == signature_title.page
    assert any(line.page == signature_name.page for line in point_of_contact_lines)
