#!/usr/bin/env python3
"""Combine the three OCR reads (A = ABBYY text layer, T = tesseract table read, C = tesseract
cell read) of every Economic Indicators housing table into one as-printed value per
issue x month, validate across issues, and write permits_asprinted_1960_1999.csv.

Deterministic rules only (no value is typed by hand or read off an image by a person):
  page level  : a value read identically by >= 2 engines is accepted ("3of3"/"2of3").
  cross-issue : each month is printed in ~13 consecutive issues. A cell the engines split on
                is accepted only if one engine's read equals the same month's accepted value
                in the adjacent issue (previous, else next) -> "split->adjacent".
                An accepted value that differs from BOTH adjacent issues while those two agree
                (revise-then-revert is not a real revision pattern) is replaced by the
                adjacent value only if one engine read that value -> "isolated->adjacent";
                otherwise it is kept and flagged "isolated_deviation".
  anything else: value left blank, status "ocr_doubt", engine reads listed in *_candidates.
Plausible read: 300..3000 thousand units and within 35% (log) of today's Census value for
that month (removes reads that lost a leading '1,'); implausible reads are still listed.
"""
import glob, os, re
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
LO, HI = 300, 3000
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December"]

FRED_P = pd.read_csv(os.path.join(HERE, "ref", "PERMIT_current.csv"), index_col=0, parse_dates=True).iloc[:, 0]
FRED_H = pd.read_csv(os.path.join(HERE, "ref", "HOUST_current.csv"), index_col=0, parse_dates=True).iloc[:, 0]


def issue_key(iss):
    m, y = iss.split("-")
    return int(y) * 12 + int(m) - 1


def load_reads():
    fs = [f for f in glob.glob(os.path.join(HERE, "parsed", "reads_*.csv"))
          if re.fullmatch(r"reads_\d\d-\d{4}\.csv", os.path.basename(f))]
    d = pd.concat([pd.read_csv(f, dtype={"permits_raw": str, "starts_raw": str, "label_raw": str}) for f in fs],
                  ignore_index=True)
    # SAAR monthly values are printed as whole thousands; a read with a decimal digit
    # ("939.2", "1, 745. 1") comes from an annual-total or NSA row -> not a valid SAAR read
    for v in ("permits", "starts"):
        raw = d[v + "_raw"].fillna("").astype(str)
        dec = raw.str.contains(r"\d\s*\.\s*\d\s*$") & ~raw.str.contains(r"\d\s*[.,]\s*\d{3}\s*$")
        d.loc[dec, v] = np.nan
    return d


def census_screen(reads):
    """blank reads more than 35% (log) from today's Census value for the month (lost '1,' etc.)"""
    for var, ref in (("permits", FRED_P), ("starts", FRED_H)):
        rv = reads.month.map(lambda m: ref.get(pd.Timestamp(m + "-01"), np.nan))
        bad = reads[var].notna() & rv.notna() & (np.log(reads[var] / rv).abs() >= 0.35)
        reads.loc[bad, var] = np.nan
    return reads


def engine_sanity(reads, var):
    """drop an engine's reads for a whole issue when its month->value map disagrees with the
    adjacent issues on most months (a row/month mis-registration, not single-digit OCR slips).
    C inherits A's (or T's) row geometry, so it is dropped together with that engine."""
    piv = reads.pivot_table(index=["issue", "month"], columns="engine", values=var, aggfunc="first")
    # provisional consensus: value read by >= 2 engines
    cons = {}
    for (iss, mon), r in piv.iterrows():
        vals = [r.get(e) for e in "ATC" if e in r and r.get(e) == r.get(e)]
        for v in vals:
            if vals.count(v) >= 2:
                cons[(iss, mon)] = v
                break
    bad = []
    for iss in piv.index.get_level_values(0).unique():
        k = issue_key(iss)
        nb = [f"{(k2 % 12) + 1:02d}-{k2 // 12}" for k2 in (k - 1, k + 1)]
        rate = {}
        for e in "ATC":
            if e not in piv.columns:
                continue
            sub = piv.loc[iss][e].dropna()
            n = agree = 0
            for mon, v in sub.items():
                ref = [cons.get((j, mon)) for j in nb if (j, mon) in cons]
                if ref:
                    n += 1
                    agree += any(abs(v - x) < 0.5 for x in ref)
            if n >= 5:
                rate[e] = (agree / n, agree, n)
        # drop only a relative failure: the other engine of the same page matches the adjacent
        # issues well. When both engines disagree with the neighbours the issue is a revision.
        for e, (r, a, n) in rate.items():
            other = [rate[o][0] for o in rate if o != e]
            if r < 0.4 and other and max(other) >= 0.7:
                bad.append((iss, e, a, n))
    return bad


