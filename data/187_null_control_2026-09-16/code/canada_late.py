#!/usr/bin/env python3
"""The Canadian transfer test — of the MECHANISM the American selection converged on, not of the series.

WHAT IS BEING TRANSFERRED. Four filters over 5,761 American channels converged on one family: central
bank and commercial bank balance sheets. Federal Reserve total assets, primary and secondary credit,
total borrowings, commercial bank cash assets — ratios of 30 to 680 against forty fake chronologies,
where the leading index, the coincident index, M1, permits and business applications sit between 0.04
and 3.6.

Those American series do not exist in Canada, so transferring them literally is impossible and would
not be the interesting test anyway. What transfers is the claim: *bank and central-bank balance sheets
move ahead of recessions, and do so in a way a wrongly dated chronology does not reproduce.* Canada has
the counterparts — Bank of Canada holdings of treasury bills and other accounts from 1955, chartered
bank holdings from 1953, consumer credit by lender from 1956 — an independent dating committee, and no
part in how the American family was chosen.

SAME GRID, SAME BAR, SAME CONTROL, NOTHING REFITTED. Horizons, directions, quantiles, windows, holds,
the [-92, -1] window, zero quiet firings, and the same false-discovery test against fake Canadian
chronologies drawn clear of real Canadian recessions.

The 1980 recession that the Business Cycle Council REMOVED from Cross and Bergevin's chronology is
scored as an expansion here, so a firing in it counts against a channel.
"""
import os, sys, json, time, random, collections, warnings
import numpy as np, pandas as pd, multiprocessing as mp
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
warnings.filterwarnings('ignore')
import late_screen as L

CA = os.environ.get('CA_DATA', '/mnt/user-data/outputs/ca')
OUT = os.environ.get('CA_OUT2', '/mnt/user-data/outputs/ca_late')
os.makedirs(OUT, exist_ok=True)

BCC = [('1929-04', '1933-02'), ('1937-11', '1938-06'), ('1947-08', '1948-03'), ('1951-04', '1951-12'),
       ('1953-07', '1954-07'), ('1957-03', '1958-01'), ('1960-03', '1961-03'), ('1974-10', '1975-03'),
       ('1981-06', '1982-10'), ('1990-03', '1992-05'), ('2008-10', '2009-05'), ('2020-02', '2020-04')]
def me(y): return pd.Timestamp(y + '-01') + pd.offsets.MonthEnd(0)
CA_PK = [me(p) for p, _ in BCC]; CA_TR = [me(t) for _, t in BCC]
CA_CONFS = {
 'claims_rising':    ('CA14100005_INITIAL_CLAIMS_RECEIVED', lambda s, k: s.pct_change(k) * 100),
 'starts_falling':   ('CA34100143_HOUSING_STARTS_TOTAL_UNITS', lambda s, k: -s.pct_change(k) * 100),
 'permits_falling':  ('CA34100008_SEASONALLY_ADJUSTED_TOTAL_RESIDENTIAL_AND_NON_', lambda s, k: -s.pct_change(k) * 100),
 'power_falling':    ('CA25100033_TOTAL_SALES', lambda s, k: -s.pct_change(k) * 100),
 'ip_falling':       ('CANPROINDMISMEI', lambda s, k: -s.pct_change(k) * 100),
 'unrate_rising':    ('LRHUTTTTCAM156S', lambda s, k: s.diff(k)),
 'covered_falling':  ('CA14100006_PERSONS_COVERED_BY_EMPLOYMENT_INSURANCE', lambda s, k: -s.pct_change(k) * 100),
 'completions_falling': ('CA34100143_HOUSING_COMPLETIONS_TOTAL_UNITS', lambda s, k: -s.pct_change(k) * 100),
}

def configure(pk, tr):
    L.FOLDERS = [CA]; L.FP2 = os.path.join(CA, '_none'); L.VDIR = L.FP2
    L.CONFS = CA_CONFS
    L.IDX = pd.date_range('1919-01-31', '2026-09-30', freq='D')
    L.NIDX = len(L.IDX); L.D0 = L.IDX[0]
    L.PK, L.TR = pk, tr
    L.PK_POS = [(int((p - L.D0).days), p.strftime('%Y-%m')) for p in pk]
    ins = np.zeros(L.NIDX, bool)
    for p, r in zip(pk, tr):
        i = max(0, int((p - L.D0).days)); j = min(L.NIDX - 1, int((r - L.D0).days))
        if j >= i: ins[i:j + 1] = True
    L.INSIDE = ins
    L.CR_LO, L.CR_HI = -1, -1          # no Canadian analogue of the American credit crunch is scored
    L._RD.clear(); L._FP.clear()

