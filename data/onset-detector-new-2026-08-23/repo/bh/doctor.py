"""`bh doctor` — is everything fine? one verdict — A2 §20.

Runs the fast mechanical assertions and prints OK or the specific failing
assertion. No interpretation required; this replaces the recurring "is
everything fine?" round trip. The heavy vault `--full` oracle is deliberately
NOT here (it belongs to the verify runbook / preflight, A2 §16) so the verdict
stays instant.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

from . import creds, gitstate, nightly, paths, receipts, sanctions, writer_lock


def _check_resolution() -> tuple[str, bool, str]:
    try:
        repo = paths.resolve_repo()
        interp = paths.resolve_interpreter()
        return ("resolution", True, f"repo={repo} interpreter={interp}")
    except paths.ResolutionError as exc:
        return ("resolution", False, str(exc))


def _check_params() -> tuple[str, bool, str]:
    from . import params

    g = params.guard()
    counts = params.provenance_counts(params.load_registry())
    if g["unregistered"]:
        return ("param_guard", False, f"{len(g['unregistered'])} undeclared magic number(s): {g['unregistered'][:5]}")
    if g["value_drift"]:
        return ("param_guard", False, f"{len(g['value_drift'])} constant(s) drifted from registry: {g['value_drift'][:5]}")
    if g["duplicates"]:
        return ("param_guard", False, f"{len(g['duplicates'])} duplicate controls without alias_of")
    if g.get("new_retired_citations"):
        return ("param_guard", False,
                f"{len(g['new_retired_citations'])} NEW citation(s) of retired parameter(s): "
                f"{g['new_retired_citations'][:5]}")
    # inherited -> 0 by RETIREMENT (owner ruling EFFN_ONLY), not by measurement.
    return ("param_guard", True,
            f"0 undeclared; inherited={counts['inherited']} (retired={counts['retired']} "
            f"by ruling not measurement; inherited defect count →0)")


def _check_lock() -> tuple[str, bool, str]:
    st = writer_lock.status()
    if st["stale"]:
        return ("writer_lock", False, f"lock stale (age {st['age_seconds']:.0f}s > {st['stale_horizon_seconds']}s) — file a blocker, never auto-break")
    return ("writer_lock", True, "held" if st["held"] else "free")


def _check_blockers() -> tuple[str, bool, str]:
    from . import blockers

    open_blockers = blockers.list_blockers()
    # Open blockers are informational, not a doctor failure by themselves.
    return ("blockers", True, f"{len(open_blockers)} open")


def _check_receipt_chain() -> tuple[str, bool, str]:
    name = receipts.latest_receipt_name()
    return ("last_receipt", True, name)


def _check_authority_tree() -> tuple[str, bool, str]:
    # B-HOUSE-3 Defect 3: uncommitted authority change == the tree the nightly
    # would publish is not the committed one. Fail loudly and name the paths.
    try:
        repo = paths.resolve_repo()
    except paths.ResolutionError as exc:
        return ("authority_tree", False, f"cannot resolve repo: {exc}")
    try:
        dirty = gitstate.authority_dirty(repo)
    except gitstate.GitStateUnknown as exc:
        # A broken git used to read as "clean" here and in the nightly gate.
        return ("authority_tree", False, f"cleanliness UNKNOWN — {exc}")
    if dirty:
        shown = ", ".join(dirty[:5])
        more = f" (+{len(dirty) - 5} more)" if len(dirty) > 5 else ""
        return ("authority_tree", False,
                f"{len(dirty)} uncommitted authority path(s) — director must commit or revert: {shown}{more}")
    return ("authority_tree", True, "clean (no uncommitted authority changes)")


def _check_sanctions() -> tuple[str, bool, str]:
    # B-SAFE-2: a sanction token past its expiry (or malformed) is a FAILURE, not
    # a warning — a live override that outlived its batch is exactly the leak the
    # fail-closed control exists to prevent. Tokens are deleted at batch close.
    try:
        repo = paths.resolve_repo()
    except paths.ResolutionError as exc:
        return ("sanctions", False, f"cannot resolve repo: {exc}")
    stale = sanctions.stale_tokens(repo)
    if stale:
        shown = ", ".join(f"{Path(p).name}({reason})" for p, reason in stale[:5])
        more = f" (+{len(stale) - 5} more)" if len(stale) > 5 else ""
        return ("sanctions", False,
                f"{len(stale)} stale/invalid sanction token(s) — director must delete: {shown}{more}")
    return ("sanctions", True, "no stale sanction tokens")


def _age_hours(stamp: str | None) -> float | None:
    # nightly stamps are `_now()` -> "%Y-%m-%dT%H:%M:%SZ" (UTC).
    if not stamp:
        return None
    try:
        t = datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    return (datetime.now(timezone.utc) - t).total_seconds() / 3600.0


def _check_nightly() -> tuple[str, bool, str]:
    # B-AUTO-2: nothing surfaced that the loaded nightly was firing daily and
    # dying at step 1 — it took a manual `launchctl print`. Doctor now FAILs when
    # the last nightly run failed, or when no SUCCESSFUL run exists within the
    # expected interval (a monitor that looks installed but never completes is
    # worse than none).
    try:
        repo = paths.resolve_repo()
    except paths.ResolutionError as exc:
        return ("nightly", False, f"cannot resolve repo: {exc}")
    status = nightly.read_status(repo)
    if status is None:
        return ("nightly", False,
                "no nightly run recorded (status file absent — nightly has never "
                "completed a tracked run)")
    run_at = status.get("run_at")
    last_success = status.get("last_success_at")
    if not status.get("ok"):
        return ("nightly", False,
                f"last nightly run FAILED at step {status.get('failed')} "
                f"(steps={status.get('failed_steps')}, at {run_at}); "
                f"last success {last_success or 'NEVER'}")
    age = _age_hours(last_success)
    if age is None or age > nightly.NIGHTLY_MAX_AGE_H:
        return ("nightly", False,
                f"no successful nightly within {nightly.NIGHTLY_MAX_AGE_H}h "
                f"(last success {last_success or 'NEVER'})")
    return ("nightly", True,
            f"last run ok @ {run_at}; last success {age:.1f}h ago")


def _check_credentials() -> tuple[str, bool, str]:
    report = creds.resolve_report()
    missing = [r["name"] for r in report if not r["resolved"]]
    # A2 §55.5 — missing credential is a warning, not a failure.
    detail = "all resolved" if not missing else f"WARNING missing: {', '.join(missing)}"
    return ("credentials", True, detail)


def run() -> tuple[bool, list]:
    checks = [
        _check_resolution(),
        _check_params(),
        _check_lock(),
        _check_blockers(),
        _check_receipt_chain(),
        _check_authority_tree(),
        _check_sanctions(),
        _check_nightly(),
        _check_credentials(),
    ]
    ok = all(passed for _, passed, _ in checks)
    return ok, checks


def cli(args) -> int:
    if getattr(args, "fix_install", False):
        from . import install as installer

        report = installer.install()
        print(f"reinstalled shim: {report['shim']} (data untouched)")
    ok, checks = run()
    for name, passed, detail in checks:
        mark = "ok " if passed else "FAIL"
        print(f"[{mark}] {name}: {detail}")
    if ok:
        print("\nbh doctor: OK")
        return 0
    failing = [name for name, passed, _ in checks if not passed]
    print(f"\nbh doctor: NOT OK ({', '.join(failing)})")
    return 1
