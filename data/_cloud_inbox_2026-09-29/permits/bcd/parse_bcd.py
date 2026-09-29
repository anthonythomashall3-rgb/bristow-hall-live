#!/usr/bin/env python3
"""Parse series 29 (new private housing units authorized by local building permits) from the
Table 1 'Basic data' page of Business Cycle Developments, Oct 1961 - Dec 1962.

Oct 1961 prints it as a LEVEL (SAAR, thousands); Nov 1961 onward as an INDEX (1957-59=100).
Two OCR reads per page, both deterministic:
  A = ABBYY text layer (pymupdf word boxes)
  T = tesseract 5 (psm 6, digits whitelist) on a 400-dpi crop of the series-29 column
Months: values in the column are taken top-to-bottom inside each year block (rows labelled
1959 / 1960 / 1961 / 1962), January first. A read is accepted when A and T agree; the
cross-issue step is in build_bcd.py.
"""
import csv, glob, os, re, subprocess, tempfile
import numpy as np
import pymupdf as fitz

HERE = os.path.dirname(os.path.abspath(__file__))
LEVEL_RX = re.compile(r"^[LH©®(]?\s*(\d),?(\d{3})$|^[LH©®(]?\s*(\d{3})$")
INDEX_RX = re.compile(r"^[LHrp©®(]?\s*(\d{2,3})[.,-](\d)$")


def val_of(tok, kind):
    """value at the end of an OCR token; leading revision/preliminary marks and box glyphs ignored"""
    t = tok.strip()
    t = re.sub(r"[lI!|\]]", "1", t)
    t = t.replace("O", "0").replace("o", "0").replace("S", "5")
    if kind == "level":
        m = re.search(r"(?:^|[^\d,])(\d)\s*,\s*(\d{3})$", t) or re.search(r"(?:^|[^\d,])(\d),?(\d{3})$", t)
        if m:
            return float(m.group(1) + m.group(2))
        m = re.search(r"(?:^|[^\d,])(\d{3})$", t)
        if m:
            return float(m.group(1))
    else:
        m = re.search(r"(\d{2,3})\s*[.,\-]\s*(\d)$", t)
        if m:
            v = float(m.group(1)) + int(m.group(2)) / 10
            if v >= 200:      # a leading mark or the neighbouring column's last digit glued on
                v = v % 100   # ('1-104-2' for r104.2, '9298.3' for 98.3); the index runs 80-125
                if v < 50:
                    v += 100
            return v
    return None


def flag_of(tok):
    head = re.sub(r"[\d.,\-\s]+$", "", tok)
    if "p" in head or "P" in head:
        return "p"
    if "r" in head:
        return "r"
    return ""


MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september",
          "october", "november", "december"]


def month_word(t):
    t = re.sub(r"[^a-z]", "", t.lower().replace("0", "o").replace("1", "l"))
    if len(t) < 3:
        return None
    for i, m in enumerate(MONTHS):
        if t[:3] == m[:3] or (len(t) >= 5 and t[:5] == m[:5]):
            return i + 1
    return None


def month_grid(ws, yrs, xl, bottom):
    """per year block: linear fit y = a + b*(month-1) from the month-name labels at the left"""
    labs = []
    for w in ws:
        if w[0] < xl * 0.45:
            m = month_word(w[4])
            if m:
                labs.append(((w[1] + w[3]) / 2, m))
    grids = []
    allb = []
    for i, (ytop, year) in enumerate(yrs):
        ynext = yrs[i + 1][0] if i + 1 < len(yrs) else bottom
        pts = [(y, m) for y, m in labs if ytop < y < ynext]
        grids.append(pts)
        if len(pts) >= 3:
            b, a = np.polyfit([m - 1 for _, m in pts], [y for y, _ in pts], 1)
            allb.append(b)
    pitch = float(np.median(allb)) if allb else 8.0
    out = []
    for i, (ytop, year) in enumerate(yrs):
        pts = grids[i]
        if len(pts) >= 3:
            b, a = np.polyfit([m - 1 for _, m in pts], [y for y, _ in pts], 1)
            if abs(b - pitch) > 0.15 * pitch:
                b = pitch
                a = float(np.median([y - (m - 1) * b for y, m in pts]))
        elif pts:
            b = pitch
            a = float(np.median([y - (m - 1) * b for y, m in pts]))
        else:
            b = pitch
            a = None
        out.append((year, a, b, len(pts)))
    return out


