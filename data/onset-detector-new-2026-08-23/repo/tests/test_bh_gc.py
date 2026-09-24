"""B-SAFE-1 §3 — `bh gc` and the walker robustness that makes it stick.

Two invariants:

  1. The vault/payload walkers never count macOS/Python tree cruft (.DS_Store,
     __pycache__, *.pyc) as a payload. A stray .DS_Store dropped by Finder into
     a payload root must NOT break `verify_data_vault.py` — the gate passes
     "without a tree clean". (RED before the walkers exclude .DS_Store.)

  2. The pure data stores stay free of that cruft on disk after `bh gc`. The
     ten .DS_Store the batch measured live under live_data/store/. (RED while
     they exist.)

`__pycache__` regenerates whenever Python imports a module, so invariant 2 is
scoped to the DATA stores (content-addressed; nothing imports from them), never
the code roots where a cache dir is normal and gitignored.
"""

from __future__ import absolute_import

import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "data_vault" / "scripts"))

import verify_data_vault as vdv  # noqa: E402
import build_handoff_manifest as bhm  # noqa: E402
from bh import gc as bh_gc  # noqa: E402

# Content-addressed data stores: no .py is imported from these, so a cache dir
# or .DS_Store here is pure cruft, never legitimate.
DATA_STORE_ROOTS = ("live_data/store", "live_data/feed_factory", "data_archive")


def _seed_payload_tree(root):
    for payload_root in vdv.PAYLOAD_ROOTS:
        d = root / payload_root
        d.mkdir(parents=True, exist_ok=True)
        (d / "real_payload.csv").write_text("value\n1\n", encoding="utf-8")
        (d / ".DS_Store").write_bytes(b"\x00\x01Bud1")
        cache = d / "__pycache__"
        cache.mkdir(exist_ok=True)
        (cache / "mod.cpython-38.pyc").write_bytes(b"\x00")


class WalkerCruftExclusionTests(unittest.TestCase):
    def test_discover_payloads_excludes_tree_cruft(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_payload_tree(root)
            got = vdv.discover_payloads(root)
            self.assertTrue(any(p.endswith("real_payload.csv") for p in got), got)
            self.assertFalse(any(p.endswith(".DS_Store") for p in got), got)
            self.assertFalse(
                any("__pycache__" in p or p.endswith(".pyc") for p in got), got
            )

    def test_verify_handoff_paths_excludes_dsstore(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = root / "data_vault"
            vault.mkdir(parents=True)
            (vault / "catalog.csv").write_text("a\n", encoding="utf-8")
            (vault / ".DS_Store").write_bytes(b"\x00")
            got = vdv.handoff_paths(root)
            self.assertFalse(any(p.endswith(".DS_Store") for p in got), got)

    def test_build_manifest_handoff_paths_excludes_dsstore(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = root / "data_vault"
            vault.mkdir(parents=True)
            (vault / "catalog.csv").write_text("a\n", encoding="utf-8")
            (vault / ".DS_Store").write_bytes(b"\x00")
            got = bhm.handoff_paths(root)
            self.assertFalse(any(p.endswith(".DS_Store") for p in got), got)


def _cruft_under(roots):
    offenders = []
    for rel in roots:
        base = REPO / rel
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if (
                path.name == ".DS_Store"
                or "__pycache__" in path.parts
                or path.suffix == ".pyc"
            ):
                offenders.append(path.relative_to(REPO).as_posix())
    return offenders


class DataStoreCleanlinessTests(unittest.TestCase):
    def test_gc_purges_the_data_stores(self):
        # macOS re-drops .DS_Store into any dir Finder/Spotlight touches, so the
        # durable invariant is that `bh gc` PURGES them — not that the OS never
        # writes one. Run gc, then assert the data stores are clean immediately.
        bh_gc.purge()
        self.assertEqual(
            _cruft_under(DATA_STORE_ROOTS), [],
            "bh gc left tree cruft under data stores",
        )


if __name__ == "__main__":
    unittest.main()
