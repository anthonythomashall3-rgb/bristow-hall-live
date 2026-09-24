"""bh quiesce / bh restore — freeze and thaw the resident agents (B-SAFE-1 §4.1).

Deterministic and byte-derived (no AI, no network, no store mutation), so it is
legal for an unattended runbook under §1.1a.

quiesce RECORDS the measured prior launchd state of every AGENT_LABELS agent
BEFORE touching anything, writes it to a state file, then boots the agents out
in an order that cannot self-revive: watchdog first (so it cannot restart the
others), live-data last.

restore reads that state file and brings each agent back to its MEASURED prior
state — live-data first, watchdog last. It REFUSES when the state file is
missing rather than guessing, and on any start failure it leaves things down,
raises, and exits non-zero WITHOUT a retry loop (§1.7).
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from . import paths
from live_data.rmv2_admission.runner import AGENT_LABELS

LIVE_DATA, WATCHDOG, AUTOPILOT = AGENT_LABELS  # (live-data, watchdog, data-autopilot)

# watchdog first so it cannot revive the others; live-data (scheduler) last.
QUIESCE_ORDER = (WATCHDOG, AUTOPILOT, LIVE_DATA)
# live-data first (the service the others depend on); watchdog last.
RESTORE_ORDER = (LIVE_DATA, AUTOPILOT, WATCHDOG)

STATE_REL = Path("live_data") / "runtime" / "bh_quiesce_state.v1.json"

# §18.4 — reuse the existing 120s bootout subprocess budget as the poll deadline
# (do not invent a new timeout). `launchctl bootout` returns while a SIGTERM'd
# service is still tearing down (measured B-SAFE-1 race: same pid lingers <0.5s),
# so measuring survivors immediately is a false positive. Poll each label until
# launchctl no longer lists it, bounded by this budget; fail closed at deadline.
BOOTOUT_BUDGET_S = 120
POLL_INTERVAL_S = 0.5


STATE_SCHEMA = "bh.quiesce_state.v2"


class QuiesceError(RuntimeError):
    """An agent survived bootout — the store is not safely frozen."""


class RestoreError(RuntimeError):
    """Restore could not reach the measured prior state (left down, no retry)."""


@dataclass(frozen=True)
class QuiesceState:
    """Typed on-disk quiesce token (B-ARCH-1).

    `prior` is the MEASURED launchd state of every agent at the moment the FIRST
    (outermost) caller acquired the freeze — it is written exactly once and never
    overwritten by a nested acquire, so a nested caller measuring agents already
    down can never clobber the true all-up prior. `depth` is the nesting count:
    the outermost acquire sets it to 1, each nested acquire increments it, each
    restore decrements it, and only the release from depth 1 -> 0 actually thaws
    the agents. Legacy v1 files (no `depth`) load as depth 1.
    """

    prior: dict
    depth: int

    @classmethod
    def load(cls, path: Path) -> "QuiesceState | None":
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return cls(prior=payload["prior"], depth=int(payload.get("depth", 1)))

    def dump(self, path: Path) -> None:
        # tmp+fsync+replace, like every other writer in this package
        # (receipts.py, promotion.py, blockers.py, install.py, nightly.py).
        # A plain write_text can be interrupted mid-write by a SIGKILL (launchd
        # job limit, reboot, power loss) and leave truncated JSON. This is the
        # ONE file the thaw path depends on: load() then raises
        # json.JSONDecodeError, which is not RestoreError, so neither
        # `bh restore` nor QueueOps.quiesce catches it — the launchd agents stay
        # booted out and BOTH commands stay broken until a human hand-deletes
        # the file. That is exactly the crash-mid-bootout case this class claims
        # to survive.
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"schema": STATE_SCHEMA, "prior": self.prior, "depth": self.depth}
        tmp = path.with_name(path.name + ".tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, indent=2, sort_keys=True))
            fh.flush()
            os.fsync(fh.fileno())
        tmp.replace(path)


def state_path(repo=None) -> Path:
    root = paths.resolve_repo(str(repo) if repo else None)
    return root / STATE_REL


class LaunchctlOps:
    """Real launchd-driving operations. Injected so quiesce/restore stay testable."""

    def __init__(self, repo):
        self.repo = Path(repo)
        self.domain = "gui/%d" % os.getuid()

    def now(self) -> float:
        return time.monotonic()

    def sleep(self, seconds) -> None:
        time.sleep(seconds)

    def measure(self, label) -> dict:
        result = subprocess.run(
            ["/bin/launchctl", "list", label],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30,
        )
        if result.returncode != 0:
            return {"loaded": False, "pid": None, "last_exit": None}
        pid = last = None
        for line in result.stdout.splitlines():
            stripped = line.strip()
            if stripped.startswith('"PID"'):
                pid = int(stripped.split("=")[1].strip().rstrip(";"))
            elif stripped.startswith('"LastExitStatus"'):
                last = int(stripped.split("=")[1].strip().rstrip(";"))
        return {"loaded": True, "pid": pid, "last_exit": last}

    def bootout(self, label) -> None:
        subprocess.run(
            ["/bin/launchctl", "bootout", "%s/%s" % (self.domain, label)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120,
        )

    def start(self, label) -> None:
        scripts = self.repo / "live_data" / "scripts"
        if label == LIVE_DATA:
            subprocess.run(["/bin/bash", str(scripts / "install_launchd.sh")], check=False, timeout=600)
        elif label == WATCHDOG:
            subprocess.run(["/bin/bash", str(scripts / "install_watchdog.sh")], check=False, timeout=300)
        elif label == AUTOPILOT:
            plist = self.repo / "live_data" / "launchd" / ("%s.plist" % label)
            if plist.exists():
                subprocess.run(["/bin/launchctl", "bootstrap", self.domain, str(plist)], check=False, timeout=120)
                subprocess.run(["/bin/launchctl", "kickstart", "%s/%s" % (self.domain, label)], check=False, timeout=120)


def _bootout_until_gone(ops, label) -> bool:
    """Bootout `label`, then poll launchctl until it no longer lists the label,
    bounded by BOOTOUT_BUDGET_S (§18.4). If the label is still loaded (or
    reappears — e.g. a racing watchdog kickstart / KeepAlive edge), bootout
    again, but never past the deadline (§1.7, no unbounded retry). Fail closed:
    return True only once measured gone; False if still loaded at the deadline."""
    deadline = ops.now() + BOOTOUT_BUDGET_S
    ops.bootout(label)
    while True:
        if not ops.measure(label).get("loaded"):
            return True
        if ops.now() >= deadline:
            return False
        ops.sleep(POLL_INTERVAL_S)
        ops.bootout(label)  # still loaded / reappeared — bootout again, bounded by deadline


def quiesce(ops, path) -> dict:
    """Acquire the freeze, idempotently and nesting-safe (B-ARCH-1).

    Outermost acquire (no state token): MEASURE the true prior of every agent,
    write it with depth 1, then bootout. Nested acquire (token already present):
    PRESERVE the recorded prior — never re-measure into it, so a caller that
    finds the agents already down cannot clobber the true all-up prior — and
    bump the depth. Either way the token is written BEFORE any bootout (so a
    crash mid-bootout still leaves a restorable record) and every agent is booted
    out and proven gone: idempotent acquire re-proves the hold and fails closed
    if an agent revived. Raises if any agent is still loaded at the deadline.
    """
    existing = QuiesceState.load(path)
    if existing is None:
        prior = {label: ops.measure(label) for label in AGENT_LABELS}
        state = QuiesceState(prior=prior, depth=1)
        nested = False
    else:
        prior = existing.prior  # preserve the outermost measured prior verbatim
        state = QuiesceState(prior=prior, depth=existing.depth + 1)
        nested = True
    state.dump(path)

    booted_out = []
    for label in QUIESCE_ORDER:
        _bootout_until_gone(ops, label)
        booted_out.append(label)

    survivors = [label for label in AGENT_LABELS if ops.measure(label).get("loaded")]
    if survivors:
        raise QuiesceError("agents still up after bootout: %s" % ", ".join(sorted(survivors)))
    return {"prior": prior, "booted_out": booted_out, "state_file": str(path),
            "depth": state.depth, "nested": nested}


def restore(ops, path) -> dict:
    """Release one level of the freeze (B-ARCH-1).

    Refuse if the token is missing (never guess a prior). A nested release
    (depth > 1) only decrements the count and returns `released=False`: it starts
    NOTHING, because an outer caller still holds the freeze — the inner queue run
    must not thaw what the operator manually froze. The outermost release
    (depth == 1) brings agents back to their MEASURED prior in RESTORE_ORDER;
    on success it clears the token so no stale file can spoof a nested acquire,
    and on any start failure it leaves things down, keeps the token for a retry,
    and raises without a retry loop (§1.7).
    """
    state = QuiesceState.load(path)
    if state is None:
        raise RestoreError(
            "quiesce state file missing (%s) — refusing to guess prior state" % path
        )
    if state.depth > 1:
        QuiesceState(prior=state.prior, depth=state.depth - 1).dump(path)
        return {"started": [], "final": None, "released": False, "depth": state.depth - 1}

    prior = state.prior
    started = []
    for label in RESTORE_ORDER:
        if prior.get(label, {}).get("loaded"):
            ops.start(label)  # exactly one attempt per label — never a retry loop
            started.append(label)

    final = {label: ops.measure(label) for label in AGENT_LABELS}
    failures = [
        label for label in RESTORE_ORDER
        if prior.get(label, {}).get("loaded") and not final[label]["loaded"]
    ]
    if failures:
        raise RestoreError(
            "restore failed for %s (left down, no retry); measured=%s"
            % (", ".join(failures), json.dumps(final, sort_keys=True))
        )
    path.unlink()  # released to depth 0 — clear the token
    return {"started": started, "final": final, "released": True, "depth": 0}


def cli(args) -> int:
    repo = paths.resolve_repo()
    ops = LaunchctlOps(repo)
    path = state_path(repo)
    action = args.quiesce_action
    if action == "quiesce":
        result = quiesce(ops, path)
        kind = "nested acquire (prior preserved)" if result["nested"] else "outermost acquire"
        print("bh quiesce — %s, depth=%d" % (kind, result["depth"]))
        print("bh quiesce — booted out (order): %s" % " -> ".join(result["booted_out"]))
        print("prior state recorded: %s" % path)
        for label in AGENT_LABELS:
            p = result["prior"][label]
            print("  %s  loaded=%s pid=%s last_exit=%s" % (label, p["loaded"], p["pid"], p["last_exit"]))
        return 0
    if action == "restore":
        try:
            result = restore(ops, path)
        except RestoreError as exc:
            print("bh restore FAILED: %s" % exc)
            return 1
        if not result["released"]:
            print("bh restore — nested release, depth=%d (outer caller still holds "
                  "the freeze; agents left down)" % result["depth"])
            return 0
        print("bh restore — released (depth 0), started (order): %s" % " -> ".join(result["started"]))
        for label in AGENT_LABELS:
            f = result["final"][label]
            print("  %s  loaded=%s pid=%s last_exit=%s" % (label, f["loaded"], f["pid"], f["last_exit"]))
        return 0
    print("unknown quiesce action: %s" % action)
    return 2
