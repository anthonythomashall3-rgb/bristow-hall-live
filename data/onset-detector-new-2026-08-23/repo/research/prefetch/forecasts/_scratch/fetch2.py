#!/usr/bin/env python3
# CH-R35 pass 2: corrected Livingston (real PDFs+support), Greenbook final probe, Cleveland, GDPNow, SEP.
import os, sys, time, json, hashlib, urllib.request, urllib.error, datetime
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
DECOY = "8d779811a40f"  # soft-404 placeholder sha256 prefix (18396 bytes)

def utc(): return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def fetch(url, outpath):
    if os.path.exists(outpath) and os.path.getsize(outpath) > 0:
        b=open(outpath,"rb").read()
        return {"url":url,"path":os.path.relpath(outpath,ROOT),"bytes":len(b),
                "sha256":hashlib.sha256(b).hexdigest(),"fetch_utc":"cached","status":"cached"}
    err=None
    for attempt in (1,2):
        try:
            req=urllib.request.Request(url,headers={"User-Agent":UA})
            with urllib.request.urlopen(req,timeout=45) as r: data=r.read()
            sha=hashlib.sha256(data).hexdigest()
            if sha.startswith(DECOY):
                return {"url":url,"path":os.path.relpath(outpath,ROOT),"bytes":len(data),
                        "sha256":sha,"status":"DECOY"}  # do NOT write soft-404
            os.makedirs(os.path.dirname(outpath),exist_ok=True)
            open(outpath,"wb").write(data)
            return {"url":url,"path":os.path.relpath(outpath,ROOT),"bytes":len(data),
                    "sha256":sha,"fetch_utc":utc(),"content_type":r.headers.get("Content-Type",""),"status":"ok"}
        except urllib.error.HTTPError as e:
            err=f"HTTP {e.code}"
            if e.code in (404,403): break
        except Exception as e: err=str(e)[:120]
        time.sleep(1.0)
    return {"url":url,"path":os.path.relpath(outpath,ROOT),"status":"FAIL","error":err}

def run(source, items):
    outdir=os.path.join(ROOT,source); recs=[]
    for name,url in items:
        rec=fetch(url,os.path.join(outdir,name)); recs.append(rec)
        print(f"  [{source}] {rec['status']:6} {name} {rec.get('bytes','')}",flush=True)
        if rec["status"] not in ("cached",): time.sleep(1.0)
    os.makedirs(outdir,exist_ok=True)
    # merge into existing manifest if present
    mp=os.path.join(outdir,"MANIFEST.sha256.json"); prev=[]
    if os.path.exists(mp):
        try: prev=json.load(open(mp)).get("files",[])
        except: pass
    seen={r["url"] for r in recs}
    merged=[p for p in prev if p["url"] not in seen and p.get("status") in ("ok","cached")]+recs
    json.dump({"source":source,"generated_utc":utc(),"files":merged},open(mp,"w"),indent=2)
    ok=sum(1 for r in recs if r["status"] in ("ok","cached"))
    print(f"== {source}: {ok}/{len(recs)} new-ok ==",flush=True)

LIV="https://www.philadelphiafed.org/-/media/FRBP/Assets/Surveys-And-Data/livingston-survey"
def livingston_items():
    it=[("livingston-documentation.pdf",LIV+"/livingston-documentation.pdf"),
        ("livingston-data-sources.pdf",LIV+"/livingston-data-sources.pdf"),
        ("livingston-errata.pdf",LIV+"/livingston-errata.pdf"),
        ("brma97dc.pdf",LIV+"/brma97dc.pdf")]
    mons=["jun","dec"]
    for yr in range(1991,2027):
        yy=f"{yr%100:02d}"
        for m in mons:
            if yr==2026 and m=="dec": continue
            it.append((f"survey_pdfs/liv{m}{yy}.pdf", LIV+f"/{yr}/liv{m}{yy}.pdf"))
    return it

def greenbook_items():
    GB="https://www.philadelphiafed.org/-/media/frbp/assets/surveys-and-data/greenbook-data-sets"
    RT="https://www.philadelphiafed.org/-/media/frbp/assets/surveys-and-data/real-time-data"
    cand=["gbweb_row_format.zip","gbweb_column_format.zip","greenbook-data-set.zip",
          "gbfcst.zip","tealbook.zip","GBweb.zip"]
    it=[(c, GB+"/"+c) for c in cand]
    it+=[("rt_gbweb_row.xlsx", RT+"/greenbook-data-sets/gbweb_row_format.xlsx")]
    return it

def cleveland_items():
    return [("cleveland_inflation_nowcast.xlsx",
             "https://www.clevelandfed.org/-/media/files/webcharts/inflationnowcasting/inflation-nowcast-data.xlsx"),
            ("cleveland_nowcasting.xlsx",
             "https://www.clevelandfed.org/indicators-and-data/inflation-nowcasting/download-data")]

def gdpnow_items():
    return [("GDPTrackingModelDataAndForecasts.xlsx",
             "https://www.atlantafed.org/-/media/documents/cqer/researchcq/gdpnow/GDPTrackingModelDataAndForecasts.xlsx"),
            ("gdpnow_track_record.xlsx",
             "https://www.atlantafed.org/-/media/documents/cqer/researchcq/gdpnow/RealGDPTrackRecord.xlsx")]

def sep_items():
    fr="https://www.federalreserve.gov"
    return [("SEPmedianandrange.csv", fr+"/monetarypolicy/files/fomcprojtabl20240320.csv"),
            ("fomc_sep_landing.htm", fr+"/monetarypolicy/fomc_projections.htm")]

if __name__=="__main__":
    jobs={"livingston":("livingston",livingston_items()),
          "greenbook":("greenbook",greenbook_items()),
          "cleveland":("cleveland_nowcast",cleveland_items()),
          "gdpnow":("gdpnow",gdpnow_items()),
          "sep":("fomc_sep",sep_items())}
    which=sys.argv[1] if len(sys.argv)>1 else "all"
    for k in (list(jobs) if which=="all" else [which]):
        run(*jobs[k])
