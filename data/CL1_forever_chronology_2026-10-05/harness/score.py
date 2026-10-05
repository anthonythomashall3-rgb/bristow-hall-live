# -*- coding: utf-8 -*-
"""CL1 scorer: one scorer for calls (openings) and closes (troughs) on the N+P1 board.

Definitions (recession-scientist skill section 4; PREREG 552 standard; the user's 5 Oct 2026 standard):
  P_i     end of recession i's peak month;  T_i  end of its trough month.
  lag     (call day - P_i) in days; negative = early.          trough lag = (close day - T_i) in days.
  window  W(lead) = [-lead, +31]. W12 lead 365 (the user's standard), W24 730, W4 122, W3 92.
  zone_i  [P_i - lead, T_i]. An opening inside zone_i is attributed to recession i.
  call    the first opening attributed to i. HIT if lag <= +31, LATE if lag > +31 (still inside the zone).
  miss    no opening attributed to i.
  false alarm  an opening attributed to no zone, counted from 1948-01-01 (an opening before P_i - lead is "too
          early" and is a false alarm; a later opening in the zone can still call i).
  close   the tool's close after an opening. A close attributed to i is a close of an episode whose opening was
          attributed to i. TROUGH HIT if the LAST close of recession i is within [T_i - 31, T_i + 31] and no close
          of i falls before T_i - 31 (a "false stop": the tool said the recession ended and it had not).
  open at end of data: an episode still open on the last scored day has no close (counted as such).
  post-board openings: openings after the last board trough are counted as false alarms (strict) and also listed
          separately as 'pending', since no peak has been dated after 2024-08.
Every count is printed by code; the self-test pins the definitions to the live tool's published record.
"""
import json, os, sys
import pandas as pd

BOARD = [('1948-11', '1949-10'), ('1953-07', '1954-05'), ('1957-08', '1958-04'), ('1960-04', '1961-02'),
         ('1969-12', '1970-11'), ('1973-11', '1975-03'), ('1980-01', '1980-07'), ('1981-07', '1982-11'),
         ('1990-07', '1991-03'), ('2001-03', '2001-11'), ('2007-12', '2009-06'), ('2020-02', '2020-04'),
         ('2024-04', '2024-08')]                      # N+P1: the NBER's twelve plus Paper 1's 2024
NBER_ONLY = BOARD[:-1]
LEADS = {'W24': 730, 'W12': 365, 'W4': 122, 'W3': 92}
LATE = 31
TROUGH = 31
SPAN0 = pd.Timestamp('1948-01-01')


def ends(board=None):
    b = board or BOARD
    return ([pd.Timestamp(p) + pd.offsets.MonthEnd(0) for p, _ in b],
            [pd.Timestamp(t) + pd.offsets.MonthEnd(0) for _, t in b])


def episodes_from_states(days, states):
    """days: sorted daily timestamps; states: same-length booleans (True = recession called). -> [(open, close|None)]"""
    eps, cur = [], None
    for d, s in zip(days, states):
        if s and cur is None: cur = d
        elif not s and cur is not None: eps.append((cur, d)); cur = None
    if cur is not None: eps.append((cur, None))
    return eps


def score(episodes, lead=365, board=None, end=None, span0=SPAN0):
    """episodes: [(open_day, close_day or None)]. Returns a dict with per-recession rows and totals."""
    P, T = ends(board)
    b = board or BOARD
    eps = sorted((pd.Timestamp(o), None if c is None else pd.Timestamp(c)) for o, c in episodes)
    eps = [(o, c) for o, c in eps if o >= span0 and (end is None or o <= pd.Timestamp(end))]
    att = []
    for o, c in eps:
        k = None
        for i in range(len(P)):
            if P[i] - pd.Timedelta(days=lead) <= o <= T[i]: k = i; break
        att.append(k)
    rows = []
    for i in range(len(P)):
        mine = [(o, c) for (o, c), k in zip(eps, att) if k == i]
        r = dict(peak=b[i][0], trough=b[i][1], call=None, lag=None, status='MISS', close=None, tlag=None,
                 tstatus='NO-CALL', false_stops=0)
        if mine:
            o0 = mine[0][0]; r['call'] = str(o0.date()); r['lag'] = (o0 - P[i]).days
            r['status'] = 'HIT' if r['lag'] <= LATE else 'LATE'
            closes = [c for _, c in mine if c is not None]
            r['false_stops'] = sum(1 for c in closes if c < T[i] - pd.Timedelta(days=TROUGH))
            if mine[-1][1] is None:
                r['tstatus'] = 'OPEN'
            else:
                c = mine[-1][1]; r['close'] = str(c.date()); r['tlag'] = (c - T[i]).days
                r['tstatus'] = 'HIT' if (abs(r['tlag']) <= TROUGH and r['false_stops'] == 0) else 'MISS'
        rows.append(r)
    fa = [(str(o.date()), None if c is None else str(c.date())) for (o, c), k in zip(eps, att) if k is None]
    post = [x for x in fa if pd.Timestamp(x[0]) > T[-1]]
    out = dict(lead=lead, rows=rows, hits=sum(r['status'] == 'HIT' for r in rows),
               late=sum(r['status'] == 'LATE' for r in rows), missed=sum(r['status'] == 'MISS' for r in rows),
               fa=len(fa), fa_list=fa, pending=post,
               trough_hits=sum(r['tstatus'] == 'HIT' for r in rows), n=len(rows))
    assert out['hits'] + out['late'] + out['missed'] == len(rows)
    return out


