#!/usr/bin/env python3
"""Parse the housing table (permits + starts, SAAR monthly rows) from each Economic
Indicators housing page saved by find_pages.py.

Two independent OCR reads of the same scanned page:
  A = the ABBYY FineReader text layer FRASER embedded in the PDF (word boxes via pymupdf)
  T = tesseract 5 on a 400-dpi render of the table region (word boxes via TSV)
Both reads go through the same row/column logic:
  1. words -> rows (y-clustering after de-skew)
  2. SAAR block = rows below the "Seasonally adjusted annual rates" banner that carry a
     month label; the year label ("1962:") anchors the months; months must be consecutive
  3. numeric tokens merged ("1," + "383" -> 1383, "128." + "2" -> 128.2), assigned to
     columns by clustering right edges (tables are right-aligned)
  4. starts column  = leftmost column with SAAR magnitude (median > 300)
     permits column = SAAR-magnitude column (not starts) whose values track today's
     Census PERMIT best (min std of log ratio); cross-checked against the header word
     "author-"/"authorized" position when found.
Output: parsed/<issue>_{A,T}.csv and a combined parsed/reads.csv (one row per issue x month x engine).
"""
import csv, glob, json, os, re, subprocess, sys, tempfile
import numpy as np
import pandas as pd
import pymupdf as fitz

HERE = os.path.dirname(os.path.abspath(__file__))
PAGES = os.path.join(HERE, "raw", "pages")
OUTD = os.path.join(HERE, "parsed")
os.makedirs(OUTD, exist_ok=True)

FRED_P = pd.read_csv(os.path.join(HERE, "ref", "PERMIT_current.csv"), index_col=0, parse_dates=True).iloc[:, 0]
FRED_H = pd.read_csv(os.path.join(HERE, "ref", "HOUST_current.csv"), index_col=0, parse_dates=True).iloc[:, 0]
FRED_C = pd.read_csv(os.path.join(HERE, "ref", "COMPUTSA_current.csv"), index_col=0, parse_dates=True).iloc[:, 0]
FRED_1F = pd.read_csv(os.path.join(HERE, "ref", "HOUST1F_current.csv"), index_col=0, parse_dates=True).iloc[:, 0]

ISSUE_HINT = None   # issue month as year*12+month-1, set by main()
MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
MONTH_RX = [
    r"^j[a-z]{0,2}n", r"^f[ce][bh]?|^fob|^feb", r"^m[a-z]?r", r"^a[a-z]?[pr]|^aur|^apr", r"^ma[yv]|^may",
    r"^jun|^june", r"^jul|^july", r"^au[gs]?|^aug", r"^se[pt]?|^sept|^scp", r"^o[ce]t|^oct|^0ct", r"^no[vy]|^nov",
    r"^de[ce]|^dec"]


def month_of(label):
    s = label.lower().replace("0", "o").replace("1", "l")
    s = re.sub(r"[^a-z]", "", s)
    if not s:
        return None
    # disambiguate the J months and the M/A months
    if s.startswith("jan") or s.startswith("jah") or s.startswith("ja"):
        return 1
    if s.startswith("jun") or s.startswith("jum") or s.startswith("jnn"):
        return 6
    if s.startswith("jul") or s.startswith("ju") and len(s) >= 3 and s[2] in "li":
        return 7
    if s.startswith("fe") or s.startswith("fo") or s.startswith("fc") or s.startswith("fb"):
        return 2
    if s.startswith("mar") or s.startswith("mr") or s.startswith("mai"):
        return 3
    if s.startswith("may") or s.startswith("mav") or s.startswith("ma") and len(s) == 2:
        return 5
    if s.startswith("ap") or s.startswith("ar") or s.startswith("aur") or s.startswith("aj"):
        return 4
    if s.startswith("au") or s.startswith("ag"):
        return 8
    if s.startswith("se") or s.startswith("sc") or s.startswith("sp"):
        return 9
    if s.startswith("oc") or s.startswith("oe") or s.startswith("ot"):
        return 10
    if s.startswith("no") or s.startswith("nv"):
        return 11
    if s.startswith("de") or s.startswith("dc"):
        return 12
    return None


