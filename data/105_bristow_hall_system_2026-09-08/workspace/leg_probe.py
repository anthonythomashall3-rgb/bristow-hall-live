"""Which legs CAN land one to thirty-one days before each peak, and which cannot?

Anthony's standard of 14 September is that every call lands between one and thirty-one days before
the peak month's end. This asks the question the walk cannot answer quickly: leg by leg, line by
line, on what day does each leg first propose in the window around each of the nine peaks? Where no
setting of any existing leg lands inside [-31, -1], the gap is a DATA gap and this prints it as one.
Run:  python3 leg_probe.py 1962 2026 pr
"""
import sys, os, io, contextlib
SEARCH_TERMS = ['unemp', 'layoffs', 'laidoff']; os.environ['BHS_SEARCH_TERMS'] = ','.join(SEARCH_TERMS)
_MARK = "# ---- the walk " + "itself"
exec(open('walk54.py').read().split(_MARK)[0].replace("walk54_%s.out", "leg_probe_%s.out"))
import pandas as pd, numpy as np

PK = ['1969-12', '1973-11', '1980-01', '1981-07', '1990-07', '2001-03', '2007-12', '2020-02', '2024-04']
END = {s: pd.Timestamp(s + '-01') + pd.offsets.MonthEnd(0) for s in PK}
print('BR (state breadth) spans', BR.dropna().index.min().date(), 'to', BR.dropna().index.max().date(),
      ' n =', int(BR.notna().sum()))
print('SI (survey-week insured rate) spans', SI.dropna().index.min().date(), 'to', SI.dropna().index.max().date())

def report(name, calls):
    out = {}
    for s in PK:
        e = END[s]
        c = [d for d, _ in calls if e - pd.Timedelta(days=400) <= d <= e + pd.Timedelta(days=200)]
        if not c: out[s] = None; continue
        # the LATEST proposal that is still before the peak month's end, else the earliest after it
        before = [d for d in c if d < e]
        out[s] = (max(before) - e).days if before else (min(c) - e).days
    print(f'{name:28s}', ' '.join(f'{s}:{("  na" if out[s] is None else f"{out[s]:+5d}")}' for s in PK), flush=True)

with contextlib.redirect_stdout(io.StringIO()):
    pass
for line in (0.70, 0.55, 0.45, 0.35, 0.30, 0.25, 0.20, 0.15):
    report(f'L insured rate 52w  {line}', [x[:2] for x in leg_gapL_x(spl, line, 52, rearm='window')] +
           [x[:2] for x in leg_rt_x(RT, line)])
for line in (0.60, 0.50, 0.45, 0.40, 0.35, 0.30, 0.25):
    report(f'W survey-week  {line}', [x[:2] for x in leg_sv_x(line, rearm='zero')])
for line in (0.60, 0.50, 0.45, 0.40):
    report(f'V survey-week win  {line}', [x[:2] for x in leg_sv_x(line, rearm='window')])
for line in (0.70, 0.60, 0.50, 0.40, 0.30, 0.20):
    report(f'B state breadth  {line}', [x[:2] for x in leg_br_x(line)])
for line in (60, 50, 45, 40, 35):
    report(f'I initial claims  {line}', [x[:2] for x in leg_ic_cx(ICfp, line)])
