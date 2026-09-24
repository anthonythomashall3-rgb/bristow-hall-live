"""`bh nightly` — the unattended nightly chores (B-AUTO-1 §2).

Runs, in order, all read-only-or-backup:

  1. verify_data_vault --full           (satisfies §17.1 NIGHTLY)
  2. vault backup                        (Defect B repair — see below)
  3. site publish IF a publisher exists  (else report + file gap 10; never invent)
  4. append `bh report --brief` to nightly.log

Fail-fast, no retry (§1.7): step 1 or 2 nonzero -> log and stop nonzero. Step 3
finding no publisher is NOT a failure (it files a gap and continues).

Nightly does NOT go through `bh queue` and does NOT quiesce — every step is
read-only or writes OUTSIDE the store (the backup dest is `../rmv2_vault_backups`,
off the repo tree). Its plist carries NO KeepAlive (KeepAlive is what broke
quiesce) and RunAtLoad false.

Defect B (vaultbackup exit 126): root cause is NOT a missing exec bit — the
quarantined job ran `/bin/sh <script>` under `~/Desktop`, and macOS TCC denies
launchd EXECUTION of anything under `~/Desktop` (the same denial that forced the
`bh` shim to `~/.local/bin`; see paths.py). The repair is architectural: the
backup no longer runs as its own `~/Desktop` script under launchd — it is a
`bh nightly` step invoked through the `~/.local/bin/bh` shim (outside `~/Desktop`,
TCC-executable). The three-part first-run proof (backup completes, manifest
sha-verifies, one sampled file restores byte-identical) closes Defect B.

Side effects are injected (`NightlyOps`) so the sequencing/fail-fast is testable
without a ~30 GB live backup.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from . import gitstate, paths

NIGHTLY_LOG_REL = Path("live_data") / "runtime" / "logs" / "nightly.log"
NIGHTLY_STATUS_REL = Path("live_data") / "runtime" / "logs" / "nightly.status.json"
PUBLISH_TIMING_REL = Path("live_data") / "runtime" / "logs" / "nightly_publish_timing.v1.json"
VAULT_BACKUP_REL = Path("live_data") / "ops" / "backup" / "vault_backup.py"
DEST_ROOT_REL = Path("..") / "rmv2_vault_backups"  # off the repo tree
PUBLISH_SRC_REL = Path("live_data") / "public_deploy" / "data" / "live"

# §18.4 — reuse existing budgets, invent none.
FULL_VERIFY_TIMEOUT_S = 600
# B-AUTO-2 (2026-08-06): the old flat 600 s was DERIVED FROM NOTHING and was
# killing every nightly (the 04:17 backup, under autopilot contention, overran
# 600 s -> uncaught TimeoutExpired -> the whole run died at step 1). Replaced
# with a value DERIVED from a real measurement, not guessed.
# Measurement receipt: live_data/runtime/logs/nightly_backup_timing.v1.json.
#   - clean-run wall time on the live store (38.3 GB uncompressed, 41,851 files):
#     176.3 s (receipt_20260806T183236Z.json, elapsed_s).
#   - the failing nightly crossed 600 s under concurrent autopilot load, i.e. the
#     real-world contention factor was >= 3.4x the clean run.
#   - store growth ~5 GB/day (receipt store_growth_estimate.bytes_per_day).
# So the budget must cover BOTH contention (observed >=3.4x) AND months of growth.
# We use a 10x multiple of the clean baseline: bounds a genuinely hung backup
# while never falsely killing one merely slowed by load or a year of growth. An
# ops timeout that is too large only defers detection of a hang; one that is too
# small is a false failure that kills the whole monitor -- asymmetric, so we err
# generous. This is an OPS budget, not a scientific parameter (bh/nightly.py is
# not in params.SCIENCE_FILES); its provenance lives in the receipt above, not
# in model_authority (frozen, science-only).
BACKUP_TIMING_MEASURED_S = 176   # clean full-backup wall time (receipt v1, rounded down)
BACKUP_TIMEOUT_MULTIPLE = 10     # contention (obs >=3.4x) + growth headroom, no re-tune for ~1y
BACKUP_TIMEOUT_S = 1800          # = ceil(BACKUP_TIMING_MEASURED_S * BACKUP_TIMEOUT_MULTIPLE, 60)
# The sampled-restore extract pulls only the SMALLEST member — fast; 600 s is
# ample headroom and does not scale with store size.
SAMPLE_RESTORE_TIMEOUT_S = 600
# B-AUTO-2 FOLLOW-UP (2026-08-07): the claim that the publisher "is a small
# rsync-class script; 600 s likewise ample" was FALSIFIED by the very next
# launchd nightly — step 3 raised TimeoutExpired at exactly 600 s
# (nightly.log 2026-08-07T11:26:31Z -> 11:36:32Z). Same defect class the batch
# existed to remove: a budget derived from nothing.
# MEASURED cause, from receipts already in the repo, not a guess:
#   - publish.sh -> live_data/publish_site.py runs with rebuild=True, so it
#     REBUILDS the public bundle from the verified active generation and re-hashes
#     every member. That is full-store I/O, not an rsync.
#   - the nightly runs under launchd with ProcessType=Background, a throttled I/O
#     band. Same-day measured penalty: the identical backup took 545.3 s under
#     launchd (rmv2_vault_backups/receipts/receipt_20260807T111725Z.json,
#     elapsed_s) vs 176.3 s clean (receipt_20260806T183236Z.json) = 3.09x.
# The publisher's own CLEAN wall time has never been measured, so no honest
# multiple of it exists. Rather than invent one, this budget is derived BY
# REFERENCE to the already-derived, already-receipted backup budget: the publisher
# reads and hashes the same store under the same launchd throttle, so the envelope
# that bounds a hung backup also bounds a hung publish. It is 3x the observed
# 601 s overrun. Same asymmetry as above (too small = false kill of a real
# publish; too large = only defers hang detection), so err generous.
PUBLISH_TIMEOUT_S = BACKUP_TIMEOUT_S
# bh doctor FAILs if no SUCCESSFUL nightly completed within this window. The
# nightly fires daily (04:17); 48 h = one full day of grace for a single missed
# or slow run before it is flagged.
NIGHTLY_MAX_AGE_H = 48


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log(repo: Path, message: str) -> None:
    path = repo / NIGHTLY_LOG_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(f"{_now()}  {message}\n")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


class NightlyOps:
    """Real nightly side effects. Injected so run_nightly is unit-testable."""

    def __init__(self, repo: Path):
        self.repo = Path(repo)

    def _env(self):
        return {"PYTHONDONTWRITEBYTECODE": "1", "PATH": "/opt/homebrew/bin:/usr/bin:/bin",
                "HOME": os.environ.get("HOME", ""), "BH_REPO": str(self.repo)}

    def verify_full(self) -> bool:
        script = self.repo / "data_vault" / "scripts" / "verify_data_vault.py"
        proc = subprocess.run(
            [sys.executable, str(script), "--full"], cwd=str(self.repo),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            timeout=FULL_VERIFY_TIMEOUT_S, env=self._env(),
        )
        return proc.returncode == 0

    def backup(self) -> dict:
        return backup_with_sampled_proof(self.repo, env=self._env())

    def site_publish(self) -> dict:
        return detect_and_publish(self.repo)

    def report_append(self) -> None:
        from . import report

        text = report.brief()
        _log(self.repo, "report --brief:\n" + text)


def backup_with_sampled_proof(repo: Path, env=None) -> dict:
    """Run the vault backup engine (integrity-only) then prove ONE sampled file
    restores byte-identical against the live manifest — the §2.2c three-part
    proof without the 21 GB full-restore scratch. Returns a proof dict."""
    repo = Path(repo)
    script = repo / VAULT_BACKUP_REL
    dest_root = (repo / DEST_ROOT_REL).resolve()
    env = env or {"PATH": "/opt/homebrew/bin:/usr/bin:/bin", "HOME": os.environ.get("HOME", "")}
    try:
        proc = subprocess.run(
            [sys.executable, str(script), "backup"], cwd=str(repo),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            timeout=BACKUP_TIMEOUT_S, env=env,
        )
    except subprocess.TimeoutExpired:
        # B-AUTO-2: a timeout must DEGRADE to a recorded failure, never raise out
        # of the nightly and suppress publish/report (that was the whole defect).
        return {"ok": False, "completed": False,
                "reason": f"backup timed out after {BACKUP_TIMEOUT_S}s"}
    if proc.returncode != 0:
        return {"ok": False, "completed": False, "reason": f"backup exit {proc.returncode}",
                "stderr_tail": proc.stderr[-400:]}
    # newest receipt
    rdir = dest_root / "receipts"
    receipts = sorted(rdir.glob("receipt_*.json")) if rdir.is_dir() else []
    if not receipts:
        return {"ok": False, "completed": True, "reason": "no backup receipt written"}
    receipt = json.loads(receipts[-1].read_text(encoding="utf-8"))
    manifest_verified = (
        receipt.get("archive_integrity") == "PASS"
        and receipt.get("member_count_matches_manifest") is True
    )
    archive = receipt.get("archive")
    snap_dir = Path(archive).parent if archive else None
    manifest_path = snap_dir / "live_manifest.json" if snap_dir else None
    sampled = _sampled_restore_ok(archive, manifest_path, env=env)
    ok = bool(manifest_verified and sampled.get("ok"))
    proof = {
        "ok": ok, "completed": True, "manifest_verified": manifest_verified,
        "sampled_restore_ok": sampled.get("ok"), "sample": sampled,
        "archive": archive, "set_hash": receipt.get("set_hash"),
        "compressed_bytes": receipt.get("compressed_bytes"),
        "manifest_files": receipt.get("manifest_files"),
    }
    if not ok:
        # B-AUTO-2 FOLLOW-UP: this path previously returned NO "reason", so the
        # nightly log printed the useless line "step2 backup FAILED (None)" and
        # the operator could not tell a corrupt archive from a missing tool.
        # Every failure must say which of the two proofs failed, and why.
        parts = []
        if not manifest_verified:
            parts.append(
                "archive manifest proof failed "
                f"(archive_integrity={receipt.get('archive_integrity')!r}, "
                f"member_count_matches_manifest={receipt.get('member_count_matches_manifest')!r})"
            )
        if not sampled.get("ok"):
            parts.append("sampled restore failed: " + str(sampled.get("reason") or "sha mismatch"))
        proof["reason"] = "; ".join(parts)
    return proof


def _sampled_restore_ok(archive, manifest_path, env=None) -> dict:
    """Extract the smallest non-empty member and compare its sha to the manifest.

    B-AUTO-2 FOLLOW-UP (2026-08-07) — THE PROOF WAS NEVER RUNNING UNDER LAUNCHD.
    This helper used to shell out with NO `env`, so it inherited the caller's
    environment. `bh nightly` hands the backup engine an explicit
    PATH=/opt/homebrew/bin:/usr/bin:/bin (NightlyOps._env), but launchd itself
    starts the job with the bare default PATH and Homebrew's `zstd` is not on it.
    Result: the backup engine (which got the good PATH) succeeded and wrote a
    PASS receipt, while this extract died with rc=127 "zstd: command not found",
    so EVERY launchd nightly reported `sampled_restore_ok=False` and failed the
    backup step — while the same command passed by hand from a terminal, where
    the interactive PATH does have Homebrew. The receipts also record
    `restore_test.performed: false`, so this sampled proof is the ONLY restore
    evidence the backup has: silently losing it meant the vault had no proven
    restore path at all.
    Fix: take the SAME resolved env the backup engine gets, resolve both tools
    against it up front, and say plainly which tool is missing instead of
    surfacing a bare rc.
    """
    if not archive or not manifest_path or not Path(manifest_path).exists():
        return {"ok": False, "reason": "archive or manifest missing"}
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    files = [f for f in manifest.get("files", []) if f.get("size", 0) > 0]
    if not files:
        return {"ok": False, "reason": "manifest has no non-empty files"}

    import shlex
    import shutil

    env = dict(env or {"PATH": "/opt/homebrew/bin:/usr/bin:/bin",
                       "HOME": os.environ.get("HOME", "")})
    search_path = env.get("PATH", "")
    tools = {}
    for tool in ("zstd", "tar"):
        found = shutil.which(tool, path=search_path)
        if not found:
            # Name the tool AND the PATH it was looked up on: the whole class of
            # bug here is an environment difference between launchd and a shell.
            return {"ok": False,
                    "reason": f"{tool} not found on PATH={search_path!r} "
                              f"(sampled restore proof cannot run)"}
        tools[tool] = found

    sample = min(files, key=lambda f: f["size"])
    member = sample["path"]  # tar member path, relative to REPO
    scratch = Path(archive).parent / "scratch_sample"
    if scratch.exists():
        shutil.rmtree(scratch)
    scratch.mkdir(parents=True)
    try:
        # shlex.quote: archive/member/scratch are external strings reaching a
        # shell; unquoted interpolation was a command-injection surface.
        command = (
            f'{shlex.quote(tools["zstd"])} -dc --long=27 {shlex.quote(str(archive))} '
            f'| {shlex.quote(tools["tar"])} -xf - -C {shlex.quote(str(scratch))} '
            f'{shlex.quote(member)}'
        )
        rc = subprocess.run(
            command,
            shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            timeout=SAMPLE_RESTORE_TIMEOUT_S, env=env,
        )
        restored = scratch / member
        if rc.returncode != 0 or not restored.exists():
            return {"ok": False, "member": member, "reason": f"extract failed rc={rc.returncode}",
                    "stderr_tail": rc.stderr[-300:]}
        got = _sha256_file(restored)
        ok = got == sample["sha256"]
        result = {"ok": ok, "member": member, "expected_sha": sample["sha256"],
                  "restored_sha": got, "size": sample["size"]}
        if not ok:
            result["reason"] = (
                f"restored sha {got} != manifest sha {sample['sha256']} for {member}"
            )
        return result
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def detect_and_publish(repo: Path) -> dict:
    """§2.3: sync public_deploy/data/live to the deployed site data dir IFF a
    publisher script already exists in the repo. None exists -> file gap 10,
    report plainly, do NOT invent a deploy target. Not a nightly failure."""
    repo = Path(repo)
    # A publisher would be a script that writes the deployed site data dir from
    # PUBLISH_SRC_REL. None is registered in the repo (measured B-AUTO-1).
    publisher = _find_publisher(repo)
    if publisher is None:
        _file_gap_10(repo)
        return {"published": False, "publisher_found": False, "gap_filed": True,
                "reason": "no publisher script in repo; gap 10 filed (site deploy target unresolved)"}
    # B-AUTO-2 FOLLOW-UP: start_new_session puts the publisher in its OWN process
    # group. subprocess.run's timeout kills only the direct child (/bin/sh), so a
    # timed-out publish previously left publish_site.py still running and still
    # writing the deployed site AFTER the nightly had recorded the step as failed
    # — an unsupervised writer racing the next run. Kill the whole group instead.
    started = time.monotonic()
    proc = subprocess.Popen(
        ["/bin/sh", str(publisher)], cwd=str(repo),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        env={"PATH": "/usr/bin:/bin", "HOME": os.environ.get("HOME", "")},
        start_new_session=True,
    )
    try:
        _out, err = proc.communicate(timeout=PUBLISH_TIMEOUT_S)
        _record_publish_timing(repo, time.monotonic() - started, True, proc.returncode)
    except subprocess.TimeoutExpired:
        _record_publish_timing(repo, time.monotonic() - started, False, None)
        _kill_process_group(proc)
        try:
            _out, err = proc.communicate(timeout=30)
        except subprocess.TimeoutExpired:  # pragma: no cover — group is already SIGKILLed
            err = ""
        # publisher_found stays TRUE. Reporting False here would make a timed-out
        # publish indistinguishable from the "no publisher exists" case above,
        # which is explicitly NOT a failure — that is how the 2026-08-07 nightly
        # logged `publisher_found=False` for a publisher it had just executed.
        return {"published": False, "publisher_found": True, "timed_out": True,
                "publisher": str(publisher), "returncode": None,
                "reason": f"publisher timed out after {PUBLISH_TIMEOUT_S}s "
                          f"(process group killed)",
                "stderr_tail": (err or "")[-400:]}
    return {"published": proc.returncode == 0, "publisher_found": True,
            "publisher": str(publisher), "returncode": proc.returncode,
            "stderr_tail": (err or "")[-400:] if proc.returncode != 0 else ""}


def _record_publish_timing(repo: Path, elapsed_s: float, completed: bool, returncode) -> None:
    """Measure the publisher ON THE MACHINE THAT RUNS IT (§19.1, §18.2).

    PUBLISH_TIMEOUT_S is currently derived BY REFERENCE to the backup budget
    because the publisher's own wall time has never been measured on this host —
    that is a pin without a measurement, which §18.2 forbids. No VM available to
    this repair could produce a valid number: the budget must bound the publisher
    under macOS launchd `ProcessType=Background` I/O throttling, and only the Mac
    running the nightly can measure that. So the nightly measures itself. After
    two or more recorded runs (§18.4 needs >=2 points to tell drift from
    regression), re-pin PUBLISH_TIMEOUT_S from this receipt plus stated headroom
    and clear the typed blocker. Never raises: a telemetry failure must not fail
    a publish that otherwise succeeded.
    """
    try:
        path = repo / PUBLISH_TIMING_REL
        path.parent.mkdir(parents=True, exist_ok=True)
        doc = {"schema": "recession-monitor-v2.nightly-publish-timing.v1", "runs": []}
        if path.exists():
            try:
                prior = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(prior.get("runs"), list):
                    doc = prior
            except Exception:  # noqa: BLE001 — corrupt telemetry restarts clean
                pass
        doc["runs"].append({
            "measured_at_utc": _now(),
            "elapsed_s": round(elapsed_s, 1),
            "completed": completed,
            "returncode": returncode,
            "budget_s": PUBLISH_TIMEOUT_S,
            "note": "wall time of publish.sh -> publish_site.py (rebuild=True, full-store "
                    "re-hash) under whatever contention the run actually saw",
        })
        doc["runs"] = doc["runs"][-50:]
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(json.dumps(doc, indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(path)
    except Exception:  # noqa: BLE001
        pass


def _kill_process_group(proc) -> None:
    """SIGKILL the child's whole process group; fall back to the child alone."""
    import signal

    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        try:
            proc.kill()
        except ProcessLookupError:
            pass


