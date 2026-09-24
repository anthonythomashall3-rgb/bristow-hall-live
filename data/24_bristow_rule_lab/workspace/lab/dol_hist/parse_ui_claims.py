"""Parse the Department's weekly release *Unemployment Insurance Claims* (1946-1983) into a weekly state panel
(4 September 2026; the wall-removal under Rule 21).

Input: HathiTrust whole-volume OCR text, one .txt per page scan, from
`Onset Detector Data/26_dol_weekly_claims_1946-1983/zips/hathi_<vol>_plaintext.zip`.

The page (v.27 no.1, page 4) reads:

    Initial claims filed during week ended July 3, 1971
    and insured unemployment for week ended June 26, 1971
    ... column headings ...
    All programs (Excl. R.R.) Total (p)
    287,872 40,821 -21,526 4,333 11,935 1,870,293 3.5 *-13,793 291,636 33,028 115,741 2,298,725
    Alaska
    493 5 -67 49 27 3,463 6.2 -704 -196 489 243 4,695
    ...

so the OCR keeps ONE STATE NAME PER LINE followed by that state's numbers on the lines after it, and it drops a
name here and there (Alabama, Connecticut, Iowa and Maine are missing from the page above).  The reader below is
therefore a BLOCK reader: it walks the page, opens a block at every state name it recognizes, and closes it at the
next one; a block whose name the OCR lost is recovered from the alphabetical order (the states are printed in
alphabetical order and the missing name is the one between its neighbours).  Each block's numbers are then assigned
to the twelve fields of the 1971 layout when twelve are present, and left as a raw list when they are not - nothing
is guessed.

The check that makes the panel usable is the release's own redundancy: each week's state numbers appear three times
in the file - as the week's own print, as the next week's "change from last week", and as the following year's
"change from a year ago" - and the page's own "All programs Total" row is the sum of the states.  `verify.py` runs
those three checks; a state-week that fails any of them is dropped, not corrected.

    python3 parse_ui_claims.py <dir of unpacked pages> <volume label>
        -> ui_claims_<label>.csv (state-weeks), ui_claims_<label>.log (page by page)
"""
import sys, os, re, glob
import pandas as pd

ORDER = ['Alabama', 'Alaska', 'Arizona', 'Arkansas', 'California', 'Colorado', 'Connecticut', 'Delaware',
         'District of Columbia', 'Florida', 'Georgia', 'Guam', 'Hawaii', 'Idaho', 'Illinois', 'Indiana', 'Iowa',
         'Kansas', 'Kentucky', 'Louisiana', 'Maine', 'Maryland', 'Massachusetts', 'Michigan', 'Minnesota',
         'Mississippi', 'Missouri', 'Montana', 'Nebraska', 'Nevada', 'New Hampshire', 'New Jersey', 'New Mexico',
         'New York', 'North Carolina', 'North Dakota', 'Ohio', 'Oklahoma', 'Oregon', 'Pennsylvania', 'Puerto Rico',
         'Rhode Island', 'South Carolina', 'South Dakota', 'Tennessee', 'Texas', 'Utah', 'Vermont',
         'Virgin Islands', 'Virginia', 'Washington', 'West Virginia', 'Wisconsin', 'Wyoming']
ALIAS = {'dist of col': 'District of Columbia', 'district of columbia': 'District of Columbia', 'dc': 'District of Columbia',
         'ilinois': 'Illinois', 'alinois': 'Illinois', 'hlinois': 'Illinois', 'illinoi': 'Illinois', 'illinois': 'Illinois',
         'kaasas': 'Kansas', 'maino': 'Maine', 'arisona': 'Arizona', 'hawali': 'Hawaii', 'india na': 'Indiana',
         'lowa': 'Iowa', 'iowa': 'Iowa', 'ala ska': 'Alaska', 'now york': 'New York', 'now jersey': 'New Jersey',
         'virgin is': 'Virgin Islands', 'virgin islands': 'Virgin Islands', 'puerto rico': 'Puerto Rico',
         'w virginia': 'West Virginia', 'west virginia': 'West Virginia', 'n carolina': 'North Carolina',
         's carolina': 'South Carolina', 'n dakota': 'North Dakota', 's dakota': 'South Dakota',
         'n hampshire': 'New Hampshire', 'r island': 'Rhode Island', 'rhode island': 'Rhode Island'}
FIELDS12 = ['ic_state', 'ic_chg_week', 'ic_chg_year', 'ic_ucfe', 'ic_ucx', 'iu_state', 'iu_rate', 'iu_chg_week',
            'iu_chg_year', 'iu_ucfe', 'iu_ucx', 'iu_all']
