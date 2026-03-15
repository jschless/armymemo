from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

RESOURCE_DIR = Path(__file__).resolve().parent / "resources" / "rules"
RULEBOOK_PATH = RESOURCE_DIR / "memo_rulebook.yaml"


@lru_cache(maxsize=1)
def load_rulebook() -> dict[str, object]:
    return yaml.safe_load(RULEBOOK_PATH.read_text(encoding="utf-8"))


def load_typst_layout_rules() -> dict[str, object]:
    rulebook = load_rulebook()
    layout = rulebook.get("layout_typst", {})
    if not isinstance(layout, dict):
        raise TypeError("Rulebook layout_typst must be a mapping")
    return layout


def load_rule_inventory() -> list[dict[str, object]]:
    rulebook = load_rulebook()
    rules = rulebook.get("rules", [])
    if not isinstance(rules, list):
        raise TypeError("Rulebook rules must be a sequence")
    return rules