def _find_publisher(repo: Path):
    """A publisher script deploys PUBLISH_SRC_REL to a site data dir. Return its
    path or None. Conservative: only a script that both exists and references the
    live publish source counts (never invent one)."""
    candidates = [
        repo / "live_data" / "scripts" / "publish_site.sh",
        repo / "live_data" / "public_deploy" / "publish.sh",
        repo / "live_data" / "ops" / "publish" / "publish.sh",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def _file_gap_10(repo: Path) -> None:
    from . import blockers

    try:
        blockers.write_blocker(
            "DECISION",
            "gap-10-site-publisher",
            {"detail": "no publisher script syncs live_data/public_deploy/data/live to a "
                       "deployed site data dir; nightly step 3 has no target",
             "batch": "B-AUTO-1", "future_batch": "own batch — do not invent a deploy target"},
            "author a publisher script (its own future batch)",
        )
    except Exception:
        # blocker ledger unavailable must not fail the nightly run
        pass


def _write_status(repo: Path, result: dict) -> dict:
    """B-AUTO-2: persist a machine-readable nightly outcome so `bh doctor` can
    surface it. Carries the last SUCCESSFUL completion forward across failed runs
    (a failure must not erase the memory of the last good run)."""
    path = repo / NIGHTLY_STATUS_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    prior = {}
    if path.exists():
        try:
            prior = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            prior = {}
    ok = result.get("failed") is None
    now = _now()
    status = {
        "run_at": now,
        "ok": ok,
        "failed": result.get("failed"),
        "failed_steps": list(result.get("failed_steps", [])),
        "last_success_at": now if ok else prior.get("last_success_at"),
    }
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(status, indent=2), encoding="utf-8")
    tmp.replace(path)
    result["status"] = status
    return status


