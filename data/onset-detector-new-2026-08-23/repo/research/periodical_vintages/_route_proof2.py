import os,json,urllib.request,time,datetime
OUT="research/periodical_vintages"
K=os.environ["FRASER_API_KEY"]; GK=os.environ.get("GOVINFO_API_KEY","DEMO_KEY")
UTC=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
def jget(url,headers,tries=5,timeout=60):
    last=None
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=timeout) as r:
                return json.load(r)
        except Exception as e: last=e; time.sleep(1.0*(i+1))
    raise last
def one(v): return v[0] if isinstance(v,list) and v else v

# Fed Bulletin (t/62) full enum
tid,slug,name=62,"federal_reserve_bulletin","Federal Reserve Bulletin"
items=[];page=1;total=None;gaps=[]
while True:
    try: d=jget(f"https://fraser.stlouisfed.org/api/title/{tid}/items?limit=100&page={page}",{"X-API-Key":K})
    except Exception as e:
        gaps.append({"page":page,"error":str(e)});page+=1
        if page>80: break
        continue
    total=d.get("total");recs=d.get("records",[])
    if not recs: break
    for r in recs:
        oi=r.get("originInfo") or {};loc=r.get("location") or {};ri=r.get("recordInfo") or {}
        rid=ri.get("recordIdentifier");rid=rid[0] if isinstance(rid,list) and rid else rid
        ti=(r.get("titleInfo") or [{}]);itl=ti[0].get("title","") if ti else ""
        items.append({"rid":rid,"item_title":itl,"sortDate":oi.get("sortDate"),"dateIssued":oi.get("dateIssued"),
            "frequency":oi.get("frequency"),"pdfUrl":one(loc.get("pdfUrl")),"textUrl":one(loc.get("textUrl")),"pageUrl":one(loc.get("url"))})
    if len(items)>=(total or 0): break
    page+=1;time.sleep(0.06)
dates=sorted([i["sortDate"][:10] for i in items if i.get("sortDate")])
json.dump({"title_id":tid,"slug":slug,"name":name,"total_declared":total,"n_enumerated":len(items),"gaps":gaps,"items":items},open(f"{OUT}/{slug}_issues.json","w"))
print(f"FEDBULL enum {len(items)}/{total} pdf={sum(1 for i in items if i.get('pdfUrl'))} span {dates[0]}..{dates[-1]} gaps={len(gaps)}")

# ERP GovInfo: declared count + bounded sample (DEMO_KEY rate cap; §19.4 note the cap)
base="https://api.govinfo.gov/collections/ERP/1900-01-01T00:00:00Z"
erp=[];offset=0;total=None;capped=False
for _ in range(3):   # <=3 pages of 100 under DEMO_KEY
    try: d=jget(f"{base}?offset={offset}&pageSize=100&api_key={GK}",{})
    except Exception as e: erp_err=str(e); break
    total=d.get("count");pk=d.get("packages",[])
    if not pk: break
    for p in pk: erp.append({"packageId":p.get("packageId"),"dateIssued":p.get("dateIssued"),"title":p.get("title"),"docClass":p.get("docClass")})
    offset+=len(pk)
    if offset>=(total or 0): break
    time.sleep(0.1)
if total and offset<total: capped=True
ed=sorted([e["dateIssued"][:10] for e in erp if e.get("dateIssued")])
json.dump({"source":"GovInfo","collection":"ERP","total_declared":total,"n_sampled":len(erp),"sample_capped":capped,"packages":erp},open(f"{OUT}/erp_issues.json","w"))
print(f"ERP declared={total} sampled={len(erp)} capped={capped} span {ed[0] if ed else '-'}..{ed[-1] if ed else '-'}")
print("ENUM2_DONE")
