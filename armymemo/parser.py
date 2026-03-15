from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from .document import BodyItem, MemoDocument, Recipient, TableBlock
from .exceptions import MemoParseError

KEY_MAP = {
    "ORGANIZATION_NAME": "unit_name",
    "ORGANIZATION_STREET_ADDRESS": "unit_street_address",
    "ORGANIZATION_CITY_STATE_ZIP": "unit_city_state_zip",
    "OFFICE_SYMBOL": "office_symbol",
    "DATE": "todays_date",
    "AUTHOR": "author_name",
    "RANK": "author_rank",
    "BRANCH": "author_branch",
    "TITLE": "author_title",
    "MEMO_TYPE": "memo_type",
    "SUBJECT": "subject",
    "FOR_ORGANIZATION_NAME": "for_unit_name",
    "FOR_ORGANIZATION_STREET_ADDRESS": "for_unit_street_address",
    "FOR_ORGANIZATION_CITY_STATE_ZIP": "for_unit_city_state_zip",
    "THRU_ORGANIZATION_NAME": "thru_unit_name",
    "THRU_ORGANIZATION_STREET_ADDRESS": "thru_unit_street_address",
    "THRU_ORGANIZATION_CITY_STATE_ZIP": "thru_unit_city_state_zip",
    "ENCLOSURE": "enclosures",
    "DISTRO": "distros",
    "CF": "cfs",
    "DOCUMENT_MARK": "document_mark",
    "SUSPENSE": "suspense_date",
    "AUTHORITY": "authority",
}

LIST_KEYS = {
    "for_unit_name",
    "for_unit_street_address",
    "for_unit_city_state_zip",
    "thru_unit_name",
    "thru_unit_street_address",
    "thru_unit_city_state_zip",
    "enclosures",
    "distros",
    "cfs",
}

BULLET_RE = re.compile(r"^(?P<indent>\s*)-\s+(?P<text>.+)$")


@dataclass(slots=True)
class _LegacyMemoFields:
    values: dict[str, object]

    def build_document(self, body: list[BodyItem | TableBlock]) -> MemoDocument:
        recipients_for = _zip_recipients(
            self.values.get("for_unit_name"),
            self.values.get("for_unit_street_address"),
            self.values.get("for_unit_city_state_zip"),
        )
        recipients_thru = _zip_recipients(
            self.values.get("thru_unit_name"),
            self.values.get("thru_unit_street_address"),
            self.values.get("thru_unit_city_state_zip"),
        )
        return MemoDocument(
            unit_name=_required(self.values, "unit_name"),
            unit_street_address=_required(self.values, "unit_street_address"),
            unit_city_state_zip=_required(self.values, "unit_city_state_zip"),
            office_symbol=_required(self.values, "office_symbol"),
            subject=_required(self.values, "subject"),
            body=body,
            author_name=_required(self.values, "author_name"),
            author_rank=_required(self.values, "author_rank"),
            author_branch=_required(self.values, "author_branch"),
            author_title=self.values.get("author_title"),
            memo_type=str(self.values.get("memo_type") or ""),
            todays_date=self.values.get("todays_date"),
            for_recipients=recipients_for,
            thru_recipients=recipients_thru,
            suspense_date=self.values.get("suspense_date"),
            document_mark=self.values.get("document_mark"),
            enclosures=list(self.values.get("enclosures", [])),
            distros=list(self.values.get("distros", [])),
            cfs=list(self.values.get("cfs", [])),
            authority=self.values.get("authority"),
        )


def parse_file(path: str | Path) -> MemoDocument:
    return parse_text(Path(path).read_text(encoding="utf-8"))


def parse_text(text: str) -> MemoDocument:
    stripped = text.lstrip()
    if stripped.startswith("---"):
        return _parse_memodoc(text)
    return _parse_legacy_amd(text)


def _parse_memodoc(text: str) -> MemoDocument:
    lines = text.splitlines()
    start = next((idx for idx, line in enumerate(lines) if line.strip()), None)
    if start is None or lines[start].strip() != "---":
        raise MemoParseError("MemoDoc input must begin with YAML front matter")

    end = next(
        (idx for idx in range(start + 1, len(lines)) if lines[idx].strip() == "---"),
        None,
    )
    if end is None:
        raise MemoParseError("MemoDoc front matter is missing a closing --- line")

    metadata = yaml.safe_load("\n".join(lines[start + 1 : end])) or {}
    if not isinstance(metadata, dict):
        raise MemoParseError("MemoDoc front matter must decode to a mapping")

    body_text = "\n".join(lines[end + 1 :])
    body = parse_body_lines(body_text.splitlines())
    return _build_memodoc_document(metadata, body)


def _build_memodoc_document(
    metadata: dict[str, object],
    body: list[BodyItem | TableBlock],
) -> MemoDocument:
    unit = metadata.get("unit", {})
    author = metadata.get("author", {})
    if not isinstance(unit, dict) or not isinstance(author, dict):
        raise MemoParseError("MemoDoc unit and author blocks must be mappings")

    return MemoDocument(
        unit_name=str(unit.get("name", "")),
        unit_street_address=str(unit.get("street_address", "")),
        unit_city_state_zip=str(unit.get("city_state_zip", "")),
        office_symbol=str(metadata.get("office_symbol", "")),
        subject=str(metadata.get("subject", "")),
        body=body,
        author_name=str(author.get("name", "")),
        author_rank=str(author.get("rank", "")),
        author_branch=str(author.get("branch", "")),
        author_title=_optional_str(author.get("title")),
        memo_type=_normalize_memo_type(_optional_str(metadata.get("memo_type"))),
        todays_date=_optional_str(metadata.get("date") or metadata.get("todays_date")),
        for_recipients=_parse_recipients(metadata.get("for")),
        thru_recipients=_parse_recipients(metadata.get("thru")),
        suspense_date=_optional_str(metadata.get("suspense_date")),
        document_mark=_optional_str(metadata.get("document_mark")),
        enclosures=_string_list(metadata.get("enclosures")),
        distros=_string_list(metadata.get("distros")),
        cfs=_string_list(metadata.get("cfs")),
        authority=_optional_str(metadata.get("authority")),
    )


