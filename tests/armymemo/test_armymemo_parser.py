from armymemo import parse_file, parse_text
from armymemo.document import MemoDocument, TableBlock


def test_parse_legacy_amd_basic_example():
    document = parse_file("resources/examples/basic_mfr.Amd")

    assert isinstance(document, MemoDocument)
    assert document.memo_type == "MEMORANDUM FOR RECORD"
    assert document.subject == "Army markdown"
    assert len(document.body) == 3


def test_parse_memodoc_roundtrip_from_legacy_table_example():
    original = parse_file("resources/examples/basic_mfr_w_table.Amd")
    memodoc = original.to_memodoc()
    reparsed = parse_text(memodoc)

    assert reparsed.subject == original.subject
    assert len(reparsed.body) == len(original.body)
    assert any(isinstance(node, TableBlock) for node in reparsed.body)


def test_memodoc_supports_structured_recipients():
    source = """---
unit:
  name: 4th Engineer Battalion
  street_address: 588 Wetzel Road
  city_state_zip: Colorado Springs, CO 80904
office_symbol: ABC-DEF-GH
date: 14 March 2026
subject: Test Subject
author:
  name: Jordan A. Carter
  rank: CPT
  branch: EN
  title: Company Commander
thru:
  - name: First Routing Activity
    street_address: 123 Main Street
    city_state_zip: Fort Example, NC 28310
for:
  - name: Final Action Office
    street_address: 456 Center Road
    city_state_zip: Fort Example, NC 28310
---
- This is a test memo.
"""

    document = parse_text(source)

    assert document.memo_type == "MEMORANDUM THRU"
    assert len(document.thru_recipients) == 1
    assert len(document.for_recipients) == 1
    assert document.author_title == "Company Commander"
