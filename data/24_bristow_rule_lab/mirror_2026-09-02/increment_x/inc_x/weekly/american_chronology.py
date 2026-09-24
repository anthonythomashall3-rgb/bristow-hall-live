"""The American chronology with ONE CALL and ONE DATE at every turn (3 September 2026, night).

Anthony: "for all of the peaks and troughs we want only one call, no confirmation call tagged
alongside; the peak and the trough calls should be the confirmation."  The tool's
american_chronology reads every leg in publication order as a state machine: the first peak
call opens a downturn and its date is the onset, final at the call; the first trough call
published after it and dated after the onset closes it, final at the call.  Nothing is
'pending', nothing is revised, nothing confirms anything later.

Legs (each as (published, dated); the objects with no dating clause of their own - the weekly
national conjunct B, the monthly conjunct M, the Philadelphia survey P - give the month of
the data they read, a convention stated as such):
  peaks    A  monthly state claims diffusion (Fieldhouse field, 36/8; dates)       C  weekly state breadth 1991 on (dates)
           B  national weekly conjunct 0.20 (the week's month)                     M  monthly conjunct 0.20, 1948 on (the data month)
  troughs  K  weekly continued claims level clause (dates)   I  weekly initial claims (dates)   D  the panel's own trough rule (dates)
           J  monthly continued claims, the field (dates)    H  monthly initial claims, the field (dates)
           P  Philadelphia Fed after D (the survey's month)  T  the diffusion index's own trough clause on leg A's index (dates)
Second condition (route B): Sahm's gap at 0.5 on the unemployment rate AS FIRST PUBLISHED (ALFRED
vintages from March 1960; the current vintage before) - the one object that separates 2024 from
1951 and 1967 in real time (lab/slack/ur_forms_rt.log: 1967 reached 0.43 on first prints, 0.47 on
FRED's SAHMREALTIME).

Variants printed: A-route (claims alone) and B-route (claims AND Sahm), each with and without
the survey leg P, and the B-route on dating legs only.  Scored against the committee as a
comparator (Rule 11): lag in days from the last day of the turn's month, date error in months,
and every call the committee has no turn for.  Output american_chronology.log.
"""
import sys, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0, '/home/claude'); sys.path.insert(0, '/home/claude/lab'); sys.path.insert(0, '/home/claude/lab/weekly'); sys.path.insert(0, '/home/claude/lab/fh'); sys.path.insert(0, '/home/claude/lab/rt')
import numpy as np, pandas as pd, bristow_rule_v3 as B
import union_peaks as U, union_troughs as T, legs_1948 as L, alfred

PK = [pd.Timestamp(x) for x in ('1948-11', '1953-07', '1957-08', '1960-04', '1969-12', '1973-11', '1980-01', '1981-07', '1990-07', '2001-03', '2007-12', '2020-02')]
TR = [pd.Timestamp(x) for x in ('1949-10', '1954-05', '1958-04', '1961-02', '1970-11', '1975-03', '1980-07', '1982-11', '1991-03', '2001-11', '2009-06', '2020-04')]
def md(a, b): return (a.year - b.year) * 12 + a.month - b.month
def month_end(t): return t + pd.offsets.MonthEnd(0)
def mon(t): return pd.Timestamp(t.year, t.month, 1)

SAFE = dict(H=8.0, J=5.0, I=20.0, K=4.0)   # trough_floor.py: the lowest drop on each clause with no 1970 misfire (K's shipped 4 already has none)

