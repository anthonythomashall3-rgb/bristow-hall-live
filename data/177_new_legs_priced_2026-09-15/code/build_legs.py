#!/usr/bin/env python3
"""Price three candidate legs causally, in the same form the WARN leg (collection 121) uses,
so that walk 69 can inject them exactly as walk 62 injects leg N.

A LEG IS A LIST OF PROPOSALS. Each row is (setting_a, setting_b, published, dated): the day the
object crossed its line as a user would have seen it, and the month that crossing is dated to.
Nothing else. The walk then arms the leg behind the rule's own record and rebuilds the chronology.

THE THREE CANDIDATES, each an object the archive found and never wired in:

  leg M  MONEY -- the paper-bill spread (collection 164). Three-month finance paper placed
         directly (1954-1997) spliced onto three-month AA financial commercial paper (1997-),
         less the three-month Treasury bill. Daily, one day's publication lag.
         Collection 164: calls November 1973 at -43 days and December 2007 at -104.

  leg A  ACTIVITY -- the Chicago Fed national activity index (collection 165). Monthly, and it
         is published about 55 days after the month it measures, which is charged here.
         Collection 165: seven firings in 66 years, zero false alarms, March 2001 at -29 and
         February 2020 at -30.

  leg P  DIFFUSION -- the Philadelphia Fed general activity diffusion index (collection 173).
         May 1968 to today, still live, and published INSIDE the month it measures -- the third
         Thursday, so 17 days after the month stamp, which is a genuinely negative lag.

CAUSAL DISCIPLINE. Every line is a quantile of the object's OWN PRIOR values, expanding from a
minimum history and shifted one period, so a crossing is never informed by itself. A proposal is
emitted on the publication day, never the data day. No line is chosen by looking at the result:
the whole grid of settings is written out and the walk picks among them from the past.
"""
import os, numpy as np, pandas as pd, warnings
warnings.filterwarnings('ignore')

_C = [os.path.expanduser('~/Projects/Onset Detector Data'), os.path.expanduser('~/mnt/Onset Detector Data')]
BASE = next((c for c in _C if os.path.isdir(os.path.join(c, '176_financial_leg_conjunction_2026-09-15'))), _C[0])
SRC = os.path.join(BASE, '176_financial_leg_conjunction_2026-09-15', 'data')
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, 'out'); os.makedirs(OUT, exist_ok=True)


def rd(sid):
    d = pd.read_csv(os.path.join(SRC, sid + '.csv')); c = list(d.columns)
    s = pd.Series(pd.to_numeric(d[c[1]], errors='coerce').values,
                  index=pd.to_datetime(d[c[0]], errors='coerce'))
    s = s[~s.index.isna()].dropna().sort_index()
    return s[~s.index.duplicated(keep='last')]


def crossings(obj, pub_offset_days, wins, qs, minobs, collapse_days=180):
    """obj oriented so HIGH = deteriorating. Returns rows (win, q, published, dated)."""
    rows = []
    for w in wins:
        x = obj.rolling(w).mean().dropna() if w > 1 else obj.dropna()
        for q in qs:
            line = x.shift(1).expanding(min_periods=minobs).quantile(q / 100.0)
            hit = (x > line) & line.notna()
            # EPISODE COLLAPSE. A daily object over a quantile crosses on many consecutive days;
            # those are one event, not hundreds of proposals. Consecutive crossings within
            # `collapse_days` of one another are one episode and only its FIRST day is emitted,
            # which is also the earliest a user could have acted. Same convention as the WARN leg.
            last = None
            for t in x.index[hit]:
                if last is not None and (t - last).days <= collapse_days:
                    last = t; continue
                pub = t + pd.Timedelta(days=pub_offset_days)
                rows.append((w, q, pub.date().isoformat(),
                             (t.to_period('M').to_timestamp()).date().isoformat()))
                last = t
    return rows


def write(name, rows, cols):
    p = os.path.join(OUT, name)
    pd.DataFrame(rows, columns=cols).to_csv(p, index=False)
    n = len(rows); k = len(set((r[0], r[1]) for r in rows))
    print('%-28s rows=%-6d settings=%-3d -> %s' % (name, n, k, os.path.basename(p)))
    return p


# ---------------- leg M : the paper-bill spread ----------------
fp = pd.concat([rd('H0RIFSPPFM06NB'), rd('DCPF3M')]).sort_index()
fp = fp[~fp.index.duplicated(keep='last')]
b3 = rd('DTB3')
pb = (fp - b3.reindex(fp.index, method='ffill')).dropna()
print('paper-bill spread: %s .. %s  n=%d' % (pb.index.min().date(), pb.index.max().date(), len(pb)))
rowsM = crossings(pb, 1, wins=[10, 20, 40], qs=[95, 97, 99], minobs=1250)
write('leg_M_money_proposals.csv', rowsM, ['mwin', 'mq', 'published', 'dated'])

# ---------------- leg A : Chicago Fed activity ----------------
cf = -rd('CFNAIMA3')          # oriented: HIGH = weak activity
print('CFNAI (3-mo avg): %s .. %s  n=%d' % (cf.index.min().date(), cf.index.max().date(), len(cf)))
rowsA = crossings(cf, 55, wins=[1, 2, 3], qs=[90, 95, 97], minobs=120)
write('leg_A_activity_proposals.csv', rowsA, ['awin', 'aq', 'published', 'dated'])

# ---------------- leg P : Philadelphia Fed diffusion ----------------
ph = -rd('GACDFSA066MSFRBPHI')  # oriented: HIGH = contracting
print('Philly Fed diffusion: %s .. %s  n=%d' % (ph.index.min().date(), ph.index.max().date(), len(ph)))
rowsP = crossings(ph, 17, wins=[1, 2, 3], qs=[90, 95, 97], minobs=120)
write('leg_P_diffusion_proposals.csv', rowsP, ['pwin', 'pq', 'published', 'dated'])
