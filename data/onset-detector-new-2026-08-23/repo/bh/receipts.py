"""Chained receipt emission and validation — A2 §7 / rulebook §1.1a.

Every receipt emitted from now on records the chain fields that make the
incremental start-gate (A2 §2) safe in perpetuity: predecessor receipt
filename, store start sha, store end sha, and generation id in/out. A test
(tests/test_bh_receipt_chain.py) fails on any receipt missing them.

Historical receipts are NOT backfilled (A2 §2.3 note) — a reconstructed chain
proves nothing. This validates receipts emitted through this module going
forward.

Every write is passed through the key-leak scan first (A2 §13 / §55.4): a
credential shape in a receipt aborts the write.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from . import keyleak, paths

RECEIPTS_DIRNAME = Path("tools") / "rmv2_data_cloudflare" / "generated_live"

CHAIN_FIELDS = (
    "predecessor_receipt",
    "store_start_sha",
    "store_end_sha",
    "generation_id_in",
    "generation_id_out",
)


def receipts_dir(repo: Path | None = None) -> Path:
    return paths.resolve_repo(str(repo) if repo else None) / RECEIPTS_DIRNAME


def store_generation_sha(repo: Path | None = None) -> str:
    """The live store's current generation id (A2 §7). 'none' if no pointer."""
    root = paths.resolve_repo(str(repo) if repo else None)
    pointer = root / "live_data" / "public" / "latest.pointer.json"
    try:
        return json.loads(pointer.read_text(encoding="utf-8"))["generation_sha256"]
    except (OSError, json.JSONDecodeError, KeyError):
        return "none"


def latest_receipt_name(repo: Path | None = None) -> str:
    directory = receipts_dir(repo)
    if not directory.is_dir():
        return "none"
    receipts = sorted(directory.glob("*.v1.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return receipts[0].name if receipts else "none"


def validate_receipt(record: dict) -> list[str]:
    """Return the list of missing/empty chain fields (empty == well-formed)."""
    chain = record.get("chain")
    if not isinstance(chain, dict):
        return ["chain"] + [f"chain.{f}" for f in CHAIN_FIELDS]
    missing = []
    for field in CHAIN_FIELDS:
        value = chain.get(field)
        if value in (None, ""):
            missing.append(f"chain.{field}")
    return missing


def build_receipt(
    *,
    batch_id: str,
    predecessor_receipt: str,
    store_start_sha: str,
    store_end_sha: str,
    generation_id_in: str,
    generation_id_out: str,
    body: dict,
) -> dict:
    record = {
        "schema_version": "recession-monitor-v2.batch-receipt.v1",
        "batch_id": batch_id,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "chain": {
            "predecessor_receipt": predecessor_receipt,
            "store_start_sha": store_start_sha,
            "store_end_sha": store_end_sha,
            "generation_id_in": generation_id_in,
            "generation_id_out": generation_id_out,
        },
        "body": body,
    }
    return record


def emit_receipt(record: dict, filename: str, repo: Path | None = None) -> Path:
    """Validate chain, key-leak scan, then atomically write (A2 §7 / §13)."""
    missing = validate_receipt(record)
    if missing:
        raise ValueError(f"receipt {filename} missing chain fields: {', '.join(missing)}")
    text = json.dumps(record, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    keyleak.assert_clean(text, where=f"receipt {filename}")
    directory = receipts_dir(repo)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / filename
    tmp = directory / (filename + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)
    return path


def cli(args) -> int:
    """bh receipt — wrap a loose JSON body with the chain fields, run the
    key-leak scan, and register the receipt INTO the chain dir (B-SAFE-1 §4.2).
    Refuses (non-zero) when a body is unreadable or any chain field is missing.
    """
    repo = Path(args.repo) if getattr(args, "repo", None) else None
    try:
        body = json.loads(Path(args.body).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"bh receipt: cannot read body {args.body}: {exc}")
        return 2
    record = build_receipt(
        batch_id=args.batch_id,
        predecessor_receipt=args.predecessor,
        store_start_sha=args.store_start,
        store_end_sha=args.store_end,
        generation_id_in=args.gen_in,
        generation_id_out=args.gen_out,
        body=body,
    )
    try:
        path = emit_receipt(record, args.out, repo=repo)
    except ValueError as exc:
        print(f"bh receipt REFUSED: {exc}")
        return 1
    except keyleak.KeyLeak as exc:
        print(f"bh receipt ABORTED (key-leak): {exc}")
        return 1
    print(f"bh receipt: emitted {path}")
    return 0
