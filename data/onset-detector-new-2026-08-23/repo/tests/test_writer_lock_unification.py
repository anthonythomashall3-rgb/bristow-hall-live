import json

import pytest

from bh import writer_lock
from live_data.rmv2_live.store import LiveStore


def _store(root):
    (root / "data_vault").mkdir()
    return LiveStore(
        root,
        {
            "store": {
                "root": "live_data/store",
                "public": "live_data/public",
                "runtime": "live_data/runtime",
            }
        },
    )


def test_store_and_batch_tools_share_one_instrumented_writer_barrier(tmp_path):
    store = _store(tmp_path)
    sidecar = tmp_path / "live_data/runtime/refresh.lock.holder.json"

    with store.refresh_lock("live-store-unit-test"):
        holder = json.loads(sidecar.read_text(encoding="utf-8"))
        assert holder["label"] == "live-store-unit-test"
        with pytest.raises(writer_lock.WriterLockHeld):
            with writer_lock.writer_lock("batch-unit-test", repo=tmp_path):
                raise AssertionError("second writer entered")

    assert not sidecar.exists()
    with writer_lock.writer_lock("batch-unit-test", repo=tmp_path):
        with pytest.raises(RuntimeError, match="already running"):
            with store.refresh_lock("live-store-unit-test"):
                raise AssertionError("second writer entered")


def test_coordinator_locks_are_not_misidentified_as_store_writer_locks():
    assert writer_lock.lock_path().name == "refresh.lock"
