"""Credential-shape leak scan — A2 §13 (core) / §55.4 / rulebook §17.5.

Runs before any receipt, blocker, log, or report bytes are written by `bh`. A
hit ABORTS the write (raises KeyLeak) — this makes "never print key values"
mechanical rather than something to remember.

Design constraint: receipts are full of legitimate sha256 hashes (32/64 hex),
so there is deliberately NO bare-hex rule — that would false-positive on every
receipt. The scan is two precise layers:

  1. Value layer  — the strongest and most precise: the literal resolved value
     of any known project credential appearing verbatim in the content. This
     cannot false-positive on hashes and directly prevents a real key leaking.
  2. Shape layer  — a small set of high-precision provider token shapes
     (AWS, GitHub, Slack, Google, JWT, PEM private keys, explicit secret
     assignments) that are unambiguous and do not collide with hashes.
"""

from __future__ import annotations

import re

# Known project credential env names (from the publisher adapters' auth_env).
KNOWN_CREDENTIAL_NAMES = (
    "FRED_API_KEY",
    "BLS_API_KEY",
    "BEA_API_KEY",
    "CENSUS_API_KEY",
    "EIA_API_KEY",
    "FRASER_API_KEY",
)

_PLACEHOLDER = re.compile(r"(?i)(redacted|example|placeholder|your[_-]?key|xxxx|<[^>]+>)")

_SHAPES = [
    ("aws_access_key_id", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\b")),
    ("pem_private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----")),
    (
        "secret_assignment",
        re.compile(
            r"(?i)\b(api[_-]?key|registrationkey|secret|password|passwd|access[_-]?token|userid)\b"
            r"\s*[:=]\s*['\"]?([A-Za-z0-9/\+_\-]{20,})"
        ),
    ),
]


class KeyLeak(RuntimeError):
    """Content matched a credential shape; the write was aborted (A2 §13)."""


def scan(content: str, extra_values: tuple[str, ...] = ()) -> list[str]:
    """Return a list of reason strings (empty == clean). Never echoes the match."""
    reasons: list[str] = []
    if not content:
        return reasons

    # 1. Value layer — resolve known credentials in-memory and check verbatim
    #    presence. Values are never stored or echoed; only the name is reported.
    try:
        from tools.rmv2_data_cloudflare.rmv2_connectors import engine

        resolver = engine._read_credential
    except Exception:
        resolver = None
    values: list[tuple[str, str]] = []
    if resolver is not None:
        for name in KNOWN_CREDENTIAL_NAMES:
            try:
                val = resolver(name)
            except Exception:
                val = ""
            if val and len(val) >= 8:
                values.append((name, val))
    for val in extra_values:
        if val and len(val) >= 8:
            values.append(("supplied", val))
    for name, val in values:
        if val in content:
            reasons.append(f"credential value present (name={name})")

    # 2. Shape layer — precise provider token shapes; skip obvious placeholders.
    for label, pattern in _SHAPES:
        for match in pattern.finditer(content):
            fragment = match.group(0)
            if _PLACEHOLDER.search(fragment):
                continue
            reasons.append(f"credential shape matched ({label})")
            break

    return reasons


def assert_clean(content: str, where: str = "content", extra_values: tuple[str, ...] = ()) -> None:
    """Raise KeyLeak if the content matches a credential shape (A2 §13)."""
    reasons = scan(content, extra_values=extra_values)
    if reasons:
        raise KeyLeak(f"key-leak scan aborted write to {where}: {'; '.join(sorted(set(reasons)))}")
