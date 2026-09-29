#!/usr/bin/env python3
"""Dump the column-header text of each EI labour table (text layer), to
out/ei_headers.csv, so layout eras can be identified."""
import csv, glob, os, sys
import pymupdf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ei_find import find_tables
from tables import extract_rows
from eicore import group_lines

W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def main():
    out = []
    for pdf in sorted(glob.glob(os.path.join(W, 'raw', 'ei', 'ei_*.pdf'))):
        issue = os.path.basename(pdf)[3:10]
        doc = pymupdf.open(pdf)
        tabs = find_tables(doc)
        for kind in ('LF', 'EMP', 'HRS'):
            for pi, top, bot in tabs.get(kind, []):
                page = doc[pi]
                words = page.get_text('words')
                rows = extract_rows(words, (int(issue[:4]), int(issue[5:])), body_top=top, body_bot=bot)['rows']
                if not rows:
                    continue
                y_first = min(w[1] for w in rows[0]['words'])
                hdr = [w for w in words if top - 80 <= w[1] < y_first - 1]
                lines = group_lines(hdr)
                txt = ' / '.join(' '.join(w[4] for w in l['w']) for l in lines)
                # in-body section labels
                body = [w for w in words if y_first - 1 <= w[1] <= max(w2[3] for w2 in rows[-1]['words'])]
                bl = group_lines(body)
                labels = [' '.join(w[4] for w in l['w']) for l in bl
                          if not any(ch.isdigit() for ch in ''.join(w[4] for w in l['w']))]
                out.append(dict(issue=issue, kind=kind, page=pi + 1, header=txt[:900], body_labels=' | '.join(labels)[:300],
                                first_ref=rows[0]['ref'], last_ref=rows[-1]['ref'], nrows=len(rows)))
    fn = os.path.join(W, 'out', 'ei_headers.csv')
    with open(fn, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    print('wrote', fn, len(out))

if __name__ == '__main__':
    main()
