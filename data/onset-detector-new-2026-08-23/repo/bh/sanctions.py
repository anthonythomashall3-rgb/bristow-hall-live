"""Sanction-token model for the deny_frozen override (B-SAFE-2).

A sanction token temporarily unlocks exactly ONE frozen file for exactly ONE
batch. Only the director creates tokens; the deny_frozen PreToolUse hook honors
a valid, matching, unexpired token and blocks otherwise (fail-closed). Tokens
live at ``model_authority/sanctions/UNFREEZE.<batch_id>.json`` and are deleted
at batch close. A token past its expiry — or malformed — is a ``bh doctor``
FAILURE, never a warning.

Token schema (all fields required):

    {"batch_id": "...", "file_path": "<repo-relative posix>", "expiry": "YYYYMMDDThhmmssZ"}

This module carries the doctor-side stale check. The hook re-implements the same
validation inline in stdlib (it must stay importless / self-contained), so the
token schema and stamp format below are the single contract both sides honor.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

SANCTIONS_DIR = "model_authority/sanctions"
TOKEN_GLOB = "UNFREEZE.*.json"
_STAMP_FMT = "%Y%m%dT%H%M%SZ"
_REQUIRED = ("batch_id", "file_path", "expiry")


def parse_expiry(value: str) -> datetime:
    """Parse a ``YYYYMMDDThhmmssZ`` expiry to an aware UTC datetime. Raises ValueError."""
    return datetime.strptime(value, _STAMP_FMT).replace(tzinfo=timezone.utc)


def load_token(path) -> dict | None:
    """Parse a token file. Returns the dict, or None if unreadable / malformed /
    missing a required field. Fails closed: a token that cannot be positively
    verified is treated as absent."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    if not all(k in data for k in _REQUIRED):
        return None
    return data


def token_grants(data: dict | None, rel: str, now: datetime | None = None) -> bool:
    """True iff ``data`` names ``rel`` and is unexpired. Fails closed."""
    if not data:
        return False
    if data.get("file_path") != rel:
        return False
    try:
        expiry = parse_expiry(data["expiry"])
    except Exception:
        return False
    now = now or datetime.now(timezone.utc)
    return now <= expiry


def stale_tokens(repo, now: datetime | None = None) -> list[tuple[str, str]]:
    """Return ``(path, reason)`` for every token that is past its expiry or cannot
    be parsed. An empty list means every present token is well-formed and live."""
    now = now or datetime.now(timezone.utc)
    d = Path(repo) / SANCTIONS_DIR
    stale: list[tuple[str, str]] = []
    if not d.is_dir():
        return stale
    for p in sorted(d.glob(TOKEN_GLOB)):
        data = load_token(p)
        if data is None:
            stale.append((str(p), "MALFORMED"))
            continue
        try:
            expiry = parse_expiry(data["expiry"])
        except Exception:
            stale.append((str(p), "BAD_EXPIRY"))
            continue
        if now > expiry:
            stale.append((str(p), "EXPIRED %s" % data["expiry"]))
    return stale
