"""B-NBER-FORK §5.1 probe — measure NBER business-cycle reference dates FROM the
fetched source bytes. Zero re-fetch. Cross-check (§5.6) against the frozen ledger's
nber_peak_comparator dates; report disagreement, never adopt.
"""
import json, hashlib, datetime as dt
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SRC = HERE / "business_cycle_dates.json"
LEDGER = REPO / "model_authority/target_ledger/instrument_onset_target_ledger.v1.json"

raw = SRC.read_bytes()
sha = hashlib.sha256(raw).hexdigest()
cycles = json.loads(raw)


def pd(s):
    return dt.date.fromisoformat(s) if s else None


peaks = [c["peak"] for c in cycles if c.get("peak")]
troughs = [c["trough"] for c in cycles if c.get("trough")]
all_dates = sorted(pd(d) for d in (peaks + troughs))

# cadence: every date first-of-month?
non_first = [d.isoformat() for d in all_dates if d.day != 1]
# modal gap between consecutive reference dates (months)
gaps = []
for a, b in zip(all_dates, all_dates[1:]):
    gaps.append((b.year - a.year) * 12 + (b.month - a.month))
from collections import Counter
gapmode = Counter(gaps).most_common(3)

# monotonic peak<trough within each cycle, and cross-cycle ordering
order_ok = True
prev = None
for c in cycles:
    p, t = pd(c.get("peak")), pd(c.get("trough"))
    if p and t and not (p < t):
        order_ok = False
    if prev and p and not (prev < p):
        order_ok = False
    if t:
        prev = t

probe = {
    "schema_version": "recession_monitor_v2.nber_reference_cycles.probe.v1",
    "batch": "B-NBER-FORK",
    "source_url": "https://data.nber.org/cycles/business_cycle_dates.json",
    "fetch_stamp": (HERE / "FETCH_STAMP.txt").read_text().strip(),
    "http": "200 bytes=2303 ctype=application/json",
    "source_sha256": sha,
    "measured_from_bytes": {
        "record_count_cycles": len(cycles),
        "peak_count": len(peaks),
        "trough_count": len(troughs),
        "first_record_has_empty_peak": cycles[0].get("peak") == "",
        "earliest_date": all_dates[0].isoformat(),
        "latest_date": all_dates[-1].isoformat(),
        "all_dates_first_of_month": len(non_first) == 0,
        "non_first_of_month": non_first,
        "gap_months_modal_top3": gapmode,
        "peak_lt_trough_and_cross_order_ok": order_ok,
        "payload_bytes": len(raw),
    },
}

# §5.6 cross-check vs ledger nber_peak_comparator (report only)
ledger = json.loads(LEDGER.read_bytes())
eps = ledger.get("recession_targets") or []
ledger_peaks = []
for e in eps:
    v = e.get("nber_peak_comparator")
    if v:
        ledger_peaks.append(v)
src_peak_set = set(peaks)
in_src = [p for p in ledger_peaks if p in src_peak_set]
not_in_src = [p for p in ledger_peaks if p not in src_peak_set]
probe["crosscheck_ledger_5_6"] = {
    "note": "cross-check ONLY per §5.6; source bytes are authoritative, ledger never adopted",
    "ledger_nber_peak_comparator_count": len(ledger_peaks),
    "ledger_peaks_present_in_source": in_src,
    "ledger_peaks_ABSENT_from_source": not_in_src,
    "all_ledger_peaks_matched": len(not_in_src) == 0,
}

print(json.dumps(probe, indent=2))
(HERE / "PROBE_RECEIPT.v1.json").write_text(json.dumps(probe, indent=2) + "\n")