def _parse_legacy_amd(text: str) -> MemoDocument:
    file_lines = [
        line
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    try:
        subject_index = next(
            index for index, line in enumerate(file_lines) if line.split("=")[0].strip() == "SUBJECT"
        )
    except (StopIteration, ValueError) as exc:
        raise MemoParseError("Legacy AMD input must define SUBJECT before the body") from exc

    raw_fields: dict[str, object] = {}
    for line in file_lines[: subject_index + 1]:
        if "=" not in line:
            continue
        key, value = [chunk.strip() for chunk in line.split("=", 1)]
        mapped = KEY_MAP.get(key)
        if mapped is None:
            raise MemoParseError(f"Unknown legacy AMD key: {key}")
        if mapped in LIST_KEYS:
            raw_fields.setdefault(mapped, [])
            assert isinstance(raw_fields[mapped], list)
            raw_fields[mapped].append(value)
        else:
            raw_fields[mapped] = value

    body = parse_body_lines(file_lines[subject_index + 1 :])
    return _LegacyMemoFields(raw_fields).build_document(body)


def parse_body_lines(lines: list[str]) -> list[BodyItem | TableBlock]:
    root: list[BodyItem | TableBlock] = []
    stack: list[tuple[int, list[BodyItem | TableBlock]]] = [(-1, root)]
    table_lines: list[str] = []
    last_item: BodyItem | None = None
    last_container = root

    def flush_table() -> None:
        nonlocal table_lines
        if not table_lines:
            return
        target = last_container if last_item is not None else root
        target.append(_parse_table_block(table_lines))
        table_lines = []

    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped == "---":
            flush_table()
            continue

        is_table = stripped.count("|") > 1 and BULLET_RE.match(line) is None
        if is_table:
            table_lines.append(stripped)
            continue

        flush_table()
        bullet_match = BULLET_RE.match(line)
        if bullet_match is not None:
            indent = len(bullet_match.group("indent").replace("\t", "    "))
            while len(stack) > 1 and indent <= stack[-1][0]:
                stack.pop()
            parent = stack[-1][1]
            item = BodyItem(paragraphs=[bullet_match.group("text").strip()])
            parent.append(item)
            stack.append((indent, item.children))
            last_item = item
            last_container = parent
            continue

        if last_item is not None:
            last_item.paragraphs.append(stripped)

    flush_table()
    return root


def _parse_table_block(lines: list[str]) -> TableBlock:
    rows = [_split_pipe_row(line) for line in lines if line.strip()]
    if not rows:
        return TableBlock(headers=[], rows=[])
    headers = rows[0]
    data_rows = rows[1:]
    if data_rows and all(_is_separator_cell(cell) for cell in data_rows[0]):
        data_rows = data_rows[1:]
    width_candidates = [len(headers), *(len(row) for row in data_rows)]
    width = max(width_candidates) if width_candidates else len(headers)
    headers = headers + [""] * max(0, width - len(headers))
    data_rows = [row + [""] * max(0, width - len(row)) for row in data_rows]
    return TableBlock(headers=headers, rows=data_rows)


def _split_pipe_row(line: str) -> list[str]:
    stripped = line.strip().strip("|")
    return [cell.strip() for cell in stripped.split("|")]


def _is_separator_cell(cell: str) -> bool:
    compact = cell.replace(" ", "")
    return bool(compact) and all(character in "-:" for character in compact)


def _zip_recipients(
    names: object,
    streets: object,
    cities: object,
) -> list[Recipient]:
    if not names:
        return []
    name_list = list(names)
    street_list = list(streets or [])
    city_list = list(cities or [])
    recipients: list[Recipient] = []
    for index, name in enumerate(name_list):
        recipients.append(
            Recipient(
                name=str(name),
                street_address=str(street_list[index]) if index < len(street_list) else "",
                city_state_zip=str(city_list[index]) if index < len(city_list) else "",
            )
        )
    return recipients


def _parse_recipients(raw_value: object) -> list[Recipient]:
    if raw_value is None:
        return []
    if not isinstance(raw_value, list):
        raise MemoParseError("Recipient lists must be YAML sequences")
    recipients: list[Recipient] = []
    for item in raw_value:
        if not isinstance(item, dict):
            raise MemoParseError("Each recipient must be a mapping")
        recipients.append(
            Recipient(
                name=str(item.get("name", "")),
                street_address=str(item.get("street_address", "")),
                city_state_zip=str(item.get("city_state_zip", "")),
            )
        )
    return recipients


def _normalize_memo_type(value: str | None) -> str:
    if not value:
        return ""
    normalized = value.replace("_", " ").strip().upper()
    aliases = {
        "MFR": "MEMORANDUM FOR RECORD",
        "MEMORANDUM FOR RECORD": "MEMORANDUM FOR RECORD",
        "MEMORANDUM FOR": "MEMORANDUM FOR",
        "MEMORANDUM THRU": "MEMORANDUM THRU",
    }
    return aliases.get(normalized, normalized)


def _string_list(value: object) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise MemoParseError("Expected a sequence of strings")
    return [str(item) for item in value]


def _optional_str(value: object) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


def _required(values: dict[str, object], key: str) -> str:
    value = values.get(key)
    if value in (None, ""):
        raise MemoParseError(f"Missing required memo field: {key}")
    return str(value)
