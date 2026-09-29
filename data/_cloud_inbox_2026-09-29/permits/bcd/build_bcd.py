#!/usr/bin/env python3
"""Consensus for BCD series 29 as printed (bcd_reads.csv -> bcd_series29_asprinted.csv).
Rules (deterministic):
  >= 2 of A (text layer), T (tesseract column), C (tesseract cell) agree -> accepted
  otherwise, a read equal to the same month's accepted value in the adjacent issue of the
  same kind (previous, else next)          -> "->adjacent"
  Oct 1961 (the only LEVEL issue): a read whose ratio to the Nov 1961 index equals the median
  level/index ratio within 0.25%           -> "->index_ratio"
  index runs that revise-then-revert (row mis-registration)  -> blanked, "run_deviation"
  else value blank, status "ocr_doubt" (reads kept in 'reads').
"""
import os, re
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December"]


def ok(v, kind):
    return v == v and ((kind == "level" and 700 <= v <= 2500) or (kind == "index" and 60 <= v <= 160))


def main():
    r = pd.read_csv(os.path.join(HERE, "bcd_reads.csv"), dtype={"issue": str, "month": str})
    r["ik"] = r.issue.map(lambda s: int(s[:4]) * 12 + int(s[5:7]) - 1)
    recs = []
    for _, x in r.iterrows():
        vals = {e: (x[e] if ok(x[e], x.kind) else np.nan) for e in ("A", "T", "C")}
        reads = ";".join(f"{e}={x[e]}" for e in ("A", "T", "C") if x[e] == x[e])
        good = [v for v in vals.values() if v == v]
        agree = [v for v in good if good.count(v) >= 2]
        if agree:
            val, st = agree[0], f"{good.count(agree[0])}of3"
        else:
            val, st = np.nan, "split" if good else "no_read"
        recs.append({"issue_ym": x.issue, "ik": x.ik, "kind": x.kind, "month": x.month, "value": val, "status": st,
                     "cands": good, "reads": reads, "page_file": x.page_file,
                     "flag": "r" if re.search(r"^\W*r", str(x.A_raw)) else ("p" if re.search(r"^\W*p", str(x.A_raw)) else "")})
    d = pd.DataFrame(recs).sort_values(["kind", "month", "ik"]).reset_index(drop=True)
    for _ in range(3):
        for (kind, mon), g in d.groupby(["kind", "month"]):
            idx = list(g.index)
            for j, i in enumerate(idx):
                if d.at[i, "status"] not in ("split",):
                    continue
                for jj in (j - 1, j + 1):
                    if 0 <= jj < len(idx) and abs(d.at[idx[jj], "ik"] - d.at[i, "ik"]) == 1:
                        ref = d.at[idx[jj], "value"]
                        if ref == ref and ref in d.at[i, "cands"]:
                            d.at[i, "value"] = ref
                            d.at[i, "status"] = "->adjacent"
                            break
    # revise-then-revert: a run of issues printing a month as v, with the nearest accepted prints
    # before and after the run both equal to u != v, is a row mis-registration, not a revision
    for (kind, mon), g in d[d.kind == "index"].groupby(["kind", "month"]):
        idx = [i for i in g.sort_values("ik").index if d.at[i, "value"] == d.at[i, "value"]]
        vals = [d.at[i, "value"] for i in idx]
        j = 0
        while j < len(idx):
            k = j
            while k + 1 < len(idx) and vals[k + 1] == vals[j]:
                k += 1
            if j > 0 and k + 1 < len(idx) and vals[j - 1] == vals[k + 1] != vals[j]:
                for q in range(j, k + 1):
                    d.at[idx[q], "status"] = "run_deviation"
                    d.at[idx[q], "value"] = np.nan
            j = k + 1
    # Oct 1961 levels vs Nov 1961 index
    lv = d[(d.kind == "level")].set_index("month")
    ix = d[(d.kind == "index") & (d.issue_ym == "1961-11")].set_index("month")
    both = [m for m in lv.index if m in ix.index and lv.at[m, "value"] == lv.at[m, "value"] and ix.at[m, "value"] == ix.at[m, "value"]]
    if len(both) >= 6:
        ratio = float(np.median([lv.at[m, "value"] / ix.at[m, "value"] for m in both]))
        for i in d[(d.kind == "level") & (d.status == "split")].index:
            m = d.at[i, "month"]
            if m in ix.index and ix.at[m, "value"] == ix.at[m, "value"]:
                hits = [c for c in d.at[i, "cands"] if abs(c / ix.at[m, "value"] / ratio - 1) < 0.0025]
                if len(hits) == 1:
                    d.at[i, "value"] = hits[0]
                    d.at[i, "status"] = "->index_ratio"
        print("level/index ratio (Oct61 level / Nov61 index):", round(ratio, 3), "on", len(both), "months")
    d.loc[d.status == "split", "status"] = "ocr_doubt"
    d = d[~((d.status == "no_read") & (d.reads == ""))]          # grid rows beyond the printed months
    newest = d[d.value.notna()].groupby("issue_ym").month.max()
    d["newest_month_in_issue"] = d.issue_ym.map(newest)
    d["issue"] = d.issue_ym.map(lambda s: f"Business Cycle Developments {MONTHS[int(s[5:7]) - 1]} {s[:4]}")
    d["as_of"] = d.issue_ym.map(lambda s: (pd.Timestamp(s + "-01") + pd.offsets.MonthEnd(0)).strftime("%Y-%m-%d"))
    d["pg"] = d.page_file.str.extract(r"_p(\d+)")[0].astype(int).astype(str)
    d["source"] = ("fraser.stlouisfed.org/files/docs/publications/BusCycD/60-69/BCD_" + d.issue_ym.str[5:7] + d.issue_ym.str[:4]
                   + ".pdf pdf p." + d.pg + " Table 1 series 29")
    d["units"] = d.kind.map({"level": "thousands of units, SAAR", "index": "index 1957-59=100, SA"})
    cols = ["issue", "issue_ym", "as_of", "month", "kind", "units", "value", "flag", "status", "reads",
            "newest_month_in_issue", "source"]
    d = d.sort_values(["issue_ym", "month"])[cols]
    d.to_csv(os.path.join(HERE, "bcd_series29_asprinted.csv"), index=False)
    print(d.status.value_counts().to_string())


if __name__ == "__main__":
    main()
