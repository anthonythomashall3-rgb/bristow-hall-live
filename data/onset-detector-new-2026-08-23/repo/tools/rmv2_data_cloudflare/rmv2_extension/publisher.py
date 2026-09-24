"""Execute a reviewed R2 upload plan with pointer-last safety."""
from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable, Dict, Mapping, Optional

RECEIPT_SCHEMA = "recession-monitor-v2.r2-publication-receipt.v1"


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")
    fd, tmp_name = tempfile.mkstemp(prefix=".%s." % path.name, suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data); handle.flush(); os.fsync(handle.fileno())
        os.replace(tmp_name, str(path))
    except Exception:
        try: os.unlink(tmp_name)
        except OSError: pass
        raise


def _default_runner(command: str) -> int:
    return subprocess.run(command, shell=True, check=False).returncode


def _validate_plan(plan: Mapping[str, Any]) -> None:
    steps = list(plan.get("steps") or [])
    if plan.get("pointer_last") is not True or not steps or steps[-1].get("key") != "current.json":
        raise ValueError("upload plan must place current.json last")
    if any(step.get("key") == "current.json" for step in steps[:-1]):
        raise ValueError("current.json appears before the final step")
    if any(not step.get("immutable") for step in steps[:-1]):
        raise ValueError("all pre-pointer upload steps must be immutable")


def execute_upload_plan(
    plan: Mapping[str, Any],
    apply: bool = False,
    runner: Optional[Callable[[str], int]] = None,
    receipt_path: Optional[Path] = None,
) -> Dict[str, Any]:
    _validate_plan(plan)
    runner = runner or _default_runner
    receipt: Dict[str, Any] = {
        "schema_version": RECEIPT_SCHEMA,
        "generation_sha256": str(plan.get("generation_sha256") or ""),
        "started_at": _utc_now(),
        "finished_at": None,
        "status": "DRY_RUN" if not apply else "WORKING",
        "apply": bool(apply),
        "executed_steps": [],
        "failed_step": None,
        "pointer_switched": False,
    }
    if apply:
        for step in plan.get("steps") or []:
            command = str(step.get("command") or "")
            code = int(runner(command))
            record = {"key": step.get("key"), "command": command, "returncode": code}
            receipt["executed_steps"].append(record)
            if code != 0:
                receipt["status"] = "FAILED"
                receipt["failed_step"] = record
                break
            if step.get("key") == "current.json":
                receipt["pointer_switched"] = True
        else:
            receipt["status"] = "SUCCESS"
    receipt["finished_at"] = _utc_now()
    if receipt_path is not None:
        _atomic_json(Path(receipt_path), receipt)
    return receipt
