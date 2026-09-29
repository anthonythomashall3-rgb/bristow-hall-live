#!/usr/bin/env python3
"""BCD / Business Cycle Developments release dates: each issue states
'The <Month> issue of BUSINESS CONDITIONS DIGEST is scheduled for release on <Month> <day>.'
(the date of the NEXT issue). Parsed from both FRASER's OCR text (raw/fraser/txt) and our layout text
(raw/fraser/text/*.txt.gz). Output work/bcd_release_dates.csv: issue (YYYY-MM), scheduled_release, source_issue, evidence.
"""
import os, re, glob, gzip, json
import pandas as pd

W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October',
          'November', 'December']
MR = '(' + '|'.join(MONTHS) + ')'
PAT = re.compile(r'The\s+' + MR + r'\s*(?:\d{4}\s+)?issue\s+of\s+(?:the\s+)?(?:BUSINESS[\s.,]+(?:CONDITIONS|CYCLE)[\s.,]+(?:DIGEST|DEVELOPMENTS)|BCD|Business\s+(?:Conditions|Cycle)\s+(?:Digest|Developments))'
                 r'(.{0,160}?)release\s+(?:on\s+)?' + MR + r'\.?\s*(\d{1,2})?', re.I | re.S)


def texts():
    for f in sorted(glob.glob(os.path.join(W, 'raw', 'fraser', 'txt', '*.txt*'))):
        op = gzip.open(f, 'rt', errors='replace') if f.endswith('.gz') else open(f, errors='replace')
        yield os.path.basename(f)[:7], 'fraser_ocr_txt', op.read()
    for f in sorted(glob.glob(os.path.join(W, 'raw', 'fraser', 'text', '*.txt.gz'))):
        yield os.path.basename(f)[:7], 'layout_text', gzip.open(f, 'rt', errors='replace').read()


def main():
    rows = []
    for iss, src, t in texts():
        t2 = re.sub(r'\s+', ' ', t)
        y, m = int(iss[:4]), int(iss[5:7])
        for mm in PAT.finditer(t2):
            nxt, mid, rmon, rday = mm.group(1), mm.group(2), mm.group(3), mm.group(4)
            # day may be displaced ("scheduled for 30. ... release on August"): look for a lone number in mid
            if not rday:
                d2 = re.search(r'\b(\d{1,2})\.', mid or '')
                rday = d2.group(1) if d2 else None
            ni = MONTHS.index(nxt.capitalize()) + 1
            ny = y + (1 if ni < m else 0)
            ri = MONTHS.index(rmon.capitalize()) + 1
            ry = ny + (1 if ri < ni else 0)
            if not rday:
                continue
            rows.append(dict(issue=f'{ny:04d}-{ni:02d}', scheduled_release=f'{ry:04d}-{ri:02d}-{int(rday):02d}',
                             stated_in_issue=iss, source=src, evidence=mm.group(0)[:200]))
    df = pd.DataFrame(rows).drop_duplicates(['issue', 'scheduled_release', 'source'])
    # consolidate: prefer agreement of both sources
    out = []
    for iss, g in df.groupby('issue'):
        vals = g.scheduled_release.value_counts()
        out.append(dict(issue=iss, scheduled_release=vals.index[0], n_sources=len(g), n_distinct=len(vals),
                        stated_in_issue=g.stated_in_issue.iloc[0], evidence=g.evidence.iloc[0]))
    o = pd.DataFrame(out)
    o.to_csv(os.path.join(W, 'work', 'bcd_release_dates.csv'), index=False)
    print(len(o), 'issues with a stated release date;', (o.n_distinct > 1).sum(), 'with conflicting parses')


if __name__ == '__main__':
    main()