def legs(safe=True, with_S=False, with_U=False):
    A = U.leg_A(); C = U.leg_C()
    Bw = [(p, mon(p - pd.Timedelta(days=7))) for p, _ in U.leg_B(0.20)]                 # the week's month
    M = [(p, mon(p - pd.DateOffset(months=1))) for p, _ in L.leg_M(0.20)]                # the data month (published the 10th of the month after)
    K = T.leg_K(); D = T.leg_D()
    P = [(p, mon(p)) for p, _ in T.leg_P()]                                              # the survey's month
    nat = L._nat_rt(); icm = np.log(nat['initial claims'].dropna()); ccm = np.log(nat['continued weeks claimed'].dropna())
    if safe:
        H = [(L.pub10(p - pd.DateOffset(months=1)), d) for p, d in B.level_trough_calls(icm, drop=SAFE['H'])]
        J = [(L.pub10(p - pd.DateOffset(months=1)), d) for p, d in B.level_trough_calls(ccm, drop=SAFE['J'])]
        import cc_trough_grid as CG
        src = open('/home/claude/lab/weekly/final_caller.py').read(); g = {'pd': pd, 'np': np, 'mo': mon, 'md': md}
        exec("def trough_calls" + src.split("def trough_calls")[1].split("def sc(")[0], g)
        N = (np.log(CG.W['ic_sa_rt']) * 100.0).rolling(8).mean()
        DI = pd.concat([N.rename('n'), (N - N.rolling(52, min_periods=26).min()).rename('g')], axis=1, sort=True).dropna()
        I = g['trough_calls'](DI, 6, SAFE['I'], 40., 13)
    else:
        H = L.leg_H(); J = L.leg_J(); I = T.leg_I()
    H = [x for x in H if x[0] >= L.RECORD_START]; J = [x for x in J if x[0] >= L.RECORD_START]
    # T: the Department's monthly index (48/13), its own trough clause - the object that ends a downturn the level clauses never arm on (2023-26)
    PAN = pd.read_csv('/home/claude/lab/dol/US_state_monthly_4ch_sa.csv', index_col=0, parse_dates=True)
    cols = [c for c in PAN.columns if c.endswith('| initial claims') or c.endswith('| continued weeks claimed')]
    Dx = B.claims_diffusion(PAN[cols], 48., 13)
    Tt = [(pd.Timestamp(p.year, p.month, 20), d) for p, d in B.diffusion_trough_calls(Dx)]
    # F: the same clause on leg A's own index (the Fieldhouse field, 36/8), 1947-2024 - the object that ends the field's mild episodes before 1971
    Pn = pd.read_csv('/home/claude/lab/fh/FH_state_claims_sa_rt_log.csv', index_col=0, parse_dates=True)
    Xf = Pn.rolling(2).mean().dropna(how='all'); Df = B.claims_diffusion(Xf, 36., 8)
    Ff = [(pd.Timestamp(p.year, p.month, 20), d) for p, d in B.diffusion_trough_calls(Df)]
    TL = dict(K=K, I=I, D=D, J=J, H=H, P=P, T=Tt, F=Ff)
    if with_S:
        TL['S'] = leg_S_gated(sahm_rt(), claims_armed())
    PLd = dict(A=A, B=Bw, C=C, M=M)
    if with_U: PLd['U'] = leg_U()
    return PLd, TL


def leg_U(line=0.50, smooth=1, back=52, quiet=26, pub=5):
    """Leg U (version 43, 4 September 2026): the insured unemployment rate - claims paid as a share of covered
    employment, the Department's own weekly rate (FRED IURSA, 1971-) - `smooth`-week mean `line` points above its
    52-week minimum, after at least `quiet` weeks below it; published `pub` days after the week (the Department's
    Thursday release); dated to the month of the week that crossed.

    The line is the Paper 2 chat's own published backstop line (0.50); the form and the line were chosen here
    leave-one-recession-out over smoothings 1-8 weeks and lines 0.30-0.70, and every one of the twelve folds picks
    (1 week, 0.50) - `iur_loo.py`.  The leg makes seven calls in fifty-five years and every one falls inside a
    recession window: it adds no quiet-period call, so under the conjunction it adds no measurable false-alarm
    hazard (memo 8v), while taking the route's median onset lag from 40 to 30 days and the worst from 142 to 126."""
    x = pd.read_csv('/home/claude/archive/data/fred/IURSA.csv'); x.columns = ['d', 'v']
    s = x.set_index(pd.to_datetime(x['d']))['v'].astype(float)
    m = s.rolling(smooth).mean(); gap = (m - m.rolling(back, min_periods=26).min()).dropna()
    out = []; below = 0
    for t, v in gap.items():
        if v >= line:
            if below >= quiet: out.append((t + pd.Timedelta(days=pub), pd.Timestamp(t.year, t.month, 1)))
            below = 0
        else: below += 1
    return out

def sahm_rt():
    cur = pd.read_csv('/home/claude/archive/data/fred/UNRATE.csv'); cur.columns = ['d', 'v']; cur['d'] = pd.to_datetime(cur['d']); cur = cur.set_index('d')['v'].astype(float)
    fp = alfred.first_prints('UNRATE')
    rt = pd.concat([cur[cur.index < fp.index.min()], fp]).sort_index()
    return B.sahm_gap(rt)

