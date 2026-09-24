"""Dependency-light, fail-closed concurrent acquisition for source recipes."""
from __future__ import annotations

import concurrent.futures
import dataclasses
import datetime as dt
import hashlib
import json
import os
import tempfile
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

RECEIPT_SCHEMA = "recession-monitor-v2.fetch-receipt.v1"


@dataclasses.dataclass(frozen=True)
class FetchRecipe:
    recipe_id: str
    url: str
    destination: str
    allowed_hosts: Sequence[str]
    allowed_content_types: Sequence[str]
    min_bytes: int = 1
    max_bytes: int = 100 * 1024 * 1024
    required_prefix: str = ""
    retries: int = 2
    timeout_seconds: float = 30.0
    backoff_seconds: float = 0.25
    max_concurrency_per_host: int = 2
    headers: Optional[Mapping[str, str]] = None


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_relative(value: str) -> Path:
    candidate = Path(value)
    if not value or candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError("unsafe destination: %s" % value)
    return candidate


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=".%s." % path.name, suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, str(path))
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def _canonical_json(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def _validate_recipe(recipe: FetchRecipe) -> None:
    if not recipe.recipe_id or any(part in recipe.recipe_id for part in ("/", "\\", "..")):
        raise ValueError("unsafe recipe id: %s" % recipe.recipe_id)
    _safe_relative(recipe.destination)
    parsed = urllib.parse.urlparse(recipe.url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("unsupported URL: %s" % recipe.url)
    if recipe.min_bytes < 0 or recipe.max_bytes < recipe.min_bytes:
        raise ValueError("invalid byte limits")


def _validate_response(recipe: FetchRecipe, data: bytes, content_type: str) -> None:
    if len(data) < recipe.min_bytes:
        raise ValueError("response is smaller than min_bytes")
    if len(data) > recipe.max_bytes:
        raise ValueError("response exceeds max_bytes")
    normalized = (content_type or "").split(";", 1)[0].strip().lower()
    allowed = {value.split(";", 1)[0].strip().lower() for value in recipe.allowed_content_types}
    if allowed and normalized not in allowed:
        raise ValueError("content type %s is not allowed" % normalized)
    lower = data[:512].lstrip().lower()
    if lower.startswith(b"<!doctype html") or lower.startswith(b"<html"):
        raise ValueError("HTML response is not accepted as data")
    if recipe.required_prefix and not data.startswith(recipe.required_prefix.encode("utf-8")):
        raise ValueError("required prefix is absent")


def _fetch_one(recipe: FetchRecipe, output_root: Path, semaphore: threading.Semaphore) -> Dict[str, Any]:
    parsed = urllib.parse.urlparse(recipe.url)
    host = (parsed.hostname or "").lower()
    receipt: Dict[str, Any] = {
        "schema_version": RECEIPT_SCHEMA,
        "recipe_id": recipe.recipe_id,
        "url": recipe.url,
        "destination": recipe.destination,
        "retrieved_at": _utc_now(),
        "status": "FAILED",
        "attempts": 0,
        "sha256": "",
        "bytes": 0,
        "content_type": "",
        "error": "",
    }
    if host not in {value.lower() for value in recipe.allowed_hosts}:
        receipt["error"] = "host is not in allowed_hosts: %s" % host
        return receipt
    last_error = ""
    with semaphore:
        for attempt in range(recipe.retries + 1):
            receipt["attempts"] = attempt + 1
            try:
                request = urllib.request.Request(recipe.url, headers=dict(recipe.headers or {}))
                with urllib.request.urlopen(request, timeout=recipe.timeout_seconds) as response:
                    data = response.read(recipe.max_bytes + 1)
                    content_type = response.headers.get("Content-Type", "application/octet-stream")
                _validate_response(recipe, data, content_type)
                destination = output_root / _safe_relative(recipe.destination)
                _atomic_write(destination, data)
                receipt.update({
                    "status": "SUCCESS", "sha256": _sha256(data), "bytes": len(data),
                    "content_type": content_type, "error": "", "retrieved_at": _utc_now(),
                })
                return receipt
            except Exception as exc:  # recorded, never converted to absence
                last_error = "%s: %s" % (type(exc).__name__, exc)
                if attempt < recipe.retries:
                    time.sleep(recipe.backoff_seconds * (2 ** attempt))
    receipt["error"] = last_error
    return receipt


def collect_recipes(
    recipes: Iterable[FetchRecipe],
    output_root: Path,
    max_workers: int = 8,
) -> List[Dict[str, Any]]:
    rows = list(recipes)
    for recipe in rows:
        _validate_recipe(recipe)
    output_root = Path(output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    semaphores: Dict[str, threading.Semaphore] = {}
    for recipe in rows:
        host = (urllib.parse.urlparse(recipe.url).hostname or "").lower()
        if host not in semaphores:
            semaphores[host] = threading.Semaphore(max(1, int(recipe.max_concurrency_per_host)))
    results: List[Dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, int(max_workers))) as executor:
        futures = {
            executor.submit(_fetch_one, recipe, output_root, semaphores[(urllib.parse.urlparse(recipe.url).hostname or "").lower()]): recipe
            for recipe in rows
        }
        for future in concurrent.futures.as_completed(futures):
            receipt = future.result()
            receipt_path = output_root / "receipts" / (receipt["recipe_id"] + ".json")
            _atomic_write(receipt_path, _canonical_json(receipt))
            results.append(receipt)
    return sorted(results, key=lambda item: item["recipe_id"])


def recipe_from_mapping(value: Mapping[str, Any]) -> FetchRecipe:
    return FetchRecipe(
        recipe_id=str(value["recipe_id"]), url=str(value["url"]), destination=str(value["destination"]),
        allowed_hosts=list(value.get("allowed_hosts") or []),
        allowed_content_types=list(value.get("allowed_content_types") or []),
        min_bytes=int(value.get("min_bytes", 1)), max_bytes=int(value.get("max_bytes", 100 * 1024 * 1024)),
        required_prefix=str(value.get("required_prefix") or ""), retries=int(value.get("retries", 2)),
        timeout_seconds=float(value.get("timeout_seconds", 30)), backoff_seconds=float(value.get("backoff_seconds", 0.25)),
        max_concurrency_per_host=int(value.get("max_concurrency_per_host", 2)), headers=value.get("headers") or {},
    )
