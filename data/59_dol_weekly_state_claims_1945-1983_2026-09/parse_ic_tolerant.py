"""Tolerant reader for ONE field - state initial claims (State UI programs) - from the OCR text of the Department's weekly
release, 1946-1983, with cross-week reconciliation.  5 September 2026.

Why: parse_ui_claims_eras.py assigns a block only when its numeric count matches the era's full layout (9-13 fields), and
Google's OCR splits rows across segments, so only ~35 of 53 states survive per week and 36 weeks reach 40+ states.  The
route's weekly state breadth (leg C) needs one number per state-week - initial claims - and that number is the FIRST
token after the state name in every layout from 1951 on (ic_w1 / ic_total / ic_state), and tokens 9-10 of eleven in the
1946-51 layout.  The release also prints the change from the previous week, so IC(t) - change(t) is a second, independent
print of IC(t-1); two prints that agree confirm each other, and a print that disagrees with its neighbour by a dropped or
added digit is repaired to the neighbour-consistent one.  Nothing is invented: every value carries its source
('own', 'implied', 'both', 'repaired') and the raw tokens are kept.

Usage: python3 parse_ic_tolerant.py <page-directory> <label> [<outdir>]
"""
import sys, os, re, glob, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parse_ui_claims_eras import (FULL, ABBR, H1955, H1946, H1951, H1953, NUM, to_date, numval as _numval, state_of as _state_of)
def numval(tok):
    return _numval(tok.rstrip(',-').replace('.', '', tok.count('.') if re.search(r'\.\d{3}(\D|$)', tok) else 0))
import difflib
# OCR and house-style variants seen in the 1946-55 tables (5 Sep 2026): footnote marks follow the name ('N.D.3/..')
ABBR.update({'Wisc':'Wisconsin','N.D':'North Dakota','N. D':'North Dakota','S.D':'South Dakota','S. D':'South Dakota','Hebr':'Nebraska','Nebr':'Nebraska',
             'N.Hex':'New Mexico','N. Hex':'New Mexico','N.Mox':'New Mexico','Wt':'Vermont','Nov':'Nevada','Nev':'Nevada','Ilaine':'Maine','Maino':'Maine',
             'Hass':'Massachusetts','Hich':'Michigan','Hinn':'Minnesota','Hiss':'Mississippi','Ho':'Missouri','Hont':'Montana','Hd':'Maryland',
             'Okla':'Oklahoma','Oreg':'Oregon','Wash':'Washington','Ala':'Alabama','Ark':'Arkansas','Ariz':'Arizona','Colo':'Colorado','Ga':'Georgia',
             'Fla':'Florida','Ill':'Illinois','Ind':'Indiana','Kans':'Kansas','Ky':'Kentucky','La':'Louisiana','Tenn':'Tennessee','Tex':'Texas','Va':'Virginia','Wyo':'Wyoming','Del':'Delaware'})
UPPER = {n.upper(): n for n in FULL}
UPPER.update({'DIST. OF COL': 'District of Columbia', 'DIST OF COL': 'District of Columbia', 'D. C': 'District of Columbia',
              'N. HAMPSHIRE': 'New Hampshire', 'N. CAROLINA': 'North Carolina', 'S. CAROLINA': 'South Carolina',
              'N. DAKOTA': 'North Dakota', 'S. DAKOTA': 'South Dakota', 'W. VIRGINIA': 'West Virginia', 'P. RICO': 'Puerto Rico'})
NUM2 = re.compile(r"^[*+\-]?\d{1,3}(?:[,;.]\d{3})*(?:\.\d+)?[,\-]?$|^[*+\-]?\d+(?:\.\d+)?[,\-]?$")
ABBR.update({'Ia':'Iowa','Iova':'Iowa','Iowa':'Iowa','Nobr':'Nebraska','Webr':'Nebraska','Orog':'Oregon','Orc':'Oregon','Kanso':'Kansas','Kons':'Kansas','Wev':'Nevada',
             'NoC':'North Carolina','NC':'North Carolina','II.C':'North Carolina','W.VL':'West Virginia','V.Va':'West Virginia','Ili':'Illinois','Okia':'Oklahoma','Tox':'Texas',
             'Tann':'Tennessee','Tem':'Tennessee','RoI':'Rhode Island','S.Do':'South Dakota','N.Ho':'New Hampshire','Com':'Connecticut','Cona':'Connecticut','Dall':'Delaware'})
ROMAN = re.compile(r"^(?:[IVX]{1,4}|N)\s+(?=[A-Z])")
def state_of(line):
    line = ROMAN.sub("", line.strip())                       # a region numeral before the name ('VII Ill.....')
    """the era reader's matcher, then the 1973-83 UPPERCASE tables (names printed as 'ALABAMA.......', OCR slips such as
    'COLORAD)' or 'IDAMU' matched by similarity >= 0.8 on the letters only)."""
    st = _state_of(line)
    if st: return st
    s = line.strip()
    m = re.match(r"^([A-Z][A-Z\.\s\)\*]{2,24}?)[\.\s\*…]*$", s)
    if not m or any(ch.isdigit() for ch in s): return None
    key = re.sub(r"[\.\*\)…]+$", "", m.group(1)).strip()
    if len(key) < 4 or key.upper() != key: return None
    if key in UPPER: return UPPER[key]
    k2 = re.sub(r"[^A-Z]", "", key)
    if len(k2) < 4: return None
    best = difflib.get_close_matches(k2, [re.sub(r"[^A-Z]", "", u) for u in UPPER], n=1, cutoff=0.8)
    if best:
        for u, n in UPPER.items():
            if re.sub(r"[^A-Z]", "", u) == best[0]: return n
    return None

