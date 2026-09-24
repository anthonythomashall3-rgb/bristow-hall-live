from pathlib import Path

from rmv2_extension.public_generation import build_generation
from rmv2_extension.upload_plan import build_upload_plan


def make_bundle(tmp_path):
    source = tmp_path / "source"; source.mkdir()
    (source / "a file.json").write_text("{}", encoding="utf-8")
    out = tmp_path / "bundle"
    build_generation(source, out, [{
        "source": "a file.json",
        "public_path": "data/a file.json",
        "public_eligible": True,
        "rights_status": "public_domain_with_attribution",
    }], generated_at="2026-07-31T00:00:00Z")
    return out


def test_plan_uploads_generation_first_and_pointer_last(tmp_path):
    plan = build_upload_plan(make_bundle(tmp_path), "bucket")
    assert plan["pointer_last"] is True
    assert plan["steps"][-1]["key"] == "current.json"
    assert all(step["immutable"] for step in plan["steps"][:-1])
    assert plan["steps"][-1]["immutable"] is False


def test_rclone_commands_are_shell_quoted(tmp_path):
    plan = build_upload_plan(make_bundle(tmp_path), "my bucket", tool="rclone")
    command = plan["steps"][0]["command"]
    assert "'r2:my bucket/" in command
    assert "--immutable" in command


def test_wrangler_plan_uses_remote_object_put(tmp_path):
    plan = build_upload_plan(make_bundle(tmp_path), "bucket", tool="wrangler")
    assert "wrangler" in plan["steps"][0]["command"]
    assert "--remote" in plan["steps"][0]["command"]
