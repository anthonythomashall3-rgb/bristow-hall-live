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
    t = tok.strip().replace("O", "0").replace("o", "0").replace("I", "1").replace("l", "1").replace("S", "5")
    t = re.sub(r"^[rp]", "", t)
    if kind == "level":
        m = LEVEL_RX.match(t)
        if m:
            return float(m.group(1) + m.group(2)) if m.group(1) else float(m.group(3))
    else:
        m = INDEX_RX.match(t)
        if m:
            return float(m.group(1)) + int(m.group(2)) / 10
    return None


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
        if re.fullmatch(r"19[56]\d", t) and w[0] < xl * 0.5 and w[1] > h29[0][1] + 20:
            yrs.append((w[1], int(t)))
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
                vals.append((w[1], w[0], v, w[4]))
    vals.sort()
    out = []
    for i, (ytop, year) in enumerate(yrs):
        ynext = yrs[i + 1][0] if i + 1 < len(yrs) else bottom
        blk = [v for v in vals if ytop < v[0] < ynext]
        for k, (yy, xx, v, raw) in enumerate(blk[:12]):
            out.append({"year": year, "month_no": k + 1, "value": v, "raw": raw, "y": round(yy, 1)})
    return out, f"kind={kind} col=({xl:.0f},{xr:.0f}) years={[y for _, y in yrs]}", kind, (xl, xr, yrs, bottom)


def tess_column(pdfpath, geom, kind, dpi=400):
    xl, xr, yrs, bottom = geom
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
        top = clip.y0 + int(c[7]) / sc
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
    out = []
    for i, (ytop, year) in enumerate(yrs):
        ynext = yrs[i + 1][0] if i + 1 < len(yrs) else bottom
        blk = [v for v in vals if ytop - 1 < v[0] < ynext - 1]
        for k, (yy, v, raw) in enumerate(blk[:12]):
            out.append({"year": year, "month_no": k + 1, "value": v, "raw": raw})
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
        T = tess_column(f, geom, kind)
        Td = {(r["year"], r["month_no"]): r for r in T}
        print(iss, note, "A", len(A), "T", len(T), flush=True)
        for r in A:
            t = Td.get((r["year"], r["month_no"]))
            rows.append({"issue": f"{iss[2:]}-{iss[:2]}", "kind": kind, "month": f"{r['year']}-{r['month_no']:02d}",
                         "A": r["value"], "A_raw": r["raw"], "T": t["value"] if t else None, "T_raw": t["raw"] if t else "",
                         "page_file": os.path.basename(f)})
        keysA = {(r["year"], r["month_no"]) for r in A}
        for k, t in Td.items():
            if k not in keysA:
                rows.append({"issue": f"{iss[2:]}-{iss[:2]}", "kind": kind, "month": f"{k[0]}-{k[1]:02d}",
                             "A": None, "A_raw": "", "T": t["value"], "T_raw": t["raw"], "page_file": os.path.basename(f)})
    with open(os.path.join(HERE, "bcd_reads.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