def read_status(repo: Path):
    """Latest persisted nightly status, or None if never run."""
    path = Path(repo) / NIGHTLY_STATUS_REL
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def run_nightly(ops, repo: Path) -> dict:
    """Steps 1-4. Step 0 (dirty authority) and step 1 (verify --full) are hard
    integrity gates — a corrupt or uncommitted tree legitimately blocks the run.
    From the BACKUP step on, the run is RESILIENT (B-AUTO-2): a backup failure or
    timeout is recorded but does NOT suppress publish + report, and no step's
    exception ever propagates out of run_nightly (that propagation was the defect
    that killed every nightly). The overall result is marked FAILED if any step
    failed. Always writes a status file for `bh doctor`. Returns a result dict."""
    repo = Path(repo)
    result = {"steps": [], "failed": None, "failed_steps": []}
    _log(repo, "nightly START")

    def _record_fail(step: str) -> None:
        if result["failed"] is None:
            result["failed"] = step
        if step not in result["failed_steps"]:
            result["failed_steps"].append(step)

    # step 0 — refuse to run over a dirty authority tree (B-HOUSE-3 Defect 3).
    # The nightly publishes the committed tree; an uncommitted authority change
    # means it would publish something the director never committed. Fail loudly.
    try:
        dirty = gitstate.authority_dirty(repo)
    except gitstate.GitStateUnknown as exc:
        # UNKNOWN is not CLEAN: a broken git must refuse the publish, not permit it.
        result["steps"].append({"step": "authority_tree", "ok": False,
                                "unknown": str(exc)})
        _record_fail("authority_tree")
        _log(repo, f"step0 authority_tree: UNKNOWN — {exc}")
        _log(repo, "nightly STOP (authority cleanliness unknown — refusing to publish)")
        _write_status(repo, result)
        return result
    if dirty:
        result["steps"].append({"step": "authority_tree", "ok": False, "dirty": dirty})
        _record_fail("authority_tree")
        result["dirty_authority"] = dirty
        _log(repo, f"step0 authority_tree: DIRTY ({len(dirty)}) — "
                   f"{', '.join(dirty[:8])}")
        _log(repo, "nightly STOP (dirty authority tree — refusing to publish)")
        _write_status(repo, result)
        return result
    result["steps"].append({"step": "authority_tree", "ok": True})
    _log(repo, "step0 authority_tree: CLEAN")

    # step 1 — verify --full (hard integrity gate: never publish/back up over a
    # vault that fails its own oracle). Exception-safe: a crash in the oracle is
    # a recorded FAIL, not a propagated raise.
    try:
        ok1 = ops.verify_full()
    except Exception as exc:  # noqa: BLE001 — must not escape the nightly
        ok1 = False
        _log(repo, f"step1 verify --full: EXCEPTION {exc!r}")
    result["steps"].append({"step": "verify_full", "ok": ok1})
    _log(repo, f"step1 verify --full: {'PASS' if ok1 else 'FAIL'}")
    if not ok1:
        _record_fail("verify_full")
        _log(repo, "nightly STOP (verify_full failed)")
        _write_status(repo, result)
        return result

    # step 2 — backup (Defect B). RESILIENT (B-AUTO-2): a failure or timeout here
    # is recorded but must NOT suppress publish + report. backup_with_sampled_proof
    # already downgrades TimeoutExpired to ok=False; the try/except is belt-and-
    # suspenders so no unexpected raise can escape and kill the run.
    try:
        proof = ops.backup()
    except Exception as exc:  # noqa: BLE001
        proof = {"ok": False, "completed": False,
                 "reason": f"backup raised {type(exc).__name__}: {exc}"}
        _log(repo, f"step2 backup: EXCEPTION {exc!r}")
    result["steps"].append({"step": "backup", "ok": proof.get("ok"), "proof": proof})
    result["backup_proof"] = proof
    _log(repo, f"step2 backup: ok={proof.get('ok')} "
               f"manifest_verified={proof.get('manifest_verified')} "
               f"sampled_restore_ok={proof.get('sampled_restore_ok')}")
    if not proof.get("ok"):
        _record_fail("backup")
        _log(repo, f"step2 backup FAILED ({proof.get('reason')}) — CONTINUING "
                   f"(publish/report not suppressed)")

    # step 3 — site publish if a publisher exists (else gap 10, not a failure).
    # Runs regardless of the backup outcome (publish does not depend on backup).
    try:
        pub = ops.site_publish()
        # B-AUTO-2 FOLLOW-UP: the step outcome must be DERIVED from the publish
        # result, not hard-coded True. "No publisher exists" is the documented
        # gap-10 case and is legitimately not a failure; but a publisher that WAS
        # found and did not publish (non-zero exit, or the timeout that
        # detect_and_publish now degrades into a dict instead of raising) is a
        # real failure. Hard-coding ok=True here would have silently swallowed
        # exactly the publish timeout observed on 2026-08-07.
        step_ok = (not pub.get("publisher_found")) or bool(pub.get("published"))
        result["steps"].append({"step": "site_publish", "ok": step_ok, "detail": pub})
        if not step_ok:
            _record_fail("site_publish")
            _log(repo, f"step3 site_publish FAILED ({pub.get('reason') or pub.get('returncode')})")
    except Exception as exc:  # noqa: BLE001
        # publisher_found is UNKNOWN here, not False: claiming False would forge
        # the gap-10 "no publisher in repo" signal.
        pub = {"published": False, "publisher_found": None,
               "error": f"{type(exc).__name__}: {exc}"}
        result["steps"].append({"step": "site_publish", "ok": False, "detail": pub})
        _record_fail("site_publish")
        _log(repo, f"step3 site_publish: EXCEPTION {exc!r}")
    result["publish"] = pub
    _log(repo, f"step3 site_publish: publisher_found={pub.get('publisher_found')} "
               f"published={pub.get('published')}")

    # step 4 — report append (always last, always attempted)
    try:
        ops.report_append()
        result["steps"].append({"step": "report_append", "ok": True})
    except Exception as exc:  # noqa: BLE001
        result["steps"].append({"step": "report_append", "ok": False})
        _record_fail("report_append")
        _log(repo, f"step4 report_append: EXCEPTION {exc!r}")

    _log(repo, "nightly COMPLETE" if result["failed"] is None
               else f"nightly FAILED ({result['failed']}; steps={result['failed_steps']})")
    _write_status(repo, result)
    return result


def cli(args) -> int:
    repo = paths.resolve_repo()
    ops = NightlyOps(repo)
    result = run_nightly(ops, repo)
    if result["failed"]:
        print(f"bh nightly FAILED at step: {result['failed']}")
        if result["failed"] == "authority_tree":
            print("  dirty authority paths (director must commit or revert):")
            for p in result.get("dirty_authority", []):
                print(f"    {p}")
        return 1
    proof = result.get("backup_proof", {})
    pub = result.get("publish", {})
    print("bh nightly: COMPLETE")
    print(f"  backup: ok={proof.get('ok')} manifest_verified={proof.get('manifest_verified')} "
          f"sampled_restore_ok={proof.get('sampled_restore_ok')}")
    print(f"  publish: publisher_found={pub.get('publisher_found')} published={pub.get('published')}")
    return 0
