from __future__ import annotations

import re
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from .comparison import ExtractedLayout, ExtractedLine, PageGeometry, extract_layout
from .document import MemoDocument
from .rules import load_typst_layout_rules

SEVERITIES = ("error", "warning", "info")
STATUSES = ("pass", "fail", "skip")
POSITION_TOLERANCE_PT = 4.0
RIGHT_MARGIN_TOLERANCE_PT = 6.0
CENTER_TOLERANCE_PT = 16.0
BOTTOM_REGION_PT = 90.0
DATE_PATTERN = re.compile(
    r"^\d{1,2}\s+(January|February|March|April|May|June|July|"
    r"August|September|October|November|December)\s+\d{4}$",
    re.IGNORECASE,
)
OFFICE_SYMBOL_PATTERN = re.compile(r"^[A-Z]{2,5}(-[A-Z0-9]{1,4})*$", re.IGNORECASE)
VALID_RANKS = {
    "PVT",
    "PV2",
    "PFC",
    "SPC",
    "CPL",
    "SGT",
    "SSG",
    "SFC",
    "MSG",
    "1SG",
    "SGM",
    "CSM",
    "SMA",
    "WO1",
    "CW2",
    "CW3",
    "CW4",
    "CW5",
    "2LT",
    "1LT",
    "CPT",
    "MAJ",
    "LTC",
    "COL",
    "BG",
    "MG",
    "LTG",
    "GEN",
    "GA",
    "MR",
    "MRS",
    "MS",
    "DR",
}
VALID_BRANCHES = {
    "AD",
    "AG",
    "AR",
    "AV",
    "CA",
    "CE",
    "CM",
    "CY",
    "EN",
    "FA",
    "FI",
    "IN",
    "JA",
    "MC",
    "MI",
    "MP",
    "MS",
    "OD",
    "QM",
    "SC",
    "SF",
    "TC",
    "USA",
}

REVIEW_RULE_METADATA: dict[str, dict[str, str]] = {
    "document.organization.complete": {
        "name": "Organization Block Complete",
        "ar_reference": "AR 25-50, para 2-4",
        "suggested_fix": "Provide the organization name, street address, and city/state/ZIP in the memo header.",
    },
    "document.office_symbol.present": {
        "name": "Office Symbol Present",
        "ar_reference": "AR 25-50, para 2-4",
        "suggested_fix": "Add the office symbol line to the memo header.",
    },
    "document.office_symbol.format": {
        "name": "Office Symbol Format",
        "ar_reference": "AR 25-50, para 2-4",
        "suggested_fix": "Use a standard office symbol format such as ATZB-CD-E.",
    },
    "document.date.present": {
        "name": "Date Present",
        "ar_reference": "AR 25-50, para 2-4",
        "suggested_fix": "Add the memo date in DD Month YYYY format.",
    },
    "document.date.format": {
        "name": "Date Format",
        "ar_reference": "AR 25-50, para 2-4",
        "suggested_fix": "Use DD Month YYYY format, for example 15 January 2025.",
    },
    "document.subject.present": {
        "name": "Subject Present",
        "ar_reference": "AR 25-50, para 2-4",
        "suggested_fix": "Add a SUBJECT line before the memo body.",
    },
    "document.subject.style.capitalization": {
        "name": "Subject Capitalization",
        "ar_reference": "AR 25-50, para 2-4",
        "suggested_fix": "Start the subject line with a capital letter.",
    },
    "document.subject.style.terminal_punctuation": {
        "name": "Subject Terminal Punctuation",
        "ar_reference": "AR 25-50, para 2-4",
        "suggested_fix": "Remove the trailing period from the subject line.",
    },
    "document.subject.style.length": {
        "name": "Subject Length",
        "ar_reference": "AR 25-50, para 2-4",
        "suggested_fix": "Keep the subject concise enough to remain readable in the header.",
    },
    "document.body.present": {
        "name": "Body Present",
        "ar_reference": "AR 25-50, para 2-4",
        "suggested_fix": "Add at least one body paragraph to the memo.",
    },
    "document.signature.complete": {
        "name": "Signature Block Complete",
        "ar_reference": "AR 25-50, para 2-5",
        "suggested_fix": "Provide the signer name, rank, and branch in the closing block.",
    },
    "document.routing.present": {
        "name": "Routing Present",
        "ar_reference": "AR 25-50, para 2-4",
        "suggested_fix": "Provide the required FOR or THRU routing block for non-MFR memos.",
    },
    "document.rank.known": {
        "name": "Known Rank Abbreviation",
        "ar_reference": "AR 25-50, para 2-5",
        "suggested_fix": "Use a recognized Army rank abbreviation such as CPT or SGT.",
    },
    "document.branch.known": {
        "name": "Known Branch Abbreviation",
        "ar_reference": "AR 25-50, para 2-5",
        "suggested_fix": "Use a recognized branch abbreviation such as EN, IN, or MI.",
    },
    "memo.heading.letterhead": {
        "name": "Letterhead Geometry",
        "ar_reference": "AR 25-50, fig 2-1 / fig 2-2",
        "suggested_fix": "Align the seal and letterhead lines to the configured first-page geometry.",
    },
    "memo.heading.office_symbol": {
        "name": "Office Symbol Position",
        "ar_reference": "AR 25-50, para 2-4",
        "suggested_fix": "Place the office symbol on the configured first-page left margin line.",
    },
    "memo.heading.date": {
        "name": "Date Alignment",
        "ar_reference": "AR 25-50, para 2-4",
        "suggested_fix": "Align the date with the office-symbol line and flush it to the right margin.",
    },
    "memo.heading.suspense": {
        "name": "Suspense Alignment",
        "ar_reference": "AR 25-50, para 2-4",
        "suggested_fix": "Place the suspense line at the configured first-page right margin.",
    },
    "memo.heading.subject": {
        "name": "Rendered Subject",
        "ar_reference": "AR 25-50, para 2-4",
        "suggested_fix": "Ensure the rendered first page contains the SUBJECT line.",
    },
    "memo.heading.route.single": {
        "name": "Single FOR Wrap Indent",
        "ar_reference": "AR 25-50, para 2-4",
        "suggested_fix": "Indent wrapped single-recipient MEMORANDUM FOR lines by one quarter inch.",
    },
    "memo.closing.authority": {
        "name": "Authority Line Order",
        "ar_reference": "AR 25-50, para 2-5",
        "suggested_fix": "Place the authority line before the signature block when authority is used.",
    },
    "memo.closing.signature": {
        "name": "Signature Block Rendering",
        "ar_reference": "AR 25-50, para 2-5",
        "suggested_fix": "Render the complete signature block on the closing page.",
    },
    "memo.closing.distribution": {
        "name": "Distribution Block Order",
        "ar_reference": "AR 25-50, para 2-6",
        "suggested_fix": "Place the distribution block after the signature block and before CF.",
    },
    "memo.closing.cf": {
        "name": "CF Block Order",
        "ar_reference": "AR 25-50, para 2-6",
        "suggested_fix": "Place the CF block after the distribution block.",
    },
    "memo.continuation.heading": {
        "name": "Continuation Header",
        "ar_reference": "AR 25-50, para 2-4",
        "suggested_fix": "Repeat the office symbol and subject at the configured continuation-page positions.",
    },
    "memo.continuation.page_number": {
        "name": "Continuation Page Number",
        "ar_reference": "AR 25-50, para 2-4",
        "suggested_fix": "Center the continuation page number in the bottom region of each page after page one.",
    },
}


