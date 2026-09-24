"""Build immutable, content-addressed public data generations."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import mimetypes
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

MANIFEST_SCHEMA = "recession-monitor-v2.public-generation-manifest.v1"
POINTER_SCHEMA = "recession-monitor-v2.public-generation-pointer.v1"

_CONTENT_TYPES = {
    ".json": "application/json; charset=utf-8",
    ".jsonl": "application/x-ndjson; charset=utf-8",
    ".csv": "text/csv; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".parquet": "application/vnd.apache.parquet",
}


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_relative(value: str) -> Path:
    candidate = Path(value)
    if not value or candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError("unsafe relative path: %s" % value)
    return candidate


def _resolve_source(root: Path, value: str) -> Path:
    relative = _safe_relative(value)
    path = root / relative
    if path.is_symlink() or not path.is_file():
        raise ValueError("source is missing, non-file, or symlink: %s" % value)
    resolved = path.resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError("unsafe source path: %s" % value) from exc
    return resolved


def _content_type(path: Path) -> str:
    return _CONTENT_TYPES.get(path.suffix.lower()) or mimetypes.guess_type(path.name)[0] or "application/octet-stream"


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=".%s." % path.name, suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data); handle.flush(); os.fsync(handle.fileno())
        os.replace(tmp_name, str(path))
    except Exception:
        try: os.unlink(tmp_name)
        except OSError: pass
        raise


def build_generation(
    source_root: Path,
    output_root: Path,
    entries: Iterable[Mapping[str, Any]],
    generated_at: Optional[str] = None,
) -> Dict[str, Any]:
    source_root = Path(source_root).resolve()
    output_root = Path(output_root).resolve()
    generated_at = generated_at or _utc_now()
    normalized: List[Dict[str, Any]] = []
    seen = set()
    for raw in entries:
        public_path = str(raw.get("public_path") or "")
        source = str(raw.get("source") or "")
        _safe_relative(public_path); _safe_relative(source)
        if public_path in seen:
            raise ValueError("duplicate public path: %s" % public_path)
        seen.add(public_path)
        if raw.get("public_eligible") is not True:
            raise ValueError("not public-eligible: %s" % source)
        rights = str(raw.get("rights_status") or "")
        if not rights or any(word in rights for word in ("pending", "restricted", "not_cleared")):
            raise ValueError("not public-eligible rights status for %s: %s" % (source, rights))
        # Publish-side rights firewall (B-LAND-11-R2). A member carrying the
        # internal_only publish_class is licensed for internal use only and must
        # never be copied into a content-addressed public bundle, regardless of
        # its free-text rights_status. Fail-closed before any file is copied.
        publish_class = str(raw.get("publish_class") or "")
        if publish_class == "internal_only":
            raise ValueError(
                "publish_class internal_only forbids public emission for %s" % source
            )
        normalized.append({
            "source": source, "public_path": public_path, "rights_status": rights,
            "source_name": str(raw.get("source_name") or source),
            "attribution": str(raw.get("attribution") or ""),
        })
    normalized.sort(key=lambda item: item["public_path"])
    output_root.mkdir(parents=True, exist_ok=True)
    generations_root = output_root / "generations"; generations_root.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".generation-", dir=str(output_root)))
    try:
        members: List[Dict[str, Any]] = []
        for item in normalized:
            source_path = _resolve_source(source_root, item["source"])
            destination = staging / _safe_relative(item["public_path"])
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(str(source_path), str(destination))
            members.append({
                "path": item["public_path"], "bytes": destination.stat().st_size,
                "sha256": _sha256_file(destination), "content_type": _content_type(destination),
                "source_name": item["source_name"], "source_path": item["source"],
                "rights_status": item["rights_status"], "attribution": item["attribution"],
            })
        manifest = {"schema_version": MANIFEST_SCHEMA, "generated_at": generated_at, "member_count": len(members), "members": members}
        manifest_bytes = _canonical_json_bytes(manifest)
        generation_sha256 = _sha256_bytes(manifest_bytes)
        _atomic_write(staging / "manifest.json", manifest_bytes)
        final_dir = generations_root / generation_sha256
        if final_dir.exists():
            check = verify_generation(output_root, generation_sha256)
            if not check["ok"]:
                raise RuntimeError("existing generation is invalid: %s" % check["errors"])
            shutil.rmtree(staging)
        else:
            os.replace(str(staging), str(final_dir))
        pointer = {
            "schema_version": POINTER_SCHEMA, "generation_sha256": generation_sha256,
            "generated_at": generated_at, "manifest_path": "generations/%s/manifest.json" % generation_sha256,
        }
        _atomic_write(output_root / "current.json", _canonical_json_bytes(pointer))
        return pointer
    except Exception:
        if staging.exists(): shutil.rmtree(staging, ignore_errors=True)
        raise


def verify_generation(output_root: Path, generation_sha256: str) -> Dict[str, Any]:
    output_root = Path(output_root).resolve()
    generation_dir = output_root / "generations" / generation_sha256
    errors: List[str] = []
    try:
        manifest = json.loads((generation_dir / "manifest.json").read_text(encoding="utf-8"))
    except Exception as exc:
        return {"ok": False, "errors": ["manifest unreadable: %s" % exc]}
    if _sha256_bytes(_canonical_json_bytes(manifest)) != generation_sha256:
        errors.append("manifest hash mismatch")
    members = manifest.get("members") or []
    if manifest.get("member_count") != len(members):
        errors.append("member count mismatch")
    for member in members:
        try:
            relative = _safe_relative(str(member["path"]))
        except Exception as exc:
            errors.append("unsafe member path: %s" % exc); continue
        path = generation_dir / relative
        if not path.is_file() or path.is_symlink():
            errors.append("member missing or invalid: %s" % member.get("path")); continue
        if path.stat().st_size != member.get("bytes"):
            errors.append("member size mismatch: %s" % member.get("path"))
        if _sha256_file(path) != member.get("sha256"):
            errors.append("member hash mismatch: %s" % member.get("path"))
    return {"ok": not errors, "errors": errors, "generation_sha256": generation_sha256}
