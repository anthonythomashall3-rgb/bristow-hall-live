#!/usr/bin/env python3
"""Text layer + physical-series row index for the FRASER 'Business Statistics weekly supplement' PDFs
held in raw/fraser/scb_weekly_pdf (1939-1948 and 1977-1981 in this collection; 1947-1976 is being pulled
by the sibling collector collect/claims_pre1975/pdf/scbw).

Step 1: pdftotext -layout (FRASER's own ABBYY OCR layer, deterministic) -> raw/fraser/scb_weekly_txt/.
Step 2: every line whose label matches one of the weekly physical/activity series below is written to
        tidy/fraser_scb_weekly/row_lines.csv with the tokens that are purely numeric ([0-9][0-9,.]*).

NOT DONE HERE: mapping tokens to week-ending dates. Column order differs by era -- in 1939-1940 issues the
LATEST week is the FIRST numeric column (then earlier weeks, then year-ago weeks); in 1962 and 1977 issues
the latest week is the RIGHTMOST column (year-ago weeks first). OCR confusions (!->1, S->5, I->1, O->0) are
NOT corrected; tokens with such characters are simply not counted as numeric. A per-era header parse is
needed before these become series.
"""
import os, re, csv, glob, subprocess

W = '/tmp/claude-0/-home-user/49f76bce-ebc7-5769-b106-ce7685453d86/scratchpad/collect/new_candidates'
P = os.path.join(W, 'raw', 'fraser', 'scb_weekly_pdf'); X = os.path.join(W, 'raw', 'fraser', 'scb_weekly_txt')
O = os.path.join(W, 'tidy', 'fraser_scb_weekly'); os.makedirs(X, exist_ok=True); os.makedirs(O, exist_ok=True)
KEYS = [('steel', r'steel\s*ingot|steel,\s*raw|raw\s*steel'),
        ('electric_power', r'electric\s*power'),
        ('freight_carloadings', r'freight[\s-]*car\s*loadings|carloadings'),
        ('bituminous_coal', r'bituminous\s*coal'),
        ('petroleum_crude', r'petroleum|crude\s*(oil|runs)'),
        ('lumber', r'^\s*lumber'),
        ('automobiles', r'automobiles|passenger\s*cars'),
        ('department_store_sales', r'department\s*store\s*sales'),
        ('business_failures', r'failures'),
        ('initial_claims', r'initial\s*(unemployment\s*)?claims'),
        ('insured_unemployment', r'insured\s*unemployment')]
NUM = re.compile(r'^[0-9][0-9,]*(\.[0-9]+)?$')
rows = []
for f in sorted(glob.glob(os.path.join(P, '*.pdf'))):
    m = re.search(r'(\d{8})', os.path.basename(f))
    d = m.group(1); iso = '%s-%s-%s' % (d[:4], d[4:6], d[6:]) if d[:2] in ('19', '20') else \
        '%s-%s-%s' % (d[4:], d[:2], d[2:4])
    t = os.path.join(X, os.path.basename(f)[:-4] + '.txt')
    if not os.path.exists(t):
        subprocess.run(['pdftotext', '-layout', f, t], check=False)
    lines = open(t, errors='replace').read().splitlines()
    for i, ln in enumerate(lines):
        lab = ln.strip()[:70].lower()
        for k, rx in KEYS:
            if re.search(rx, lab):
                toks = [x for x in re.split(r'\s+', ln.strip()) if NUM.match(x)]
                if not toks: continue
                rows.append(dict(issue_date=iso, pdf=os.path.basename(f), key=k, line_no=i + 1,
                                 n_numeric=len(toks), numeric_tokens='|'.join(toks), raw_line=ln.strip()))
                break
with open(os.path.join(O, 'row_lines.csv'), 'w', newline='') as g:
    w = csv.DictWriter(g, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
iss = []
for f in sorted(glob.glob(os.path.join(P, '*.pdf'))):
    out = subprocess.run(['pdfinfo', f], capture_output=True, text=True).stdout
    pg = re.search(r'Pages:\s+(\d+)', out)
    iss.append(dict(pdf=os.path.basename(f), bytes=os.path.getsize(f), pages=int(pg.group(1)) if pg else ''))
pd_ = __import__('pandas').DataFrame(iss)
pd_['issue_date'] = [ (lambda d: '%s-%s-%s' % (d[:4], d[4:6], d[6:]) if d[:2] in ('19', '20') else '%s-%s-%s' % (d[4:], d[:2], d[2:4]))(re.search(r'(\d{8})', x).group(1)) for x in pd_['pdf']]
pd_.sort_values('issue_date').to_csv(os.path.join(O, 'issues_held.csv'), index=False)
print(len(rows), 'lines from', len(iss), 'issues')
