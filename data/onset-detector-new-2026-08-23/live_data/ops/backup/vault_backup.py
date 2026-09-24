#!/usr/bin/env python3
"""Recession Monitor V2 -- irreplaceable-set backup engine (batch R1A, section 1).

Backs up the IRREPLACEABLE set only:

  scientific vault (verify_data_vault manifest scope):
    data/            source bytes                         -- irreplaceable
    data_archive/    ALFRED vintages / first-release      -- irreplaceable
    method_source/   preserved method source bytes        -- irreplaceable
  authored contracts / config (small, not regenerable):
    model_authority/       authored contracts             -- irreplaceable
    live_data/config/      source/queue/calendar config   -- irreplaceable
  acquisition store (ALFRED windows have moved -> not re-pullable):
    live_data/store/generations/     poll snapshots        -- irreplaceable
    live_data/store/normalized/      normalized pulls      -- irreplaceable
    live_data/store/objects/         content-addressed raw -- irreplaceable
    live_data/store/attempts/        raw poll attempts     -- irreplaceable
    live_data/store/receipts/        poll receipts/audit   -- irreplaceable
    live_data/store/snapshot_projection/  published proj.  -- kept (cheap; regen needs full pipeline)

EXCLUDED as derived / regenerable (documented, not silently dropped):
    live_data/store/binding_attestation/  F1 attestation cache -- regenerable from blobs in ~145s
                                          (F1 proved round-trip byte-identical); rebuilt post-restore.
    **/__pycache__, *.pyc, .DS_Store      OS/interpreter cruft -- regenerable.

MEDIA GAP (typed blocker OFF_MEDIA): destination is on the SAME physical disk as the store
(only /dev/disk0 present; no external volume). This protects against a bad write or a failed
repair, NOT against disk failure. An off-disk destination is a follow-up batch.

Usage:
  vault_backup.py plan                    # classify + measure, no write
  vault_backup.py backup [--full-restore-test]   # archive + receipt + retention (+ optional full restore compare)
  vault_backup.py manifest ROOT           # emit set manifest for ROOT (debug)
"""
import argparse, hashlib, json, os, shutil, subprocess, sys, time, warnings
from datetime import datetime, timezone

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
DEST_ROOT = os.path.abspath(os.path.join(REPO, "..", "rmv2_vault_backups"))

# irreplaceable roots, relative to REPO
INCLUDE = [
    "data",
    "data_archive",
    "method_source",
    "model_authority",
    "live_data/config",
    "live_data/ops/poll_history",   # durable poll-outcome log (sole copy past receipt window)
    "live_data/store/generations",
    "live_data/store/normalized",
    "live_data/store/objects",
    "live_data/store/attempts",
    "live_data/store/receipts",
    "live_data/store/snapshot_projection",
]
# excluded (derived / regenerable); recorded in the receipt
EXCLUDE_DERIVED = ["live_data/store/binding_attestation"]
EXCLUDE_NAMES = {".DS_Store"}
EXCLUDE_DIRNAMES = {"__pycache__"}
EXCLUDE_SUFFIX = (".pyc",)

RESERVE_BYTES = 20 * 1024**3   # keep >=20 GiB free on the destination disk
ZSTD_LEVEL = "-12"
ZSTD_LONG = "--long=27"        # 128 MiB match window (8 GiB RAM safe); cross-vintage dedup


def utc_stamp():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _skip(rel, name):
    if name in EXCLUDE_NAMES:
        return True
    if name.endswith(EXCLUDE_SUFFIX):
        return True
    parts = rel.split(os.sep)
    return any(p in EXCLUDE_DIRNAMES for p in parts)


def iter_files(root):
    """Yield (relpath_from_REPO, abspath) for every included file under root."""
    base = os.path.join(REPO, root)
    if not os.path.exists(base):
        return
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRNAMES]
        for fn in filenames:
            ab = os.path.join(dirpath, fn)
            rel = os.path.relpath(ab, REPO)
            if _skip(rel, fn):
                continue
            if os.path.islink(ab):
                continue
            yield rel, ab


