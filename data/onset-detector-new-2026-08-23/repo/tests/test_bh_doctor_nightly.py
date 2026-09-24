"""bh doctor — nightly health check (B-AUTO-2 item 3).

Doctor must FAIL when the last nightly run failed, or when no successful run
exists within the expected interval. Nothing surfaced the broken nightly before;
this is the surface.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from bh import doctor, nightly


def _stamp(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


@pytest.fixture
def repo(tmp_path, monkeypatch):
    monkeypatch.setattr(doctor.paths, "resolve_repo", lambda *a, **k: tmp_path)
    return tmp_path


def _write_status(repo, status):
    path = repo / nightly.NIGHTLY_STATUS_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    import json

    path.write_text(json.dumps(status), encoding="utf-8")


def test_nightly_check_fails_when_never_run(repo):
    name, ok, detail = doctor._check_nightly()
    assert name == "nightly"
    assert ok is False
    assert "never" in detail.lower() or "absent" in detail.lower()


def test_nightly_check_fails_when_last_run_failed(repo):
    now = _stamp(datetime.now(timezone.utc))
    _write_status(repo, {"run_at": now, "ok": False, "failed": "backup",
                         "failed_steps": ["backup"], "last_success_at": None})
    name, ok, detail = doctor._check_nightly()
    assert ok is False
    assert "backup" in detail


def test_nightly_check_fails_when_success_is_stale(repo):
    old = _stamp(datetime.now(timezone.utc) - timedelta(hours=nightly.NIGHTLY_MAX_AGE_H + 5))
    _write_status(repo, {"run_at": old, "ok": True, "failed": None,
                         "failed_steps": [], "last_success_at": old})
    name, ok, detail = doctor._check_nightly()
    assert ok is False
    assert "within" in detail


def test_nightly_check_passes_on_recent_success(repo):
    now = _stamp(datetime.now(timezone.utc))
    _write_status(repo, {"run_at": now, "ok": True, "failed": None,
                         "failed_steps": [], "last_success_at": now})
    name, ok, detail = doctor._check_nightly()
    assert ok is True
    assert "last run ok" in detail


def test_nightly_check_included_in_doctor_run(repo):
    now = _stamp(datetime.now(timezone.utc))
    _write_status(repo, {"run_at": now, "ok": True, "failed": None,
                         "failed_steps": [], "last_success_at": now})
    _, checks = doctor.run()
    assert any(name == "nightly" for name, _, _ in checks)
