#!/usr/bin/env python3
"""CH-R33 SPLICE PRE-MEASUREMENT (read-only, offline).

For each CH-R26 Tier-4 splice pair whose BOTH halves are cached under
research/prefetch/, measure: coverage windows, overlap window, overlap n,
level ratio (median modern/old on overlap), Pearson corr on overlap, and
break-candidate gap (months between old-end and modern-start when no overlap).

Pure measurement from cached bytes. Zero network, zero store writes.
Outputs: research/splice_premeasure_v1.csv  +  research/splice_premeasure_v1.txt
Feeds S16.
"""
import json, math, os, csv, re
from datetime import date

PF = os.path.join(os.path.dirname(__file__), "prefetch")

# ---------- loaders: each returns dict{ 'YYYY-MM' -> float }, monthly-keyed ----------

def _mkey(d):  # 'YYYY-MM-DD' -> 'YYYY-MM'
    return d[:7]

def load_fred_obs(path):
    """FRED-API json (fred_miss/*.obs.json or alfred_obs vintage)."""
    d = json.load(open(path))
    obs = d["observations"] if isinstance(d, dict) and "observations" in d else d
    out = {}
    for r in obs:
        v = r.get("value")
        if v in (None, ".", ""):
            continue
        try:
            out[_mkey(r["date"])] = float(v)
        except ValueError:
            continue
    return _monthly_collapse(out)

def load_nber_dat(path):
    """NBER macrohistory .dat: 'YEAR  MONTH  VALUE' ; '.' == missing."""
    out = {}
    for line in open(path, errors="replace"):
        p = line.split()
        if len(p) < 3:
            continue
        yr, mo, val = p[0], p[1], p[2]
        if val == "." or not re.match(r"^-?\d", val):
            continue
        try:
            y, m = int(yr), int(mo)
            f = float(val)
        except ValueError:
            continue
        if not (1 <= m <= 12):
            continue
        out[f"{y:04d}-{m:02d}"] = f
    return out

def _monthly_collapse(daily_or_monthly):
    """If keys already monthly this is identity; if a month has many entries
    (daily series), keep the last-of-month value."""
    # keys are 'YYYY-MM'; multiple daily obs already merged to last by dict order
    return daily_or_monthly

def load_fred_daily_to_monthly(path):
    """Daily FRED series -> month-end (last obs of month)."""
    d = json.load(open(path))
    obs = d["observations"] if isinstance(d, dict) and "observations" in d else d
    tmp = {}
    for r in obs:
        v = r.get("value")
        if v in (None, ".", ""):
            continue
        try:
            tmp.setdefault(_mkey(r["date"]), []).append((r["date"], float(v)))
        except ValueError:
            continue
    return {k: sorted(vs)[-1][1] for k, vs in tmp.items()}

# ---------- metrics ----------

def span(series):
    if not series:
        return (None, None, 0)
    ks = sorted(series)
    return (ks[0], ks[-1], len(series))

def _months_between(a, b):  # 'YYYY-MM' inclusive-exclusive gap in months
    ya, ma = int(a[:4]), int(a[5:7])
    yb, mb = int(b[:4]), int(b[5:7])
    return (yb - ya) * 12 + (mb - ma)

def pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return None
    mx = sum(xs) / n; my = sum(ys) / n
    sx = sum((x - mx) ** 2 for x in xs); sy = sum((y - my) ** 2 for y in ys)
    if sx == 0 or sy == 0:
        return None
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    return sxy / math.sqrt(sx * sy)