DATE = re.compile(r'week ended\s+([A-Z][a-z]+)\.?\s+(\d{1,2})\s*,?\s*(\d{4})', re.I)
NUM = re.compile(r'\*?\(?-?\d[\d,]*(?:\.\d+)?\)?')

def clean(tok):
    t = tok.replace('*', '').replace(',', '')
    neg = t.startswith('(') and t.endswith(')')
    t = t.strip('()')
    try: v = float(t)
    except ValueError: return None
    return -v if neg else v

def norm_name(line):
    s = re.sub(r'[.,:;•·]+', ' ', line).strip()
    s = re.sub(r'\s+', ' ', s)
    if not s or len(s) > 26: return None
    key = s.lower().strip(' .*')
    if key in ALIAS: return ALIAS[key]
    for st in ORDER:
        if key == st.lower(): return st
    # a name with one OCR slip: same first four letters and same length within one
    for st in ORDER:
        k = st.lower()
        if len(key) >= 5 and abs(len(key) - len(k)) <= 1 and key[:4] == k[:4]: return st
    return None

def page_dates(text):
    d = DATE.findall(text)
    out = []
    for m in d:
        try: out.append(pd.Timestamp(f'{m[0]} {m[1]}, {m[2]}'))
        except Exception: pass
    return out

def is_state_page(text):
    hits = sum(1 for st in ORDER if st in text)
    return hits >= 12 and ('Initial claims' in text or 'Insured unemployment' in text or 'insured unemployment' in text)

def read_blocks(text):
    """[(state or None, [numbers])] in page order, then the missing names filled from alphabetical order"""
    lines = text.split('\n')
    blocks = []; cur = None; nums = []
    for ln in lines:
        nm = norm_name(ln)
        if nm:
            if cur is not None or nums: blocks.append((cur, nums))
            cur = nm; nums = []
            trailing = [clean(x) for x in NUM.findall(ln)]
            nums += [x for x in trailing if x is not None]
            continue
        vals = [clean(x) for x in NUM.findall(ln)]
        vals = [v for v in vals if v is not None]
        if vals: nums += vals
    if cur is not None or nums: blocks.append((cur, nums))
    # fill a missing name from its neighbours' alphabetical positions
    out = []
    for i, (nm, v) in enumerate(blocks):
        if nm is None:
            nxt = next((blocks[j][0] for j in range(i + 1, len(blocks)) if blocks[j][0]), None)
            prv = next((blocks[j][0] for j in range(i - 1, -1, -1) if blocks[j][0]), None)
            if nxt in ORDER:
                k = ORDER.index(nxt)
                cand = ORDER[k - 1] if k > 0 else None
                if cand and (prv is None or (prv in ORDER and ORDER.index(prv) < k - 1)):
                    nm = cand
        out.append((nm, v))
    return out

def parse_volume(d, label, outdir='/home/claude/lab/dol_hist'):
    pages = sorted(glob.glob(os.path.join(d, '000*.txt')))
    rows = []; log = []
    for p in pages:
        t = open(p, errors='ignore').read()
        if not is_state_page(t): continue
        dts = page_dates(t)
        w_ic = dts[0] if dts else None; w_iu = dts[1] if len(dts) > 1 else None
        blocks = read_blocks(t)
        named = [(nm, v) for nm, v in blocks if nm]
        for nm, v in named:
            r = dict(volume=label, page=os.path.basename(p), week_ic=w_ic, week_iu=w_iu, state=nm, n=len(v),
                     raw='|'.join(f'{x:g}' for x in v[:14]))
            if len(v) == 12:
                r.update({k: v[i] for i, k in enumerate(FIELDS12)})
            rows.append(r)
        log.append(f'{os.path.basename(p)} ic={w_ic} iu={w_iu} blocks={len(blocks)} named={len(named)} '
                   f'twelve={sum(1 for nm, v in named if len(v) == 12)}')
    df = pd.DataFrame(rows)
    df.to_csv(f'{outdir}/ui_claims_{label}.csv', index=False)
    open(f'{outdir}/ui_claims_{label}.log', 'w').write('\n'.join(log))
    tw = int((df.n == 12).sum()) if len(df) else 0
    print(f'{label}: {len(pages)} pages, {df.page.nunique() if len(df) else 0} state pages, {len(df)} state rows, '
          f'{tw} with the full twelve fields, weeks {df.week_ic.min() if len(df) else "-"} to {df.week_ic.max() if len(df) else "-"}')
    return df

if __name__ == '__main__':
    parse_volume(sys.argv[1], sys.argv[2])
