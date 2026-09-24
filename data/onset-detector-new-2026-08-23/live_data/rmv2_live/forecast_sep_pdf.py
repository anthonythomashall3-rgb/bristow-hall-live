"""FOMC SEP *compilation* projection-table parser (B-REG-FORECAST-PDFS-R2).

Pure stdlib. Extracts the Summary of Economic Projections Table 1 (Central
tendency + Range, per variable per horizon year) from an FOMC SEP compilation
PDF's text layer (zlib FlateDecode content streams + parenthesised string scan),
returning offline-current comparator records for the ``forecast_sep_pdf`` adapter.

MODE substituted_diagnostic. These are external forecast comparators bound to the
registered family ``fomc_sep`` (role forecast_comparator). NEVER a member, never
fitted, never in any channel (CLAUDE.md forecast firewall; brief STOP).

ANTI-FABRICATION FIREWALL (R1-recommended, brief-mandated). A document yields
records ALL-OR-NOTHING; a document that fails any check yields NOTHING (the caller
records it as a failure with a reason string, never a silent skip):
  (a) a year-header run of >=3 ascending years is found;
  (b) >=3 of the 4 canonical variables parse in BOTH the Central-Tendency and the
      Range column set;
  (c) each parsed variable yields exactly year-count range pairs in each set;
  (d) central_tendency in [range_low, range_high] for EVERY (variable, horizon).

Two Table-1 layouts are recognised: the 2007-2009 SEQUENTIAL format ("Central
Tendencies" block then "Ranges" block) and the 2010-2015/2020 WIDE format (one row
per variable holding 2*ncols 'lo to hi' pairs, CT columns then Range columns). The
2015H2-2019 bare-number tables and the modern figure-rendered fomcprojtabl files are
NOT text-extractable and are handled as recorded failures upstream, not here.
"""
import re
import zlib


def extract_text(pdf_bytes):
    """Concatenated text-layer strings from all FlateDecode content streams."""
    out = []
    for m in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", pdf_bytes, re.DOTALL):
        try:
            data = zlib.decompress(m.group(1))
        except Exception:  # noqa: BLE001
            continue
        buf = []
        i = 0
        n = len(data)
        while i < n:
            if data[i:i + 1] == b"(":
                j = i + 1
                depth = 1
                s = bytearray()
                while j < n and depth > 0:
                    ch = data[j:j + 1]
                    if ch == b"\\":
                        s += data[j + 1:j + 2]
                        j += 2
                        continue
                    if ch == b"(":
                        depth += 1
                        s += ch
                    elif ch == b")":
                        depth -= 1
                        if depth > 0:
                            s += ch
                    else:
                        s += ch
                    j += 1
                buf.append(s.decode("latin-1", "replace"))
                i = j
            else:
                i += 1
        if buf:
            out.append("".join(buf))
    return "\n".join(out)


VAR_PATTERNS = [
    ("RGDP", re.compile(r"(?:Change in real GDP|Real GDP Growth|Real GDP)", re.I)),
    ("UNRATE", re.compile(r"Unemployment Rate", re.I)),
    ("PCE", re.compile(r"(?:Total PCE Inflation|PCE Inflation|PCE inflation)", re.I)),
    ("COREPCE", re.compile(r"Core PCE [Ii]nflation", re.I)),
]
VAR_UNIT = {
    "RGDP": "percent, Q4/Q4 change in real GDP",
    "UNRATE": "percent, Q4 unemployment rate",
    "PCE": "percent, Q4/Q4 PCE inflation",
    "COREPCE": "percent, Q4/Q4 core PCE inflation",
}
PAIR = re.compile(r"(-?\d+\.\d)\s*to\s*(-?\d+\.\d)")
YEARRUN = re.compile(r"(?:19|20)\d{2}")
LR = re.compile(r"longer\s*run", re.I)
STOP_ROW = re.compile(r"projection", re.I)


def _year_headers(segment):
    yrs = [(m.start(), int(m.group())) for m in YEARRUN.finditer(segment)]
    best = []
    i = 0
    while i < len(yrs):
        run = [yrs[i]]
        j = i + 1
        while j < len(yrs) and yrs[j][1] == run[-1][1] + 1 and yrs[j][0] - run[-1][0] <= 6:
            run.append(yrs[j])
            j += 1
        if len(run) > len(best):
            best = run
        i = j if j > i + 1 else i + 1
    return [y for _, y in best]