# ---------------------------------------------------------------- word sources
def words_abbyy(pdfpath):
    d = fitz.open(pdfpath)
    p = d[0]
    ws = [(w[0], w[1], w[2], w[3], w[4]) for w in p.get_text("words")]
    return ws, (p.rect.width, p.rect.height)


def words_tess(pdfpath, dpi=400, clip=None):
    d = fitz.open(pdfpath)
    p = d[0]
    scale = dpi / 72.0
    mat = fitz.Matrix(scale, scale)
    pix = p.get_pixmap(matrix=mat, clip=clip, colorspace=fitz.csGRAY)
    ox, oy = (clip.x0, clip.y0) if clip is not None else (0, 0)
    with tempfile.TemporaryDirectory() as td:
        img = os.path.join(td, "p.png")
        pix.save(img)
        r = subprocess.run(["tesseract", img, "stdout", "--psm", "6", "-c", "preserve_interword_spaces=1", "tsv"],
                           capture_output=True, text=True)
    ws = []
    for line in r.stdout.splitlines()[1:]:
        f = line.split("\t")
        if len(f) < 12 or f[11].strip() == "":
            continue
        l, t, w, h = map(int, f[6:10])
        ws.append((ox + l / scale, oy + t / scale, ox + (l + w) / scale, oy + (t + h) / scale, f[11]))
    return ws


# ---------------------------------------------------------------- rows
def group_rows(ws, tol=3.2):
    """cluster words into text rows by y-centre, after estimating page skew"""
    if not ws:
        return []
    def cluster(ws, slope):
        items = sorted(ws, key=lambda w: ((w[1] + w[3]) / 2 - slope * w[0]))
        rows = []
        for w in items:
            yc = (w[1] + w[3]) / 2 - slope * w[0]
            if rows and abs(rows[-1]["y"] - yc) < tol:
                rows[-1]["w"].append(w)
                n = len(rows[-1]["w"])
                rows[-1]["y"] = rows[-1]["y"] + (yc - rows[-1]["y"]) / n
            else:
                rows.append({"y": yc, "w": [w]})
        for r in rows:
            r["w"].sort(key=lambda w: w[0])
        return rows
    rows = cluster(ws, 0.0)
    slopes = []
    for r in rows:
        if len(r["w"]) >= 8:
            xs = np.array([(w[0] + w[2]) / 2 for w in r["w"]])
            ys = np.array([(w[1] + w[3]) / 2 for w in r["w"]])
            if np.ptp(xs) > 150:
                slopes.append(np.polyfit(xs, ys, 1)[0])
    slope = float(np.median(slopes)) if slopes else 0.0
    if abs(slope) > 0.002:
        rows = cluster(ws, slope)
    return rows


NUMCHARS = str.maketrans({"O": "0", "o": "0", "D": "0", "Q": "0", "l": "1", "I": "1", "i": "1", "|": "1",
                          "]": "1", "[": "1", "!": "1", "S": "5", "s": "5", "B": "8", "Z": "2", "z": "2",
                          "G": "6", "b": "6", "g": "9", "q": "9", "T": "7", "A": "4"})


def clean_num_token(t):
    """normalise an OCR token that should be (part of) a number; returns (string, n_substitutions)"""
    t0 = t.strip("_-—–~'\"`*•·:;")
    # revised / preliminary marks printed against a figure ('r988', '1,146p')
    t0 = re.sub(r"^[rpP](?=[\d,])", "", t0)
    t0 = re.sub(r"(?<=\d)[rpP]$", "", t0)
    if not t0:
        return None, 0
    if re.fullmatch(r"[Il\]\[|!i][,.]", t0):
        return "1" + t0[-1], 1
    subs = sum(1 for ch in t0 if ch in "OoDQlIi|][!SsBZzGbgqTA")
    t1 = t0.translate(NUMCHARS)
    if re.fullmatch(r"[\d.,]+", t1) and re.search(r"\d", t1):
        # letters allowed only if the token is mostly digits
        if subs and subs * 2 >= len(t1):
            return None, 0
        return t1, subs
    return None, 0


