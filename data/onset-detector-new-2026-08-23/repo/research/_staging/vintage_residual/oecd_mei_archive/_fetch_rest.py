import urllib.request,hashlib,json,os,time
measures={"B1GQ_Q":"GDP volume","P3_S1M_Q":"HH consumption vol","P3_S13_Q":"Govt consumption vol",
"P51G_Q":"GFCF vol","P6_Q":"Exports G&S vol","P7_Q":"Imports G&S vol","B1GQ_V":"GDP current prices",
"B1GQ_D":"GDP deflator","PRVM":"Production volume","TOVM":"Retail trade volume",
"LI_TR":"CLI trend restored","LI_AA":"CLI amplitude adj","RS":"Reference series GDP","CP":"Consumer prices",
"UNEMP":"Unemployment","EMP":"Employment","H_EARN":"Hourly earnings","ULC":"Unit labour cost",
"MABM":"M3","CA":"Current account","IM":"Merch imports","EX":"Merch exports"}
base="https://sdmx.oecd.org/public/rest/data/OECD.SDD.STES,DSD_STES_REVISIONS@DF_STES_REVISIONS,4.0/USA..{}....?format=csvfilewithlabels"
outdir="research/_staging/vintage_residual/oecd_mei_archive/us"
recs=[]
for m,lbl in measures.items():
    p=os.path.join(outdir,m+".csv"); url=base.format(m)
    rec={"measure":m,"label":lbl,"url":url,"path":p}
    if os.path.exists(p) and os.path.getsize(p)>1000:
        data=open(p,"rb").read()
        rec.update(status=200,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),
                   rows=data.count(b"\n"),note="already_present")
        recs.append(rec); continue
    for attempt in range(3):
        try:
            req=urllib.request.Request(url,headers={"User-Agent":"bristow-hall-vintage-fetch"})
            t=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())
            with urllib.request.urlopen(req,timeout=300) as r:
                data=r.read(); lm=r.headers.get("Last-Modified"); status=r.status
            open(p,"wb").write(data)
            rec.update(status=status,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),
                       rows=data.count(b"\n"),last_modified=lm,fetch_utc=t)
            break
        except Exception as e:
            rec.update(status="FAIL",error=str(e),attempt=attempt+1)
            time.sleep(5)
    recs.append(rec)
json.dump(recs,open(os.path.join(outdir,"_sidecars.json"),"w"),indent=2)
ok=[r for r in recs if r.get("status")==200]
open(os.path.join(outdir,"_DONE_FLAG"),"w").write(f"OK {len(ok)}/{len(measures)} bytes {sum(r['bytes'] for r in ok)}\n")
