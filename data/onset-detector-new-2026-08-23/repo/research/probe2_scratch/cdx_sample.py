"""B-PROBE-2 §2.3 sample captures, byte-inspect payload-bearing verdict.
For each URL: find one capture near a target pre-2020 year, fetch RAW (id_ mode),
measure bytes + digit-density + table heuristic. Serial, polite."""
import json, re, time, urllib.request, urllib.parse
from pathlib import Path
H = Path("research/probe2_scratch")

# family : (target url, sample-year, payload regex hint)
SAMPLES = {
 "fed_g17":      ("federalreserve.gov/releases/g17/current/", "2010"),
 "bls_empsit":   ("bls.gov/news.release/empsit.nr0.htm", "2010"),
 "dol_ui":       ("dol.gov/ui/data.pdf", "2014"),
 "census_nrc":   ("census.gov/construction/nrc/index.html", "2013"),
 "philly_bos":   ("philadelphiafed.org/research-and-data/regional-economy/business-outlook-survey", "2012"),
 "census_mtis":  ("census.gov/mtis/index.html", "2012"),
 "chicago_nfci": ("chicagofed.org/publications/nfci/index", "2015"),
 "umich_sca":    ("sca.isr.umich.edu/", "2010"),
}
def get(url, raw=False):
    req = urllib.request.Request(url, headers={"User-Agent":"rmv2-probe/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.status, r.read()

out={}
for fam,(target,yr) in SAMPLES.items():
    rec={"url":target,"sample_year":yr}
    try:
        q=("http://web.archive.org/cdx/search/cdx?url="+urllib.parse.quote(target,safe='')+
           f"&output=json&from={yr}0101&to={yr}1231&fl=timestamp,statuscode&filter=statuscode:200&limit=1")
        _,b=get(q); rows=json.loads(b) if b.strip() else []
        data=rows[1:] if rows and rows[0][0]=="timestamp" else rows
        if not data:
            rec.update({"sampled":False,"note":"no 200 capture in target year"}); out[fam]=rec; time.sleep(2); continue
        ts=data[0][0]
        cap="http://web.archive.org/web/%sid_/%s"%(ts,("https://" if not target.startswith("http") else "")+target)
        st,body=get(cap)
        is_pdf = body[:4]==b"%PDF"
        text = "" if is_pdf else body.decode("utf-8","replace")
        # payload heuristics
        digits=len(re.findall(r"\d",text)) if text else None
        rows_numeric=len(re.findall(r"\d[\d,]{2,}\.\d",text)) if text else None  # decimal data cells
        table_tags=text.count("<table") if text else None
        payload = bool(is_pdf) or (rows_numeric and rows_numeric>20) or (table_tags and table_tags>0 and rows_numeric and rows_numeric>5)
        rec.update({"sampled":True,"capture_ts":ts,"http_status":st,"bytes":len(body),
                    "is_pdf":is_pdf,"table_tags":table_tags,"decimal_data_cells":rows_numeric,
                    "digit_count":digits,"payload_bearing":bool(payload)})
        (H/("sample_%s.txt"%fam)).write_bytes(body[:6000])
    except Exception as e:
        rec.update({"sampled":False,"error":repr(e)[:200]})
    out[fam]=rec
    print(fam, rec.get("capture_ts"), "bytes=",rec.get("bytes"),"pdf=",rec.get("is_pdf"),
          "cells=",rec.get("decimal_data_cells"),"PAYLOAD=",rec.get("payload_bearing"))
    time.sleep(2.5)
(H/"cdx_samples.json").write_text(json.dumps(out,indent=1)+"\n")
print("WROTE cdx_samples.json")
