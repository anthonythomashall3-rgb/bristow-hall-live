#!/usr/bin/env python3
"""Validation of permits_asprinted_1960_1999.csv (writes validation_*.csv and prints a summary).

1. Read status: how each cell was accepted (3of3 / 2of3 / cross-issue / doubt).
2. External check, starts: ALFRED HOUST vintages exist from 1960-07-21. For each issue, the
   vintage whose newest month equals the issue's newest starts month (latest such vintage
   dated on or before the end of the issue month) is compared cell by cell.
3. External check, permits: ALFRED PERMIT vintages exist from 1999-08-17; issues from Aug 1999
   onward are compared the same way.
4. Revision pattern: each month is printed in ~13 issues; count value changes and isolated
   deviations (a value differing from both neighbors that agree with each other).
5. Distance from today's Census values (log ratio), by decade.
"""
import os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ALF = "/home/user/bristow-hall-live/data/onset-detector-new-2026-08-23/27_realtime_vintages/alfred_all_vintages/"


def load_vint(name):
    f = os.path.join(ALF, f"{name}_all_vintages.csv")
    if not os.path.exists(f):
        return None
    w = pd.read_csv(f, index_col=0)
    w.index = pd.to_datetime(w.index).strftime("%Y-%m")
    cols = {pd.Timestamp(c.split("_")[-1]): c for c in w.columns}
    return w, cols


def external(df, var, name):
    vv = load_vint(name)
    if vv is None:
        return pd.DataFrame()
    w, cols = vv
    vdates = sorted(cols)
    last_obs = {d: w[cols[d]].last_valid_index() for d in vdates}
    out = []
    for iss, g in df.groupby("issue_ym"):
        as_of = pd.Timestamp(g.as_of.iloc[0])
        gv = g[g[var].notna()]
        if gv.empty:
            continue
        newest = gv.month.max()
        cands = [d for d in vdates if d <= as_of + pd.Timedelta(days=5) and last_obs[d] == newest]
        if not cands:
            continue
        vd = cands[-1]
        col = cols[vd]
        for _, r in g.iterrows():
            a = w.at[r.month, col] if r.month in w.index else np.nan
            out.append({"issue_ym": iss, "month": r.month, "vintage": vd.strftime("%Y-%m-%d"), "printed": r[var],
                        "alfred": a, "status": r[var.replace("_authorized_saar_thous", "").replace("_total_saar_thous", "") + "_read_status"]})
    return pd.DataFrame(out)


def revision_pattern(df, var):
    rows = []
    iso = []
    for mon, g in df.sort_values("issue_ym").groupby("month"):
        v = g[var].values
        iss = g.issue_ym.values
        vals = [x for x in v if x == x]
        ch = sum(1 for a, b in zip(v[:-1], v[1:]) if a == a and b == b and a != b)
        rows.append({"month": mon, "n_prints": len(vals), "n_distinct": len(set(vals)), "n_changes": ch})
        for k in range(1, len(v) - 1):
            if v[k - 1] == v[k - 1] and v[k + 1] == v[k + 1] and v[k] == v[k] and v[k - 1] == v[k + 1] != v[k]:
                iso.append({"month": mon, "issue_ym": iss[k], "value": v[k], "neighbors": v[k - 1]})
    return pd.DataFrame(rows), pd.DataFrame(iso)


def main():
    df = pd.read_csv(os.path.join(HERE, "permits_asprinted_1960_1999.csv"), dtype={"month": str, "issue_ym": str})
    lines = []
    lines.append(f"rows {len(df)}; issues {df.issue_ym.nunique()} ({df.issue_ym.min()} .. {df.issue_ym.max()}); "
                 f"months {df.month.min()} .. {df.month.max()}")
    for v, st in (("permits_authorized_saar_thous", "permits_read_status"), ("starts_total_saar_thous", "starts_read_status")):
        lines.append(f"{v}: non-null {df[v].notna().sum()} / {len(df)}")
        lines.append("  status: " + "; ".join(f"{k}={n}" for k, n in df[st].value_counts().items()))
    ext = []
    for v, name in (("starts_total_saar_thous", "HOUST"), ("permits_authorized_saar_thous", "PERMIT")):
        e = external(df, v, name)
        if e.empty:
            lines.append(f"ALFRED {name}: no overlapping vintages")
            continue
        e["series"] = name
        both = e[e.printed.notna() & e.alfred.notna()]
        exact = (both.printed == both.alfred).mean() if len(both) else np.nan
        lines.append(f"ALFRED {name}: {both.issue_ym.nunique()} issues matched to a same-newest-month vintage; "
                     f"{len(both)} cells; exact match {exact:.1%}; |diff|<=1: {((both.printed - both.alfred).abs() <= 1).mean():.1%}")
        ext.append(e)
    if ext:
        pd.concat(ext).to_csv(os.path.join(HERE, "validation_alfred.csv"), index=False)
    for v in ("permits_authorized_saar_thous", "starts_total_saar_thous"):
        rp, iso = revision_pattern(df, v)
        lines.append(f"{v}: months {len(rp)}; median prints/month {rp.n_prints.median():.0f}; "
                     f"median distinct values/month {rp.n_distinct.median():.0f}; isolated deviations {len(iso)}")
        iso.to_csv(os.path.join(HERE, f"validation_isolated_{v.split('_')[0]}.csv"), index=False)
    for v, c in (("permits_authorized_saar_thous", "census_current_permits"), ("starts_total_saar_thous", "census_current_starts")):
        x = df[df[v].notna() & df[c].notna()].copy()
        x["lr"] = np.log(x[v] / x[c])
        x["decade"] = x.month.str[:3] + "0s"
        s = x.groupby("decade").lr.agg(["count", "median", lambda z: np.median(np.abs(z))])
        s.columns = ["n", "median_log_ratio", "median_abs_log_ratio"]
        lines.append(f"{v} vs today's Census (log printed/current):\n" + s.round(4).to_string())
        big = x[x.lr.abs() > 0.2]
        big.to_csv(os.path.join(HERE, f"validation_far_from_census_{v.split('_')[0]}.csv"), index=False)
        lines.append(f"  cells with |log ratio|>0.2: {len(big)}")
    g = df.groupby("issue_ym").month.agg(["min", "max", "count"])
    mins = pd.PeriodIndex(g["min"], freq="M")
    lost = [g.index[i] for i in range(1, len(g) - 1) if (mins[i] - mins[i - 1]).n > 1 and (mins[i + 1] - mins[i]).n < 1]
    lines.append(f"issues whose oldest printed row appears lost in OCR (month present in earlier issues): {len(lost)} {lost}")
    f = df[df.is_newest_month]
    lines.append(f"newest-month rows: {len(f)}; permits non-null {f.permits_authorized_saar_thous.notna().sum()}")
    txt = "\n".join(lines)
    open(os.path.join(HERE, "validation_summary.txt"), "w").write(txt + "\n")
    print(txt)


if __name__ == "__main__":
    main()
