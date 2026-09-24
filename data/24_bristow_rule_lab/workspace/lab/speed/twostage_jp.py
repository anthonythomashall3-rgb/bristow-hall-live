"""The two-stage trough in Japan on the Cabinet Office's Economy Watchers Survey.

The survey (景気ウォッチャー調査) asks some two thousand people in customer-facing jobs each
month how business conditions compare with three months earlier; the diffusion index for
current conditions is published around the 8th of the following month (the September 2025
result was released on 8 October 2025), monthly from January 2000, by sector and by region
(lab/acq/jpsurv/, fetched 2 September 2026 from www5.cao.go.jp/keizai3/watcher.html;
unadjusted, adjusted here in real time).  Stage 1 is the level route's D on the OECD Japanese
panel (production, retail volume, employment), each reading in hand two months after its
month.  Stage 2 (a) the national current-conditions DI rising `a` points from its minimum for
`r` months; (b) the breadth of the eleven regions (Hokkaido, Tohoku, Kanto, Koshinetsu, Tokai,
Hokuriku, Kinki, Chugoku, Shikoku, Kyushu, Okinawa): share whose DI rose over `k` months at or
above q per cent for `r` months.  Published in the month after the call's data month, so
'within the month' = data month no later than the trough month.  Scored against the ESRI's
four troughs since 2000 (January 2002, March 2009, November 2012, May 2020) and ECRI's.
"""
import sys, itertools, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab'); sys.path.insert(0,'/home/claude/lab/speed')
import numpy as np, pandas as pd
import bristow_rule_v3 as B, bench
from bench import kei, pro
import ecbcs_speed as E, twostage_ec as T2
ACQ='/home/claude/lab/acq/jpsurv'
ESRI_T=[E.ts(x) for x in ['2002-01','2009-03','2012-11','2020-05']]
ECRI_T=[E.ts(d) for k,d in E.ECRI['Japan'] if k=='T' and d>='2000-06']
REGIONS=['北海道','東北','関東','甲信越','東海','北陸','近畿','中国','四国','九州','沖縄']
def panel():
    return [(nm,pro(p,kind)) for nm,p,kind in kei('JPN') if nm in ('industrial production','retail volume','employment')]
def d_available():
    D=B.composite_deviation(panel(),12,3,1).dropna(); D.index=D.index+pd.DateOffset(months=2); return D
def shift_pub(calls): return [(p+pd.DateOffset(months=1),d) for p,d in calls]   # published the month after the data month
if __name__=='__main__':
    D=d_available()
    nat=pd.read_csv(f'{ACQ}/JPN_ews_current_by_sector_nsa.csv',index_col=0,parse_dates=True)
    reg=pd.read_csv(f'{ACQ}/JPN_ews_current_by_region_nsa.csv',index_col=0,parse_dates=True)
    s=E.sa_rt(nat['合計'].dropna()).dropna()
    print('panel',[nm for nm,x in panel()],'| survey',s.index.min().strftime('%Y-%m'),'->',s.index.max().strftime('%Y-%m'))
    for label,T in (('ESRI',ESRI_T),('ECRI',ECRI_T)):
        print(f'\n=== troughs against {label} ({len(T)}): {[t.strftime("%Y-%m") for t in T]}')
        tt=[(p,d) for p,d in B.real_time_trough_calls(panel(),publication_lag=2,fall_months=4,drop=0.5,min_channels=1) if d>=pd.Timestamp('2000-06-01')]
        T2.line("the tool's own clause on D, published +2 months",tt,T)
        rows=[]
        for a,r in itertools.product((2.,3.,5.,8.),(1,2,3)):
            calls=shift_pub(T2.twostage(D,s,a,r)); rows.append((T2.line(f'  national DI a={a} r={r}',calls,T,show=False),a,r,calls))
        rows.sort(key=lambda x:(x[0][0],-x[0][1],x[0][5],x[0][4]),reverse=True)
        for res,a,r,calls in rows[:3]: T2.line(f'  national DI a={a:.0f} r={r}',calls,T)
        X=pd.DataFrame({c:E.sa_rt(reg[c].dropna()) for c in REGIONS if c in reg}).dropna(how='all')
        rows=[]
        for k,q,r in itertools.product((1,2,3),(60.,70.,80.,90.,100.),(1,2)):
            ch=X.diff(k); Bd=(ch>0).sum(axis=1)/ch.notna().sum(axis=1)*100.0
            C=((X-X.rolling(120,min_periods=36).mean())/X.rolling(120,min_periods=36).std()).mean(axis=1)
            out=[]; state='quiet'; open_at=None; last=None
            for t in Bd.index:
                if t not in D.index or np.isnan(Bd[t]): continue
                dd=float(D[t])
                if state=='quiet':
                    if dd>=2.0 and (last is None or T2.md(t,last)>=12): state='open'; open_at=t
                elif state=='open':
                    seg=Bd[open_at:t]
                    if len(seg)>=r and bool((seg.iloc[-r:]>=q).all()):
                        cs=C[open_at-pd.DateOffset(months=3):t].dropna(); m=cs.idxmin() if len(cs) else t
                        out.append((t,m)); last=m; state='recover'
                else:
                    if dd<2.0: state='quiet'
            calls=shift_pub(out); rows.append((T2.line(f'  regional breadth k={k} q={q:.0f} r={r}',calls,T,show=False),k,q,r,calls))
        rows.sort(key=lambda x:(x[0][0],-x[0][1],x[0][5],x[0][4]),reverse=True)
        for res,k,q,r,calls in rows[:3]: T2.line(f'  regional breadth k={k} q={q:.0f} r={r}',calls,T)
        z=[x for x in rows if x[0][1]==0]
        if z: res,k,q,r,calls=z[0]; T2.line(f'  best with no other call k={k} q={q:.0f} r={r}',calls,T)