def assign_by_grid(vals, grid, yrs, bottom):
    """vals: list of (ycenter, value, raw). returns {(year, month): (value, raw, resid)}"""
    res = {}
    for i, (year, a, b, npts) in enumerate(grid):
        ytop = yrs[i][0]
        ynext = yrs[i + 1][0] if i + 1 < len(yrs) else bottom
        blk = sorted(v for v in vals if ytop < v[0] < ynext)
        if a is None:
            # no month labels in block: fall back to order
            for k, (y, v, raw) in enumerate(blk[:12]):
                res[(year, k + 1)] = (v, raw, None)
            continue
        for y, v, raw in blk:
            k = int(round((y - a) / b))
            resid = (y - a) / b - k
            if 0 <= k < 12 and abs(resid) < 0.4:
                key = (year, k + 1)
                if key in res:
                    res[key] = (None, res[key][1] + "|" + raw, None)   # two values on one month: doubt
                else:
                    res[key] = (v, raw, round(resid, 2))
    return res


def parse_page(pdfpath):
    d = fitz.open(pdfpath)
    p = d[0]
    ws = p.get_text("words")
    txt = p.get_text()
    kind = "index" if re.search(r"29\.\s*Index\s+of", txt) else "level"
    # header x of series 29 and of the next column header (12.) if any
    h29 = [w for w in ws if w[4] in ("29.", "private29.") or w[4].endswith("29.")]
    h29 = [w for w in h29 if w[1] < p.rect.height * 0.35]
    if not h29:
        return None, "no series-29 header", kind
    hx = h29[0][2] - 12 if h29[0][4] != "29." else h29[0][0]
    h12 = [w for w in ws if w[4] == "12." and w[0] > hx and abs(w[1] - h29[0][1]) < 6]
    xr = h12[0][0] - 2 if h12 else p.rect.width
    xl = hx - 12
    # year rows
    yrs = []
    for w in ws:
        t = w[4].replace("I9", "19").replace("l9", "19").replace("!J", "5")
        if re.match(r"19[56]\d(?!\d)", t) and w[0] < xl * 0.5 and w[1] > h29[0][1] + 20:
            yrs.append((w[1], int(t[:4])))
    yrs.sort()
    # guard OCR'd year labels: force consecutive years starting at the first
    if not yrs:
        return None, "no year rows", kind
    y0 = yrs[0][1]
    yrs = [(y, y0 + i) for i, (y, _) in enumerate(yrs)]
    bottom = p.rect.height * 0.97
    vals = []
    for w in ws:
        xc = (w[0] + w[2]) / 2
        if xl <= xc <= xr and w[1] > yrs[0][0]:
            v = val_of(w[4], kind)
            if v is not None:
                vals.append(((w[1] + w[3]) / 2, w[0], v, w[4]))
    grid = month_grid(ws, yrs, xl, bottom)
    got = assign_by_grid([(v[0], v[2], v[3]) for v in vals], grid, yrs, bottom)
    out = [{"year": k[0], "month_no": k[1], "value": v[0], "raw": v[1], "resid": v[2]} for k, v in sorted(got.items())]
    return out, f"kind={kind} col=({xl:.0f},{xr:.0f}) years={[y for _, y in yrs]} grid={[(g[0], g[3]) for g in grid]}", kind, (xl, xr, yrs, bottom, grid)


def tess_column(pdfpath, geom, kind, dpi=300):
    xl, xr, yrs, bottom, grid = geom
    last = [a + 12 * b for (_, a, b, _) in grid if a is not None]
    bottom = min(bottom, max(last) + 10) if last else bottom
    d = fitz.open(pdfpath)
    p = d[0]
    clip = fitz.Rect(xl - 4, yrs[0][0] - 2, xr + 2, bottom)
    sc = dpi / 72
    pix = p.get_pixmap(matrix=fitz.Matrix(sc, sc), clip=clip, colorspace=fitz.csGRAY)
    with tempfile.TemporaryDirectory() as td:
        f = os.path.join(td, "c.png")
        pix.save(f)
        r = subprocess.run(["tesseract", f, "stdout", "--psm", "6", "-c", "tessedit_char_whitelist=0123456789.,",
                            "tsv"], capture_output=True, text=True)
    toks = []
    for line in r.stdout.splitlines()[1:]:
        c = line.split("\t")
        if len(c) < 12 or not c[11].strip():
            continue
        top = clip.y0 + (int(c[7]) + int(c[9]) / 2) / sc
        toks.append((top, clip.x0 + int(c[6]) / sc, c[11]))
    # merge tokens on the same line (e.g. '1,' '045')
    toks.sort()
    lines = []
    for t in toks:
        if lines and abs(lines[-1][0] - t[0]) < 3:
            lines[-1][1].append(t)
        else:
            lines.append([t[0], [t]])
    vals = []
    for top, ts in lines:
        ts.sort(key=lambda z: z[1])
        s = "".join(z[2] for z in ts)
        v = val_of(s, kind)
        if v is not None:
            vals.append((top, v, s))
    got = assign_by_grid(vals, grid, yrs, bottom)
    return [{"year": k[0], "month_no": k[1], "value": v[0], "raw": v[1]} for k, v in sorted(got.items())]


