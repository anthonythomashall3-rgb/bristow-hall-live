#!/usr/bin/env python3
"""PreToolUse guard — refuse edits to frozen artifacts (B-SAFE-1 §4.4).

Registered on Edit|Write|NotebookEdit. Reads the tool-call JSON on stdin,
resolves the target file, and BLOCKS (exit 2, reason on stderr) when the target
is a frozen artifact. Protection is by PATH (and, for growth floors, by numeric
value) — never a line number, so a pin that moves when its file is edited stays
protected instead of silently slipping out of a line range.

Protected:
  * model_authority/target_ledger/**            frozen onset target ledger (pin)
  * method_source/index_v1.py                   frozen index construction (pin)
  * method_source/nowcast_live.py               frozen nowcast coefficients §57.4 (pin)
  * method_source/forecaster_site.py            frozen registered AUC §57.3 (pin)
  * model_authority/parameters/parameter_registry.v1.json   the parameter ledger
  * live_data/config/source_registry_growth_floors.v1.json  — only edits that
        LOWER a floor are blocked; raising a floor is allowed.

The four science pins are {index_v1.py, nowcast_live.py, forecaster_site.py,
target_ledger/**}, matching the parameter registry's frozen entries. Fails
CLOSED: for a protected target the hook blocks whenever it cannot positively
prove the edit is safe.
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

SANCTIONS_DIR = "model_authority/sanctions"

FROZEN_FILES = (
    "method_source/index_v1.py",
    "method_source/nowcast_live.py",
    "method_source/forecaster_site.py",
    "model_authority/parameters/parameter_registry.v1.json",
)
FROZEN_DIRS = ("model_authority/target_ledger/",)
GROWTH_FLOORS = "live_data/config/source_registry_growth_floors.v1.json"

_KEY_NUM = re.compile(r'"([A-Za-z0-9_./-]+)"\s*:\s*(-?\d+(?:\.\d+)?)')


def _repo_root():
    return Path(__file__).resolve().parents[2]


def _repo_rel(file_path):
    """Best-effort repo-relative posix path for matching."""
    root = _repo_root()
    p = Path(file_path)
    try:
        return p.resolve().relative_to(root).as_posix()
    except Exception:
        text = p.as_posix()
        rootstr = root.as_posix()
        if text.startswith(rootstr + "/"):
            return text[len(rootstr) + 1:]
        return text.lstrip("./")


def _block(reason):
    sys.stderr.write("BLOCKED by deny_frozen (B-SAFE-1 §4.4): " + reason + "\n")
    sys.exit(2)


def _token_grants(rel):
    """B-SAFE-2: True iff a valid, matching, unexpired sanction token unlocks
    ``rel``. A token lives at model_authority/sanctions/UNFREEZE.<batch_id>.json
    and must name the exact file, a batch id, and a future expiry. Fails CLOSED:
    a token that cannot be positively verified never unlocks."""
    d = _repo_root() / SANCTIONS_DIR
    if not d.is_dir():
        return False
    now = datetime.now(timezone.utc)
    for p in sorted(d.glob("UNFREEZE.*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue  # malformed token never unlocks
        if not isinstance(data, dict):
            continue
        if not all(k in data for k in ("batch_id", "file_path", "expiry")):
            continue
        if data.get("file_path") != rel:
            continue  # per-file: a token for another file does not unlock this one
        try:
            expiry = datetime.strptime(data["expiry"], "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        except Exception:
            continue  # unparseable expiry never unlocks
        if now <= expiry:
            return True
    return False


def _sanctioned(rel):
    """Honor a valid token: log the exception loudly on stderr, allow the edit."""
    if _token_grants(rel):
        sys.stderr.write(
            "deny_frozen (B-SAFE-2): SANCTIONED edit to %s under a valid sanction token.\n" % rel)
        sys.exit(0)


def _lowers_a_floor(old_string, new_string):
    """True if the edit removes a floor key or decreases any floor value. Fails
    CLOSED: if the old snippet carries no parseable "key": number anchor at all,
    the edit cannot be proven a raise, so it is treated as unsafe."""
    old_pairs = {k: float(v) for k, v in _KEY_NUM.findall(old_string or "")}
    new_pairs = {k: float(v) for k, v in _KEY_NUM.findall(new_string or "")}
    if not old_pairs:
        # anchor matched zero — cannot verify a raise; fail closed.
        return True
    for key, old_val in old_pairs.items():
        if key not in new_pairs:
            return True  # floor key removed = coverage lowered
        if new_pairs[key] < old_val:
            return True  # value lowered
    return False


def main():
    try:
        event = json.loads(sys.stdin.read() or "{}")
    except Exception:
        sys.exit(0)  # unparseable / not our concern — do not interfere
    if event.get("tool_name") not in ("Edit", "Write", "NotebookEdit"):
        sys.exit(0)
    tool_input = event.get("tool_input") or {}
    file_path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    if not file_path:
        sys.exit(0)

    rel = _repo_rel(file_path)

    # B-SAFE-2: creating/modifying a sanction token is loud but permitted — only
    # the director may author tokens; this notice makes any authorship visible.
    name = Path(rel).name
    if rel.startswith(SANCTIONS_DIR + "/") and name.startswith("UNFREEZE.") and name.endswith(".json"):
        sys.stderr.write(
            "deny_frozen (B-SAFE-2): NOTICE — sanction token %s created/modified. "
            "Tokens must be authored ONLY by the director; a batch unlocking itself defeats the control.\n" % rel)
        sys.exit(0)

    if rel in FROZEN_FILES:
        _sanctioned(rel)
        _block("%s is a frozen science pin; edits are not permitted (no valid sanction token)." % rel)
    for frozen_dir in FROZEN_DIRS:
        if rel == frozen_dir.rstrip("/") or rel.startswith(frozen_dir):
            _sanctioned(rel)
            _block("%s is under the frozen %s ledger; edits are not permitted (no valid sanction token)." % (rel, frozen_dir))
    if rel.endswith("source_registry_growth_floors.v1.json"):
        if event.get("tool_name") != "Edit":
            _block("growth floors may only be RAISED via a reviewed Edit; a full Write cannot be proven a raise.")
        if _lowers_a_floor(tool_input.get("old_string", ""), tool_input.get("new_string", "")):
            _block("edit LOWERS a growth floor (or cannot be proven a raise); only raises are allowed.")

    sys.exit(0)


if __name__ == "__main__":
    main()
