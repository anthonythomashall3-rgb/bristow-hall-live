import json
from pathlib import Path

import pytest

from rmv2_extension.public_generation import build_generation, verify_generation


def entry(source, public_path, **overrides):
    row = {
        "source": source,
        "public_path": public_path,
        "public_eligible": True,
        "rights_status": "public_domain_with_attribution",
        "source_name": source,
        "attribution": "Test source",
    }
    row.update(overrides)
    return row


def test_build_generation_is_deterministic_and_pointer_is_created(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "a.json").write_text('{"a":1}\n', encoding="utf-8")
    out = tmp_path / "out"
    first = build_generation(source, out, [entry("a.json", "data/a.json")], generated_at="2026-07-31T00:00:00Z")
    second = build_generation(source, out, [entry("a.json", "data/a.json")], generated_at="2026-07-31T00:00:00Z")
    assert first == second
    assert json.loads((out / "current.json").read_text(encoding="utf-8"))["generation_sha256"] == first["generation_sha256"]
    assert verify_generation(out, first["generation_sha256"])["ok"]


def test_non_public_entry_is_refused(tmp_path):
    source = tmp_path / "source"; source.mkdir()
    (source / "a.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="not public-eligible"):
        build_generation(source, tmp_path / "out", [entry("a.json", "a.json", public_eligible=False)])


def test_pending_or_restricted_rights_are_refused(tmp_path):
    source = tmp_path / "source"; source.mkdir()
    (source / "a.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="rights status"):
        build_generation(source, tmp_path / "out", [entry("a.json", "a.json", rights_status="rights_pending")])


def test_tamper_is_detected(tmp_path):
    source = tmp_path / "source"; source.mkdir()
    (source / "a.json").write_text("{}", encoding="utf-8")
    out = tmp_path / "out"
    pointer = build_generation(source, out, [entry("a.json", "a.json")])
    member = out / "generations" / pointer["generation_sha256"] / "a.json"
    member.write_text('{"changed":true}', encoding="utf-8")
    check = verify_generation(out, pointer["generation_sha256"])
    assert check["ok"] is False
    assert any("hash mismatch" in error for error in check["errors"])


def test_path_traversal_is_refused(tmp_path):
    source = tmp_path / "source"; source.mkdir()
    (source / "a.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="unsafe"):
        build_generation(source, tmp_path / "out", [entry("a.json", "../a.json")])
