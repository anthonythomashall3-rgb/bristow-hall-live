import json,urllib.request,os,time,hashlib,datetime
KEY=os.environ["FRASER_API_KEY"]
ANCHORS=["1973-11-01","1980-01-01","1981-07-01","1990-07-01","2001-03-01","2008-09-01","2020-02-01"]
def d2(s):
    try: return datetime.date.fromisoformat(s[:10])
    except: return None
def fetch(url):
    req=urllib.request.Request(url,headers={"X-API-Key":KEY,"User-Agent":"RMV2-BFETCH-FRASER"})
    with urllib.request.urlopen(req,timeout=90) as r:
        return r.getcode(), r.read()
SLUGS=["employment_situation","employment_earnings","employment_earnings_us",
       "g17_industrial_production","g123_industrial_production","survey_current_business"]
man=[]
st="research/_staging/fraser/_dl_status.txt"
for slug in SLUGS:
    D=json.load(open(f"research/_staging/fraser/{slug}_items.json"))
    items=[i for i in D["items"] if i.get("pdfUrl") and i.get("sortDate")]
    items.sort(key=lambda i:i["sortDate"])
    picks={}
    if items:
        picks[items[0]["rid"]]=("earliest",items[0])
        picks[items[-1]["rid"]]=("latest",items[-1])
        for a in ANCHORS:
            ad=d2(a)
            cand=min(items,key=lambda i:abs((d2(i["sortDate"])-ad).days) if d2(i["sortDate"]) else 10**9)
            cd=d2(cand["sortDate"])
            if cd and abs((cd-ad).days)<=550:
                picks.setdefault(cand["rid"],(f"anchor_{a[:4]}",cand))
    outdir=f"research/_staging/fraser/{slug}"; os.makedirs(outdir,exist_ok=True)
    for rid,(tag,it) in picks.items():
        url=it["pdfUrl"]; fn=url.split("/")[-1] or f"{rid}.pdf"
        dest=f"{outdir}/{rid}__{fn}"
        rec={"slug":slug,"title_id":D["title_id"],"rid":rid,"tag":tag,
             "sortDate":it["sortDate"],"dateIssued":it.get("dateIssued"),
             "item_title":it.get("item_title"),"pageUrl":it.get("pageUrl"),
             "pdfUrl":url,"textUrl":it.get("textUrl"),
             "fetch_utc":datetime.datetime.now(datetime.timezone.utc).isoformat()}
        try:
            code,body=fetch(url)
            open(dest,"wb").write(body)
            rec.update({"http_status":code,"bytes":len(body),
                        "sha256":hashlib.sha256(body).hexdigest(),"local_path":dest})
        except Exception as e:
            rec.update({"http_status":None,"bytes":0,"error":str(e),"local_path":None})
        # sidecar
        json.dump(rec,open(dest+".sidecar.json","w"),indent=1) if rec.get("local_path") else None
        man.append(rec)
        open(st,"w").write(f"{slug} {tag} {rid} {rec.get('http_status')} {rec.get('bytes')}B\n")
        time.sleep(0.15)
json.dump(man,open("research/_staging/fraser/_sample_download_manifest.json","w"),indent=1)
ok=[m for m in man if m.get("bytes",0)>0]
open(st,"w").write(f"ALL_DONE downloaded {len(ok)}/{len(man)} bytes={sum(m.get('bytes',0) for m in man)}\n")
