"""B-SAFE-1 §4.2 — `bh receipt` chain-registering emitter.

The emitter wraps a loose body with the chain fields, runs the key-leak scan,
and writes the receipt INTO the chain directory (so `bh report --brief` heads at
it). It REFUSES to emit when any required chain field is missing.
"""

from __future__ import absolute_import

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from bh import receipts  # noqa: E402


def _make_repo(tmp):
    """A minimal tree resolve_repo() will accept (needs live_data + data_vault)."""
    root = Path(tmp)
    (root / "live_data").mkdir(exist_ok=True)
    (root / "data_vault").mkdir(exist_ok=True)
    return root


def _valid_kwargs():
    return dict(
        batch_id="TEST-BATCH",
        predecessor_receipt="PRED.v1.json",
        store_start_sha="a" * 64,
        store_end_sha="a" * 64,
        generation_id_in="b" * 64,
        generation_id_out="b" * 64,
        body={"stop": "planned", "note": "hello"},
    )


class ReceiptEmitTests(unittest.TestCase):
    def test_refuses_when_a_chain_field_is_missing(self):
        kwargs = _valid_kwargs()
        kwargs["store_end_sha"] = ""  # missing
        record = receipts.build_receipt(**kwargs)
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(tmp)
            with self.assertRaises(ValueError) as ctx:
                receipts.emit_receipt(record, "T.v1.json", repo=root)
            self.assertIn("chain.store_end_sha", str(ctx.exception))

    def test_registers_into_the_chain_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(tmp)
            record = receipts.build_receipt(**_valid_kwargs())
            path = receipts.emit_receipt(record, "ZZZ_NEWEST.v1.json", repo=root)
            self.assertTrue(path.exists())
            # written under the chain dir, and discoverable as the latest receipt
            self.assertIn("generated_live", path.as_posix())
            self.assertEqual(receipts.latest_receipt_name(repo=root), "ZZZ_NEWEST.v1.json")

    def test_cli_refuses_missing_chain_arg(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(tmp)
            body_file = root / "body.json"
            body_file.write_text(json.dumps({"stop": "planned"}), encoding="utf-8")

            class Args:
                repo = str(root)
                body = str(body_file)
                batch_id = "T"
                predecessor = "PRED.v1.json"
                store_start = "a" * 64
                store_end = ""  # missing
                gen_in = "b" * 64
                gen_out = "b" * 64
                out = "T.v1.json"

            rc = receipts.cli(Args())
            self.assertNotEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
