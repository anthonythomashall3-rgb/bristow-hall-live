import os,sys,json,urllib.request,time,hashlib,datetime
OUT="research/periodical_vintages"
K=os.environ.get("FRASER_API_KEY")
GK=os.environ.get("GOVINFO_API_KEY","DEMO_KEY")
UTC=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()

def jget(url,headers,tries=5,timeout=60):
    last=None
    for i in range(tries):
        try:
            req=urllib.request.Request(url,headers=headers)
            with urllib.request.urlopen(req,timeout=timeout) as r:
                return json.load(r)
        except Exception as e:
            last=e; time.sleep(1.0*(i+1))
    raise last

def fetch_bytes(url,headers,timeout=120):
    req=urllib.request.Request(url,headers=headers)
    with urllib.request.urlopen(req,timeout=timeout) as r:
        return r.getcode(), r.read()

# ---------- FRASER titles ----------
FRASER=[(46,"survey_current_business","Survey of Current Business"),
        (62,"federal_reserve_bulletin","Federal Reserve Bulletin")]
summary={"generated_utc":UTC(),"families":[]}
for tid,slug,name in FRASER:
    items=[]; page=1; total=None; gaps=[]
    while True:
        try:
            d=jget(f"https://fraser.stlouisfed.org/api/title/{tid}/items?limit=100&page={page}",{"X-API-Key":K})
        except Exception as e:
            gaps.append({"page":page,"error":str(e)}); page+=1
            if page>80: break
            continue
        total=d.get("total"); recs=d.get("records",[])
        if not recs: break
        for r in recs:
            oi=r.get("originInfo") or {}
            loc=r.get("location") or {}
            ri=r.get("recordInfo") or {}
            rid=ri.get("recordIdentifier"); rid=rid[0] if isinstance(rid,list) and rid else rid
            ti=(r.get("titleInfo") or [{}]); itl=ti[0].get("title","") if ti else ""
            def one(v): return v[0] if isinstance(v,list) and v else v
            items.append({"rid":rid,"item_title":itl,"sortDate":oi.get("sortDate"),
                "dateIssued":oi.get("dateIssued"),"frequency":oi.get("frequency"),
                "pdfUrl":one(loc.get("pdfUrl")),"textUrl":one(loc.get("textUrl")),"pageUrl":one(loc.get("url"))})
        if len(items)>=(total or 0): break
        page+=1; time.sleep(0.06)
    dates=sorted([i["sortDate"][:10] for i in items if i.get("sortDate")])
    json.dump({"title_id":tid,"slug":slug,"name":name,"total_declared":total,"n_enumerated":len(items),
               "gaps":gaps,"items":items}, open(f"{OUT}/{slug}_issues.json","w"))
    summary["families"].append({"source":"FRASER","title_id":tid,"slug":slug,"name":name,
        "total_declared":total,"n_enumerated":len(items),"n_with_pdf":sum(1 for i in items if i.get("pdfUrl")),
        "n_with_text":sum(1 for i in items if i.get("textUrl")),
        "n_with_sortDate":len(dates),"earliest":dates[0] if dates else None,"latest":dates[-1] if dates else None,
        "gaps":len(gaps)})
    print(f"FRASER {slug}: enum {len(items)}/{total} pdf={summary['families'][-1]['n_with_pdf']} span {dates[0] if dates else '-'}..{dates[-1] if dates else '-'}")

# ---------- GovInfo ERP ----------
erp=[]; offset=0; page_size=100; total=None
base="https://api.govinfo.gov/collections/ERP/1900-01-01T00:00:00Z"
while True:
    try:
        d=jget(f"{base}?offset={offset}&pageSize={page_size}&api_key={GK}",{})
    except Exception as e:
        summary.setdefault("erp_error",str(e)); break
    total=d.get("count"); pk=d.get("packages",[])
    if not pk: break
    for p in pk:
        erp.append({"packageId":p.get("packageId"),"dateIssued":p.get("dateIssued"),
            "title":p.get("title"),"docClass":p.get("docClass"),"packageLink":p.get("packageLink")})
    offset+=len(pk)
    if offset>=(total or 0): break
    time.sleep(0.08)
ed=sorted([e["dateIssued"][:10] for e in erp if e.get("dateIssued")])
json.dump({"source":"GovInfo","collection":"ERP","total_declared":total,"n_enumerated":len(erp),"packages":erp},
          open(f"{OUT}/erp_issues.json","w"))
summary["families"].append({"source":"GovInfo","collection":"ERP","name":"Economic Report of the President",
    "total_declared":total,"n_enumerated":len(erp),"earliest":ed[0] if ed else None,"latest":ed[-1] if ed else None})
print(f"GovInfo ERP: enum {len(erp)}/{total} span {ed[0] if ed else '-'}..{ed[-1] if ed else '-'}")

json.dump(summary,open(f"{OUT}/_enum_summary.json","w"),indent=1)
print("ENUM_DONE")