def sha256_file(path, _buf=1024 * 1024):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(_buf)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def source_of(rel):
    """Per-source key where the path encodes a source_id (attempts/, receipts/)."""
    parts = rel.split(os.sep)
    if len(parts) >= 4 and parts[:3] == ["live_data", "store", "attempts"]:
        return ("attempts", parts[3])
    if len(parts) >= 4 and parts[:3] == ["live_data", "store", "receipts"]:
        return ("receipts", parts[3])
    return None


def group_of(rel):
    parts = rel.split(os.sep)
    if parts[0] in ("data", "data_archive", "method_source", "model_authority"):
        return parts[0]
    if parts[:2] == ["live_data", "config"]:
        return "live_data/config"
    if parts[:2] == ["live_data", "store"] and len(parts) >= 3:
        return "live_data/store/" + parts[2]
    return "other"


def build_manifest(root_prefix=REPO, includes=INCLUDE, progress=False):
    """Content manifest over the irreplaceable set rooted at root_prefix.

    Returns dict with per-file (relpath,size,sha), a single set_hash (record-level),
    total counts/bytes, per-group counts/bytes, and per-source counts."""
    global REPO
    saved = REPO
    REPO = root_prefix
    try:
        files = []
        groups = {}
        per_source = {"attempts": {}, "receipts": {}}
        total_bytes = 0
        n = 0
        for root in includes:
            for rel, ab in iter_files(root):
                sz = os.path.getsize(ab)
                sh = sha256_file(ab)
                files.append((rel, sz, sh))
                total_bytes += sz
                n += 1
                g = group_of(rel)
                gg = groups.setdefault(g, {"files": 0, "bytes": 0})
                gg["files"] += 1
                gg["bytes"] += sz
                src = source_of(rel)
                if src:
                    per_source[src[0]][src[1]] = per_source[src[0]].get(src[1], 0) + 1
                if progress and n % 2000 == 0:
                    print(f"  ... hashed {n} files", file=sys.stderr)
    finally:
        REPO = saved
    files.sort()
    set_h = hashlib.sha256()
    for rel, sz, sh in files:
        set_h.update(rel.encode())
        set_h.update(b"\0")
        set_h.update(sh.encode())
        set_h.update(b"\n")
    return {
        "total_files": len(files),
        "total_bytes": total_bytes,
        "set_hash": set_h.hexdigest(),
        "groups": groups,
        "per_source": per_source,
        "files": files,
    }


def free_bytes(path):
    st = os.statvfs(path)
    return st.f_bavail * st.f_frsize


def same_disk(a, b):
    return os.stat(a).st_dev == os.stat(b).st_dev


def store_growth():
    """Coarse bytes/day for the store from oldest..newest generation mtime."""
    gens = os.path.join(REPO, "live_data/store/generations")
    if not os.path.isdir(gens):
        return None
    mtimes, tot = [], 0
    for rel, ab in iter_files("live_data/store"):
        try:
            mtimes.append(os.path.getmtime(ab))
            tot += os.path.getsize(ab)
        except OSError as exc:
            warnings.warn(
                "store-growth stat failed for %s: %s" % (ab, exc),
                RuntimeWarning,
            )
    if len(mtimes) < 2:
        return None
    span_days = max((max(mtimes) - min(mtimes)) / 86400.0, 0.5)
    return {"store_bytes": tot, "span_days": round(span_days, 2),
            "bytes_per_day": int(tot / span_days)}


def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=2, sort_keys=True)
    os.replace(tmp, path)


def write_blocker(kind, detail, extra=None):
    d = os.path.join(DEST_ROOT, "blockers")
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, f"BLOCKER_{kind}_{utc_stamp()}.json")
    obj = {"kind": kind, "detail": detail, "at_utc": utc_stamp()}
    if extra:
        obj.update(extra)
    write_json(p, obj)
    return p


def cmd_plan():
    m = build_manifest(progress=True)
    growth = store_growth()
    free = free_bytes(DEST_ROOT if os.path.exists(DEST_ROOT) else REPO)
    print(json.dumps({
        "irreplaceable_total_files": m["total_files"],
        "irreplaceable_total_bytes": m["total_bytes"],
        "set_hash": m["set_hash"],
        "groups": m["groups"],
        "per_source_counts": {k: len(v) for k, v in m["per_source"].items()},
        "excluded_derived": EXCLUDE_DERIVED,
        "store_growth": growth,
        "dest_free_bytes": free,
    }, indent=2))


