from armymemo.document import MemoDocument
from armymemo.parser import parse_file
from armymemo.renderers.typst import render_typst_pdf
from armymemo.review import review_document


def test_review_document_flags_missing_subject():
    document = MemoDocument(
        unit_name="Test Unit",
        unit_street_address="123 Example Road",
        unit_city_state_zip="Fort Example, NC 28310",
        office_symbol="S1-123",
        subject="",
        body=[],
        author_name="Jordan A. Carter",
        author_rank="CPT",
        author_branch="EN",
    )

    report = review_document(document)
    findings = {finding.rule_id: finding for finding in report.findings}

    assert findings["document.subject.present"].status == "fail"
    assert findings["document.body.present"].status == "fail"


def test_review_document_passes_pdf_continuation_checks_for_long_memo(tmp_path):
    document = parse_file("resources/examples/long_memo.Amd")
    pdf_path = tmp_path / "long_memo.pdf"

    render_typst_pdf(document, pdf_path)

    report = review_document(document, pdf_source=pdf_path)
    findings = {finding.rule_id: finding for finding in report.findings}

    assert findings["pdf.first_page_header.present"].status == "pass"
    assert findings["pdf.continuation_header.present"].status == "pass"
    assert findings["pdf.continuation_page_number.present"].status == "pass"