def fetch_urls():
    """actual URL that delivered each issue (base pattern or EI_MMYYYY alternate)"""
    log = pd.read_csv(os.path.join(HERE, "fetch_log.csv"))
    log = log[log.status.astype(str) == "200"]
    out = {}
    for u in log.url:
        m = re.search(r"/ei/(\d{4})/(?:(\d\d)-\d{4}|EI_(\d\d)\d{4})\.pdf", u)
        if m:
            out[f"{m.group(2) or m.group(3)}-{m.group(1)}"] = u.replace("https://", "")
    return out


# ------------------------------------------------------------------ universe (permit-issuing places)
def norm_txt(t):
    t = t.replace("\n", " ")
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"(\d)\s*[.,]\s*(000)", r"\1,\2", t)
    t = re.sub(r"(?<=\d)[lI](?=\d)|(?<=\d)[lI](?=,000)", "1", t)
    t = t.replace("I9", "19").replace("l9", "19")
    return t


VALID_UNIVERSES = {10000, 12000, 13000, 14000, 16000, 17000, 19000}   # every figure the footnotes use


def universe_rules(txt):
    """list of (lo_year, hi_year, places) stated in the page footnotes; hi inclusive.
    Footnotes are set in two columns, so the other column's words can sit between the parts of
    a sentence: gaps of up to ~120 characters are allowed."""
    t = norm_txt(txt)
    G = r".{0,120}?"
    R = []
    m = re.search(r"(\d\d),000 permit-issu" + G + r"prior to (19\d\d),?" + G + r"(\d\d),000 or more thereafter", t)
    if m:
        R += [(1900, int(m.group(2)) - 1, int(m.group(1)) * 1000), (int(m.group(2)), 2100, int(m.group(3)) * 1000)]
    for m in re.finditer(r"(\d\d),000 permit-issu" + G + r"places? beginning (19\d\d)", t):
        R.append((int(m.group(2)), 2100, int(m.group(1)) * 1000))
    for m in re.finditer(r"(\d\d),000 for (19\d\d)-(\d\d)\b", t):
        R.append((int(m.group(2)), 1900 + int(m.group(3)), int(m.group(1)) * 1000))
    for m in re.finditer(r"(\d\d),000 prior to (19\d\d)", t):
        R.append((1900, int(m.group(2)) - 1, int(m.group(1)) * 1000))
    for m in re.finditer(r"[Bb]eginning (19\d\d),? units authorized are for (\d\d),000", t):
        R.append((int(m.group(1)), 2100, int(m.group(2)) * 1000))
    for m in re.finditer(r"[Uu]nits authorized beginning (19\d\d) relate to (\d\d),000", t):
        R.append((int(m.group(1)), 2100, int(m.group(2)) * 1000))
    for m in re.finditer(r"for (19\d\d)-(\d\d)" + G + r"are for (\d\d),000", t):
        R.append((int(m.group(1)), 1900 + int(m.group(2)), int(m.group(3)) * 1000))
    for m in re.finditer(r"for (19\d\d), for (\d\d),000", t):
        R.append((int(m.group(1)), int(m.group(1)), int(m.group(2)) * 1000))
    m = re.search(r"other data shown,?" + G + r"are for (\d\d),000", t)
    if m:
        R.append((1900, 2100, int(m.group(1)) * 1000))   # default: applies where nothing narrower does
    # OCR-garbled figures (e.g. '18,000', '39,000') are not universes any footnote uses
    return [r for r in R if r[2] in VALID_UNIVERSES and 1900 <= r[0] <= r[1]]


def universe_for(rules, year):
    hits = [(hi - lo, pl) for lo, hi, pl in rules if lo <= year <= hi]
    if not hits:
        return None
    return min(hits)[1]


def universe_note(txt):
    t = norm_txt(txt)
    m = re.search(r"([^.]{0,60}permit-issuing[^.]{0,200}\.)", t)
    if not m:
        m = re.search(r"(NOTE[^.]{0,40}units authorized[^.]{0,200}\.(?:[^.]{0,120}\.)?)", t)
    return m.group(1).strip() if m else ""


