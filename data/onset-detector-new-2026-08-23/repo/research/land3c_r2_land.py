import json,sys,os,re,argparse
sys.path.insert(0,"live_data")
from pathlib import Path
from rmv2_live.config import load_config
from rmv2_live.store import LiveStore
from rmv2_live.pipeline import RefreshPipeline
from rmv2_live import fredmd_panel as fp
from rmv2_live.offline_binding import bind_offline_vintage

ROOT=Path(".").resolve()
CFG_PATH=ROOT/"live_data/config/sources.v1.json"
AS_OF="2026-08-05T00:00:00Z"
DMIN,DMAX="20000101","20191231"

BASES={
 "W875RX1":{"label":"Real personal income excluding current transfer receipts",
            "unit":"Billions of Chained 2017 Dollars","near":False,
            "concept":"Real personal income ex current transfer receipts"},
 "CLAIMSx":{"label":"Initial Claims (FRED-MD spliced construct, NEAR of ICSA)",
            "unit":"Number","near":True,"concept":"Initial unemployment claims"},
 "CMRMTSPLx":{"label":"Real Manufacturing and Trade Industries Sales (FRED-MD spliced construct, NEAR of CMRMTSPL)",
            "unit":"Millions of Chained 2017 Dollars","near":True,
            "concept":"Real manufacturing and trade industries sales"},
}

def source_for(base):
    m=BASES[base]
    return {
     "adapter":"fred_json_api_vintages_deep",
     "allowed_hosts":["www.stlouisfed.org"],
     "archival":True,
     "coverage_source_ids":["fred_md_official_panels"],
     "enabled":False,
     "endpoint":"https://www.stlouisfed.org/research/economists/mccracken/fred-databases",
     "expected_content_types":["text/csv"],
     "frequency":"monthly",
     "information_set_mode":"archive_snapshot_asof",
     "label":"%s (FRED-MD monthly panel reconstructed vintage matrix, as-of snapshots) [DEEP pre-2020 as-of window]"%m["concept"],
     "max_bytes":33554432,
     "method_version":"fred_%s_fredmd_panel_vintages_deep.v1"%base.lower(),
     "poll_seconds":21600,
     "publisher":"Federal Reserve Bank of St. Louis (McCracken FRED-MD)",
     "publisher_release_clock":"named monthly FRED-MD panel release; underlying publisher release time null unless separately proven",
     "rights_status":"FRED_terms_and_underlying_publisher_rights_control",
     "secret_env":None,
     "secret_required":False,
     "series":{"label":m["label"],"series_id":base,"unit":m["unit"]},
     "source_id":"fred_%s_fredmd_panel_vintages_deep"%base.lower(),
     "value_status":"actual",
    }

def all_panels():
    roots=["data_archive/additional_vintages/fred_md_official/extracted",
           "data_archive/additional_vintages/fred_md_official/current"]
    ps=[]
    for r in roots:
        for dp,_,fns in os.walk(r):
            for fn in fns:
                if fn.lower().endswith(".csv"): ps.append(os.path.join(dp,fn))
    return sorted(ps)

def store_existing(store, base):
    """existing deep floor (min vintage yyyymmdd) + existing deepasof ids for base."""
    ids=set()
    for sid in ["fred_%s_api_vintages_deep"%base.lower(),
                "fred_%s_api_vintages"%base.lower()]:
        h=store.read_source_head(sid)
        if not h: continue
        n=store.read_normalized(h["normalized_sha256"])
        for r in n["records"]:
            ids.add(r["series_id"])
    deep=[i for i in ids if ".DEEPASOF" in i and i.startswith(base+".DEEPASOF")]
    vintages=sorted(i.split(".DEEPASOF")[1] for i in deep)
    floor=vintages[0] if vintages else None
    return floor, ids

def plan(store):
    panels=all_panels()
    out={}
    for base in BASES:
        floor, existing = store_existing(store, base)
        kept=[]; excl_window=[]; excl_floor=[]; excl_coll=[]
        for p in panels:
            v=fp.vintage_yyyymmdd(p)
            if not (DMIN<=v<=DMAX): excl_window.append((p,v)); continue
            sid="%s.DEEPASOF%s"%(base,v)
            if sid in existing: excl_coll.append((p,v)); continue
            if floor is not None and v>=floor: excl_floor.append((p,v)); continue
            kept.append(p)
        out[base]={"floor":floor,"kept":kept,"n_kept":len(kept),
                   "n_excl_window":len(excl_window),"n_excl_floor":len(excl_floor),
                   "n_excl_coll":len(excl_coll),
                   "excl_coll":[v for _,v in excl_coll],
                   "kept_vmin":fp.vintage_yyyymmdd(kept[0]) if kept else None,
                   "kept_vmax":fp.vintage_yyyymmdd(kept[-1]) if kept else None}
    return out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--dry",action="store_true"); a=ap.parse_args()
    cfg=load_config(CFG_PATH)
    store=LiveStore(ROOT,cfg); store.initialize()
    pl=plan(store)
    for b,d in pl.items():
        print(f"{b}: floor={d['floor']} kept={d['n_kept']} ({d['kept_vmin']}..{d['kept_vmax']}) "
              f"excl_window={d['n_excl_window']} excl_floor={d['n_excl_floor']} excl_coll={d['n_excl_coll']} {d['excl_coll']}")
    if a.dry:
        json.dump({b:{k:v for k,v in d.items() if k!='kept'} for b,d in pl.items()},
                  open("research/land3c_r2_plan.json","w"),indent=1)
        print("DRY — no writes"); return
    # REAL landing
    pipeline=RefreshPipeline(ROOT,cfg)
    pipeline.store.initialize()
    pred=None; outcomes=[]
    # W875RX1 blocked by the append-only one-.DEEPASOF-lane-per-base invariant
    # (ALFRED fred_w875rx1_api_vintages_deep already owns W875RX1.DEEPASOF*).
    # Owner-decision filed; only the two NEW NEAR bases land this sitting.
    for base in ["CLAIMSx","CMRMTSPLx"]:
        src=source_for(base); kept=pl[base]["kept"]
        oc=bind_offline_vintage(pipeline, src, kept, AS_OF,
                                predecessor_receipt_sha256=pred, transcoder=fp)
        pred=oc["receipt_sha256"]
        cfg["sources"].append(src)
        outcomes.append(oc)
        print("BOUND",base,"records",oc["record_count"],"series",len(oc["landed_series"]),"receipt",oc["receipt_sha256"][:12])
    # write config with 3 new sources
    raw=json.load(open(CFG_PATH))
    raw["sources"]=cfg["sources"]
    tmp=str(CFG_PATH)+".tmp"
    json.dump(raw,open(tmp,"w"),indent=1,sort_keys=True); os.replace(tmp,CFG_PATH)
    print("CONFIG written; n_sources",len(raw["sources"]))
    # publish generation
    ATT="2026-08-05T21:30:00Z"
    snap=pipeline.build_snapshot(ATT); cov=pipeline.build_coverage(ATT); st=pipeline.build_status(ATT)
    ptr=pipeline.store.publish_generation(snap, st, cov)
    print("PUBLISHED generation", ptr.get("generation_sha256"))
    json.dump({"outcomes":outcomes,"pointer":ptr},open("research/land3c_r2_land_out.json","w"),indent=1)

main()
