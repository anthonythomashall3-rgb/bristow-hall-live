import urllib.request,json,urllib.parse,re,ast,hashlib,os,datetime,sys
UA={"User-Agent":"Mozilla/5.0 Chrome/120"}
ROOT="research/_staging/bea_histdata"
API="https://apps.bea.gov/histdata/core/data/"
def get(u,timeout=60):
    req=urllib.request.Request(u,headers=UA)
    with urllib.request.urlopen(req,timeout=timeout) as r: return r.status,r.read(),dict(r.headers)
def kids(hmi,tp):
    u=API+f"Fea_DisplayChildrenC/?HistMainId={hmi}&thePath={urllib.parse.quote(tp)}&getFiles=false&getDirs=true"
    s,b,h=get(u); j=json.loads(b); row=j[0] if isinstance(j,list) else j
    fa=row.get("FileArray")
    if isinstance(fa,str) and fa.strip().startswith('['): fa=ast.literal_eval(fa)
    return fa or []
def files_at(hmi,tp):
    u=API+f"Fea_DisplayChildrenC/?HistMainId={hmi}&thePath={urllib.parse.quote(tp)}&getFiles=true&getDirs=false"
    s,b,h=get(u); j=json.loads(b); row=j[0] if isinstance(j,list) else j
    fa=row.get("FileArray")
    if isinstance(fa,str) and fa.strip().startswith('['): fa=ast.literal_eval(fa)
    return fa or []
def leaf(p): return re.split(r'Releases[\\/]',p)[-1].replace('\\','/')
def to_public(p):
    p=re.sub(r'(?i)Inetpub/wwwroot/website/website/HistData','apps.bea.gov/HistData',p.lstrip('/'))
    return 'https://'+p.replace('\\','/')
def rel_date(vintdir):
    m=re.search(r'([A-Za-z]+)-(\d{1,2})-(\d{4})',vintdir)
    if not m: return None
    try:
        return datetime.datetime.strptime(f"{m.group(1)}-{m.group(2)}-{m.group(3)}","%B-%d-%Y").date().isoformat()
    except Exception: return None
def now(): return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

# selection: (hmi, subdir-internal-path-fragment). Bounded representative slice.
# earliest + latest numeric year per chosen subdir; ALL vintages of those years.
import pickle
fa=pickle.loads(open(ROOT+"/_fa.pkl","rb").read())
def sub_internal(hmi,name):
    for p in fa[hmi]:
        if leaf(p)==name: return p
    return None
TARGETS=[(2,"GDP_and_PI"),(5,"Regional"),(3,"Industry"),(4,"International_Transactions"),(6,"IntegratedMacroAcct")]
CAP_BYTES=220*1024*1024
manifest={"batch":"B-FETCH-BEA-HISTDATA","fetched_utc":now(),"api_base":API,
          "public_pattern":"https://apps.bea.gov/HistData/Files/Releases/<subdir>/<year>/<Q>/<n. Stage_Month-DD-YYYY>/<file>",
          "cap_bytes":CAP_BYTES,"objects":[],"failures":[],"selection_rule":"earliest+latest numeric release-year per target subdir, ALL vintages/files of those years; bounded representative slice, NOT full archive"}
total=0
def numeric_years(hmi,subpath):
    ys=kids(hmi,subpath)
    num=[y for y in ys if re.fullmatch(r'\d{4}',leaf(y).split('/')[-1])]
    num.sort(key=lambda p:leaf(p).split('/')[-1])
    return num
for hmi,name in TARGETS:
    sp=sub_internal(hmi,name)
    if sp is None:
        manifest["failures"].append({"target":f"{hmi}/{name}","reason":"subdir not found in FileArray"}); continue
    ny=numeric_years(hmi,sp)
    if not ny:
        manifest["failures"].append({"target":f"{hmi}/{name}","reason":"no numeric year dirs"}); continue
    chosen=[ny[0]] if len(ny)==1 else [ny[0],ny[-1]]
    manifest["selection_rule"]="earliest+latest numeric release-year per target subdir; ONE representative vintage (first quarter's first vintage leaf) per boundary year, ALL its files; bounded representative slice, NOT full archive"
    for yp in chosen:
        qs=kids(hmi,yp)
        if not qs: continue
        vps=kids(hmi,qs[0])
        if not vps: continue
        vp=vps[0]
        vint=leaf(vp).split('/')[-1]
        try: flist=files_at(hmi,vp)
        except Exception as e:
            manifest["failures"].append({"path":leaf(vp),"reason":f"files_at {type(e).__name__}:{e}"}); continue
        for fpath in flist:
            if total>=CAP_BYTES: manifest["cap_hit"]=True; break
            pub=to_public(fpath); enc=urllib.parse.quote(pub,safe=':/')
            dest=os.path.join(ROOT,leaf(fpath))
            try:
                s,b,h=get(enc)
                os.makedirs(os.path.dirname(dest),exist_ok=True)
                open(dest,"wb").write(b)
                total+=len(b)
                manifest["objects"].append({"account_hmi":hmi,"subdir":name,"public_url":pub,
                    "staging_path":dest,"http_status":s,"last_modified":h.get("Last-Modified"),
                    "content_type":h.get("Content-Type"),"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest(),
                    "fetch_utc":now(),"vintage_dir":vint,"release_date":rel_date(vint)})
            except Exception as e:
                manifest["failures"].append({"public_url":pub,"reason":f"{type(e).__name__}:{e}"})
            manifest["object_count"]=len(manifest["objects"]); manifest["total_bytes"]=total
            open(ROOT+"/FETCH_MANIFEST.v1.json","w").write(json.dumps(manifest,indent=1))
        if manifest.get("cap_hit"): break
manifest["total_bytes"]=total
manifest["object_count"]=len(manifest["objects"])
manifest["failure_count"]=len(manifest["failures"])
open(ROOT+"/FETCH_MANIFEST.v1.json","w").write(json.dumps(manifest,indent=1))
print("objects",len(manifest["objects"]),"bytes",total,"failures",len(manifest["failures"]),"cap_hit",manifest.get("cap_hit",False))
# per-account summary
from collections import defaultdict
by=defaultdict(lambda:[0,0])
for o in manifest["objects"]: by[o["subdir"]][0]+=1; by[o["subdir"]][1]+=o["bytes"]
for k,v in by.items(): print(" ",k,"files",v[0],"bytes",v[1])
