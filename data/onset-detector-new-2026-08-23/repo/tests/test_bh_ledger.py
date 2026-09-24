"""bh ledger — DONE.md close-out stamp lint (B-HOUSE-3 Defect 1)."""

from __future__ import annotations

from datetime import datetime, timezone

from bh import ledger


def _epoch(stamp: str) -> float:
    return datetime.strptime(stamp, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc).timestamp()


def test_parse_done_rows_skips_notes_and_markers():
    text = (
        "# a correction note line\n"
        "\n"
        "B-OFFLINE-5_NBER_REMAINDER  20260806T120000Z  COMPLETE\n"
        "IDLE_W2 marker with no stamp column here\n"
        "B-SCI-1_REGISTRY_DECLARATIONS  20260806T111611Z  STOP\n"
    )
    rows = ledger.parse_done_rows(text)
    assert [r["batch_id"] for r in rows] == [
        "B-OFFLINE-5_NBER_REMAINDER", "B-SCI-1_REGISTRY_DECLARATIONS"]
    assert rows[0]["status"] == "COMPLETE"
    assert rows[1]["status"] == "STOP"


def test_find_backdated_flags_stamp_before_brief():
    # the real CH-R49/R51 defect: stamp 06:35 but brief written 06:48
    rows = [{"batch_id": "CH-R49", "stamp": "20260806T063500Z", "status": "COMPLETE"}]
    mtimes = {"CH-R49": _epoch("20260806T064844Z")}
    v = ledger.find_backdated(rows, mtimes)
    assert len(v) == 1
    assert v[0]["batch_id"] == "CH-R49"
    assert v[0]["backdated_seconds"] == 824.0  # 06:48:44 - 06:35:00 = 13m44s


def test_find_backdated_clean_when_stamp_after_brief():
    rows = [{"batch_id": "B-X", "stamp": "20260806T070000Z", "status": "COMPLETE"}]
    mtimes = {"B-X": _epoch("20260806T065000Z")}
    assert ledger.find_backdated(rows, mtimes) == []


def test_find_backdated_ignores_rows_without_a_brief():
    rows = [{"batch_id": "IDLE_W2", "stamp": "20260806T010000Z", "status": "COMPLETE"}]
    assert ledger.find_backdated(rows, {}) == []  # no brief -> not judged


def test_lint_done_file_end_to_end(tmp_path):
    briefs = tmp_path / "briefs"
    briefs.mkdir()
    good = briefs / "B-GOOD.md"
    good.write_text("ok")
    import os
    os.utime(good, (_epoch("20260806T065000Z"), _epoch("20260806T065000Z")))
    bad = briefs / "B-BAD.md"
    bad.write_text("late brief")
    os.utime(bad, (_epoch("20260806T064844Z"), _epoch("20260806T064844Z")))
    done = tmp_path / "DONE.md"
    done.write_text(
        "B-GOOD  20260806T070000Z  COMPLETE\n"
        "B-BAD   20260806T063500Z  COMPLETE\n"
    )
    v = ledger.lint_done_file(done, briefs)
    assert [x["batch_id"] for x in v] == ["B-BAD"]


def test_now_stamp_is_close_out_shaped():
    s = ledger.now_stamp()
    assert ledger.STAMP_RE.match(s)
    # round-trips through the parser used by the linter
    assert ledger.parse_stamp(s).tzinfo is timezone.utc
