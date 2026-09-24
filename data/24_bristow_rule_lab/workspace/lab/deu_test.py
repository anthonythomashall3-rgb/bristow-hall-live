"""Germany, held out: a twelfth official chronology, and the panel chronology §12 item 7 wanted.

The German Council of Economic Experts (Sachverständigenrat zur Begutachtung der
gesamtwirtschaftlichen Entwicklung) is a statutory body created by the Act of 14 August
1963, its members appointed by the Federal President on the Government's proposal.  It has
dated German business cycles since 1950 and publishes month-dated peaks and troughs.

It states its own concept and its own evidence, and both are what this paper requires:

  concept  "klassische Konjunkturzyklen" - a classical, level cycle.
  method   "Zur Identifikation der zyklischen Hoch- und Tiefpunkte werden MEHRERE
           makrooekonomische Indikatoren auf Monats- und Quartalsbasis herangezogen",
           and the dating "folgt dabei keinem festen Algorithmus".
  monthly  "Hierunter fallen die Produktion im Produzierenden Gewerbe ohne Bau, die
           evidence  realen Auftragseingaenge in der Industrie, die realen Umsaetze im
           Einzelhandel sowie die Arbeitslosenquote."
  and the sentence this paper has been arguing for eighty pages, from a committee:
           "Gegenueber dem vom Sachverstaendigenrat verwendeten Verfahren stellt die
           BESCHRAENKUNG AUF LEDIGLICH EINE REFERENZZEITREIHE aber EINEN NACHTEIL dar."
  (Breuer, Kirsch, Elstner and Wieland, Arbeitspapier 13/2018, pp. 10, 12, 41.)

THIS IS A COMMITTEE THAT DATES A PANEL DIRECTLY, which is what §12 item 7 has been waiting
for: the NBER's structure rather than Japan's, so a filter that decides which channels of a
panel may vote has something to act on.

Nothing about Germany entered any choice made in building the rule; the configuration is
the shipped one, unchanged.
"""
import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import numpy as np, pandas as pd, warnings; warnings.filterwarnings('ignore')
bench.SKIP=set(); bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
# Business Cycle Reference Dates, sheet "Business Cycles" of BusinessCycleData.xlsx,
# sachverstaendigenrat-wirtschaft.de.  Dated in months.
DE=[('1966-03','1967-05'),('1974-01','1975-07'),('1980-01','1982-11'),('1992-02','1993-07'),
    ('2001-02','2003-06'),('2008-01','2009-04'),('2020-02','2020-04')]
def L(f): return load('/home/claude/lab/kei/'+f)
CH=[('industrial production',L('DEU_PRVM_BTE.csv')),      # the Council's own first channel
    ('retail volume',L('DEU_TOVM_G47.csv')),              # the Council's own third channel
    ('exports',L('DEU_EX__T.csv')),
    ('imports',L('DEU_IM__T.csv')),
    ('construction production',L('DEU_PRVM_F.csv')),
    ('car registrations',L('DEU_TOCAPA_G45.csv'))]
# The Council's other two named channels, found 2 September 2026 in long keyless series at the
# Bundesbank (BBDE1 / BBDL1 through DBnomics, lab/nat/deu): real orders received by industry,
# seasonally adjusted, monthly from January 1952; the registered unemployment rate, seasonally
# adjusted - West Germany from December 1949, chained onto the all-German rate at December 1991.
NAT='/home/claude/lab/nat/deu'
COUNCIL_EXTRA=[('real orders received',load(f'{NAT}/DEU_orders_real_sa.csv')),
               ('unemployment rate',100.0-load(f'{NAT}/DEU_unemployment_rate_sa_spliced.csv'))]   # a rate: 100 - u
for nm,s in CH+COUNCIL_EXTRA: print(f'   channel {nm:26s} {s.index.min().date()}..{s.index.max().date()}  n={len(s)}')
def run(mode,chs):
    hp=ht=0; ep=[]; et=[]; rows=[]; n=0
    for pk_off,tr_off in DE:
        pkm=ts(pk_off); trm=ts(tr_off)
        w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
        use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=trm]
        if len(use)<2: rows.append((pk_off,None,tr_off,None)); continue
        n+=1
        b=date_any('Germany',use,w0,w1,**K)
        a,e1=hit(b['peak'],pk_off,'M'); c,e2=hit(b['trough'],tr_off,'M')
        hp+=a; ht+=c
        if e1 is not None: ep.append(abs(e1))
        if e2 is not None: et.append(abs(e2))
        rows.append((pk_off,e1,tr_off,e2))
    return hp,ht,n,(np.mean(ep) if ep else float('nan')),(np.mean(et) if et else float('nan')),rows
COUNCIL=[c for c in CH if c[0] in ('industrial production','retail volume')]
print()
print(f'{"route":52s} {"peaks":>8s} {"troughs":>8s}  {"MAD p":>6s} {"MAD t":>6s}')
for tag,chs in [("the two channels the Council itself names",COUNCIL),
                ("the full six-channel German panel",CH),
                ("the four channels the Council itself names",COUNCIL+COUNCIL_EXTRA),
                ("the six-channel panel with the Council's other two",CH+COUNCIL_EXTRA)]:
    r=run(tag,chs)
    print(f'{tag:52s} {r[0]:3d}/{r[2]:<4d} {r[1]:4d}/{r[2]:<4d}  {r[3]:6.2f} {r[4]:6.2f}')
print()
r=run('full',CH)
print('per episode, the full panel:')
for x in r[5]: print(f'   peak {x[0]} err {str(x[1]):>5s}    trough {x[2]} err {str(x[3]):>5s}')
for tag,chs in (("the four channels the Council itself names",COUNCIL+COUNCIL_EXTRA),("the six-channel panel with the Council's other two",CH+COUNCIL_EXTRA)):
    r=run(tag,chs); print(f'\nper episode, {tag}:')
    for x in r[5]: print(f'   peak {x[0]} err {str(x[1]):>5s}    trough {x[2]} err {str(x[3]):>5s}')
