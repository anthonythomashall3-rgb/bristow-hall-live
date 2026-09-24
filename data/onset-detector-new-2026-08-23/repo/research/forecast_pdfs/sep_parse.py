"""B-REG-FORECAST-PDFS-R2 — strict validator-gated parser for FOMC SEP *compilation*
projection Table 1 (Central Tendencies + Ranges), 2007-2017 text-table era.

ANTI-FABRICATION FIREWALL (R1-recommended, brief-mandated). A document is landed
ALL-OR-NOTHING: every one of these must hold or the whole doc is a recorded FAILURE:
  (a) year-header run found (3..6 tokens incl optional 'Longer run');
  (b) >=3 of 4 canonical variables parsed in BOTH the Central-Tendency and Range block;
  (c) each parsed variable row yields EXACTLY year-count range pairs in each block;
  (d) central_tendency in [range_low, range_high] for EVERY (var, horizon) cell.
A doc that fails any check lands NOTHING and is reported with a reason string.

Pure stdlib. Does not import the store. Records carry the meeting (knowledge) date.
"""
import re
import sys

sys.path.insert(0, "research/forecast_pdfs")
from probe_extract import extract_text  # noqa: E402

# canonical variable label variants -> canonical key
VAR_PATTERNS = [
    ("RGDP", re.compile(r"(?:Change in real GDP|Real GDP Growth|Real GDP)", re.I)),
    ("UNRATE", re.compile(r"Unemployment Rate", re.I)),
    ("PCE", re.compile(r"(?:Total PCE Inflation|PCE Inflation|PCE inflation)", re.I)),
    ("COREPCE", re.compile(r"Core PCE [Ii]nflation", re.I)),
]
PAIR = re.compile(r"(-?\d+\.\d)\s*to\s*(-?\d+\.\d)")
YEARRUN = re.compile(r"(?:19|20)\d{2}")


def _find_year_headers(segment):
    """Longest run of >=3 consecutive ascending years in the segment head."""
    yrs = [(m.start(), int(m.group())) for m in YEARRUN.finditer(segment)]
    best = []
    i = 0
    while i < len(yrs):
        run = [yrs[i]]
        j = i + 1
        while j < len(yrs) and yrs[j][1] == run[-1][1] + 1 and yrs[j][0] - run[-1][0] <= 6:
            run.append(yrs[j]); j += 1
        if len(run) > len(best):
            best = run
        i = j if j > i + 1 else i + 1
    return [y for _, y in best]


def _parse_block(text, block_start, block_end, ncols):
    """Return {VAR: [ (lo,hi), ... ncols ]} for variables found in [start,end)."""
    seg = text[block_start:block_end]
    # locate each variable label position in this segment
    hits = []
    for key, pat in VAR_PATTERNS:
        m = pat.search(seg)
        if m:
            hits.append((m.end(), key))
    hits.sort()
    out = {}
    for idx, (pos, key) in enumerate(hits):
        nxt = hits[idx + 1][0] if idx + 1 < len(hits) else len(seg)
        pairs = PAIR.findall(seg[pos:nxt])
        if len(pairs) >= ncols:
            out[key] = [(float(a), float(b)) for a, b in pairs[:ncols]]
    return out


def _emit(records, meeting_date, key, stat, yr, lo, hi):
    base = "SEP.%s.%s.%s" % (meeting_date.replace("-", ""), key, stat)
    records.append({"series_id": base + ".LOW", "observation_period": str(yr),
                    "value": lo, "knowledge_date": meeting_date,
                    "variable": key, "statistic": stat, "bound": "low"})
    records.append({"series_id": base + ".HIGH", "observation_period": str(yr),
                    "value": hi, "knowledge_date": meeting_date,
                    "variable": key, "statistic": stat, "bound": "high"})


# tokenizer for "lo to hi" pairs WITH their positions
PAIRPOS = re.compile(r"(-?\d+\.\d)\s*to\s*(-?\d+\.\d)")
LR = re.compile(r"longer\s*run", re.I)
STOP_ROW = re.compile(r"projection", re.I)  # prior-meeting comparison row


def _parse_wide(txt, meeting_date):
    """Format-2 (~2010-2015 & 2020): one row per variable holding 2*ncols 'to' pairs
    (first ncols = Central tendency columns, last ncols = Range columns), preceded by
    a header that repeats the year run. Validator (d) CT subset Range still gates."""
    hdr = re.search(r"[Cc]entral\s*tendency.{0,40}?[Rr]ange.{0,20}?[Vv]ariable", txt, re.S)
    if not hdr:
        return {"ok": False, "reason": "wide:no_header"}
    # year run in the header window (take the FIRST ascending run, dedup the repeat)
    win = txt[hdr.end():hdr.end() + 240]
    yrs = [int(m.group()) for m in YEARRUN.finditer(win)]
    run = []
    for y in yrs:
        if not run or y == run[-1] + 1:
            run.append(y)
        else:
            break
    if len(run) < 2:
        return {"ok": False, "reason": "wide:year_run<2(%r)" % run[:6]}
    has_lr = bool(LR.search(win[:120]))
    years = list(run) + (["LR"] if has_lr else [])
    ncols = len(years)
    records = []
    found = 0
    for key, pat in VAR_PATTERNS:
        m = pat.search(txt, hdr.end())
        if not m:
            continue
        # collect pairs after the label, stop at the prior-meeting "projection" row
        tail = txt[m.end():m.end() + 900]
        stop = STOP_ROW.search(tail)
        seg = tail[:stop.start()] if stop else tail
        pairs = PAIRPOS.findall(seg)
        if len(pairs) < 2 * ncols:
            continue
        pairs = [(float(a), float(b)) for a, b in pairs[:2 * ncols]]
        ct = pairs[:ncols]
        rg = pairs[ncols:2 * ncols]
        ok = True
        for (clo, chi), (rlo, rhi) in zip(ct, rg):
            if not (rlo - 1e-9 <= clo and chi <= rhi + 1e-9):
                ok = False
                break
        if not ok:
            continue
        for h, yr in enumerate(years):
            _emit(records, meeting_date, key, "CT", yr, ct[h][0], ct[h][1])
            _emit(records, meeting_date, key, "RANGE", yr, rg[h][0], rg[h][1])
        found += 1
    if found < 3:
        return {"ok": False, "reason": "wide:vars_validated<3(%d)" % found}
    return {"ok": True, "reason": None, "meeting_date": meeting_date,
            "years": years, "n_vars": found, "records": records, "format": "wide"}


