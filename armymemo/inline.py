from __future__ import annotations

import re

TRIPLE_STAR_RE = re.compile(r"\*\*\*(.+?)\*\*\*")
DOUBLE_STAR_RE = re.compile(r"\*\*(.+?)\*\*")
SINGLE_STAR_RE = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)")
BACKTICK_RE = re.compile(r"`(.+?)`")


def escape_typst_text(text: str) -> str:
    escaped = text.replace("\\", "\\\\")
    for character in ["#", "[", "]", "{", "}", "$", "<", ">", "@"]:
        escaped = escaped.replace(character, f"\\{character}")
    return escaped


def render_typst_inline(text: str) -> str:
    def _wrap(pattern: re.Pattern[str], replacement: str, value: str) -> str:
        return pattern.sub(
            lambda match: replacement.format(text=escape_typst_text(match.group(1))),
            value,
        )

    rendered = escape_typst_text(text)
    rendered = _wrap(TRIPLE_STAR_RE, "#underline[{text}]", rendered)
    rendered = _wrap(DOUBLE_STAR_RE, "*{text}*", rendered)
    rendered = _wrap(SINGLE_STAR_RE, "_{text}_", rendered)
    rendered = _wrap(BACKTICK_RE, "#highlight[{text}]", rendered)
    return rendered