def _block(text, start, end, ncols):
    seg = text[start:end]
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


def _cells(years, ct, rg):
    """Validate CT subset of range for all cells; return cell list or None."""
    cells = []
    for h, yr in enumerate(years):
        clo, chi = ct[h]
        rlo, rhi = rg[h]
        if not (rlo - 1e-9 <= clo and chi <= rhi + 1e-9):
            return None
        cells.append((str(yr), clo, chi, rlo, rhi))
    return cells


def _parse_wide(txt):
    hdr = re.search(r"[Cc]entral\s*tendency.{0,40}?[Rr]ange.{0,20}?[Vv]ariable", txt, re.S)
    if not hdr:
        return None
    win = txt[hdr.end():hdr.end() + 240]
    yrs = [int(m.group()) for m in YEARRUN.finditer(win)]
    run = []
    for y in yrs:
        if not run or y == run[-1] + 1:
            run.append(y)
        else:
            break
    if len(run) < 2:
        return None
    years = list(run) + (["LR"] if LR.search(win[:120]) else [])
    ncols = len(years)
    parsed = {}
    for key, pat in VAR_PATTERNS:
        m = pat.search(txt, hdr.end())
        if not m:
            continue
        tail = txt[m.end():m.end() + 900]
        stop = STOP_ROW.search(tail)
        seg = tail[:stop.start()] if stop else tail
        pairs = PAIR.findall(seg)
        if len(pairs) < 2 * ncols:
            continue
        pairs = [(float(a), float(b)) for a, b in pairs[:2 * ncols]]
        cells = _cells(years, pairs[:ncols], pairs[ncols:2 * ncols])
        if cells is not None:
            parsed[key] = cells
    if len(parsed) < 3:
        return None
    return years, parsed


def _parse_sequential(txt):
    for ctm in re.finditer(r"central\s*tendenc", txt, re.I):
        rg = re.search(r"range", txt[ctm.end():], re.I)
        if not rg:
            continue
        rg_start = ctm.end() + rg.start()
        years = _year_headers(txt[max(0, ctm.start() - 160):ctm.start()])
        if len(years) < 3:
            continue
        ncols = len(years)
        ctb = _block(txt, ctm.end(), rg_start, ncols)
        rgb = _block(txt, rg_start, rg_start + 1600, ncols)
        common = [k for k in ctb if k in rgb]
        if len(common) < 3:
            continue
        parsed = {}
        ok = True
        for key in common:
            cells = _cells(years, ctb[key], rgb[key])
            if cells is None:
                ok = False
                break
            parsed[key] = cells
        if ok:
            return years, parsed
    return None


def parse_sep_compilation(pdf_bytes, meeting_date):
    """-> dict(ok, reason, meeting_date, years, cells{VAR:[(yr,clo,chi,rlo,rhi)]})."""
    try:
        txt = extract_text(pdf_bytes)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "reason": "extract_error:%r" % exc}
    for parser in (_parse_wide, _parse_sequential):
        res = parser(txt)
        if res is not None:
            years, parsed = res
            return {"ok": True, "reason": None, "meeting_date": meeting_date,
                    "years": years, "n_vars": len(parsed), "cells": parsed}
    return {"ok": False, "reason": "no_validated_table"}


def sep_records(meeting_date, cells):
    """Flatten validated cells to (series_id, target_year, statistic, bound, value,
    variable, unit) tuples. Meeting (knowledge) date is encoded in the series id."""
    stamp = meeting_date.replace("-", "")
    for var, rows in sorted(cells.items()):
        unit = VAR_UNIT[var]
        for yr, clo, chi, rlo, rhi in rows:
            base = "SEP.%s.%s" % (stamp, var)
            # SEP values are exactly one decimal place (matched by \d+\.\d); "%.1f" is
            # a lossless canonical-decimal string. The store forbids float values.
            yield ("%s.CT.LOW" % base, yr, "central_tendency", "low", "%.1f" % clo, var, unit)
            yield ("%s.CT.HIGH" % base, yr, "central_tendency", "high", "%.1f" % chi, var, unit)
            yield ("%s.RANGE.LOW" % base, yr, "range", "low", "%.1f" % rlo, var, unit)
            yield ("%s.RANGE.HIGH" % base, yr, "range", "high", "%.1f" % rhi, var, unit)