# ------------------------------------------------------------------ consensus
def page_consensus(vals):
    """vals: dict engine -> value (float or nan). returns (value, status, candidates)"""
    good = {e: v for e, v in vals.items() if v == v and v is not None and LO <= v <= HI}
    cands = ";".join(f"{e}={int(v) if float(v).is_integer() else v}" for e, v in sorted(vals.items()) if v == v and v is not None)
    if not good:
        return np.nan, "no_read", cands
    cnt = {}
    for v in good.values():
        cnt[v] = cnt.get(v, 0) + 1
    v, c = max(cnt.items(), key=lambda kv: kv[1])
    if c >= 3:
        return v, "3of3", cands
    if c == 2:
        return v, "2of3", cands
    return np.nan, "split", cands


def build(var, reads, issues_sorted, raw=None):
    """var: 'permits' or 'starts'. returns DataFrame issue x month with value/status/cands"""
    piv = reads.pivot_table(index=["issue", "month"], columns="engine", values=var, aggfunc="first")
    rawp = (raw if raw is not None else reads).pivot_table(index=["issue", "month"], columns="engine", values=var, aggfunc="first")
    for e in "ATC":
        if e not in piv.columns:
            piv[e] = np.nan
    ref = FRED_P if var == "permits" else FRED_H
    recs = []
    for (iss, mon), r in piv.iterrows():
        vals = {e: r[e] for e in "ATC"}
        rv = ref.get(pd.Timestamp(mon + "-01"), np.nan)
        rr = rawp.loc[(iss, mon)] if (iss, mon) in rawp.index else {}
        cands0 = ";".join(f"{e}={int(rr[e]) if float(rr[e]).is_integer() else rr[e]}" for e in "ACT" if e in rr and rr[e] == rr[e])
        # a read more than 35% (log) away from today's Census value for that month is an OCR
        # failure (dropped '1,' etc.), not a revision: excluded from the vote, still listed
        if rv == rv:
            vals = {e: (v if v == v and abs(np.log(v / rv)) < 0.35 else np.nan) for e, v in vals.items()}
        v, st, cands = page_consensus(vals)
        cands = cands0
        recs.append({"issue": iss, "month": mon, "value": v, "status": st, "cands": cands,
                     "reads": vals})
    df = pd.DataFrame(recs)
    df["ik"] = df.issue.map(issue_key)
    df = df.sort_values(["month", "ik"]).reset_index(drop=True)
    # cross-issue resolution, iterate until stable
    for _ in range(3):
        changed = 0
        for mon, g in df.groupby("month"):
            idx = list(g.index)
            for j, i in enumerate(idx):
                prev_i = idx[j - 1] if j > 0 and df.at[idx[j - 1], "ik"] == df.at[i, "ik"] - 1 else None
                next_i = idx[j + 1] if j + 1 < len(idx) and df.at[idx[j + 1], "ik"] == df.at[i, "ik"] + 1 else None
                pv = df.at[prev_i, "value"] if prev_i is not None else np.nan
                nv = df.at[next_i, "value"] if next_i is not None else np.nan
                reads_i = [x for x in df.at[i, "reads"].values() if x == x and LO <= x <= HI]
                st = df.at[i, "status"]
                if st in ("split", "no_read"):
                    for ref, lab in ((pv, "split->prev_issue"), (nv, "split->next_issue")):
                        if ref == ref and ref in reads_i:
                            df.at[i, "value"] = ref
                            df.at[i, "status"] = lab
                            changed += 1
                            break
                elif st in ("3of3", "2of3") and pv == pv and nv == nv and pv == nv and df.at[i, "value"] != pv:
                    if pv in reads_i:
                        df.at[i, "value"] = pv
                        df.at[i, "status"] = st + ";isolated->adjacent"
                        changed += 1
                    elif "isolated_deviation" not in st:
                        df.at[i, "status"] = st + ";isolated_deviation"
        if not changed:
            break
    df.loc[df.status.isin(["split", "no_read"]), "status"] = df.status.map(lambda s: "ocr_doubt" if s == "split" else "no_read")
    return df


