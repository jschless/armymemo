from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Callable

from .comparison import ExtractedLayout, extract_layout
from .document import MemoDocument

SEVERITIES = ("error", "warning", "info")
STATUSES = ("pass", "fail", "skip")


@dataclass(slots=True)
class RenderedPageReview:
    page_number: int
    lines: list[str]
    normalized_lines: list[str]
    top_lines: list[str]
    normalized_top_lines: list[str]
    bottom_lines: list[str]
    normalized_bottom_lines: list[str]


@dataclass(slots=True)
class ReviewFeatures:
    document: MemoDocument
    page_count: int | None = None
    pages: list[RenderedPageReview] = field(default_factory=list)


@dataclass(slots=True)
class ReviewFinding:
    rule_id: str
    severity: str
    status: str
    message: str
    evidence: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.severity not in SEVERITIES:
            raise ValueError(f"Unsupported severity: {self.severity}")
        if self.status not in STATUSES:
            raise ValueError(f"Unsupported status: {self.status}")

    @property
    def passed(self) -> bool:
        return self.status == "pass"

    def to_dict(self) -> dict[str, object]:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "status": self.status,
            "message": self.message,
            "evidence": self.evidence,
        }


@dataclass(slots=True)
class ReviewReport:
    findings: list[ReviewFinding]

    @property
    def passed(self) -> bool:
        return not any(
            finding.status == "fail" and finding.severity == "error"
            for finding in self.findings
        )

    @property
    def executed_rules(self) -> int:
        return sum(1 for finding in self.findings if finding.status != "skip")

    @property
    def failed_rules(self) -> int:
        return sum(1 for finding in self.findings if finding.status == "fail")

    @property
    def skipped_rules(self) -> int:
        return sum(1 for finding in self.findings if finding.status == "skip")

    def to_dict(self) -> dict[str, object]:
        return {
            "passed": self.passed,
            "executed_rules": self.executed_rules,
            "failed_rules": self.failed_rules,
            "skipped_rules": self.skipped_rules,
            "findings": [finding.to_dict() for finding in self.findings],
        }


ReviewRule = Callable[[ReviewFeatures], ReviewFinding]


def extract_review_features(
    document: MemoDocument,
    pdf_source: str | Path | bytes | None = None,
) -> ReviewFeatures:
    if pdf_source is None:
        return ReviewFeatures(document=document)

    layout = extract_layout(pdf_source)
    return ReviewFeatures(
        document=document,
        page_count=layout.page_count,
        pages=_pages_from_layout(layout),
    )


def review_document(
    document: MemoDocument,
    *,
    pdf_source: str | Path | bytes | None = None,
    rules: list[ReviewRule] | None = None,
) -> ReviewReport:
    features = extract_review_features(document, pdf_source=pdf_source)
    active_rules = rules or default_review_rules()
    return ReviewReport(findings=[rule(features) for rule in active_rules])


def default_review_rules() -> list[ReviewRule]:
    return [
        _subject_present_rule,
        _body_present_rule,
        _signature_complete_rule,
        _routing_rule,
        _first_page_header_rule,
        _continuation_header_rule,
        _continuation_page_number_rule,
    ]


def _pages_from_layout(layout: ExtractedLayout) -> list[RenderedPageReview]:
    grouped: dict[int, list[str]] = {page.page: [] for page in layout.pages}
    for line in layout.lines:
        grouped.setdefault(line.page, []).append(line.text)

    pages: list[RenderedPageReview] = []
    for page_number in sorted(grouped):
        lines = grouped[page_number]
        normalized = [_normalize_text(line) for line in lines]
        pages.append(
            RenderedPageReview(
                page_number=page_number + 1,
                lines=lines,
                normalized_lines=normalized,
                top_lines=lines[:6],
                normalized_top_lines=normalized[:6],
                bottom_lines=lines[-6:],
                normalized_bottom_lines=normalized[-6:],
            )
        )
    return pages


def _subject_present_rule(features: ReviewFeatures) -> ReviewFinding:
    if features.document.subject.strip():
        return ReviewFinding(
            rule_id="document.subject.present",
            severity="error",
            status="pass",
            message="Subject line is present.",
        )
    return ReviewFinding(
        rule_id="document.subject.present",
        severity="error",
        status="fail",
        message="Subject line is missing.",
    )


def _body_present_rule(features: ReviewFeatures) -> ReviewFinding:
    if features.document.body:
        return ReviewFinding(
            rule_id="document.body.present",
            severity="error",
            status="pass",
            message="Body content is present.",
            evidence={"body_items": len(features.document.body)},
        )
    return ReviewFinding(
        rule_id="document.body.present",
        severity="error",
        status="fail",
        message="Body content is missing.",
    )


