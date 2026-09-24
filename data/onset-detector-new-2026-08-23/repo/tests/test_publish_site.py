from __future__ import absolute_import

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from live_data.publish_site import PublishError, publish


FILES = (
    "coverage.json",
    "manifest.json",
    "pointer.json",
    "series_latest.json",
    "status.json",
    "summary.json",
)
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _bundle(root):
    out = Path(root) / "bundle"
    source = out / "data" / "live"
    source.mkdir(parents=True)
    files = {}
    for name in FILES:
        data = json.dumps({"file": name}, sort_keys=True).encode("utf-8") + b"\n"
        (source / name).write_bytes(data)
        files[name] = {
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }
    (out / "publish_receipt.json").write_text(
        json.dumps({
            "files": files,
            "generation_sha256": "a" * 64,
            "schema_version": "recession-monitor-v2.public-web-bundle.v1",
            "scientific_effect": "none",
        }),
        encoding="utf-8",
    )
    return source


def _site(root):
    site = Path(root) / "site"
    target = site / "data" / "live"
    target.mkdir(parents=True)
    (site / "index.html").write_text("site", encoding="utf-8")
    return site, target


def test_publish_copies_verified_bundle_and_preserves_unrelated_site_files(tmp_path):
    source = _bundle(tmp_path)
    _site_root, target = _site(tmp_path)
    (target / "keep.txt").write_text("unrelated", encoding="utf-8")

    result = publish(tmp_path, target=target, source=source, rebuild=False)

    assert result["published"] is True
    assert result["generation_sha256"] == "a" * 64
    assert (target / "keep.txt").read_text(encoding="utf-8") == "unrelated"
    for name in FILES:
        assert (target / name).read_bytes() == (source / name).read_bytes()


def test_publish_refuses_target_that_is_not_an_existing_site(tmp_path):
    source = _bundle(tmp_path)
    target = tmp_path / "not-a-site" / "data" / "live"
    target.mkdir(parents=True)

    with pytest.raises(PublishError, match="index.html"):
        publish(tmp_path, target=target, source=source, rebuild=False)


def test_publish_refuses_bundle_whose_receipt_does_not_match(tmp_path):
    source = _bundle(tmp_path)
    _site_root, target = _site(tmp_path)
    (source / "summary.json").write_text("tampered", encoding="utf-8")

    with pytest.raises(PublishError, match="receipt"):
        publish(tmp_path, target=target, source=source, rebuild=False)


def test_publish_resolves_the_explicit_repo_target_file(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    source = _bundle(project)
    _site_root, target = _site(tmp_path)
    config = project / "live_data" / "public_deploy" / "site_target.path"
    config.parent.mkdir(parents=True)
    config.write_text("../site/data/live\n", encoding="utf-8")

    result = publish(project, source=source, rebuild=False)

    assert Path(result["target"]) == target.resolve()


def test_shell_wrapper_reads_recorded_interpreter_from_application_support(tmp_path):
    capture = tmp_path / "args.txt"
    interpreter = tmp_path / "fake-python"
    interpreter.write_text(
        "#!/bin/sh\nprintf '%s\\n' \"$@\" > \"$WRAPPER_CAPTURE\"\n",
        encoding="utf-8",
    )
    interpreter.chmod(0o755)
    support = tmp_path / "Library" / "Application Support" / "bristow-hall"
    support.mkdir(parents=True)
    (support / "interpreter.path").write_text(
        str(interpreter) + "\n", encoding="utf-8"
    )
    env = dict(os.environ)
    env.pop("BH_PROJECT_INTERPRETER", None)
    env.update({"HOME": str(tmp_path), "WRAPPER_CAPTURE": str(capture)})

    result = subprocess.run(
        ["/bin/sh", str(PROJECT_ROOT / "live_data/public_deploy/publish.sh")],
        cwd=str(PROJECT_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    args = capture.read_text(encoding="utf-8").splitlines()
    assert args[0] == "-B"
    assert args[1] == str(PROJECT_ROOT / "live_data/publish_site.py")
    assert args[2] == str(PROJECT_ROOT)


def test_direct_script_execution_resolves_the_repo_package(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            str(PROJECT_ROOT / "live_data/publish_site.py"),
            str(tmp_path),
        ],
        cwd=str(tmp_path),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    assert result.returncode == 1
    assert "SITE PUBLISH FAILED:" in result.stderr
    assert "Traceback" not in result.stderr
