from pathlib import Path

import pytest

from rmv2_extension.installer import install_overlay


def make_package(tmp_path):
    package = tmp_path / "package"
    (package / "scripts").mkdir(parents=True)
    (package / "scripts" / "tool.py").write_text("print('ok')\n", encoding="utf-8")
    (package / "cloudflare").mkdir()
    (package / "cloudflare" / "worker.js").write_text("export default {};\n", encoding="utf-8")
    return package


def test_dry_run_does_not_copy(tmp_path):
    package = make_package(tmp_path)
    project = tmp_path / "project"; project.mkdir()
    receipt = install_overlay(package, project, apply=False)
    assert receipt["planned"]
    assert receipt["copied"] == []
    assert not (project / "tools/rmv2_data_cloudflare/scripts/tool.py").exists()


def test_apply_copies_only_overlay_paths(tmp_path):
    package = make_package(tmp_path)
    project = tmp_path / "project"; project.mkdir()
    receipt = install_overlay(package, project, apply=True)
    assert receipt["copied"]
    assert (project / "tools/rmv2_data_cloudflare/scripts/tool.py").is_file()
    assert (project / "cloudflare/recession-monitor-v2-data/worker.js").is_file()


def test_conflicting_existing_file_is_refused(tmp_path):
    package = make_package(tmp_path)
    project = tmp_path / "project"; project.mkdir()
    target = project / "tools/rmv2_data_cloudflare/scripts/tool.py"
    target.parent.mkdir(parents=True)
    target.write_text("different", encoding="utf-8")
    with pytest.raises(FileExistsError, match="conflicting"):
        install_overlay(package, project, apply=True)


def test_identical_existing_file_is_skipped(tmp_path):
    package = make_package(tmp_path)
    project = tmp_path / "project"; project.mkdir()
    target = project / "tools/rmv2_data_cloudflare/scripts/tool.py"
    target.parent.mkdir(parents=True)
    target.write_text("print('ok')\n", encoding="utf-8")
    receipt = install_overlay(package, project, apply=True)
    assert "tools/rmv2_data_cloudflare/scripts/tool.py" in receipt["skipped_identical"]
