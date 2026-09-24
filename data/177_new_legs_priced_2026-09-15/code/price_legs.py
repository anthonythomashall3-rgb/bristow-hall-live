#!/usr/bin/env python3
"""Price each candidate leg the way collection 121 priced the WARN leg: for every setting, does
it reach a peak inside the window, and how often does it fire when nothing is happening?

A leg is admissible as an ACCELERATOR if, once armed behind the rule's own record, its quiet
firings are gone and its in-window hits survive. Arming is simulated here with v3.29's own
episodes, which is what walk 62 does with leg N: a proposal is refused while the record is open
and for eighteen months after the close that ended the last episode.

Nothing is selected by result. Every setting is printed.
"""
import json, os, numpy as np, pandas as pd, warnings
warnings.filterwarnings('ignore')

_C = [os.path.expanduser('~/Projects/Onset Detector Data'), os.path.expanduser('~/mnt/Onset Detector Data')]
BASE = next((c for c in _C if os.path.isdir(os.path.join(c, '105_bristow_hall_system_2026-09-08'))), _C[0])
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, 'out')

PEAKS = ['1948-11','1953-07','1957-08','1960-04','1969-12','1973-11',
         '1980-01','1981-07','1990-07','2001-03','2007-12','2020-02','2024-04']
def me(ym): return pd.Timestamp(ym+'-01') + pd.offsets.MonthEnd(0)
PK = [me(p) for p in PEAKS]

# v3.29's own episodes, from the deployed state file -- the arming record
st = json.load(open(os.path.join(BASE, '105_bristow_hall_system_2026-09-08', 'bhs_state.json')))
EP = [(pd.Timestamp(e['open_pub']), pd.Timestamp(e['close_pub']))
      for e in st['episodes'] if e.get('close_pub')]
BARS = [(o, c + pd.DateOffset(months=18)) for o, c in EP]
print('arming bars from v3.29 episodes:', len(BARS))

def armed_out(t):
    return any(a <= t <= b for a, b in BARS)

LEGS = [('M', 'leg_M_money_proposals.csv', ['mwin','mq'], 'paper-bill spread'),
        ('A', 'leg_A_activity_proposals.csv', ['awin','aq'], 'Chicago Fed activity index'),
        ('P', 'leg_P_diffusion_proposals.csv', ['pwin','pq'], 'Philadelphia Fed diffusion')]

rows = []
for letter, fn, keys, label in LEGS:
    d = pd.read_csv(os.path.join(OUT, fn))
    d['published'] = pd.to_datetime(d['published'])
    print('\n=== leg %s : %s ===' % (letter, label))
    print('%-12s %-6s %-6s %-30s %-6s %-6s' % ('setting','fires','armed','in-window hits (peak:days)','quiet','quiet_armed'))
    for (a, b), g in d.groupby(keys):
        pubs = sorted(g['published'])
        hits, used = {}, set()
        for p in PK:
            c = [t for t in pubs if 0 <= (p - t).days <= 400]
            if c:
                t = c[-1]; hits[p.strftime('%Y-%m')] = (t - p).days; used.add(t)
        inw = {k: v for k, v in hits.items() if -92 <= v <= -1}
        quiet = [t for t in pubs if t not in used]
        quiet_armed = [t for t in quiet if not armed_out(t)]
        rows.append(dict(leg=letter, s1=a, s2=b, n_fire=len(pubs), n_hit=len(hits),
                         n_inwindow=len(inw), n_quiet=len(quiet), n_quiet_after_arming=len(quiet_armed),
                         inwindow=json.dumps(inw),
                         quiet_armed_dates=';'.join(str(t.date()) for t in quiet_armed[:8])))
        show = ', '.join('%s:%+d' % (k[:7], v) for k, v in sorted(inw.items())) or '-'
        print('%-12s %-6d %-6d %-30s %-6d %-6d' % ('%s=%s,%s' % (keys[0][0], a, b), len(pubs),
                                                    len(pubs) - len(quiet_armed), show[:30],
                                                    len(quiet), len(quiet_armed)))
r = pd.DataFrame(rows)
r.to_csv(os.path.join(OUT, 'leg_pricing.csv'), index=False)
print('\n=== settings with ZERO quiet firings after arming, ranked by in-window hits ===')
z = r[r.n_quiet_after_arming == 0].sort_values(['n_inwindow','n_hit'], ascending=False)
if len(z):
    print(z[['leg','s1','s2','n_fire','n_hit','n_inwindow','inwindow']].head(12).to_string(index=False))
else:
    print('none')
