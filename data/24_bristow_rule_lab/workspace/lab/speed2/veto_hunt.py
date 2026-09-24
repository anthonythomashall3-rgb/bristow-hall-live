"""The speed hunt, part one: a FAST second condition (3 September 2026, night, second half).

Anthony: speed first, without false alarms; think about data - daily, weekly - that could carry the
information the unemployment rate carries (present in the twelve and in 2023-24, absent in 1951,
1952 and 1967) but faster.  The claims objects already open sixteen episodes since 1948 under one
call, one date (route A); every candidate is read AT those sixteen calls, because inside the route
only those days matter.  Read at the call day and over the thirty and sixty days after it:

  S&P 500 (daily, Yahoo ^GSPC from December 1927): drawdown from the trailing 252-day high;
      three- and six-month returns
  Moody's Baa less Aaa (monthly, 1919 on): the spread's rise over its previous-twelve-month low
  the term spread, ten-year less three-month bill (monthly, 1934 on): level, and level a year before
  three-month bill (monthly): change over three months (is the Fed easing?)
  freight cars loaded (NBER, monthly 1918-1973): year-over-year change
  business failures with liabilities >= $100,000 (NBER, monthly 1948-1969): year-over-year change

For each object the question is the one the unemployment rate answers slowly: is there a line that
the twelve (and 2023) cross within a month of the claims call and that 1951, 1952 and 1967 do not?
Part two reads the S&P alone as a possible CALL object: the day its drawdown first reached 5, 10, 15
per cent inside [peak month - 6, peak month + 3] for each of the thirteen, and every other such day
since 1948 (a stock object without the claims gate).  Output veto_hunt.log.
"""
import numpy as np, pandas as pd
D = '/home/claude/lab/speed2/data'
def fred(sid):
    s = pd.read_csv(f'{D}/{sid}.csv', index_col=0, parse_dates=True).iloc[:, 0]; return s
CALLS = [('1948-12-10', 'M', 'recession 1948-11'), ('1951-09-20', 'A', 'DISTURBANCE 1951'), ('1952-04-10', 'M', 'DISTURBANCE 1952'),
         ('1953-09-20', 'A', 'recession 1953-07'), ('1957-08-20', 'A', 'recession 1957-08'), ('1960-02-20', 'A', 'recession 1960-04'),
         ('1967-04-20', 'A', 'DISTURBANCE 1967'), ('1970-01-31', 'B', 'recession 1969-12'), ('1974-02-16', 'B', 'recession 1973-11'),
         ('1980-03-20', 'A', 'recession 1980-01'), ('1981-12-20', 'A', 'recession 1981-07'), ('1990-09-20', 'A', 'recession 1990-07'),
         ('2001-03-31', 'B', 'recession 2001-03'), ('2007-12-28', 'C', 'recession 2007-12'), ('2020-03-28', 'C', 'recession 2020-02'),
         ('2023-08-28', 'C', '2023-24 (Anthony: a recession)')]
PEAKS = ['1948-11', '1953-07', '1957-08', '1960-04', '1969-12', '1973-11', '1980-01', '1981-07', '1990-07', '2001-03', '2007-12', '2020-02', '2023-07']
TROUGHS = ['1949-10', '1954-05', '1958-04', '1961-02', '1970-11', '1975-03', '1980-07', '1982-11', '1991-03', '2001-11', '2009-06', '2020-04', '2026-02']

sp = pd.read_csv(f'{D}/sp500_daily_yahoo.csv', index_col=0, parse_dates=True).iloc[:, 0]
dd = (sp / sp.rolling(252, min_periods=200).max() - 1) * 100          # drawdown from the trailing-year high, per cent
r3 = (sp / sp.shift(63) - 1) * 100; r6 = (sp / sp.shift(126) - 1) * 100
baa = fred('BAA'); aaa = fred('AAA'); spr = baa - aaa; spr_gap = spr - spr.shift(1).rolling(12).min()
tb = fred('TB3MS'); g10 = fred('GS10'); term = (g10 - tb).dropna(); tb_d3 = tb - tb.shift(3)
cars = fred('M03002USM544NNBR'); cars_yoy = (cars / cars.shift(12) - 1) * 100
fail = fred('M09077USM234NNBR'); fail_yoy = (fail.rolling(3).mean() / fail.rolling(3).mean().shift(12) - 1) * 100

def at(s, day):
    """the latest observation at or before `day` (daily: that day; monthly: the month before, in hand)"""
    seg = s[:day].dropna(); return None if seg.empty else float(seg.iloc[-1])
def mon_at(s, day):
    d = pd.Timestamp(day); m = pd.Timestamp(d.year, d.month, 1) - pd.DateOffset(months=1)   # the month before the call is in hand
    return None if m not in s.index or pd.isna(s.get(m)) else float(s[m])
