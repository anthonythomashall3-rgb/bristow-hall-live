import urllib.request,json,urllib.parse,re,ast,hashlib,os,datetime,pickle
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
def rel_date(v):
    m=re.search(r'([A-Za-z]+)-(\d{1,2})-(\d{4})',v)
    if not m: return None
    try: return datetime.datetime.strptime(f"{m.group(1)}-{m.group(2)}-{m.group(3)}","%B-%d-%Y").date().isoformat()
    except Exception: return None
def now(): return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
fa=pickle.loads(open(ROOT+"/_fa.pkl","rb").read())
m=json.load(open(ROOT+"/FETCH_MANIFEST.v1.json"))
# drop the stale not-found failures we are now handling
m["failures"]=[f for f in m["failures"] if "subdir not found" not in f.get("reason","")]
total=m["total_bytes"]
NAMES={3:"Industry",4:"International_Transactions",5:"Regional",6:"IntegratedMacroAcct"}
CAP=m["cap_bytes"]
for hmi,name in NAMES.items():
    # year dirs are direct entries of fa[hmi]
    ny=[p for p in fa[hmi] if re.fullmatch(r'\d{4}',leaf(p).split('/')[-1])]
    ny.sort(key=lambda p:leaf(p).split('/')[-1])
    if not ny:
        m["failures"].append({"target":f"{hmi}/{name}","reason":"no numeric year dirs (direct)"}); continue
    chosen=[ny[0]] if len(ny)==1 else [ny[0],ny[-1]]
    for yp in chosen:
        qs=kids(hmi,yp)
        node=qs[0] if qs else None
        # descend until we reach a vintage leaf that has files
        depth=0
        while node is not None and depth<5:
            fl=files_at(hmi,node)
            if fl: break
            sub=kids(hmi,node)
            node=sub[0] if sub else None; depth+=1
        if not node:
            m["failures"].append({"target":f"{hmi}/{leaf(yp)}","reason":"no leaf files found"}); continue
        try: flist=files_at(hmi,node)
        except Exception as e:
            m["failures"].append({"path":leaf(node),"reason":f"files_at {e}"}); continue
        vint=leaf(node).split('/')[-1]
        for fpath in flist:
            if total>=CAP: m["cap_hit"]=True; break
            if fpath.lower().endswith(".inc"): continue
            pub=to_public(fpath); enc=urllib.parse.quote(pub,safe=':/')
            dest=os.path.join(ROOT,leaf(fpath))
            try:
                s,b,h=get(enc)
                os.makedirs(os.path.dirname(dest),exist_ok=True); open(dest,"wb").write(b)
                total+=len(b)
                m["objects"].append({"account_hmi":hmi,"subdir":name,"public_url":pub,"staging_path":dest,
                    "http_status":s,"last_modified":h.get("Last-Modified"),"content_type":h.get("Content-Type"),
                    "bytes":len(b),"sha256":hashlib.sha256(b).hexdigest(),"fetch_utc":now(),
                    "vintage_dir":vint,"release_date":rel_date(vint)})
            except Exception as e:
                m["failures"].append({"public_url":pub,"reason":f"{type(e).__name__}:{e}"})
        m["object_count"]=len(m["objects"]); m["total_bytes"]=total; m["failure_count"]=len(m["failures"])
        open(ROOT+"/FETCH_MANIFEST.v1.json","w").write(json.dumps(m,indent=1))
print("objects",m["object_count"],"bytes",total,"failures",len(m["failures"]))
