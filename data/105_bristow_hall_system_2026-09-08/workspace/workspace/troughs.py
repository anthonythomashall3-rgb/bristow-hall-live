from mini import *
from hub import leg_X2
from legu_min import leg_U, s_cur
import legs_1948 as L
nat=pd.read_csv(W+'/lab/dol/US_nat_monthly_4ch_sa.csv',index_col=0,parse_dates=True)
print('Department national monthly file (real-time adjusted):',nat.shape,nat.index.min().date(),nat.index.max().date(),list(nat.columns))
SAFE=dict(H=8.0,J=5.0)
def clause(col,drop):
    s=np.log(nat[col].dropna()); return [(L.pub10(p-pd.DateOffset(months=1)),d) for p,d in B.level_trough_calls(s,drop=drop)]
cols=list(nat.columns)
ic_col=[c for c in cols if 'initial' in c.lower()][0]; cc_col=[c for c in cols if 'contin' in c.lower()][0]
Hd=clause(ic_col,SAFE['H']); Jd=clause(cc_col,SAFE['J'])
print("H on the Department's file:",[(p.strftime('%Y-%m-%d'),d.strftime('%Y-%m')) for p,d in Hd])
print("H on the Fieldhouse field :",[(p.strftime('%Y-%m-%d'),d.strftime('%Y-%m')) for p,d in TLG['H'] if p>=pd.Timestamp('1971-01-01')])
print("J on the Department's file:",[(p.strftime('%Y-%m-%d'),d.strftime('%Y-%m')) for p,d in Jd])
print("J on the Fieldhouse field :",[(p.strftime('%Y-%m-%d'),d.strftime('%Y-%m')) for p,d in TLG['J'] if p>=pd.Timestamp('1971-01-01')])
print("K (weekly continued claims):",[(p.strftime('%Y-%m-%d'),d.strftime('%Y-%m')) for p,d in TLG['K']])
print("S gated (Paper 1 Bristow rule):",[(p.strftime('%Y-%m-%d'),d.strftime('%Y-%m')) for p,d in TLG['S']])
print("T (Dept diffusion 48/13 trough clause):",[(p.strftime('%Y-%m-%d'),d.strftime('%Y-%m')) for p,d in TLG['T']])
X=leg_X2(); U=leg_U(s_cur)
def trow(nm,tl):
    r=score13(chron({'U':U,'X':X},tl,['V','H','P'])); lt=[r['lags_t'].get(i) for i in range(13)]; et=[r['errs_t'].get(i) for i in range(13)]
    v=[l for l in lt if l is not None]
    print(f"{nm:34}",[('-' if l is None else l) for l in lt],f"| n {len(v)} med {np.median(v):.0f} worst {max(v)} exact {sum(1 for e in et if e==0)} within1 {sum(1 for e in et if e is not None and abs(e)<=1)}; errs",[('-' if e is None else e) for e in et])
TLD=dict(TLG); TLD['Hd']=Hd; TLD['Jd']=Jd
for nm,keys in [("K,J,H,S (frozen closers + Paper 1)",'KJHS'),("K,S",'KS'),("K,J,H",'KJH'),("K + J,H on the Dept file (1971-) + S",['K','Jd','Hd','S']),("J,H (FH) + S, no K",'JHS'),("K,J,H,S,T",'KJHST')]:
    trow(nm,{k:TLD[k] for k in keys})
print("--- minimal closer sets ---")
for nm,keys in [("K + H (FH) + S",'KHS'),("K + H (Dept file) + S",['K','Hd','S']),("K + H,J (FH) + S = frozen",'KJHS'),("H (FH) + S only",'HS'),("K + H (Dept) + J (Dept) + S",['K','Hd','Jd','S'])]:
    trow(nm,{k:TLD[k] for k in keys})