def vacancy_gap(k=3, back=12):
    """The vacancy rate's fall: the k-month mean below its maximum over the previous `back` months, in points
    (Petrosky-Nadeau-Zhang to 2000, JOLTS after - lab/vac/vacancy_rate_PNZ_JOLTS.csv; current vintage, the
    reconstruction; lab/speed2/vacancy_veto.log, vacancy_forms.log).  (3, 12) is Sahm's form at line 0.6 (version 37);
    (2, 6) at line 0.36 is the fast form of version 38 - the two-month mean 0.36 points below its six-month
    maximum.  Public near the end of the month after (pub_day 30)."""
    sys.path.insert(0, '/home/claude/lab/slack')
    from objects import load
    v = -load()['-vacancy rate']; m = v.rolling(k).mean()
    return (m.shift(1).rolling(back).max() - m).dropna()

def vacancy_gap_rt(k=2, back=6):
    """The same object with JOLTS AS FIRST PUBLISHED from the first ALFRED vintage (August 2010): the vacancy rate rebuilt
    each month as first-print openings over payrolls plus openings, the current-vintage series before - the treatment
    the unemployment rate gets (first prints from 1960).  lab/speed2/vacancy_forms_rt.log."""
    sys.path.insert(0, '/home/claude/lab/slack')
    from objects import load
    v = -load()['-vacancy rate']
    pay = pd.read_csv('/home/claude/lab/cps/03_payroll_employment/monthly/PAYEMS.csv'); pay.columns = ['d', 'v']; pay['d'] = pd.to_datetime(pay['d']); pay = pay.set_index('d')['v'].astype(float)
    fp = alfred.first_prints('JTSJOL')
    first_vintage = alfred.vintages('JTSJOL')[0]                      # August 2010: months before it carry that vintage's revised values, not first prints
    fp = fp[fp.index >= pd.Timestamp(first_vintage.year, first_vintage.month, 1) - pd.DateOffset(months=2)]
    rate_fp = (fp / (pay.reindex(fp.index) + fp) * 100).dropna()
    rt = pd.concat([v[v.index < rate_fp.index.min()], rate_fp]).sort_index()
    m = rt.rolling(k).mean()
    return (m.shift(1).rolling(back).max() - m).dropna()

def leg_S(gap, line=0.5, below=3, pub_day=5):
    """the same rule ungated (measured: it ends 1973-75 in March 1974); see the tool's sahm_end_calls"""
    return B.sahm_end_calls(gap, armed=None, line=line, below=below, pub_day=pub_day)

def _leg_S_old(gap, line=0.5, below=3, pub_day=5):
    """Paper 1's own end rule as a trough leg (S): the downturn ends in the month Sahm's gap attains its episode maximum;
    called when `below` consecutive monthly readings have printed below that maximum, and only once the maximum has
    stood at Sahm's line or above (an episode the rate never confirmed cannot be ended by the rate).  Read on the rate
    as first published; each call is published the `pub_day`th of the month after the third reading.  A running
    object: every month the running maximum since the last call is tracked, so the leg emits a call at every such
    turn of the gap - the route's state machine takes the first one after an onset.  Paper 1's record: all twelve
    within three months of the committee's troughs, no called maximum ever exceeded afterwards."""
    out = []; runmax = None; runmax_t = None; n_below = 0; armed = False; prev = None
    for t, v in gap.items():
        if not armed:
            if v >= line and (prev is None or prev < line):      # the gap crosses Sahm's line from below: an episode of the rate opens
                armed = True; runmax = float(v); runmax_t = t; n_below = 0
        else:
            if v > runmax:
                runmax = float(v); runmax_t = t; n_below = 0
            else:
                n_below += 1
                if n_below >= below:
                    out.append((pd.Timestamp(t.year, t.month, 1) + pd.DateOffset(months=1) + pd.Timedelta(days=pub_day - 1), runmax_t))
                    armed = False                                   # the episode's end is called; the next needs a fresh crossing of the line
        prev = float(v)
    return out

