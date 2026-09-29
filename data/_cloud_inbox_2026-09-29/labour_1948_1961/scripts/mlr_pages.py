#!/usr/bin/env python3
"""Keep only the 'Current Labor Statistics' sections A (employment and pay rolls) and C (earnings and
hours) of each MLR issue as a small PDF + text in raw/mlr_pages/; the ~50 MB issues are then deleted
(URLs in raw/mlr/fetch_log.csv). Not parsed (see FINDING.md)."""
import glob, os, re
import pymupdf
W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
out = os.path.join(W, 'raw', 'mlr_pages')
os.makedirs(out, exist_ok=True)
for pdf in sorted(glob.glob(os.path.join(W, 'raw', 'mlr', 'mlr_*.pdf'))):
    issue = re.search(r'(\d{4}-\d{2})', pdf).group(1)
    doc = pymupdf.open(pdf)
    keep = []
    for pi, p in enumerate(doc):
        head = re.sub(r'\s+', ' ', p.get_text()[:400]).upper()
        if re.search(r'EMPLOYMENT AND PAY ?R[O0]LLS|EARNINGS AND HOURS|CURRENT LABOR STATISTICS', head):
            keep.append(pi)
    if keep:
        nd = pymupdf.open()
        for pi in keep:
            nd.insert_pdf(doc, from_page=pi, to_page=pi)
        nd.save(os.path.join(out, f'mlr_{issue}_sectionsAC.pdf'), garbage=3, deflate=True)
        with open(os.path.join(out, f'mlr_{issue}_sectionsAC.txt'), 'w') as f:
            for pi in keep:
                f.write(f'\n\f=== original page {pi+1}\n' + doc[pi].get_text())
    print(issue, len(keep), [k + 1 for k in keep][:3], flush=True)