@dataclass(slots=True)
class RenderedPageReview:
    page_number: int
    geometry: PageGeometry
    line_objects: list[ExtractedLine]
    lines: list[str]
    normalized_lines: list[str]
    top_line_objects: list[ExtractedLine]
    top_lines: list[str]
    normalized_top_lines: list[str]
    bottom_line_objects: list[ExtractedLine]
    bottom_lines: list[str]
    normalized_bottom_lines: list[str]


@dataclass(slots=True)
class ReviewFeatures:
    document: MemoDocument
    page_count: int | None = None
    pages: list[RenderedPageReview] = field(default_factory=list)
    layout_rules: dict[str, object] = field(default_factory=load_typst_layout_rules)


@dataclass(slots=True)
class ReviewFinding:
    rule_id: str
    severity: str
    status: str
    message: str
    evidence: dict[str, object] = field(default_factory=dict)
    name: str | None = None
    ar_reference: str | None = None
    suggested_fix: str | None = None

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
            "rule_name": self.name,
            "name": self.name,
            "severity": self.severity,
            "status": self.status,
            "message": self.message,
            "ar_reference": self.ar_reference,
            "suggested_fix": self.suggested_fix,
            "evidence": self.evidence,
        }


@dataclass(slots=True)
class ReviewReport:
    findings: list[ReviewFinding]

    @property
    def passed(self) -> bool:
        return not any(
            finding.status == "fail" and finding.severity != "info"
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

    @property
    def passing_rules(self) -> int:
        return sum(1 for finding in self.findings if finding.status == "pass")

    @property
    def status_counts(self) -> dict[str, int]:
        return {status: sum(1 for finding in self.findings if finding.status == status) for status in STATUSES}

    @property
    def failing_severity_counts(self) -> dict[str, int]:
        return {
            severity: sum(
                1
                for finding in self.findings
                if finding.status == "fail" and finding.severity == severity
            )
            for severity in SEVERITIES
        }

    def to_dict(self) -> dict[str, object]:
        return {
            "passed": self.passed,
            "executed_rules": self.executed_rules,
            "failed_rules": self.failed_rules,
            "skipped_rules": self.skipped_rules,
            "passing_rules": self.passing_rules,
            "status_counts": self.status_counts,
            "failing_severity_counts": self.failing_severity_counts,
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
    findings = [_apply_rule_metadata(rule(features)) for rule in active_rules]
    return ReviewReport(findings=findings)


def review_rendered_document(document: MemoDocument) -> ReviewReport:
    from .renderers.typst import render_typst_pdf

    with tempfile.TemporaryDirectory(prefix="armymemo-rendered-review-") as temp_dir_name:
        output_path = Path(temp_dir_name) / "review.pdf"
        render_typst_pdf(document, output_path)
        return review_document(document, pdf_source=output_path)


def default_document_review_rules() -> list[ReviewRule]:
    return [
        _organization_complete_rule,
        _office_symbol_present_rule,
        _office_symbol_format_rule,
        _date_present_rule,
        _date_format_rule,
        _subject_present_rule,
        _subject_capitalization_rule,
        _subject_terminal_punctuation_rule,
        _subject_length_rule,
        _body_present_rule,
        _signature_complete_rule,
        _routing_rule,
        _rank_known_rule,
        _branch_known_rule,
    ]


def default_rendered_review_rules() -> list[ReviewRule]:
    return [
        _letterhead_geometry_rule,
        _office_symbol_position_rule,
        _date_alignment_rule,
        _suspense_alignment_rule,
        _rendered_subject_rule,
        _single_recipient_route_indent_rule,
        _authority_line_rule,
        _signature_block_rule,
        _distribution_order_rule,
        _cf_order_rule,
        _continuation_heading_rule,
        _continuation_page_number_rule,
    ]


def default_review_rules() -> list[ReviewRule]:
    return [*default_document_review_rules(), *default_rendered_review_rules()]


def _pages_from_layout(layout: ExtractedLayout) -> list[RenderedPageReview]:
    grouped: dict[int, list[ExtractedLine]] = {page.page: [] for page in layout.pages}
    geometry_by_page = {page.page: page for page in layout.pages}
    for line in layout.lines:
        grouped.setdefault(line.page, []).append(line)

    pages: list[RenderedPageReview] = []
    for page_number in sorted(grouped):
        line_objects = grouped[page_number]
        lines = [line.text for line in line_objects]
        normalized = [_normalize_text(line) for line in lines]
        geometry = geometry_by_page[page_number]
        pages.append(
            RenderedPageReview(
                page_number=page_number + 1,
                geometry=geometry,
                line_objects=line_objects,
                lines=lines,
                normalized_lines=normalized,
                top_line_objects=line_objects[:8],
                top_lines=lines[:8],
                normalized_top_lines=normalized[:8],
                bottom_line_objects=line_objects[-8:],
                bottom_lines=lines[-8:],
                normalized_bottom_lines=normalized[-8:],
            )
        )
    return pages


def _apply_rule_metadata(finding: ReviewFinding) -> ReviewFinding:
    metadata = REVIEW_RULE_METADATA.get(finding.rule_id)
    if metadata is None:
        return finding
    if finding.name is None:
        finding.name = metadata["name"]
    if finding.ar_reference is None:
        finding.ar_reference = metadata["ar_reference"]
    if finding.suggested_fix is None:
        finding.suggested_fix = metadata["suggested_fix"]
    return finding


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


def _organization_complete_rule(features: ReviewFeatures) -> ReviewFinding:
    missing = [
        label
        for label, value in [
            ("organization name", features.document.unit_name),
            ("street address", features.document.unit_street_address),
            ("city/state/ZIP", features.document.unit_city_state_zip),
        ]
        if not str(value or "").strip()
    ]
    if not missing:
        return ReviewFinding(
            rule_id="document.organization.complete",
            severity="error",
            status="pass",
            message="Organization block is complete.",
        )
    return ReviewFinding(
        rule_id="document.organization.complete",
        severity="error",
        status="fail",
        message=f"Organization block is missing: {', '.join(missing)}.",
        evidence={"missing_fields": missing},
    )


def _office_symbol_present_rule(features: ReviewFeatures) -> ReviewFinding:
    if features.document.office_symbol.strip():
        return ReviewFinding(
            rule_id="document.office_symbol.present",
            severity="error",
            status="pass",
            message="Office symbol is present.",
        )
    return ReviewFinding(
        rule_id="document.office_symbol.present",
        severity="error",
        status="fail",
        message="Office symbol is missing.",
    )


def _office_symbol_format_rule(features: ReviewFeatures) -> ReviewFinding:
    office_symbol = features.document.office_symbol.strip()
    if not office_symbol:
        return ReviewFinding(
            rule_id="document.office_symbol.format",
            severity="info",
            status="skip",
            message="Office symbol format check skipped because the office symbol is missing.",
        )
    if OFFICE_SYMBOL_PATTERN.match(office_symbol):
        return ReviewFinding(
            rule_id="document.office_symbol.format",
            severity="warning",
            status="pass",
            message="Office symbol matches the expected format.",
        )
    return ReviewFinding(
        rule_id="document.office_symbol.format",
        severity="warning",
        status="fail",
        message=f"Office symbol '{office_symbol}' does not match the expected format.",
        evidence={"office_symbol": office_symbol},
    )


def _date_present_rule(features: ReviewFeatures) -> ReviewFinding:
    if str(features.document.todays_date or "").strip():
        return ReviewFinding(
            rule_id="document.date.present",
            severity="error",
            status="pass",
            message="Date is present.",
        )
    return ReviewFinding(
        rule_id="document.date.present",
        severity="error",
        status="fail",
        message="Date is missing.",
    )


def _date_format_rule(features: ReviewFeatures) -> ReviewFinding:
    date_value = str(features.document.todays_date or "").strip()
    if not date_value:
        return ReviewFinding(
            rule_id="document.date.format",
            severity="info",
            status="skip",
            message="Date format check skipped because the date is missing.",
        )
    if DATE_PATTERN.match(date_value):
        return ReviewFinding(
            rule_id="document.date.format",
            severity="error",
            status="pass",
            message="Date matches DD Month YYYY format.",
        )
    return ReviewFinding(
        rule_id="document.date.format",
        severity="error",
        status="fail",
        message=f"Date '{date_value}' must use DD Month YYYY format.",
        evidence={"date": date_value},
    )


def _subject_capitalization_rule(features: ReviewFeatures) -> ReviewFinding:
    subject = features.document.subject.strip()
    if not subject:
        return ReviewFinding(
            rule_id="document.subject.style.capitalization",
            severity="info",
            status="skip",
            message="Subject capitalization check skipped because the subject is missing.",
        )
    if subject[0].isupper():
        return ReviewFinding(
            rule_id="document.subject.style.capitalization",
            severity="warning",
            status="pass",
            message="Subject starts with a capital letter.",
        )
    return ReviewFinding(
        rule_id="document.subject.style.capitalization",
        severity="warning",
        status="fail",
        message="Subject should start with a capital letter.",
        evidence={"subject": subject},
    )


def _subject_terminal_punctuation_rule(features: ReviewFeatures) -> ReviewFinding:
    subject = features.document.subject.strip()
    if not subject:
        return ReviewFinding(
            rule_id="document.subject.style.terminal_punctuation",
            severity="info",
            status="skip",
            message="Subject punctuation check skipped because the subject is missing.",
        )
    if not subject.endswith("."):
        return ReviewFinding(
            rule_id="document.subject.style.terminal_punctuation",
            severity="warning",
            status="pass",
            message="Subject does not end with terminal punctuation.",
        )
    return ReviewFinding(
        rule_id="document.subject.style.terminal_punctuation",
        severity="warning",
        status="fail",
        message="Subject should not end with a period.",
        evidence={"subject": subject},
    )


def _subject_length_rule(features: ReviewFeatures) -> ReviewFinding:
    subject = features.document.subject.strip()
    if not subject:
        return ReviewFinding(
            rule_id="document.subject.style.length",
            severity="info",
            status="skip",
            message="Subject length check skipped because the subject is missing.",
        )
    if len(subject) <= 150:
        return ReviewFinding(
            rule_id="document.subject.style.length",
            severity="warning",
            status="pass",
            message="Subject length is within the recommended range.",
            evidence={"length": len(subject)},
        )
    return ReviewFinding(
        rule_id="document.subject.style.length",
        severity="warning",
        status="fail",
        message=f"Subject is {len(subject)} characters long; shorten it for readability.",
        evidence={"length": len(subject)},
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


def _rank_known_rule(features: ReviewFeatures) -> ReviewFinding:
    rank = features.document.author_rank.strip().upper()
    if not rank:
        return ReviewFinding(
            rule_id="document.rank.known",
            severity="info",
            status="skip",
            message="Rank recognition check skipped because the rank is missing.",
        )
    if rank in VALID_RANKS:
        return ReviewFinding(
            rule_id="document.rank.known",
            severity="warning",
            status="pass",
            message="Rank abbreviation is recognized.",
            evidence={"rank": rank},
        )
    return ReviewFinding(
        rule_id="document.rank.known",
        severity="warning",
        status="fail",
        message=f"Rank '{rank}' is not a recognized Army abbreviation.",
        evidence={"rank": rank},
    )


def _branch_known_rule(features: ReviewFeatures) -> ReviewFinding:
    branch = features.document.author_branch.strip().upper()
    if not branch:
        return ReviewFinding(
            rule_id="document.branch.known",
            severity="info",
            status="skip",
            message="Branch recognition check skipped because the branch is missing.",
        )
    if branch in VALID_BRANCHES:
        return ReviewFinding(
            rule_id="document.branch.known",
            severity="warning",
            status="pass",
            message="Branch abbreviation is recognized.",
            evidence={"branch": branch},
        )
    return ReviewFinding(
        rule_id="document.branch.known",
        severity="warning",
        status="fail",
        message=f"Branch '{branch}' is not a recognized Army abbreviation.",
        evidence={"branch": branch},
    )


def _letterhead_geometry_rule(features: ReviewFeatures) -> ReviewFinding:
    first_page = _first_page(features, "memo.heading.letterhead")
    if isinstance(first_page, ReviewFinding):
        return first_page

    line_tops = _letterhead_line_tops(features)
    expected_lines = [
        ("DEPARTMENT OF THE ARMY", line_tops[0]),
        (features.document.unit_name, line_tops[1]),
        (features.document.unit_street_address, line_tops[2]),
        (features.document.unit_city_state_zip, line_tops[3]),
    ]
    mismatches: list[dict[str, object]] = []
    for text, expected_y in expected_lines:
        line = _find_line(first_page, text)
        if line is None:
            mismatches.append({"text": text, "expected_y": expected_y, "actual": None})
            continue
        if abs(line.y_pos - expected_y) > POSITION_TOLERANCE_PT:
            mismatches.append(
                {
                    "text": text,
                    "expected_y": expected_y,
                    "actual_y": line.y_pos,
                }
            )

    if not mismatches:
        return ReviewFinding(
            rule_id="memo.heading.letterhead",
            severity="warning",
            status="pass",
            message="Letterhead lines match the configured first-page geometry.",
        )
    return ReviewFinding(
        rule_id="memo.heading.letterhead",
        severity="warning",
        status="fail",
        message="Letterhead lines do not match the configured first-page geometry.",
        evidence={"mismatches": mismatches},
    )


def _office_symbol_position_rule(features: ReviewFeatures) -> ReviewFinding:
    first_page = _first_page(features, "memo.heading.office_symbol")
    if isinstance(first_page, ReviewFinding):
        return first_page

    line = _find_line(first_page, features.document.office_symbol)
    if line is None:
        return ReviewFinding(
            rule_id="memo.heading.office_symbol",
            severity="error",
            status="fail",
            message="Office symbol line is missing from the rendered first page.",
        )

    expected_y = float(features.layout_rules["heading"]["office_symbol_line_top_pt"])
    expected_x = _left_margin(features)
    passed = (
        abs(line.y_pos - expected_y) <= POSITION_TOLERANCE_PT
        and abs(line.x_start - expected_x) <= POSITION_TOLERANCE_PT
    )
    if passed:
        return ReviewFinding(
            rule_id="memo.heading.office_symbol",
            severity="error",
            status="pass",
            message="Office symbol is positioned at the configured first-page origin.",
        )
    return ReviewFinding(
        rule_id="memo.heading.office_symbol",
        severity="error",
        status="fail",
        message="Office symbol is not at the configured first-page origin.",
        evidence={"expected_x": expected_x, "expected_y": expected_y, "actual": _line_geometry(line)},
    )


def _date_alignment_rule(features: ReviewFeatures) -> ReviewFinding:
    if not features.document.todays_date:
        return ReviewFinding(
            rule_id="memo.heading.date",
            severity="info",
            status="skip",
            message="Date alignment check was skipped because the memo has no date.",
        )

    first_page = _first_page(features, "memo.heading.date")
    if isinstance(first_page, ReviewFinding):
        return first_page

    line = _find_line(first_page, features.document.todays_date)
    if line is None:
        return ReviewFinding(
            rule_id="memo.heading.date",
            severity="error",
            status="fail",
            message="Date is missing from the rendered first page.",
        )

    expected_y = float(features.layout_rules["heading"]["office_symbol_line_top_pt"])
    expected_right = _right_margin_target(features, first_page)
    passed = (
        abs(line.y_pos - expected_y) <= POSITION_TOLERANCE_PT
        and abs(line.x_end - expected_right) <= RIGHT_MARGIN_TOLERANCE_PT
    )
    if passed:
        return ReviewFinding(
            rule_id="memo.heading.date",
            severity="error",
            status="pass",
            message="Date is aligned with the office-symbol line and flush to the right margin.",
        )
    return ReviewFinding(
        rule_id="memo.heading.date",
        severity="error",
        status="fail",
        message="Date is not aligned with the configured office-symbol line and right margin.",
        evidence={"expected_y": expected_y, "expected_right": expected_right, "actual": _line_geometry(line)},
    )


def _suspense_alignment_rule(features: ReviewFeatures) -> ReviewFinding:
    if not features.document.suspense_date:
        return ReviewFinding(
            rule_id="memo.heading.suspense",
            severity="info",
            status="skip",
            message="Suspense alignment check was skipped because the memo has no suspense date.",
        )

    first_page = _first_page(features, "memo.heading.suspense")
    if isinstance(first_page, ReviewFinding):
        return first_page

    line = _find_line(first_page, f"S: {features.document.suspense_date}")
    if line is None:
        return ReviewFinding(
            rule_id="memo.heading.suspense",
            severity="error",
            status="fail",
            message="Suspense line is missing from the rendered first page.",
        )

    expected_y = float(features.layout_rules["letterhead"]["suspense_dy_pt"])
    expected_right = _right_margin_target(features, first_page)
    passed = (
        abs(line.y_pos - expected_y) <= POSITION_TOLERANCE_PT
        and abs(line.x_end - expected_right) <= RIGHT_MARGIN_TOLERANCE_PT
    )
    if passed:
        return ReviewFinding(
            rule_id="memo.heading.suspense",
            severity="error",
            status="pass",
            message="Suspense line is placed at the configured first-page right margin.",
        )
    return ReviewFinding(
        rule_id="memo.heading.suspense",
        severity="error",
        status="fail",
        message="Suspense line is not at the configured first-page geometry.",
        evidence={"expected_y": expected_y, "expected_right": expected_right, "actual": _line_geometry(line)},
    )


def _rendered_subject_rule(features: ReviewFeatures) -> ReviewFinding:
    first_page = _first_page(features, "memo.heading.subject")
    if isinstance(first_page, ReviewFinding):
        return first_page

    subject = _find_line(first_page, f"SUBJECT: {features.document.subject}")
    if subject is not None:
        return ReviewFinding(
            rule_id="memo.heading.subject",
            severity="error",
            status="pass",
            message="Subject line is present on the rendered first page.",
        )
    return ReviewFinding(
        rule_id="memo.heading.subject",
        severity="error",
        status="fail",
        message="Subject line is missing from the rendered first page.",
    )


def _single_recipient_route_indent_rule(features: ReviewFeatures) -> ReviewFinding:
    document = features.document
    if document.thru_recipients or len(document.for_recipients) != 1:
        return ReviewFinding(
            rule_id="memo.heading.route.single",
            severity="info",
            status="skip",
            message="Single-recipient route indentation check did not apply to this memo.",
        )

    first_page = _first_page(features, "memo.heading.route.single")
    if isinstance(first_page, ReviewFinding):
        return first_page

    subject_line = _find_line(first_page, f"SUBJECT: {document.subject}")
    if subject_line is None:
        return ReviewFinding(
            rule_id="memo.heading.route.single",
            severity="warning",
            status="fail",
            message="Could not locate the subject line while checking wrapped route indentation.",
        )

    route_lines = [
        line
        for line in first_page.line_objects
        if 140 <= line.y_pos < subject_line.y_pos
    ]
    if len(route_lines) <= 1:
        return ReviewFinding(
            rule_id="memo.heading.route.single",
            severity="info",
            status="skip",
            message="Single-recipient route indentation check was skipped because the route did not wrap.",
        )

    expected_x = _left_margin(features) + float(features.layout_rules["route"]["hanging_indent_pt"])
    failures = [
        _line_geometry(line)
        for line in route_lines[1:]
        if abs(line.x_start - expected_x) > POSITION_TOLERANCE_PT
    ]
    if not failures:
        return ReviewFinding(
            rule_id="memo.heading.route.single",
            severity="error",
            status="pass",
            message="Wrapped single-recipient route lines use the configured hanging indent.",
        )
    return ReviewFinding(
        rule_id="memo.heading.route.single",
        severity="error",
        status="fail",
        message="Wrapped single-recipient route lines do not use the configured hanging indent.",
        evidence={"expected_x": expected_x, "lines": failures},
    )


def _authority_line_rule(features: ReviewFeatures) -> ReviewFinding:
    if not features.document.authority:
        return ReviewFinding(
            rule_id="memo.closing.authority",
            severity="info",
            status="skip",
            message="Authority-line check was skipped because the memo has no authority line.",
        )

    last_page = _last_page(features, "memo.closing.authority")
    if isinstance(last_page, ReviewFinding):
        return last_page

    authority = _find_line(last_page, _authority_text(features.document))
    signature = _find_line(last_page, features.document.author_name.upper())
    if authority is None:
        return ReviewFinding(
            rule_id="memo.closing.authority",
            severity="error",
            status="fail",
            message="Authority line is missing from the rendered closing block.",
        )
    if signature is None:
        return ReviewFinding(
            rule_id="memo.closing.authority",
            severity="warning",
            status="fail",
            message="Authority line was found, but the signature block was not detected.",
            evidence={"authority": _line_geometry(authority)},
        )
    if authority.y_pos < signature.y_pos:
        return ReviewFinding(
            rule_id="memo.closing.authority",
            severity="error",
            status="pass",
            message="Authority line is present before the signature block.",
        )
    return ReviewFinding(
        rule_id="memo.closing.authority",
        severity="error",
        status="fail",
        message="Authority line appears below the signature block.",
        evidence={"authority": _line_geometry(authority), "signature": _line_geometry(signature)},
    )


def _signature_block_rule(features: ReviewFeatures) -> ReviewFinding:
    last_page = _last_page(features, "memo.closing.signature")
    if isinstance(last_page, ReviewFinding):
        return last_page

    expected_texts = [
        features.document.author_name.upper(),
        f"{features.document.author_rank}, {features.document.author_branch}",
    ]
    if features.document.author_title:
        expected_texts.append(features.document.author_title)

    missing = [text for text in expected_texts if _find_line(last_page, text) is None]
    if not missing:
        return ReviewFinding(
            rule_id="memo.closing.signature",
            severity="error",
            status="pass",
            message="Rendered signature block contains the expected signature lines.",
        )
    return ReviewFinding(
        rule_id="memo.closing.signature",
        severity="error",
        status="fail",
        message="Rendered signature block is missing expected signature lines.",
        evidence={"missing": missing},
    )


def _distribution_order_rule(features: ReviewFeatures) -> ReviewFinding:
    if not features.document.distros:
        return ReviewFinding(
            rule_id="memo.closing.distribution",
            severity="info",
            status="skip",
            message="Distribution check was skipped because the memo has no distribution list.",
        )

    last_page = _last_page(features, "memo.closing.distribution")
    if isinstance(last_page, ReviewFinding):
        return last_page

    distribution = _find_line(last_page, "DISTRIBUTION:")
    signature = _find_line(last_page, features.document.author_name.upper())
    cf = _find_line(last_page, "CF:")
    missing = [value for value in features.document.distros if _find_line(last_page, value) is None]
    if distribution is None or missing:
        return ReviewFinding(
            rule_id="memo.closing.distribution",
            severity="error",
            status="fail",
            message="Distribution block is missing expected title or entries.",
            evidence={"missing_entries": missing, "has_title": distribution is not None},
        )
    if signature is not None and distribution.y_pos <= signature.y_pos:
        return ReviewFinding(
            rule_id="memo.closing.distribution",
            severity="error",
            status="fail",
            message="Distribution block appears above the signature block.",
            evidence={"distribution": _line_geometry(distribution), "signature": _line_geometry(signature)},
        )
    if cf is not None and distribution.y_pos >= cf.y_pos:
        return ReviewFinding(
            rule_id="memo.closing.distribution",
            severity="error",
            status="fail",
            message="Distribution block appears below the CF block.",
            evidence={"distribution": _line_geometry(distribution), "cf": _line_geometry(cf)},
        )
    return ReviewFinding(
        rule_id="memo.closing.distribution",
        severity="error",
        status="pass",
        message="Distribution block is present after the signature block and before CF.",
    )


def _cf_order_rule(features: ReviewFeatures) -> ReviewFinding:
    if not features.document.cfs:
        return ReviewFinding(
            rule_id="memo.closing.cf",
            severity="info",
            status="skip",
            message="CF check was skipped because the memo has no CF block.",
        )

    last_page = _last_page(features, "memo.closing.cf")
    if isinstance(last_page, ReviewFinding):
        return last_page

    cf = _find_line(last_page, "CF:")
    distribution = _find_line(last_page, "DISTRIBUTION:")
    missing = [value for value in features.document.cfs if _find_line(last_page, value) is None]
    if cf is None or missing:
        return ReviewFinding(
            rule_id="memo.closing.cf",
            severity="error",
            status="fail",
            message="CF block is missing expected title or entries.",
            evidence={"missing_entries": missing, "has_title": cf is not None},
        )
    if distribution is not None and cf.y_pos <= distribution.y_pos:
        return ReviewFinding(
            rule_id="memo.closing.cf",
            severity="error",
            status="fail",
            message="CF block appears above the distribution block.",
            evidence={"distribution": _line_geometry(distribution), "cf": _line_geometry(cf)},
        )
    return ReviewFinding(
        rule_id="memo.closing.cf",
        severity="error",
        status="pass",
        message="CF block is present after the distribution block.",
    )


def _continuation_heading_rule(features: ReviewFeatures) -> ReviewFinding:
    if features.page_count is None:
        return ReviewFinding(
            rule_id="memo.continuation.heading",
            severity="warning",
            status="skip",
            message="Continuation-heading check was skipped because no PDF was provided.",
        )
    if features.page_count <= 1:
        return ReviewFinding(
            rule_id="memo.continuation.heading",
            severity="info",
            status="skip",
            message="Continuation-heading check was skipped because the memo is one page.",
        )

    expected_office_y = float(features.layout_rules["continuation"]["office_symbol_top_pt"])
    expected_subject_y = float(features.layout_rules["continuation"]["subject_top_pt"])
    expected_x = _left_margin(features)
    failures: list[dict[str, object]] = []
    for page in features.pages[1:]:
        office = _find_line(page, features.document.office_symbol)
        subject = _find_line(page, f"SUBJECT: {features.document.subject}")
        if office is None or subject is None:
            failures.append(
                {
                    "page": page.page_number,
                    "missing": [
                        name
                        for name, line in [("office_symbol", office), ("subject", subject)]
                        if line is None
                    ],
                }
            )
            continue
        if abs(office.y_pos - expected_office_y) > POSITION_TOLERANCE_PT or abs(office.x_start - expected_x) > POSITION_TOLERANCE_PT:
            failures.append({"page": page.page_number, "line": "office_symbol", "actual": _line_geometry(office)})
        if abs(subject.y_pos - expected_subject_y) > POSITION_TOLERANCE_PT or abs(subject.x_start - expected_x) > POSITION_TOLERANCE_PT:
            failures.append({"page": page.page_number, "line": "subject", "actual": _line_geometry(subject)})

    if not failures:
        return ReviewFinding(
            rule_id="memo.continuation.heading",
            severity="error",
            status="pass",
            message="All continuation pages include the configured office-symbol and subject geometry.",
        )
    return ReviewFinding(
        rule_id="memo.continuation.heading",
        severity="error",
        status="fail",
        message="One or more continuation pages do not match the configured header geometry.",
        evidence={"pages": failures},
    )


def _continuation_page_number_rule(features: ReviewFeatures) -> ReviewFinding:
    if features.page_count is None:
        return ReviewFinding(
            rule_id="memo.continuation.page_number",
            severity="warning",
            status="skip",
            message="Continuation-page number check was skipped because no PDF was provided.",
        )
    if features.page_count <= 1:
        return ReviewFinding(
            rule_id="memo.continuation.page_number",
            severity="info",
            status="skip",
            message="Continuation-page number check was skipped because the memo is one page.",
        )

    failures: list[dict[str, object]] = []
    for page in features.pages[1:]:
        page_number_line = _find_exact_line(page.bottom_line_objects, str(page.page_number))
        if page_number_line is None:
            failures.append({"page": page.page_number, "missing": "page_number"})
            continue
        center_delta = abs(page_number_line.x_center - (page.geometry.width / 2))
        if center_delta > CENTER_TOLERANCE_PT or page_number_line.y_pos < (page.geometry.height - BOTTOM_REGION_PT):
            failures.append(
                {
                    "page": page.page_number,
                    "actual": _line_geometry(page_number_line),
                    "center_delta": round(center_delta, 1),
                }
            )

    if not failures:
        return ReviewFinding(
            rule_id="memo.continuation.page_number",
            severity="error",
            status="pass",
            message="All continuation pages include a centered page number in the bottom region.",
        )
    return ReviewFinding(
        rule_id="memo.continuation.page_number",
        severity="error",
        status="fail",
        message="One or more continuation pages are missing or misplacing the page number.",
        evidence={"pages": failures},
    )


def _first_page(
    features: ReviewFeatures,
    rule_id: str,
) -> RenderedPageReview | ReviewFinding:
    if not features.pages:
        return ReviewFinding(
            rule_id=rule_id,
            severity="warning",
            status="skip",
            message="PDF-derived checks were skipped because no PDF was provided.",
        )
    return features.pages[0]


def _last_page(
    features: ReviewFeatures,
    rule_id: str,
) -> RenderedPageReview | ReviewFinding:
    if not features.pages:
        return ReviewFinding(
            rule_id=rule_id,
            severity="warning",
            status="skip",
            message="PDF-derived checks were skipped because no PDF was provided.",
        )
    return features.pages[-1]


def _find_line(page: RenderedPageReview, text: str) -> ExtractedLine | None:
    normalized = _normalize_text(text)
    for line in page.line_objects:
        if normalized in _normalize_text(line.text):
            return line
    return None


def _find_exact_line(lines: list[ExtractedLine], text: str) -> ExtractedLine | None:
    normalized = _normalize_text(text)
    for line in lines:
        if _normalize_text(line.text) == normalized:
            return line
    return None


def _line_geometry(line: ExtractedLine) -> dict[str, float]:
    return {
        "x_start": line.x_start,
        "x_end": line.x_end,
        "x_center": line.x_center,
        "y_pos": line.y_pos,
        "y_end": line.y_end,
    }


def _authority_text(document: MemoDocument) -> str:
    return f"{document.authority.rstrip(':').upper()}:"


def _left_margin(features: ReviewFeatures) -> float:
    return float(features.layout_rules["page_margin"]["left"])


def _right_margin_target(features: ReviewFeatures, page: RenderedPageReview) -> float:
    return round(page.geometry.width - float(features.layout_rules["page_margin"]["right"]), 1)


def _letterhead_top(features: ReviewFeatures) -> float:
    return float(features.layout_rules["letterhead"]["header_top_pt"])


def _letterhead_line_tops(features: ReviewFeatures) -> tuple[float, float, float, float]:
    top = _letterhead_top(features)
    department_size = float(features.layout_rules["letterhead"]["department_font_size_pt"])
    detail_size = float(features.layout_rules["letterhead"]["detail_font_size_pt"])
    gap = float(features.layout_rules["letterhead"]["header_line_gap_pt"])
    detail_top = top + department_size + gap
    return (
        top,
        detail_top,
        detail_top + detail_size + gap,
        detail_top + ((detail_size + gap) * 2),
    )


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", "", text).upper().strip()
