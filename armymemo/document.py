from __future__ import annotations

from dataclasses import dataclass, field

import yaml


@dataclass(slots=True)
class Recipient:
    name: str
    street_address: str
    city_state_zip: str

    def to_dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "street_address": self.street_address,
            "city_state_zip": self.city_state_zip,
        }


@dataclass(slots=True)
class TableBlock:
    headers: list[str]
    rows: list[list[str]]

    def normalized_rows(self) -> list[list[str]]:
        width_candidates = [len(self.headers), *(len(row) for row in self.rows)]
        width = max(width_candidates) if width_candidates else 0
        headers = self.headers + [""] * max(0, width - len(self.headers))
        rows = [row + [""] * max(0, width - len(row)) for row in self.rows]
        self.headers = headers
        self.rows = rows
        return rows

    def to_dict(self) -> dict[str, list[list[str]] | list[str]]:
        return {"type": "table", "headers": self.headers, "rows": self.rows}


BodyNode = "BodyItem | TableBlock"


@dataclass(slots=True)
class BodyItem:
    paragraphs: list[str]
    children: list[BodyItem | TableBlock] = field(default_factory=list)

    @property
    def text(self) -> str:
        return self.paragraphs[0] if self.paragraphs else ""

    def to_dict(self) -> dict[str, object]:
        data: dict[str, object] = {"type": "item", "paragraphs": list(self.paragraphs)}
        if self.children:
            data["children"] = [child.to_dict() for child in self.children]
        return data


@dataclass(slots=True)
class MemoDocument:
    unit_name: str
    unit_street_address: str
    unit_city_state_zip: str
    office_symbol: str
    subject: str
    body: list[BodyItem | TableBlock]
    author_name: str
    author_rank: str
    author_branch: str
    author_title: str | None = None
    memo_type: str = "MEMORANDUM FOR RECORD"
    todays_date: str | None = None
    for_recipients: list[Recipient] = field(default_factory=list)
    thru_recipients: list[Recipient] = field(default_factory=list)
    suspense_date: str | None = None
    document_mark: str | None = None
    enclosures: list[str] = field(default_factory=list)
    distros: list[str] = field(default_factory=list)
    cfs: list[str] = field(default_factory=list)
    authority: str | None = None

    def __post_init__(self) -> None:
        if not self.memo_type:
            self.memo_type = self.infer_memo_type()

    def infer_memo_type(self) -> str:
        if self.thru_recipients:
            return "MEMORANDUM THRU"
        if self.for_recipients:
            return "MEMORANDUM FOR"
        return "MEMORANDUM FOR RECORD"

    def to_metadata_dict(self) -> dict[str, object]:
        data: dict[str, object] = {
            "unit": {
                "name": self.unit_name,
                "street_address": self.unit_street_address,
                "city_state_zip": self.unit_city_state_zip,
            },
            "office_symbol": self.office_symbol,
            "subject": self.subject,
            "date": self.todays_date,
            "memo_type": self.memo_type,
            "author": {
                "name": self.author_name,
                "rank": self.author_rank,
                "branch": self.author_branch,
                "title": self.author_title,
            },
        }
        if self.for_recipients:
            data["for"] = [recipient.to_dict() for recipient in self.for_recipients]
        if self.thru_recipients:
            data["thru"] = [recipient.to_dict() for recipient in self.thru_recipients]
        if self.suspense_date:
            data["suspense_date"] = self.suspense_date
        if self.document_mark:
            data["document_mark"] = self.document_mark
        if self.enclosures:
            data["enclosures"] = list(self.enclosures)
        if self.distros:
            data["distros"] = list(self.distros)
        if self.cfs:
            data["cfs"] = list(self.cfs)
        if self.authority:
            data["authority"] = self.authority
        return data

    def to_dict(self) -> dict[str, object]:
        data = self.to_metadata_dict()
        data["body"] = [node.to_dict() for node in self.body]
        return data

    def to_memodoc(self) -> str:
        metadata = yaml.safe_dump(
            self.to_metadata_dict(),
            sort_keys=False,
            allow_unicode=False,
            default_flow_style=False,
        ).strip()
        body = body_to_markdown(self.body).rstrip()
        return f"---\n{metadata}\n---\n{body}\n"

    def to_amd(self) -> str:
        lines = [
            f"ORGANIZATION_NAME = {self.unit_name}",
            f"ORGANIZATION_STREET_ADDRESS = {self.unit_street_address}",
            f"ORGANIZATION_CITY_STATE_ZIP = {self.unit_city_state_zip}",
            "",
            f"OFFICE_SYMBOL = {self.office_symbol}",
        ]
        if self.todays_date:
            lines.append(f"DATE = {self.todays_date}")
        lines.extend(
            [
                f"AUTHOR = {self.author_name}",
                f"RANK = {self.author_rank}",
                f"BRANCH = {self.author_branch}",
            ]
        )
        if self.author_title:
            lines.append(f"TITLE = {self.author_title}")
        if self.suspense_date:
            lines.append(f"SUSPENSE = {self.suspense_date}")
        if self.authority:
            lines.append(f"AUTHORITY = {self.authority}")
        for key, recipients in [
            ("FOR", self.for_recipients),
            ("THRU", self.thru_recipients),
        ]:
            if recipients:
                lines.append("")
                for recipient in recipients:
                    lines.extend(
                        [
                            f"{key}_ORGANIZATION_NAME = {recipient.name}",
                            f"{key}_ORGANIZATION_STREET_ADDRESS = {recipient.street_address}",
                            f"{key}_ORGANIZATION_CITY_STATE_ZIP = {recipient.city_state_zip}",
                        ]
                    )
        for key, values in [
            ("ENCLOSURE", self.enclosures),
            ("DISTRO", self.distros),
            ("CF", self.cfs),
        ]:
            if values:
                lines.append("")
                lines.extend(f"{key} = {value}" for value in values)
        lines.extend(["", f"SUBJECT = {self.subject}", "", body_to_markdown(self.body).rstrip()])
        return "\n".join(lines).rstrip() + "\n"


def body_to_markdown(nodes: list[BodyItem | TableBlock], indent: int = 0) -> str:
    lines: list[str] = []
    prefix = " " * indent
    for node in nodes:
        if isinstance(node, TableBlock):
            headers = node.headers
            rows = node.normalized_rows()
            if not headers:
                continue
            lines.append(f"{prefix}| " + " | ".join(headers) + " |")
            lines.append(
                f"{prefix}| " + " | ".join("---" for _ in headers) + " |"
            )
            for row in rows:
                lines.append(f"{prefix}| " + " | ".join(row) + " |")
            lines.append("")
            continue

        if not node.paragraphs:
            continue
        lines.append(f"{prefix}- {node.paragraphs[0]}")
        for paragraph in node.paragraphs[1:]:
            lines.append(f"{prefix}{paragraph}")
        if node.children:
            child_block = body_to_markdown(node.children, indent + 4).rstrip()
            if child_block:
                lines.append(child_block)
        lines.append("")
    return "\n".join(lines).rstrip() + ("\n" if lines else "")