def measure(old, modern):
    o0, o1, on = span(old)
    m0, m1, mn = span(modern)
    keys = sorted(set(old) & set(modern))
    r = {"old_start": o0, "old_end": o1, "old_n": on,
         "mod_start": m0, "mod_end": m1, "mod_n": mn,
         "ov_start": None, "ov_end": None, "ov_n": len(keys),
         "level_ratio_med": None, "corr": None, "gap_months": None}
    if keys:
        r["ov_start"], r["ov_end"] = keys[0], keys[-1]
        ratios = [modern[k] / old[k] for k in keys if old[k] != 0]
        if ratios:
            ratios.sort(); r["level_ratio_med"] = ratios[len(ratios) // 2]
        r["corr"] = pearson([old[k] for k in keys], [modern[k] for k in keys])
    else:
        # no overlap -> break candidate = gap between old_end and modern_start
        if o1 and m0:
            r["gap_months"] = _months_between(o1, m0)
    return r

# ---------- pair registry (only pairs with BOTH halves cached) ----------
F = lambda p: os.path.join(PF, p)

PAIRS = [
    # id, category, old(loader,path,label,unit), modern(loader,path,label,unit), note
    ("rail_freight", "NBER-rail<->modern-rail",
     (load_nber_dat, "nber_macrohistory/data/03/m03001.dat", "NBER m03001 net ton-miles", "bil ton-miles"),
     (load_fred_obs, "alfred_obs/RAILFRTCARLOADSD11__2026-08-03.json", "RAILFRTCARLOADSD11", "carloads idx D11"),
     "AAR modern proprietary; RAILFRTCARLOADSD11 = public modern rail proxy"),
    ("dept_store_retail", "dept-store<->retail",
     (load_nber_dat, "nber_macrohistory/data/06/m06002a.dat", "NBER m06002a dept-store sales SA", "idx 1935-39=100"),
     (load_fred_obs, "alfred_obs/RSAFS__2026-07-16.json", "RSAFS retail&food sales", "mil $ SA"),
     "index vs dollars: level_ratio not scientifically meaningful, corr on overlap is"),
    ("money_stock_h6", "money-stock<->H.6",
     (load_nber_dat, "nber_macrohistory/data/14/m14144a.dat", "NBER m14144a money stock (cb+currency) SA", "bil $"),
     (load_fred_obs, "alfred_obs/M2SL__2026-07-28.json", "M2SL", "bil $ SA"),
     "Friedman-Schwartz-class money vs modern M2; both billions $"),
    ("comm_paper_rate", "NBER-CP-rate<->modern-CP-rate",
     (load_fred_obs, "fred_miss/M13002US35620M156NNBR.obs.json", "NBER commercial paper rate", "pct"),
     (load_fred_daily_to_monthly, "fred_miss/DCPF3M.obs.json", "DCPF3M 3m financial CP", "pct"),
     "both interest rates (pct); direct level splice plausible if overlap"),
    ("call_money_rate", "NBER-call-money<->FEDFUNDS",
     (load_fred_obs, "fred_miss/M13009USM156NNBR.obs.json", "NBER call money rate", "pct"),
     (load_fred_daily_to_monthly, "alfred_obs/FEDFUNDS__2026-08-03.json", "FEDFUNDS", "pct"),
     "call money -> fed funds is a known rate-regime successor, not identity"),
    ("moody_aaa_control", "Moody's-AAA lineage (POSITIVE CONTROL)",
     (load_fred_obs, "alfred_obs/AAA__2026-08-03.json", "AAA monthly", "pct"),
     (load_fred_daily_to_monthly, "alfred_obs/DAAA__2026-08-05.json", "DAAA daily->monthly", "pct"),
     "same Moody's AAA lineage; expect full overlap + corr~1 (harness sanity)"),
]

def main():
    rows = []
    lines = ["CH-R33 SPLICE PRE-MEASUREMENT  (read-only, offline; feeds S16)", "=" * 70, ""]
    for pid, cat, oldspec, modspec, note in PAIRS:
        ol_load, ol_path, ol_lab, ol_unit = oldspec
        md_load, md_path, md_lab, md_unit = modspec
        op, mp = F(ol_path), F(md_path)
        if not os.path.exists(op) or not os.path.exists(mp):
            miss = ol_path if not os.path.exists(op) else md_path
            lines.append(f"[{pid}] DROP — half not cached: {miss}")
            rows.append({"pair_id": pid, "category": cat, "status": "HALF_NOT_CACHED",
                         "old_series": ol_lab, "modern_series": md_lab, "note": f"missing {miss}"})
            continue
        old = ol_load(op); mod = md_load(mp)
        m = measure(old, mod)
        status = "OVERLAP" if m["ov_n"] > 0 else ("GAP" if m["gap_months"] is not None else "EMPTY")
        rows.append({"pair_id": pid, "category": cat, "status": status,
                     "old_series": ol_lab, "old_unit": ol_unit, "old_start": m["old_start"],
                     "old_end": m["old_end"], "old_n": m["old_n"],
                     "modern_series": md_lab, "modern_unit": md_unit, "mod_start": m["mod_start"],
                     "mod_end": m["mod_end"], "mod_n": m["mod_n"],
                     "overlap_start": m["ov_start"], "overlap_end": m["ov_end"], "overlap_n": m["ov_n"],
                     "level_ratio_med_mod_over_old": m["level_ratio_med"], "corr_overlap": m["corr"],
                     "break_gap_months": m["gap_months"], "note": note})
        lines.append(f"[{pid}] {status}  ({cat})")
        lines.append(f"   old : {ol_lab:42s} {str(m['old_start']):>7}..{str(m['old_end']):>7} n={m['old_n']} [{ol_unit}]")
        lines.append(f"   mod : {md_lab:42s} {str(m['mod_start']):>7}..{str(m['mod_end']):>7} n={m['mod_n']} [{md_unit}]")
        if m["ov_n"] > 0:
            lr = m["level_ratio_med"]; cr = m["corr"]
            lines.append(f"   overlap {m['ov_start']}..{m['ov_end']} n={m['ov_n']}  "
                         f"level_ratio(mod/old)={lr:.4g}  corr={('%.4f'%cr) if cr is not None else 'NA'}")
        else:
            lines.append(f"   NO OVERLAP -> break candidate gap = {m['gap_months']} months "
                         f"({(m['gap_months'] or 0)/12:.1f}y) between old-end and modern-start")
        lines.append(f"   note: {note}")
        lines.append("")

    # write CSV
    cols = ["pair_id", "category", "status", "old_series", "old_unit", "old_start", "old_end", "old_n",
            "modern_series", "modern_unit", "mod_start", "mod_end", "mod_n",
            "overlap_start", "overlap_end", "overlap_n",
            "level_ratio_med_mod_over_old", "corr_overlap", "break_gap_months", "note"]
    outdir = os.path.dirname(__file__)
    with open(os.path.join(outdir, "splice_premeasure_v1.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols); w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})
    txt = "\n".join(lines)
    open(os.path.join(outdir, "splice_premeasure_v1.txt"), "w").write(txt)
    print(txt)

if __name__ == "__main__":
    main()
