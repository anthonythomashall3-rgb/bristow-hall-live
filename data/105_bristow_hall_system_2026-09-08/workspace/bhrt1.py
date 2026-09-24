"""THE TWO-SIDED RULE AS A PUBLISHED SERIES — the analogue of FRED's SAHMREALTIME.
SAHMREALTIME is one number a month: the Sahm gap computed on the unemployment rate AS IT WAS AVAILABLE THAT MONTH,
against a fixed line of 0.50. It begins in December 1959 because ALFRED's UNRATE vintages begin in March 1960 — the
same wall this rule meets. SAHMCURRENT is the same formula on today's revised file, from March 1949.
This builds the same pair for the two-sided rule. One number a month, on the same convention: the reading divided by
its line, so that 1.00 is exactly at the line and the rule calls at 1.00 or above.
   for each branch (U, L, I, hub): score = min(proposal reading / its line, best confirmer reading / its line in the window)
   the indicator = the largest branch score that month
A number below 1.00 says how far the tool is from speaking; 1.00 or above is a call."""
from mini import *
from legu_min import s_cur, spl
exec(open('daily4.py').read().split("qq=sorted(")[0].replace("out=open('daily4.out','w')","out=open('bhrt1.out','w')"))
C25=os.path.join(os.environ['HOME'],'mnt','Onset Detector Data','25_fred_daily_weekly')
D59=W.replace('24_bristow_rule_lab/workspace','59_dol_weekly_state_claims_1945-1983_2026-09')
def L25(nm):
    for d in ['fred_daily','fred_weekly','fred_biweekly']:
        p=os.path.join(C25,d,nm+'.csv')
        if os.path.exists(p):
            x=pd.read_csv(p).iloc[:,:2]; x.columns=['d','v']; x['d']=pd.to_datetime(x['d'],errors='coerce')
            s=pd.to_numeric(x.set_index('d')['v'],errors='coerce').dropna(); return s[s.index.notna()]
aa=L25('H0RIFSPPFM01NWF'); bb=L25('WTB3MS'); idx=aa.index.union(bb.index)
CPB=(aa.reindex(idx).ffill()-bb.reindex(idx).ffill()).dropna(); CPB=CPB[CPB.index>=max(aa.index.min(),bb.index.min())]
Sm=CPB.rolling(13).mean().dropna(); GSP=(Sm-Sm.rolling(39).min()).dropna(); SPRLINE=1.323
RT=pd.read_csv(os.path.join(D59,'national_iur_realtime_sa_first_prints_1948_1983.csv'),index_col=0,parse_dates=True).iloc[:,0].dropna()
def monthly_max(s):
    return s.resample('MS').max()
def build_series(vint):
    s = spl if vint=='realtime' else s_cur
    G=vgap(4,4)                                   # vacancy object
    Hc,MX=mkpair3(29,4,3,18)                      # housing x rate pair (MX is the pair's own reading)
    Hh=mkhours(2.0,1.20)
    gU=(s-s.rolling(91,min_periods=91).min().shift(1)).dropna()/0.45
    gL=(s-s.rolling(52,min_periods=52).min().shift(1)).dropna()/0.25
    ic = ICfp if vint=='realtime' else IC
    m4=ic.rolling(4).mean(); gI=((m4/m4.rolling(52,min_periods=52).min().shift(1)-1)*100).dropna()/50.0
    gX=(g/0.43).dropna()                          # the hub, Sahm's gap on first prints over the rule's line
    cV=(G/0.20); cH=(Hh['gap']/Hh['line']) if isinstance(Hh,dict) else None
    cP=(MX/1.0) if MX is not None else None; cS=(GSP/SPRLINE)
    idx=pd.date_range('1948-01-01','2026-08-01',freq='MS')
    def mm(x): return monthly_max(x).reindex(idx)
    U,L,I,X = mm(gU),mm(gL),mm(gI),mm(gX)
    V,Hp,Pp,Sp = mm(cV),mm(cH) if cH is not None else None,mm(cP) if cP is not None else None,mm(cS)
    def best_conf(which,t):
        """the best confirmer available to a branch in the window six months back and four forward"""
        lo=t-pd.DateOffset(months=6); hi=t+pd.DateOffset(months=4)
        vals=[]
        for c in ([V,Hp,Sp] if which in ('U','I') else [Pp,Sp]):
            if c is None: continue
            w=c[(c.index>=lo)&(c.index<=hi)].dropna()
            if len(w): vals.append(float(w.max()))
        return max(vals) if vals else np.nan
    rows={}
    for t in idx:
        best=np.nan; who=''
        for nm,leg in [('U',U),('L',L),('I',I)]:
            p=leg.get(t,np.nan)
            if np.isnan(p): continue
            sc=min(p,best_conf(nm,t))
            if np.isnan(best) or sc>best: best,who=sc,nm
        p=X.get(t,np.nan)
        if not np.isnan(p):
            w=V[(V.index>=t-pd.DateOffset(months=6))&(V.index<=t)].dropna()
            sc=min(p,float(w.max()) if len(w) else np.nan)
            if np.isnan(best) or sc>best: best,who=sc,'hub'
        rows[t]=(best,who)
    return pd.DataFrame({'indicator':{k:v[0] for k,v in rows.items()},'branch':{k:v[1] for k,v in rows.items()}})
for vint,nm in [('realtime','BHRT_REALTIME'),('current','BHRT_CURRENT')]:
    df=build_series(vint); df=df.dropna(subset=['indicator'])
    df.to_csv(f'cache/{nm}.csv')
    P(f"{nm}: {df.index.min():%Y-%m} -> {df.index.max():%Y-%m}, {len(df)} months; at or above 1.00 in {(df['indicator']>=1).sum()} months")
    P("   2024: "+", ".join(f"{t:%Y-%m} {v:.2f}" for t,v in df.loc['2024','indicator'].items()))
    P("   latest twelve: "+", ".join(f"{t:%Y-%m} {v:.2f}" for t,v in df['indicator'].tail(12).items()))
out.close()
