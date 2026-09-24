#!/usr/bin/env python3
"""The financial-leg conjunction: a labour proposer confirmed by a money, activity or
diffusion leg. Built independently of the live tool; nothing here touches v3.29.

WHY THIS SHAPE. Five exhaustive sweeps (collections 113, 114, 127, 171, 173, 174) have now
established that no single series and no panel-breadth summary detects recessions cleanly.
The one thing that has ever worked in this programme is a CONJUNCTION between specific,
causally different objects, because each leg kills the other's false alarms -- collection
105's q40 measured exactly that: the market gate alone fired in nine episodes, the claims
week alone eleven times, the conjunction twice and never outside a recession.

The archive review of 15 September found four objects that each cover the peaks the
labour-only rule misses, and NONE of them is in the tool:

  collection 85   a term-spread gate -- the only thing ever recorded as moving this
                  programme's causal frontier outward (detection 0 -> 42 at a
                  ten-false-alarm budget). Its three named next steps were never built.
  collection 164  the paper-bill spread -- calls November 1973 at -43 days and December
                  2007 at -104, the two peaks labour handles worst.
  collection 165  the Chicago Fed activity index -- zero false alarms in 66 years,
                  March 2001 at -29 days and February 2020 at -30.
  collection 173  the Philadelphia Fed diffusion index -- May 1968 to today, still live,
                  and it reaches the monetary and energy peaks on its OWN observations.

THE RULE. A labour object PROPOSES. A money, activity or diffusion object CONFIRMS within a
window. Neither side alone can open a recession. Every line is an expanding quantile of the
object's own prior values, shifted, so nothing is informed by its own crossing. Publication
lag is charged. An episode re-arms only after a minimum expansion.

Nothing is chosen by looking at what wins: every proposer, every confirmer, every window and
every quantile is run and the whole grid is written out.
"""
import itertools, json, os, sys, numpy as np, pandas as pd, warnings
warnings.filterwarnings('ignore')

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA, OUT = os.path.join(HERE, 'data'), os.path.join(HERE, 'out')
os.makedirs(OUT, exist_ok=True)

PEAKS = ['1948-11','1953-07','1957-08','1960-04','1969-12','1973-11',
         '1980-01','1981-07','1990-07','2001-03','2007-12','2020-02']
TROUGHS = ['1949-10','1954-05','1958-04','1961-02','1970-11','1975-03',
           '1980-07','1982-11','1991-03','2001-11','2009-06','2020-04']
CRUNCH = ('1965-07','1968-06')
WIN_EARLY, WIN_LATE = -92, -1
LAG = {'D': 1, 'W': 12, 'M': 40, 'Q': 120}


def me(ym): return pd.Timestamp(ym + '-01') + pd.offsets.MonthEnd(0)
PK, TR = [me(p) for p in PEAKS], [me(t) for t in TROUGHS]
def inside(t): return any(p <= t <= tr for p, tr in zip(PK, TR))


def rd(sid):
    d = pd.read_csv(os.path.join(DATA, sid + '.csv')); c = list(d.columns)
    s = pd.Series(pd.to_numeric(d[c[1]], errors='coerce').values,
                  index=pd.to_datetime(d[c[0]], errors='coerce'))
    s = s[~s.index.isna()].dropna().sort_index()
    return s[~s.index.duplicated(keep='last')]


def freq_of(s):
    d = np.median(np.diff(s.index.values).astype('timedelta64[D]').astype(int))
    return 'D' if d <= 3 else ('W' if d <= 10 else ('M' if d <= 45 else 'Q'))


def to_month(s):
    """Charge the publication lag, then carry to a month-end grid, causally."""
    t = s.copy(); t.index = t.index + pd.Timedelta(days=LAG[freq_of(s)])
    idx = pd.date_range('1919-01-31', '2026-09-30', freq='ME')
    return t.reindex(idx.union(t.index)).ffill().reindex(idx)


def build_objects():
    """Each object is oriented so that HIGH = deteriorating."""
    o = {}
    # labour proposers
    u = rd('UNRATE')
    o['sahm_gap'] = to_month(u.rolling(3).mean() - u.rolling(12).min())
    ic = rd('ICNSA').rolling(4).mean()
    o['claims_vs_low'] = to_month(ic / ic.rolling(52).min() - 1.0)
    iur = rd('IURNSA')
    o['insured_vs_low'] = to_month(iur - iur.rolling(52).min())
    cc = rd('CCNSA').rolling(4).mean()
    o['contclaims_vs_low'] = to_month(cc / cc.rolling(52).min() - 1.0)
    pe = rd('PAYEMS'); o['payems_fall'] = to_month(-(pe.pct_change(3)))
    aw = rd('AWHMAN'); o['hours_fall'] = to_month(-(aw - aw.rolling(12).max()))
    th = rd('TEMPHELPS'); o['temphelp_fall'] = to_month(-(th.pct_change(6)))
    # money and credit confirmers
    baa, aaa, tb = rd('BAA'), rd('AAA'), rd('TB3MS')
    o['baa_aaa'] = to_month((baa - aaa))
    o['baa_tbill'] = to_month((baa - tb.reindex(baa.index, method='ffill')))
    pr = rd('MPRIME'); o['prime_tbill'] = to_month(pr - tb.reindex(pr.index, method='ffill'))
    # paper-bill spread, spliced: finance paper to 1996, AA financial from 1997
    fp = pd.concat([rd('H0RIFSPPFM06NB'), rd('DCPF3M')]).sort_index()
    fp = fp[~fp.index.duplicated(keep='last')]
    b3 = rd('DTB3')
    pb = (fp - b3.reindex(fp.index, method='ffill')).dropna()
    o['paper_bill'] = to_month(pb.rolling(20).mean())
    # term spread -- collection 85's gate, as a LEVEL (one of its three unbuilt next steps)
    g10, g1 = rd('GS10'), rd('GS1')
    o['term_inv'] = to_month(-(g10 - g1.reindex(g10.index, method='ffill')))
    # activity confirmers
    o['cfnai_fall'] = to_month(-rd('CFNAIMA3'))
    o['cfnaidiff_fall'] = to_month(-rd('CFNAIDIFF'))
    ip = rd('INDPRO'); o['indpro_fall'] = to_month(-(ip.pct_change(6)))
    im = rd('IPMAT'); o['ipmat_fall'] = to_month(-(im.pct_change(6)))
    # diffusion confirmers -- live, and reach 1968
    for k, sid in [('philly_gac','GACDFSA066MSFRBPHI'), ('philly_no','NOCDFSA066MSFRBPHI'),
                   ('philly_emp','NECDFSA066MSFRBPHI')]:
        o[k] = to_month(-rd(sid))
    return {k: v.replace([np.inf, -np.inf], np.nan) for k, v in o.items()}


