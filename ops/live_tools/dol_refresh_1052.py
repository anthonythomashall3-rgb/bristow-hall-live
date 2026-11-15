#!/usr/bin/env python3
"""LIVE TOOLS ON GITHUB (1052, 15 Nov 2026; no AI): the Department of Labor's State claims files the State page reads
(1032 data/dol/ar539.csv: weekly ETA 539; ar5159.csv: monthly ETA 5159), from https://oui.doleta.gov/unemploy/csv/ - the same files and
address the detector's backstop tier reads each run (s2/backstop.py ar539()).
Same rule as 1052 code/state_inputs_refresh_1052.py refresh_philly(): the held file is replaced only when the new one parses with the same
columns, its newest report date is no earlier than the held one's, and it differs; the held file is first copied unchanged to
data/dol/../_dated_copies/dol_asof_<its modified date>/ (nothing is deleted). Writes $LT_OUT/dol_refresh_1052.json."""
import os, io, sys, json, time, shutil, urllib.request
import pandas as pd
ROOT = os.path.expanduser('~/Projects/Onset Detector Data'); DOL = os.path.join(ROOT, '1032_state_recession_indicator_all_states_dc_2026-11-09', 'data', 'dol')
OUTD = os.environ.get('LT_OUT') or '/tmp'
def log(*a): print(time.strftime('%H:%M:%S'), *a, flush=True)
def one(name):
    p = os.path.join(DOL, name); old = pd.read_csv(p, low_memory=False, usecols=['st', 'rptdate']); held_last = str(old.rptdate.max())
    try:
        with urllib.request.urlopen(urllib.request.Request('https://oui.doleta.gov/unemploy/csv/' + name, headers={'User-Agent': 'Mozilla/5.0 (research data collector)'}), timeout=180) as r: b = r.read()
    except Exception as e: return dict(file=name, before=held_last, after=held_last, changed=False, note=f'{type(e).__name__} {e}'[:200])
    if b == open(p, 'rb').read(): return dict(file=name, before=held_last, after=held_last, changed=False, note='identical to the held file')
    try:
        n = pd.read_csv(io.BytesIO(b), low_memory=False); oc = list(pd.read_csv(p, nrows=0).columns)
        assert list(n.columns) == oc, f'columns differ: {list(n.columns)[:6]}'; new_last = str(n.rptdate.max()); assert n.st.nunique() >= 50
    except Exception as e: return dict(file=name, before=held_last, after=held_last, changed=False, note=f'new file does not parse: {e}'[:200])
    if new_last < held_last: return dict(file=name, before=held_last, after=held_last, changed=False, note=f'new file ends {new_last}; held kept')
    dst = os.path.join(os.path.dirname(DOL), '_dated_copies', 'dol_asof_' + time.strftime('%Y-%m-%d', time.localtime(os.path.getmtime(p)))); os.makedirs(dst, exist_ok=True)
    if not os.path.exists(os.path.join(dst, name)): shutil.copy2(p, os.path.join(dst, name))
    open(p + '.tmp1052', 'wb').write(b); os.replace(p + '.tmp1052', p)
    return dict(file=name, before=held_last, after=new_last, changed=True, note='oui.doleta.gov', copy=dst)
if __name__ == '__main__':
    R = dict(run=time.strftime('%Y-%m-%dT%H:%M:%S%z'), files=[one('ar539.csv'), one('ar5159.csv')]); R['changed'] = any(f['changed'] for f in R['files'])
    log(json.dumps(R)); os.makedirs(OUTD, exist_ok=True); json.dump(R, open(os.path.join(OUTD, 'dol_refresh_1052.json'), 'w'), indent=1)