def merge_numbers(tokens, gap_max=7.5):
    """tokens: list of (x0,y0,x1,y1,text) sorted by x. returns list of dicts (x0,x1,raw,val,subs)."""
    items = []
    for w in tokens:
        s, subs = clean_num_token(w[4])
        items.append((w, s, subs))
    out = []
    i = 0
    while i < len(items):
        w, s, subs = items[i]
        if s is None:
            out.append({"x0": w[0], "x1": w[2], "y0": w[1], "y1": w[3], "raw": w[4], "txt": None, "subs": 0})
            i += 1
            continue
        cur = {"x0": w[0], "x1": w[2], "y0": w[1], "y1": w[3], "raw": w[4], "txt": s, "subs": subs}
        while i + 1 < len(items):
            w2, s2, subs2 = items[i + 1]
            if s2 is None:
                break
            gap = w2[0] - cur["x1"]
            a = cur["txt"]
            join = False
            if gap < gap_max:
                if re.fullmatch(r"\d{1,3}[.,]", a) and re.fullmatch(r"\d{1,3}(\.\d)?", s2):
                    join = True           # "1," + "383"  /  "128." + "2"  / "1," + "383.5"
                elif re.fullmatch(r"\d{1,3}", a) and re.fullmatch(r"[.,]\d{1,3}(\.\d)?", s2):
                    join = True           # "1" + ",383"
                elif re.fullmatch(r"\d", a) and re.fullmatch(r"\d{3}(\.\d)?", s2) and gap < 5.5:
                    join = True           # "1" + "383" (comma lost)
                elif re.fullmatch(r"\d{1,3}", a) and re.fullmatch(r"\d", s2) and gap < 4.5 and False:
                    join = True
            if not join:
                break
            cur["x1"] = w2[2]
            cur["y0"] = min(cur["y0"], w2[1]); cur["y1"] = max(cur["y1"], w2[3])
            cur["raw"] += " " + w2[4]
            cur["txt"] = a + s2
            cur["subs"] += subs2
            i += 1
        out.append(cur)
        i += 1
    for o in out:
        o["val"] = to_value(o["txt"]) if o["txt"] else None
    return out


def to_value(t):
    t = t.strip(".,")
    if not t:
        return None
    # thousands comma: 1,383 or 1.383 (OCR) ; decimal: 128.2
    m = re.fullmatch(r"(\d{1,2})[.,](\d{3})(?:[.,](\d))?", t)
    if m:
        v = float(m.group(1) + m.group(2))
        if m.group(3):
            v += int(m.group(3)) / 10
        return v
    m = re.fullmatch(r"(\d{1,4})[.,](\d)", t)
    if m:
        return float(m.group(1)) + int(m.group(2)) / 10
    m = re.fullmatch(r"\d{1,4}", t)
    if m:
        return float(t)
    return None


# ---------------------------------------------------------------- table
def row_text(r):
    return " ".join(w[4] for w in r["w"])


BANNER_RX = r"adj[a-z.]*annu|annu[a-z!.]*ra[t!]|onal[a-z.]*adj[a-z.]*an|easonal[a-z.]*adj"


def banner_rows(rows):
    """indices of rows that look like a 'Seasonally adjusted annual rates' banner"""
    out = []
    for i, r in enumerate(rows):
        t = row_text(r).lower().replace(" ", "")
        if re.search(BANNER_RX, t) and len(r["w"]) <= 8:
            out.append(i)
    return out


def find_saar_block(rows, label_xmax=None):
    b = banner_rows(rows)
    return b[0] + 1 if b else None


