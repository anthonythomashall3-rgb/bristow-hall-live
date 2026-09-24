"""Credential resolution reporting — A2 §55.

This does NOT reimplement resolution. The single source of truth is the chain
RTDSM-1 added to `engine._read_credential` / `engine._credential_source`
(env -> live_data/config/local.env -> macOS keychain). A2 §55 asked to
generalize the *reporting* of that chain to every project credential and to
prove it resolves under launchd.

Owner ruling (2026-08-04): keep `local.env` in the chain — this supersedes the
literal "no .env file" wording of A2 §55.1; RTDSM-1's chain is authoritative.

Only `resolved: true|false` and `via: env|local_env|keychain|none` ever leave
this module. Never a value, never its length, never a prefix (A2 §55.3).
"""

from __future__ import annotations

from .keyleak import KNOWN_CREDENTIAL_NAMES


def _credential_source(name: str) -> str:
    """Delegate to the authoritative engine resolver. 'error' if unimportable."""
    try:
        from tools.rmv2_data_cloudflare.rmv2_connectors import engine
    except Exception:
        return "error"
    try:
        return engine._credential_source(name)
    except Exception:
        return "error"


def resolve_report(names=KNOWN_CREDENTIAL_NAMES) -> list[dict]:
    """Per credential: name, resolved bool, via. No value ever (A2 §55.3)."""
    out = []
    for name in names:
        via = _credential_source(name)
        out.append({"name": name, "resolved": via not in ("none", "error"), "via": via})
    return out


def cli(_args) -> int:
    report = resolve_report()
    for row in report:
        status = "resolved" if row["resolved"] else "missing"
        print(f"{row['name']}: {status} (via {row['via']})")
    missing = [r["name"] for r in report if not r["resolved"]]
    if missing:
        # A2 §55.5 — a missing credential is a warning by name, not a failure.
        print(f"\nwarning: {len(missing)} credential(s) not resolved: {', '.join(missing)}")
    return 0
