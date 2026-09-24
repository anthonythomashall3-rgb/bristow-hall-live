#!/usr/bin/env python3
"""Rule B' — the rolling-breadth gate.

RULE B' (frozen 2026-08-16): a rolling recession is confirmed when >=30 of 51
jurisdictions record fresh state-episode onsets within a 24-month window that
contains no confirmed national recession months ("clean window").
Constants inherited, not tuned: 30 = Rule B's breadth bar; episode definition =
state Sahm >=0.50 under the frozen chronology conventions. Window W=24 primary;
verdict identical for W in {18,24,30}; W=12 too short (nothing ever passes).
"""
import csv

EPS = "/root/recession/state_episodes.csv"
REC = [('1980-01','1980-07'),('1981-07','1982-11'),('1990-07','1991-03'),
       ('2001-03','2001-11'),('2007-12','2009-06'),('2020-02','2020-04')]

def mnum(s): y,m=s.split('-'); return int(y)*12+int(m)-1
def mstr(n): return f"{n//12:04d}-{n%12+1:02d}"

eps = list(csv.DictReader(open(EPS)))
recm = set(t for a,b in REC for t in range(mnum(a), mnum(b)+1))
lo, hi = mnum('1977-01'), mnum('2026-06')

def scan(W, floor=0.50, bar=30):
    ons = [(r['state'], mnum(r['start'])) for r in eps if float(r['peak_val']) >= floor]
    cnt = {t: len(set(st for st,a in ons if t-W+1 <= a <= t)) for t in range(lo, hi+1)}
    clean = lambda t: not any(x in recm for x in range(t-W+1, t+1))
    hits = [t for t in range(lo, hi+1) if clean(t) and cnt[t] >= bar]
    runs = []
    for t in hits:
        if runs and t == runs[-1][1]+1: runs[-1][1] = t
        else: runs.append([t, t])
    return cnt, clean, runs

for W in (12, 18, 24, 30):
    cnt, clean, runs = scan(W)
    desc = [f"{mstr(a)}->{mstr(b)} peak {max(cnt[x] for x in range(a,b+1))}" for a,b in runs]
    prev = max((cnt[t], t) for t in range(lo, mnum('2022-12')) if clean(t))
    print(f"W={W:2d}: clean-window passages >=30: {desc or 'NONE'} | "
          f"best non-wave clean month: {prev[0]} at {mstr(prev[1])}")

print("\nsensitivity (W=24): floor -> wave max | best non-wave | gap")
for floor in (0.50, 0.55, 0.60, 0.70):
    cnt, clean, _ = scan(24, floor)
    wave = max(cnt[t] for t in range(mnum('2023-01'), hi+1) if clean(t))
    prev = max(cnt[t] for t in range(lo, mnum('2022-12')) if clean(t))
    print(f"  {floor:.2f} -> {wave} | {prev} | +{wave-prev}")
