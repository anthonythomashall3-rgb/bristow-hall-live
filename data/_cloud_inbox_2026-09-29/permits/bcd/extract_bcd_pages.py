#!/usr/bin/env python3
"""Keep only the BCD 'Table 1. Basic data' page(s) that carry series 29 (index of new private
housing units authorized by local building permits), then the full PDFs can be deleted."""
import csv, glob, os, re, subprocess
import pymupdf as fitz
HERE = os.path.dirname(os.path.abspath(__file__))
rows = []
for f in sorted(glob.glob(os.path.join(HERE, "pdf", "BCD_*.pdf"))):
    iss = os.path.basename(f)[4:-4]          # MMYYYY
    d = fitz.open(f)
    keep = []
    for i, p in enumerate(d):
        t = p.get_text()
        if re.search(r"[B3]ASIC\s+DATA", t, re.I) and re.search(r"29\.\s*(Index\s+of|New\s+pri)", t) and re.search(r"authorized", t, re.I):
            keep.append(i)
    for i in keep:
        nd = fitz.open(); nd.insert_pdf(d, from_page=i, to_page=i)
        out = os.path.join(HERE, "pages", f"BCD_{iss}_p{i+1:02d}.pdf"); nd.save(out)
        txt = subprocess.run(["pdftotext", "-layout", "-f", str(i + 1), "-l", str(i + 1), f, "-"], capture_output=True, text=True).stdout
        open(out[:-4] + ".txt", "w").write(txt)
    front = subprocess.run(["pdftotext", "-layout", "-f", "1", "-l", "2", f, "-"], capture_output=True, text=True).stdout
    open(os.path.join(HERE, "pages", f"BCD_{iss}_front.txt"), "w").write(front)
    rows.append({"issue": iss, "pages": ";".join(str(i + 1) for i in keep), "npages": len(d),
                 "bytes": os.path.getsize(f), "sha256": subprocess.run(["sha256sum", f], capture_output=True, text=True).stdout[:64]})
    print(iss, [i + 1 for i in keep], flush=True)
with open(os.path.join(HERE, "pages", "page_index.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
