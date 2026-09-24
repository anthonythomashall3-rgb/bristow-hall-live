"""Deterministic link discovery for official static archive pages."""
from __future__ import annotations

import dataclasses
import re
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional, Sequence


@dataclasses.dataclass(frozen=True)
class ArchiveRecipe:
    archive_id: str
    page_url: str
    allowed_hosts: Sequence[str]
    allowed_suffixes: Sequence[str]
    include_pattern: str = ""
    timeout_seconds: float = 30.0
    max_bytes: int = 5 * 1024 * 1024


class _Links(HTMLParser):
    def __init__(self) -> None:
        HTMLParser.__init__(self)
        self.hrefs: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[Any]) -> None:
        if tag.lower() != "a":
            return
        for key, value in attrs:
            if key.lower() == "href" and value:
                self.hrefs.append(str(value))


def discover_archive(recipe: ArchiveRecipe, opener: Optional[Any] = None) -> Dict[str, Any]:
    parsed = urllib.parse.urlparse(recipe.page_url)
    allowed = {value.lower() for value in recipe.allowed_hosts}
    if not parsed.hostname or parsed.hostname.lower() not in allowed:
        raise ValueError("page host is not in allowlist")
    opener = opener or urllib.request.urlopen
    result: Dict[str, Any] = {"archive_id": recipe.archive_id, "page_url": recipe.page_url, "status": "FAILED", "links": [], "error": ""}
    try:
        request = urllib.request.Request(recipe.page_url, headers={"User-Agent": "RecessionMonitorV2/1.0"})
        with opener(request, timeout=recipe.timeout_seconds) as response:
            content_type = (response.headers.get("Content-Type") or "").lower()
            data = response.read(recipe.max_bytes + 1)
        if len(data) > recipe.max_bytes:
            raise ValueError("archive page exceeds max_bytes")
        if "html" not in content_type and not data.lstrip().lower().startswith((b"<!doctype html", b"<html")):
            raise ValueError("archive response is not HTML")
        parser = _Links(); parser.feed(data.decode("utf-8", errors="replace"))
        pattern = re.compile(recipe.include_pattern) if recipe.include_pattern else None
        suffixes = tuple(value.lower() for value in recipe.allowed_suffixes)
        links = set()
        for href in parser.hrefs:
            absolute = urllib.parse.urljoin(recipe.page_url, href)
            target = urllib.parse.urlparse(absolute)
            if not target.hostname or target.hostname.lower() not in allowed:
                continue
            if suffixes and not target.path.lower().endswith(suffixes):
                continue
            if pattern and not pattern.search(target.path):
                continue
            links.add(absolute)
        result.update({"status": "SUCCESS", "links": sorted(links)})
    except Exception as exc:
        result["error"] = "%s: %s" % (type(exc).__name__, exc)
    return result


def archive_recipe_from_mapping(value: Dict[str, Any]) -> ArchiveRecipe:
    return ArchiveRecipe(
        archive_id=str(value["archive_id"]), page_url=str(value["page_url"]),
        allowed_hosts=list(value.get("allowed_hosts") or []), allowed_suffixes=list(value.get("allowed_suffixes") or []),
        include_pattern=str(value.get("include_pattern") or ""), timeout_seconds=float(value.get("timeout_seconds", 30)),
        max_bytes=int(value.get("max_bytes", 5 * 1024 * 1024)),
    )