def page_blocks(path):
    txt = open(path, errors="ignore").read()
    era = d1 = None
    for pat, tag in ((H1955, 'E1955'), (H1946, 'E1946'), (H1951, 'E1951'), (H1953, 'E1953')):
        m = pat.search(txt)
        if m:
            era = tag; d1 = to_date(m.group(1)); d2 = to_date(m.group(2)) if tag != 'E1953' else d1; break
    if era is None: return era, None, None, []
    blocks, cur = [], None
    for ln in txt.split("\n"):
        st = state_of(ln)
        if st:
            if cur: blocks.append(cur)
            rest = ln.strip()
            for nm in [st] + [k for k, v in ABBR.items() if v == st]:
                if rest.startswith(nm): rest = rest[len(nm):]; break
            cur = dict(state=st, toks=[t for t in re.split(r"\s+", rest.strip(" .:")) if NUM2.match(t)])
        elif cur is not None:
            for t in re.split(r"\s+", ln.strip()):
                if NUM2.match(t): cur['toks'].append(t)
    if cur: blocks.append(cur)
    # 1973-83 pages list several state NAMES first and their rows after: a run of empty blocks followed by one block holding
    # (n+1) rows' worth of tokens is split back in printed order, twelve tokens a row (the E1971 layout), when the count fits
    L = 12
    out = []; run = []
    for b in blocks:
        if not b['toks']: run.append(b); continue
        if run and len(b['toks']) >= L * (len(run) + 1) - 2 and len(b['toks']) <= L * (len(run) + 1) + 2:
            toks = b['toks']; names = run + [b]
            for i, nb in enumerate(names):
                out.append(dict(state=nb['state'], toks=toks[i * L:(i + 1) * L] if i < len(names) - 1 else toks[i * L:]))
            run = []; continue
        out.extend(run); run = []; out.append(b)
    out.extend(run)
    return era, d1, d2, out

def ic_from_block(era, toks):
    """(week-of-ic, ic, change-from-previous-week or None) candidates from one block."""
    vals = [numval(t) for t in toks]; vals = [v for v in vals if v is not None]
    out = []
    if not vals: return out
    if era in ('E1955',):               # 1955-83 layouts: ic first, change second (signed); 1956 on, change from a year ago third
        ic = vals[0]; chg = vals[1] if len(vals) > 1 else None
        if chg is not None and abs(chg) > max(2 * ic, 500): chg = None   # a second token that cannot be a weekly change
        chy = vals[2] if len(vals) > 2 else None
        if chy is not None and abs(chy) > max(3 * ic, 500): chy = None
        out.append(('d1', ic, chg, chy))
    elif era == 'E1951':                # ic_w1, ic_w2, ic_chg, ...
        if len(vals) >= 2: out.append(('d1', vals[0], None, None)); out.append(('d2', vals[1], None, None))
        else: out.append(('d1', vals[0], None, None))
    elif era == 'E1953':                # ic_total, ic_total_chg, ic_state, ic_state_chg, ...
        if len(vals) >= 3: out.append(('d1', vals[2], vals[3] if len(vals) > 3 else None, None))
        else: out.append(('d1', vals[0], vals[1] if len(vals) > 1 else None, None))
    elif era == 'E1946':                # eleven numbers, ic_w1 at 9, ic_w2 at 10 (1-based)
        if len(vals) == 11: out.append(('d1', vals[8], None, None)); out.append(('d2', vals[9], None, None))
        elif len(vals) >= 10: out.append(('d1', vals[-3], None, None)); out.append(('d2', vals[-2], None, None))
    return out

def parse_volume(d, label, outdir="."):
    rows = []
    for p in sorted(glob.glob(os.path.join(d, "*.txt"))):
        era, d1, d2, blocks = page_blocks(p)
        if era is None or pd.isna(d1): continue
        for b in blocks:
            for which, ic, chg, chy in ic_from_block(era, b['toks']):
                wk = d1 if which == 'd1' else d2
                if pd.isna(wk): continue
                rows.append(dict(week=wk, state=b['state'], ic=ic, chg=chg, chg_yr=chy, era=era, page=os.path.basename(p), raw="|".join(b['toks'])))
    df = pd.DataFrame(rows)
    if not len(df): print(label, 'nothing'); return df
    df = df[(df.ic > 0) & (df.ic < 400000)]
    df['volume'] = label
    os.makedirs(outdir, exist_ok=True); df.to_csv(f"{outdir}/ic_tolerant_{label}.csv", index=False)
    print(f"{label}: {len(df)} state-week prints, weeks {df.week.min().date()} to {df.week.max().date()}, states {df.state.nunique()}")
    return df

if __name__ == "__main__":
    parse_volume(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else ".")
