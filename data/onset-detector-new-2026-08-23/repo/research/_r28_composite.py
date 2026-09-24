import sys, os, json, csv, datetime as dt, shutil, subprocess
sys.path.insert(0,'research')
from _r28_lib import members, load_source, asof_date
DATES=[dt.date(2012,6,1),dt.date(2015,9,1),dt.date(2019,3,1),dt.date(2020,4,1),dt.date(2022,10,1),dt.date(2024,6,1)]
CUR="data_archive/current_revised_and_spatial/"
ALL=["ICSA","IURSA","SAHMREALTIME","UNRATE","INDPRO","CMRMTSPL","TCU","GACDFSA066MSFRBPHI",
 "NASDAQCOM","BAA","AAA","BAA10Y","NFCI","VIXCLS","HOUST","PERMIT","UMCSENT","W875RX1",
 "GS10","GS1","USRECD","RRSFS","MORTGAGE30US","PAYEMS","CCSA","DBAA","DAAA"]
# member -> fred id used by index_v1 (revising only)
MEMFRED={'ICSA':'ICSA','IURSA':'IURSA','SAHM':'SAHMREALTIME','UNRATEv':'UNRATE','INDPRO':'INDPRO',
 'CMRMT':'CMRMTSPL','TCU':'TCU','PHILLY':'GACDFSA066MSFRBPHI','NFCI':'NFCI','HOUST':'HOUST',
 'PERMIT':'PERMIT','UMCSENT':'UMCSENT','W875':'W875RX1'}
def to_date(s):
    s=s[:10]; return dt.date(int(s[:4]),int(s[5:7]),int(s[8:10]))
ms,ch=members()
# preload store tuples
SRC={}
for name,m in ms.items():
    for s in m['store_vintage_sources']:
        if s in SRC: continue
        try: h,rr=load_source(s)
        except Exception: SRC[s]=[]; continue
        t=[]
        for r in rr:
            a=asof_date(r.get('series_id'))
            if a is None: continue
            try: v=float(r['value'])
            except: continue
            t.append((a,to_date(r['observation_period']),v))
        SRC[s]=t
print('store loaded',file=sys.stderr)
def asof_series(tuples,D):
    best={}
    for a,op,v in tuples:
        if a>D: continue
        c=best.get(op)
        if c is None or a>c[0]: best[op]=(a,v)
    return {op:val for op,(a,val) in best.items()}
def read_cur(fred):
    o={}
    for r in csv.reader(open(CUR+fred+".csv")):
        if r and r[0][:1].isdigit() and len(r)>1 and r[1] not in("","."):
            o[to_date(r[0])]=float(r[1])
    return o
def write_csv(path,series):
    with open(path,'w',newline='') as f:
        w=csv.writer(f); w.writerow(['date','value'])
        for d in sorted(series): w.writerow([d.isoformat(),series[d]])
RUN="research/r28_run"; os.makedirs(RUN,exist_ok=True)
def run_index(rawdir,out):
    env=dict(os.environ); env['NOWCAST_DISABLE']='1'; env['INDEX_OUT']=os.path.abspath(out)
    r=subprocess.run([sys.executable, os.path.abspath('method_source/index_v1.py')],
                     cwd=rawdir, env=env, capture_output=True, text=True, timeout=600)
    return r
# ---- baseline: current-vintage published proxy ----
base=os.path.join(RUN,'cur'); os.makedirs(os.path.join(base,'raw'),exist_ok=True)
for s in ALL: shutil.copy(CUR+s+'.csv', os.path.join(base,'raw',s+'.csv'))
r=run_index(base, os.path.join(base,'out.json'))
print('CUR run rc',r.returncode, r.stderr[-300:] if r.returncode else r.stdout.strip().splitlines()[-1] if r.stdout else '',file=sys.stderr)
curline=json.load(open(os.path.join(base,'out.json')))['line']
# ---- per-date as-of runs (truncated ≤D, revising members swapped to as-of) ----
results=[]
for D in DATES:
    wd=os.path.join(RUN,'asof_'+D.isoformat()); os.makedirs(os.path.join(wd,'raw'),exist_ok=True)
    fallback=[]; asofm=[]
    for s in ALL:
        cur=read_cur(s)
        curT={d:v for d,v in cur.items() if d<=D}
        # is this a revising member with store as-of coverage?
        mem=[k for k,f in MEMFRED.items() if f==s]
        if mem:
            name=mem[0]; srcs=ms[name]['store_vintage_sources']
            tup=[]
            for src in srcs: tup+=SRC.get(src,[])
            asf=asof_series(tup,D)
            asf={op:v for op,v in asf.items() if op<=D}
            if asf:
                write_csv(os.path.join(wd,'raw',s+'.csv'),asf); asofm.append(name); continue
            else:
                fallback.append(name)
        write_csv(os.path.join(wd,'raw',s+'.csv'),curT)
    r=run_index(wd, os.path.join(wd,'out.json'))
    if r.returncode!=0:
        print('ASOF',D,'FAIL',r.stderr[-400:],file=sys.stderr); results.append((D,None,None,fallback,asofm)); continue
    aline=json.load(open(os.path.join(wd,'out.json')))['line']
    # composite value AT D (carry-forward last <=D)
    def val_at(line,D):
        ks=[k for k in line if to_date(k)<=D]
        if not ks: return None
        return line[max(ks,key=lambda k:to_date(k))]
    cv=val_at(curline,D); av=val_at(aline,D)
    results.append((D,cv,av,fallback,asofm))
    print('ASOF',D,'cur=%.3f asof=%.3f'%(cv,av) if cv and av else (cv,av),file=sys.stderr)
out=[]
for D,cv,av,fb,am in results:
    out.append({'date':str(D),'published_composite':round(cv,4) if cv is not None else None,
                'asof_composite':round(av,4) if av is not None else None,
                'divergence':round(abs(cv-av),4) if (cv is not None and av is not None) else None,
                'n_asof_members':len(am),'n_fallback_members':len(fb),'fallback_members':fb})
json.dump(out,open('research/r28_composite.json','w'),indent=1)
print(json.dumps(out,indent=1))
