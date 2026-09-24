#!/usr/bin/env python3
"""The menu form: ANY labour proposer over its line, confirmed by ANY money, activity or
diffusion object over its line, within a window. This is the architecture the live rule
actually has -- seven objects, not one pair -- and it is why a single pair cannot reach
twelve peaks: a pair can only cover peaks where BOTH its legs already existed.

No subset is chosen by result. Three families are run:
  ALL         every proposer, every confirmer
  LABOUR_ONLY every proposer, confirmed only by another labour object (the control:
              this is roughly what the live rule is, with no financial leg)
  +CHANNEL    every proposer, confirmed only by one named channel, so the contribution
              of the money, activity and diffusion channels can be read separately

The quantiles are swept jointly, one value for proposers and one for confirmers, so that
no individual object gets its own fitted line.
"""
import json, os, sys, numpy as np, pandas as pd, warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import conjunction as C

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, 'out')

CHANNELS = {
    'money':     ['baa_aaa','baa_tbill','prime_tbill','paper_bill','term_inv'],
    'activity':  ['cfnai_fall','cfnaidiff_fall','indpro_fall','ipmat_fall'],
    'diffusion': ['philly_gac','philly_no','philly_emp'],
}
LABOUR_CONF = ['payems_fall','hours_fall','contclaims_vs_low','temphelp_fall']


def union_fire(o, names, q):
    f = None
    for n in names:
        if n not in o: continue
        x = C.over_line(o[n], q)
        f = x if f is None else (f | x)
    return f


def run(o, props, confs, qp, qc, win):
    pf, cf = union_fire(o, props, qp), union_fire(o, confs, qc)
    if pf is None or cf is None: return None
    return C.score(C.emit(pf, cf, win))


def main():
    o = C.build_objects()
    QS = [0.85, 0.90, 0.95, 0.975]
    WINS = [3, 6, 9, 12]
    fams = {'ALL': C.CONFIRMERS, 'LABOUR_ONLY(control)': LABOUR_CONF}
    for k, v in CHANNELS.items(): fams['only_' + k] = v
    fams['money+diffusion'] = CHANNELS['money'] + CHANNELS['diffusion']
    fams['money+activity'] = CHANNELS['money'] + CHANNELS['activity']
    fams['activity+diffusion'] = CHANNELS['activity'] + CHANNELS['diffusion']
    rows = []
    for fam, confs in fams.items():
        for qp in QS:
            for qc in QS:
                for w in WINS:
                    sc = run(o, C.PROPOSERS, confs, qp, qc, w)
                    if sc is None: continue
                    rows.append(dict(family=fam, qp=qp, qc=qc, win=w, **sc))
    d = pd.DataFrame(rows)
    d.to_csv(os.path.join(OUT, 'menu_grid.csv'), index=False)
    print('configurations:', len(d))
    print('\n%-22s %-6s %-7s %-6s %-6s' % ('family', 'best', 'at false', 'IN', 'tight'))
    for fam in fams:
        s = d[(d.family == fam) & (d.n_crunch == 0)]
        if not len(s): continue
        z = s[s.n_false == 0]
        b = (z if len(z) else s).sort_values(['n_cov','n_in','n_tight'], ascending=False).iloc[0]
        print('%-22s %-6d %-7d %-6d %-6d   qp=%.3f qc=%.3f win=%d'
              % (fam, b.n_cov, b.n_false, b.n_in, b.n_tight, b.qp, b.qc, b.win))
    z = d[(d.n_false == 0) & (d.n_crunch == 0)]
    print('\nzero false AND 1966-silent:', len(z), '| max peaks:', (z.n_cov.max() if len(z) else 0))
    if len(z):
        b = z.sort_values(['n_cov','n_in','n_tight'], ascending=False).head(8)
        print(b[['family','qp','qc','win','n_call','n_cov','n_in','n_tight','n_late']].to_string(index=False))
        t = b.iloc[0]
        print('\nBEST:', t.family, 'qp=%.3f qc=%.3f win=%d' % (t.qp, t.qc, t.win))
        print('lags:', t.lags)
    print('\n=== frontier (1966-silent) ===')
    print(d[d.n_crunch == 0].groupby('n_false').n_cov.max().head(8).to_string())


if __name__ == '__main__':
    main()