def _signature_complete_rule(features: ReviewFeatures) -> ReviewFinding:
    missing = [
        name
        for name, value in [
            ("author_name", features.document.author_name),
            ("author_rank", features.document.author_rank),
            ("author_branch", features.document.author_branch),
        ]
        if not value.strip()
    ]
    if not missing:
        return ReviewFinding(
            rule_id="document.signature.complete",
            severity="error",
            status="pass",
            message="Signature block has name, rank, and branch.",
        )
    return ReviewFinding(
        rule_id="document.signature.complete",
        severity="error",
        status="fail",
        message="Signature block is incomplete.",
        evidence={"missing_fields": missing},
    )


def _routing_rule(features: ReviewFeatures) -> ReviewFinding:
    document = features.document
    has_routing = bool(document.for_recipients or document.thru_recipients)
    if has_routing or document.memo_type == "MEMORANDUM FOR RECORD":
        return ReviewFinding(
            rule_id="document.routing.present",
            severity="error",
            status="pass",
            message="Routing information matches the memo type.",
            evidence={
                "memo_type": document.memo_type,
                "for_count": len(document.for_recipients),
                "thru_count": len(document.thru_recipients),
            },
        )
    return ReviewFinding(
        rule_id="document.routing.present",
        severity="error",
        status="fail",
        message="Routing information is missing for a non-MFR memo.",
        evidence={"memo_type": document.memo_type},
    )


def _first_page_header_rule(features: ReviewFeatures) -> ReviewFinding:
    if not features.pages:
        return ReviewFinding(
            rule_id="pdf.first_page_header.present",
            severity="warning",
            status="skip",
            message="PDF-derived checks were skipped because no PDF was provided.",
        )

    page = features.pages[0]
    office_symbol = _normalize_text(features.document.office_symbol)
    subject = _normalize_text(f"SUBJECT: {features.document.subject}")
    top_area = page.normalized_lines[:10]
    missing: list[str] = []
    if not any(office_symbol in line for line in top_area):
        missing.append("office_symbol")
    if not any(subject in line for line in page.normalized_lines):
        missing.append("subject")
    if not missing:
        return ReviewFinding(
            rule_id="pdf.first_page_header.present",
            severity="warning",
            status="pass",
            message="First-page office symbol and subject are present in the rendered PDF.",
        )
    return ReviewFinding(
        rule_id="pdf.first_page_header.present",
        severity="warning",
        status="fail",
        message="First-page header information is missing from the rendered PDF.",
        evidence={"missing": missing, "page": 1},
    )


def _continuation_header_rule(features: ReviewFeatures) -> ReviewFinding:
    if features.page_count is None:
        return ReviewFinding(
            rule_id="pdf.continuation_header.present",
            severity="warning",
            status="skip",
            message="Continuation-page header check was skipped because no PDF was provided.",
        )
    if features.page_count <= 1:
        return ReviewFinding(
            rule_id="pdf.continuation_header.present",
            severity="info",
            status="skip",
            message="Continuation-page header check was skipped because the memo is one page.",
        )

    office_symbol = _normalize_text(features.document.office_symbol)
    subject = _normalize_text(f"SUBJECT: {features.document.subject}")
    missing_pages: list[int] = []
    for page in features.pages[1:]:
        has_office = any(office_symbol in line for line in page.normalized_top_lines)
        has_subject = any(subject in line for line in page.normalized_top_lines)
        if not (has_office and has_subject):
            missing_pages.append(page.page_number)

    if not missing_pages:
        return ReviewFinding(
            rule_id="pdf.continuation_header.present",
            severity="error",
            status="pass",
            message="All continuation pages include the office symbol and subject header.",
        )
    return ReviewFinding(
        rule_id="pdf.continuation_header.present",
        severity="error",
        status="fail",
        message="One or more continuation pages are missing the expected header.",
        evidence={"pages": missing_pages},
    )


def _continuation_page_number_rule(features: ReviewFeatures) -> ReviewFinding:
    if features.page_count is None:
        return ReviewFinding(
            rule_id="pdf.continuation_page_number.present",
            severity="warning",
            status="skip",
            message="Continuation-page number check was skipped because no PDF was provided.",
        )
    if features.page_count <= 1:
        return ReviewFinding(
            rule_id="pdf.continuation_page_number.present",
            severity="info",
            status="skip",
            message="Continuation-page number check was skipped because the memo is one page.",
        )

    missing_pages = [
        page.page_number
        for page in features.pages[1:]
        if str(page.page_number) not in page.normalized_bottom_lines
    ]
    if not missing_pages:
        return ReviewFinding(
            rule_id="pdf.continuation_page_number.present",
            severity="error",
            status="pass",
            message="All continuation pages include a page number.",
        )
    return ReviewFinding(
        rule_id="pdf.continuation_page_number.present",
        severity="error",
        status="fail",
        message="One or more continuation pages are missing a page number.",
        evidence={"pages": missing_pages},
    )


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", "", text).upper().strip()
