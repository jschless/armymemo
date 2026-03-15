from __future__ import annotations

import re

TRIPLE_STAR_RE = re.compile(r"\*\*\*(.+?)\*\*\*")
DOUBLE_STAR_RE = re.compile(r"\*\*(.+?)\*\*")
SINGLE_STAR_RE = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)")
BACKTICK_RE = re.compile(r"`(.+?)`")

STRONG_SENTINEL_OPEN = "\u0001STRONG_OPEN\u0001"
STRONG_SENTINEL_CLOSE = "\u0001STRONG_CLOSE\u0001"
UNDERLINE_SENTINEL_OPEN = "\u0001UNDERLINE_OPEN\u0001"
UNDERLINE_SENTINEL_CLOSE = "\u0001UNDERLINE_CLOSE\u0001"


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
    rendered = _wrap(
        TRIPLE_STAR_RE,
        f"{UNDERLINE_SENTINEL_OPEN}{{text}}{UNDERLINE_SENTINEL_CLOSE}",
        rendered,
    )
    rendered = _wrap(
        DOUBLE_STAR_RE,
        f"{STRONG_SENTINEL_OPEN}{{text}}{STRONG_SENTINEL_CLOSE}",
        rendered,
    )
    rendered = _wrap(SINGLE_STAR_RE, "_{text}_", rendered)
    rendered = _wrap(BACKTICK_RE, "#highlight[{text}]", rendered)
    rendered = rendered.replace(
        STRONG_SENTINEL_OPEN, "*"
    ).replace(STRONG_SENTINEL_CLOSE, "*")
    rendered = rendered.replace(
        UNDERLINE_SENTINEL_OPEN, "#underline["
    ).replace(UNDERLINE_SENTINEL_CLOSE, "]")
    return rendered
