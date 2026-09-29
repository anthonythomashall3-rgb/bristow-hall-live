#!/usr/bin/env python3
"""Validation of hwi_asprinted_long.csv: first prints vs Barnichon (2010) reconstruction, cross-source overlaps,
revisions across vintages. Writes work/validation_summary.txt and work/first_prints.csv."""
import os
import numpy as np, pandas as pd

W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BARN = '/home/user/bristow-hall-live/data/24_bristow_rule_lab/workspace/lab/vac/barnichon_hwi.csv'
out = []


def p(*a):
    s = ' '.join(str(x) for x in a)
    print(s); out.append(s)


L = pd.read_csv(os.path.join(W, 'hwi_asprinted_long.csv'), dtype={'series': str})
L = L[(L.series == '46') & (~L.table.isin(['S-page', 'news_other']))]
bn = pd.read_csv(BARN).dropna(); bn['month'] = bn.d.str.slice(0, 7); bn = bn.set_index('month').hwi


def src(x):
    return ('BCD' if 'Business C' in x else 'SCB' if 'Survey' in x else 'NEEI' if 'New England' in x else 'NEWS')


L['src'] = L.publication.map(src)
# first print = earliest publication_date printing the month (non-historical tables)
F = L[L.table != 'historical'].sort_values(['month', 'publication_date', 'ocr_doubtful'])
first = F.drop_duplicates('month').copy()
first['barnichon'] = first.month.map(bn)
first.to_csv(os.path.join(W, 'work', 'first_prints.csv'), index=False)
p('FIRST PRINTS: months', len(first), 'range', first.month.min(), first.month.max())
p(first.groupby(['src', 'base']).agg(n=('value', 'size'), first=('month', 'min'), last=('month', 'max')).to_string())
p('\nFirst print vs Barnichon, by base (ratio level, corr of log changes):')
for b, g in first.groupby('base'):
    g = g.dropna(subset=['barnichon']).sort_values('month')
    if len(g) < 6:
        continue
    r = g.value / g.barnichon
    lv = np.log(g.value.values); lb = np.log(g.barnichon.values)
    dc = np.corrcoef(np.diff(lv), np.diff(lb))[0, 1] if len(g) > 3 else np.nan
    p(f'  {b:12s} n={len(g):4d} {g.month.min()}..{g.month.max()} ratio median={r.median():.3f} '
      f'IQR=[{r.quantile(.25):.3f},{r.quantile(.75):.3f}] corr(dlog)={dc:.3f} corr(level)={np.corrcoef(lv, lb)[0,1]:.3f}')
    bad = g[(r / r.median() - 1).abs() > 0.08]
    p(f'     months with ratio >8% off median: {len(bad)}', ', '.join(f"{m}:{v:g}" for m, v in zip(bad.month.head(15), bad.value.head(15))))
# cross-source overlap: SCB C-page vs BCD (1989-1990)
p('\nOverlap SCB C-pages vs BCD (same month, closest publication dates):')
a = L[(L.src == 'SCB') & (L.table == 'C-page')].groupby('month').value.first()
b = L[(L.src == 'BCD')].sort_values('publication_date').groupby('month').value.last()
j = pd.concat([a.rename('scb'), b.rename('bcd_last')], axis=1).dropna()
p(f'  n={len(j)}, identical={int((j.scb == j.bcd_last).sum())}, max abs diff={(j.scb - j.bcd_last).abs().max() if len(j) else None}')
# NEEI vs news
p('\nOverlap NEEI vs news reports (news value vs NEEI first print of that month):')
ne = L[L.src == 'NEEI'].sort_values('publication_date').groupby('month').value.first()
nw = L[L.src == 'NEWS'].groupby('month').value.first()
j = pd.concat([ne.rename('neei_first'), nw.rename('news')], axis=1).dropna()
p(f'  n={len(j)}, identical={int((j.neei_first == j.news).sum())}; diffs:', j[j.neei_first != j.news].to_dict('index'))
# revisions within BCD / SCB / NEEI
p('\nRevisions (first vs last print within the same base):')
for s_, g in L[L.table != 'historical'].groupby(['src', 'base']):
    g = g.sort_values('publication_date')
    fl = g.groupby('month').value.agg(['first', 'last', 'size'])
    fl = fl[fl['size'] > 1]
    if len(fl) == 0:
        continue
    d = fl['last'] - fl['first']
    p(f'  {s_}: months printed >1 time={len(fl)}, share revised={np.mean(d != 0):.2f}, mean |rev|={d.abs().mean():.2f}')
# repeated values
p('\nOCR doubtful share by source:', L.groupby('src').ocr_doubtful.mean().round(3).to_dict())
open(os.path.join(W, 'work', 'validation_summary.txt'), 'w').write('\n'.join(out) + '\n')
