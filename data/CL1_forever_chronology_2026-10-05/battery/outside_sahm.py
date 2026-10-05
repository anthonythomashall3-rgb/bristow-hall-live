"""Test the tests (1): the Sahm rule, real time, on our engine and scorer. Reads panel/vintages/UNRATE_vintages.csv
(ALFRED, every vintage from 1960-03-15). The rule opens on the release day the real-time gap first reaches 0.50 and,
for this outside-tool test only, closes when the gap falls back below 0.50 (Sahm defines no trough rule; the trough
column is therefore not a test of the Sahm rule). Prints the record under W12, W24, W4."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'harness'))
import pandas as pd, rt, score
V = rt.load_vintages(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'panel', 'vintages', 'UNRATE_vintages.csv'))
g = rt.rt_stat_fast(V, rt.sahm_gap)
on = (g.round(10) >= 0.50)
eps = score.episodes_from_states(list(g.index), list(on.values))
start = pd.Timestamp('1960-03-15')
print('Sahm rule (real time, ALFRED vintages from 1960-03-15): %d openings' % len(eps))
for nm, lead in [('W12', 365), ('W24', 730), ('W4', 122)]:
    s = score.score(eps, lead=lead, span0=start)
    s['rows'] = [r for r in s['rows'] if r['peak'] >= '1960-04']   # recessions whose window the data can reach
    s['hits'] = sum(r['status'] == 'HIT' for r in s['rows']); s['n'] = len(s['rows'])
    s['late'] = sum(r['status'] == 'LATE' for r in s['rows']); s['missed'] = sum(r['status'] == 'MISS' for r in s['rows'])
    print(score.fmt(s, 'Sahm %s' % nm) if nm == 'W12' else score.fmt(s, 'Sahm %s' % nm).split('\n')[0])
