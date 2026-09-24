"""Promotion ledger — derived criterion, sha-mismatch demotion (B-AUTO-1 §3)."""

from __future__ import annotations

from pathlib import Path

import pytest

from bh import promotion


def _write_runbook(tmp_path: Path, name: str, body: str = "#!/bin/sh\nexit 0\n") -> Path:
    p = tmp_path / name
    p.write_text(body, encoding="utf-8")
    return p


def test_criterion_is_derived_from_cited_classes():
    crit = promotion._derivation()
    assert crit["value"] == len(promotion.MEASURED_FAILURE_CLASSES)
    assert crit["value"] >= 5  # at least the five named in the batch header
    for cls in crit["measured_failure_classes"]:
        assert cls["class"] and cls["citation"], "every class must carry a citation"


def test_promotes_only_at_criterion_and_read_only(tmp_path):
    rb = _write_runbook(tmp_path, "chore.sh")
    ledger = promotion.default_ledger()
    promotion.register_runbook(ledger, "chore", str(rb), read_only=True)
    sha = promotion.sha256_file(rb)
    for i in range(promotion.PROMOTION_CRITERION - 1):
        promotion.record_clean_run(ledger, "chore", sha)
    v = promotion.check_promotion(ledger, rb)
    assert not v["ok"], "must not promote before criterion"
    promotion.record_clean_run(ledger, "chore", sha)  # reaches criterion
    v = promotion.check_promotion(ledger, rb)
    assert v["ok"], v["reason"]


def test_store_writing_runbook_never_auto_promotes(tmp_path):
    rb = _write_runbook(tmp_path, "writer.sh")
    ledger = promotion.default_ledger()
    promotion.register_runbook(ledger, "writer", str(rb), read_only=False)
    sha = promotion.sha256_file(rb)
    for _ in range(promotion.PROMOTION_CRITERION + 3):
        promotion.record_clean_run(ledger, "writer", sha)
    entry = promotion._find(ledger, "writer")
    assert entry["unattended"] is False, "read_only=False must not be auto-promoted (stage 1)"


def test_byte_change_demotes_via_sha_mismatch(tmp_path):
    rb = _write_runbook(tmp_path, "chore.sh")
    ledger = promotion.default_ledger()
    promotion.register_runbook(ledger, "chore", str(rb), read_only=True)
    sha = promotion.sha256_file(rb)
    for _ in range(promotion.PROMOTION_CRITERION):
        promotion.record_clean_run(ledger, "chore", sha)
    assert promotion.check_promotion(ledger, rb)["ok"]
    rb.write_text("#!/bin/sh\necho edited\nexit 0\n", encoding="utf-8")  # edit bytes
    v = promotion.check_promotion(ledger, rb)
    assert not v["ok"] and v.get("sha_mismatch"), "edited runbook must be refused"


def test_ledger_round_trips_single_file(tmp_repo):
    repo = tmp_repo
    ledger = promotion.default_ledger()
    rb = _write_runbook(repo, "chore.sh")
    promotion.register_runbook(ledger, "chore", str(rb), read_only=True)
    path = promotion.save_ledger(ledger, repo)
    assert path == promotion.ledger_path(repo)
    reloaded = promotion.load_ledger(repo)
    assert reloaded["schema"] == promotion.SCHEMA
    assert len(reloaded["runbooks"]) == 1


@pytest.fixture
def tmp_repo(tmp_path):
    (tmp_path / "live_data" / "config").mkdir(parents=True)
    (tmp_path / "data_vault").mkdir()
    return tmp_path
