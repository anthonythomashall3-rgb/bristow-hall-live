"""`bh report --brief` — the derived batch brief — A2 §19.

Emits a short summary derived from the latest bh-emitted batch receipt: batch
id, whether a STOP was reached and where, gates that passed, measured numbers
that changed, open blockers, and the next batch per the receipt's own
predecessor/next field. Everything else stays on disk. Ten-ish lines, no prose.

The brief is passed through the key-leak scan before printing (A2 §13 / §40):
a credential shape aborts the emit.
"""

from __future__ import annotations

import json

from . import keyleak, receipts


def _latest_receipt_record():
    name = receipts.latest_receipt_name()
    if name == "none":
        return None, None
    path = receipts.receipts_dir() / name
    try:
        return name, json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return name, None


def brief() -> str:
    name, record = _latest_receipt_record()
    if record is None:
        return f"bh report: no readable batch receipt (latest={name})"
    body = record.get("body", {}) if isinstance(record, dict) else {}
    chain = record.get("chain", {})
    lines = [
        f"batch: {record.get('batch_id', '?')}  ({name})",
        f"generated_at: {record.get('generated_at', '?')}",
        f"predecessor: {chain.get('predecessor_receipt', '?')}",
        f"store: {chain.get('store_start_sha', '?')[:12]} -> {chain.get('store_end_sha', '?')[:12]}",
        f"stop: {body.get('stop', '?')}",
        f"gates: {body.get('gates_summary', '?')}",
        f"changed: {body.get('changed_numbers', '?')}",
        f"open_blockers: {body.get('open_blockers', '?')}",
        f"next: {body.get('next_batch', '?')}",
    ]
    return "\n".join(lines)


def cli(args) -> int:
    text = brief()
    keyleak.assert_clean(text, where="report --brief")
    print(text)
    return 0
