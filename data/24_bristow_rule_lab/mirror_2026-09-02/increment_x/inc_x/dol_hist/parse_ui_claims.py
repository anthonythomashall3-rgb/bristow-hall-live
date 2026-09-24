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

THOUSANDS = re.compile(r'^-?\d{1,3}\.\d{3}$')

def clean(tok):
    """One printed figure.  The only genuine decimal in the table is the insured unemployment RATE, printed to one
    place; every other column is a count in units.  So a token with exactly THREE figures after the point is the
    OCR reading a thousands comma as a full stop - `3.997` is 3,997 and `157.551` is 157,551 - and the point is
    removed.  A token with one or two places is left alone (it is a rate, or a genuine small figure)."""
    t = tok.replace('*', '').replace(',', '')
    neg = t.startswith('(') and t.endswith(')')
    t = t.strip('()')
    if THOUSANDS.match(t): t = t.replace('.', '')
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
    """A state TABLE page, not a page of prose that happens to name states.  The covering letter of every issue
    names a dozen states in its text; the table carries a figure for every state in every column, so the test is
    a figure count as well as a name count."""
    low = text.lower()
    hits = sum(1 for st in ORDER if st.lower() in low)
    return hits >= 12 and len(NUM.findall(text)) >= 120 and ('initial claims' in low or 'insured unemployment' in low)


def regroup(blocks):
    """The 1978-83 layout prints the state COLUMN first and the figures after it.

    The scans of v.34 and later put a run of names together - ALABAMA, ALASKA, ARIZONA ... IDAHO - and then the
    figures for all of them, so a block reader keyed to names gives every name in the run an empty block and the
    last name the whole run's figures.  Where a run of `m` names with no figures is followed by a block carrying
    exactly `12 * m` figures, the figures are dealt back to the run in the order printed: twelve to the first
    name, twelve to the second, and so on.  Nothing is guessed - the count has to come out exactly, and
    `verify.py` still tests every row three ways.
    """
    out = []; i = 0
    while i < len(blocks):
        nm, v = blocks[i]
        if not v and nm is not None:
            j = i
            while j < len(blocks) and blocks[j][0] is not None and not blocks[j][1]: j += 1
            if j < len(blocks) and blocks[j][0] is not None:
                run = [blocks[k][0] for k in range(i, j)] + [blocks[j][0]]
                w = blocks[j][1]
                if len(w) == 12 * len(run):
                    for q, st in enumerate(run): out.append((st, w[12 * q:12 * (q + 1)]))
                    i = j + 1; continue
        out.append((nm, v)); i += 1
    return out

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
    blocks = regroup(blocks)
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


def plausible(v):
    """the twelve fields of the 1971 layout, sanity-checked: the state's initial claims positive, the insured
    unemployment positive and larger than a week's initial claims is not required, the insured rate between a
    tenth of a point and thirty points (no state has ever printed outside that), the all-programs total positive"""
    if len(v) != 12: return False
    ic_state, iu_state, iu_rate, iu_all = v[0], v[5], v[6], v[11]
    return (ic_state > 0 and iu_state > 0 and 0.1 <= iu_rate <= 30.0 and iu_all > 0)

def split_block(nm, v):
    """One block, one or more states.

    The release prints the states in alphabetical order, so a block carrying 24 numbers is TWO states whose second
    name the OCR lost, a block carrying 36 is three, and so on: the missing names are the ones that follow `nm` in
    the printed order.  This is not a guess about the numbers - the numbers are read as printed; it is a claim
    about which state they belong to, and `verify.py` tests that claim three ways (the next week's change column,
    the following year's change column, and the state's own magnitude) and drops what fails.

    A block carrying THIRTEEN numbers has one token too many - a footnote marker read as a figure, a page number,
    a rule mistaken for a minus.  Dropping the first or the last leaves twelve; the one that satisfies the
    layout's own arithmetic (`plausible`) is kept, and if both or neither do, nothing is claimed.
    """
    n = len(v)
    if n == 12 or nm is None: return [(nm, v)]
    if n in (24, 36, 48) and nm in ORDER:
        k = ORDER.index(nm); out = []
        for j in range(n // 12):
            if k + j >= len(ORDER): break
            out.append((ORDER[k + j], v[12 * j:12 * (j + 1)]))
        return out
    if n == 13:
        cands = [v[1:], v[:12]]
        ok = [c for c in cands if plausible(c)]
        if len(ok) == 1: return [(nm, ok[0])]
    return [(nm, v)]

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
            for st, vv in split_block(nm, v):
                r = dict(volume=label, page=os.path.basename(p), week_ic=w_ic, week_iu=w_iu, state=st, n=len(vv),
                         raw='|'.join(f'{x:g}' for x in vv[:14]))
                if len(vv) == 12:
                    r.update({k: vv[i] for i, k in enumerate(FIELDS12)})
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
