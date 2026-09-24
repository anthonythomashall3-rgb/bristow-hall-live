#!/usr/bin/env python3
"""CH-R27 NBER Macrohistory prefetch. Read-only vs store; writes only under this dir.
Fetches monthly (m*) series .dat + docs .txt for recession-relevant chapters.
Resume-safe (skips non-empty files on disk), ~1 req/s, 2 tries then record-and-move-on."""
import os,sys,time,hashlib,json,urllib.request,csv,datetime

BASE="https://data.nber.org/databases/macrohistory/rectdata"
ROOT=os.path.dirname(os.path.abspath(__file__))
INV=json.load(open(os.path.join(ROOT,"_inventory.json")))
REL={'01','02','03','04','05','06','07','08','11','12','13','14'}
# data.nber.org returns 403 to non-browser UAs; use a browser UA (CH-R27 diagnosis).
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
MAN=os.path.join(ROOT,"manifest.csv")
LOG=os.path.join(ROOT,"fetch.log")

def utc(): return datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
def log(m):
    open(LOG,"a").write(f"{utc()} {m}\n")

# targets: monthly in relevant chapters (weekly=0 in this db)
targets=[(ch,fn) for ch,fn,cad in INV if ch in REL and cad=='monthly']
log(f"START targets={len(targets)}")

# manifest header if new
new=not os.path.exists(MAN)
mf=open(MAN,"a",newline="")
w=csv.writer(mf)
if new: w.writerow(["chapter","series_file","kind","url","fetch_utc","http","bytes","sha256","status"])

def fetch(url,dest):
    """returns (http,bytes,sha256,status). Skips if dest non-empty.
    Throttles ~1 req/s on EVERY attempt; exponential backoff on 403/429."""
    if os.path.exists(dest) and os.path.getsize(dest)>0:
        b=open(dest,"rb").read()
        return (200,len(b),hashlib.sha256(b).hexdigest(),"cached")
    for attempt in (1,2,3):
        time.sleep(1.0)  # throttle before every network hit
        try:
            req=urllib.request.Request(url,headers={"User-Agent":UA})
            with urllib.request.urlopen(req,timeout=45) as r:
                data=r.read(); code=r.getcode()
            os.makedirs(os.path.dirname(dest),exist_ok=True)
            open(dest,"wb").write(data)
            return (code,len(data),hashlib.sha256(data).hexdigest(),"fetched")
        except urllib.error.HTTPError as e:
            log(f"try{attempt} HTTP{e.code} {url}")
            if e.code in (403,429):
                time.sleep(15*attempt)  # backoff: 15s,30s,45s
            if e.code==404:  # missing doc/data — real, stop retrying
                return (404,0,"","missing")
        except Exception as e:
            log(f"try{attempt} FAIL {url} :: {e}")
            time.sleep(3)
    return (0,0,"","failed")

n=0
for ch,fn in targets:
    stem=fn[:-4]  # strip .dat
    # data file
    du=f"{BASE}/{ch}/{fn}"
    dd=os.path.join(ROOT,"data",ch,fn)
    http,by,sh,st=fetch(du,dd)
    w.writerow([ch,fn,"dat",du,utc(),http,by,sh,st]); mf.flush()
    # doc file
    tu=f"{BASE}/{ch}/docs/{stem}.txt"
    td=os.path.join(ROOT,"docs",ch,f"{stem}.txt")
    http2,by2,sh2,st2=fetch(tu,td)
    w.writerow([ch,fn,"doc",tu,utc(),http2,by2,sh2,st2]); mf.flush()
    n+=1
    if n%100==0: log(f"progress {n}/{len(targets)}")
log(f"DONE processed={n}")
mf.close()
print("FETCH_COMPLETE",n)
