"""The survivors of the collection-25 sweep (15,128 daily/weekly/biweekly files) run through the machine as extra
confirmers, at their construction-grade lines and above. Only configurations that keep 13/13 and no other call on
either vintage are reported as OK."""
from mini import *
from legu_min import s_cur, spl
exec(open('daily1.py').read().split('P("\\nbaseline v3.0")')[0].replace("out=open('daily1.out','w')","out=open('daily6.out','w')"))
import glob,pickle
C25=os.path.join(os.environ['HOME'],'mnt','Onset Detector Data','25_fred_daily_weekly')
def L25(nm):
    for d in ['fred_daily','fred_weekly','fred_biweekly']:
        p=os.path.join(C25,d,nm+'.csv')
        if os.path.exists(p):
            x=pd.read_csv(p).iloc[:,:2]; x.columns=['d','v']; x['d']=pd.to_datetime(x['d'],errors='coerce')
            s=pd.to_numeric(x.set_index('d')['v'],errors='coerce').dropna(); return s[s.index.notna()]
    return None
C=[]
for f in glob.glob('cache/daily5_cands_*.pkl'): C+=pickle.load(open(f,'rb'))
d=pd.DataFrame(C,columns=['id','kind','wmon','win','line','nrec','qmax','nq','start'])
d=d[~d.id.isin(('CC','ICSA','IURSA','CCSA','CC4WSA','ICNSA','CCNSA','IURNSA','IC4WSA','CCNSA'))]
d['start']=pd.to_datetime(d['start'])
top=pd.concat([d[d.start<'1968-01-01'].sort_values(['nq','nrec'],ascending=False).drop_duplicates(['id','kind']).head(30),
               d.sort_values(['nrec','nq'],ascending=False).drop_duplicates(['id','kind']).head(20)]).drop_duplicates(['id','kind','wmon'])
P("baseline v3.1"); go9('v3.1',[CRED]) if 'CRED' in dir() else None
CREDs=L25('NFCICREDIT'); CRED=dict(name='credit12',gap=(CREDs-CREDs.rolling(12).min()).dropna(),line=1.25,pub_lag_days=1)
P("baseline v3.1"); go9('v3.1 (credit 1.25)',[CRED])
P(f"\n--- {len(top)} survivors run through the machine (line, then 1.25x and 1.6x the construction-grade line) ---")
for _,r in top.iterrows():
    s=L25(r['id'])
    if s is None: P(f"   {r['id']}: not found"); continue
    G=((s.rolling(int(r['win'])).max()-s) if r['kind']=='fall' else (s-s.rolling(int(r['win'])).min())).dropna()
    for mult in [1.0,1.25,1.6]:
        ln=round(float(r['line'])*mult,6)
        go9(f"{r['id']} {r['kind']}{int(r['wmon'])}m >= {ln:g}",[CRED,dict(name=r['id'],gap=G,line=ln,pub_lag_days=1)])
out.close()