def fmt(s, name=''):
    L = ['%s  lead %d: calls %d/%d inside [-%d,+%d] (late %d, missed %d), false alarms %d, troughs %d/%d inside [-31,+31]'
         % (name, s['lead'], s['hits'], s['n'], s['lead'], LATE, s['late'], s['missed'], s['fa'], s['trough_hits'], s['n'])]
    for r in s['rows']:
        L.append('   %s/%s  call %s (%s, %s)  close %s (%s, %s)%s' % (
            r['peak'], r['trough'], r['call'], '' if r['lag'] is None else '%+d' % r['lag'], r['status'],
            r['close'], '' if r['tlag'] is None else '%+d' % r['tlag'], r['tstatus'],
            ('  false stops %d' % r['false_stops']) if r['false_stops'] else ''))
    if s['fa_list']: L.append('   false alarms: %s' % s['fa_list'])
    return '\n'.join(L)


def selftest():
    """Pins the scorer to (a) synthetic cases with known answers and (b) the live tool v3.76's published record."""
    fails = []
    P, T = ends()
    # (a) synthetic: a call exactly at +31 is a hit, +32 late; a call at -365 a hit under W12, -366 a false alarm
    s = score([(P[0] + pd.Timedelta(days=31), T[0])], lead=365)
    if s['rows'][0]['status'] != 'HIT' or s['rows'][0]['tstatus'] != 'HIT': fails.append('a1')
    s = score([(P[0] + pd.Timedelta(days=32), T[0] + pd.Timedelta(days=31))], lead=365)
    if s['rows'][0]['status'] != 'LATE' or s['rows'][0]['tstatus'] != 'HIT': fails.append('a2')
    s = score([(P[1] - pd.Timedelta(days=365), T[1] + pd.Timedelta(days=32))], lead=365)
    if s['rows'][1]['status'] != 'HIT' or s['rows'][1]['tstatus'] != 'MISS' or s['fa'] != 0: fails.append('a3')
    s = score([(P[1] - pd.Timedelta(days=366), P[1] - pd.Timedelta(days=300))], lead=365)
    if s['fa'] != 1 or s['rows'][1]['status'] != 'MISS': fails.append('a4')
    # a false stop: close 40 days before the trough end, re-open, close at the trough end
    s = score([(P[2], T[2] - pd.Timedelta(days=40)), (T[2] - pd.Timedelta(days=20), T[2])], lead=365)
    if s['rows'][2]['false_stops'] != 1 or s['rows'][2]['tstatus'] != 'MISS' or s['fa'] != 0: fails.append('a5')
    # an opening after the last trough is a false alarm and pending
    s = score([(T[-1] + pd.Timedelta(days=10), None)], lead=365)
    if s['fa'] != 1 or len(s['pending']) != 1: fails.append('a6')
    # (b) the live tool's thirteen episodes (bhs_state.json). v3.76's own commit (e114175, collection 441) states:
    # "12 of 13 in [-92,+31]; 1980 opens 1979-09-07; 2020 opens 2020-03-16". Under W12 every call is inside and
    # every close is inside [-31,+31], with no false alarm.
    here = os.path.dirname(os.path.abspath(__file__))
    st = json.load(open(os.path.join(here, '..', '..', '105_bristow_hall_system_2026-09-08', 'bhs_state.json')))
    eps = [(e['open_pub'], e['close_pub']) for e in st['episodes']]
    s3 = score(eps, lead=92)
    if not (s3['hits'] == 12 and s3['rows'][6]['status'] == 'MISS' and s3['fa_list'] == [('1979-09-07', '1980-07-09')]):
        fails.append('b1 W3 %s' % fmt(s3, 'v3.76'))
    s12 = score(eps, lead=365)
    if not (s12['hits'] == 13 and s12['fa'] == 0 and s12['trough_hits'] == 13 and s12['rows'][6]['lag'] == -146):
        fails.append('b2 W12 %s' % fmt(s12, 'v3.76'))
    print(fmt(s12, 'v3.76 (live state file, %s) W12' % st['version']))
    print(fmt(s3, 'v3.76 W3').split(chr(10))[0])
    print('SELFTEST', 'PASS' if not fails else 'FAIL %s' % fails)
    return 0 if not fails else 1


if __name__ == '__main__':
    sys.exit(selftest())
