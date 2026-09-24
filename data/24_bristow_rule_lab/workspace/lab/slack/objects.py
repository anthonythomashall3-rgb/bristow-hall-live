"""Every American labor-slack object on hand, monthly, in one frame - the household survey's
components, the payroll survey's hours and temporary help, the claims field's insured rate, the
vacancy rate, and the states' unemployment rates.  Built 3 September 2026 for the question Anthony
put: is there an object that is present in the twelve committee recessions AND in 2024, absent in
1951 and 1967, and fast?

Sources (all on the Mac, copied to lab/cps on 3 September 2026; current vintage unless noted):
  01_labor_unemployment/monthly  - CPS: UNRATE, UEMPLT5, UEMP5TO14, UEMP15OV, UEMPMEAN, UEMPMED,
                                   CLF16OV, EMRATIO, CIVPART, U6RATE, LNS13023621 (job losers),
                                   LNS13023653 (on temporary layoff), LNS13023654 (not on layoff),
                                   LNS13023705 (permanent job losers), LNS12300060 (prime-age EPOP)
  03_payroll_employment/monthly  - CE16OV, LNS12032194 (part time for economic reasons), TEMPHELPS,
                                   PAYEMS, MANEMP, USPRIV
  04_hours_earnings/monthly      - AWHMAN, AWOTMAN
  18_regional_state/state/monthly, 01_labor_unemployment/monthly/LAUST* - state unemployment rates
                                   (44 FRED files; IA KS KY SC SD TN TX rebuilt from LAUS unemployed and
                                   employed counts, LAUST..04 / LAUST..05)
  lab/fh/FH_national.csv         - Fieldhouse et al. USIUR (insured unemployment rate, 1947 on)
  lab/vac/vacancy_rate_PNZ_JOLTS.csv - vacancy rate, Petrosky-Nadeau-Zhang to 2000, JOLTS after
"""
import glob, os, re
import numpy as np, pandas as pd

ROOT = '/home/claude/lab/cps'
U = f'{ROOT}/01_labor_unemployment/monthly'; P = f'{ROOT}/03_payroll_employment/monthly'
H = f'{ROOT}/04_hours_earnings/monthly'; S = f'{ROOT}/18_regional_state/state/monthly'

def fred(path):
    d = pd.read_csv(path); d.columns = ['date', 'v']
    d['date'] = pd.to_datetime(d['date']); s = d.set_index('date')['v']
    s = pd.to_numeric(s, errors='coerce').dropna()
    s.index = pd.DatetimeIndex([pd.Timestamp(t.year, t.month, 1) for t in s.index])
    return s

def load():
    """Returns a dict of monthly Series, each a rate in percentage points (or an index)."""
    g = lambda d, n: fred(f'{d}/{n}.csv')
    o = {}
    ur = g(U, 'UNRATE'); clf = g(U, 'CLF16OV')
    o['UR'] = ur
    o['U<5w'] = g(U, 'UEMPLT5') / clf * 100          # short-term unemployed, share of labor force
    o['U5-14w'] = g(U, 'UEMP5TO14') / clf * 100
    o['U<15w'] = (g(U, 'UEMPLT5') + g(U, 'UEMP5TO14')) / clf * 100
    o['U15w+'] = g(U, 'UEMP15OV') / clf * 100
    o['job losers'] = (g(U, 'LNS13023621') / clf * 100).dropna()          # 1967 on
    o['on layoff'] = (g(U, 'LNS13023653') / clf * 100).dropna()           # 1967 on
    o['not on layoff'] = (g(U, 'LNS13025699') / clf * 100).dropna()       # 1967 on
    o['permanent losers'] = ((g(U, 'LNS13025699') - g(U, 'LNS13023705')) / clf * 100).dropna()  # not on layoff less completed temporary jobs, 1967 on
    o['PTER'] = (g(P, 'LNS12032194') / clf * 100).dropna()     # 1955 on
    o['U6'] = g(U, 'U6RATE')                                   # 1994 on
    o['-EPOP'] = -g(U, 'EMRATIO')                              # sign flipped: a rise is slack
    o['-EPOP 25-54'] = -g(U, 'LNS12300060')
    o['-hours mfg'] = -g(H, 'AWHMAN')
    o['-overtime mfg'] = -g(H, 'AWOTMAN')                      # 1956 on
    o['-temp help (log)'] = -np.log(g(P, 'TEMPHELPS')) * 100   # 1990 on
    o['-household emp (log)'] = -np.log(g(P, 'CE16OV')) * 100
    o['-payrolls (log)'] = -np.log(g(P, 'PAYEMS')) * 100
    o['mean duration'] = g(U, 'UEMPMEAN')
    fh = pd.read_csv('/home/claude/lab/fh/FH_national.csv', index_col=0, parse_dates=True)
    o['IUR (FH)'] = fh['USIUR'].dropna()
    v = pd.read_csv('/home/claude/lab/vac/vacancy_rate_PNZ_JOLTS.csv', index_col=0, parse_dates=True).iloc[:, 0]
    vs = v.copy(); vs.index = pd.DatetimeIndex([pd.Timestamp(t.year, t.month, 1) for t in vs.index])
    o['-vacancy rate'] = -pd.to_numeric(vs, errors='coerce').dropna()
    return o

def state_ur():
    """State unemployment rates, seasonally adjusted, 1976 on: 44 FRED files plus seven rebuilt."""
    cols = {}
    for f in sorted(glob.glob(f'{S}/??UR.csv')):
        st = os.path.basename(f)[:2]; cols[st] = fred(f)
    fips = {'19': 'IA', '20': 'KS', '21': 'KY', '46': 'SD', '47': 'TN', '48': 'TX', '72': 'PR'}
    for code, st in fips.items():
        try:
            un = fred(f'{U}/LAUST{code}0000000000004.csv'); em = fred(f'{U}/LAUST{code}0000000000005.csv')
            cols[st] = (un / (un + em) * 100).dropna()
        except FileNotFoundError:
            pass
    df = pd.DataFrame(cols).sort_index()
    return df.drop(columns=[c for c in ('PR',) if c in df.columns])

def sahm(s, k=3, back=12):
    """Sahm's form: the k-month mean less its minimum over the previous `back` months."""
    m = s.rolling(k).mean()
    return (m - m.shift(1).rolling(back).min()).dropna()

def gap1(s, back=12):
    """One-month form: the month's value less the minimum of the previous `back` months."""
    return (s - s.shift(1).rolling(back).min()).dropna()

if __name__ == '__main__':
    o = load()
    for k, s in o.items():
        print(f'{k:24s} {s.index.min():%Y-%m} to {s.index.max():%Y-%m}  n={len(s)}  last={s.iloc[-1]:.2f}')
    su = state_ur(); print('state UR', su.shape, su.index.min().date(), su.index.max().date(), sorted(su.columns))
