# -*- coding: utf-8 -*-
"""THE MERGED WEEKLY CLAIMS FIRST-PRINT TABLE, WRITTEN AS SOON AS A RELEASE IS IN (1167, 24 Nov 2026). No AI.

cache/national_first_prints_1985_live.csv is the early first prints of 1975-2002 (s2/first_prints_early_1975_2002.csv, static) in front of
collection 45's live table (45_dol_first_prints_2026-09/national_first_prints.csv). bhs_build.py writes it (E66) - but the starter
(s2/c1021.py), the home tiles (s2/home_tiles.py), Tool 4 and the Time Machine read it BEFORE bhs_build.py runs, so on a release run that
takes the week from the Department's own release (bhs_dol_press.py, 8:30 AM, before FRED and ALFRED carry it) they read the table as the
LAST build left it, without the week just released, until the next run. bhs_update.py now calls write() right after the release is
appended to 45, so every reader of the run sees it. The merge is bhs_build.py's E66 block line for line (the same columns, the same order,
the same CSV text); bhs_build.py still writes it at the build and finds it unchanged. Written to a temporary name and moved into place.
BHS_FIRSTPRINTS_OFF=1 (a cmpstate on 45 alone) leaves the file as it is, as the build does.
    write(workspace=None) -> 'written' | 'unchanged' | 'off' | 'no early table'"""
import os


def write(workspace=None):
    import pandas as pd
    ws = workspace or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    early = os.path.join(ws, 's2', 'first_prints_early_1975_2002.csv')
    if os.environ.get('BHS_FIRSTPRINTS_OFF'): return 'off'
    if not os.path.exists(early): return 'no early table'
    root = next(r for r in (os.path.expanduser('~/Projects/Onset Detector Data'), os.path.expanduser('~/mnt/Onset Detector Data')) if os.path.isdir(r))
    p45 = os.path.join(root, '45_dol_first_prints_2026-09', 'national_first_prints.csv')
    e = pd.read_csv(early, dtype=str).fillna(''); live = pd.read_csv(p45, dtype=str).fillna('')
    first45 = pd.to_datetime(live['release_date']).min()
    e = e[pd.to_datetime(e['release_date']) < first45]          # the early table ends where 45 begins
    cols = list(live.columns)
    for c in cols:
        if c not in e.columns: e[c] = ''
    live['source'] = '45'; live['fills'] = ''
    merged = pd.concat([e[cols + ['source', 'fills']], live[cols + ['source', 'fills']]], ignore_index=True)
    os.makedirs(os.path.join(ws, 'cache'), exist_ok=True); pm = os.path.join(ws, 'cache', 'national_first_prints_1985_live.csv')
    txt = merged.to_csv(index=False)
    if os.path.exists(pm) and open(pm).read() == txt: return 'unchanged'
    tmp = pm + '.tmp'
    with open(tmp, 'w') as fh: fh.write(txt)
    os.replace(tmp, pm)
    return 'written'


if __name__ == '__main__':
    print('first prints merged table:', write())