def fmt(v, w=7, p=1): return f'{v:{w}.{p}f}' if v is not None else ' ' * (w - 1) + '-'

print('PART ONE - every candidate at the sixteen claims calls (the objects that would have to carry the veto)')
print('call         leg  what                             S&P dd@call  min dd +30d  min dd +60d   r3m@call  r6m@call | Baa-Aaa gap  term  term-12m  bill d3m | cars yoy  failures yoy')
for day, leg, what in CALLS:
    d = pd.Timestamp(day)
    w30 = dd[d: d + pd.Timedelta(days=30)]; w60 = dd[d: d + pd.Timedelta(days=60)]
    t12 = pd.Timestamp(d.year - 1, d.month, 1)
    print(f'{day}   {leg}    {what:32s} {fmt(at(dd, d))}     {fmt(w30.min())}      {fmt(w60.min())}     {fmt(at(r3, d))}   {fmt(at(r6, d))} |  {fmt(mon_at(spr_gap, d), 6, 2)}    {fmt(mon_at(term, d), 5, 2)}  {fmt(None if t12 not in term.index else float(term[t12]), 5, 2)}    {fmt(mon_at(tb_d3, d), 5, 2)} | {fmt(mon_at(cars_yoy, d))}   {fmt(mon_at(fail_yoy, d))}')

print("\nthe S&P drawdown's separation: recessions' weakest reading against the disturbances' strongest, at the call and within thirty days")
rec = [(pd.Timestamp(day)) for day, leg, what in CALLS if what.startswith('recession')]
dis = [(pd.Timestamp(day)) for day, leg, what in CALLS if what.startswith('DIST')]
for label, f in (('at the call', lambda d: at(dd, d)), ('minimum within 30 days', lambda d: dd[d: d + pd.Timedelta(days=30)].min()), ('minimum within 60 days', lambda d: dd[d: d + pd.Timedelta(days=60)].min())):
    rv = [f(d) for d in rec]; dv = [f(d) for d in dis]
    print(f'  {label:24s} recessions: weakest {max(rv):6.1f} (all: {", ".join(f"{v:.1f}" for v in rv)});  disturbances: strongest {min(dv):6.1f} ({", ".join(f"{v:.1f}" for v in dv)});  2023: {f(pd.Timestamp("2023-08-28")):.1f}')

print('\nPART TWO - the S&P alone as a call object: first day the drawdown from the trailing-year high reached the line, per peak, and every other episode since 1948')
def episodes(line):
    """episode starts: the first day dd <= -line after at least 126 trading days above -line/2 (hysteresis)"""
    out = []; above = 0
    for t, v in dd.dropna().items():
        if v <= -line:
            if above >= 126: out.append(t)
            above = 0
        elif v > -line / 2: above += 1
    return out
for line in (5, 10, 15, 20):
    eps = episodes(line)
    rows = []; used = set()
    for p, q in zip(PEAKS, TROUGHS):
        P = pd.Timestamp(p + '-01'); pe = P + pd.offsets.MonthEnd(0)
        c = [e for e in eps if P - pd.DateOffset(months=9) <= e <= pd.Timestamp(q + '-01')]
        if c: e = c[0]; used.add(e); rows.append(f'{p}:{(e - pe).days:+d}d')
        else: rows.append(f'{p}:none')
    other = [e.strftime('%Y-%m') for e in eps if e not in used and e >= pd.Timestamp('1948-01-01')]
    print(f'  line {line:2d}%: ' + ' '.join(rows))
    print(f'           other episodes since 1948 ({len(other)}): {other}')

print('\nEXPOSURE of a stock-market veto: share of days on which the drawdown from the trailing-year high reaches the line within the next N days (quiet days = outside [peak-9m, trough+6m] of the thirteen)')
d = dd['1948':].dropna()
quiet = pd.Series(True, index=d.index)
for p, q in zip(PEAKS, TROUGHS):
    quiet[(d.index >= pd.Timestamp(p + '-01') - pd.DateOffset(months=9)) & (d.index <= pd.Timestamp(q + '-01') + pd.DateOffset(months=6))] = False
fwd60 = d[::-1].rolling(42, min_periods=1).min()[::-1]   # ~60 calendar days = 42 trading days
fwd30 = d[::-1].rolling(21, min_periods=1).min()[::-1]
for line in (5, 6, 7, 8, 10, 12, 15):
    print(f'  line {line:2d}%: within 30 days - all days {(fwd30 <= -line).mean() * 100:4.1f}%, quiet days {(fwd30[quiet] <= -line).mean() * 100:4.1f}%;   within 60 days - all {(fwd60 <= -line).mean() * 100:4.1f}%, quiet {(fwd60[quiet] <= -line).mean() * 100:4.1f}%')
print('  reading: a disturbance whose claims call lands on a random quiet day is wrongly confirmed with that probability; the three disturbances on the record (1951, 1952, 1967) all fell on the other side.')
