from pathlib import Path

import pytest

from armymemo import parse_file, render_typst_pdf
from armymemo.document import BodyItem, MemoDocument, Recipient
from armymemo.review import review_document
from armymemo.renderers.typst import render_typst_source

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
