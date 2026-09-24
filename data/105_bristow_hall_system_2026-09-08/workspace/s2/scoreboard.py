# -*- coding: utf-8 -*-
"""L5 - THE SHADOW SCOREBOARD (plan Step 5, L4/L5; 23 September 2026, collection 335).

The outside daters run beside the rule as evidence, never as a lesson: the Sahm rule (0.50 on first prints), SOS (unadjusted insured rate,
the programme's declared form), the SF Fed's LMSI-30 (30 of 51 states accelerating), the Chicago Fed's CFNAI-MA3 (below -0.70) and
Michaillat-Saez's Michez rule (0.29 on the smaller of the unemployment and vacancy indicators). Their calls on the programme's real-time
data 1948-2026 are collection 249's, scored in 275 (scoreboard_calls.json); from there on the live tier (s2/backstop.py) carries them.

Scored against the board the tool is scored on (the NBER's recessions and Paper 1's 2024): a dater's call is FOR a recession when it
falls from 122 days before the end of the peak month to 31 days after the end of the trough month (the W4 window of 275's scorer);
otherwise it is a false alarm. For every recession since 1994: each dater's first call, its lead or lag against the tool, and who called
first. The ledger says who called first and who false-alarmed since 1994 - the jury of L4 was tested on this record and refused as a
lesson source (2024: the daters that spoke did so ten months apart; 2003 and 2022-23: rightly no lesson).

Writes out/scoreboard.json; the backstop page prints it."""
import os, sys, json, datetime
import pandas as pd
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def _od():
    for r in (os.path.expanduser('~/Projects/Onset Detector Data'), os.path.expanduser('~/mnt/Onset Detector Data')):
        if os.path.isdir(r): return r
    return None
OD = _od()
NBER = [('1948-11', '1949-10'), ('1953-07', '1954-05'), ('1957-08', '1958-04'), ('1960-04', '1961-02'), ('1969-12', '1970-11'), ('1973-11', '1975-03'), ('1980-01', '1980-07'),
        ('1981-07', '1982-11'), ('1990-07', '1991-03'), ('2001-03', '2001-11'), ('2007-12', '2009-06'), ('2020-02', '2020-04'), ('2024-04', '2024-08')]   # 275/code/clock.py, board N+P1
DATERS = {'Sahm': 'Sahm 0.50 first prints (249)', 'SOS_NSA': 'SOS NSA (249)', 'LMSI30': 'LMSI-30 states (249)', 'CFNAI': 'CFNAI-MA3 (249)', 'Michez': 'Michez (249)'}
def mend(ym): return pd.Timestamp(ym + '-01') + pd.offsets.MonthEnd(0)
def frozen_calls():
    # the frozen daters' calls travel with the workspace (cache/scoreboard_calls_275.json, a copy of 275's file made 23 September
    # 2026 for the cloud, whose data copy has no collection 275); the collection's own file is read where it exists
    p = os.path.join(HERE, 'cache', 'scoreboard_calls_275.json')
    if not os.path.exists(p) and OD: p = os.path.join(OD, '275_best_bhrt_frozen_and_walk_2026-09-20', 'out', 'scoreboard_calls.json')
    j = json.load(open(p)); return {k: [pd.Timestamp(x) for x in j[v]['calls']] for k, v in DATERS.items()}
def live_calls(state_path, backstop_path):
    """the tool's calls from the site's record; the tier's current ON runs as calls when they are newer than the frozen history"""
    S = json.load(open(state_path)); tool = [pd.Timestamp(e['open_pub']) for e in S['episodes'] if e.get('open_pub')]
    live = {}
    try:
        B = json.load(open(backstop_path))
        for k in ('SOS_NSA', 'LMSI30', 'CFNAI', 'Michez'):
            r = B['rules'].get(k) or {}
            if r.get('on') and r.get('since'): live[k] = pd.Timestamp(r['since'])
    except Exception: pass
    try:
        sa = S.get('sahm') or {}
        if isinstance(sa, dict) and sa.get('crossed') and sa.get('crossed_pub'): live['Sahm'] = pd.Timestamp(sa['crossed_pub'])
    except Exception: pass
    return tool, live
