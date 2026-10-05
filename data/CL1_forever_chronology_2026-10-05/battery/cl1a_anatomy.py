"""CL1-A diagnosis (exploratory, after scoring; G1): each family's highest record ratio inside every W12 onset window
(to +31 days) against its quiet record, (a) on the pre-registered quiet set and (b) on the quiet set with three structural
artifacts removed: recession aftermath (quiet starts trough + 730 days, since 12-month look-backs still hold the
recession), the first real-time seasonal-adjustment years (lines from 1953), and major strikes (+60 days; dates in
STRIKES, from the BLS major work stoppages record; to be sourced line by line in the next round). Prints markdown tables."""
import os, sys
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, 'harness'))
import score, anatomy
FAM = ['F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7', 'F8']
STRIKES = [('1952-04-29', '1952-07-24'), ('1956-07-01', '1956-07-27'), ('1959-07-15', '1959-11-07'), ('1964-09-25', '1964-11-07'),
           ('1967-09-07', '1967-10-25'), ('1970-09-15', '1970-11-20'), ('1977-12-06', '1978-03-25'), ('1997-08-04', '1997-08-19'),
           ('2019-09-16', '2019-10-25'), ('2023-09-15', '2023-10-30')]


def table(P, q, lab):
    rows = []; R = pd.DataFrame(index=P.index)
    for f in FAM:
        x = P[f]; xq = x[q].dropna(); med, rec = xq.median(), xq.max(); R[f] = (x - med) / (rec - med)
        rows.append([f] + ['%.2f' % R[f][lab == 'ONSET%d' % i].max() for i in range(13)] + [str(xq.idxmax().date())])
    srt = np.sort(R[FAM].fillna(-9).values, axis=1)[:, ::-1]
    for k in [2, 3]:
        s = pd.Series(srt[:, k - 1], index=P.index).where(lambda v: v > -9); rec = s[q].max()
        rows.append(['2nd largest' if k == 2 else '3rd largest'] + ['%.2f' % (s[lab == 'ONSET%d' % i].max() / rec) for i in range(13)]
                    + [str(s[q].idxmax().date())])
    hdr = '| family | ' + ' | '.join(b[0] for b in score.BOARD) + ' | quiet record set on |'
    out = [hdr, '|' + '---|' * (15)]
    out += ['| ' + ' | '.join(str(c).replace('nan', '—') for c in r) + ' |' for r in rows]
    return '\n'.join(out)


P = pd.read_parquet(os.path.join(HERE, 'private', 'panel', 'families_daily.parquet'))
days = P.index; lab = anatomy.populations(days); Pe, Te = score.ends()
qa = np.asarray(days >= pd.Timestamp('1948-01-01'))
for p, t in zip(Pe, Te): qa &= ~np.asarray((days >= p - pd.Timedelta(days=365)) & (days <= t + pd.Timedelta(days=365)))
qb = np.asarray(days >= pd.Timestamp('1953-01-01'))
for p, t in zip(Pe, Te): qb &= ~np.asarray((days >= p - pd.Timedelta(days=365)) & (days <= t + pd.Timedelta(days=730)))
for a, b in STRIKES: qb &= ~np.asarray((days >= pd.Timestamp(a)) & (days <= pd.Timestamp(b) + pd.Timedelta(days=60)))
print('### (a) Pre-registered quiet set (ratios: 1.00 = the family\'s quiet record)\n'); print(table(P, qa, lab))
print('\n### (b) Quiet set without aftermath (to trough + 730 days), without 1948-52, without major strikes + 60 days\n'); print(table(P, qb, lab))
