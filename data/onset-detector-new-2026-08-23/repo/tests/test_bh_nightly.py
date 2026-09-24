"""bh nightly — step sequencing + fail-fast (B-AUTO-1 §2), injected ops."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from bh import nightly


class FakeNightlyOps:
    def __init__(self, *, verify_ok=True, backup=None, publish=None, backup_raises=None):
        self.verify_ok = verify_ok
        self._backup = backup if backup is not None else {"ok": True, "manifest_verified": True,
                                                          "sampled_restore_ok": True}
        self._backup_raises = backup_raises  # exception instance to raise from backup()
        self._publish = publish if publish is not None else {
            "published": False, "publisher_found": False, "gap_filed": True}
        self.calls = []

    def verify_full(self):
        self.calls.append("verify_full")
        return self.verify_ok

    def backup(self):
        self.calls.append("backup")
        if self._backup_raises is not None:
            raise self._backup_raises
        return self._backup

    def site_publish(self):
        self.calls.append("site_publish")
        return self._publish

    def report_append(self):
        self.calls.append("report_append")


@pytest.fixture
def repo(tmp_path):
    (tmp_path / "live_data" / "runtime" / "logs").mkdir(parents=True)
    # A real git repo, not a bare temp dir: step 0 now treats "git could not
    # answer" as UNKNOWN and refuses to publish (it used to read as CLEAN, which
    # let the nightly publish an uncommitted authority tree). The fixture must
    # model the production precondition rather than lean on the fail-open path.
    subprocess.run(["git", "init", "-q"], cwd=str(tmp_path), check=True)
    return tmp_path


def test_all_steps_in_order_on_clean_run(repo):
    ops = FakeNightlyOps()
    result = nightly.run_nightly(ops, repo)
    assert result["failed"] is None
    assert ops.calls == ["verify_full", "backup", "site_publish", "report_append"]
    assert (repo / nightly.NIGHTLY_LOG_REL).exists()


def test_verify_fail_stops_before_backup(repo):
    ops = FakeNightlyOps(verify_ok=False)
    result = nightly.run_nightly(ops, repo)
    assert result["failed"] == "verify_full"
    assert "backup" not in ops.calls  # fail-fast, no retry


def test_backup_fail_does_not_suppress_publish_and_report(repo):
    # B-AUTO-2: the observed defect was a backup failure/timeout killing every
    # downstream step. A backup failure must be RECORDED but must NOT suppress
    # publish + report; the run is still marked FAILED overall.
    ops = FakeNightlyOps(backup={"ok": False, "reason": "backup exit 1"})
    result = nightly.run_nightly(ops, repo)
    assert result["failed"] == "backup"
    assert result["failed_steps"] == ["backup"]
    assert ops.calls == ["verify_full", "backup", "site_publish", "report_append"]


def test_backup_timeout_is_caught_and_downstream_still_runs(repo):
    # The exact production failure: subprocess.TimeoutExpired escaping the backup
    # step. It must be caught, recorded as a backup failure, and publish + report
    # must still run — proving one failing step does not suppress the others.
    import subprocess

    exc = subprocess.TimeoutExpired(cmd="vault_backup.py backup", timeout=nightly.BACKUP_TIMEOUT_S)
    ops = FakeNightlyOps(backup_raises=exc)
    result = nightly.run_nightly(ops, repo)
    assert result["failed"] == "backup"
    assert ops.calls == ["verify_full", "backup", "site_publish", "report_append"]
    assert result["backup_proof"]["ok"] is False


def test_backup_with_sampled_proof_downgrades_timeout(repo, monkeypatch):
    # backup_with_sampled_proof must convert TimeoutExpired into ok=False, never raise.
    import subprocess

    def _boom(*a, **k):
        raise subprocess.TimeoutExpired(cmd="backup", timeout=nightly.BACKUP_TIMEOUT_S)

    monkeypatch.setattr(nightly.subprocess, "run", _boom)
    (repo / "live_data" / "ops" / "backup").mkdir(parents=True)
    (repo / "live_data" / "ops" / "backup" / "vault_backup.py").write_text("# stub")
    proof = nightly.backup_with_sampled_proof(repo)
    assert proof["ok"] is False
    assert proof["completed"] is False
    assert "timed out" in proof["reason"]


def test_no_publisher_is_not_a_failure(repo):
    ops = FakeNightlyOps(publish={"published": False, "publisher_found": False, "gap_filed": True})
    result = nightly.run_nightly(ops, repo)
    assert result["failed"] is None
    assert result["publish"]["gap_filed"] is True
    assert ops.calls[-1] == "report_append"  # ran to the end


def test_find_publisher_returns_none_when_absent(repo):
    assert nightly._find_publisher(repo) is None  # never invents a target


def test_dirty_authority_tree_refuses_before_any_step(repo, monkeypatch):
    # B-HOUSE-3 Defect 3: nightly must refuse to publish over a dirty authority tree.
    monkeypatch.setattr(nightly.gitstate, "authority_dirty",
                        lambda r: ["live_data/catalog/metric_catalog.csv"])
    ops = FakeNightlyOps()
    result = nightly.run_nightly(ops, repo)
    assert result["failed"] == "authority_tree"
    assert result["dirty_authority"] == ["live_data/catalog/metric_catalog.csv"]
    assert ops.calls == []  # refused before verify/backup/publish even started


def test_clean_authority_tree_runs_all_steps(repo, monkeypatch):
    monkeypatch.setattr(nightly.gitstate, "authority_dirty", lambda r: [])
    ops = FakeNightlyOps()
    result = nightly.run_nightly(ops, repo)
    assert result["failed"] is None
    assert result["steps"][0] == {"step": "authority_tree", "ok": True}
    assert ops.calls == ["verify_full", "backup", "site_publish", "report_append"]


# --- B-AUTO-2: status file for `bh doctor` -----------------------------------

def test_clean_run_writes_ok_status(repo):
    result = nightly.run_nightly(FakeNightlyOps(), repo)
    status = nightly.read_status(repo)
    assert status is not None
    assert status["ok"] is True
    assert status["failed"] is None
    assert status["last_success_at"] == status["run_at"]
    assert result["status"] == status


def test_failed_run_writes_failed_status_and_preserves_last_success(repo):
    # first a clean run establishes a last_success_at
    nightly.run_nightly(FakeNightlyOps(), repo)
    good = nightly.read_status(repo)["last_success_at"]
    assert good is not None
    # then a failing backup run: status is not-ok, but last_success_at is preserved
    nightly.run_nightly(FakeNightlyOps(backup={"ok": False, "reason": "x"}), repo)
    status = nightly.read_status(repo)
    assert status["ok"] is False
    assert status["failed"] == "backup"
    assert status["last_success_at"] == good  # a failure must not erase the memory


def test_read_status_none_when_never_run(repo):
    assert nightly.read_status(repo) is None


def test_backup_timeout_constant_is_measured_multiple():
    # provenance guard: the timeout must stay the documented measured multiple,
    # not silently drift back to a magic number.
    assert nightly.BACKUP_TIMEOUT_S >= nightly.BACKUP_TIMING_MEASURED_S * nightly.BACKUP_TIMEOUT_MULTIPLE
    assert nightly.BACKUP_TIMEOUT_S > 600  # strictly above the value that was killing the nightly


# --- B-AUTO-2 FOLLOW-UP (2026-08-07): the three live nightly defects ----------
# Evidence for all three is one production run recorded in
# live_data/runtime/logs/nightly.log at 2026-08-07T11:17:07Z-11:36:32Z.


def test_sampled_restore_names_the_missing_tool_instead_of_a_bare_rc(tmp_path):
    """DEFECT: the sampled restore shelled out with NO env, so under launchd
    (bare PATH, no Homebrew) `zstd` was not found, every nightly reported
    sampled_restore_ok=False, and the only restore evidence the vault has was
    silently lost. It must resolve tools against the SAME env the backup engine
    gets and name what is missing."""
    manifest = tmp_path / "live_manifest.json"
    manifest.write_text(
        '{"files": [{"path": "a.txt", "size": 3, "sha256": "' + "0" * 64 + '"}]}',
        encoding="utf-8",
    )
    archive = tmp_path / "irreplaceable.tar.zst"
    archive.write_bytes(b"not-a-real-archive")

    out = nightly._sampled_restore_ok(archive, manifest, env={"PATH": "/nonexistent"})
    assert out["ok"] is False
    assert "zstd" in out["reason"]
    assert "/nonexistent" in out["reason"]
    # and it must never silently fall back to the ambient PATH
    assert "not found" in out["reason"]


def test_backup_proof_always_carries_a_reason_when_it_fails(tmp_path, monkeypatch):
    """DEFECT: the completed-but-unproven path returned no "reason", so the
    nightly log printed the useless `step2 backup FAILED (None)`."""
    repo = tmp_path / "repo"
    (repo / "live_data" / "ops" / "backup").mkdir(parents=True)
    dest = (repo / nightly.DEST_ROOT_REL).resolve()
    (dest / "receipts").mkdir(parents=True)
    (dest / "snapshots" / "S").mkdir(parents=True)
    (dest / "receipts" / "receipt_1.json").write_text(
        '{"archive": "%s", "archive_integrity": "PASS",'
        ' "member_count_matches_manifest": true}' % (dest / "snapshots" / "S" / "a.tar.zst"),
        encoding="utf-8",
    )

    class _Proc:
        returncode = 0
        stderr = ""

    monkeypatch.setattr(nightly.subprocess, "run", lambda *a, **k: _Proc())
    monkeypatch.setattr(
        nightly, "_sampled_restore_ok",
        lambda *a, **k: {"ok": False, "reason": "zstd not found on PATH='/usr/bin:/bin'"},
    )
    proof = nightly.backup_with_sampled_proof(repo, env={"PATH": "/usr/bin:/bin"})
    assert proof["ok"] is False
    assert proof.get("reason"), "a failed backup proof must say why"
    assert "zstd not found" in proof["reason"]


def test_publish_timeout_keeps_publisher_found_true(tmp_path, monkeypatch):
    """DEFECT: a publish timeout was reported as publisher_found=False, which is
    the documented `gap 10 / no publisher exists` signal and is explicitly NOT a
    failure. A publisher that WAS executed and timed out must not forge it."""
    repo = tmp_path / "repo"
    publisher = repo / "live_data" / "public_deploy" / "publish.sh"
    publisher.parent.mkdir(parents=True)
    publisher.write_text("#!/bin/sh\nsleep 600\n", encoding="utf-8")

    class _Hanging:
        pid = 424242
        returncode = None

        def communicate(self, timeout=None):
            raise nightly.subprocess.TimeoutExpired(cmd="publish.sh", timeout=timeout)

    monkeypatch.setattr(nightly.subprocess, "Popen", lambda *a, **k: _Hanging())
    monkeypatch.setattr(nightly, "_kill_process_group", lambda proc: None)

    out = nightly.detect_and_publish(repo)
    assert out["publisher_found"] is True
    assert out["published"] is False
    assert out["timed_out"] is True
    assert "timed out" in out["reason"]


def test_found_publisher_that_did_not_publish_is_a_failed_step(repo):
    """DEFECT: step 3 was recorded ok=True unconditionally, so a found publisher
    that timed out or exited non-zero was swallowed as a success."""
    ops = FakeNightlyOps(publish={"published": False, "publisher_found": True,
                                  "timed_out": True, "reason": "publisher timed out"})
    result = nightly.run_nightly(ops, repo)
    assert result["failed"] == "site_publish"
    assert "site_publish" in result["failed_steps"]
    assert ops.calls == ["verify_full", "backup", "site_publish", "report_append"]
    assert nightly.read_status(repo)["ok"] is False


def test_absent_publisher_is_still_not_a_failure(repo):
    """Guard the other side: gap 10 (no publisher in the repo) stays a clean run."""
    ops = FakeNightlyOps(publish={"published": False, "publisher_found": False,
                                  "gap_filed": True})
    result = nightly.run_nightly(ops, repo)
    assert result["failed"] is None
    assert nightly.read_status(repo)["ok"] is True


def test_publish_timeout_budget_is_not_the_falsified_600s():
    """Provenance guard: 600 s was falsified in production on 2026-08-07."""
    assert nightly.PUBLISH_TIMEOUT_S > 600
    assert nightly.PUBLISH_TIMEOUT_S == nightly.BACKUP_TIMEOUT_S