def _init(pktr):
    configure(*pktr); L.init()

def free_months():
    months = pd.date_range(pd.Timestamp('1946-06-30'), pd.Timestamp('2026-06-30'), freq='ME')
    bad = np.zeros(len(months), bool)
    for p, r in zip(CA_PK, CA_TR):
        bad |= ((months >= p - pd.Timedelta(days=365)) & (months <= r + pd.Timedelta(days=365)))
    return list(months[~bad])
def draw(rng, npk, free, dur):
    for _ in range(8000):
        pk = sorted(rng.sample(free, npk))
        if min((pk[i + 1] - pk[i]).days for i in range(npk - 1)) >= 365:
            return pk, [min(p + pd.Timedelta(days=rng.choice(dur)), L.IDX[-1]) for p in pk]
    raise RuntimeError('no admissible fake chronology')

def run(pk, tr, cand, tag):
    t0 = time.time(); rows = []
    with mp.Pool(max(1, os.cpu_count() or 2), initializer=_init, initargs=((pk, tr),)) as pool:
        for res in pool.imap_unordered(L.one, cand, chunksize=2): rows += res
    c = collections.Counter(); per = collections.Counter()
    for r in rows:
        c[r['proposer']] += 1
        for p in json.loads(r['tight']): per[p] += 1
    print('%-9s %6d configs, %4d channels, %.1f min  %s'
          % (tag, len(rows), len(c), (time.time() - t0) / 60, dict(sorted(per.items()))), flush=True)
    return rows, c

if __name__ == '__main__':
    import re
    ndraws = int(os.environ.get('NDRAWS', '20'))
    configure(CA_PK, CA_TR)
    pat = re.compile(r'BANK|CHARTERED|CREDIT|LOAN|DEPOSIT|CURRENCY|RESERVE|MONEY|MORTGAGE|LIQUID|ADVANCE|DISCOUNT|TREASURY|BOND|ASSET', re.I)
    cand = sorted({f[:-4] for f in os.listdir(CA)
                   if f.endswith('.csv') and not f.startswith('MANIFEST') and pat.search(f)}
                  - {v[0] for v in CA_CONFS.values()})
    print('Canadian bank/credit/money channels: %d, fake chronologies: %d' % (len(cand), ndraws), flush=True)
    rows, true_c = run(CA_PK, CA_TR, cand, 'TRUE')
    pd.DataFrame(rows).to_csv(os.path.join(OUT, 'canada_late_true.csv'), index=False)
    rng = random.Random(90210); free = free_months()
    dur = [int((r - p).days) for p, r in zip(CA_PK, CA_TR)]
    fake = collections.defaultdict(list)
    for d in range(ndraws):
        pk, tr = draw(rng, len(CA_PK), free, dur)
        _, c = run(pk, tr, cand, 'null %d' % (d + 1))
        for sid in cand: fake[sid].append(c.get(sid, 0))
    out = []
    for sid in cand:
        f = np.array(fake[sid], float); t = float(true_c.get(sid, 0))
        if t == 0 and f.max() == 0: continue
        out.append(dict(channel=sid, true_cfg=int(t), fake_mean=f.mean(), fake_max=int(f.max()),
                        ratio=(t / f.mean()) if f.mean() > 0 else (float('inf') if t > 0 else 0.0),
                        p_exceed=float((f >= t).mean())))
    D = pd.DataFrame(out).sort_values(['p_exceed', 'ratio'], ascending=[True, False])
    D.to_csv(os.path.join(OUT, 'canada_late_power.csv'), index=False)
    print('\n%-56s %6s %9s %8s %9s' % ('channel', 'true', 'fake mean', 'ratio', 'P(fake>=true)'))
    for _, r in D.head(25).iterrows():
        print('%-56s %6d %9.1f %8.1f %9.3f' % (r.channel[:56], r.true_cfg, r.fake_mean, r.ratio, r.p_exceed))