def cmd_manifest(root):
    m = build_manifest(os.path.abspath(root), progress=True)
    m.pop("files", None)
    print(json.dumps(m, indent=2))


def cmd_backup(full_restore_test):
    os.makedirs(DEST_ROOT, exist_ok=True)
    stamp = utc_stamp()
    snap_dir = os.path.join(DEST_ROOT, "snapshots", stamp)
    os.makedirs(snap_dir, exist_ok=True)
    archive = os.path.join(snap_dir, "irreplaceable.tar.zst")
    live_manifest_path = os.path.join(snap_dir, "live_manifest.json")
    receipt_path = os.path.join(DEST_ROOT, "receipts", f"receipt_{stamp}.json")

    t0 = time.time()
    off_media = same_disk(REPO, DEST_ROOT)

    try:
        # 1. live manifest (record-level content hash of the irreplaceable set)
        print("[1/5] building live manifest ...", file=sys.stderr)
        m = build_manifest(progress=True)
        files_only = [{"path": p, "size": s, "sha256": h} for (p, s, h) in m["files"]]
        write_json(live_manifest_path, {
            "stamp": stamp, "set_hash": m["set_hash"],
            "total_files": m["total_files"], "total_bytes": m["total_bytes"],
            "groups": m["groups"], "per_source": m["per_source"],
            "files": files_only,
        })

        # 2. archive: tar the include list, pipe through zstd (repetitive text -> high ratio)
        print("[2/5] creating compressed archive ...", file=sys.stderr)
        include_existing = [r for r in INCLUDE if os.path.exists(os.path.join(REPO, r))]
        exclude_args = []
        for pat in EXCLUDE_DIRNAMES:
            exclude_args += ["--exclude", pat]
        for pat in EXCLUDE_NAMES:
            exclude_args += ["--exclude", pat]
        exclude_args += ["--exclude", "*.pyc"]
        for d in EXCLUDE_DERIVED:
            exclude_args += ["--exclude", d]
        tar = subprocess.Popen(
            ["tar", "-C", REPO, "-cf", "-"] + exclude_args + include_existing,
            stdout=subprocess.PIPE)
        with open(archive, "wb") as out:
            zst = subprocess.Popen(
                ["zstd", ZSTD_LEVEL, ZSTD_LONG, "-T0", "-q", "-"],
                stdin=tar.stdout, stdout=out)
            tar.stdout.close()
            zst.communicate()
        if tar.wait() != 0 or zst.returncode != 0:
            raise RuntimeError(f"archive failed tar={tar.returncode} zstd={zst.returncode}")
        comp = os.path.getsize(archive)
        ratio = m["total_bytes"] / comp if comp else 0

        # 3. archive integrity (streamed checksum verify) + member count
        print("[3/5] verifying archive integrity ...", file=sys.stderr)
        tv = subprocess.run(["zstd", "-t", ZSTD_LONG, archive],
                            capture_output=True)
        if tv.returncode != 0:
            raise RuntimeError("zstd -t integrity failed: " + tv.stderr.decode()[:400])
        listing = subprocess.run(
            f'zstd -dc {ZSTD_LONG} "{archive}" | tar -tf - | grep -v "/$" | wc -l',
            shell=True, capture_output=True, text=True)
        member_files = int(listing.stdout.strip() or "0")

        # 4. optional full restore + record-level compare
        restore = {"performed": False}
        if full_restore_test:
            print("[4/5] full restore compare ...", file=sys.stderr)
            scratch = os.path.join(DEST_ROOT, "scratch_restore")
            if os.path.exists(scratch):
                shutil.rmtree(scratch)
            os.makedirs(scratch)
            rc = subprocess.run(
                f'zstd -dc {ZSTD_LONG} "{archive}" | tar -xf - -C "{scratch}"',
                shell=True)
            if rc.returncode != 0:
                raise RuntimeError("restore extract failed")
            rm = build_manifest(scratch, progress=True)
            restore = {
                "performed": True,
                "restored_set_hash": rm["set_hash"],
                "restored_total_files": rm["total_files"],
                "restored_total_bytes": rm["total_bytes"],
                "set_hash_match": rm["set_hash"] == m["set_hash"],
                "counts_match": rm["total_files"] == m["total_files"]
                                and rm["total_bytes"] == m["total_bytes"],
                "per_source_match": rm["per_source"] == m["per_source"],
                "groups_match": rm["groups"] == m["groups"],
            }
            shutil.rmtree(scratch)
        else:
            print("[4/5] (integrity-only; full restore not requested)", file=sys.stderr)

        # 5. retention: derive from measured free disk / this backup size (recomputed each run)
        print("[5/5] applying retention ...", file=sys.stderr)
        free = free_bytes(DEST_ROOT)
        usable = max(free - RESERVE_BYTES, 0)
        keep_n = max(1, int(usable // comp) + 1)  # +1: this backup already on disk
        snaps_root = os.path.join(DEST_ROOT, "snapshots")
        snaps = sorted(d for d in os.listdir(snaps_root)
                       if os.path.isdir(os.path.join(snaps_root, d)))
        pruned = []
        while len(snaps) > keep_n:
            victim = snaps.pop(0)
            shutil.rmtree(os.path.join(snaps_root, victim))
            pruned.append(victim)

        growth = store_growth()
        elapsed = round(time.time() - t0, 1)
        ok = (not full_restore_test) or (
            restore["set_hash_match"] and restore["counts_match"]
            and restore["per_source_match"])

        receipt = {
            "status": "OK" if ok else "RESTORE_MISMATCH",
            "stamp": stamp, "at_utc": utc_stamp(), "elapsed_s": elapsed,
            "archive": archive,
            "uncompressed_bytes": m["total_bytes"],
            "compressed_bytes": comp,
            "compression_ratio": round(ratio, 2),
            "set_hash": m["set_hash"],
            "manifest_files": m["total_files"],
            "archive_member_files": member_files,
            "member_count_matches_manifest": member_files == m["total_files"],
            "archive_integrity": "PASS",
            "restore_test": restore,
            "retention": {
                "policy": "keep = 1 + floor((dest_free - 20GiB reserve) / this_compressed_size); recomputed every run from live free space and live backup size -- self-adjusts to growth, no chosen number",
                "dest_free_bytes_after": free,
                "reserve_bytes": RESERVE_BYTES,
                "this_compressed_bytes": comp,
                "keep_n": keep_n,
                "pruned": pruned,
                "kept": sorted(os.listdir(snaps_root)),
            },
            "store_growth_estimate": growth,
            "media": {
                "dest_root": DEST_ROOT,
                "same_physical_disk_as_store": off_media,
                "off_media_blocker": off_media,
            },
            "excluded_derived": EXCLUDE_DERIVED,
        }
        write_json(receipt_path, receipt)

        if off_media:
            write_blocker("OFF_MEDIA",
                          "Backup destination is on the SAME physical disk as the store "
                          "(only /dev/disk0 present; no external volume mounted). Protects "
                          "against a bad write or a failed repair, NOT against disk failure. "
                          "Copy the archive to external media; off-disk destination is a "
                          "follow-up batch.",
                          {"dest_root": DEST_ROOT, "archive": archive, "stamp": stamp})
        if not ok:
            write_blocker("RESTORE_MISMATCH",
                          "Restore-test record set did not reproduce the live set.",
                          {"restore": restore, "stamp": stamp})

        print(json.dumps(receipt, indent=2))
        return 0 if ok else 3

    except Exception as e:  # noqa
        bp = write_blocker("BACKUP_FAILED", str(e), {"stamp": stamp})
        print(f"BACKUP FAILED: {e}\nblocker: {bp}", file=sys.stderr)
        return 4


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("plan")
    b = sub.add_parser("backup")
    b.add_argument("--full-restore-test", action="store_true")
    mm = sub.add_parser("manifest")
    mm.add_argument("root")
    a = ap.parse_args()
    if a.cmd == "plan":
        return cmd_plan()
    if a.cmd == "manifest":
        return cmd_manifest(a.root)
    if a.cmd == "backup":
        return cmd_backup(a.full_restore_test)


if __name__ == "__main__":
    sys.exit(main() or 0)