def parse_rows(rows, label_xmax, start=0):
    """identify monthly rows (from rows[start:]): [(year or None, month, label_raw, numeric items)]"""
    out = []
    for r in rows[start:]:
        lab = [w for w in r["w"] if w[0] < label_xmax]
        rest = [w for w in r["w"] if w[0] >= label_xmax]
        labtxt = " ".join(w[4] for w in lab)
        nums = merge_numbers(rest)
        nvals = [n for n in nums if n["val"] is not None]
        words = [w[4] for w in r["w"] if re.fullmatch(r"[A-Za-z][a-z]{3,}[.,;:]?", w[4])]
        if len(words) >= 2 and len(out) >= 4 and not month_of(labtxt or "x"):
            break                      # footnotes / notes reached
        if len(words) >= 3 and len(out) >= 4:
            break
        ym = re.search(r"(19[4-9]\d)", labtxt.replace(" ", "").replace("I9", "19").replace("l9", "19"))
        year = int(ym.group(1)) if ym else None
        if year and not out and not re.search(r"19[4-9]\d\s*[:;\-]", labtxt) and not month_of(re.sub(r"[\d\W_]", "", labtxt) or "x"):
            continue                   # an annual-total row above the monthly block
        mtxt = re.sub(r"(19[4-9]\d)\s*:?", "", labtxt).strip()
        mon = month_of(mtxt) if mtxt else None
        if mon is None and year is None:
            if len(nvals) >= 4 and out:
                out.append({"year": None, "month": None, "label": labtxt, "nums": nums, "y": r["y"], "w": r["w"]})
            continue
        if len(nvals) == 0:
            continue
        out.append({"year": year, "month": mon, "label": labtxt, "nums": nums, "y": r["y"], "w": r["w"]})
    return out, None


def label_boundary(rows):
    """x position separating the row label from the first data column: the left edge of the
    first merged number (value >= 10) after the month word, on rows labelled like '1962: Jan'"""
    xs, xs2 = [], []
    for r in rows:
        ws = r["w"]
        if len(ws) < 4:
            continue
        t0 = ws[0][4]
        if not re.fullmatch(r"[1Il]9[4-9]\d[:;.]?", t0):
            continue
        k = None
        for j in (1, 2):
            if j < len(ws) and re.match(r"[A-Za-z]{2,}", ws[j][4]) and month_of(ws[j][4]):
                k = j
                break
        start = k + 1 if k is not None else 1
        for n in merge_numbers(ws[start:]):
            if n["val"] is not None and n["val"] >= 10 and n["x0"] - ws[start - 1][2] > 4:
                (xs if k is not None else xs2).append(n["x0"])
                break
    # right edge of the month words: the first data column is right-aligned, so a wider number
    # ('1,066' under '860') starts left of the first number seen on the year rows
    labx = []
    for r in rows:
        ws = r["w"]
        for j in range(min(3, len(ws))):
            if re.match(r"[A-Za-z]{3,}", ws[j][4]) and month_of(ws[j][4]):
                labx.append(ws[j][2])
                break
    xs = xs or xs2
    if xs and labx:
        lx_num = float(np.median(xs)) - 4
        lx_lab = float(np.median(labx)) + 2
        return min(lx_num, max(lx_lab, lx_num - 25))
    if not xs:
        # year labels unreadable: use rows that start with a month word
        for r in rows:
            ws = r["w"]
            if len(ws) < 5 or not re.match(r"[A-Za-z]{3,}", ws[0][4]) or not month_of(ws[0][4]):
                continue
            for n in merge_numbers(ws[1:]):
                if n["val"] is not None and n["val"] >= 10 and n["x0"] - ws[0][2] > 4:
                    xs.append(n["x0"])
                    break
        if len(xs) < 4:
            return None
    return float(np.median(xs)) - 4


def row_steps(prow):
    """month offset of each row from the first, from the row y-positions (rows are evenly
    spaced; a row lost in OCR leaves a double gap instead of shifting later months)"""
    ys = [r["y"] for r in prow]
    if len(ys) < 3:
        return list(range(len(ys)))
    d = np.diff(ys)
    pitch = float(np.median(d))
    if pitch <= 0:
        return list(range(len(ys)))
    ks = [0]
    for i in range(1, len(ys)):
        step = max(1, int(round((ys[i] - ys[i - 1]) / pitch)))
        ks.append(ks[-1] + step)
    return ks


def assign_months(prow):
    """two hypotheses for the month offsets of the rows -- strictly consecutive, or from the row
    spacing (a row lost in OCR leaves a double gap) -- each scored against the OCR'd month words
    and year labels; the better-scoring one is used (ties: consecutive)"""
    a1 = _assign_months(prow, list(range(len(prow))))
    ks = row_steps(prow)
    if ks == list(range(len(prow))):
        return a1[0], a1[1]
    a2 = _assign_months(prow, ks)
    if a2[0] is not None and (a1[0] is None or a2[2] > a1[2]):
        return a2[0], a2[1] + " (row-spacing offsets)"
    return a1[0], a1[1]