def cell_reads(pdfpath, geom, kind):
    """engine C: tesseract (psm 7, digits) on each month cell of the series-29 column, the cell
    placed by the month grid fitted to the month-name labels; 3 preprocessing variants, majority"""
    from PIL import Image, ImageFilter, ImageOps
    xl, xr, yrs, bottom, grid = geom
    d = fitz.open(pdfpath)
    p = d[0]
    out = []
    for i, (year, a, b, npts) in enumerate(grid):
        if a is None:
            continue
        ynext = yrs[i + 1][0] if i + 1 < len(yrs) else bottom
        for k in range(12):
            yc = a + k * b
            if yc > ynext - 0.3 * b or yc > bottom:
                break
            vals, raws = [], []
            for dpi, pad, blur in ((300, 20, 1.0), (450, 20, 0.0), (300, 0, 1.0)):
                sc = dpi / 72
                pix = p.get_pixmap(matrix=fitz.Matrix(sc, sc), clip=fitz.Rect(xl, yc - 0.5 * b, xr, yc + 0.5 * b),
                                   colorspace=fitz.csGRAY)
                im = Image.frombytes("L", (pix.width, pix.height), pix.samples)
                if blur:
                    im = im.filter(ImageFilter.GaussianBlur(blur))
                if pad:
                    im = ImageOps.expand(im, border=pad, fill=255)
                with tempfile.TemporaryDirectory() as td:
                    f = os.path.join(td, "c.png")
                    im.save(f)
                    r = subprocess.run(["tesseract", f, "stdout", "--psm", "7", "-c", "tessedit_char_whitelist=0123456789.,",
                                        "-c", "load_system_dawg=0", "-c", "load_freq_dawg=0"], capture_output=True, text=True)
                t = re.sub(r"\s+", "", r.stdout)
                raws.append(t)
                vals.append(val_of(t, kind) if t else None)
            good = [v for v in vals if v is not None]
            best = None
            for v in good:
                if good.count(v) >= 2:
                    best = v
                    break
            out.append({"year": year, "month_no": k + 1, "value": best, "raw": "|".join(raws)})
    return out


def main():
    rows = []
    for f in sorted(glob.glob(os.path.join(HERE, "pages", "BCD_*_p*.pdf"))):
        iss = os.path.basename(f).split("_")[1]
        res = parse_page(f)
        if res[0] is None:
            print(iss, res[1])
            continue
        A, note, kind, geom = res
        T = tess_column(f, geom, kind) if os.environ.get("BCD_TESS", "1") == "1" else []
        C = cell_reads(f, geom, kind) if os.environ.get("BCD_TESS", "1") == "1" else []
        Td = {(r["year"], r["month_no"]): r for r in T}
        Cd = {(r["year"], r["month_no"]): r for r in C}
        print(iss, note, "A", len(A), "T", len(T), "C", sum(1 for c in C if c["value"] is not None), flush=True)
        Ad = {(r["year"], r["month_no"]): r for r in A}
        for k in sorted(set(Ad) | set(Td) | set(Cd)):
            a, t, c = Ad.get(k), Td.get(k), Cd.get(k)
            rows.append({"issue": f"{iss[2:]}-{iss[:2]}", "kind": kind, "month": f"{k[0]}-{k[1]:02d}",
                         "A": a["value"] if a else None, "A_raw": a["raw"] if a else "", "A_resid": a.get("resid") if a else None,
                         "T": t["value"] if t else None, "T_raw": t["raw"] if t else "",
                         "C": c["value"] if c else None, "C_raw": c["raw"] if c else "",
                         "page_file": os.path.basename(f)})
    with open(os.path.join(HERE, "bcd_reads.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
