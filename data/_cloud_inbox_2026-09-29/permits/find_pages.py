#!/usr/bin/env python3
"""Locate the housing table page in each Economic Indicators PDF and save it.

For every raw/pdf/MM-YYYY.pdf: score each page's ABBYY text layer for the housing
table (permits + starts keywords), pick the best page, and write
  raw/pages/MM-YYYY_pNN.pdf   (the single page, original scan)
  raw/pages/MM-YYYY_pNN.txt   (pdftotext -layout of that page)
and a row in raw/pages/page_index.csv (issue, page (1-based), score, printed page no.)
"""
import csv, glob, os, re, subprocess, sys
import fitz  # pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
PDF = os.path.join(HERE, "raw", "pdf")
OUT = os.path.join(HERE, "raw", "pages")
os.makedirs(OUT, exist_ok=True)

KEYS = [
    (r"author", 3), (r"building\s+permit", 3), (r"permit-issuing", 4),
    (r"housing\s+starts", 2), (r"units\s+started", 2), (r"new\s+private\s+housing", 3),
    (r"seasonally\s+adjusted\s+annual\s+rates?", 2), (r"thousands\s+of\s+units", 2),
    (r"vacancy", 1), (r"FHA", 1), (r"apprais", 1),
]


def score(txt):
    s = 0
    for k, w in KEYS:
        if re.search(k, txt, re.I):
            s += w
    # table pages have many numbers
    s += min(len(re.findall(r"\d[\d,. ]{2,}", txt)) / 40.0, 3)
    # penalise table of contents / chart-only pages
    if re.search(r"contents", txt, re.I):
        s -= 5
    return s


def main(pattern="*.pdf"):
    idx = os.path.join(OUT, "page_index.csv")
    done = {}
    if os.path.exists(idx):
        for r in csv.DictReader(open(idx)):
            done[r["issue"]] = r
    rows = list(done.values())
    for f in sorted(glob.glob(os.path.join(PDF, pattern))):
        iss = os.path.basename(f)[:-4]
        if iss in done:
            continue
        try:
            doc = fitz.open(f)
        except Exception as e:
            print("OPENFAIL", iss, e)
            continue
        best = None
        for i, pg in enumerate(doc):
            t = pg.get_text()
            sc = score(t)
            if best is None or sc > best[0]:
                best = (sc, i)
        sc, i = best
        out_pdf = os.path.join(OUT, f"{iss}_p{i+1:02d}.pdf")
        nd = fitz.open()
        nd.insert_pdf(doc, from_page=i, to_page=i)
        nd.save(out_pdf)
        txt = subprocess.run(["pdftotext", "-layout", "-f", str(i + 1), "-l", str(i + 1), f, "-"],
                             capture_output=True, text=True).stdout
        open(out_pdf[:-4] + ".txt", "w").write(txt)
        rows.append({"issue": iss, "page": i + 1, "score": round(sc, 2), "npages": len(doc)})
        print(iss, i + 1, round(sc, 2), flush=True)
    rows.sort(key=lambda r: (r["issue"][3:], r["issue"][:2]))
    with open(idx, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["issue", "page", "score", "npages"])
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main(*(sys.argv[1:]))
