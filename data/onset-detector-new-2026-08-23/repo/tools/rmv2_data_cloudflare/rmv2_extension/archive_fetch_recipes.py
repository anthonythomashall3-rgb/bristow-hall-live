"""Convert reviewed archive-discovery output into candidate-only fetch recipes."""
from __future__ import annotations

import hashlib
import re
import urllib.parse
from pathlib import PurePosixPath
from typing import Any, Dict, List, Mapping

_SCHEMA_VERSION = "recession-monitor-v2.archive-fetch-recipes.v1"
_SAFE_COMPONENT = re.compile(r"[^A-Za-z0-9._-]+")

_CONTENT_TYPES = {
    ".pdf": ["application/pdf", "application/octet-stream"],
    ".csv": ["text/csv", "application/csv", "application/octet-stream", "text/plain"],
    ".json": ["application/json", "application/octet-stream", "text/plain"],
    ".jsonl": ["application/x-ndjson", "application/json", "application/octet-stream", "text/plain"],
    ".zip": ["application/zip", "application/x-zip-compressed", "application/octet-stream"],
    ".xlsx": ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/zip", "application/octet-stream"],
    ".xls": ["application/vnd.ms-excel", "application/octet-stream"],
    ".xml": ["application/xml", "text/xml", "application/octet-stream", "text/plain"],
    ".txt": ["text/plain", "application/octet-stream"],
}

_PREFIXES = {".pdf": "%PDF", ".zip": "PK", ".xlsx": "PK"}


def _safe_component(value: str, fallback: str) -> str:
    cleaned = _SAFE_COMPONENT.sub("-", value.strip()).strip("-._")
    return cleaned or fallback


def _destination(archive_id: str, url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    basename = PurePosixPath(parsed.path).name or "download"
    basename = _safe_component(basename, "download")
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    return "archive_candidates/%s/%s-%s" % (
        _safe_component(archive_id, "archive"), digest, basename,
    )


def build_archive_fetch_recipes(discovery: Mapping[str, Any]) -> Dict[str, Any]:
    """Return deterministic candidate recipes for successful discovered links.

    Archive bytes are never public-eligible or canonical by this conversion alone.
    Feed Factory identity, parser, rights, and semantic review remain required.
    """
    recipes: List[Dict[str, Any]] = []
    seen_urls = set()
    failed_archives: List[Dict[str, str]] = []
    for result in discovery.get("results") or []:
        archive_id = str(result.get("archive_id") or "archive")
        if result.get("status") != "SUCCESS":
            failed_archives.append({
                "archive_id": archive_id,
                "error": str(result.get("error") or "discovery_failed"),
            })
            continue
        for raw_url in result.get("links") or []:
            url = str(raw_url)
            if url in seen_urls:
                continue
            seen_urls.add(url)
            parsed = urllib.parse.urlparse(url)
            if parsed.scheme not in ("http", "https") or not parsed.hostname:
                continue
            suffix = PurePosixPath(parsed.path).suffix.lower()
            content_types = _CONTENT_TYPES.get(
                suffix, ["application/octet-stream", "text/plain"]
            )
            digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
            recipes.append({
                "recipe_id": "archive_%s_%s" % (
                    _safe_component(archive_id, "archive").lower(), digest
                ),
                "archive_id": archive_id,
                "enabled": True,
                "candidate_only": True,
                "public_eligible": False,
                "url": url,
                "destination": _destination(archive_id, url),
                "allowed_hosts": [parsed.hostname.lower()],
                "allowed_content_types": content_types,
                "min_bytes": 32,
                "max_bytes": 250 * 1024 * 1024,
                "required_prefix": _PREFIXES.get(suffix, ""),
                "retries": 2,
                "timeout_seconds": 120,
                "backoff_seconds": 1.0,
                "max_concurrency_per_host": 2,
                "rights_status": "review_required_before_public_export",
                "admission_note": (
                    "Candidate archive bytes only. Exact publisher identity, release stage, "
                    "parser, rights, and Feed Factory review are required before canonical use."
                ),
            })
    recipes.sort(key=lambda row: (row["archive_id"], row["url"]))
    failed_archives.sort(key=lambda row: row["archive_id"])
    return {
        "schema_version": _SCHEMA_VERSION,
        "candidate_only": True,
        "recipe_count": len(recipes),
        "recipes": recipes,
        "failed_archives": failed_archives,
    }
