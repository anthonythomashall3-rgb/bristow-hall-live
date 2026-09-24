"""Content-addressed model specifications and append-only experiment records."""

import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Dict


def spec_hash(spec: Dict[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(spec, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def append_experiment(path: Path, record: Dict[str, object]) -> str:
    path = Path(path)
    payload = dict(record)
    payload.setdefault("recorded_at", dt.datetime.now(dt.timezone.utc).isoformat())
    payload["spec_hash"] = spec_hash(payload["spec"])
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            existing = json.loads(line)
            if existing.get("run_id") == payload.get("run_id"):
                if existing != payload:
                    raise ValueError("run_id already exists with different content")
                return payload["spec_hash"]
    with path.open("a", encoding="utf-8") as handle:
        handle.write(serialized + "\n")
    return payload["spec_hash"]
