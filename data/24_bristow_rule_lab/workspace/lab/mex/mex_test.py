"""Mexico, held out: a thirteenth official chronology — and §12 item 10 is withdrawn.

Version 17 said "Mexico stays out, for a documented reason": INEGI no longer uses its
classical composite system to date cycles, and the Sistema de Indicadores Cíclicos it does
publish is a growth-cycle system.  Both statements are still true and both are beside the
point, because the dating is not done by INEGI.

The **Comité de Fechado de Ciclos de la Economía de México** was established on 3 February
2021 under a convenio between INEGI and the Instituto Mexicano de Ejecutivos de Finanzas
signed 16 December 2020 — the direct successor of the 2020 INEGI working group §12 item 10
already cited.  It publishes a monthly chronology of six recessions, 1980–2020.

Its own words, from its technical note of 2 August 2022:

  concept  "ha adoptado el ENFOQUE CLÁSICO de los ciclos económicos, el fechado
           correspondiente se hace a partir de las series de tendencia-ciclo-irregular".
  method   "el CFCEM hace sus análisis principalmente, aunque no exclusivamente, A PARTIR
           DE SERIES DE TIEMPO MENSUALES ... el IGAE total y desagregado en cada uno de sus
           quince subsectores ... el Indicador de Volumen Físico de la Actividad Industrial,
           Número de Asegurados Permanentes del IMSS, Índice de Ventas Netas al Por Menor
           ... la Tasa de Desocupación Urbana y las Importaciones Totales."
  criteria Shiskin's three D's — "profundidad ... duración ... difusión" — with the note
           that "recesión técnica ... es simplista y limitada".

That is a classical, level concept dated from a PANEL of monthly indicators read directly:
the NBER's structure, and the second such committee this pass has found.

The committee's turning-point convention is stated on its own page: "El primero [pico] se
refiere al mes en el que la actividad económica alcanza un máximo local, indicando el
término de una fase de expansión y el inicio de una recesión" — so the pico is the last
month of the expansion and the recession begins the month after.  The chronology's five
published picos are used as the peaks.  The first cycle has no published pico, because the
table begins with its recession, so that contraction is dated at the trough only.

THE PANEL IS COMPLETED WITH THE SERIES THE COMMITTEE NAMES FIRST.  The note above lists
the IGAE total ahead of everything else, and the OECD's Mexican panel does not carry it.
INEGI publishes the IGAE as open data - `igae_mensual_csv.zip` under
`www.inegi.org.mx/contenidos/programas/igae/2018/datosabiertos/`, base 2018=100, monthly
from January 1993 - but only as ORIGINAL series; the seasonally adjusted form is behind
INEGI's registered-token API.  It is therefore adjusted here with the routine the speed
section uses: month-of-year factors estimated on a moving seven-year window as medians,
refitted each December from the data available then.  That is stated because it is this
program's own adjustment on a held-out chronology, and because it does real work - the
month-of-year spread falls from 6.1 log points to 0.8, and the raw series does not recover
the peak.  The result does not depend on the window: 5, 7, 10 and 15 years all give the
same answer, and `igae_build.py` reproduces the series.
"""
import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import numpy as np, pandas as pd, warnings; warnings.filterwarnings('ignore')
bench.SKIP=set(); bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
# Puntos de giro de los ciclos de la economía mexicana, 1980-2020, CFCEM.
# (peak = fin de la expansión anterior; trough = fin (valle) de la recesión)
MX=[(None,'1983-06'),('1985-09','1986-12'),('1994-11','1995-05'),('2000-09','2002-01'),
    ('2008-06','2009-05'),('2019-05','2020-05')]
def L(f): return load('/home/claude/lab/kei/'+f)
CH=[('industrial production',L('MEX_PRVM_BTE.csv')),
    ('construction production',L('MEX_PRVM_F.csv')),
    ('exports',L('MEX_EX__T.csv')),
    ('imports',L('MEX_IM__T.csv')),
    ('retail volume',L('MEX_TOVM_G47.csv')),
    ('unemployment',L('MEX_UNEMP__T.csv')),
    ('IGAE',load('/home/claude/lab/mex/MEX_igae_sa.csv')),
    ('vehicle production',load('/home/claude/lab/mex/MEX_vehicles_sa.csv'))]   # adopted 2 Sep 2026 (Anthony); INEGI via DBnomics, 1983-01 on
for nm,s in CH: print(f'   channel {nm:26s} {s.index.min().date()}..{s.index.max().date()}  n={len(s)}')
def run(chs):
    hp=ht=0; np_=nt=0; ep=[]; et=[]; rows=[]
    for pk_off,tr_off in MX:
        trm=ts(tr_off)
        pkm=ts(pk_off) if pk_off else trm-pd.DateOffset(months=18)
        w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
        use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=trm]
        if len(use)<2: rows.append((pk_off,'no data',tr_off,'no data')); continue
        b=date_any('Mexico',use,w0,w1,**K)
        e1=None
        if pk_off:
            np_+=1; a,e1=hit(b['peak'],pk_off,'M'); hp+=a
            if e1 is not None: ep.append(abs(e1))
        nt+=1; c,e2=hit(b['trough'],tr_off,'M'); ht+=c
        if e2 is not None: et.append(abs(e2))
        rows.append((pk_off,e1,tr_off,e2))
    return hp,np_,ht,nt,(np.mean(ep) if ep else float('nan')),(np.mean(et) if et else float('nan')),rows
r=run(CH)
print()
print(f'the eight-channel Mexican panel:  peaks {r[0]}/{r[1]}   troughs {r[2]}/{r[3]}   '
      f'MAD {r[4]:.2f} / {r[5]:.2f}')
print()
print('per episode:')
for x in r[6]: print(f'   peak {str(x[0]):>8s} err {str(x[1]):>7s}    trough {x[2]} err {str(x[3]):>7s}')
