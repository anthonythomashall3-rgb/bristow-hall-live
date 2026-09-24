"""Create immutable-first, pointer-last Cloudflare R2 upload plans."""
from __future__ import annotations

import json
import mimetypes
import shlex
from pathlib import Path
from typing import Any, Dict, List

from .public_generation import verify_generation


def _content_type(path: Path) -> str:
    mapping = {".json": "application/json; charset=utf-8", ".jsonl": "application/x-ndjson; charset=utf-8", ".csv": "text/csv; charset=utf-8", ".html": "text/html; charset=utf-8"}
    return mapping.get(path.suffix.lower()) or mimetypes.guess_type(path.name)[0] or "application/octet-stream"


def _command(tool: str, bucket: str, key: str, path: Path, immutable: bool) -> str:
    if tool == "rclone":
        args = ["rclone", "copyto", str(path), "r2:%s/%s" % (bucket, key), "--checksum"]
        if immutable: args.append("--immutable")
    elif tool == "wrangler":
        args = ["npx", "wrangler", "r2", "object", "put", "%s/%s" % (bucket, key), "--file", str(path), "--remote", "--content-type", _content_type(path)]
    else:
        raise ValueError("unsupported upload tool: %s" % tool)
    return " ".join(shlex.quote(value) for value in args)


def build_upload_plan(bundle_root: Path, bucket: str, tool: str = "rclone") -> Dict[str, Any]:
    root = Path(bundle_root).resolve()
    pointer_path = root / "current.json"
    pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
    generation = str(pointer["generation_sha256"])
    check = verify_generation(root, generation)
    if not check["ok"]:
        raise ValueError("generation verification failed: %s" % check["errors"])
    generation_root = root / "generations" / generation
    steps: List[Dict[str, Any]] = []
    for path in sorted(p for p in generation_root.rglob("*") if p.is_file()):
        key = str(path.relative_to(root)).replace("\\", "/")
        steps.append({"key": key, "local_path": str(path), "immutable": True, "command": _command(tool, bucket, key, path, True)})
    steps.append({"key": "current.json", "local_path": str(pointer_path), "immutable": False, "command": _command(tool, bucket, "current.json", pointer_path, False)})
    return {"schema_version": "recession-monitor-v2.r2-upload-plan.v1", "tool": tool, "bucket": bucket, "generation_sha256": generation, "pointer_last": True, "steps": steps}
