"""SPREADS — a class of object the 15,128-file sweep could not see, because a spread is not a series on the shelf.
Credit stress is the widening of a private money-market rate over the Treasury bill, and those rates exist WEEKLY from
1946-55 — long before the Chicago Fed's credit subindex begins in 1971. If any of them clears every quiet proposal
window, it is the only candidate that can reach 1960 and 1969, the two turns bound by a confirming object."""
from mini import *
from legu_min import s_cur, spl
exec(open('daily1.py').read().split('P("\\nbaseline v3.0")')[0].replace("out=open('daily1.out','w')","out=open('daily13.out','w')"))
C25=os.path.join(os.environ['HOME'],'mnt','Onset Detector Data','25_fred_daily_weekly')
def L25(nm):
    for d in ['fred_daily','fred_weekly','fred_biweekly']:
        p=os.path.join(C25,d,nm+'.csv')
        if os.path.exists(p):
            x=pd.read_csv(p).iloc[:,:2]; x.columns=['d','v']; x['d']=pd.to_datetime(x['d'],errors='coerce')
            s=pd.to_numeric(x.set_index('d')['v'],errors='coerce').dropna(); return s[s.index.notna()]
CS=L25('NFCICREDIT'); CRED=dict(name='credit12',gap=(CS-CS.rolling(12).min()).dropna(),line=1.25,pub_lag_days=1)
QP=sorted({dd for p_,dd in leg_gapL(s_cur,0.25,52,rearm='window') if not inw(dd)}|{dd for p_,dd in leg_gapL(spl,0.25,52,rearm='window') if not inw(dd)}
          |{dd for p_,dd in leg_gap_mx2(gm,0.25,boundary='ge') if dd<pd.Timestamp('1971-01-01') and not inw(dd)}
          |{dd for p_,dd in leg_gap_mx2(gm,0.45,boundary='ge') if dd<pd.Timestamp('1971-01-01') and not inw(dd)}
          |{dd for p_,dd in leg_gapL(s_cur,0.45,52,rearm='zero') if not inw(dd)}|{dd for p_,dd in leg_ic(IC,50) if not inw(dd)})
def wseg(G,dd):
    lo=dd-pd.DateOffset(months=6); hi=dd+pd.DateOffset(months=4)+pd.offsets.MonthEnd(0); return G[(G.index>=lo)&(G.index<=hi)]
PAIRS=[('CP3m-bill3m','H0RIFSPPFM03NWF','WTB3MS'),('CP1m-bill3m','H0RIFSPPFM01NWF','WTB3MS'),('CP6m-bill3m','H0RIFSPPFM06NWF','WTB3MS'),
       ('BA3m-bill3m','H1RIFSPABM03NWF','WTB3MS'),('prime-bill3m','WPRIME','WTB3MS'),('funds-bill3m','FF','WTB3MS'),
       ('bill6m-bill3m','WTB6MS','WTB3MS'),('CD3m-bill3m','WCD3M','WTB3MS'),('CP3m-funds','H0RIFSPPFM03NWF','FF'),
       ('prime-funds','WPRIME','FF'),('CP3m-bill3m_d','DCPF3M','DTB3'),('BA-bill_d','DBKAC','DTB3'),('prime-bill3m_d','DPRIME','DTB3'),
       ('CP1m-bill3m_alt','H0RIFSPPFM01NB','WTB3MS'),('CP2m-bill3m','H0RIFSPPFM02NB','WTB3MS')]
P("SPREADS BUILT AND SCREENED (the reading is the spread's RISE above its lowest value of the trailing window)")
CAND=[]
for nm,a,b in PAIRS:
    aa=L25(a); bb=L25(b)
    if aa is None or bb is None: P(f"   {nm}: {'missing '+a if aa is None else 'missing '+b}"); continue
    idx=aa.index.union(bb.index); S=(aa.reindex(idx).ffill()-bb.reindex(idx).ffill()).dropna()
    S=S[S.index>=max(aa.index.min(),bb.index.min())]
    if len(S)<300: continue
    per=max(1,int(round(float(np.median(np.diff(S.index.values).astype('timedelta64[D]').astype(int))))))
    row=[]
    for wmon in [3,6,12]:
        win=max(4,int(wmon*30/per)); GG=(S-S.rolling(win).min()).dropna()
        segs=[(float(wseg(GG,dd).max()),dd.strftime('%Y-%m')) for dd in QP if len(wseg(GG,dd))]
        if not segs: continue
        qmax=max(segs)[0] if segs else 0; qwho=max(segs)[1]; line=qmax*1.02
        rec={PK[i].strftime('%Y-%m'):(round(float(wseg(GG,PK[i]).max()),2) if len(wseg(GG,PK[i])) else None) for i in range(13)}
        nrec=sum(1 for v in rec.values() if v is not None and v>=line)
        row.append((wmon,round(line,3),qwho,nrec,len(segs)))
        if nrec>=2: CAND.append((nm,wmon,win,line,GG))
    P(f"   {nm:18s} {S.index.min().date()} -> {S.index.max().date()}  " + " | ".join(f"{w}m line {l:.2f} (quiet max at {q}) fires {n}/13, covers {c}" for w,l,q,n,c in row))
P(f"\n{len(CAND)} spread configurations fire in two or more recessions at a construction-grade line — through the machine:")
for nm,wmon,win,line,GG in CAND:
    for mult in [1.0,1.3,1.7]:
        go9(f"{nm} rise{wmon}m >= {line*mult:.3f}",[CRED,dict(name=nm,gap=GG,line=line*mult,pub_lag_days=1)])
out.close()
