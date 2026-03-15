from armymemo.review_pack import generate_review_pack, list_review_packs


def test_list_review_packs_exposes_representative_pack():
    assert "representative_5" in list_review_packs()


def test_generate_review_pack_writes_manifest_and_five_pdfs(tmp_path):
    generated = generate_review_pack(tmp_path)

    assert len(generated) == 5
    assert all(path.exists() for path in generated)
    assert (tmp_path / "README.md").exists()
    manifest = (tmp_path / "README.md").read_text(encoding="utf-8")
    assert "01-basic_mfr.pdf" in manifest
    assert "05-long_memo.pdf" in manifest