PROPOSERS = ['sahm_gap','claims_vs_low','insured_vs_low','contclaims_vs_low',
             'payems_fall','hours_fall','temphelp_fall']
CONFIRMERS = ['baa_aaa','baa_tbill','prime_tbill','paper_bill','term_inv',
              'cfnai_fall','cfnaidiff_fall','indpro_fall','ipmat_fall',
              'philly_gac','philly_no','philly_emp']


def over_line(s, q, minobs=120):
    line = s.shift(1).expanding(min_periods=minobs).quantile(q)
    return (s > line) & line.notna()


def emit(prop, conf, win, min_expansion=6):
    """Proposer fires; a confirmer must be over its own line within `win` months either
    side. Neither alone opens anything. Re-arm after a minimum expansion."""
    cw = conf.rolling(2 * win + 1, center=True, min_periods=1).max().astype(bool)
    fire = prop & cw
    calls, armed, last = [], True, None
    for t, f in fire.items():
        if armed and f:
            calls.append(t); armed = False; last = t
        elif not armed and last is not None and (t - last).days >= min_expansion * 30:
            if not f: armed = True
    return calls


def score(calls):
    lags, used = {}, set()
    for p in PK:
        c = [t for t in calls if 0 <= (p - t).days <= 400]
        if c:
            t = c[-1]; lags[p.strftime('%Y-%m')] = (t - p).days; used.add(t)
    c0, c1 = pd.Timestamp(CRUNCH[0] + '-01'), me(CRUNCH[1])
    false = [t for t in calls if t not in used and not inside(t)]
    crunch = [t for t in false if c0 <= t <= c1]
    v = list(lags.values())
    return dict(n_call=len(calls), n_cov=len(v),
                n_in=sum(1 for z in v if WIN_EARLY <= z <= WIN_LATE),
                n_tight=sum(1 for z in v if -31 <= z <= -1),
                n_early=sum(1 for z in v if z < WIN_EARLY),
                n_late=sum(1 for z in v if z >= 0),
                n_false=len(false), n_crunch=len(crunch),
                lags=json.dumps(lags), false=';'.join(str(t.date()) for t in false[:6]))


def main():
    o = build_objects()
    print('objects built:', len(o))
    for k in sorted(o):
        s = o[k].dropna()
        print('  %-20s %s .. %s  n=%d' % (k, s.index.min().date(), s.index.max().date(), len(s)))
    QS = [0.85, 0.90, 0.95, 0.975]
    WINS = [3, 6, 9]
    rows = []
    for pn in PROPOSERS:
        for qp in QS:
            pf = over_line(o[pn], qp)
            if pf.sum() == 0: continue
            for cn in CONFIRMERS:
                for qc in QS:
                    cf = over_line(o[cn], qc)
                    if cf.sum() == 0: continue
                    for w in WINS:
                        sc = score(emit(pf, cf, w))
                        if sc['n_cov'] == 0: continue
                        rows.append(dict(proposer=pn, qp=qp, confirmer=cn, qc=qc, win=w, **sc))
    d = pd.DataFrame(rows)
    d.to_csv(os.path.join(OUT, 'conjunction_grid.csv'), index=False)
    print('\nconfigurations with at least one peak:', len(d))
    zf = d[(d.n_false == 0) & (d.n_crunch == 0)]
    print('zero false alarms AND silent on 1966:', len(zf), '| max peaks covered:', (zf.n_cov.max() if len(zf) else 0))
    if len(zf):
        b = zf.sort_values(['n_cov','n_in','n_tight'], ascending=False).head(12)
        print('\n%-18s %-6s %-16s %-6s %-4s %-5s %-4s %-6s %-5s' %
              ('proposer','qp','confirmer','qc','win','calls','cov','IN','tight'))
        for _, r in b.iterrows():
            print('%-18s %-6.3f %-16s %-6.3f %-4d %-5d %-4d %-6d %-5d'
                  % (r.proposer, r.qp, r.confirmer, r.qc, r.win, r.n_call, r.n_cov, r.n_in, r.n_tight))
        t = b.iloc[0]
        print('\nBEST zero-false: %s(%.3f) + %s(%.3f) win=%d -> %d/12 peaks, %d in window'
              % (t.proposer, t.qp, t.confirmer, t.qc, t.win, t.n_cov, t.n_in))
        print('lags:', t.lags)
    print('\n=== frontier: max peaks at each false-alarm count (1966-silent only) ===')
    q = d[d.n_crunch == 0]
    print(q.groupby('n_false').n_cov.max().head(10).to_string())


if __name__ == '__main__':
    main()