def _assign_months(prow, ks):
    n = len(prow)
    years = [r["year"] for r in prow if r["year"]]
    gaps = sum(1 for a, b in zip(ks[:-1], ks[1:]) if b - a > 1)
    if not years:
        if ISSUE_HINT is None:
            return None, "no year anchor", -99
        # no readable year label: the newest row must fall 0-3 months before the issue month
        best = None
        for b in range(ISSUE_HINT - 3 - ks[-1], ISSUE_HINT - ks[-1] + 1):
            sc = sum(1 for i, r in enumerate(prow) if r["month"] and r["month"] == (b + ks[i]) % 12 + 1)
            if best is None or sc > best[0]:
                best = (sc, b)
        nlab = sum(1 for r in prow if r["month"])
        if best[0] < max(3, 0.6 * nlab):
            return None, "no year anchor", -99
        b = best[1]
        ym = [((b + k) // 12, (b + k) % 12 + 1) for k in ks]
        return ym, f"labels agree {best[0]} (no year label; months anchored on issue date) gaps={gaps}", best[0]
    best = None
    for Y in set(years):
        for b in range((Y - 2) * 12, (Y + 2) * 12):
            sc = 0
            ymatch = 0
            for i, r in enumerate(prow):
                k = b + ks[i]
                if r["month"] and r["month"] == k % 12 + 1:
                    sc += 1
                if r["year"]:
                    if r["year"] == k // 12:
                        sc += 2
                        ymatch += 1
                    else:
                        sc -= 2
            if ymatch and (best is None or sc > best[0]):
                best = (sc, b)
    if best is None:
        return None, "no year anchor", -99
    b = best[1]
    ym = [((b + k) // 12, (b + k) % 12 + 1) for k in ks]
    agree = sum(1 for i, r in enumerate(prow) if r["month"] and r["month"] == ym[i][1])
    dis = sum(1 for i, r in enumerate(prow) if r["month"] and r["month"] != ym[i][1])
    return ym, f"labels agree {agree} disagree {dis} gaps={gaps}", best[0]


def column_centres(prow):
    xs = sorted(n["x1"] for r in prow for n in r["nums"] if n["val"] is not None)
    if not xs:
        return []
    clusters = [[xs[0]]]
    for x in xs[1:]:
        if x - clusters[-1][-1] > 7:
            clusters.append([x])
        else:
            clusters[-1].append(x)
    return [float(np.median(c)) for c in clusters if len(c) >= max(2, len(prow) // 4)]


def build_table(prow, ym):
    cents = column_centres(prow)
    if not cents:
        return [], []
    tab = []
    for r, k in zip(prow, ym):
        cells = {}
        for n in r["nums"]:
            if n["val"] is None:
                continue
            j = int(np.argmin([abs(n["x1"] - c) for c in cents]))
            if abs(n["x1"] - cents[j]) > 9:
                continue
            if j in cells:  # two tokens in one column: keep the wider, flag
                cells[j]["dup"] = True
                continue
            cells[j] = dict(n)
        tab.append({"ym": k, "label": r["label"], "cells": cells, "y": r["y"], "w": r["w"]})
    return cents, tab


def _fit(tab, j, ref):
    lr = []
    for t in tab:
        if j in t["cells"]:
            y, m = t["ym"]
            d = pd.Timestamp(y, m, 1)
            v = t["cells"][j]["val"]
            if d in ref.index and v and v > 0:
                lr.append(np.log(v / ref[d]))
    if len(lr) < 4:
        return None
    lr = np.array(lr)
    lvl = float(np.median(lr))
    # robust spread: median absolute deviation (single OCR slips do not dominate)
    sd = float(np.median(np.abs(lr - lvl))) * 1.4826
    return round(sd, 4), round(lvl, 4)


def pick_columns(cents, tab, header_author_x=None):
    """starts = leftmost SAAR-magnitude column; permits = the column the 'author-' header sits
    over when that column tracks today's Census PERMIT, else the column that tracks PERMIT best
    and does not track completions / 1-unit starts better"""
    ncol = len(cents)
    med = []
    for j in range(ncol):
        v = [t["cells"][j]["val"] for t in tab if j in t["cells"]]
        med.append(np.median(v) if len(v) >= 3 else 0)
    saar = [j for j in range(ncol) if 300 < med[j] < 4000]
    if not saar:
        return None, None, "no SAAR-magnitude column", {}
    starts = saar[0]
    diag, ok = {}, []
    for j in saar:
        if j == starts:
            continue
        fp = _fit(tab, j, FRED_P)
        if fp is None:
            continue
        diag[j] = fp
        if fp[0] > 0.12 or abs(fp[1]) > 0.2:
            continue
        rivals = [f for f in (_fit(tab, j, FRED_C), _fit(tab, j, FRED_1F), _fit(tab, j, FRED_H)) if f is not None]
        if any(f[0] + 0.5 * abs(f[1]) < 0.8 * (fp[0] + 0.5 * abs(fp[1])) for f in rivals):
            diag[j] = fp + ("fits_other_series",)
            continue
        ok.append(j)
    jh = int(np.argmin([abs(c - header_author_x) for c in cents])) if header_author_x is not None else None
    note = f"diag={diag} header_col={jh}"
    if jh is not None and jh in ok:
        return starts, jh, note + " ->header", diag
    if ok:
        permits = min(ok, key=lambda j: diag[j][0] + 0.5 * abs(diag[j][1]))
        if jh is not None:
            note += " HEADER_MISMATCH"
        return starts, permits, note + " ->fit", diag
    # nothing tracks PERMIT well: fall back to header column if it is SAAR-magnitude
    if jh is not None and jh in saar and jh != starts:
        return starts, jh, note + " WEAK ->header", diag
    return starts, None, note + " NO_PERMITS_COLUMN", diag


def header_author_x(rows):
    for r in rows:
        for w in r["w"]:
            if re.match(r"(?i)author|authori|ized", w[4]):
                return (w[0] + w[2]) / 2 + 6
    return None


def flag_from_label(label):
    s = label.strip()
    s = re.sub(r"19\d\d\s*:?", "", s).strip()
    m = re.search(r"(?:^|[\s._\-])([pr])[\s._\-]*$|[a-z]\s+([pr])\b", s)
    if re.search(r"\s[pP][\s._\-]*$|\s[pP]\s", " " + s + " "):
        return "p"
    if re.search(r"\s[rR][\s._\-]*$|\s[rR]\.?\s", " " + s + " "):
        return "r"
    return ""


def parse_block(rows, bi):
    """parse the table whose SAAR banner is rows[bi]; returns (res, note, score)"""
    block = rows[bi + 1: bi + 28]
    lx = label_boundary(block)
    if lx is None:
        return None, "no label boundary", 9e9
    prow, err = parse_rows(block, lx)
    if err or not prow:
        return None, err or "no rows", 9e9
    ym, note1 = assign_months(prow)
    if ym is None:
        return None, note1, 9e9
    cents, tab = build_table(prow, ym)
    hx = header_author_x(rows[max(0, bi - 25): bi + 1])
    sc, pc, note2, diag = pick_columns(cents, tab, hx)
    if pc is None:
        return None, f"{note1}; cols={len(cents)} no permits column {note2}", 9e9
    def colgeom(j):
        c = [t["cells"][j] for t in tab if j in t["cells"]]
        return (min(x["x0"] for x in c), max(x["x1"] for x in c)) if c else None
    geo = {"p": colgeom(pc), "s": colgeom(sc) if sc is not None else None}
    ys = sorted(t["y"] for t in tab)
    pitch = float(np.median(np.diff(ys))) if len(ys) > 2 else 8.0
    pitch = min(max(pitch, 6.0), 12.0)

    def cellbox(t, key):
        g = geo[key]
        if g is None:
            return ""
        xl, xr = g
        near = [w for w in t["w"] if abs((w[0] + w[2]) / 2 - (xl + xr) / 2) < 90 and re.search(r"\d", w[4])]
        if not near:
            near = t["w"]
        yc = float(np.median([(w[1] + w[3]) / 2 for w in near]))
        return f"{xl - 2.5:.1f},{yc - 0.5 * pitch:.1f},{xr + 2.5:.1f},{yc + 0.5 * pitch:.1f}"
    res = []
    for t in tab:
        y, m = t["ym"]
        pcell = t["cells"].get(pc)
        scell = t["cells"].get(sc) if sc is not None else None
        res.append({
            "month": f"{y:04d}-{m:02d}",
            "permits": pcell["val"] if pcell else None,
            "permits_raw": pcell["raw"] if pcell else "",
            "permits_subs": pcell["subs"] if pcell else "",
            "starts": scell["val"] if scell else None,
            "starts_raw": scell["raw"] if scell else "",
            "starts_subs": scell["subs"] if scell else "",
            "label_raw": t["label"],
            "flag": flag_from_label(t["label"]),
            "ncols": len(cents),
            "row_y": round(t["y"], 1),
            "pbox": cellbox(t, "p"),
            "sbox": cellbox(t, "s"),
        })
    # prefer the block with the most month rows (a chart caption 'SEASONALLY ADJUSTED ANNUAL
    # RATES' above the table yields a truncated block), then the best PERMIT fit
    score = -len(res) + (diag.get(pc, (1, 1))[0] if pc in diag else 1.0)
    return res, f"{note1}; cols={len(cents)} starts_col={sc} permits_col={pc} {note2}", score


def parse_words(ws):
    rows = group_rows(ws)
    best = (None, "no SAAR banner", 9e9, None)
    cands = banner_rows(rows)
    # fallback anchors: the row just above a 'YYYY: Mon' label (banner garbled or lost in OCR)
    for i, r in enumerate(rows):
        ws = r["w"]
        nxt = rows[i + 1]["w"] if i + 1 < len(rows) and rows[i + 1]["w"] else [(0, 0, 0, 0, "")]
        if i > 0 and len(ws) >= 5 and re.fullmatch(r"[1Il]9[4-9]\d[:;\-]", ws[0][4]) \
                and (month_of(ws[1][4]) or month_of(nxt[0][4])
                     or sum(1 for n in merge_numbers(ws[1:]) if n["val"] is not None and n["val"] >= 10) >= 5) \
                and (i - 1) not in cands and not any(c < i and i - c < 16 for c in cands):
            cands.append(i - 1)
    for bi in sorted(set(cands)):
        res, note, sc = parse_block(rows, bi)
        if res is not None and sc < best[2]:
            best = (res, note, sc, bi)
    return best, rows


def table_clip(pdfpath, res, rows_y_margin=10):
    """page region holding the parsed SAAR rows (for the tesseract read)"""
    d = fitz.open(pdfpath)
    W, H = d[0].rect.width, d[0].rect.height
    ys = [r["row_y"] for r in res]
    return fitz.Rect(0, max(0, min(ys) - 22), W, min(H, max(ys) + rows_y_margin))


def parse_issue(pdfpath, engine, clip=None):
    if engine == "A":
        ws, _ = words_abbyy(pdfpath)
        (res, note, sc, bi), rows = parse_words(ws)
        return res, note
    ws = words_tess(pdfpath, dpi=int(os.environ.get("TESS_DPI", "350")), clip=clip)
    # the clip begins just above the first month row; add a synthetic banner row
    ws = [(0, clip.y0 + 1 if clip else 0, 5, (clip.y0 + 2) if clip else 1, "Seasonally adjusted annual rates")] + ws
    (res, note, sc, bi), rows = parse_words(ws)
    return res, note


CELL_VARIANTS = [(300, 20, 1.0), (450, 20, 0.0), (300, 0, 1.0)]   # (dpi, white pad px, gaussian blur); chosen on a hand-read benchmark page


def ocr_cell(page, box, save=None):
    """tesseract (psm 7, digits only) on a single table cell under three preprocessing
    variants; returns (majority value or None, 'v1|v2|v3')"""
    from PIL import Image, ImageFilter, ImageOps
    x0, y0, x1, y1 = box
    vals, raws = [], []
    for k, (dpi, pad, blur) in enumerate(CELL_VARIANTS):
        scale = dpi / 72.0
        pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), clip=fitz.Rect(x0, y0, x1, y1), colorspace=fitz.csGRAY)
        im = Image.frombytes("L", (pix.width, pix.height), pix.samples)
        if save and k == 1:
            im.save(save)
        if blur:
            im = im.filter(ImageFilter.GaussianBlur(blur))
        if pad:
            im = ImageOps.expand(im, border=pad, fill=255)
        with tempfile.TemporaryDirectory() as td:
            img = os.path.join(td, "c.png")
            im.save(img)
            r = subprocess.run(["tesseract", img, "stdout", "--psm", "7", "-c", "tessedit_char_whitelist=0123456789,.",
                                "-c", "load_system_dawg=0", "-c", "load_freq_dawg=0"], capture_output=True, text=True)
        t = re.sub(r"\s+", "", r.stdout.strip())
        raws.append(t)
        vals.append(to_value(t) if t else None)
        if k == 1 and vals[0] is not None and vals[0] == vals[1]:
            break                      # two variants agree: third not needed
    good = [v for v in vals if v is not None]
    best = None
    if good:
        cnt = {v: good.count(v) for v in good}
        v, c = max(cnt.items(), key=lambda kv: kv[1])
        if c >= 2:
            best = v
    return best, "|".join(raws)


def engine_c(pdfpath, resA, save_dir=None):
    d = fitz.open(pdfpath)
    page = d[0]
    out = []
    for r in resA:
        rec = {k: r[k] for k in ("month", "label_raw", "flag", "ncols", "row_y", "pbox", "sbox")}
        for key, col in (("pbox", "permits"), ("sbox", "starts")):
            if r.get(key):
                box = tuple(float(v) for v in r[key].split(","))
                sv = os.path.join(save_dir, f"{col}_{r['month']}.png") if save_dir else None
                v, raw = ocr_cell(page, box, save=sv)
                rec[col] = v
                rec[col + "_raw"] = raw
            else:
                rec[col] = None
                rec[col + "_raw"] = ""
            rec[col + "_subs"] = ""
        out.append(rec)
    return out


def main(argv):
    pages = sorted(glob.glob(os.path.join(PAGES, "*_p*.pdf")))
    if argv:
        pages = [p for p in pages if any(a in os.path.basename(p) for a in argv)]
    log = []
    allrows = []
    for p in pages:
        iss = os.path.basename(p).split("_")[0]
        mm, yy = iss.split("-")
        global ISSUE_HINT
        ISSUE_HINT = int(yy) * 12 + int(mm) - 1
        if int(yy) * 100 + int(mm) < 196211:
            continue
        engines = os.environ.get("ENGINES", "A,T,C").split(",")
        resA = resT = None
        for eng in engines:
            try:
                if eng == "C":
                    if not resA and not resT:
                        res, note = None, "no A or T read to locate cells"
                    elif not resA:
                        sd = os.path.join(HERE, "raw", "cells", iss)
                        os.makedirs(sd, exist_ok=True)
                        res, note = engine_c(p, resT, sd), "cell OCR at T geometry"
                    else:
                        sd = os.path.join(HERE, "raw", "cells", iss)
                        os.makedirs(sd, exist_ok=True)
                        res, note = engine_c(p, resA, sd), "cell OCR at A geometry"
                elif eng == "T":
                    if resA:
                        clip = table_clip(p, resA)
                    else:
                        d = fitz.open(p)
                        clip = fitz.Rect(0, d[0].rect.height * 0.45, d[0].rect.width, d[0].rect.height * 0.95)
                    res, note = parse_issue(p, "T", clip)
                    resT = res
                else:
                    res, note = parse_issue(p, "A")
                    resA = res
            except Exception as e:
                import traceback; traceback.print_exc()
                res, note = None, f"EXC {type(e).__name__}: {e}"
            log.append({"issue": iss, "engine": eng, "page_file": os.path.basename(p),
                        "n": len(res) if res else 0, "note": note})
            print(iss, eng, len(res) if res else 0, note[:200], flush=True)
            if res:
                for r in res:
                    r.update({"issue": iss, "engine": eng, "page_file": os.path.basename(p)})
                    allrows.append(r)
    tag = os.environ.get("OUT_TAG") or ("_".join(argv) if argv else "all")
    pd.DataFrame(allrows).to_csv(os.path.join(OUTD, f"reads_{tag}.csv"), index=False)
    pd.DataFrame(log).to_csv(os.path.join(OUTD, f"parselog_{tag}.csv"), index=False)


if __name__ == "__main__":
    main(sys.argv[1:])
