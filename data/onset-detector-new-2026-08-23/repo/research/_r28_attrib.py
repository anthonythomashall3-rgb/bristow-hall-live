import sys,os,json,csv,datetime as dt,shutil,subprocess
DATES=[dt.date(2012,6,1),dt.date(2015,9,1),dt.date(2019,3,1),dt.date(2020,4,1),dt.date(2022,10,1),dt.date(2024,6,1)]
CUR="data_archive/current_revised_and_spatial/"
ALL=["ICSA","IURSA","SAHMREALTIME","UNRATE","INDPRO","CMRMTSPL","TCU","GACDFSA066MSFRBPHI",
 "NASDAQCOM","BAA","AAA","BAA10Y","NFCI","VIXCLS","HOUST","PERMIT","UMCSENT","W875RX1",
 "GS10","GS1","USRECD","RRSFS","MORTGAGE30US","PAYEMS","CCSA","DBAA","DAAA"]
def to_date(s): s=s[:10]; return dt.date(int(s[:4]),int(s[5:7]),int(s[8:10]))
def read_cur(f):
    o={}
    for r in csv.reader(open(CUR+f+".csv")):
        if r and r[0][:1].isdigit() and len(r)>1 and r[1] not in("","."): o[to_date(r[0])]=float(r[1])
    return o
def write_csv(p,s):
    with open(p,'w',newline='') as f:
        w=csv.writer(f); w.writerow(['date','value'])
        for d in sorted(s): w.writerow([d.isoformat(),s[d]])
RUN="research/r28_run"
def run_index(rd,out):
    env=dict(os.environ); env['NOWCAST_DISABLE']='1'; env['INDEX_OUT']=os.path.abspath(out)
    return subprocess.run([sys.executable,os.path.abspath('method_source/index_v1.py')],cwd=rd,env=env,capture_output=True,text=True,timeout=600)
curline=json.load(open(os.path.join(RUN,'cur','out.json')))['line']
def val_at(line,D):
    ks=[k for k in line if to_date(k)<=D]
    return line[max(ks,key=lambda k:to_date(k))] if ks else None
comp=json.load(open('research/r28_composite.json'))
out=[]
for row in comp:
    D=dt.date.fromisoformat(row['date'])
    wd=os.path.join(RUN,'curT_'+D.isoformat()); os.makedirs(os.path.join(wd,'raw'),exist_ok=True)
    for s in ALL:
        c=read_cur(s); write_csv(os.path.join(wd,'raw',s+'.csv'),{d:v for d,v in c.items() if d<=D})
    r=run_index(wd,os.path.join(wd,'out.json'))
    curT=val_at(json.load(open(os.path.join(wd,'out.json')))['line'],D) if r.returncode==0 else None
    pub=row['published_composite']; asof=row['asof_composite']
    baseline_recency = round(abs(pub-curT),4) if curT is not None else None   # full-hist vs through-D, current inputs
    input_revision   = round(abs(asof-curT),4) if (curT is not None and asof is not None) else None  # vintage vs current, same window
    out.append({'date':row['date'],'published':pub,'curT_throughD':round(curT,4) if curT else None,
                'asof':asof,'total_div':row['divergence'],
                'attrib_baseline+recency':baseline_recency,'attrib_input_revision':input_revision,
                'n_fallback':row['n_fallback_members']})
json.dump(out,open('research/r28_attribution.json','w'),indent=1)
print(json.dumps(out,indent=1))
