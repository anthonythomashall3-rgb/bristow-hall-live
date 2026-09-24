import csv, glob, os, statistics
from collections import defaultdict
V1="/Users/anthonyhall/Projects/RecessionMonitor/raw"
NBER_PEAK={"2001":"2001-03","2008":"2007-12","2020":"2020-02"}  # business-cycle peaks

def load(path):
    out={}
    with open(path) as f:
        r=csv.reader(f); next(r,None)
        for row in r:
            if len(row)<2: continue
            d,v=row[0],row[1]
            if v in("",".","NA"): continue
            try: out[d[:7]]=float(v)
            except: pass
    return out

def panel(layer,pat):
    files=glob.glob(os.path.join(V1,layer,pat))
    P={}
    for fp in files:
        name=os.path.basename(fp).replace(".csv","")
        s=load(fp)
        if len(s)>24: P[name]=s
    return P

def all_months(P):
    ms=set()
    for s in P.values(): ms|=set(s.keys())
    return sorted(ms)

def diffusion(P, rising_is_bad, lag=3):
    # share of members whose lag-month change is in the 'deterioration' direction
    ms=all_months(P)
    res={}
    for i,m in enumerate(ms):
        if i<lag: continue
        m0=ms[i-lag]
        num=den=0
        for s in P.values():
            if m in s and m0 in s:
                den+=1
                ch=s[m]-s[m0]
                if rising_is_bad:
                    if ch>0: num+=1   # UR up = bad
                else:
                    if ch<0: num+=1   # coincident down = bad
        if den>=10:
            res[m]=(num/den, den)
    return res

def onset_lead(diff, peak, thresh=0.5, sustain=2):
    # earliest month in [peak-18, peak] where diffusion >= thresh for `sustain` consecutive months
    ms=sorted(diff.keys())
    py,pm=int(peak[:4]),int(peak[5:7])
    def mnum(x): return int(x[:4])*12+int(x[5:7])
    pk=py*12+pm
    cross=None
    for i,m in enumerate(ms):
        if not(pk-18<=mnum(m)<=pk+3): continue
        window=[diff[ms[j]][0] for j in range(i,min(i+sustain,len(ms)))]
        if len(window)==sustain and all(w>=thresh for w in window):
            cross=m; break
    if cross is None: return None,None
    lead=pk-mnum(cross)   # positive = crosses before peak
    return cross,lead

def peak_val(diff, peak, win=6):
    py,pm=int(peak[:4]),int(peak[5:7]); pk=py*12+pm
    def mnum(x): return int(x[:4])*12+int(x[5:7])
    vals=[(m,diff[m][0]) for m in diff if pk-3<=mnum(m)<=pk+win]
    if not vals: return None
    return max(vals,key=lambda x:x[1])

# PHCI: coincident indexes, decline is bad
phci=panel("phci","*.csv")
phci_diff=diffusion(phci, rising_is_bad=False, lag=3)
# State UR: rise is bad
ur=panel("states","*UR.csv")
ur={k:v for k,v in ur.items() if len(k)==4 and k.endswith("UR")}  # <ST>UR
ur_diff=diffusion(ur, rising_is_bad=True, lag=3)

print("=== PHCI panel members:",len(phci)," UR panel members:",len(ur))
for label,diff in [("PHCI_3mo_decline",phci_diff),("StateUR_3mo_rise",ur_diff)]:
    print(f"\n--- {label} ---")
    for ep,peak in NBER_PEAK.items():
        cross,lead=onset_lead(diff,peak)
        pk=peak_val(diff,peak)
        print(f"  {ep} peak={peak}: cross@{cross} lead={lead}mo  peak_diffusion={pk}")

# baseline false-alarm: max diffusion in calm windows (mid-expansion)
def calm_max(diff, windows):
    def mnum(x): return int(x[:4])*12+int(x[5:7])
    out={}
    for name,(a,b) in windows.items():
        aa,bb=mnum(a+"-01" if len(a)==4 else a),mnum(b+"-01" if len(b)==4 else b)
        vals=[diff[m][0] for m in diff if aa<=mnum(m)<=bb]
        out[name]=max(vals) if vals else None
    return out
calm={"1995-96":("1995-01","1996-12"),"2005-06":("2005-01","2006-12"),"2014-16":("2014-01","2016-12")}
for label,diff in [("PHCI",phci_diff),("StateUR",ur_diff)]:
    print(f"\n{label} calm-window max diffusion (false-alarm gauge):",calm_max(diff,calm))