def claims_armed():
    """A monthly flag: TRUE in any month in which a claims level object stood ARMED - the weekly continued claims'
    four-week mean 30 log points above its 52-week minimum (leg K's arm), the weekly initial claims' eight-week mean 40
    above (leg I's), or the field's monthly initial or continued claims 50 above their 30-month minimum (legs H/J's,
    level_trough_calls' arm_gap) - the state in which those legs can end a downturn.  Leg S is admitted only in
    episodes where this flag never rose after the rate's crossing: a downturn the claims field never carried far
    enough to end is ended by the rate's own rule (Paper 1's), and a claims recession is ended by the claims legs."""
    import cc_trough_grid as CG
    N = pd.read_csv('/home/claude/lab/weekly/DOL_national_weekly_claims_sa_rt.csv', index_col=0, parse_dates=True)
    def gap(col, sm, arm):
        n = (np.log(N[col]) * 100.0).rolling(sm).mean(); g = (n - n.rolling(52, min_periods=26).min()).dropna()
        return (g >= arm).resample('MS').max()
    wk = pd.concat([gap('cc_sa_rt', 4, 30.0), gap('ic_sa_rt', 8, 40.0)], axis=1).max(axis=1)
    nat = L._nat_rt()
    def mgap(col):
        x = (np.log(nat[col].dropna()) * 100.0).rolling(2).mean(); g = (x - x.rolling(30, min_periods=12).min()).dropna()
        return (g >= 50.0)
    mo = pd.concat([mgap('initial claims'), mgap('continued weeks claimed')], axis=1).max(axis=1)
    allf = pd.concat([wk, mo], axis=1).max(axis=1).fillna(0).astype(bool)
    allf.index = pd.DatetimeIndex([pd.Timestamp(t.year, t.month, 1) for t in allf.index])
    return allf.groupby(level=0).max()

def leg_S_gated(gap, armed, line=0.5, below=3, pub_day=5):
    """the tool's sahm_end_calls with the claims field's arming as its gate (leg S of the route from version 39)"""
    return B.sahm_end_calls(gap, armed=armed, line=line, below=below, pub_day=pub_day)

def score(turns, label, start='1948-06-01'):
    pk = [t for t in turns if t['kind'] == 'peak' and t['published'] >= pd.Timestamp(start)]
    tr = [t for t in turns if t['kind'] == 'trough' and t['published'] >= pd.Timestamp(start)]
    print(f'\n=== {label}')
    print('  onset call        leg  date      committee   lag(d)  err   |  end call          leg  date      committee   lag(d)  err')
    used_p = set(); used_t = set(); rows = []
    lags_p = []; errs_p = []; lags_t = []; errs_t = []
    for t in pk:
        c = [i for i, (p, q) in enumerate(zip(PK, TR)) if p - pd.DateOffset(months=6) <= t['date'] <= q]
        c = [i for i in c if i not in used_p]
        cm = None if not c else c[0]
        if cm is not None:
            used_p.add(cm); lag = (t['published'] - month_end(PK[cm])).days; err = md(t['date'], PK[cm]); lags_p.append(lag); errs_p.append(err)
        # the trough that closed this episode
        nxt = [u for u in tr if u['published'] > t['published']]
        u = nxt[0] if nxt else None
        tl = ''
        if u is not None:
            ct = [i for i, q in enumerate(TR) if abs(md(u['date'], q)) <= 6 and i not in used_t]
            if cm is not None and cm in ct: ct = [cm]
            if ct:
                used_t.add(ct[0]); lagt = (u['published'] - month_end(TR[ct[0]])).days; errt = md(u['date'], TR[ct[0]]); lags_t.append(lagt); errs_t.append(errt)
                tl = f"{u['published']:%Y-%m-%d}   {u['leg']:3s}  {u['date']:%Y-%m}   {TR[ct[0]]:%Y-%m}     {lagt:5d}   {errt:+d}"
            else:
                tl = f"{u['published']:%Y-%m-%d}   {u['leg']:3s}  {u['date']:%Y-%m}   none"
        else:
            tl = 'open'
        pl = f"{t['published']:%Y-%m-%d}   {t['leg']:3s}  {t['date']:%Y-%m}   " + (f"{PK[cm]:%Y-%m}     {lag:5d}   {err:+d}" if cm is not None else 'none              ')
        print('  ' + pl + '   |  ' + tl)
    n = len(PK)
    print(f"  peaks: {len(used_p)}/{n} committee peaks called; other onset calls {len(pk) - len(used_p)}; lag median {np.median(lags_p):.0f} d, worst {max(lags_p)}, inside the month {sum(1 for l in lags_p if l <= 0)}, within a month after {sum(1 for l in lags_p if l <= 31)}; dates exact {sum(1 for e in errs_p if e == 0)}, within one {sum(1 for e in errs_p if abs(e) <= 1)}, mae {np.mean(np.abs(errs_p)):.2f}")
    print(f"  troughs: {len(used_t)}/{n} committee troughs closed; lag median {np.median(lags_t):.0f} d, worst {max(lags_t)}, within a month after {sum(1 for l in lags_t if l <= 31)}; dates exact {sum(1 for e in errs_t if e == 0)}, within one {sum(1 for e in errs_t if abs(e) <= 1)}, mae {np.mean(np.abs(errs_t)):.2f}")
    return dict(lags_p=lags_p, errs_p=errs_p, lags_t=lags_t, errs_t=errs_t, other=len(pk) - len(used_p))