def score(calls, tool, since='1994-01-01'):
    since = pd.Timestamp(since); recs = [(p, t) for p, t in NBER if mend(p) >= since]
    out = dict(recessions=[], false_alarms={}, first_caller={}, since=str(since.date()))
    for p, t in recs:
        lo, hi = mend(p) - pd.Timedelta(days=122), mend(t) + pd.Timedelta(days=31)
        row = dict(peak=p, trough=t, window=[str(lo.date()), str(hi.date())], daters={})
        tc = [d for d in tool if lo <= d <= hi]; row['tool'] = str(tc[0].date()) if tc else None
        for k, cl in calls.items():
            c = [d for d in cl if lo <= d <= hi]
            row['daters'][k] = dict(call=(str(c[0].date()) if c else None), days_after_tool=(int((c[0] - tc[0]).days) if c and tc else None))
        firsts = [(pd.Timestamp(v['call']), k) for k, v in row['daters'].items() if v['call']]
        if tc: firsts.append((tc[0], 'the rule'))
        row['first'] = sorted(firsts)[0][1] if firsts else None
        out['recessions'].append(row)
    for k, cl in calls.items():
        fa = [d for d in cl if d >= since and not any(mend(p) - pd.Timedelta(days=122) <= d <= mend(t) + pd.Timedelta(days=31) for p, t in NBER)]
        out['false_alarms'][k] = [str(d.date()) for d in fa]
    out['false_alarms']['the rule'] = [str(d.date()) for d in tool if d >= since and not any(mend(p) - pd.Timedelta(days=122) <= d <= mend(t) + pd.Timedelta(days=31) for p, t in NBER)]
    for k in list(calls) + ['the rule']: out['first_caller'][k] = sum(1 for r in out['recessions'] if r['first'] == k)
    return out
def main():
    calls = frozen_calls(); tool, live = live_calls(os.path.join(HERE, 'out', 'bhs_state.json'), os.path.join(HERE, 'out', 'backstop_state.json'))
    for k, d in live.items():
        if k in calls and (not calls[k] or d > calls[k][-1] + pd.Timedelta(days=182)): calls[k].append(d)
    sb = score(calls, tool); sb['built_at'] = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    sb['note'] = ('evidence, never a lesson: the outside rules on the programme\'s real-time data (collection 249, scored in 275), carried forward by the live tier; '
                  'a call counts for a recession inside [-122, +31] days of the peak and trough months\' ends, else it is a false alarm; the jury (three of five within a month) was tested and refused as a lesson source (collection 335)')
    sb['jury'] = dict(rule='a provisional lesson when at least three of the five non-NBER daters call a peak within one month of one another and the committee has not spoken',
                      test_2024=dict(calls={k: [str(d.date()) for d in cl if pd.Timestamp('2023-06-01') <= d <= pd.Timestamp('2025-06-01')] for k, cl in calls.items()}, verdict='no three within a month: Sahm 2024-08-02, SOS NSA 2023-10-05, Michez 2023-11-03 - the jury takes no lesson where Paper 1 dates April 2024; REFUSED as a lesson source'),
                      test_2003=dict(verdict='Sahm alone (2003-07-03): no lesson, correctly'), test_2022_23=dict(verdict='SOS NSA and Michez within a month of each other (2023-10-05, 2023-11-03), no third: no lesson, correctly'))
    os.makedirs(os.path.join(HERE, 'out'), exist_ok=True); json.dump(sb, open(os.path.join(HERE, 'out', 'scoreboard.json'), 'w'), indent=1)
    print('scoreboard: %d recessions since %s; first caller %s; false alarms %s' % (len(sb['recessions']), sb['since'], sb['first_caller'], {k: len(v) for k, v in sb['false_alarms'].items()}))
    return 0
if __name__ == '__main__': sys.exit(main())
