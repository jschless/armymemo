from armymemo import parse_file
from armymemo.renderers.typst import render_typst_source
from armymemo.rules import load_rule_inventory, load_rulebook, load_typst_layout_rules


def test_rulebook_exposes_layout_and_inventory():
    rulebook = load_rulebook()
    layout = load_typst_layout_rules()
    rules = load_rule_inventory()

    assert rulebook["meta"]["title"] == "Army Memorandum Rulebook"
    assert layout["page_margin"]["left"] == 72
    assert layout["letterhead"]["department_font_size_pt"] == 10
    assert layout["letterhead"]["detail_font_size_pt"] == 8
    assert layout["letterhead"]["header_line_gap_pt"] == 2
    assert layout["body"]["level_1_first_line_indent_pt"] == 16
    assert layout["body"]["level_2_first_line_indent_pt"] == 36
    assert layout["body"]["level_3_first_line_indent_pt"] == 54
    assert layout["route"]["single_for_wrap_width_chars"] == 74
    assert any(rule["id"] == "memo.continuation.page_number" for rule in rules)


def test_typst_source_includes_injected_rulebook():
    source = render_typst_source(parse_file("resources/examples/basic_mfr.Amd"))

    assert "#let rulebook =" in source
    assert "memo.page.margins" in source