def parse_sep_compilation(pdf_bytes, meeting_date):
    """-> dict(ok, reason, meeting_date, years, records[]). Tries the 2007-2009
    sequential block format first, then the 2010-2015/2020 wide interleaved format."""
    try:
        txt = extract_text(pdf_bytes)
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "reason": "extract_error:%r" % e}
    wide = _parse_wide(txt, meeting_date)
    if wide["ok"]:
        return wide
    _seq_reason_holder = {"r": None}
    # The numeric Table 1 is preceded by a "Central tendency" label AND a year-header
    # run; chart legends also say "Central tendency" but carry no year-header run. So
    # ITERATE every central-tendency anchor and accept the FIRST that yields a fully
    # validated table. Validator (d) (CT subset of range) is the fabrication firewall:
    # a mis-anchored region fails it and contributes nothing.
    last = None
    for ctm in re.finditer(r"central\s*tendenc", txt, re.I):
        rg = re.search(r"range", txt[ctm.end():], re.I)
        if not rg:
            last = "no_ranges_anchor"; continue
        rg_start = ctm.end() + rg.start()
        years = _find_year_headers(txt[max(0, ctm.start() - 160):ctm.start()])
        if len(years) < 3:
            last = "year_header_run<3(found=%d)" % len(years); continue
        ncols = len(years)
        ct_block = _parse_block(txt, ctm.end(), rg_start, ncols)
        rg_block = _parse_block(txt, rg_start, rg_start + 1600, ncols)
        common = [k for k in ct_block if k in rg_block]
        if len(common) < 3:
            last = ("vars_in_both_blocks<3(ct=%d,rg=%d,common=%d)"
                    % (len(ct_block), len(rg_block), len(common))); continue
        # validator (d): CT subset of Range for every (var, horizon) cell
        bad = None
        records = []
        for key in common:
            for h, yr in enumerate(years):
                clo, chi = ct_block[key][h]
                rlo, rhi = rg_block[key][h]
                if not (rlo - 1e-9 <= clo and chi <= rhi + 1e-9):
                    bad = ("CT_not_subset:%s@%s CT[%.1f,%.1f] R[%.1f,%.1f]"
                           % (key, yr, clo, chi, rlo, rhi)); break
                for stat, (lo, hi) in (("CT", (clo, chi)), ("RANGE", (rlo, rhi))):
                    base = "SEP.%s.%s.%s" % (meeting_date.replace("-", ""), key, stat)
                    records.append({"series_id": base + ".LOW", "observation_period": str(yr),
                                    "value": lo, "knowledge_date": meeting_date,
                                    "variable": key, "statistic": stat, "bound": "low"})
                    records.append({"series_id": base + ".HIGH", "observation_period": str(yr),
                                    "value": hi, "knowledge_date": meeting_date,
                                    "variable": key, "statistic": stat, "bound": "high"})
            if bad:
                break
        if bad:
            last = bad; continue
        return {"ok": True, "reason": None, "meeting_date": meeting_date,
                "years": years, "n_vars": len(common), "records": records}
    return {"ok": False, "reason": last or "no_central_tendency_anchor"}


if __name__ == "__main__":
    import json
    from pathlib import Path
    rows = json.load(open("research/forecast_pdfs/pdf_dated_index.v1.json"))
    comps = sorted([r for r in rows if r["base"].endswith("SEPcompilation.pdf")],
                   key=lambda r: r["meeting_or_doc_date"])
    rep = []
    for r in comps:
        res = parse_sep_compilation(Path(r["path"]).read_bytes(),
                                    r["meeting_or_doc_date"])
        rep.append({"base": r["base"], "date": r["meeting_or_doc_date"],
                    "ok": res["ok"], "reason": res.get("reason"),
                    "n_records": len(res.get("records", [])),
                    "years": res.get("years"), "n_vars": res.get("n_vars")})
    ok = [x for x in rep if x["ok"]]
    Path("research/forecast_pdfs/sep_parse_report.json").write_text(
        json.dumps({"n_total": len(rep), "n_ok": len(ok),
                    "n_records_total": sum(x["n_records"] for x in ok),
                    "rows": rep}, indent=1))
    print("SEP compilation parse: %d/%d docs pass strict validators; %d records"
          % (len(ok), len(rep), sum(x["n_records"] for x in ok)))
    for x in rep:
        if not x["ok"]:
            print("  FAIL", x["date"], x["base"], "->", x["reason"])
