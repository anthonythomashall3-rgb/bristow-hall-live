import csv, glob, os
V1="/Users/anthonyhall/Projects/RecessionMonitor/raw"
NBER_PEAK={"2001":"2001-03","2008":"2007-12","2020":"2020-02"}
def load(p):
    o={}
    with open(p) as f:
        r=csv.reader(f); next(r,None)
        for row in r:
            if len(row)<2 or row[1] in("",".","NA"): continue
            try:o[row[0][:7]]=float(row[1])
            except:pass
    return o
def panel(layer,pat):
    P={}
    for fp in glob.glob(os.path.join(V1,layer,pat)):
        n=os.path.basename(fp).replace(".csv","")
        s=load(fp)
        if len(s)>24:P[n]=s
    return P
def mnum(x):return int(x[:4])*12+int(x[5:7])
def diffusion(P,lag=3):
    ms=sorted(set().union(*[set(s) for s in P.values()]))
    res={}
    for i,m in enumerate(ms):
        if i<lag:continue
        m0=ms[i-lag];num=den=0
        for s in P.values():
            if m in s and m0 in s:
                den+=1
                if s[m]-s[m0]>0:num+=1
        if den>=10:res[m]=num/den
    return res
def lead(diff,peak,thr,sustain=2):
    ms=sorted(diff);pk=mnum(peak)
    for i,m in enumerate(ms):
        if not(pk-18<=mnum(m)<=pk+3):continue
        w=[diff[ms[j]] for j in range(i,min(i+sustain,len(ms)))]
        if len(w)==sustain and all(x>=thr for x in w):return m,pk-mnum(m)
    return None,None
def calm_max(diff,a,b):
    aa,bb=mnum(a),mnum(b)
    return max([v for m,v in diff.items() if aa<=mnum(m)<=bb])
ur=panel("states","*UR.csv");ur={k:v for k,v in ur.items() if len(k)==4}
d=diffusion(ur)
for thr in (0.5,0.6,0.7,0.8):
    leads={ep:lead(d,pk,thr)[1] for ep,pk in NBER_PEAK.items()}
    fa={w:round(calm_max(d,a,b),2) for w,(a,b) in {"1995-96":("1995-01","1996-12"),"2005-06":("2005-01","2006-12"),"2014-16":("2014-01","2016-12")}.items()}
    print(f"thr={thr}: leads={leads}  calm_max={fa}")