if __name__ == '__main__':
    PL, TLu = legs(safe=False); _, TL = legs(safe=True)
    for k, v in PL.items(): print(f'peak leg {k}: {len(v)} calls; ' + ', '.join(f'{p:%Y-%m-%d}>{d:%Y-%m}' for p, d in v))
    for k, v in TL.items(): print(f'trough leg {k} (safe drops {SAFE}): {len(v)} calls; ' + ', '.join(f'{p:%Y-%m-%d}>{d:%Y-%m}' for p, d in v))
    g = sahm_rt()
    print('\n---- the shipped trough clauses (drop 1 / 1 / 10 / 4): the 1970 pause ends the recession in May 1970')
    score(B.american_chronology(PL, TLu), 'ROUTE A, shipped trough drops, all legs')
    score(B.american_chronology(PL, TLu, sahm=g), 'ROUTE B, shipped trough drops, all legs')
    print('\n---- trough clauses at their 1970 floor (H 8, J 5, I 20, K 4)')
    score(B.american_chronology(PL, TL), 'ROUTE A - the claims objects alone, one call one date, all legs')
    score(B.american_chronology(PL, {k: v for k, v in TL.items() if k != 'P'}), 'ROUTE A without the survey leg P')
    score(B.american_chronology(PL, TL, sahm=g), 'ROUTE B - claims AND Sahm 0.5 (first prints); the claims date; all legs')
    score(B.american_chronology(PL, TL, sahm=g, date_rule='later'), "ROUTE B with version 35's 'later' date rule")
    score(B.american_chronology(PL, {k: v for k, v in TL.items() if k != 'P'}, sahm=g), 'ROUTE B without the survey leg P')
    score(B.american_chronology({k: v for k, v in PL.items() if k in ('A', 'C')}, TL, sahm=g), 'ROUTE B on dating peak legs only (A, C)')
    vg = vacancy_gap()
    for vline in (0.5, 0.6, 0.8):
        score(B.american_chronology(PL, TL, sahm=g, second=[dict(name='vacancy', gap=vg, line=vline, pub_day=30)]),
              f"ROUTE B' - claims AND (Sahm 0.5 OR the vacancy rate's fall >= {vline}); the claims date; all legs")
    score(B.american_chronology(PL, TL, second=[dict(name='vacancy', gap=vg, line=0.6, pub_day=30)]), 'the vacancy rate alone as the second condition (0.6)')
    vf = vacancy_gap(2, 6)
    score(B.american_chronology(PL, TL, sahm=g, second=[dict(name='vacancy(2,6)', gap=vf, line=0.36, pub_day=30)]),
          "ROUTE B'' - claims AND (Sahm 0.5 OR the vacancy rate's fast form (2, 6) >= 0.36); the claims date; all legs")
    score(B.american_chronology(PL, TL, second=[dict(name='vacancy(2,6)', gap=vf, line=0.36, pub_day=30)]), 'the fast vacancy form alone as the second condition (0.36)')
    vr = vacancy_gap_rt(2, 6)
    score(B.american_chronology(PL, TL, sahm=g, second=[dict(name='vacancy(2,6)', gap=vr, line=0.36, pub_day=30)]),
          "ROUTE B'' on first prints - the vacancy rate as first published from August 2010 (JOLTS vintages), current vintage before")
    S = leg_S(g)
    print(f"\nleg S (Paper 1's end rule on the rate as first published): {len(S)} calls; " + ', '.join(f'{p:%Y-%m-%d}>{d:%Y-%m}' for p, d in S if p >= pd.Timestamp('1948-06-01')))
    TLS = dict(TL); TLS['S'] = S
    score(B.american_chronology(PL, TLS, sahm=g, second=[dict(name='vacancy(2,6)', gap=vr, line=0.36, pub_day=30)]),
          "ROUTE B'' with leg S (Paper 1's Sahm-maximum end) among the trough legs, ungated - the 1974 plateau ends the recession")
    arm = claims_armed(); Sg = leg_S_gated(g, arm)
    print(f"leg S gated by the claims field (admitted only where no level object armed): {len(Sg)} calls; " + ', '.join(f'{p:%Y-%m-%d}>{d:%Y-%m}' for p, d in Sg if p >= pd.Timestamp('1948-06-01')))
    print('months in which a claims level object stood armed, by year (count):', arm.groupby(arm.index.year).sum()[lambda x: x > 0].to_dict())
    TLG = dict(TL); TLG['S'] = Sg
    score(B.american_chronology(PL, TLG, sahm=g, second=[dict(name='vacancy(2,6)', gap=vr, line=0.36, pub_day=30)]),
          "ROUTE B'' with leg S gated by the claims field's arming - THE CANDIDATE")
    PLU = dict(PL); PLU['U'] = leg_U()
    score(B.american_chronology(PLU, TLG, sahm=g, second=[dict(name='vacancy(2,6)', gap=vr, line=0.36, pub_day=30)]),
          "ROUTE B'' + leg S + LEG U (the insured unemployment rate, 1-week, 0.50) - THE VERSION-43 DEFAULT")
    turns = B.american_chronology(PL, TLG, sahm=g, second=[dict(name='vacancy(2,6)', gap=vr, line=0.36, pub_day=30)])
    print("\nthe chronology under ROUTE B'' with the gated leg S, every turn:")
    for t in turns:
        if t['published'] < pd.Timestamp('1948-06-01'): continue
        extra = f"  (claims call {t['claims_published']:%Y-%m-%d}; {t['condition']} crossing {t['sahm_month']:%Y-%m})" if 'sahm_month' in t else ''
        print(f"  {t['kind']:6s} called {t['published']:%Y-%m-%d} by {t['leg']:2s} dated {t['date']:%Y-%m}{extra}")
    turns = B.american_chronology(PL, TL, sahm=g, second=[dict(name='vacancy(2,6)', gap=vr, line=0.36, pub_day=30)])
    print("\nthe chronology under ROUTE B'' (Sahm 0.5 or vacancy (2,6) 0.36; first prints), every turn:")
    for t in turns:
        if t['published'] < pd.Timestamp('1948-06-01'): continue
        extra = f"  (claims call {t['claims_published']:%Y-%m-%d}; {t['condition']} crossing {t['sahm_month']:%Y-%m})" if 'sahm_month' in t else ''
        print(f"  {t['kind']:6s} called {t['published']:%Y-%m-%d} by {t['leg']:2s} dated {t['date']:%Y-%m}{extra}")
    turns = B.american_chronology(PL, TL, sahm=g, second=[dict(name='vacancy', gap=vg, line=0.6, pub_day=30)])
    print("\nthe chronology under ROUTE B' (Sahm 0.5 or vacancy 0.6), every turn:")
    for t in turns:
        if t['published'] < pd.Timestamp('1948-06-01'): continue
        extra = f"  (claims call {t['claims_published']:%Y-%m-%d}; {t['condition']} crossing {t['sahm_month']:%Y-%m})" if 'sahm_month' in t else ''
        print(f"  {t['kind']:6s} called {t['published']:%Y-%m-%d} by {t['leg']:2s} dated {t['date']:%Y-%m}{extra}")
    turns = B.american_chronology(PL, TL, sahm=g)
    print('\nthe chronology under ROUTE B (claims date, all legs, safe drops), every turn - one call, one date:')
    for t in turns:
        if t['published'] < pd.Timestamp('1948-06-01'): continue
        extra = f"  (claims call {t['claims_published']:%Y-%m-%d}, Sahm crossing {t['sahm_month']:%Y-%m})" if 'sahm_month' in t else ''
        print(f"  {t['kind']:6s} called {t['published']:%Y-%m-%d} by {t['leg']:2s} dated {t['date']:%Y-%m}{extra}")
    turns = B.american_chronology(PL, TL)
    print('\nthe chronology under ROUTE A (claims alone, all legs, safe drops), every turn:')
    for t in turns:
        if t['published'] < pd.Timestamp('1948-06-01'): continue
        print(f"  {t['kind']:6s} called {t['published']:%Y-%m-%d} by {t['leg']:2s} dated {t['date']:%Y-%m}")
