#!/usr/bin/env python3
"""Before the full PDFs are deleted (shared-disk limit): keep the front-matter text (pages 1-3,
cover date + contents) of every issue, and verify the chosen housing page mentions permits."""
import csv, glob, os, re, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
rows = []
idx = {r["issue"]: r for r in csv.DictReader(open(os.path.join(HERE, "raw/pages/page_index.csv")))}
for f in sorted(glob.glob(os.path.join(HERE, "raw/pdf/*.pdf"))):
    iss = os.path.basename(f)[:-4]
    t = subprocess.run(["pdftotext", "-layout", "-f", "1", "-l", "3", f, "-"], capture_output=True, text=True).stdout
    open(os.path.join(HERE, "raw/pages", f"{iss}_front.txt"), "w").write(t)
    pg = idx[iss]["page"]
    pt = open(glob.glob(os.path.join(HERE, "raw/pages", f"{iss}_p*.txt"))[0]).read()
    cover = re.findall(r"(JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)\s*,?\s*(19\d\d)", t.upper())
    rows.append({"issue": iss, "page": pg, "has_author": bool(re.search(r"author", pt, re.I)),
                 "has_permit": bool(re.search(r"permit", pt, re.I)),
                 "cover_dates": ";".join(sorted(set(" ".join(c) for c in cover)))[:120]})
with open(os.path.join(HERE, "raw/pages/page_check.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]))
    w.writeheader(); w.writerows(rows)
print(len(rows))
