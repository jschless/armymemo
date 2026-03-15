from __future__ import annotations

import armymemo
from armymemo.cli import main
from armymemo.examples import list_packaged_examples, read_packaged_example


def test_packaged_examples_include_basic_fixture():
    assert "basic_mfr.Amd" in list_packaged_examples()
    assert "SUBJECT = Army markdown" in read_packaged_example("basic_mfr.Amd")


def test_cli_render_accepts_packaged_example_name(tmp_path):
    output_path = tmp_path / "basic_mfr.typ"

    exit_code = main(["render", "basic_mfr.Amd", "--source-only", "--output", str(output_path)])

    assert exit_code == 0
    assert output_path.exists()
    assert "SUBJECT:" in output_path.read_text(encoding="utf-8")


def test_cli_benchmark_accepts_packaged_example_name():
    exit_code = main(["benchmark", "basic_mfr.Amd", "--iterations", "1", "--json"])

    assert exit_code == 0


def test_public_api_excludes_internal_geometry_and_rule_helpers():
    assert not hasattr(armymemo, "ExtractedLayout")
    assert not hasattr(armymemo, "ExtractedLine")
    assert not hasattr(armymemo, "default_review_rules")
    assert not hasattr(armymemo, "extract_review_features")
    assert not hasattr(armymemo, "load_rulebook")
    assert hasattr(armymemo, "review_document")
    assert hasattr(armymemo, "render_typst_pdf")
