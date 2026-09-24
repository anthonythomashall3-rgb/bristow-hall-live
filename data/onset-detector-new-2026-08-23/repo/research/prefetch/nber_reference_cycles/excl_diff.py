"""B-NBER-FORK — Wave-14 EXCL-failure-mode check: diff the shelved ledger's date
constants against LIVE code/authority. A shelved value that still appears live
governs invisibly ("the value outlives the file"). Report every match; fixing the
asof/onset dependence is a separate science batch (§22.4), not this DATA fork.
"""
import json, re
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SHELVED = REPO / "_shelf/v1/model_authority/target_ledger/instrument_onset_target_ledger.v1.json"
led = json.loads(SHELVED.read_text())

onset = sorted({e["onset_T_star"] for e in led.get("recession_targets", []) if e.get("onset_T_star")})
ends = sorted({e["end"] for e in led.get("recession_targets", []) if e.get("end")})
peaks = sorted({e["nber_peak_comparator"] for e in led.get("recession_targets", []) if e.get("nber_peak_comparator")})
dist = []
for w in led.get("disturbance_background_windows", []):
    for k in ("start", "end"):
        if w.get(k):
            dist.append(w[k])
dist = sorted(set(dist))

# LIVE trees to scan — construction code + authority the system reads. Excludes the
# data store, vintage fixtures, feed_factory *.bin fixtures, research/, docs/, _shelf/,
# and the fork itself (which legitimately re-sources the NBER peaks).
LIVE_DIRS = ["method_source", "bh", "model_authority", ".claude/hooks", "data_vault/scripts"]
SUFF = {".py", ".json", ".md", ".csv"}
EXCLUDE_SUBSTR = ("_shelf/", "external_comparators/nber_reference_cycles", "/candidates/", ".bin")


def live_files():
    for d in LIVE_DIRS:
        base = REPO / d
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if not (p.is_file() and p.suffix in SUFF):
                continue
            rp = p.relative_to(REPO).as_posix()
            if any(s in rp for s in EXCLUDE_SUBSTR):
                continue
            yield p


groups = {"onset_T_star": onset, "ledger_end": ends, "nber_peak_comparator": peaks,
          "disturbance_window": dist}
report = {"shelved_ledger": SHELVED.relative_to(REPO).as_posix(),
          "shelved_ledger_sha256": "8b204ccd3f9204464c94f486b29c06bcc927e69ad92da68a106202b87fc13d0f",
          "date_constants": {k: v for k, v in groups.items()},
          "live_matches": {}}

files = list(live_files())
for gname, dates in groups.items():
    hits = []
    for dstr in dates:
        for p in files:
            try:
                txt = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for i, line in enumerate(txt.splitlines(), 1):
                if dstr in line:
                    hits.append({"date": dstr, "file": p.relative_to(REPO).as_posix(),
                                 "line": i, "text": line.strip()[:200]})
    report["live_matches"][gname] = hits

# nber peaks are EXPECTED to reappear via the fork's re-sourcing; separate that class.
report["interpretation"] = {
    "onset_T_star_live_hits": len(report["live_matches"]["onset_T_star"]),
    "note": "onset_T_star / disturbance-window hits in LIVE artifacts = the 'value outlives "
            "the shelved file' failure mode (Wave-14). nber_peak_comparator hits are the SAME "
            "published dates the fork re-sources from NBER bytes and are not a leak.",
}

OUT = Path(__file__).resolve().parent / "EXCL_DIFF.v1.json"
OUT.write_text(json.dumps(report, indent=2) + "\n")
for g in groups:
    print(g, "->", len(report["live_matches"][g]), "live hit(s)")
print("\nonset_T_star / disturbance live hits (the leak class):")
for g in ("onset_T_star", "disturbance_window", "ledger_end"):
    for h in report["live_matches"][g]:
        print("  [%s] %s:%d  %s" % (h["date"], h["file"], h["line"], h["text"][:120]))
