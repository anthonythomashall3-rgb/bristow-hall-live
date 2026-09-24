"""The non-claims candidates from the sweep run through the machine as extra confirmers. Claims-family candidates (CCSA, CC4WSA, IURSA) are
excluded on the architecture's own rule — a claims object may not confirm a claims proposal — and the NBER indicator series are excluded as
circular. Lines construction-grade (just above the highest reading in any quiet proposal's window), then swept."""
from mini import *
from legu_min import s_cur, spl
exec(open('daily1.py').read().split('P("\\nbaseline v3.0")')[0].replace("out=open('daily1.out','w')","out=open('daily3.out','w')"))
def L(nm):
    for d in ['fred_daily','extra']:
        f=os.path.join(DD,d,nm+'.csv')
        if os.path.exists(f):
            x=pd.read_csv(f); x.columns=['d','v']; x['d']=pd.to_datetime(x['d']); return pd.to_numeric(x.set_index('d')['v'],errors='coerce').dropna()
SPEC=[('NFCICREDIT','rise',12,[0.72,0.80,0.90,1.00]),('NFCI','rise',51,[2.39,2.0,1.5,1.0]),('ANFCI','rise',51,[2.57,2.0,1.5]),
      ('T10Y2Y','rise',180,[1.50,1.25,1.00,0.75]),('CPFF','rise',180,[1.22,1.0,0.8]),('CPFF','fall',180,[1.17,1.0,0.8]),
      ('DCPN3M','fall',180,[2.09,1.5,1.0]),('DCPF3M','fall',180,[0.88,0.7,0.5]),('DFII5','fall',90,[0.95,0.7]),('EFFR','fall',180,[0.91,0.7]),
      ('DEXJPUS','rise',180,[45.6,35,25]),('WM2NS','rise',25,[332.7,250,200])]
P("baseline v3.0"); go9('v3.0',[])
for nm,kind,win,lines in SPEC:
    s=L(nm)
    if s is None: P(f"  {nm}: not held"); continue
    G=((s.rolling(win).max()-s) if kind=='fall' else (s-s.rolling(win).min())).dropna()
    P(f"\n{nm} {kind} over {win} obs: span {G.index.min().date()} -> {G.index.max().date()}")
    for ln in lines: go9(f'  {nm} {kind} >= {ln}',[dict(name=f'{nm}{kind}',gap=G,line=ln,pub_lag_days=1)])
out.close()
