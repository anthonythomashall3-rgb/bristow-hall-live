"""bh gitstate — authority-tree cleanliness (B-HOUSE-3 Defect 3)."""

from __future__ import annotations

import subprocess

import pytest

from bh import gitstate


def test_is_authority_dir_boundary():
    assert gitstate._is_authority("live_data/config/x.json")
    assert gitstate._is_authority("model_authority/params.json")
    assert gitstate._is_authority("contrib/free_official_sources_v1/a.py")
    assert gitstate._is_authority("data_vault/manifests/live_manifest.json")
    # boundary: a sibling that merely shares a prefix is NOT authority
    assert not gitstate._is_authority("live_data/config_backup/x")
    assert not gitstate._is_authority("live_data/store/blob")
    # research scratch is never authority — the whole point of Defect 3's carve-out
    assert not gitstate._is_authority("research/CH_probe.txt")


def test_parse_porcelain_selects_only_authority():
    text = (
        " M live_data/catalog/metric_catalog.csv\n"
        "?? research/scratch/foo.txt\n"
        "?? live_data/store/blob\n"
        "A  model_authority/projections/new.json\n"
        "R  method_source/old.py -> method_source/new.py\n"
    )
    dirty = gitstate.parse_porcelain(text)
    assert dirty == [
        "live_data/catalog/metric_catalog.csv",
        "method_source/new.py",   # rename keys on the destination path
        "model_authority/projections/new.json",
    ]


def test_parse_porcelain_clean_is_empty():
    assert gitstate.parse_porcelain("?? research/a.txt\n?? live_data/runtime/log\n") == []


def _git(repo, *args):
    subprocess.run(["git", *args], cwd=str(repo), check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


@pytest.fixture
def gitrepo(tmp_path):
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "t@t")
    _git(tmp_path, "config", "user.name", "t")
    (tmp_path / "model_authority").mkdir()
    (tmp_path / "model_authority" / "p.json").write_text("{}")
    (tmp_path / "research").mkdir()
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-m", "init")
    return tmp_path


def test_authority_dirty_clean_repo(gitrepo):
    # untracked research scratch must NOT trip the check
    (gitrepo / "research" / "scratch.txt").write_text("x")
    assert gitstate.authority_dirty(gitrepo) == []


def test_authority_dirty_flags_modified_authority(gitrepo):
    (gitrepo / "model_authority" / "p.json").write_text('{"a":1}')
    assert gitstate.authority_dirty(gitrepo) == ["model_authority/p.json"]


def test_authority_dirty_flags_untracked_authority(gitrepo):
    (gitrepo / "live_data" / "catalog").mkdir(parents=True)
    (gitrepo / "live_data" / "catalog" / "new.csv").write_text("a,b\n")
    assert gitstate.authority_dirty(gitrepo) == ["live_data/catalog/new.csv"]


def test_authority_dirty_unknown_is_not_clean(tmp_path):
    # REGRESSION (2026-08-07): this used to assert [] — i.e. CLEAN — whenever git
    # failed, which made the nightly's only publish gate FAIL OPEN. A broken git
    # (`xcrun: error: invalid active developer path` after a macOS update, git
    # removed, or simply not a repo) let `bh nightly` step 0 log
    # "authority_tree: CLEAN" and publish an uncommitted authority tree.
    # UNKNOWN must be distinguishable from CLEAN, and must refuse.
    with pytest.raises(gitstate.GitStateUnknown):
        gitstate.authority_dirty(tmp_path)


def test_broken_git_binary_is_unknown_not_clean(tmp_path, monkeypatch):
    def _boom(*a, **k):
        raise OSError("git: command not found")

    monkeypatch.setattr(gitstate.subprocess, "run", _boom)
    with pytest.raises(gitstate.GitStateUnknown):
        gitstate.authority_dirty(tmp_path)
