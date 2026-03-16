from armymemo.document import BodyItem, MemoDocument, Recipient
from armymemo.parser import parse_file
from armymemo.renderers.typst import render_typst_pdf
from armymemo.review import (
    ReviewFinding,
    ReviewReport,
    default_document_review_rules,
    review_document,
    review_rendered_document,
)


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
    assert findings["document.subject.present"].name == "Subject Present"
    assert findings["document.subject.present"].ar_reference == "AR 25-50, para 2-4"
    assert findings["document.subject.present"].suggested_fix is not None


def test_document_only_review_rules_skip_rendered_checks():
    document = MemoDocument(
        unit_name="Test Unit",
        unit_street_address="123 Example Road",
        unit_city_state_zip="Fort Example, NC 28310",
        office_symbol="S1-123",
        subject="Testing Live Review",
        body=[BodyItem(["Body paragraph."])],
        author_name="Jordan A. Carter",
        author_rank="CPT",
        author_branch="EN",
        todays_date="15 January 2025",
    )

    report = review_document(document, rules=default_document_review_rules())
    rule_ids = {finding.rule_id for finding in report.findings}

    assert "memo.heading.letterhead" not in rule_ids
    assert "document.date.format" in rule_ids
    assert report.skipped_rules == 0


def test_review_document_flags_missing_header_fields_and_style_issues():
    document = MemoDocument(
        unit_name="",
        unit_street_address="",
        unit_city_state_zip="",
        office_symbol="bad symbol",
        subject="lowercase subject.",
        body=[BodyItem(["Body paragraph."])],
        author_name="Jordan A. Carter",
        author_rank="captain",
        author_branch="engineers",
        todays_date="01/15/2025",
    )

    report = review_document(document, rules=default_document_review_rules())
    findings = {finding.rule_id: finding for finding in report.findings}

    assert findings["document.organization.complete"].status == "fail"
    assert findings["document.office_symbol.format"].status == "fail"
    assert findings["document.date.format"].status == "fail"
    assert findings["document.subject.style.capitalization"].status == "fail"
    assert findings["document.subject.style.terminal_punctuation"].status == "fail"
    assert findings["document.rank.known"].status == "fail"
    assert findings["document.branch.known"].status == "fail"


def test_review_report_fails_on_warning_findings():
    report = ReviewReport(
        findings=[
            ReviewFinding(
                rule_id="memo.heading.letterhead",
                severity="warning",
                status="fail",
                message="Letterhead geometry mismatch.",
            )
        ]
    )

    assert report.passed is False
    assert report.failing_severity_counts["warning"] == 1


def test_review_document_passes_first_page_geometry_for_basic_mfr(tmp_path):
    document = parse_file("resources/examples/basic_mfr.Amd")
    pdf_path = tmp_path / "basic_mfr.pdf"

    render_typst_pdf(document, pdf_path)

    report = review_document(document, pdf_source=pdf_path)
    findings = {finding.rule_id: finding for finding in report.findings}

    assert findings["memo.heading.letterhead"].status == "pass"
    assert findings["memo.heading.office_symbol"].status == "pass"
    assert findings["memo.heading.date"].status == "pass"
    assert findings["memo.heading.subject"].status == "pass"
    assert findings["memo.closing.signature"].status == "pass"


def test_review_document_passes_extra_feature_closing_checks(tmp_path):
    document = parse_file("resources/examples/memo_extra_features.Amd")
    pdf_path = tmp_path / "memo_extra_features.pdf"

    render_typst_pdf(document, pdf_path)

    report = review_document(document, pdf_source=pdf_path)
    findings = {finding.rule_id: finding for finding in report.findings}

    assert findings["memo.heading.suspense"].status == "pass"
    assert findings["memo.closing.authority"].status == "pass"
    assert findings["memo.closing.distribution"].status == "pass"
    assert findings["memo.closing.cf"].status == "pass"


def test_review_document_passes_pdf_continuation_checks_for_long_memo(tmp_path):
    document = parse_file("resources/examples/long_memo.Amd")
    pdf_path = tmp_path / "long_memo.pdf"

    render_typst_pdf(document, pdf_path)

    report = review_document(document, pdf_source=pdf_path)
    findings = {finding.rule_id: finding for finding in report.findings}

    assert findings["memo.continuation.heading"].status == "pass"
    assert findings["memo.continuation.page_number"].status == "pass"


def test_review_document_enforces_single_for_wrap_indent(tmp_path):
    document = MemoDocument(
        unit_name="4th Engineer Battalion",
        unit_street_address="588 Wetzel Road",
        unit_city_state_zip="Colorado Springs, CO 80904",
        office_symbol="ABC-DEF-GH",
        subject="Long Single Address",
        body=[BodyItem(["This is a test memo body."])],
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
    pdf_path = tmp_path / "single_for_indent.pdf"

    render_typst_pdf(document, pdf_path)

    report = review_document(document, pdf_source=pdf_path)
    findings = {finding.rule_id: finding for finding in report.findings}

    assert findings["memo.heading.route.single"].status == "pass"


def test_review_rendered_document_returns_structured_summary():
    document = parse_file("resources/examples/basic_mfr.Amd")

    report = review_rendered_document(document)
    payload = report.to_dict()

    assert payload["passed"] is True
    assert payload["passing_rules"] > 0
    assert payload["status_counts"]["pass"] > 0
    assert payload["findings"][0]["name"] is not None
    assert payload["findings"][0]["ar_reference"] is not None