def main():
    reads = load_reads()
    reads = reads[reads.month.notna()]
    raw_reads = reads.copy()
    reads = census_screen(reads)
    dropped = []
    for var in ("permits", "starts"):
        for iss, e, a, n in engine_sanity(reads, var):
            dropped.append({"issue": iss, "var": var, "engine": e, "agree_with_adjacent": a, "n_compared": n})
            m = (reads.issue == iss) & (reads.engine == e)
            reads.loc[m, var] = np.nan
    pd.DataFrame(dropped).to_csv(os.path.join(HERE, "parsed", "engine_drops.csv"), index=False)
    urls = fetch_urls()
    pidx = pd.read_csv(os.path.join(HERE, "raw", "pages", "page_index.csv"), dtype=str).set_index("issue")
    issues = sorted(reads.issue.unique(), key=issue_key)
    P = build("permits", reads, issues, raw_reads).set_index(["issue", "month"])
    S = build("starts", reads, issues, raw_reads).set_index(["issue", "month"])
    # month set per issue: from engine A when present, else T, else C
    months = {}
    for iss, g in reads.groupby("issue"):
        for e in ("A", "T", "C"):
            mm = sorted(g[g.engine == e].month.unique())
            if mm:
                months[iss] = mm
                break
    # rows that are not SAAR data rows: (a) annual-total rows caught above the monthly block
    # (figures with a decimal digit), (b) newest rows that print only FHA/VA figures (the
    # permits and starts cells are blank: the cell OCR returns nothing but rule/dot noise)
    def is_dec(x):
        return bool(re.search(r"\d\s*\.\s*\d\s*$", x)) and not re.search(r"\d\s*[.,]\s*\d{3}\s*$", x)

    def is_blank(x):
        return re.fullmatch(r"[|.,\s]*", x) is not None
    rinfo = {}
    for (iss, mon), g in raw_reads.groupby(["issue", "month"]):
        vals = [str(v) for v in pd.concat([g.permits_raw, g.starts_raw]).dropna()]
        c = g[g.engine == "C"]
        cvals = [str(v) for v in pd.concat([c.permits_raw, c.starts_raw]).dropna()]
        rinfo[(iss, mon)] = (any(is_dec(v) for v in vals), bool(cvals) and all(is_blank(v) for v in cvals) and not
                             [v for v in vals if not is_blank(v) and v not in cvals])
    dropped_rows = []
    for iss in list(months):
        keep = []
        for mon in months[iss]:
            pv = P.loc[(iss, mon)]["value"] if (iss, mon) in P.index else np.nan
            sv = S.loc[(iss, mon)]["value"] if (iss, mon) in S.index else np.nan
            dec, blank = rinfo.get((iss, mon), (False, False))
            if pv != pv and sv != sv and (dec or blank):
                dropped_rows.append({"issue": iss, "month": mon, "reason": "annual/NSA row (decimal figures)" if dec else "blank permits and starts cells"})
            else:
                keep.append(mon)
        months[iss] = keep
    pd.DataFrame(dropped_rows).to_csv(os.path.join(HERE, "parsed", "dropped_rows.csv"), index=False)
    labels = reads[reads.engine == "A"].set_index(["issue", "month"]).label_raw.to_dict()
    flags = reads[reads.engine == "A"].set_index(["issue", "month"]).flag.to_dict()
    # a revision/preliminary mark printed against the permits figure itself ('r918', '1,146p')
    pr = raw_reads[raw_reads.engine == "A"].set_index(["issue", "month"]).permits_raw.fillna("").astype(str)
    for k, v in pr.items():
        m = re.match(r"^\s*([rp])\s*\d", v) or re.search(r"\d\s*([rp])\s*$", v)
        if m and not (isinstance(flags.get(k), str) and flags.get(k)):
            flags[k] = m.group(1)
    labelsT = reads[reads.engine == "T"].set_index(["issue", "month"]).label_raw.to_dict()
    out = []
    for iss in issues:
        mm, yy = iss.split("-")
        pgf = glob.glob(os.path.join(HERE, "raw", "pages", f"{iss}_p*.txt"))
        txt = open(pgf[0]).read() if pgf else ""
        rules = universe_rules(txt)
        unote = universe_note(txt)
        newest = max(months[iss])
        ym = f"{yy}-{mm}"
        as_of = (pd.Timestamp(int(yy), int(mm), 1) + pd.offsets.MonthEnd(0)).strftime("%Y-%m-%d")
        page = pidx.loc[iss, "page"] if iss in pidx.index else ""
        src = f"{urls.get(iss, 'fraser.stlouisfed.org/files/docs/publications/ei/%s/%s.pdf' % (yy, iss))} pdf p.{page}"
        for mon in months[iss]:
            p = P.loc[(iss, mon)] if (iss, mon) in P.index else None
            s = S.loc[(iss, mon)] if (iss, mon) in S.index else None
            d = pd.Timestamp(mon + "-01")
            uni = universe_for(rules, d.year)
            fl = flags.get((iss, mon), "")
            fl = fl if isinstance(fl, str) else ""
            lab = labels.get((iss, mon), labelsT.get((iss, mon), ""))
            out.append({
                "issue": f"Economic Indicators {MONTHS[int(mm) - 1]} {yy}",
                "issue_ym": ym,
                "as_of": as_of,
                "month": mon,
                "permits_authorized_saar_thous": p["value"] if p is not None else np.nan,
                "starts_total_saar_thous": s["value"] if s is not None else np.nan,
                "flag": fl,
                "source": src,
                "newest_month_in_issue": newest,
                "is_newest_month": mon == newest,
                "permits_universe_places": uni if uni else "",
                "universe_basis": "footnote on page" if uni else ("footnote not parsed/absent" if not rules else "footnote does not cover year"),
                "universe_footnote": unote,
                "permits_read_status": p["status"] if p is not None else "missing",
                "permits_ocr_reads": p["cands"] if p is not None else "",
                "starts_read_status": s["status"] if s is not None else "missing",
                "starts_ocr_reads": s["cands"] if s is not None else "",
                "row_label_ocr": lab if isinstance(lab, str) else "",
                "census_current_permits": FRED_P.get(d, np.nan),
                "census_current_starts": FRED_H.get(d, np.nan),
            })
    df = pd.DataFrame(out)
    # a stated universe that differs from the same month's statement in both adjacent issues
    # (nearest stating issue within 3 on each side; they agree) is a footnote OCR slip (e.g. '10,000' for '16,000'): use the adjacent value
    df["ikey"] = df.issue_ym.map(lambda s: int(s[:4]) * 12 + int(s[5:7]))
    st = df[df.universe_basis == "footnote on page"]
    key = {(r.month, r.ikey): r.permits_universe_places for r in st.itertuples()}
    def near(m, k, step):
        for j in range(1, 4):
            v = key.get((m, k + step * j))
            if v is not None:
                return v
        return None
    for i in st.index:
        m, k, u = df.at[i, "month"], df.at[i, "ikey"], df.at[i, "permits_universe_places"]
        a, b = near(m, k, -1), near(m, k, 1)
        if a is not None and a == b and a != u:
            df.at[i, "permits_universe_places"] = a
            df.at[i, "universe_basis"] = f"footnote on page read as {int(u)}; adjacent issues state {int(a)}"
    # the same misread footnote applies to the issue's other months (e.g. the newest ones,
    # which have no earlier issue to compare with)
    fixes = {}
    for i in df.index[df.universe_basis.str.startswith("footnote on page read as")]:
        m = re.search(r"read as (\d+); adjacent issues state (\d+)", df.at[i, "universe_basis"])
        fixes[(df.at[i, "issue_ym"], float(m.group(1)))] = (float(m.group(2)), df.at[i, "universe_basis"])
    for i in df.index[df.universe_basis == "footnote on page"]:
        f = fixes.get((df.at[i, "issue_ym"], df.at[i, "permits_universe_places"]))
        if f:
            df.at[i, "permits_universe_places"], df.at[i, "universe_basis"] = f
    df = df.drop(columns="ikey")
    # where the page states no universe for a month's year, show the statement of the nearest
    # issue (earlier first) that does, labelled as such
    stated = df[df.universe_basis.str.startswith("footnote on page")]
    for i in df.index[df.universe_basis.isin(["footnote not parsed/absent", "footnote does not cover year"])]:
        mon, iss = df.at[i, "month"], df.at[i, "issue_ym"]
        c = stated[stated.month == mon]
        if c.empty:
            continue
        before = c[c.issue_ym < iss]
        src = before.iloc[-1] if not before.empty else c.iloc[0]
        df.at[i, "permits_universe_places"] = src["permits_universe_places"]
        df.at[i, "universe_basis"] = f"not stated on page; as stated for this month in EI {src['issue_ym']}"
    df.to_csv(os.path.join(HERE, "permits_asprinted_1960_1999.csv"), index=False)
    return df


if __name__ == "__main__":
    df = main()
    print(df.shape)
    print(df.permits_read_status.value_counts())
    print(df.starts_read_status.value_counts())
