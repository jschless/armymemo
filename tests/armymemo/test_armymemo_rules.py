from armymemo import load_rule_inventory, load_rulebook, load_typst_layout_rules, parse_file
from armymemo.renderers.typst import render_typst_source


def test_rulebook_exposes_layout_and_inventory():
    rulebook = load_rulebook()
    layout = load_typst_layout_rules()
    rules = load_rule_inventory()

    assert rulebook["meta"]["title"] == "Army Memorandum Rulebook"
    assert layout["page_margin"]["left"] == 72
    assert any(rule["id"] == "memo.continuation.page_number" for rule in rules)


def test_typst_source_includes_injected_rulebook():
    source = render_typst_source(parse_file("resources/examples/basic_mfr.Amd"))

    assert "#let rulebook =" in source
    assert "memo.page.margins" in source
