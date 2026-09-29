#!/usr/bin/env python3
"""Locate seasonally adjusted tables in Employment and Earnings issues (text layer).
Writes out/ee_pages_index.csv: issue, table (EMP_SA|HRS_SA), page, orientation hint."""
import csv, glob, os, re, sys
import pymupdf
W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def norm(t):
    return re.sub(r'\s+', '', t).lower()

def main():
    out = []
    for pdf in sorted(glob.glob(os.path.join(W, 'raw', 'ee', 'ee_*.pdf'))):
        issue = re.search(r'(\d{4}-\d{2})', pdf).group(1)
        doc = pymupdf.open(pdf)
        for pi, page in enumerate(doc):
            t = page.get_text()
            n = norm(t)
            head = norm(t[:1500])
            nnum = len(re.findall(r'\d,\d{3}', t))
            if (re.search(r'division.{0,12}season', head) or re.search(r'season.{0,25}industryemploy', head)
                    or (re.search(r'b-4', head) and 'season' in head)) and 'contents' not in head[:400] \
                    and not re.search(r'productionworkers.{0,40}season', head[:200]):
                out.append((issue, 'EMP_SA', pi + 1, nnum))
            if re.search(r'hours.{0,30}season', head) and 'contents' not in head[:400] \
                    and len(re.findall(r'\d\d[.,] ?\d', t)) > 8:
                out.append((issue, 'HRS_SA', pi + 1, nnum))
    with open(os.path.join(W, 'out', 'ee_pages_index.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['issue', 'table', 'page', 'n_thousands_numbers'])
        w.writerows(out)
    from collections import defaultdict
    d = defaultdict(list)
    for iss, k, p, nn in out:
        d[iss].append(f'{k}:p{p}')
    for iss in sorted(d):
        print(iss, d[iss])

if __name__ == '__main__':
    main()
